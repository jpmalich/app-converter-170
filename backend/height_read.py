"""SEND-47 HEIGHT BUILD — wired (Howard authorized 2026-08-18).

Sealed DP-1: siding height = FIRST FLOOR (subfloor line) -> topmost TOP
OF PLATE (plate/soffit), read from the face's OWN elevation drawing. A
face that establishes the band is DERIVED; every other face REFUSES with
the exact gap named. Model heights are DEMOTED TO HYPOTHESIS (census
finding, SEND-46): shown on the record, never feeding a quantity.

Standing Prohibition is structural here: a rail can only enter a face if
its glyph box lies inside that face's own title-carved band — cross-face
copying is not a policy, it is impossible.

DP-5 (sealed): an overall rail is admitted POSITIONALLY — its glyph box
straddles an interior datum line inside the span (a rail resident in one
gap is that gap's rail, Ruling JJ). Subtraction closes undimensioned
strips only from such a rail with strict closure (all-bound spans demand
residual 0). None exists in the current datastore (SEND-46 census) — the
joist band refuses, a named open. No convention is invented.
"""
import re

from ocr_geometry import (normalize_marks, is_dimension_like, axis_class,
                          glyph_count, merge_positions, _member_inches)

FACES = ("front", "rear", "left", "right")
MODEL_LABEL_TO_FACE = {"front": "front", "back": "rear", "rear": "rear",
                       "left": "left", "right": "right"}
DATUM_DEFS = (("TOP_OF_PLATE", "TOPOFPLATE"),
              ("SECOND_FLOOR", "SECONDFLOOR"),
              ("FIRST_FLOOR", "FIRSTFLOOR"),
              ("TOP_OF_FOUNDATION", "TOPOFFOUNDATION"),
              ("WALKOUT_FOOTER", "WALKOUTFOOTER"))
# prose + sheet-index strings, never datum lines
DATUM_EXCLUDE = ("PLAN", "JOIST", "ELEC", "CEILING")


def _sq(s):
    return re.sub(r"[^A-Z]", "", (s or "").upper())


def _cy(r):
    return r["loc"]["y_pct"] + r["loc"]["h_pct"] / 2


def face_bands(runs):
    """Per-face sub-titles carve the page into y-bands. A sub-title is a
    squashed string carrying exactly ONE face name plus ELEVATION in
    either token order — never a combined '&' sheet title (ELEVATIONS).
    The title sits BELOW its drawing: band = (previous title y, own y)."""
    best = {}
    for r in runs:
        s = _sq(r["raw"])
        if "ELEVATION" not in s or "ELEVATIONS" in s:
            continue
        hits = [f for f in FACES if f.upper() in s]
        if len(hits) != 1:
            continue
        y = _cy(r)
        if hits[0] not in best or y < best[hits[0]]:
            best[hits[0]] = y
    bands, prev = {}, 0.0
    for y, f in sorted((y, f) for f, y in best.items()):
        bands[f] = (prev, y)
        prev = y
    return bands


def elevation_page_faces(ot):
    """{page: {face: (y0, y1)}} for every page carrying face sub-titles."""
    out = {}
    for pg, page in ot.items():
        runs = page.get("runs") or []
        bands = face_bands(runs)
        if bands:
            out[str(pg)] = bands
    return out


def furniture_index(ot, elevation_pages):
    """TITLE-BLOCK FURNITURE (parameter-free, SEND-45): a squashed string
    whose box has an identical-string overlapping twin on a NON-ELEVATION
    page rides the title block on every sheet — never an elevation datum.
    Set membership, no thresholds."""
    idx = {}
    for pg, page in ot.items():
        if str(pg) in elevation_pages:
            continue
        for run in merge_positions(page.get("runs") or []):
            l = run["loc"]
            idx.setdefault(_sq(run["raw"]), []).append(
                (l["x_pct"], l["y_pct"],
                 l["x_pct"] + l["w_pct"], l["y_pct"] + l["h_pct"]))
    return idx


def _is_furniture(run, idx):
    l = run["loc"]
    a = (l["x_pct"], l["y_pct"], l["x_pct"] + l["w_pct"], l["y_pct"] + l["h_pct"])
    for b in idx.get(_sq(run["raw"]), ()):
        if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
            return True
    return False


