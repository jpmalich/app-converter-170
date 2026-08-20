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
            singles.append({"x_top": x, "x_bot": x, "jog_y": None,
                            # SEND-71 item 3: a stroke TERMINATING at the
                            # plate box (within a joint) is the drawn
                            # WALL LINE itself; roof-borne edges (rake,
                            # corner board) continue far above it.
                            "pt": s["top"] >= plate_box[0] - gap_tol})
        elif reach_top and s["top"] >= plate_box[0] - gap_tol:
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
                    chains.append({"x_top": xa, "x_bot": xb, "jog_y": jy,
                                   "pt": True})
                    break
    return singles + chains


def wall_outline_from_segments(segments, band, plate_box, ff_box,
                               mask_boxes, x_fence=None):
    """Pure core. segments: {x0,x1,top,bottom} in percent-of-page.
    band: (y0,y1) — the face's title-carved band. plate_box/ff_box: the
    governing datum LABEL's own (b0,b1) y-box (the FLOOR box may be the
    TOP OF FOUNDATION when the ladder dropped the bottom there).
    mask_boxes: OCR text boxes (x0,y0,x1,y1) pct. x_fence (SEND-77,
    authorized): the face's OWN datum-line extent (xmin,xmax) in pct —
    FENCE CONTAINMENT mirrors BAND CONTAINMENT: a qualifying stroke
    lies entirely inside the fence (± the drawing's own line-weight
    tolerance), so a second drawing sharing the band's y-range is
    excluded by the face's own evidence. The fence is applied VERBATIM
    — never shrunk to fit (that would be a threshold). Returns RESOLVED
    with the outline polygon, or INDETERMINATE with the reason."""
    y0, y1 = band
    gap_tol = max(plate_box[1] - plate_box[0], ff_box[1] - ff_box[0])
    keep = []
    for s in segments:
        top, bot = min(s["top"], s["bottom"]), max(s["top"], s["bottom"])
        # BAND CONTAINMENT — structural sheet-border exclusion.
        if top < y0 or bot > y1:
            continue
        # FENCE CONTAINMENT (SEND-77) — the face's own datum extent.
        if x_fence is not None:
            lo, hi = min(s["x0"], s["x1"]), max(s["x0"], s["x1"])
            if lo < x_fence[0] - gap_tol or hi > x_fence[1] + gap_tol:
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
    # drawn continuity: rejoin strokes fragmented at intersections
    vert = _merge_collinear(vert, "v", gap_tol)
    horiz = _merge_collinear(horiz, "h", gap_tol)
    cands = _lateral_candidates(vert, horiz, plate_box, ff_box, gap_tol)
    # SEND-71 item 3 — RAKE-EDGE SEPARATION. Where the drawing shows
    # WALL LINES (spanning strokes terminating at the plate box), the
    # outline is chosen among them and roof-borne edges lose. Where it
    # shows none (eave faces whose corner trim carries the edge up to
    # the eave), the spanning set stands as the only drawn boundary.
    # A preference for stronger evidence — not a size threshold, and
    # nothing tunes toward any sealed width.
    plate_terminated = [c for c in cands if c.get("pt")]
    if plate_terminated:
        cands = plate_terminated
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
    corner_singles = [c["x_top"] for c in cands
                      if c["jog_y"] is None and c.get("pt")]
    return {"status": "RESOLVED",
            "x_span": [round(min(xs), 2), round(max(xs), 2)],
            "top_corners": [round(left["x_top"], 2),
                            round(right["x_top"], 2)],
            # the outermost DRAWN WALL LINES (plate-terminated singles) —
            # the gable's base corners; a chimney chain is silhouette,
            # not a wall corner carrying a rake.
            "wall_corners": ([round(min(corner_singles), 2),
                              round(max(corner_singles), 2)]
                             if len(corner_singles) >= 2 else None),
            "y_top": round(y_top, 2), "y_bot": round(y_bot, 2),
            "n_spanning": len(cands), "n_vertices": len(pts),
            "vertices_pct": [[round(x / 100.0, 4), round(y / 100.0, 4)]
                             for x, y in pts]}


