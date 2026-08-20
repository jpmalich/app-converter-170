"""SEND-77 pins — X-SCOPING CURE (authorized; reported before wiring:
memory/send77_dryrun.py · memory/send77_prediction.md).

FENCE CONTAINMENT mirrors BAND CONTAINMENT: a qualifying stroke lies
entirely inside the face's OWN datum-line extent in x (± the drawing's
own line-weight tolerance), exactly as it must lie inside the title
band in y. Set membership against the drawing's own evidence — no
threshold, and the fence is NEVER shrunk to fit (Howard, verbatim:
"DO NOT SHRINK THE FENCE TO MAKE IT FIT. That would be a threshold").

Live outcome pinned as an observation (dry run, 2026-08-21): LETRICK
right RESOLVED 29.65 ft with 4 vertices under the fence — Howard's own
prediction named this branch ("IF IT RETURNS 30.0 FLAT WITH 4
VERTICES, either the chimney is offset toward the left side of the
house, or the read missed it on right. Howard's prints settle which").
No currently-resolved face moved (all 7 others byte-identical).
"""
import sys

sys.path.insert(0, "/app/backend")
from linework_read import wall_outline_from_segments  # noqa: E402

BAND = (10.0, 50.0)
PLATE = (25.5, 26.5)
FLOOR = (43.5, 44.5)

# The face's own drawing: a plain rectangle at x 20–60.
_OWN = [
    {"x0": 20, "x1": 20, "top": 25, "bottom": 45},   # left wall
    {"x0": 60, "x1": 60, "top": 25, "bottom": 45},   # right wall
    {"x0": 20, "x1": 60, "top": 26, "bottom": 26},   # plate line
    {"x0": 20, "x1": 60, "top": 44, "bottom": 44},   # floor line
]
# A NEIGHBOURING drawing sharing the band's y-range (the Letrick-right
# failure shape): its verticals span the same datum interval, so
# without a fence the outermost boundary jumps to x=90 and the plate
# line (20–60) can no longer close the top.
_NEIGHBOUR = [
    {"x0": 80, "x1": 80, "top": 25, "bottom": 45},
    {"x0": 90, "x1": 90, "top": 25, "bottom": 45},
    {"x0": 80, "x1": 90, "top": 26, "bottom": 26},
    {"x0": 80, "x1": 90, "top": 44, "bottom": 44},
]
FENCE = (10.0, 70.0)   # the face's own datum-line extent (leader-wide)


def test_a_neighbouring_drawing_breaks_closure_without_the_fence():
    """The BEFORE truth (Letrick right's live failure, reproduced):
    the neighbour's strokes become the outermost boundary and the
    face's own plate line cannot close against them."""
    r = wall_outline_from_segments(_OWN + _NEIGHBOUR, BAND, PLATE,
                                   FLOOR, [])
    assert r["status"] == "INDETERMINATE"
    assert "not closed" in r["reason"]


def test_the_fence_excludes_the_neighbour_and_the_face_resolves():
    r = wall_outline_from_segments(_OWN + _NEIGHBOUR, BAND, PLATE,
                                   FLOOR, [], x_fence=FENCE)
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 60.0]
    assert r["n_vertices"] == 4


def test_fence_containment_is_set_membership_not_a_threshold():
    """A stroke NOT entirely inside the fence is excluded; one within
    the drawing's own line-weight tolerance of the edge is kept (the
    tolerance is the datum box height — numeric noise, not a knob)."""
    outside = [{"x0": 72, "x1": 72, "top": 25, "bottom": 45}]
    r = wall_outline_from_segments(_OWN + outside, BAND, PLATE, FLOOR,
                                   [], x_fence=FENCE)
    assert r["status"] == "RESOLVED"           # 72 > 70+1.0 → excluded
    assert r["x_span"] == [20.0, 60.0]

    edge = [{"x0": 70.5, "x1": 70.5, "top": 25, "bottom": 45}]
    r2 = wall_outline_from_segments(_OWN + edge, BAND, PLATE, FLOOR,
                                    [], x_fence=FENCE)
    # 70.5 ≤ 70+1.0 (line-weight) → KEPT, and the plate line cannot
    # close against it — proving the stroke entered the set.
    assert r2["status"] == "INDETERMINATE"
    assert "not closed" in r2["reason"]


def test_no_fence_means_no_behavior_change():
    """x_fence=None is byte-identical to the pre-SEND-77 read — the
    cure only ever REMOVES foreign strokes, it invents nothing."""
    a = wall_outline_from_segments(_OWN, BAND, PLATE, FLOOR, [])
    b = wall_outline_from_segments(_OWN, BAND, PLATE, FLOOR, [],
                                   x_fence=None)
    assert a == b
    assert a["status"] == "RESOLVED" and a["x_span"] == [20.0, 60.0]


def test_the_fence_is_never_shrunk_a_wall_at_the_fence_edge_resolves():
    """The fence is the datum extent VERBATIM: a wall sitting exactly
    at the fence bounds still resolves — nothing pulls the fence
    inward toward any width."""
    r = wall_outline_from_segments(_OWN, BAND, PLATE, FLOOR, [],
                                   x_fence=(20.0, 60.0))
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [20.0, 60.0]


def test_propose_path_passes_the_face_datum_extent_as_the_fence():
    """Structural: the live propose call feeds x_fence from the face's
    own datum markers and DISCLOSES it on proposed_from.linework."""
    import pathlib
    src = pathlib.Path("/app/backend/routes/pdf_overlay.py").read_text()
    assert "x_fence=x_fence" in src
    call = src.index("x_fence=x_fence")
    region = src[call - 1200:call]
    assert "markers" in region       # fence built from datum markers
    assert '"x_fence": lw.get("x_fence")' in src   # disclosed