def datum_lines(runs, y0, y1, furn_idx):
    """Datum labels in the band become horizontal datum LINES. Same-label
    instances whose glyph boxes y-overlap merge into ONE line (both ends
    label the same line); non-overlapping same-label instances are
    SEPARATE lines (two plate lines are real on a 2-story face)."""
    inst = []
    for r in runs:
        s = _sq(r["raw"])
        if any(x in s for x in DATUM_EXCLUDE):
            continue
        if _is_furniture(r, furn_idx):
            continue
        for name, tok in DATUM_DEFS:
            if tok in s:
                b0 = r["loc"]["y_pct"]
                b1 = b0 + r["loc"]["h_pct"]
                if y0 <= (b0 + b1) / 2 <= y1:
                    inst.append({"name": name, "b0": b0, "b1": b1})
                break
    lines = []
    for i in sorted(inst, key=lambda d: d["b0"]):
        for L in lines:
            if L["name"] == i["name"] and i["b0"] <= L["b1"] and i["b1"] >= L["b0"]:
                L["b0"] = min(L["b0"], i["b0"])
                L["b1"] = max(L["b1"], i["b1"])
                break
        else:
            lines.append(dict(i))
    for L in lines:
        L["y"] = round((L["b0"] + L["b1"]) / 2, 1)
    return sorted(lines, key=lambda L: L["y"])


def vertical_rails(runs, y0, y1):
    out = []
    for r in runs:
        if not is_dimension_like(normalize_marks(r["raw"])):
            continue
        if axis_class(r["loc"], glyph_count(r["raw"])) != "VERTICAL":
            continue
        b0 = r["loc"]["y_pct"]
        b1 = b0 + r["loc"]["h_pct"]
        if y0 <= (b0 + b1) / 2 <= y1:
            out.append({"raw": r["raw"], "in": _member_inches(r["raw"]),
                        "b0": b0, "b1": b1})
    return out


def gap_bind(lines, rails):
    """A rail binds to the adjacent datum-line pair whose OPEN interval
    STRICTLY contains its whole glyph box (a box touching a line is AT
    the datum, not between the pair). One distinct value per gap = BOUND
    (Ruling JJ, vertical analog); more = CONTESTED; none = UNDIMENSIONED."""
    gaps = []
    for a, b in zip(lines, lines[1:]):
        members = [r for r in rails if r["b0"] > a["b1"] and r["b1"] < b["b0"]]
        vals = sorted({r["in"] for r in members if r["in"] is not None})
        status = ("UNDIMENSIONED" if not members
                  else "BOUND" if len(vals) == 1 else "CONTESTED")
        gaps.append({"top": a, "bottom": b, "status": status,
                     "from": f"{a['name']}@{a['y']}",
                     "to": f"{b['name']}@{b['y']}",
                     "value_in": vals[0] if len(vals) == 1 else None,
                     "rails": [{"raw": r["raw"], "in": r["in"]}
                               for r in members]})
    return gaps


def _overall_candidates(lines, rails, top, bot):
    """DP-5 positional admission: strictly inside the span AND straddling
    an interior datum line (a gap-resident rail is that gap's rail)."""
    interior = [L for L in lines if top["y"] < L["y"] < bot["y"]]
    out = []
    for r in rails:
        if not (r["b0"] > top["b1"] and r["b1"] < bot["b0"]):
            continue
        if any(r["b0"] < L["b1"] and r["b1"] > L["b0"] for L in interior):
            out.append(r)
    return out


def _fmt_ftin(inches):
    ft, rem = divmod(int(inches), 12)
    return f"{ft}'-{rem}\""


def _contested_message(values_in):
    """SEND-48 ruled language for two-or-more wall-height candidates on
    one elevation. General: uses only the dimensions found on THIS
    drawing; never references another job; no hard-coded house."""
    dims = " and ".join(_fmt_ftin(v) for v in sorted(values_in))
    return (f"Two different wall heights found on this elevation ({dims}). "
            f"This usually means the front and rear plate heights are "
            f"different (common with cut-short side gables or stepped "
            f"foundations). Please verify or draw a zone.")


