"""R1 (Howard ruled 2026-07-30): EXACTLY 2 J PASSES PER RAKE.
One WALL pass on the wall J-Channel line (vinyl accessories category),
ONE rake pass on Soffit J (soffit category). The old soffit-J 2×rakes term
(3 passes total) is retired.

PIN THE TWO TOGETHER (Howard's mandate): the finish-trim exclusion comment
and the derivations now agree through ONE doctrine marker — a change to one
that does not change the other fails here. Behavioral triangle: wall-J
counts the rake once, soffit-J counts it once, finish trim counts it zero;
total == 2. The line note must NAME the pre-ruling delta so the move never
arrives silently inside a rebuild."""
import math

from routes.hover import (
    RAKE_J_DOCTRINE, _finish_trim_pcs, _j_channel_pcs, _build_lines,
)

MARKER = "R1 ruled 2026-07-30"


def _soffit_j(lines):
    return next(l for l in lines
                if l["name"].startswith('3/4" Soffit J-Channel'))


def _mk(eaves, rakes):
    return _build_lines({"siding_sqft": 2000, "eaves_lf": eaves,
                         "rakes_lf": rakes, "window_count": 0})


def test_soffit_j_counts_the_rake_once():
    # E=125 → 10 pcs alone; R=125 adds exactly ONE pass = 10 more (2× gave 20)
    assert _soffit_j(_mk(125, 0))["qty"] == 10
    assert _soffit_j(_mk(125, 125))["qty"] == 20
    assert _soffit_j(_mk(100, 140))["qty"] == math.ceil(240 / 12.5)  # 20, not 31


def test_wall_j_counts_the_rake_once():
    base = _j_channel_pcs({"eaves_lf": 125, "rakes_lf": 0, "window_count": 0})
    with_r = _j_channel_pcs({"eaves_lf": 125, "rakes_lf": 125, "window_count": 0})
    assert with_r - base == 10  # one pass


def test_finish_trim_counts_the_rake_zero():
    a = _finish_trim_pcs({"eaves_lf": 125, "rakes_lf": 0, "window_count": 0})
    b = _finish_trim_pcs({"eaves_lf": 125, "rakes_lf": 500, "window_count": 0})
    assert a == b


def test_total_rake_passes_is_exactly_two():
    r = 125.0
    wall = (_j_channel_pcs({"eaves_lf": 125, "rakes_lf": r, "window_count": 0})
            - _j_channel_pcs({"eaves_lf": 125, "rakes_lf": 0, "window_count": 0}))
    soffit = _soffit_j(_mk(125, r))["qty"] - _soffit_j(_mk(125, 0))["qty"]
    passes = (wall + soffit) / (r / 12.5)
    assert passes == 2.0, f"rake J passes = {passes} — ruling says exactly 2"


def test_comment_and_derivation_are_pinned_together():
    """A change to the derivation that does not change the doctrine (or vice
    versa) fails: the marker must live in the doctrine constant, in the
    finish-trim exclusion docstring, and on the emitted soffit-J note."""
    assert MARKER in RAKE_J_DOCTRINE
    assert MARKER in (_finish_trim_pcs.__doc__ or "")
    note = _soffit_j(_mk(100, 140))["note"]
    assert MARKER in note


def test_delta_is_named_on_the_line_never_silent_in_a_rebuild():
    note = _soffit_j(_mk(100, 140))["note"]
    assert "pre-ruling 2×rakes rule gave 31" in note and "now 20" in note
