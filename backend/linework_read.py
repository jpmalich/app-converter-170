"""SEND-69 — LINE-WORK READ, wall outline only (design:
memory/send63_linework_design.md, approved SEND-65/69).

Structural rules (design §1–§5 — set membership, no plausibility
thresholds; the only tolerance is the drawing's own line-weight scale,
taken from the datum label's own box height):

- Only `lines` + rect edges are read; glyphs are outlined CURVES in
  these prints and never enter. OCR boxes mask what remains.
- BAND CONTAINMENT: a qualifying stroke lies ENTIRELY inside the face's
  title-carved band. The SHEET BORDER is excluded by this rule
  STRUCTURALLY — it spans the page, so it always exits the band (into
  another drawing's band or the title block) on at least one end. Not a
  size threshold.
- LATERAL BOUNDARY: a single stroke spanning plate box → floor box, or
  a JOINTED CHAIN (vertical touching the plate + vertical touching the
  floor, terminating at the same y, with a horizontal whose ENDS meet
  both — a drawn joint, not a crossing). Steps and projections survive
  as extra vertices; the outline is the OUTERMOST spanning boundary on
  each side (the silhouette, by definition).
- Unresolvable → INDETERMINATE with the reason, never a silent
  fallback: the caller keeps the datum span under ITS OWN geometry
  tier and says so.

Nothing here is fit to any sealed width — 54/30/58/30'-2"/33 are
checks in the handback, never targets.
"""


# coordinate identity of one drawn vector line (numeric noise, in
# percent-of-page) — NOT a plausibility bound.
_COORD_EPS = 0.05


def _merge_cover(intervals, x0, x1, gap_tol):
    """Do the intervals cover [x0, x1] allowing joints up to gap_tol
    (the drawing's own datum-label box height — its line-weight scale)?"""
    ivs = sorted(intervals)
    cur = x0
    for a, b in ivs:
        if a > cur + gap_tol:
            return False
        cur = max(cur, b)
        if cur >= x1 - gap_tol:
            return True
    return cur >= x1 - gap_tol


def _merge_collinear(strokes, axis, gap_tol):
    """Drawn continuity: CAD strokes fragment at intersections. Pieces
    of ONE drawn line share its vector coordinate (identity within
    numeric noise, _COORD_EPS — not a plausibility bound); gaps ALONG
    the line up to gap_tol are joints. axis: 'v' or 'h'."""
    if axis == "v":
        items = sorted(((s["x0"] + s["x1"]) / 2.0, s["top"], s["bottom"])
                       for s in strokes)
    else:
        items = sorted(((s["top"] + s["bottom"]) / 2.0,
                        min(s["x0"], s["x1"]), max(s["x0"], s["x1"]))
                       for s in strokes)
    clusters = []
    for c, a, b in items:
        if clusters and c - clusters[-1][-1][0] <= _COORD_EPS:
            clusters[-1].append((c, a, b))
        else:
            clusters.append([(c, a, b)])
    merged = []
    for cl in clusters:
        ivs = sorted((a, b) for _, a, b in cl)
        pos = sum(c for c, _, _ in cl) / len(cl)
        cur_a, cur_b = ivs[0]
        for a, b in ivs[1:]:
            if a <= cur_b + gap_tol:
                cur_b = max(cur_b, b)
            else:
                merged.append((pos, cur_a, cur_b))
                cur_a, cur_b = a, b
        merged.append((pos, cur_a, cur_b))
    if axis == "v":
        return [{"x0": p, "x1": p, "top": a, "bottom": b}
                for p, a, b in merged]
    return [{"x0": a, "x1": b, "top": p, "bottom": p}
            for p, a, b in merged]