def dp1_face_height(face, lines, gaps, rails):
    """Sealed DP-1: lowest FIRST FLOOR line up to the topmost TOP OF
    PLATE line, every gap on the path BOUND (or closed by a DP-5 overall
    rail). Returns DERIVED with the chain, or REFUSED with the exact gap
    named in the surface language."""
    def refuse(reason):
        return {"status": "REFUSED",
                "refusal": (f"wall height not established from {face} "
                            f"elevation — {reason} — area not derivable")}
    plates = [L for L in lines if L["name"] == "TOP_OF_PLATE"]
    floors = [L for L in lines if L["name"] == "FIRST_FLOOR"]
    if not plates:
        return refuse("no TOP OF PLATE datum located")
    if not floors:
        return refuse("no FIRST FLOOR datum located")
    top, bot = plates[0], floors[-1]
    path = [g for g in gaps if g["top"]["y"] >= top["y"]
            and g["bottom"]["y"] <= bot["y"]]
    contested = [g for g in path if g["status"] == "CONTESTED"]
    if contested:
        vals = sorted({r["in"] for r in contested[0]["rails"]
                       if r["in"] is not None})
        return {"status": "REFUSED", "refusal": _contested_message(vals)}
    unbound = [g for g in path if g["status"] != "BOUND"]
    bound_sum = sum(g["value_in"] for g in path if g["status"] == "BOUND")
    cands = [r for r in _overall_candidates(lines, rails, top, bot)
             if r["in"] is not None]
    if not unbound:
        for r in cands:
            if r["in"] != bound_sum:
                return refuse(f"overall rail {r['raw']}({r['in']}\") does not "
                              f"close against the bound sum {bound_sum}\" "
                              f"(residual {r['in'] - bound_sum}\")")
        total = bound_sum
        chain = [f"{g['from']} → {g['to']} = {g['value_in']}\"" for g in path]
    else:
        vals = sorted({r["in"] for r in cands if r["in"] >= bound_sum})
        if not vals:
            g = unbound[0]
            return refuse(f"gap {g['from']} → {g['to']} UNDIMENSIONED")
        if len(vals) > 1:
            return {"status": "REFUSED", "refusal": _contested_message(vals)}
        total = vals[0]
        chain = [f"overall rail {vals[0]}\" − bound sum {bound_sum}\" closes "
                 + "; ".join(f"{g['from']} → {g['to']}" for g in unbound)
                 + f" (residual {vals[0] - bound_sum}\")"]
    return {"status": "DERIVED", "inches": total,
            "ft": round(total / 12.0, 2), "chain": chain,
            "span": f"{top['name']}@{top['y']} → {bot['name']}@{bot['y']}",
            "span_y": [top["y"], bot["y"]]}


