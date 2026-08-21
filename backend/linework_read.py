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


def _joint_lines(horiz, y_lo, y_hi):
    """RULING CCC (SEND-84) — drawn horizontal LINES strictly between
    the datum boxes (the jog region): raw kept strokes clustered at
    line-weight (_COORD_EPS) in y, each line's ink merged along x with
    breaks up to line-weight ONLY. The joint is judged on the line's
    own drawn ink — the gap_tol merge absorbs course lines and the
    joint's own connector pieces (SEND-82's 'shortfall' was that
    artifact). Returns [(y, [[x0, x1], ...]), ...]."""
    items = sorted({((s["top"] + s["bottom"]) / 2.0,
                     min(s["x0"], s["x1"]), max(s["x0"], s["x1"]))
                    for s in horiz
                    if y_lo < (s["top"] + s["bottom"]) / 2.0 < y_hi})
    lines = []
    for y, a, b in items:
        if lines and y - lines[-1][-1][0] <= _COORD_EPS:
            lines[-1].append((y, a, b))
        else:
            lines.append([(y, a, b)])
    out = []
    for cl in lines:
        y = sum(c[0] for c in cl) / len(cl)
        ivs = sorted((a, b) for _, a, b in cl)
        runs = [list(ivs[0])]
        for a, b in ivs[1:]:
            if a <= runs[-1][1] + _COORD_EPS:
                runs[-1][1] = max(runs[-1][1], b)
            else:
                runs.append([a, b])
        out.append((y, runs))
    return out


def _ccc_end_ok(r_end, x_bound, inward, through, strict_overspan=False):
    """RULING CCC (SEND-84, Howard's option b stated as a MINIMUM): one
    end of a joint line against its member's boundary stroke. `through`
    is the sorted x-list of through-going verticals at the line's y.
    - Reaching the boundary stroke (line-weight) passes.
    - Falling SHORT into the gap passes only if the end terminates ON
      the member's INNER TWIN: a through-going vertical at the end
      (line-weight identity) with NO other through-going vertical
      between it and the boundary stroke. A joint that cannot name the
      reference it terminates at has not established a shoulder — no
      snapping to the nearest stroke (that is how a tolerance sneaks
      back in through the endpoint). The allowance is the member's own
      drawn twin separation, never a constant.
    - OVERSPAN: for shoulder pairs (strict_overspan) the same naming
      law runs outward — the end terminates ON the boundary or ON the
      member's outer twin, never merely NEAR it (a face-long course
      line overspanning two members within gap_tol is a crossing, not
      a shoulder). Fragment chains keep the SEND-69 joint law outside
      (the caller bounds overspill by gap_tol — their members TERMINATE
      at the jog, which ties the joint structurally)."""
    over = (x_bound - r_end) * inward
    short = (r_end - x_bound) * inward
    if short <= _COORD_EPS and (not strict_overspan
                                or over <= _COORD_EPS):
        return True
    if over > _COORD_EPS and not strict_overspan:
        return True
    import bisect
    i = bisect.bisect_left(through, r_end - _COORD_EPS)
    if i >= len(through) or through[i] > r_end + _COORD_EPS:
        return False                # lands on neither twin of the member
    lo, hi = sorted((x_bound, r_end))
    # a stroke strictly between = the member carries 3+ strokes
    j = bisect.bisect_right(through, lo + _COORD_EPS)
    k = bisect.bisect_left(through, hi - _COORD_EPS)
    return j >= k