def _lateral_candidates(vert, horiz, plate_box, ff_box, gap_tol):
    """Boundary elements spanning the datum interval: single strokes
    plus one-jog jointed chains. A chain's jog lies STRICTLY BETWEEN
    the datum boxes — a horizontal AT datum level is a closure line,
    never a step. Each: {x_top, x_bot, jog_y}."""
    singles, tops, bots = [], [], []
    for s in vert:
        reach_top = s["top"] <= plate_box[1] and s["bottom"] >= plate_box[0]
        reach_bot = s["bottom"] >= ff_box[0] and s["top"] <= ff_box[1]
        span_top = s["top"] <= plate_box[1]
        span_bot = s["bottom"] >= ff_box[0]
        if span_top and span_bot:
            x = (s["x0"] + s["x1"]) / 2.0
            singles.append({"x_top": x, "x_bot": x, "jog_y": None})
        elif reach_top:
            tops.append(s)
        elif reach_bot:
            bots.append(s)
    jog_h = [h for h in horiz
             if plate_box[1] < (h["top"] + h["bottom"]) / 2.0 < ff_box[0]]
    chains = []
    for a in tops:
        xa = (a["x0"] + a["x1"]) / 2.0
        for b in bots:
            xb = (b["x0"] + b["x1"]) / 2.0
            if abs(a["bottom"] - b["top"]) > gap_tol:
                continue                      # do not terminate together
            lo, hi = min(xa, xb), max(xa, xb)
            if hi - lo <= gap_tol:
                continue                      # collinear stub, not a step
            jy = (a["bottom"] + b["top"]) / 2.0
            for h in jog_h:
                hy = (h["top"] + h["bottom"]) / 2.0
                if abs(hy - jy) > gap_tol:
                    continue
                h0, h1 = min(h["x0"], h["x1"]), max(h["x0"], h["x1"])
                # a JOINT: the horizontal's ENDS meet both verticals
                if abs(h0 - lo) <= gap_tol and abs(h1 - hi) <= gap_tol:
                    chains.append({"x_top": xa, "x_bot": xb, "jog_y": jy})
                    break
    return singles + chains


