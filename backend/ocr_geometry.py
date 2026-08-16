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

# Cuts pinned INSIDE the observed separation gap (max vertical 0.087,
# min horizontal 0.212 on the verified set).
AXIS_VERTICAL_MAX = 0.12
AXIS_HORIZONTAL_MIN = 0.18

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
    return len(_DIM_RE.findall(str(raw or "")))


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
    return bool(_DIM_RE.search(str(raw or "")))


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


def rail_envelope(runs: list, extra_dim_runs: list | None = None) -> dict:
    """Footprint envelope from the outermost dimension rails: y-bounds
    from the top/bottom HORIZONTAL width rails, x-bounds from the
    left/right VERTICAL depth rails. RULING II: rail candidates carry no
    alphabetic characters (a SCALE note is never a rail). INDETERMINATE
    (with a named reason) when it cannot be established — never a
    default."""
    out = {"status": INDETERMINATE, "reason": None, "x_lo": None,
           "x_hi": None, "y_lo": None, "y_hi": None, "rails": None}
    dims = [r for r in (runs or [])
            if isinstance(r, dict) and r.get("loc")
            and is_rail_candidate(r.get("raw"))]
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
                          "left": left["raw"], "right": right["raw"]}})
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
    the same axis, and inch component <= 11. Envelope not established →
    NOTHING admitted (never a default)."""
    marked = [r for r in (runs or [])
              if isinstance(r, dict) and r.get("loc")
              and is_dimension_like(r.get("raw"))]
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
    bare forms are admitted (and reported) before the rule applies."""
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
                 and is_dimension_like(r.get("raw"))
                 and r.get("axis") == VERTICAL]
    vert_dims += [r for r in admitted_runs if r.get("axis") == VERTICAL]
    for side in ("left", "right"):
        side_dims = [r for r in vert_dims
                     if (_cx(r) >= mid_x) == (side == "right")]
        cands = [r for r in side_dims
                 if interior_exterior(r, env) == EXTERIOR]
        cands.sort(key=lambda r: abs(_cx(r) - mid_x), reverse=True)
        report["sides"][side] = {
            "chosen": ({"raw": cands[0]["raw"], "loc": cands[0]["loc"]}
                       if cands else None),
            "contenders": [{"raw": r["raw"], "loc": r["loc"],
                            "dist_from_mid_pct": round(abs(_cx(r) - mid_x), 2)}
                           for r in cands],
            # Visible, not silent: vertical dims on this side the 2D test
            # classed INTERIOR — what the rule NEARLY returned.
            "excluded_interior": [{"raw": r["raw"], "loc": r["loc"]}
                                  for r in side_dims if r not in cands],
        }
    return report