def _ccc_joint(jog_lines, vert, xa, xb, gap_tol, y_near=None,
               strict_overspan=False, _cache=None):
    """A drawn joint between boundary strokes at xa < xb under RULING
    CCC: a jog line whose ink meets both members. Outside, each end
    stays within the joint law (_ccc_end_ok — a joint, not a crossing);
    inside, a shortfall must terminate on the member's named inner
    twin. Returns the joint's drawn y or None. _cache memoizes each
    line's through-going verticals across pairs (identity, not a
    rule)."""
    import bisect
    if _cache is None:
        _cache = {}
    ys = _cache.get("_ys")
    if ys is None:
        ys = _cache["_ys"] = [ly for ly, _ in jog_lines]
    if y_near is not None:
        i0 = bisect.bisect_left(ys, y_near - gap_tol)
        i1 = bisect.bisect_right(ys, y_near + gap_tol)
    else:
        i0, i1 = 0, len(jog_lines)
    for li in range(i0, i1):
        ly, runs = jog_lines[li]
        through = None
        for r0, r1 in runs:
            if r1 < xa - gap_tol or r0 > xb + gap_tol:
                continue
            if r0 < xa - gap_tol or r1 > xb + gap_tol:
                continue            # a crossing, not a joint
            if through is None:
                through = _cache.get(li)
                if through is None:
                    through = _cache[li] = sorted(
                        (v["x0"] + v["x1"]) / 2.0 for v in vert
                        if v["top"] <= ly - _COORD_EPS
                        and v["bottom"] >= ly + _COORD_EPS)
            if (_ccc_end_ok(r0, xa, 1, through, strict_overspan)
                    and _ccc_end_ok(r1, xb, -1, through,
                                    strict_overspan)):
                return ly
    return None


