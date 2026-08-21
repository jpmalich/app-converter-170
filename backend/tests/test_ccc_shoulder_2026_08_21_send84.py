"""SEND-84 — RULING CCC wired (option b as a MINIMUM).

A joint line must span at least the inner-to-inner gap of the members
it joins; a shortfall must terminate ON the member's named inner twin
(through-going vertical at line-weight, nothing between it and the
boundary stroke). Overspill stays within the existing joint law.
Guards: endpoint naming no reference, member not double-drawn at the
shortfall, member carrying 3+ strokes → no joint, no snapping.
Synthetic geometry only — no job figures, nothing tunes to any sealed
width."""
from linework_read import wall_outline_from_segments

# datum boxes: plate (20,21), floor (60,61) → gap_tol = 1.0
PLATE, FLOOR = (20.0, 21.0), (60.0, 61.0)
BAND = (0.0, 100.0)


def _v(x, top, bottom):
    return {"x0": x, "x1": x, "top": top, "bottom": bottom}


def _h(x0, x1, y):
    return {"x0": x0, "x1": x1, "top": y, "bottom": y}


def _base(right_wall=50.0):
    """Two plate-terminated wall lines + drawn closures."""
    return [
        _v(10.0, 20.2, 61.0), _v(right_wall, 20.2, 61.0),
        _h(9.0, 60.0, 20.5),          # plate closure (generous)
        _h(9.0, 60.0, 60.5),          # floor closure (generous)
    ]


def test_true_shoulder_joins_projection_on_its_own_ink():
    """A dropped spanning stroke (chimney, rises past the plate) joins
    via a drawn shoulder whose ink reaches the wall line and terminates
    on the projection member's inner twin — 6 vertices, projection on
    the right edge, boundary carried by the OUTER stroke."""
    segs = _base() + [
        _v(56.0, 15.0, 61.0),         # projection inner twin (drop)
        _v(58.0, 15.0, 61.0),         # projection outer stroke (drop)
        _h(50.0, 56.0, 40.0),         # the shoulder: wall -> inner twin
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 58.0]
    assert r["n_vertices"] == 6
    # jog carried at the drawn joint line's own y
    ys = {round(p[1] * 100, 1) for p in r["vertices_pct"]}
    assert 40.0 in ys
    assert not r.get("projection_refusals")
    # the wall corners stay the plate-terminated singles (gable basis)
    assert r["wall_corners"] == [10.0, 50.0]


def test_shoulder_split_by_lineweight_fragments_still_joins():
    """CAD fragmentation: the same joint drawn as pieces with breaks
    within line-weight (the Letrick anatomy — connector, rect rail,
    connector) still establishes; gap_tol-scale breaks do not."""
    segs = _base() + [
        _v(56.0, 15.0, 61.0), _v(58.0, 15.0, 61.0),
        _h(50.0, 52.0, 40.0), _h(52.02, 55.0, 40.0),
        _h(55.03, 56.0, 40.01),
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 58.0]


def test_shortfall_on_no_reference_refuses_projection():
    """The jog ink stops inside the gap on NO drawn stroke — it cannot
    name the reference it terminates at: no joint, wall-only outline,
    and the face SAYS the projection refused."""
    segs = _base() + [
        _v(58.0, 15.0, 61.0),         # projection, single-drawn
        _h(50.0, 56.0, 40.0),         # ink stops 2.0 short, on nothing
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 50.0]
    assert r["n_vertices"] == 4
    refs = r.get("projection_refusals") or []
    assert any(abs(p["x"] - 58.0) < 0.06 for p in refs)
    assert "no drawn shoulder" in refs[0]["reason"]


def test_member_with_three_strokes_yields_no_joint_to_outermost():
    """A stroke strictly between the landing and the boundary means the
    member carries 3+ strokes — the joint to the outermost stroke is
    refused (no snapping past named references)."""
    segs = _base() + [
        _v(56.0, 15.0, 61.0), _v(57.0, 15.0, 61.0), _v(58.0, 15.0, 61.0),
        _h(50.0, 56.0, 40.0),
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    # joint to 58 dies (57 sits between the landing at 56 and 58);
    # the inner pair {56,57} is double-drawn on its own references.
    assert r["x_span"][1] < 58.0 - 0.05
    refs = r.get("projection_refusals") or []
    assert any(abs(p["x"] - 58.0) < 0.06 for p in refs)


def test_fragment_chain_jog_short_on_nothing_dies():
    """The wrong-edge-bump anatomy: a top fragment and a bottom
    fragment whose jog ink meets neither within line-weight and lands
    on no through-stroke — accepted under the old gap_tol end test,
    DEAD under CCC."""
    segs = _base(right_wall=50.0) + [
        _v(30.0, 20.2, 40.0),          # top fragment
        _v(32.0, 40.0, 61.0),          # bottom fragment
        _h(30.2, 31.2, 40.0),          # old law: 0.2/0.8 <= gap_tol
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 50.0]   # no bump — chain refused
    assert r["n_vertices"] == 4


def test_full_span_chain_jog_unaffected():
    """A legitimate jog whose drawn line reaches both members (within
    the joint law outside) still chains — the 100–105% course-line
    jogs move nowhere under the minimum framing."""
    segs = [
        _v(10.0, 20.2, 61.0),
        _v(30.0, 20.2, 40.0),          # top fragment (right side)
        _v(34.0, 40.0, 61.0),          # bottom fragment
        _h(29.9, 34.05, 40.0),         # spans member to member
        _h(9.0, 40.0, 20.5), _h(9.0, 40.0, 60.5),
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 34.0]
    assert r["n_vertices"] == 6


def test_crossing_is_not_a_joint():
    """A line sailing past both members by more than the joint law is
    a crossing: it establishes nothing (unchanged from SEND-69)."""
    segs = _base() + [
        _v(30.0, 20.2, 40.0), _v(34.0, 40.0, 61.0),
        _h(20.0, 45.0, 40.0),          # crosses both
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 50.0]
    assert r["n_vertices"] == 4


def test_course_line_overspanning_members_is_not_a_shoulder():
    """A face-long course line whose ends merely come NEAR two spanning
    members (within gap_tol) names no reference — a crossing, not a
    shoulder. No phantom projection joint."""
    segs = _base() + [
        _v(56.0, 15.0, 61.0), _v(58.0, 15.0, 61.0),
        _h(49.0, 59.0, 45.0),          # overspans both by 1.0
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 50.0]
    refs = r.get("projection_refusals") or []
    assert {round(p["x"]) for p in refs} == {56, 58}


def test_shoulder_terminating_at_outer_strokes_overspans_and_passes():
    """Both drafting variants accommodated: ink running outer-to-outer
    covers the inner-to-inner gap and passes with no second case."""
    segs = _base() + [
        _v(56.0, 15.0, 61.0), _v(58.0, 15.0, 61.0),
        _h(50.0, 58.0, 40.0),          # reaches the outer stroke
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 58.0]
    assert r["n_vertices"] == 6
