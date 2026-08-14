"""RULING Q SYNTHETIC PINS — base-course & batten refusal paths
(Howard sealed 2026-08-14 send-18).

MANDATORY (send-18 Q): shared-source is a flag not a kill since send-13, so a
real fixture's widths/heights survive and these refusal branches may never
fire on the fixture set. Each pin deliberately KILLS the input and asserts
the derived quantity carries its NOT-DERIVABLE / PARTIAL status rather than a
silent 0.
"""
import sys

sys.path.insert(0, "/app/backend")

from quantity import DERIVED, PARTIAL  # noqa: E402


# ── Base-course starter: a killed wall width routes through the gateway ──

def test_killed_width_wall_is_not_derivable_never_a_silent_base_course():
    from profile_callouts import breakdown_walls_by_profile
    # No segments, no width read — width is dead. eave height present.
    dead = {"label": "front", "height_ft": 9.0, "width_ft": None,
            "wall_body_profile_callout": "lap"}
    out = breakdown_walls_by_profile([dead], default_body_profile="lap")
    # The face is NAMED not-derivable (never silently 0 base course).
    nd = out["faces_not_derivable"]
    assert any(f.get("elevation") == "front" and f.get("surface") == "body"
               and "width not read" in (f.get("reason") or "") for f in nd)
    # And its area was NOT silently credited to the profile totals.
    assert out["per_profile_sqft"].get("lap", 0) == 0


def test_readable_width_wall_still_derives_base_course():
    from profile_callouts import breakdown_walls_by_profile
    live = {"label": "front", "height_ft": 9.0, "width_ft": 20.0,
            "wall_body_profile_callout": "lap"}
    out = breakdown_walls_by_profile([live], default_body_profile="lap")
    assert out["per_profile_sqft"].get("lap", 0) > 0
    assert not out["faces_not_derivable"]


# ── Batten: the +1-run term is PARTIAL, not a silent 0 ──

def test_batten_run_term_partial_when_wall_height_unconfirmed():
    from lp_smartside_formulas import board_batten_batten_pieces_status
    q = board_batten_batten_pieces_status(1000.0, spacing_in=12, wall_height_ft=0)
    assert q.status == PARTIAL and q.value is not None and q.value > 0
    assert any("run" in str(x) for x in q.excluded)


def test_batten_derived_when_wall_height_confirmed():
    from lp_smartside_formulas import board_batten_batten_pieces_status
    q = board_batten_batten_pieces_status(1000.0, spacing_in=12, wall_height_ft=18.0)
    assert q.status == DERIVED and q.value > 0


def test_batten_no_area_is_a_clean_zero():
    from lp_smartside_formulas import board_batten_batten_pieces_status
    q = board_batten_batten_pieces_status(0.0, spacing_in=12, wall_height_ft=0)
    assert q.status == DERIVED and q.value == 0
