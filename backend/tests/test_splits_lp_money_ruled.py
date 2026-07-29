"""SPLITS → LP MONEY, RULED A/B/C (Howard 2026-07-26). §6 test-plan order.

A — per-family mapping + CONSERVATION invariant (mandatory gate) +
    byte-identical fixture bar (single-family runs bypass the split path
    by construction; the existing Letrick/Casile pins in this suite ARE
    the acceptance bar and must stay green).
B — as-shake toggles are an alias over the breakdown; flat ceil(sqft/4)
    math retired; equivalence pin mandatory.
C — CORRECTED family waste table (sealed 2026-07-24): lap/soffit 10 ·
    shake 15 · board&batten/vertical 30 (Casile 68-panel walk) ·
    nickel gap 12. The visible estimate field governs only its own
    (selected) family in a split.
"""
import math
from pathlib import Path

import lp_smartside_formulas as lpf
from lp_conventions import FAMILY_WASTE_DEFAULTS, family_waste_default_pct
from lp_package import _conserve_per_profile
from routes.hover import _build_lines, _lp_profile_sku_entry

FE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
AIBTN = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()


# ── §6.1 conservation ────────────────────────────────────────────────
def test_conservation_residue_to_default_family():
    m = {"siding_sqft": 1000.0, "_default_family": "lap",
         "_per_profile_sqft": {"lap": 600.0, "shake": 300.0}}
    out = _conserve_per_profile(m)
    per = out["_per_profile_sqft"]
    assert per == {"lap": 700.0, "shake": 300.0}
    assert abs(sum(per.values()) - 1000.0) < 0.01
    assert "residue" in out["_profile_conservation_note"]


def test_conservation_negative_residue_absorbed_by_default():
    m = {"siding_sqft": 1000.0, "_default_family": "lap",
         "_per_profile_sqft": {"lap": 800.0, "shake": 400.0}}
    per = _conserve_per_profile(m)["_per_profile_sqft"]
    assert per == {"lap": 600.0, "shake": 400.0}
    assert abs(sum(per.values()) - 1000.0) < 0.01


def test_conservation_proportional_scale_when_default_exhausted():
    m = {"siding_sqft": 1000.0, "_default_family": "lap",
         "_per_profile_sqft": {"lap": 20.0, "shake": 1200.0}}
    out = _conserve_per_profile(m)
    per = out["_per_profile_sqft"]
    assert abs(sum(per.values()) - 1000.0) < 0.05
    assert per["shake"] < 1200.0 and per["lap"] < 20.0
    assert "scaled proportionally" in out["_profile_conservation_note"]


def test_conservation_single_family_noop_fixture_bar():
    # single positive family (every locked fixture today) → untouched dict
    m = {"siding_sqft": 2099.7, "_default_family": "lap",
         "_per_profile_sqft": {"lap": 1780.5}}
    assert _conserve_per_profile(m) is m


# ── §6.3 waste by family (ruling C, corrected) ───────────────────────
def test_sealed_family_waste_table():
    assert FAMILY_WASTE_DEFAULTS.get("lap") == 10
    assert FAMILY_WASTE_DEFAULTS.get("shake") == 15
    assert FAMILY_WASTE_DEFAULTS.get("board_batten") == 30
    assert FAMILY_WASTE_DEFAULTS.get("nickel_gap") == 12
    # the 2026-07-16 registry value is superseded — never 10 for B&B again
    assert lpf.BB_RULED_FINAL["panel_waste_default"] == 0.30


def _family_line(lines, needle):
    return next(l for l in lines if l["tab"] == "lp_smart" and needle in l["name"].lower())


def test_split_lines_use_family_waste_not_field():
    meas = {
        "siding_sqft": 1800.0,
        "_default_family": "lap",
        "_waste_pct": 0.20,  # contractor edited the visible field
        "_per_profile_sqft": {"lap": 1000.0, "board_batten": 500.0,
                              "shake": 200.0, "nickel_gap": 100.0},
    }
    with lpf.override_flag(True):
        lines = _build_lines(meas)
        expected = {}
        for fam, sqft in meas["_per_profile_sqft"].items():
            entry = _lp_profile_sku_entry(fam)
            w = 0.20 if fam == "lap" else family_waste_default_pct(fam) / 100.0
            expected[fam] = lpf.pieces_needed(sqft, entry[2], w)
    assert _family_line(lines, "lap")["qty"] == expected["lap"]
    assert _family_line(lines, "panel")["qty"] == expected["board_batten"]
    assert _family_line(lines, "shake")["qty"] == expected["shake"]
    assert _family_line(lines, "nickel gap")["qty"] == expected["nickel_gap"]
    # provenance: non-selected families carry the family-default note
    # (wording de-doctrined 2026-07-29 — plain trade language in the UI)
    assert "family default" in _family_line(lines, "panel")["note"]
    assert "family default" not in _family_line(lines, "lap")["note"]


def test_single_family_field_governs_unchanged():
    # Casile-class: one family → the visible field governs, note untouched
    meas = {"siding_sqft": 2064.0, "_default_family": "board_batten",
            "_waste_pct": 0.30, "_force_profile_lines": True,
            "_per_profile_sqft": {"board_batten": 2064.0}}
    with lpf.override_flag(True):
        lines = _build_lines(meas)
        entry = _lp_profile_sku_entry("board_batten")
        expected = lpf.pieces_needed(2064.0, entry[2], 0.30)
    row = _family_line(lines, "panel")
    assert row["qty"] == expected == 68  # the sealed 68-panel walk
    assert "family default" not in row["note"]


# ── §6.4 unknown family flag ─────────────────────────────────────────
def test_unknown_family_flags_never_prices():
    meas = {"siding_sqft": 1150.0, "_default_family": "lap",
            "_waste_pct": 0.10,
            "_per_profile_sqft": {"lap": 1000.0, "unknown": 150.0}}
    with lpf.override_flag(True):
        lines = _build_lines(meas)
    flag = next(l for l in lines if l["name"] == "UNCLASSIFIED SIDING PROFILE")
    assert flag["qty"] == 0
    assert "never priced by guess" in flag["note"]


# ── §6.5 as-shake alias equivalence (ruling B) ───────────────────────
def test_flat_swap_math_retired():
    assert "swapSidingToShake" not in AIBTN
    assert "Math.ceil(swapSqft / 4)" not in AIBTN
    assert "shakeSku" not in AIBTN  # SKU pickers retired with the flat math


def test_alias_mutates_breakdown_and_rederives():
    assert 'e[`${kind}_profile`] = "shake"' in AIBTN
    assert 'api.post("/measure/map", { measurements: newMeas })' in AIBTN
    # equivalence by construction: identical breakdown mutation +
    # identical mapper call as a hand-set profile — pinned as strings
    assert "toggle ≡ hand-set profile" in AIBTN