def derive_face_heights(ot):
    """{face: result} for all four faces from the persisted OCR pages."""
    pages = elevation_page_faces(ot)
    furn_idx = furniture_index(ot, set(pages))
    where = {}
    for pg, bands in pages.items():
        for face, band in bands.items():
            where.setdefault(face, []).append((pg, band))
    out = {}
    for face in FACES:
        homes = where.get(face) or []
        if not homes:
            out[face] = {"status": "REFUSED",
                         "refusal": (f"no {face} elevation drawing located — "
                                     f"height not established — area not "
                                     f"derivable")}
            continue
        # RULING YY (SEND-48, structural — no sheet-type classification):
        # applies ONLY when a face's title appears more than once. A
        # duplicate title only competes if its band actually holds the
        # makings of a height read (FIRST FLOOR + TOP OF PLATE datum
        # lines AND vertical rails). A title over an empty band (an inset
        # or reference) is DROPPED, recorded on the provenance. Two
        # qualifying bands that AGREE corroborate; two that DISAGREE keep
        # the refusal and name both pages. A face with a SINGLE title
        # always evaluates directly (its refusal names its own gap).
        evals, dropped = [], []
        for pg, (y0, y1) in homes:
            raw_runs = ot[pg].get("runs") or []
            lines = datum_lines(raw_runs, y0, y1, furn_idx)
            rails = vertical_rails(merge_positions(raw_runs), y0, y1)
            qualifies = (len(homes) == 1
                         or (any(L["name"] == "TOP_OF_PLATE" for L in lines)
                             and any(L["name"] == "FIRST_FLOOR" for L in lines)
                             and bool(rails)))
            if qualifies:
                gaps = gap_bind(lines, rails)
                evals.append((pg, (y0, y1), lines, rails, gaps))
            else:
                dropped.append({"page": pg,
                                "reason": ("Ruling YY: band holds no "
                                           "FIRST FLOOR + TOP OF PLATE "
                                           "datums with vertical rails — "
                                           "not a competing height source")})
        if not evals:
            out[face] = {"status": "REFUSED",
                         "refusal": (f"no {face} elevation drawing located — "
                                     f"height not established — area not "
                                     f"derivable"),
                         "dropped_titles": dropped}
            continue
        results = []
        for pg, (y0, y1), lines, rails, gaps in evals:
            r = dp1_face_height(face, lines, gaps, rails)
            r["page"] = pg
            r["band"] = [round(y0, 1), round(y1, 1)]
            r["datum_lines"] = [f"{L['name']}@{L['y']}" for L in lines]
            r["gaps"] = [{k: g[k] for k in ("from", "to", "status",
                                            "value_in", "rails")}
                         for g in gaps]
            results.append(r)
        if len(results) == 1:
            r = results[0]
        else:
            derived = [x for x in results if x["status"] == "DERIVED"]
            if (len(derived) == len(results)
                    and len({x["inches"] for x in derived}) == 1):
                r = dict(derived[0])
                r["corroborated_by_pages"] = [x["page"] for x in derived[1:]]
            else:
                r = {"status": "REFUSED",
                     "refusal": (f"multiple {face} elevation drawings "
                                 f"located (pages "
                                 + ", ".join(x["page"] for x in results)
                                 + ") and they do not agree — area not "
                                   "derivable"),
                     "candidates": results}
        if dropped:
            r["dropped_titles"] = dropped
        out[face] = r
    return out


def apply_height_build(raw, walls):
    """Mutates walls per the sealed rulings and records provenance on
    raw['_height_build']. A run with no persisted OCR text CANNOT read
    its elevations: the build does not run, the walls stand as the model
    read them, and the run says so — disclosed, never silent."""
    ot = raw.get("_ocr_text_by_page")
    if not isinstance(ot, dict) or not ot:
        raw["_height_build"] = {
            "status": "NOT_RUN",
            "reason": ("no OCR text persisted on this run — the height "
                       "build cannot read the elevations; model heights "
                       "stand UNVERIFIED")}
        return raw["_height_build"]
    faces = derive_face_heights(ot)
    for w in walls:
        if not isinstance(w, dict):
            continue
        face = MODEL_LABEL_TO_FACE.get(str(w.get("label") or "").lower())
        w["_model_height_hypothesis_ft"] = w.get("height_ft")
        segs = [s for s in (w.get("height_segments") or [])
                if isinstance(s, dict)]
        for s in segs:
            s["_model_height_hypothesis_ft"] = s.get("height_ft")
            s["height_ft"] = None
        r = faces.get(face) if face else None
        if r is None:
            w["height_ft"] = None
            w["height_refusal_reason"] = (
                f"wall label {w.get('label')!r} does not map to an "
                f"elevation face — height not established — area not "
                f"derivable")
        elif r["status"] == "DERIVED" and segs:
            w["height_ft"] = None
            w["height_refusal_reason"] = (
                f"face height established ({r['ft']} ft) from the {face} "
                f"elevation, but the model claims height segments — "
                f"segment heights are HYPOTHESIS only — area not "
                f"derivable pending elevation segment x-extents (named "
                f"open)")
        elif r["status"] == "DERIVED":
            w["height_ft"] = r["ft"]
            w["height_src"] = "height_build"
        else:
            w["height_ft"] = None
            w["height_refusal_reason"] = r["refusal"]
    raw["_height_build"] = {"status": "APPLIED",
                            "model_heights_demoted": True,
                            "faces": faces}
    return raw["_height_build"]
