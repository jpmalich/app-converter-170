"""INTAKE CLASSES A/B/C + TALL CORNERS + CEILING DEDUP (sealed 2026-07-28).
Register classes KILLED BY CONSTRUCTION — detectors fail on ANY instance;
261 Haugh is EVIDENCE #1 (graduated fixture), not the subject.
RIDER 2: Class B is detection only — changes NO derivation and NO dollar.
"""
import math
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routes.lp_package_routes import _hover_mapping_contract
from routes.hover import _osc_lp_pcs, PROMPT_TEMPLATE
from lp_package import assemble_lp_package, OSC_ITEM
from hover_field_register import HOVER_FIELD_REGISTER, CONSUMED, NOT_CONSUMED

# 261 Haugh — GRADUATED FIXTURE (test-estimate doctrine: surfaced a new
# defect class → pins the class; values verbatim from the 2026-07-27 run).
HAUGH = {
    "siding_sqft": 2610, "soffit_sqft": 463, "eaves_lf": 184.17,
    "rakes_lf": 136.58, "starter_lf": 304.67,
    "outside_corner_count": 20, "outside_corner_lf": 140.33,
    "inside_corner_count": 6, "inside_corner_lf": 36.92,
    "opening_count": 39, "opening_perimeter_lf": 574.33,
    "window_count": 32, "door_count": 7, "entry_door_count": 3,
    "patio_door_count": 3, "garage_door_count": 1,
    "level_frieze_lf": 215.67, "sloped_frieze_lf": 129.83,
    "drip_edge_lf": 320.75, "overhang_in": 12.0,
    "facade_breakdown": {"siding_sqft": None, "stucco_sqft": 312,
                         "brick_sqft": 234, "stone_sqft": None,
                         "metal_sqft": None, "other_sqft": 2064},
}

DEGREE3_FB = {"siding_sqft": 4504,
              "facade_breakdown": {"siding_sqft": None, "brick_sqft": 265,
                                   "other_sqft": 4239}}


def _flag(flags, code):
    return next((f for f in flags if f.get("code") == code), None)


# ── CLASS A — conservation at intake ─────────────────────────────────────
def test_class_a_haugh_zero_siding_row_never_composes_the_lump():
    m, flags = _hover_mapping_contract(dict(HAUGH), "board_batten")
    assert m["siding_sqft"] == 2064          # wrap-suggested, NOT 2610
    fs = m["_facade_scope"]
    assert fs["mode"] == "label_suggested_wrap"
    assert fs["excluded"] == {"stucco": 312, "brick": 234}
    f = _flag(flags, "facade_scope")
    assert f is not None and "SUGGEST" in f["label"] and "never GOVERN" in f["label"]
    cons = m["_area_conservation"]
    assert cons["measured_total_sqft"] == 2610
    assert cons["sided_sqft"] + cons["excluded_sqft"] + cons["flagged_sqft"] == 2610


def test_class_a_conservation_holds_on_every_intake_shape():
    cases = [
        dict(HAUGH),                                     # zero Siding row
        {"siding_sqft": 4504, "facade_breakdown": DEGREE3_FB["facade_breakdown"]},
        {"siding_sqft": 4239, "facade_breakdown": {"siding_sqft": 4239, "brick_sqft": 265}},
        {"siding_sqft": 2000},                           # no breakdown at all
    ]
    for hm in cases:
        m, flags = _hover_mapping_contract(hm, "lap")
        c = m["_area_conservation"]
        assert round(c["sided_sqft"] + c["excluded_sqft"] + c["flagged_sqft"], 1) \
            == c["measured_total_sqft"], f"ft² leaked at intake: {hm} -> {c}"
        if c["flagged_sqft"] > 0.5:
            assert _flag(flags, "area_conservation") is not None


def test_class_a_explicit_scope_still_governs():
    m, _ = _hover_mapping_contract(dict(HAUGH), "board_batten",
                                   facade_scope={"mode": "custom", "wrap_sqft": 2064,
                                                 "excluded": {"stucco": 312, "brick": 234}})
    assert m["siding_sqft"] == 2064
    assert m["_facade_scope"]["mode"] == "custom"


def test_class_a_3degree_same_anatomy_moves():
    m, flags = _hover_mapping_contract(dict(DEGREE3_FB), "board_batten")
    assert m["siding_sqft"] == 4239          # was 4504 (brick composed silently)
    assert m["_facade_scope"]["excluded"] == {"brick": 265}
    assert _flag(flags, "facade_scope") is not None


# ── CLASS C — labels suggest; opening attribution never inferred ─────────
def test_class_c_opening_attribution_flags_when_unattributable():
    m, flags = _hover_mapping_contract(dict(HAUGH), "board_batten")
    f = _flag(flags, "opening_facade_attribution")
    assert f is not None
    assert "never inferred" in f["label"]
    # counts DO NOT move on a guess — all openings derive until attributed
    assert m["window_count"] == 32 and m["door_count"] == 7


def test_class_c_no_flag_when_report_assigns_openings():
    hm = dict(HAUGH)
    hm["opening_facade_assignments"] = [{"id": "W-101", "facade": "siding"}]
    _, flags = _hover_mapping_contract(hm, "board_batten")
    assert _flag(flags, "opening_facade_attribution") is None