def wall_outline_from_segments(segments, band, plate_box, ff_box,
                               mask_boxes):
    """Pure core. segments: {x0,x1,top,bottom} in percent-of-page.
    band: (y0,y1) — the face's title-carved band. plate_box/ff_box: the
    governing datum LABEL's own (b0,b1) y-box (the FLOOR box may be the
    TOP OF FOUNDATION when the ladder dropped the bottom there).
    mask_boxes: OCR text boxes (x0,y0,x1,y1) pct. Returns RESOLVED with
    the outline polygon, or INDETERMINATE with the reason."""
    y0, y1 = band
    keep = []
    for s in segments:
        top, bot = min(s["top"], s["bottom"]), max(s["top"], s["bottom"])
        # BAND CONTAINMENT — structural sheet-border exclusion.
        if top < y0 or bot > y1:
            continue
        mx = (s["x0"] + s["x1"]) / 2.0
        my = (top + bot) / 2.0
        if any(bx0 <= mx <= bx1 and by0 <= my <= by1
               for bx0, by0, bx1, by1 in mask_boxes):
            continue
        keep.append({"x0": s["x0"], "x1": s["x1"],
                     "top": top, "bottom": bot})
    vert = [s for s in keep
            if abs(s["x1"] - s["x0"]) < (s["bottom"] - s["top"])]
    horiz = [s for s in keep
             if abs(s["x1"] - s["x0"]) >= (s["bottom"] - s["top"])]
    gap_tol = max(plate_box[1] - plate_box[0], ff_box[1] - ff_box[0])
    # drawn continuity: rejoin strokes fragmented at intersections
    vert = _merge_collinear(vert, "v", gap_tol)
    horiz = _merge_collinear(horiz, "h", gap_tol)
    cands = _lateral_candidates(vert, horiz, plate_box, ff_box, gap_tol)
    # a chain CONTRADICTED by a full spanning stroke strictly inside its
    # jog range is not a region boundary — that is interior detail
    # joined by a trim line, not a step in the silhouette.
    singles = [c for c in cands if c["jog_y"] is None]
    sx = [c["x_top"] for c in singles]
    cands = singles + [
        c for c in cands if c["jog_y"] is not None
        and not any(min(c["x_top"], c["x_bot"]) + _COORD_EPS < x
                    < max(c["x_top"], c["x_bot"]) - _COORD_EPS
                    for x in sx)]
    if len(cands) < 2:
        return {"status": "INDETERMINATE",
                "reason": ("fewer than two drawn boundaries span the "
                           "datum interval")}
    left = min(cands, key=lambda c: min(c["x_top"], c["x_bot"]))
    right = max(cands, key=lambda c: max(c["x_top"], c["x_bot"]))
    # two boundaries within one line-weight of each other are ONE drawn
    # corner (double-stroked), not two sides.
    if (max(left["x_top"], left["x_bot"]) + gap_tol
            >= min(right["x_top"], right["x_bot"])):
        return {"status": "INDETERMINATE",
                "reason": "all spanning boundaries sit at one corner"}

    def closure(box, xa, xb):
        cands_h = [s for s in horiz
                   if box[0] <= (s["top"] + s["bottom"]) / 2.0 <= box[1]]
        ivs = [(min(s["x0"], s["x1"]), max(s["x0"], s["x1"]))
               for s in cands_h]
        lo, hi = min(xa, xb), max(xa, xb)
        if not _merge_cover(ivs, lo, hi, gap_tol):
            return None
        tot = sum(abs(s["x1"] - s["x0"]) for s in cands_h) or 1.0
        return sum(((s["top"] + s["bottom"]) / 2.0)
                   * abs(s["x1"] - s["x0"]) for s in cands_h) / tot

    y_top = closure(plate_box, left["x_top"], right["x_top"])
    y_bot = closure(ff_box, left["x_bot"], right["x_bot"])
    if y_top is None:
        return {"status": "INDETERMINATE",
                "reason": "top boundary not closed at the plate level"}
    if y_bot is None:
        return {"status": "INDETERMINATE",
                "reason": "bottom boundary not closed at the floor level"}
    pts = [(left["x_top"], y_top), (right["x_top"], y_top)]
    if right["jog_y"] is not None:
        pts += [(right["x_top"], right["jog_y"]),
                (right["x_bot"], right["jog_y"])]
    pts += [(right["x_bot"], y_bot), (left["x_bot"], y_bot)]
    if left["jog_y"] is not None:
        pts += [(left["x_bot"], left["jog_y"]),
                (left["x_top"], left["jog_y"])]
    xs = [p[0] for p in pts]
    return {"status": "RESOLVED",
            "x_span": [round(min(xs), 2), round(max(xs), 2)],
            "y_top": round(y_top, 2), "y_bot": round(y_bot, 2),
            "n_spanning": len(cands), "n_vertices": len(pts),
            "vertices_pct": [[round(x / 100.0, 4), round(y / 100.0, 4)]
                             for x, y in pts]}


def page_segments(pdf_path, page_index):
    """Vector strokes of one PDF page in percent-of-page (top-based).
    Only `lines` and rect edges — glyphs are outlined CURVES here and
    never enter."""
    import pdfplumber
    segs = []
    with pdfplumber.open(pdf_path) as pdf:
        pg = pdf.pages[page_index]
        W, H = float(pg.width), float(pg.height)
        for L in pg.lines:
            segs.append({"x0": L["x0"] / W * 100, "x1": L["x1"] / W * 100,
                         "top": L["top"] / H * 100,
                         "bottom": L["bottom"] / H * 100})
        for rc in pg.rects:
            x0, x1 = rc["x0"] / W * 100, rc["x1"] / W * 100
            t, b = rc["top"] / H * 100, rc["bottom"] / H * 100
            segs += [{"x0": x0, "x1": x1, "top": t, "bottom": t},
                     {"x0": x0, "x1": x1, "top": b, "bottom": b},
                     {"x0": x0, "x1": x0, "top": t, "bottom": b},
                     {"x0": x1, "x1": x1, "top": t, "bottom": b}]
    return segs
