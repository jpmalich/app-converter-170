"""SEND-90 register (Howard, 2026-08-14, verbatim core): "RULING XX
WIDTH CROSS-CHECK. WIRE IT. Left and right elevation widths that
disagree are FLAGGED ON THE PAYLOAD, NEVER AUTO-RESOLVED."

Condition 1 — COMPARE WALL-ONLY, NOT SILHOUETTE: "XX'S VERDICT IS THAT
THE TWO SIDE DEPTHS ARE EQUAL. A DEPTH IS A PLAN-DERIVED WALL FIGURE.
A LINE-WORK SILHOUETTE INCLUDES PROJECTIONS. Those are not the same
measurement and pairing them mixes two rulers. A PROJECTION ON ONE
SIDE ONLY WOULD MAKE SILHOUETTES DIFFER LEGITIMATELY AND THE CHECK
WOULD FALSE-FIRE."

Condition 2 — A REPORTED DIFFERENCE, NOT A BOOLEAN FLAG: "ANY 'AGREE
WITHIN X' IS A CHOSEN THRESHOLD ... REPORT THE MAGNITUDE INSTEAD ...
No threshold, no fatigue, and the size carries the meaning. If Howard
later wants a loud rail above some size, that is his threshold to set
and it goes in a send. NOT ONE THE CODE PICKS."

Silences: "silent-because-indeterminate must be distinguishable from
silent-because-agreeing. That distinction is the whole reason it would
have caught the missing chimney."

WHAT IT EXISTS FOR: "THIS WOULD HAVE CAUGHT THE MISSING CHIMNEY
WITHOUT ANYONE CHECKING PRINTS. Left read 32.60 and right read 29.65,
three feet apart, on a house XX already knew had equal depths. Nobody
noticed until Howard looked at the drawings."
"""
import inspect

import pytest

import routes.pdf_overlay as po


IMM = {"status": "IMMATERIAL", "why": "equal side depths",
       "seat_pages": ["5", "7"]}


def test_reported_difference_is_a_magnitude_never_a_boolean():
    sides = {"left": {"wall_only_ft": 29.4, "silhouette_ft": 31.94},
             "right": {"wall_only_ft": 29.65, "silhouette_ft": 32.24}}
    out = po._xx_width_cross_check(IMM, sides)
    assert out["state"] == "REPORTED"
    assert out["difference_ft"] == 0.25
    assert "left 29.4 ft" in out["statement"]
    assert "right 29.65 ft" in out["statement"]
    assert "differ by 0.25 ft" in out["statement"]
    # no boolean verdict key, no threshold key of any kind
    for k in ("agree", "agrees", "ok", "within", "threshold", "alarm",
              "exceeds", "flagged"):
        assert k not in out, f"boolean/threshold key {k} present"


def test_comparison_runs_on_wall_only_silhouette_rides_uncompared():
    sides = {"left": {"wall_only_ft": 29.4, "silhouette_ft": 31.94},
             "right": {"wall_only_ft": 29.65, "silhouette_ft": 32.24}}
    out = po._xx_width_cross_check(IMM, sides)
    # the compared magnitude is the wall-only one (0.25), not the
    # silhouette one (0.30); the silhouette figure is carried and
    # explicitly marked NOT the compared figure
    assert out["difference_ft"] == 0.25
    assert out["silhouette_difference_ft"] == 0.3
    assert "NOT the compared figures" in out["statement"]


def test_large_difference_gets_the_same_reported_state_no_loud_rail():
    # SEND-90: "the size carries the meaning" — a 3 ft gap reports
    # identically in STATE; no code-picked threshold escalates it.
    sides = {"left": {"wall_only_ft": 32.60, "silhouette_ft": None},
             "right": {"wall_only_ft": 29.65, "silhouette_ft": None}}
    out = po._xx_width_cross_check(IMM, sides)
    assert out["state"] == "REPORTED"
    assert out["difference_ft"] == 2.95
    assert "differ by 2.95 ft" in out["statement"]


def test_silent_because_indeterminate_is_distinguishable():
    v = {"status": "INDETERMINATE",
         "why": "p4 left winner is an exact positional tie",
         "seat_pages": ["4", "6", "7"]}
    out = po._xx_width_cross_check(v, {})
    assert out["state"] == "SILENT_INDETERMINATE"
    assert "NOT because the sides agree" in out["statement"]
    assert "positional tie" in out["statement"]


