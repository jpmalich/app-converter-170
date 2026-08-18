"""SEND-30 (Howard sealed 2026-08-16) — OCR geometry instruments.

AXIS CLASS (Correction 1): raw w/h measures STRING LENGTH, not
orientation — upright text gets wider with every glyph while its height
stays fixed, so a 5-glyph and a 7-glyph upright string land at different
raw ratios. Normalize by glyph count: nr = (w/h) / glyphs. VERIFIED on
the full 21 dimension-like runs of Boni p6 plus the four key strings
BEFORE adoption: verticals land 0.058-0.087, horizontals 0.212-0.396 —
a 2.4x gap with zero overlap, and both 58'-0" rails move to HORIZONTAL
where they belong. The cuts sit INSIDE that observed gap (typography,
not tuning — no cut approaches 712, 725, 33'-0", 30'-2" or any zone
figure). INDETERMINATE stays first-class: a classifier that never says
"I cannot tell" is the coin flip again.

RAIL ENVELOPE (Correction 2): INTERIOR MEANS INSIDE ON BOTH AXES. A
side depth chain sits OUTSIDE the footprint on x while its y falls
between the top and bottom width rails — a y-only envelope would class
the very depths the anchor needs as INTERIOR and delete them. The
x-bounds come from the left/right depth rails, which are rotated
strings, so this test structurally depends on rotated coverage having
landed first (SEND-30 items 1+2). When the envelope cannot be
established the answer is INDETERMINATE — never default-to-exterior,
never default-to-interior.

POSITIONAL RULE PROBE (item 5): REPORT ONLY. It never binds the anchor.

RULING HH (SEND-31): BARE FORM, GATED ON POSITION NOT VALUE. The true
30'-2" transcribed as bare "30-2" (foot and inch marks lost) and the
text filter rightly refuses digits-hyphen-digits globally (it swallows
dates). The bare form is admitted ONLY when the positional substrate
already supports it: axis class VERTICAL or HORIZONTAL (never
INDETERMINATE), EXTERIOR by the 2D envelope, sitting on a dimension
chain (aligned with a fully-marked dimension of the same axis within
one box-width — geometry, not a picked number), AND inch component
<= 11 (feet-and-inches notation cannot carry 12 or more inches — a
bound from the notation itself). A date is never a rotated vertical
string on an exterior dimension rail. POSITIONS DISAMBIGUATE, VALUES
DO NOT. No envelope -> nothing admitted, never a default.

RULING II (SEND-31): SCALE NOTES OUT OF RAIL CANDIDACY. A rail
candidate contains NO ALPHABETIC CHARACTERS beyond the foot and inch
marks. SCALE:3/16"=1'-0" fails on "SCALE" alone. Deliberately NOT a
blocklist of note types — one structural property generalizing to
every note without naming any.
"""
from __future__ import annotations

import re

VERTICAL = "VERTICAL"
HORIZONTAL = "HORIZONTAL"
INDETERMINATE = "INDETERMINATE"
INTERIOR = "INTERIOR"
EXTERIOR = "EXTERIOR"

# RULING UU (SEND-38): the INDETERMINATE band IS the observed gap on
# MERGED data (Boni p6 merged: vertical max 0.1143, horizontal min
# 0.212). Set to the boundaries themselves — not chosen, observed.
AXIS_VERTICAL_MAX = 0.1143
AXIS_HORIZONTAL_MIN = 0.212

# RULING VV (SEND-38): foot and inch marks normalize by UNICODE
# CONFUSABLE CLASS — not by appending U+2032 to a list. Third
# appearance of the glyph family ends it; a list invites a fourth.
_FOOT_CONFUSABLES = "\u2018\u2019\u0060\u00b4\u2032"   # ‘ ’ ` ´ ′
_INCH_CONFUSABLES = "\u201c\u201d\u2033\u02dd"          # “ ” ″ ˝
_MARK_TRANS = str.maketrans(
    {c: "'" for c in _FOOT_CONFUSABLES} | {c: '"' for c in _INCH_CONFUSABLES})


def normalize_marks(s) -> str:
    return str(s or "").translate(_MARK_TRANS)


# Dimension-like: a foot-mark chain (3'-10, 15'-0*) OR the glyph-noise
# form OCR returns for the big rails (58-0°, 33-11%) where the foot mark
# was eaten but an inch/noise tail survived.
_DIM_RE = re.compile(
    r"\d+\s*['\u2019`]\s*-?\s*\d+"
    r"|\d+\s*-\s*\d+\s*[\"\u201d%\u00b0*]"
)


