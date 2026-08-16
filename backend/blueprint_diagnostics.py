"""SEND-27 Item 3 — a plain diagnostic Howard can read IN THE BROWSER,
without a database view. Pure + read-only: it summarises what is ALREADY
persisted (GG OCR, EE closure reasons) and probes the OCR for the FF inputs.
It computes NOTHING that reaches money and selects NO depth value — it
surfaces RAW strings, pages and percent boxes so a human can verify.

Three sections, exactly as ruled:
  GG   — run count per page, where the OCR lives, truncation, int-key fires.
  FF   — the three input probes (garage label, LEFT/RIGHT elevation title
         blocks, depth string nearest the garage block) each with raw
         string + page + percent box, or ABSENT.
  EE   — per face: the refusal reason verbatim, the failing relation, and
         WHICH check produced it.
"""
from __future__ import annotations

import re

FACES = ("front", "back", "left", "right")
_FEET_INCH = re.compile(r"\d{1,3}\s*[-'’]")   # depth-ish: a number + feet mark


def _center(loc):
    if not isinstance(loc, dict):
        return None
    try:
        return (loc["x_pct"] + loc["w_pct"] / 2.0,
                loc["y_pct"] + loc["h_pct"] / 2.0)
    except (KeyError, TypeError):
        return None


def _gg_section(result: dict, ocr_by_page: dict | None) -> dict:
    raw = result.get("raw_ai") or {}
    ref = raw.get("_ocr_text_ref") or {}
    by_page = raw.get("_ocr_text_by_page") or ocr_by_page or {}
    pages = {str(p): len((blk or {}).get("runs") or [])
             for p, blk in (by_page or {}).items()}
    where = ref.get("where") or ("run_doc" if raw.get("_ocr_text_by_page")
                                 else ("ai_blueprint_ocr" if ocr_by_page else None))
    coercions = (result.get("measurements") or {}).get("_int_key_coercions")
    return {
        "where": where,
        "pages": pages,
        "total_runs": sum(pages.values()),
        "truncated": ref.get("truncated"),
        "int_key_coercions": coercions or None,
        "coverage_chars": raw.get("_ocr_page_coverage_chars"),
    }


def _hits(by_page: dict, pred) -> list:
    out = []
    for pg, blk in (by_page or {}).items():
        for r in (blk or {}).get("runs") or []:
            if pred((r.get("raw") or ""), (r.get("norm") or "")):
                out.append({"page": str(pg), "raw": r.get("raw"),
                            "loc": r.get("loc")})
    return out


def _ff_section(result: dict, ocr_by_page: dict | None) -> dict:
    raw = result.get("raw_ai") or {}
    by_page = raw.get("_ocr_text_by_page") or ocr_by_page or {}

    garage = _hits(by_page, lambda t, n: "garage" in t.lower())

    def _title(side):
        # OCR often concatenates "LEFT ELEVATION" → "LEFTELEVATION".
        return _hits(by_page, lambda t, n, s=side:
                     s in t.upper() and "ELEVATION" in t.upper()
                     and "&" not in t)

    left_title = _title("LEFT")
    right_title = _title("RIGHT")

    # Depth string NEAREST the garage-block label, per page it appears on.
    # A geometric nearest-neighbour over feet-inch-looking runs — it selects
    # by DISTANCE, never by value (no tuning toward any figure).
    depth_near = []
    anchor = None
    # prefer a "3 CAR GARAGE" style block label over stray GARAGE tokens
    for h in garage:
        if "car" in (h["raw"] or "").lower() and _center(h["loc"]):
            anchor = h
            break
    if anchor is None:
        for h in garage:
            if _center(h["loc"]):
                anchor = h
                break
    if anchor is not None:
        ac = _center(anchor["loc"])
        cands = []
        for r in (by_page.get(anchor["page"]) or {}).get("runs") or []:
            txt = r.get("raw") or ""
            c = _center(r.get("loc"))
            if c and _FEET_INCH.search(txt):
                d = ((c[0] - ac[0]) ** 2 + (c[1] - ac[1]) ** 2) ** 0.5
                cands.append((d, {"page": anchor["page"], "raw": txt,
                                  "loc": r.get("loc"),
                                  "dist_pct": round(d, 1)}))
        cands.sort(key=lambda x: x[0])
        depth_near = [c for _d, c in cands[:3]]

    return {
        "garage_label": garage or "ABSENT",
        "garage_anchor_used": anchor or "ABSENT",
        "left_elevation_title": left_title or "ABSENT",
        "right_elevation_title": right_title or "ABSENT",
        "depth_near_garage": depth_near or "ABSENT",
    }


