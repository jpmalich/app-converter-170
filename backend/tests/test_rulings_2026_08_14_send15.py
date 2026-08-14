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

@pytest.mark.skip(reason=(
    "ruling:held: RULING G (send-15) corner never-average refusal — the "
    "CENSUS is delivered in the handback (every priced averaging site: "
    "lp_package _corner_height_ft/OSC/ISC, ai_blueprint corner ledger "
    "basis='averaged', inside_corner_lf = count x avg, and the avg_wall_"
    "height_ft fallbacks with a hardcoded 9.5). Howard ruled 'I want the "
    "list before anything is changed' for averaging wider than corners; "
    "the corner refusal build is therefore gated on his review of that "
    "census. WHAT WOULD UNHOLD IT: his go-ahead after reading the census."))
def test_ruling_G_corner_reports_not_derivable_over_unheighted_wall():
    raise AssertionError("held pending census review — see skip reason")


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


@pytest.mark.skip(reason=(
    "ruling:held: RULING H remaining siblings (base course, batten +1 run) "
    "and the PREFERRED 'only-obtainable' shape. FEASIBILITY (reported): the "
    "true 'only-obtainable' shape (a caller cannot reach a raw width_ft / "
    "height_ft) is NOT reachable without breaking JSON/Mongo serialization "
    "of the wall dicts and dozens of readers; the reachable shape is the "
    "one-copy accessor (built) that every priced reader MUST call, enforced "
    "by a census pin. WHAT WOULD UNHOLD IT: Howard's go-ahead to wire base "
    "course + batten to the accessor and add the 'no raw width/height read "
    "in a priced path' census pin. gable + eaves are already wired."))
def test_ruling_H_all_five_siblings_wired_and_census_pinned():
    raise AssertionError("partially built — see skip reason")