def glyph_count(raw) -> int:
    return len(re.sub(r"\s", "", str(raw or "")))


_ALPHA_RE = re.compile(r"[A-Za-z]")

# RULING HH: the bare form — digits-hyphen-digits and NOTHING else.
_BARE_FORM_RE = re.compile(r"^\s*(\d{1,3})\s*-\s*(\d{1,2})\s*$")


def parse_bare_form(raw):
    """(feet, inches) for a bare digits-hyphen-digits string, else None.
    A two-hyphen date (03-26-26) never parses."""
    m = _BARE_FORM_RE.match(str(raw or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def is_rail_candidate(raw) -> bool:
    """RULING II: a rail candidate is dimension-like AND carries no
    alphabetic characters beyond the foot and inch marks.
    RULING JJ (SEND-32): AND carries EXACTLY ONE dimension token — a
    size pair (2-11½ × 3-11½) is an annotation, not a chain dimension.
    Same shape as II: one structural property, no catalog of note
    forms or glyphs."""
    s = str(raw or "")
    return (is_dimension_like(s) and not _ALPHA_RE.search(s)
            and dimension_token_count(s) == 1)


def dimension_token_count(raw) -> int:
    return len(_DIM_RE.findall(normalize_marks(raw)))


# RULING KK (SEND-32, Howard ruled): the p4/p6 2" difference is a
# REFERENCE-PLANE difference, not a disagreement. Foundation plans
# dimension to the outside of the FOUNDATION WALL; floor plans to the
# outside of FRAMING/SHEATHING. Siding wraps the framing, so the
# first-floor dimension governs siding; the foundation figure stays
# VISIBLE ALONGSIDE — not hidden, not discarded, not a conflict.
# HOW THE CODE TELLS A PLANE DIFFERENCE FROM A GENUINE CONTRADICTION
# (the whole ruling): readings are grouped BY PLANE. Two readings on
# the SAME plane that disagree are a GENUINE CONTRADICTION and report
# as one. Readings on DIFFERENT planes that differ are two planes,
# both correct — the material names which governs. When a plane cannot
# be attributed, the two cases CANNOT be told apart and the verdict is
# INDETERMINATE — reported unresolved, never defaulted. There is no
# magnitude threshold anywhere: "prefer the later sheet" and "small
# difference = plane offset" are the heuristics this rule exists to
# avoid.
PLANE_FOUNDATION = "foundation"
PLANE_FRAMING = "framing"
_MATERIAL_GOVERNING_PLANE = {"siding": PLANE_FRAMING}


def plane_for_sheet_title(title):
    """Plane attribution rides on the sheet's OWN title-block text —
    'FOUNDATION' names the foundation plane, a floor plan dimensions
    framing. Unrecognized → None (plane unknown, never guessed)."""
    t = str(title or "").upper()
    if "FOUNDATION" in t:
        return PLANE_FOUNDATION
    if "FLOOR PLAN" in t:
        return PLANE_FRAMING
    return None


def reference_plane_verdict(readings: list, material: str = "siding") -> dict:
    """RULING KK. readings: [{"value", "page", "plane"}]. Returns
    status ∈ CONTRADICTION / REFERENCE_PLANES / AGREE / INDETERMINATE
    with the governing reading for the material and the other plane's
    reading visible alongside."""
    def _digits(v):
        return re.sub(r"\D", "", str(v or ""))
    readings = [r for r in (readings or []) if isinstance(r, dict)]
    known = [r for r in readings
             if r.get("plane") in (PLANE_FOUNDATION, PLANE_FRAMING)
             and r.get("value")]
    unknown = [r for r in readings if r not in known]
    out = {"material": material, "status": None, "governs": None,
           "alongside": [], "why": None, "readings": readings}
    by_plane: dict = {}
    for r in known:
        by_plane.setdefault(r["plane"], []).append(r)
    # SAME-plane disagreement = a genuine cross-sheet conflict. It must
    # still report as one — this check is what keeps KK from being
    # "prefer the later sheet" wearing a ruling's name.
    for plane, rs in by_plane.items():
        if len({_digits(r["value"]) for r in rs}) > 1:
            out["status"] = "CONTRADICTION"
            out["why"] = (f"two readings on the SAME reference plane "
                          f"({plane}) disagree — a genuine cross-sheet "
                          f"conflict, not a plane difference")
            return out
    if unknown or not known:
        out["status"] = INDETERMINATE
        out["why"] = ("reference plane unknown for at least one reading — "
                      "plane difference and contradiction cannot be told "
                      "apart; reported unresolved, no default")
        return out
    gov_plane = _MATERIAL_GOVERNING_PLANE.get(str(material or "").lower())
    if gov_plane is None:
        out["status"] = INDETERMINATE
        out["why"] = (f"no governing plane is ruled for material "
                      f"{material!r} — no default")
        return out
    if gov_plane not in by_plane:
        out["status"] = INDETERMINATE
        out["why"] = (f"the governing plane ({gov_plane}) was not read — "
                      f"the other plane never substitutes")
        return out
    gov = by_plane[gov_plane][0]
    out["governs"] = {"plane": gov_plane, "value": gov["value"],
                      "page": gov.get("page"),
                      "why": "siding wraps the framing — the first-floor "
                             "dimension applies to the material"}
    out["alongside"] = [
        {"plane": p, "value": rs[0]["value"], "page": rs[0].get("page"),
         "note": "the other reference plane — visible alongside, "
                 "not a conflict"}
        for p, rs in by_plane.items() if p != gov_plane]
    vals = {_digits(rs[0]["value"]) for rs in by_plane.values()}
    out["status"] = "AGREE" if len(vals) <= 1 else "REFERENCE_PLANES"
    return out


def is_dimension_like(raw) -> bool:
    return bool(_DIM_RE.search(normalize_marks(raw)))


def axis_class(loc: dict, glyphs: int) -> str:
    """Glyph-normalized orientation of a percent box. INDETERMINATE is a
    real answer and must stay reachable."""
    try:
        w = float(loc.get("w_pct") or 0)
        h = float(loc.get("h_pct") or 0)
    except (TypeError, ValueError, AttributeError):
        return INDETERMINATE
    if w <= 0 or h <= 0 or glyphs <= 0:
        return INDETERMINATE
    nr = (w / h) / glyphs
    if nr <= AXIS_VERTICAL_MAX:
        return VERTICAL
    if nr >= AXIS_HORIZONTAL_MIN:
        return HORIZONTAL
    return INDETERMINATE


def _cx(r: dict) -> float:
    return float(r["loc"]["x_pct"]) + float(r["loc"]["w_pct"]) / 2


def _cy(r: dict) -> float:
    return float(r["loc"]["y_pct"]) + float(r["loc"]["h_pct"]) / 2


# RULING MM (SEND-36): POSITION MERGE is the FIRST operation on the
# store. Three passes reading the same pixels produce up to three
# "readings" of ONE physical string ('30-0*', '0-00', '0-.00' at one
# spot on Letrick p5); treating them as independent strings triplicated
# every census and let a fragment outrun its own true reading (p8 LEFT,
# confirmed error). Readings whose boxes overlap are ONE string —
# same-location test is parameter-free: either center inside the other's
# box. Prefer the most completely parsed reading (fully-marked > bare
# form > other; glyph count breaks ties). TWO COMPLETE READINGS
# DISAGREEING IN VALUE (first two numeric groups) is INDETERMINATE —
# the merged string is marked conflicted and never enters a dimension
# path. A chain mate must be a DIFFERENT physical string, established
# AFTER merge.
_NUM_RE = re.compile(r"\d+")


def _first_two_groups(raw):
    g = _NUM_RE.findall(str(raw or ""))
    return tuple(int(x) for x in g[:2]) if g else None


def _same_location(a: dict, b: dict) -> bool:
    la, lb = a["loc"], b["loc"]
    def _inside(cx, cy, l):
        return (l["x_pct"] <= cx <= l["x_pct"] + l["w_pct"]
                and l["y_pct"] <= cy <= l["y_pct"] + l["h_pct"])
    return (_inside(_cx(a), _cy(a), lb) or _inside(_cx(b), _cy(b), la))


def _parse_rank(raw):
    """Completeness of a reading: fully-marked beats bare form beats
    anything else; glyph count breaks ties."""
    s = str(raw or "")
    if is_dimension_like(s):
        tier = 2
    elif parse_bare_form(s):
        tier = 1
    else:
        tier = 0
    return (tier, glyph_count(s))


def merge_positions(runs: list) -> list:
    """RULING MM. Collapse same-location readings into one string each.
    Idempotent on already-merged data (the survivor keeps its own box)."""
    items = [r for r in (runs or []) if isinstance(r, dict) and r.get("loc")]
    n = len(items)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if _same_location(items[i], items[j]):
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pj] = pi
    groups: dict = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(items[i])
    merged = []
    for members in groups.values():
        members.sort(key=lambda r: _parse_rank(r.get("raw")), reverse=True)
        best = dict(members[0])
        best["merge_count"] = len(members)
        best["merged_srcs"] = sorted({m.get("src") or "?" for m in members})
        best["merged_raws"] = [m.get("raw") for m in members]
        complete = [m for m in members if is_dimension_like(m.get("raw"))]
        vals = {_first_two_groups(m.get("raw")) for m in complete}
        best["merge_conflict"] = len(vals) > 1
        merged.append(best)
    return merged


def _is_clean_dim(r: dict) -> bool:
    return (is_dimension_like(r.get("raw"))
            and not r.get("merge_conflict"))


def rail_envelope(runs: list, extra_dim_runs: list | None = None) -> dict:
    """Footprint envelope from the outermost dimension rails: y-bounds
    from the top/bottom HORIZONTAL width rails, x-bounds from the
    left/right VERTICAL depth rails. RULING II: rail candidates carry no
    alphabetic characters (a SCALE note is never a rail). INDETERMINATE
    (with a named reason) when it cannot be established — never a
    default."""
    out = {"status": INDETERMINATE, "reason": None, "x_lo": None,
           "x_hi": None, "y_lo": None, "y_hi": None, "rails": None}
    runs = merge_positions(runs)  # RULING MM: merge is the first operation
    dims = [r for r in runs
            if r.get("loc") and is_rail_candidate(r.get("raw"))
            and not r.get("merge_conflict")]
    dims += [r for r in (extra_dim_runs or [])
             if isinstance(r, dict) and r.get("loc")]
    horiz = [r for r in dims if r.get("axis") == HORIZONTAL]
    vert = [r for r in dims if r.get("axis") == VERTICAL]
    if len(horiz) < 2:
        out["reason"] = "fewer than two horizontal dimension rails"
        return out
    if len(vert) < 2:
        out["reason"] = "fewer than two vertical dimension rails"
        return out
    top = min(horiz, key=_cy)
    bottom = max(horiz, key=_cy)
    left = min(vert, key=_cx)
    right = max(vert, key=_cx)
    y_lo = float(top["loc"]["y_pct"]) + float(top["loc"]["h_pct"])
    y_hi = float(bottom["loc"]["y_pct"])
    x_lo = float(left["loc"]["x_pct"]) + float(left["loc"]["w_pct"])
    x_hi = float(right["loc"]["x_pct"])
    if not (y_lo < y_hi and x_lo < x_hi):
        out["reason"] = "rails cross — envelope cannot be established"
        return out
    out.update({"status": "ESTABLISHED", "x_lo": x_lo, "x_hi": x_hi,
                "y_lo": y_lo, "y_hi": y_hi,
                "rails": {"top": top["raw"], "bottom": bottom["raw"],
                          "left": left["raw"], "right": right["raw"]},
                "_rail_runs": {"top": top, "bottom": bottom,
                               "left": left, "right": right}})
    return out


def interior_exterior(run: dict, envelope: dict) -> str:
    """2D test — INTERIOR means inside on BOTH axes. Envelope not
    established → INDETERMINATE, never a default either way."""
    if not isinstance(envelope, dict) or envelope.get("status") != "ESTABLISHED":
        return INDETERMINATE
    cx, cy = _cx(run), _cy(run)
    inside_x = envelope["x_lo"] < cx < envelope["x_hi"]
    inside_y = envelope["y_lo"] < cy < envelope["y_hi"]
    return INTERIOR if (inside_x and inside_y) else EXTERIOR


def _chain_aligned(run: dict, marked_dims: list):
    """RULING HH chain gate: the bare form must sit on a dimension chain
    — aligned with a fully-marked dimension of the SAME axis within one
    box-width (the tolerance comes from the boxes themselves)."""
    axis = run.get("axis")
    for m in marked_dims:
        if m is run or m.get("axis") != axis:
            continue
        if axis == VERTICAL:
            if abs(_cx(run) - _cx(m)) <= max(run["loc"]["w_pct"],
                                             m["loc"]["w_pct"]):
                return m
        else:
            if abs(_cy(run) - _cy(m)) <= max(run["loc"]["h_pct"],
                                             m["loc"]["h_pct"]):
                return m
    return None


def gated_bare_form_admissions(runs: list) -> dict:
    """RULING HH — admit a bare digits-hyphen-digits string ONLY when
    position already supports it: axis VERTICAL/HORIZONTAL, EXTERIOR by
    the marked-dims envelope, chain-aligned with a marked dimension of
    the same axis, and inch component <= 11. RULING NN: zero total
    length is refused. RULING MM runs first — a fragment overlapping its
    own true reading is the SAME string, never a chain mate. Envelope
    not established → NOTHING admitted (never a default)."""
    runs = merge_positions(runs)
    marked = [r for r in (runs or [])
              if isinstance(r, dict) and r.get("loc")
              and _is_clean_dim(r)]
    env = rail_envelope(runs)
    out = {"envelope_status": env["status"], "admitted": []}
    if env["status"] != "ESTABLISHED":
        return out
    for r in (runs or []):
        if not isinstance(r, dict) or not r.get("loc"):
            continue
        if is_dimension_like(r.get("raw")):
            continue
        pf = parse_bare_form(r.get("raw"))
        if not pf:
            continue
        feet, inches = pf
        if inches > 11:
            continue
        # RULING NN (SEND-36): zero TOTAL LENGTH is not a dimension.
        # A 6" dimension (0-6) is real; 0-0 dimensions nothing.
        if feet * 12 + inches == 0:
            continue
        if r.get("axis") not in (VERTICAL, HORIZONTAL):
            continue
        if interior_exterior(r, env) != EXTERIOR:
            continue
        mate = _chain_aligned(r, marked)
        if mate is None:
            continue
        out["admitted"].append({"run": r, "feet": feet, "inches": inches,
                                "chain_mate": mate["raw"]})
    return out


def positional_rule_probe(runs: list, gated_bare: bool = True) -> dict:
    """SEND-30 item 5 — the rule, applied and REPORTED, never bound:
    the outermost VERTICAL EXTERIOR dimension on the same side of the
    footprint as the garage label. Reports what it returns, what it
    nearly returned, and what classed INDETERMINATE. RULING HH: gated
    bare forms are admitted (and reported) before the rule applies.
    RULING MM: position merge is the first operation on the store."""
    runs = merge_positions(runs)
    adm = (gated_bare_form_admissions(runs)
           if gated_bare else {"admitted": []})
    admitted_runs = [a["run"] for a in adm["admitted"]]
    env = rail_envelope(runs or [], extra_dim_runs=admitted_runs)
    report = {"rule": "outermost VERTICAL EXTERIOR dimension on the same "
                      "side of the footprint as the garage label",
              "envelope": env, "labels": [], "sides": {}, "binds": False,
              "gated_bare_admitted": [
                  {"raw": a["run"]["raw"], "loc": a["run"]["loc"],
                   "src": a["run"].get("src"), "feet": a["feet"],
                   "inches": a["inches"], "chain_mate": a["chain_mate"]}
                  for a in adm["admitted"]],
              "indeterminate_axis": [
                  {"raw": r["raw"], "loc": r["loc"]}
                  for r in (runs or [])
                  if isinstance(r, dict) and r.get("loc")
                  and is_dimension_like(r.get("raw"))
                  and r.get("axis") == INDETERMINATE]}
    if env["status"] != "ESTABLISHED":
        report["result"] = INDETERMINATE
        report["reason"] = env.get("reason")
        return report
    mid_x = (env["x_lo"] + env["x_hi"]) / 2
    for lb in (runs or []):
        if isinstance(lb, dict) and lb.get("loc") \
                and "GARAGE" in str(lb.get("norm") or ""):
            report["labels"].append(
                {"raw": lb.get("raw"), "loc": lb.get("loc"),
                 "side": "right" if _cx(lb) >= mid_x else "left"})
    vert_dims = [r for r in (runs or [])
                 if isinstance(r, dict) and r.get("loc")
                 and _is_clean_dim(r)
                 and r.get("axis") == VERTICAL]
    vert_dims += [r for r in admitted_runs if r.get("axis") == VERTICAL]
    for side in ("left", "right"):
        side_dims = [r for r in vert_dims
                     if (_cx(r) >= mid_x) == (side == "right")]
        ext = [r for r in side_dims
               if interior_exterior(r, env) == EXTERIOR]
        # RULING WW (SEND-38): a depth candidate must LIE ON THE SIDE'S
        # ESTABLISHED RAIL LINE — vertical and exterior is not enough.
        # This excludes a mid-sheet projection (the chimney) structurally
        # rather than by position luck.
        rail_run = (env.get("_rail_runs") or {}).get(side)
        if rail_run is not None:
            cands = [r for r in ext
                     if abs(_cx(r) - _cx(rail_run))
                     <= max(r["loc"]["w_pct"], rail_run["loc"]["w_pct"])]
            off_rail = [r for r in ext if r not in cands]
        else:
            cands, off_rail = list(ext), []
        cands.sort(key=lambda r: abs(_cx(r) - mid_x), reverse=True)
        # An EXACT positional tie between distinct values for the
        # outermost slot is INDETERMINATE — named, never a silent
        # list-order coin flip. (Boni p4 LEFT: merge collapsed the 0.08
        # photo finish into this tie — the margin was cross-pass box
        # noise, not signal. Segment-vs-total still needs its ruling.)
        tie = None
        if len(cands) >= 2:
            d0 = abs(_cx(cands[0]) - mid_x)
            tied = [r for r in cands if abs(_cx(r) - mid_x) == d0]
            vals = {_first_two_groups(normalize_marks(r["raw"]))
                    for r in tied}
            if len(tied) > 1 and len(vals) > 1:
                tie = [r["raw"] for r in tied]
        report["sides"][side] = {
            "chosen": (None if tie else
                       ({"raw": cands[0]["raw"], "loc": cands[0]["loc"]}
                        if cands else None)),
            "tie": tie,
            "contenders": [{"raw": r["raw"], "loc": r["loc"],
                            "dist_from_mid_pct": round(abs(_cx(r) - mid_x), 2)}
                           for r in cands],
            # WW exclusions stay VISIBLE, never silent.
            "excluded_off_rail": [{"raw": r["raw"], "loc": r["loc"]}
                                  for r in off_rail],
            # Visible, not silent: vertical dims on this side the 2D test
            # classed INTERIOR — what the rule NEARLY returned.
            "excluded_interior": [{"raw": r["raw"], "loc": r["loc"]}
                                  for r in side_dims
                                  if r not in cands and r not in off_rail],
        }
    return report


# RULING LL (SEND-36): SUM CLOSURE, computed against MERGED strings —
# a chain holding three readings of one member cannot be summed. A
# chain is the set of dimension strings aligned on one line (same
# column for vertical, same row for horizontal, within one box-width —
# the same geometry as the HH chain gate). The largest member is the
# TOTAL CANDIDATE; the chain CLOSES when the rest sum to it exactly
# (in inches, first-two-numeric-groups parse). Fractions the OCR
# cannot read make honest residuals — they are REPORTED, never
# tolerated away with a picked threshold.

def _member_inches(raw):
    g = _first_two_groups(raw)
    if not g:
        return None
    feet = g[0]
    inches = g[1] if len(g) > 1 else 0
    if inches > 11:
        return None
    return feet * 12 + inches


def chain_clusters(runs: list) -> list:
    """Merged dimension strings grouped into chains by axis+alignment."""
    runs = merge_positions(runs)
    out = []
    for axis, coord in ((VERTICAL, _cx), (HORIZONTAL, _cy)):
        dims = [r for r in runs if r.get("loc") and _is_clean_dim(r)
                and r.get("axis") == axis]
        dims.sort(key=coord)
        chain: list = []
        for r in dims:
            if chain:
                prev = chain[-1]
                span_key = "w_pct" if axis == VERTICAL else "h_pct"
                tol = max(prev["loc"][span_key], r["loc"][span_key])
                if abs(coord(r) - coord(prev)) > tol:
                    out.append({"axis": axis, "members": chain})
                    chain = []
            chain.append(r)
        if chain:
            out.append({"axis": axis, "members": chain})
    return [c for c in out if len(c["members"]) >= 2]


def chain_sum_closure(runs: list) -> list:
    """RULING LL report: per chain — members, total candidate, segment
    sum, and CLOSES / FAILS(residual) / UNPARSEABLE."""
    report = []
    for c in chain_clusters(runs):
        vals = [(r["raw"], _member_inches(r["raw"])) for r in c["members"]]
        entry = {"axis": c["axis"],
                 "members": [{"raw": r["raw"], "loc": r["loc"]}
                             for r in c["members"]],
                 "values_in": vals}
        if any(v is None for _, v in vals):
            entry["status"] = "UNPARSEABLE"
            entry["why"] = "a member's value could not be parsed"
        else:
            total = max(v for _, v in vals)
            rest = sum(v for _, v in vals) - total
            entry["total_candidate_in"] = total
            entry["segment_sum_in"] = rest
            if rest == total:
                entry["status"] = "CLOSES"
            else:
                entry["status"] = "FAILS"
                entry["residual_in"] = rest - total
        report.append(entry)
    return report


# RULING XX (SEND-38, ADOPTED — Howard's words): "Equal left/right
# depths make attribution immaterial. It never overrides closure.
# Unequal depths still require the anchor or a refusal. This does not
# close the 'different depths + no garage' case — that stays open for
# a later ruling."
XX_CLOSURE_PIN = ("EQUALITY NEVER OVERRIDES CLOSURE — EE still blocks an "
                  "unclosable footprint, and this verdict carries NO "
                  "derivability claim of any kind. It answers attribution "
                  "and nothing else.")

# NAMED OPEN ITEM (registered, not designed): DIFFERENT DEPTHS + NO
# GARAGE refuses today and that is correct until ruled otherwise.
# Observation for the register only: the anchor is not garage-specific
# in MECHANISM ("a labelled interior volume whose outboard wall lands
# on one side elevation") — the garage is one reliably-identifiable
# instance.
XX_NAMED_OPEN = "different depths + no garage: REFUSES — open for a later ruling"


def attribution_verdict(runs: list) -> dict:
    """RULING XX. The side pair is GEOMETRIC (envelope mid-line), no
    attribution presupposed. Equality tested on parsed feet+inches
    AFTER merge. Returns IMMATERIAL / MATERIAL / NO_PAIR /
    INDETERMINATE — and never a quantity."""
    probe = positional_rule_probe(runs)
    out = {"closure_pin": XX_CLOSURE_PIN, "named_open": XX_NAMED_OPEN,
           "probe_envelope": probe["envelope"]["status"], "pair": None,
           "status": None, "why": None, "depth": None}
    if probe["envelope"]["status"] != "ESTABLISHED":
        out["status"] = INDETERMINATE
        out["why"] = probe["envelope"].get("reason")
        return out
    pair = {}
    for side in ("left", "right"):
        s = probe["sides"][side]
        if s.get("tie"):
            out["status"] = INDETERMINATE
            out["why"] = (f"{side} winner is an exact positional tie "
                          f"{s['tie']} — the outermost rule cannot order "
                          f"them; segment-vs-total needs its ruling")
            return out
        ch = s["chosen"]
        pair[side] = None if not ch else {
            "raw": ch["raw"], "loc": ch["loc"],
            "parsed": _first_two_groups(normalize_marks(ch["raw"]))}
    out["pair"] = pair
    if not pair["left"] or not pair["right"]:
        out["status"] = "NO_PAIR"
        out["why"] = "no candidate on a side — refusal stands"
        return out
    lv, rv = pair["left"]["parsed"], pair["right"]["parsed"]
    if lv is None or rv is None:
        out["status"] = INDETERMINATE
        out["why"] = "a winner's value could not be parsed"
        return out
    if lv == rv:
        out["status"] = "IMMATERIAL"
        out["why"] = ("equal side depths — crossing them is harmless; "
                      "both faces may derive WITHOUT an anchor, subject to "
                      "every other gate (closure included)")
        out["depth"] = {"feet": lv[0],
                        "inches": lv[1] if len(lv) > 1 else 0}
    else:
        out["status"] = "MATERIAL"
        out["why"] = ("unequal side depths — attribution requires the "
                      "anchor, or the faces refuse")
    return out


def _fraction_uncertain(raw) -> bool:
    s = normalize_marks(raw)
    return bool(re.search(r"[%/\u00bc\u00bd\u00be]", s))


def tt_closure(runs: list) -> list:
    """RULING TT (SEND-37): corrected LL — segments on the INNER line
    sum to the total on the NEXT RAIL OUT. Fraction loss is DECLARED
    per member, never a tolerance. REPORTS, NEVER GATES."""
    runs = merge_positions(runs)
    report = []
    for axis, coord, span in ((VERTICAL, _cx, "w_pct"),
                              (HORIZONTAL, _cy, "h_pct")):
        dims = [r for r in runs if r.get("loc") and _is_clean_dim(r)
                and r.get("axis") == axis]
        if len(dims) < 2:
            continue
        dims.sort(key=coord)
        lines, cur = [], []
        for r in dims:
            if cur and abs(coord(r) - coord(cur[-1])) > max(
                    cur[-1]["loc"][span], r["loc"][span]):
                lines.append(cur)
                cur = []
            cur.append(r)
        if cur:
            lines.append(cur)
        if len(lines) < 2:
            continue
        mid = (coord(lines[0][0]) + coord(lines[-1][-1])) / 2
        halves = {"low": [l for l in lines if coord(l[0]) < mid],
                  "high": [l for l in lines if coord(l[0]) >= mid]}
        for half, hl in halves.items():
            # inner -> outer: outward is AWAY from mid.
            hl = sorted(hl, key=lambda l: abs(coord(l[0]) - mid))
            for i in range(len(hl) - 1):
                inner, outer = hl[i], hl[i + 1]
                if len(outer) != 1:
                    continue  # the next rail out is not a single total
                total = _member_inches(outer[0]["raw"])
                segs = [(_member_inches(r["raw"]), r["raw"]) for r in inner]
                entry = {"axis": axis, "half": half,
                         "total_raw": outer[0]["raw"],
                         "segments": [s for _, s in segs],
                         "declared_fraction_uncertainty": sorted(
                             {r["raw"] for r in inner + outer
                              if _fraction_uncertain(r["raw"])})}
                if total is None or any(v is None for v, _ in segs):
                    entry["status"] = "UNPARSEABLE"
                else:
                    ssum = sum(v for v, _ in segs)
                    entry.update({"total_in": total, "segment_sum_in": ssum,
                                  "status": ("CLOSES" if ssum == total
                                             else "FAILS"),
                                  "residual_in": ssum - total})
                report.append(entry)
    return report


# THE REGISTER (SEND-44). Ruled out stays ruled out; named opens stay
# visible so they never quietly become assumptions.
RULINGS_REGISTER = {
    "ruled_out": [
        "multi-structure support inside one estimate — detached garage / "
        "outbuilding is its OWN estimate (Howard, SEND-44). Do not build, "
        "do not design.",
    ],
    "named_open": [
        "segment-vs-total on one line (blocking Boni p4 LEFT)",
        "different depths + no garage (refuses today — correct)",
        "room-label precondition is the ONLY thing excluding joist sheets",
        "two footprints drawn on one sheet (separate estimates keep "
        "takeoffs apart, not drawings apart) — report-only, no build",
        "elevation segment x-extents (SEND-46: DP-2 and DP-3 are ONE "
        "problem — two rails at different x on the same gap is a face "
        "that is not a single column, not a value conflict; refuse both, "
        "no tiebreak, until segment x-extents on the elevation exist)",
        "the joist band where no overall rail closes it (SEND-46 DP-5: "
        "refuse; do not invent a convention for the joist band)",
    ],
    # SEND-46: registered findings and sealed field rulings.
    "findings": [
        "CENSUS FINDING (SEND-46, qualifies every Boni accuracy claim "
        "from SEND-19 forward): Boni's model height 20.0 ft is "
        "UNRECONSTRUCTABLE from its own cited evidence — 9'-11\" + "
        "8'-1 1/2\" = 18.04 ft, and the 8'-1 1/2\" string was NEVER "
        "LOCATED on any sheet (the sheets print 8'-1 1/8\", a ceiling "
        "note). Letrick's model fans ONE string (9'-11 1/8\", p1) "
        "across all four faces including two faces that live on p2. "
        "Model heights are DEMOTED TO HYPOTHESIS: a model height may "
        "be shown as an unverified hypothesis; it may NEVER feed a "
        "quantity. Height derives from each face's own elevation "
        "drawing or the face refuses.",
    ],
    "sealed": [
        "DP-1 (SEND-46, Howard field ruling): siding band = FIRST "
        "FLOOR (subfloor line) up to plate/soffit — the band the "
        "elevations actually dimension. A face that establishes this "
        "band is DERIVED. The foundation → first-floor / rim-joist "
        "strip is BELOW the siding measurement and does not need "
        "resolving for height.",
        "DP-4 (SEND-46): a walkout footer is a foundation reference, "
        "not a grade line — it may only create SUSPICION of STEP, "
        "never establish the extent of a siding step.",
        "DP-5 (SEND-46): the joist band is SIDED — zero-for-siding is "
        "incorrect. Close by subtraction only: overall vertical rail "
        "minus the sum of bound sub-gaps, strict closure, residual 0 "
        "required when all gaps are bound. If no overall rail exists, "
        "REFUSE and leave the band a named open.",
    ],
}