def test_material_verdict_makes_no_equality_comparison():
    v = {"status": "MATERIAL", "why": "unequal side depths"}
    sides = {"left": {"wall_only_ft": 29.4},
             "right": {"wall_only_ft": 29.65}}
    out = po._xx_width_cross_check(v, sides)
    assert out["state"] == "NOT_COMPARED"
    assert out["difference_ft"] is None
    assert "differ by" not in out["statement"]


def test_missing_wall_only_figure_names_the_side_and_reason():
    sides = {"left": {"wall_only_ft": None, "silhouette_ft": 31.94,
                      "note": "no plate-terminated wall corners on "
                              "this drawing — a wall-only width does "
                              "not stand"},
             "right": {"wall_only_ft": 29.65, "silhouette_ft": 32.24}}
    out = po._xx_width_cross_check(IMM, sides)
    assert out["state"] == "SILENT_NO_FIGURE"
    assert "left" in out["statement"]
    assert "no plate-terminated wall corners" in out["statement"]
    # it never fabricates a comparison from the silhouette instead
    assert out["difference_ft"] is None


def test_seat_is_the_floor_plan_sheets_and_disagreement_flags(
        monkeypatch):
    import ocr_geometry
    run = {"result": {"raw_ai": {"sheets_identified": [
        {"page": 1, "useful_for": "elevation"},
        {"page": 4, "useful_for": "floor_plan"},
        {"page": 6, "useful_for": "floor_plan"},
    ]}}}
    ot = {"1": {"runs": []}, "4": {"runs": []}, "6": {"runs": []}}
    verdicts = {"4": {"status": "INDETERMINATE",
                      "why": "exact positional tie", "depth": None},
                "6": {"status": "MATERIAL",
                      "why": "unequal side depths", "depth": None}}
    calls = []

    def fake(runs):
        pg = [p for p, page in ot.items() if page["runs"] is runs]
        calls.append(pg[0])
        return verdicts[pg[0]]

    # distinct list objects so identity lookup works
    for p in ot:
        ot[p]["runs"] = [p]
    monkeypatch.setattr(ocr_geometry, "attribution_verdict", fake)
    out = po._xx_seat_verdict(ot, run)
    # only the floor-plan pages are consulted — never the elevation
    assert set(calls) == {"4", "6"}
    assert out["seat_pages"] == ["4", "6"]
    assert out["status"] == "INDETERMINATE"
    assert "flagged, never resolved" in out["why"]
    assert "p4 INDETERMINATE" in out["why"]
    assert "p6 MATERIAL" in out["why"]


def test_seat_agreement_passes_through_immaterial_with_depth(
        monkeypatch):
    import ocr_geometry
    run = {"result": {"raw_ai": {"sheets_identified": [
        {"page": 5, "useful_for": "floor_plan"},
        {"page": 7, "useful_for": "floor_plan"},
    ]}}}
    ot = {"5": {"runs": ["5"]}, "7": {"runs": ["7"]}}
    monkeypatch.setattr(
        ocr_geometry, "attribution_verdict",
        lambda runs: {"status": "IMMATERIAL", "why": "equal",
                      "depth": {"feet": 30, "inches": 0}})
    out = po._xx_seat_verdict(ot, run)
    assert out["status"] == "IMMATERIAL"
    assert out["depth"] == {"feet": 30, "inches": 0}


def test_no_floor_plan_sheet_means_no_seat():
    out = po._xx_seat_verdict({}, {"result": {"raw_ai": {
        "sheets_identified": [{"page": 1, "useful_for": "elevation"}]}}})
    assert out["status"] == "INDETERMINATE"
    assert "no floor-plan sheet" in out["why"]


def test_structural_propose_route_carries_the_cross_check():
    src = inspect.getsource(po.propose_zones)
    assert "_xx_seat_verdict" in src
    assert "_xx_width_cross_check" in src
    assert "width_cross_check" in src
    # the verdict rides every proposal's provenance
    assert '"attribution"' in src


def test_register_states_what_it_exists_for():
    assert "would have caught the missing chimney" in \
        po.XX_CROSS_CHECK_REGISTER.lower()
    assert "32.60" in po.XX_CROSS_CHECK_REGISTER
    assert "29.65" in po.XX_CROSS_CHECK_REGISTER
    assert "NEVER" in po.XX_CROSS_CHECK_REGISTER