def _ee_section(result: dict) -> list:
    meas = result.get("measurements") or {}
    fc = meas.get("_footprint_closure") or {}
    refused = fc.get("refused_faces") or {}
    rels = fc.get("failing_relations") or []
    nd = meas.get("_faces_not_derivable") or []
    out = []
    for face in FACES:
        rows = [f for f in nd
                if str(f.get("elevation") or f.get("label") or "").lower() == face]
        if not rows and face not in refused:
            continue
        # prefer the footprint_closure surface for the headline reason
        fc_row = next((r for r in rows if r.get("surface") == "footprint_closure"), None)
        headline = (fc_row or (rows[0] if rows else {}))
        reason = headline.get("reason") or refused.get(face)
        produced_by = ("footprint_closure (Ruling EE)"
                       if headline.get("surface") == "footprint_closure"
                       or face in refused
                       else "derive-or-disclose (width/height not read)")
        failing_relation = refused.get(face) or next(
            (r for r in rels if r.lower().startswith(face)), None)
        out.append({
            "face": face,
            "refusal_reason": reason,
            "failing_relation": failing_relation,
            "produced_by": produced_by,
            "all_surfaces": [r.get("surface") for r in rows],
        })
    return out


def build_blueprint_diagnostics(result: dict, ocr_by_page: dict | None = None) -> dict:
    """The whole diagnostic. `result` is the stored run result; `ocr_by_page`
    is the separate-collection OCR body when it moved off the run doc."""
    result = result or {}
    return {
        "gg": _gg_section(result, ocr_by_page),
        "ff_inputs": _ff_section(result, ocr_by_page),
        "ee": _ee_section(result),
        "note": ("READ-ONLY diagnostic. Surfaces persisted GG OCR + EE "
                 "closure reasons and probes the OCR for FF inputs. Selects "
                 "no value; computes nothing that reaches money."),
    }


def render_plain(diag: dict) -> str:
    """Plain-text render (a fallback / the shape the UI mirrors). Readable
    without a database."""
    L = []
    gg = diag.get("gg") or {}
    L.append("== GG (OCR persistence) ==")
    L.append(f"stored: {gg.get('where')} · total runs: {gg.get('total_runs')}")
    L.append(f"runs per page: {gg.get('pages')}")
    L.append(f"truncated: {gg.get('truncated')} · int-key coercions: {gg.get('int_key_coercions')}")
    ff = diag.get("ff_inputs") or {}
    L.append("\n== FF INPUTS (probes) ==")
    for k in ("garage_label", "left_elevation_title", "right_elevation_title",
              "depth_near_garage"):
        v = ff.get(k)
        if v == "ABSENT" or not v:
            L.append(f"{k}: ABSENT")
        else:
            for h in (v if isinstance(v, list) else [v]):
                L.append(f"{k}: {h.get('raw')!r} p{h.get('page')} {h.get('loc')}")
    L.append("\n== EE (per-face refusal) ==")
    for e in diag.get("ee") or []:
        L.append(f"{e['face'].upper()}: {e.get('refusal_reason')}")
        L.append(f"   produced by: {e.get('produced_by')}")
    return "\n".join(L)
