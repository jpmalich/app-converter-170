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


# ── CLASS A — conservation at intake · SEALED DEFAULT COMPOSES (Howard,
# 2026-07-28 production restore): wall classes side, masonry classes
# exclude with the reason named, unrecognized labels SIDE and flag loudly.
# FLAGGED means WE MADE A CALL AND TOLD THE USER — the "no call made, no
# material produced" fourth state is RETIRED (it zeroed the vinyl door). ──
def test_class_a_haugh_zero_siding_row_never_composes_the_lump():
    m, flags = _hover_mapping_contract(dict(HAUGH), "board_batten")
    assert m["siding_sqft"] == 2064          # composed default, NOT 2610
    fs = m["_facade_scope"]
    assert fs["mode"] == "composed_default"
    assert fs["excluded"] == {"stucco": 312, "brick": 234}
    f = _flag(flags, "facade_scope")
    assert f is not None
    assert "COMPOSED AT IMPORT" in f["label"]
    assert "never a gate" in f["label"]
    assert "masonry" in f["label"]           # exclusion reason NAMED
    cons = m["_area_conservation"]
    assert cons["measured_total_sqft"] == 2610
    assert cons["sided_sqft"] + cons["excluded_sqft"] + cons["flagged_sqft"] == 2610
    assert cons["flagged_sqft"] == 0         # every ft² attributed AT IMPORT


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


# ── PRODUCTION RESTORE (Howard, 2026-07-28) — the sealed default COMPOSES
# on the SHARED Hover door; a fresh VINYL import fills siding again. ──────
DEGREE3_MORNING = {
    # verbatim anatomy of the 2026-07-28 12:39 UTC production run that
    # came back with NO siding line: extractor followed the pinned
    # "Siding row only" rule and returned a top-level zero.
    "siding_sqft": 0, "siding_with_openings_sqft": 0,
    "eaves_lf": 308.25, "rakes_lf": 319.42, "starter_lf": 654.67,
    "outside_corner_count": 26, "outside_corner_lf": 175.42,
    "window_count": 30, "door_count": 5, "entry_door_count": 4,
    "opening_perimeter_lf": 535.08, "soffit_sqft": 2620, "overhang_in": 12.0,
    "facade_breakdown": {"siding_sqft": None, "stucco_sqft": None,
                         "brick_sqft": 265, "stone_sqft": None,
                         "metal_sqft": None, "other_sqft": 4239},
}


def test_restore_known_truth_defaults():
    """Howard's known-truth check: the default yields 2,064 ft² on 261
    Haugh and 4,239 ft² on 3 Degree Rd with nobody touching anything."""
    from lp_conventions import compose_default_facade_scope
    assert compose_default_facade_scope(HAUGH["facade_breakdown"])["wrap_sqft"] == 2064
    assert compose_default_facade_scope(DEGREE3_MORNING["facade_breakdown"])["wrap_sqft"] == 4239


def test_restore_worker_door_composes_into_measurements():
    from routes.hover import _compose_facade_default_into
    m = dict(DEGREE3_MORNING)
    scope = _compose_facade_default_into(m)
    assert scope is not None
    assert m["siding_sqft"] == 4239
    assert m["_siding_sqft_report"] == 0     # report figure preserved
    assert m["_facade_scope"]["excluded_reasons"]["brick"].startswith("masonry")
    c = m["_area_conservation"]
    assert c["sided_sqft"] + c["excluded_sqft"] + c["flagged_sqft"] == c["measured_total_sqft"]
    assert c["flagged_sqft"] == 0


