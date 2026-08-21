"""SEND-94 register (Howard, 2026-08-14, verbatim core):

RULINGS: "LETRICK REAR CHIMNEY SIDING WIDTH = ≈5'-4\" OUTSIDE. The
6'-0\" is THE BRICK FACADE, NOT THE SIDED SURFACE. LEAVE THE REAR
HEIGHT CONTESTED."

Item 1: "5'-4\" IS A HUMAN DIMENSION. MARK IT AS ONE ... NEVER
PRESENTED AS DERIVED. A human dimension wearing a derived label is
the same defect as a model height wearing one."

Item 2: "THE SEALED WIDTH BREAKS THE EXACT-SUM PIN. FIX BY
CONSTRUCTION ... DO NOT ADD A TOLERANCE. THE CHASE IS THE HUMAN-SET
VALUE. THE TWO WALL SECTIONS ARE THE REMAINDER, split at the chase's
drawn position. Then the partition closes at EITHER contestant's
scale."

Wire: "Sides revert to WALL-ONLY, 29.4 and 29.65. THE BUMP MOVES TO
ITS OWN SURFACE — it does not disappear. Rear becomes three surfaces,
sides two. The partition-sums-to-the-face pin runs on every face,
every house, every time. The above-plate chase stops being dropped."

Synthetic geometry only in these pins — no job figures; the sealed
5'-4\" lives as DATA (human_dimensions collection), never in code.
"""
import pathlib

from linework_read import wall_outline_from_segments
from routes.pdf_overlay import _chase_partition

PLATE, FLOOR = (20.0, 21.0), (60.0, 61.0)
BAND = (0.0, 100.0)


def _v(x, top, bottom):
    return {"x0": x, "x1": x, "top": top, "bottom": bottom}


def _h(x0, x1, y):
    return {"x0": x0, "x1": x1, "top": y, "bottom": y}


def _base():
    return [
        _v(10.0, 20.2, 61.0), _v(50.0, 20.2, 61.0),
        _h(9.0, 60.0, 20.5),
        _h(9.0, 60.0, 60.5),
    ]


def test_partition_sum_holds_by_construction_at_either_scale():
    """Item 2 — integer hundredths: chase fixed, walls the remainder
    split at the drawn position. The sum equals the face EXACTLY at
    both contested scales; no tolerance exists anywhere."""
    ratio = 15.23 / 38.84            # a drawn split position
    for face_h in (6015, 5510):      # both contestants of a face
        wl, cc, wr = _chase_partition(face_h, 533, ratio)
        assert wl + cc + wr == face_h            # exact, always
        assert cc == 533                         # chase fixed either way
    # walls shift with the contestant; the chase does not
    a = _chase_partition(6015, 533, ratio)
    b = _chase_partition(5510, 533, ratio)
    assert a[0] != b[0] and a[2] != b[2] and a[1] == b[1]


def test_partition_never_carries_a_tolerance_key():
    src = pathlib.Path("/app/backend/routes/pdf_overlay.py").read_text()
    fn = src[src.index("def _chase_partition"):]
    fn = fn[:fn.index("\ndef ")]
    for word in ("epsilon", "abs(", "1e-"):
        assert word not in fn, f"tolerance-shaped token {word!r}"


def test_edge_chase_splits_off_and_body_reverts_to_wall_only():
    """Sides: the bump moves to its own surface — it does not
    disappear. body_x_span = the plate-terminated wall corners; the
    chase carries wall/projection strokes + its above-plate ink top."""
    segs = _base() + [
        _v(56.0, 15.0, 61.0),         # projection inner twin
        _v(58.0, 15.0, 61.0),         # projection outer stroke
        _h(50.0, 56.0, 40.0),         # drawn shoulder
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert r["x_span"] == [10.0, 58.0]          # silhouette unchanged
    assert r["body_x_span"] == [10.0, 50.0]     # wall-only body
    ch = (r["chases"] or [])
    assert len(ch) == 1 and ch[0]["kind"] == "edge"
    assert ch[0]["x_wall"] == 50.0 and ch[0]["x_proj"] == 58.0
    assert ch[0]["top_ink_y"] == 15.0           # above-plate ink kept


def test_interrupting_chase_detected_by_full_height_members_and_cap():
    """Rear: full-height non-pt members strictly inside the body,
    joined by a DRAWN CAP above the plate → three surfaces."""
    segs = _base() + [
        _v(28.0, 15.0, 61.0),         # chase member, full height
        _v(32.0, 15.0, 61.0),         # chase member, full height
        _h(28.0, 32.0, 15.0),         # the drawn cap joins their tops
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    ch = (r["chases"] or [])
    assert len(ch) == 1 and ch[0]["kind"] == "interrupting"
    assert ch[0]["x_inner"] == [28.0, 32.0]
    assert ch[0]["top_ink_y"] == 15.0
    assert r["body_x_span"] == [10.0, 50.0]


def test_full_height_discriminator_a_window_never_becomes_a_chase():
    """SEND-89 item 2 — a projection that does not span the full wall
    height is an opening, never a surface split. Same ink, cut short
    of the floor → no chase."""
    segs = _base() + [
        _v(28.0, 25.0, 45.0),         # window-height verticals
        _v(32.0, 25.0, 45.0),
        _h(28.0, 32.0, 25.0),         # a head line joining their tops
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    assert r["status"] == "RESOLVED"
    assert not r.get("chases")


def test_eave_lines_never_pair_as_a_cap():
    """A face-long horizontal above the plate (eave/ridge) ends at the
    face boundary, not on the chase members — it must not create an
    interrupting chase between boundary trim strokes."""
    segs = _base() + [
        _v(28.0, 15.0, 61.0), _v(32.0, 15.0, 61.0),
        _h(9.0, 60.0, 15.0),          # eave-like spanner (a crossing)
    ]
    r = wall_outline_from_segments(segs, BAND, PLATE, FLOOR, [])
    # ends at 9/60 land on no member's top → no cap, no chase
    assert not r.get("chases")


def test_structural_propose_wires_the_partition_and_the_provenance():
    src = pathlib.Path("/app/backend/routes/pdf_overlay.py").read_text()
    # human-supplied widths come from DATA, marked, never derived
    assert "human_dimensions" in src
    assert "HUMAN DIMENSION, never" in src
    assert '"width_source": ("human" if hd' in src.replace(
        "\n", " ").replace("  ", " ") or '"width_source"' in src
    # the chase is its own surface; wall sections split the body
    assert 'f"chase:{face_to_id[face]}"' in src
    assert "WALL SECTION" in src
    # the partition payload rides the response
    assert '"partitions": partitions' in src
    # the sum-by-construction helper is the only partition arithmetic
    assert "_chase_partition" in src


def test_silhouette_is_kept_beside_the_wall_only_body():
    src = pathlib.Path("/app/backend/routes/pdf_overlay.py").read_text()
    assert '"silhouette_x_span": lw.get("x_span")' in src
    assert '"body_x_span": lw.get("body_x_span")' in src
