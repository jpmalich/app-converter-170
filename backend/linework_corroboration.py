"""SEND-129 — the SECOND READ the lift consumes: per-face WALL-ONLY widths
from the drawn line-work, produced with the pipeline's own instruments
(height_read.derive_face_heights for the face's band + datum chain,
linework_read.wall_outline_from_segments for the outline).

Geometry only: the read never sees a label, so it cannot inherit a label's
ambiguity — but it CAN inherit two other ways, and both are checked here:
  · FENCE — a neighbouring drawing's datum extent reaching inside this
    face's fence (SEND-84 rule) → the read is flagged, never lifted;
  · SCALE — the pixels→feet ruler is the face's own datum chain quote; a
    CONTESTED chain, or a quote that is itself unattributed, makes the
    read circular → flagged, never lifted.
"""
import os

FACE_KEY = {"front": "front", "rear": "back", "left": "left",
            "right": "right"}


def _fppx(cand, top_d, bot_d, pgd):
    ft = cand.get("feet")
    if ft is None and cand.get("inches"):
        ft = float(cand["inches"]) / 12.0
    if ft is None:
        vals = [g.get("value_in") for g in (cand.get("gaps") or [])
                if g.get("from") == "TOP_OF_PLATE" and g.get("value_in")]
        ft = (max(vals) / 12.0) if vals else None
    if not ft or not pgd.get("page_w") or not pgd.get("page_h"):
        return None, None
    span = abs(bot_d["y"] - top_d["y"])
    if span <= 0:
        return None, None
    return (float(ft) / (span / 100.0 * pgd["page_h"]) * pgd["page_w"]
            / 100.0), float(ft)


def _fences(faces_geo):
    """{page: [(face, band, fence)]} for the neighbouring-drawing check."""
    out = {}
    for face, cand in faces_geo:
        geo = cand.get("datum_geometry") or {}
        xs = []
        for dkey in ("top_of_plate", "first_floor", "top_of_foundation"):
            for mk in (geo.get(dkey) or {}).get("markers") or []:
                xs.extend(mk)
        if len(xs) < 2:
            continue
        band = cand.get("band") or [0.0, 100.0]
        out.setdefault(str(cand.get("page")), []).append(
            (face, (band[0], band[1]), (min(xs), max(xs))))
    return out


def read_face_widths(ot: dict, pdf_path: str,
                     ambiguous_quotes=None) -> dict:
    """{face_key: read} for the four faces. face_key matches the wall
    labels the aggregation uses (front/back/left/right)."""
    from height_read import derive_face_heights
    from linework_read import page_segments, wall_outline_from_segments

    if not (isinstance(ot, dict) and ot and pdf_path
            and os.path.exists(pdf_path)):
        return {}
    ambiguous_quotes = {str(q) for q in (ambiguous_quotes or [])}
    faces = derive_face_heights(ot)
    pairs = []
    for face, res in faces.items():
        for c in (res.get("candidates") or ([res] if res.get("band") else [])):
            pairs.append((face, c, res))
    fences = _fences([(f, c) for f, c, _ in pairs])
    seg_cache = {}
    out = {}
    for face, cand, res in pairs:
        key = FACE_KEY.get(face, face)
        if key in out and out[key].get("status") == "RESOLVED":
            continue
        geo = cand.get("datum_geometry") or {}
        top_d, bot_d = geo.get("top_of_plate"), geo.get("first_floor")
        if not (top_d and bot_d and top_d.get("b0") is not None
                and bot_d.get("b0") is not None):
            out[key] = {"status": "NOT_ATTEMPTED",
                        "reason": (res.get("refusal")
                                   or "datum pair not located on this "
                                      "drawing")}
            continue
        page = str(cand.get("page"))
        idx = int(page) - 1
        pgd = ot.get(page) or {}
        try:
            if idx not in seg_cache:
                seg_cache[idx] = page_segments(pdf_path, idx)
            mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
                     u["loc"]["x_pct"] + u["loc"]["w_pct"],
                     u["loc"]["y_pct"] + u["loc"]["h_pct"])
                    for u in (pgd.get("runs") or [])]
            xs = []
            for dkey in ("top_of_plate", "first_floor", "top_of_foundation"):
                for mk in (geo.get(dkey) or {}).get("markers") or []:
                    xs.extend(mk)
            x_fence = (min(xs), max(xs)) if len(xs) >= 2 else None
            band = cand.get("band") or [0.0, 100.0]
            lw = wall_outline_from_segments(
                seg_cache[idx], (band[0], band[1]),
                (top_d["b0"], top_d["b1"]), (bot_d["b0"], bot_d["b1"]),
                mask, x_fence=x_fence)
        except Exception as e:
            out[key] = {"status": "INDETERMINATE",
                        "reason": f"line-work read failed: {e}"}
            continue
        warn = None
        if x_fence:
            for f2, b2, fn2 in fences.get(page, []):
                if f2 == face or not (b2[0] < band[1] and b2[1] > band[0]):
                    continue
                if fn2[0] < x_fence[1] and fn2[1] > x_fence[0]:
                    warn = (f"the {f2} drawing's datum extent reaches "
                            f"inside this face's fence")
                    break
        fppx, chain_ft = _fppx(cand, top_d, bot_d, pgd)
        span = lw.get("wall_corners") or lw.get("body_x_span")
        entry = {
            "status": lw.get("status"), "reason": lw.get("reason"),
            "page": page, "fence_margin_warning": warn,
            "scale_quote": cand.get("from_quote") or cand.get("quote"),
            "scale_contested": str(cand.get("status")) == "CONTESTED"
                               or str(res.get("status")) == "CONTESTED",
            "scale_quote_unattributed": bool(
                str(cand.get("from_quote") or "") in ambiguous_quotes),
            "wall_only_ft": (round((span[1] - span[0]) * fppx, 2)
                             if (span and fppx) else None),
            "silhouette_ft": (round((lw["x_span"][1] - lw["x_span"][0])
                                    * fppx, 2)
                              if (lw.get("x_span") and fppx) else None),
            "chain_ft": chain_ft,
        }
        if entry["wall_only_ft"] is None and lw.get("status") == "RESOLVED":
            entry["reason"] = (entry["reason"]
                               or ("no plate-terminated wall corners, or no "
                                   "face scale — a wall-only width does not "
                                   "stand"))
        out[key] = entry
    return out