def _lateral_candidates(vert, jog_lines, plate_box, ff_box, gap_tol):
    """Boundary elements spanning the datum interval: single strokes
    plus one-jog jointed chains. A chain's jog lies STRICTLY BETWEEN
    the datum boxes — a horizontal AT datum level is a closure line,
    never a step. Joints are established under RULING CCC (SEND-84).
    Each: {x_top, x_bot, jog_y}."""
    ccc_cache = {}
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
            ly = _ccc_joint(jog_lines, vert, lo, hi, gap_tol, y_near=jy,
                            _cache=ccc_cache)
            if ly is not None:
                chains.append({"x_top": xa, "x_bot": xb, "jog_y": ly,
                               "pt": True})
    # RULING CCC (SEND-84) — PROJECTION SHOULDERS. A spanning stroke
    # that does not terminate at the plate (a chimney rising past the
    # roof) joins the outline only through a DRAWN SHOULDER: a jog line
    # meeting the wall line and the projection member under the same
    # joint law. The chain carries the wall's x above the shoulder and
    # the projection's x below it. ONE true shoulder across two houses
    # — UNVALIDATED beyond n=1 (memory/register_send84.md).
    for w in [c for c in singles if c["pt"]]:
        for p in [c for c in singles if not c["pt"]]:
            lo, hi = sorted((w["x_top"], p["x_top"]))
            if hi - lo <= gap_tol:
                continue                      # one drawn corner, not a step
            ly = _ccc_joint(jog_lines, vert, lo, hi, gap_tol,
                            strict_overspan=True, _cache=ccc_cache)
            if ly is not None:
                chains.append({"x_top": w["x_top"], "x_bot": p["x_top"],
                               "jog_y": ly, "pt": True})
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
    # RULING CCC: joints are judged on the RAW kept horizontals (line-
    # weight merging only) — the gap_tol merge below is for closures.
    jog_lines = _joint_lines(horiz, plate_box[1], ff_box[0])
    # drawn continuity: rejoin strokes fragmented at intersections
    vert = _merge_collinear(vert, "v", gap_tol)
    horiz = _merge_collinear(horiz, "h", gap_tol)
    cands = _lateral_candidates(vert, jog_lines, plate_box, ff_box,
                                gap_tol)
    all_singles = [c for c in cands if c["jog_y"] is None]
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
    # ── SEND-89/94 — THE PARTITION: a chimney/chase is its own surface.
    # EDGE (the outline's own shoulder chain to a non-plate-terminated
    # projection member) → two surfaces; INTERRUPTING (full-height
    # non-pt members strictly inside the body, joined by a DRAWN CAP
    # above the plate) → three. Detection is drawn structure only — the
    # full-height discriminator (SEND-89 item 2) is the spanning-singles
    # set itself; no window/bay enters it on either house.
    nonpt_xs = [c["x_top"] for c in all_singles if not c.get("pt")]

    def _ink_top(x):
        tops = [v["top"] for v in vert
                if abs(((v["x0"] + v["x1"]) / 2.0) - x) <= _COORD_EPS
                and v["top"] < plate_box[0] - gap_tol]
        return min(tops) if tops else None

    body_lo = min(corner_singles) if len(corner_singles) >= 2 else min(xs)
    body_hi = max(corner_singles) if len(corner_singles) >= 2 else max(xs)
    chases = []
    for c in (left, right):
        if c["jog_y"] is None:
            continue
        if not any(abs(c["x_bot"] - nx) <= _COORD_EPS for nx in nonpt_xs):
            continue                 # a drawn step, not a projection
        ti = _ink_top(c["x_bot"])
        chases.append({"kind": "edge",
                       "x_wall": round(c["x_top"], 2),
                       "x_proj": round(c["x_bot"], 2),
                       "jog_y": round(c["jog_y"], 2),
                       "top_ink_y": None if ti is None else round(ti, 2)})
    # interrupting: cluster interior non-pt spanning members at
    # line-weight-scale, pair adjacent clusters through a drawn cap
    # whose ends land on riser tops of each cluster (a joint, not a
    # crossing — the eave/ridge lines end at the face boundary, never
    # on the chase members).
    interior = sorted(x for x in nonpt_xs
                      if body_lo + gap_tol < x < body_hi - gap_tol)
    clusters = []
    for x in interior:
        if clusters and x - clusters[-1][-1] <= gap_tol:
            clusters[-1].append(x)
        else:
            clusters.append([x])

    def _cap_between(cl_l, cl_r):
        caps_y = []
        for h in horiz:
            hy = (h["top"] + h["bottom"]) / 2.0
            if hy >= plate_box[0]:
                continue
            h0, h1 = min(h["x0"], h["x1"]), max(h["x0"], h["x1"])
            if not (any(abs(x - h0) <= gap_tol for x in cl_l)
                    and any(abs(x - h1) <= gap_tol for x in cl_r)):
                continue
            ends_on_tops = all(
                any(abs(((v["x0"] + v["x1"]) / 2.0) - he) <= gap_tol
                    and abs(v["top"] - hy) <= gap_tol
                    and v["bottom"] > hy + gap_tol for v in vert)
                for he in (h0, h1))
            if ends_on_tops:
                caps_y.append(hy)
        return min(caps_y) if caps_y else None      # topmost drawn cap

    for i in range(len(clusters) - 1):
        cap_y = _cap_between(clusters[i], clusters[i + 1])
        if cap_y is None:
            continue
        tis = [t for t in (_ink_top(x)
                           for x in clusters[i] + clusters[i + 1])
               if t is not None]
        chases.append({
            "kind": "interrupting",
            "x_inner": [round(max(clusters[i]), 2),
                        round(min(clusters[i + 1]), 2)],
            "x_outer": [round(min(clusters[i]), 2),
                        round(max(clusters[i + 1]), 2)],
            "cap_y": round(cap_y, 2),
            "top_ink_y": round(min(tis), 2) if tis else None})
    # RULING CCC (SEND-84) — an unresolvable projection SAYS SO: a
    # spanning stroke outside the resolved silhouette that no drawn
    # shoulder joins to a wall line is a REFUSED projection, disclosed
    # by x. Silhouette geometry alone cannot tell a chimney from a
    # course-end line (structural-identity bound, register_send82.md);
    # only a drawn shoulder distinguishes, and only where one exists.
    refusals = [
        {"x": round(d["x_top"], 2),
         "reason": (f"spanning stroke at x={d['x_top']:.2f}% carries no "
                    "drawn shoulder joining it to a wall line — "
                    "projection refused (RULING CCC)")}
        for d in all_singles
        if not d.get("pt")
        and (d["x_top"] < min(xs) - _COORD_EPS
             or d["x_top"] > max(xs) + _COORD_EPS)]
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
            # SEND-89/94 — partition surfaces: the body is WALL-ONLY
            # where a chase splits off; the chase never disappears.
            "body_x_span": [round(body_lo, 2), round(body_hi, 2)],
            "chases": chases or None,
            "y_top": round(y_top, 2), "y_bot": round(y_bot, 2),
            "n_spanning": len(cands), "n_vertices": len(pts),
            "projection_refusals": refusals or None,
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
