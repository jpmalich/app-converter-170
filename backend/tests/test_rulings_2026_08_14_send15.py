"""RULINGS REGISTER — SEND-15 (2026-08-14).

Per Ruling C (sealed send-14): one register file per send, ruling WORDS
verbatim in docstrings, held/unbuilt rulings visible and named. Full send
prose is archived verbatim at backend/rulings_archive/send15.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes.ai_blueprint as ab  # noqa: E402


def test_ruling_E_axis_is_declared_unknown_fires_conflict():
    """RULING E (send-15): 'Every dimension leaf DECLARES its axis:
    VERTICAL, HORIZONTAL, or UNKNOWN. Undeclared is UNKNOWN. Not
    horizontal. Never inferred from the field name. A share involving an
    UNKNOWN-axis leaf fires the CONFLICT rail, naming the undeclared
    leaf.' Built + pinned in test_axis_declaration_2026_08_14_send15.py."""
    assert ab._leaf_axis("parapet_ft") == "U"
    assert ab._shared_attribution_conflict(
        ["walls.front.width_ft", "walls.front.parapet_ft"]) is True


def test_ruling_H_subset_aware_accessor_is_the_one_copy():
    """RULING H (send-15): 'A KILLED OR SUBSET INPUT NEVER PRODUCES A
    SILENT NUMBER. It produces a named refusal or a disclosed subset.'
    PREFERRED SHAPE (feasibility reported NOT fully reachable — see the
    NOT BUILT note below): the one-copy subset-aware accessors
    wall_width_for_pricing / wall_height_for_pricing exist and a killed
    input returns not-derivable, never a silent 0. walk_walls gable +
    eaves_from_walls are wired to them (canonical disclosing path)."""
    from measure_staging import wall_width_for_pricing, wall_height_for_pricing
    assert wall_width_for_pricing({"label": "left", "width_ft": None}) \
        == (0.0, False, False, ["left"])
    assert wall_height_for_pricing({"label": "b", "height_ft": None}) \
        == (0.0, False)


def test_ruling_J_money_reflects_a_not_derivable_quantity():
    """RULING J (send-15 addendum, verbatim): 'Money is derived from the
    material quantities... Do not build special money-line logic,
    averages, or silent zeros. If a quantity is NOT DERIVABLE, the money
    that depends on it should reflect that — not be filled in quietly.'
    Enforced structurally: the priced quantity itself carries status
    (Ruling H), so no bespoke money-line logic is needed. A killed wall
    body produces a NOT DERIVABLE face, not a silent 0."""
    from profile_callouts import breakdown_walls_by_profile
    bd = breakdown_walls_by_profile([{"label": "left", "width_ft": None,
                                       "height_ft": None,
                                       "wall_body_profile_callout": "lap"}])
    assert bd["per_elevation"][0]["wall_body_sqft"] is None
    assert any(f.get("surface") == "body" for f in bd["faces_not_derivable"])


# ---- RULINGS ON THE RECORD BUT NOT FULLY BUILT THIS SEND ----

def test_ruling_G_corner_reports_not_derivable_over_unheighted_wall():
    # BUILT send-18 (Ruling R/Q): a corner/OSC over a wall with no verified
    # height is NOT DERIVABLE — never the min(), never the average. Full
    # synthetic coverage in test_ruling_qr_corner_refusal_2026_08_14_send18.
    from lp_package import _corner_height_ft
    q_ = _corner_height_ft({"type": "outside", "walls": ["back"]}, {"front": 9.0})
    assert q_.status == "NOT_DERIVABLE" and q_.value is None
    assert "back" in " ".join(q_.excluded)


@pytest.mark.skip(reason=(
    "ruling:held: RULING F (send-15) money-line + elevation-sheet surfaces. "
    "MONEY LINE is SUPERSEDED by Ruling J: money must reflect the quantity's "
    "status via the honest takeoff (Ruling H), NOT bespoke money-line note "
    "logic which J forbids ('do not build special money-line logic'). "
    "ELEVATION-SHEET rail render is a frontend surface whose 'what renders' "
    "pin needs frontend test infra not present in the pytest suite. "
    "WHAT WOULD UNHOLD IT: Howard's decision on whether the elevation sheet "
    "gets the rail given J, plus a frontend render harness for the pin. "
    "The two send-13 surfaces are recorded NOT BUILT in the send-13 register."))
def test_ruling_F_money_line_and_sheet_surfaces():
    raise AssertionError("held/superseded — see skip reason")


def test_ruling_H_all_five_siblings_wired_and_census_pinned():
    # BUILT send-18 (Ruling Q + P): base course routes through
    # wall_width_for_pricing (killed width ⇒ NOT DERIVABLE face, no silent
    # area); the batten +1-run term is PARTIAL when the wall height is
    # unconfirmed (never a folded silent 0); the census pin (Ruling P)
    # scans all priced modules and no in-scan reader remains
    # PENDING_CONVERSION. gable + eaves were already wired (send-15).
    from lp_smartside_formulas import board_batten_batten_pieces_status
    from profile_callouts import breakdown_walls_by_profile
    bd = breakdown_walls_by_profile([{"label": "l", "width_ft": None,
                                      "height_ft": 9.0,
                                      "wall_body_profile_callout": "lap"}])
    assert any(f.get("surface") == "body" for f in bd["faces_not_derivable"])
    assert bd["per_profile_sqft"].get("lap", 0) == 0
    assert board_batten_batten_pieces_status(1000.0, 12, 0).status == "PARTIAL"
    baseline = (Path(__file__).parent / "_raw_wall_dim_baseline.txt").read_text()
    pending = [ln for ln in baseline.splitlines()
               if ln.strip() and not ln.strip().startswith("#")
               and "PENDING_CONVERSION" in _class_above(baseline, ln)]
    assert not pending, f"a reader is still PENDING_CONVERSION: {pending}"


def _class_above(text: str, line: str) -> str:
    cls = ""
    for ln in text.splitlines():
        if ln.strip().startswith("# ["):
            cls = ln.strip()[3:ln.strip().index("]")]
        if ln == line:
            return cls
    return cls