# ── TALL CORNERS — never-average rule (both emitters, pinned equal) ─────
def test_tall_corner_takes_two_sticks_never_averaged():
    base = {"_hover_source": True, "siding_sqft": 2064,
            "outside_corner_count": 14, "outside_corner_lf": 140.33}
    assert _osc_lp_pcs(base) == 14                      # average hides it
    tall = {**base, "_osc_tall_corners_ft": [18.42]}    # taped 18'5"
    assert _osc_lp_pcs(tall) == 15                      # 13×1 + ceil(18.42/16)=2
    pkg = assemble_lp_package(dict(tall))
    osc = next(l for l in pkg["lines"] if l["name"] == OSC_ITEM)
    assert osc["qty"] == 15
    assert "TALL corner" in osc["note"] and "never-average" in osc["note"]


@pytest.mark.parametrize("tall,expected_extra", [([16.5], 1), ([18.42, 33.0], 1 + 2)])
def test_tall_corner_math_both_emitters_identical(tall, expected_extra):
    m = {"_hover_source": True, "outside_corner_count": 14,
         "outside_corner_lf": 140.33, "_osc_tall_corners_ft": tall}
    spec = _osc_lp_pcs(m)
    pkg = assemble_lp_package(dict(m, siding_sqft=2064))
    osc = next(l for l in pkg["lines"] if l["name"] == OSC_ITEM)
    assert spec == osc["qty"] == (14 - len(tall)) + sum(math.ceil(h / 16) for h in tall)


def test_never_average_rule_sealed_text():
    from lp_conventions import NEVER_AVERAGE_RULE
    assert "NEVER averaged" in NEVER_AVERAGE_RULE
    # the Hover flag names the exposure
    _, flags = _hover_mapping_contract(dict(HAUGH), "board_batten")
    cl = _flag(flags, "corner_locators")
    assert "AVERAGE" in cl["label"] and "tall" in cl["label"].lower()


# ── CEILING DEDUP class ──────────────────────────────────────────────────
def test_ceiling_dedup_fold_taped_governs():
    from routes.lp_package_routes import _apply_flag_checklist
    m = {"soffit_sqft": 463.0}
    est = {"lp_flag_checklist": {"ceiling_dedup": {
        "status": "closed", "values": {"duplicate_sqft": 40}}}}
    out = _apply_flag_checklist(m, est, {"source": "hover"})
    assert out["soffit_sqft"] == 423.0
    assert out["_soffit_sqft_hover"] == 463.0 and out["_soffit_dedup_sqft"] == 40


def test_ceiling_dedup_dynamic_flag_when_both_exist():
    from routes.lp_package_routes import _checklist_flags
    run = {"hover_mapping_flags": [],
           "measurements": {"soffit_sqft": 463.0}, "source": "hover"}
    est = {"porch_ceilings": [{"label": "set-back entry", "length_ft": 7.75, "width_ft": 2.0}]}
    flags = _checklist_flags(run, est)
    f = _flag(flags, "ceiling_dedup")
    assert f is not None and f["status"] == "open" and "TAPED governs" in f["label"]
    # no hand entry → no flag
    assert _flag(_checklist_flags(run, {}), "ceiling_dedup") is None


# ── CLASS B — register + detectors, NO number changes (Rider 2) ─────────
def _schema_fields():
    return set(re.findall(r'^\s{2}"(\w+)":', PROMPT_TEMPLATE, re.M))


def test_class_b_every_schema_field_registered():
    missing = _schema_fields() - set(HOVER_FIELD_REGISTER)
    assert not missing, (
        f"NEW/unregistered Hover fields (fail until Howard rules them): {sorted(missing)}")


def test_class_b_registered_fields_exist_in_schema_or_payload():
    stale = set(HOVER_FIELD_REGISTER) - _schema_fields()
    assert not stale, f"register entries with no schema field (dropped field?): {sorted(stale)}"


def test_class_b_consumed_fields_actually_consumed_in_source():
    src = ""
    for p in ("routes/hover.py", "routes/lp_package_routes.py", "lp_package.py",
              "routes/elevation_sheets.py", "routes/estimates.py"):
        src += (Path(__file__).resolve().parent.parent / p).read_text()
    for field, entry in HOVER_FIELD_REGISTER.items():
        if entry["status"] == CONSUMED:
            assert field in src, (
                f"'{field}' registered CONSUMED but no source reads it — "
                "a field stopped being consumed (Class B fails)")
        else:
            assert entry.get("reason"), f"'{field}' not consumed without a named reason"


# ── TEST-ESTIMATE doctrine ───────────────────────────────────────────────
def test_admin_rollup_excludes_test_estimates():
    src = (Path(__file__).resolve().parent.parent / "routes/catalog.py").read_text()
    assert 'startswith("TEST_")' in src


def test_qr_minting_refuses_test_estimates():
    src = (Path(__file__).resolve().parent.parent / "routes/lp_package_routes.py").read_text()
    assert "QR minting refused" in src