def gable_triangle_from_segments(segments, band, plate_box, top_corners,
                                 y_plate, mask_boxes):
    """SEND-71 item 5 — trace the DRAWN gable triangle above the plate.

    top_corners: (xL, xR), the resolved wall outline's top-edge corners.
    y_plate: the drawn plate-level closure. A RAKE is a diagonal stroke
    (both extents beyond the line-weight scale) whose line passes within
    a joint of a wall corner and rises inward; the two rakes' lines must
    intersect at an apex ABOVE the plate, inside the span, and both
    drawn upper ends must reach that apex within a joint — the triangle
    is drawn geometry or it is not returned. Never computed from pitch
    and width; nothing tunes toward any derived figure."""
    y0, y1 = band
    gap_tol = plate_box[1] - plate_box[0]
    diags = []
    for s in segments:
        if "p0" not in s:
            continue                     # rect edges are axis-aligned
        top, bot = min(s["top"], s["bottom"]), max(s["top"], s["bottom"])
        if top < y0 or bot > y1:
            continue                     # band containment (border out)
        dx, dy = abs(s["x1"] - s["x0"]), bot - top
        if dx <= gap_tol or dy <= gap_tol:
            continue                     # not a diagonal
        mx, my = (s["x0"] + s["x1"]) / 2.0, (top + bot) / 2.0
        if any(bx0 <= mx <= bx1 and by0 <= my <= by1
               for bx0, by0, bx1, by1 in mask_boxes):
            continue
        diags.append((tuple(s["p0"]), tuple(s["p1"])))
    if not diags:
        return {"status": "INDETERMINATE",
                "reason": "no diagonal strokes in this drawing's band"}

    def _line_dist(p, a, b):
        (px, py), (ax, ay), (bx, by) = p, a, b
        vx, vy = bx - ax, by - ay
        n = (vx * vx + vy * vy) ** 0.5
        return abs(vx * (py - ay) - vy * (px - ax)) / n if n else 1e9

    xl, xr = top_corners

    def _rake_for(cx, inward_right):
        best = None
        for a, b in diags:
            if _line_dist((cx, y_plate), a, b) > gap_tol:
                continue
            hi = a if a[1] < b[1] else b      # upper end (smaller top-y)
            if inward_right and not (hi[0] > cx + gap_tol):
                continue
            if not inward_right and not (hi[0] < cx - gap_tol):
                continue
            d = _line_dist((cx, y_plate), a, b)
            if best is None or d < best[0]:
                best = (d, a, b, hi)
        return best

    L = _rake_for(xl, inward_right=True)
    R = _rake_for(xr, inward_right=False)
    if not L or not R:
        return {"status": "INDETERMINATE",
                "reason": ("no drawn rake passes within a joint of the "
                           + ("left" if not L else "right")
                           + " wall corner")}
    (_, a1, b1, hi1), (_, a2, b2, hi2) = L, R
    # intersection of the two rake lines
    x1, y1a = a1
    dx1, dy1 = b1[0] - a1[0], b1[1] - a1[1]
    x2, y2a = a2
    dx2, dy2 = b2[0] - a2[0], b2[1] - a2[1]
    den = dx1 * dy2 - dy1 * dx2
    if abs(den) < 1e-9:
        return {"status": "INDETERMINATE",
                "reason": "the two rakes are parallel — no apex"}
    t = ((x2 - x1) * dy2 - (y2a - y1a) * dx2) / den
    ax_, ay_ = x1 + t * dx1, y1a + t * dy1
    if not (y0 <= ay_ < plate_box[0]):
        return {"status": "INDETERMINATE",
                "reason": "apex not above the plate inside this band"}
    if not (xl + gap_tol < ax_ < xr - gap_tol):
        return {"status": "INDETERMINATE",
                "reason": "apex outside the wall span"}
    for hi in (hi1, hi2):
        if ((hi[0] - ax_) ** 2 + (hi[1] - ay_) ** 2) ** 0.5 > 2 * gap_tol:
            return {"status": "INDETERMINATE",
                    "reason": ("a rake's drawn end stops short of the "
                               "apex — the ridge is not drawn to the "
                               "peak")}
    return {"status": "RESOLVED",
            "apex": [round(ax_, 2), round(ay_, 2)],
            "rise_pct": round(y_plate - ay_, 2),
            "n_diagonals": len(diags),
            "vertices_pct": [[round(xl / 100.0, 4),
                              round(y_plate / 100.0, 4)],
                             [round(ax_ / 100.0, 4),
                              round(ay_ / 100.0, 4)],
                             [round(xr / 100.0, 4),
                              round(y_plate / 100.0, 4)]]}


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
            # `pts` carries TRUE endpoint pairing (top-based); the bbox
            # y0/y1 fields are normalized and lose the slope sign.
            p0, p1 = L["pts"][0], L["pts"][-1]
            segs.append({"x0": L["x0"] / W * 100, "x1": L["x1"] / W * 100,
                         "top": L["top"] / H * 100,
                         "bottom": L["bottom"] / H * 100,
                         "p0": [p0[0] / W * 100, p0[1] / H * 100],
                         "p1": [p1[0] / W * 100, p1[1] / H * 100]})
        for rc in pg.rects:
            x0, x1 = rc["x0"] / W * 100, rc["x1"] / W * 100
            t, b = rc["top"] / H * 100, rc["bottom"] / H * 100
            segs += [{"x0": x0, "x1": x1, "top": t, "bottom": t},
                     {"x0": x0, "x1": x1, "top": b, "bottom": b},
                     {"x0": x0, "x1": x0, "top": t, "bottom": b},
                     {"x0": x1, "x1": x1, "top": t, "bottom": b}]
    return segs