def test_restore_vinyl_and_ascend_siding_lines_fill():
    """FRESH-DOOR pin: the exact code path a fresh import runs (worker
    composition → _build_lines) produces vinyl AND ascend siding rows
    with real quantities — never an empty siding section."""
    from routes.hover import _compose_facade_default_into, _build_lines
    m = dict(DEGREE3_MORNING)
    _compose_facade_default_into(m)
    lines = _build_lines(m)
    vinyl = next(l for l in lines if l["tab"] == "vinyl"
                 and l["section"] == "Vinyl Siding")
    ascend = next(l for l in lines if l["tab"] == "ascend"
                  and l["section"] == "Ascend Cladding")
    assert vinyl["qty"] == pytest.approx(42.4, abs=0.05)   # 4239 ÷ 100
    assert ascend["qty"] == pytest.approx(42.4, abs=0.05)
    lp = next(l for l in lines if l["tab"] == "lp_smart"
              and l["name"].startswith("38 Series Lap"))
    assert lp["qty"] > 0


def test_restore_consistent_report_untouched():
    """Pure-vinyl house whose Facades table agrees with the top level:
    composition is a no-op — swo (+10% openings adder) keeps composing."""
    from routes.hover import _compose_facade_default_into
    m = {"siding_sqft": 3000, "siding_with_openings_sqft": 3300,
         "facade_breakdown": {"siding_sqft": 3000}}
    _compose_facade_default_into(m)
    assert m["siding_sqft"] == 3000
    assert m["siding_with_openings_sqft"] == 3300
    assert "_siding_sqft_report" not in m


def test_restore_unrecognized_label_sides_and_flags_loudly():
    """Howard's invariant: if a facade cannot be attributed at all, SIDE
    IT and flag loudly — a short load costs a contractor a day; an extra
    bundle goes back on the truck."""
    from lp_conventions import compose_default_facade_scope, facade_scope_flag_label
    scope = compose_default_facade_scope({"wood_sqft": 500, "brick_sqft": 100})
    assert scope["wrap_sqft"] == 500         # SIDED, not zeroed
    assert scope["unrecognized_sided"] == ["wood"]
    label = facade_scope_flag_label(scope)
    assert "UNRECOGNIZED" in label and "SIDED by rule" in label


def test_restore_flag_is_informational_never_a_gate():
    """The flag rides WITH a composed siding figure — it never holds the
    area at zero."""
    m, flags = _hover_mapping_contract(dict(DEGREE3_MORNING), "lap")
    assert m["siding_sqft"] == 4239
    f = _flag(flags, "facade_scope")
    assert f is not None and "never a gate" in f["label"]


# ── CLASS C — labels suggest; opening attribution never inferred ─────────
def test_class_c_opening_attribution_flags_when_unattributable():
    m, flags = _hover_mapping_contract(dict(HAUGH), "board_batten")
    f = _flag(flags, "opening_facade_attribution")
    assert f is not None
    assert "not assigned to a wall" in f["label"]  # wording de-doctrined 2026-07-29
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
    assert "TALL corner" in osc["note"] and "never the average" in osc["note"]


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
    assert "average" in cl["label"] and "tall" in cl["label"].lower()  # wording de-doctrined 2026-07-29


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


def test_class_b_published_field_register():
    """MOVED UP (Howard, 2026-07-28): 'five confirmed dropped fields is
    not a queue item any more.' Every figure the Hover REPORT publishes
    maps to a schema key AND a consumption ruling — the detector that
    catches the next dropped field at once instead of one-at-a-time."""
    from hover_field_register import HOVER_PUBLISHED_FIELDS
    schema = _schema_fields()
    no_schema = {label: key for label, key in HOVER_PUBLISHED_FIELDS.items()
                 if key not in schema}
    assert not no_schema, (
        f"PUBLISHED figures with no extraction key (the dropped-field class): {no_schema}")
    unruled = sorted(k for k in HOVER_PUBLISHED_FIELDS.values()
                     if k not in HOVER_FIELD_REGISTER)
    assert not unruled, f"published fields without a consumption ruling: {unruled}"
    # the two caught 2026-07-28 stay pinned by name
    assert "footprint_perimeter_ft" in HOVER_FIELD_REGISTER
    assert "footprint_area_sqft" in HOVER_FIELD_REGISTER


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
