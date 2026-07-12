"""Iter 79j.96 — CONFIDENTIAL PRICING pins (BlueLinx PIT00003 basis).
PRICING BASIS RULING: cost keyed by PRODUCT + FINISH; ExpertFinish
selection NEVER falls back to mill. MARGIN RULING: true margin,
sell = cost ÷ (1 − m) — a 25% markup ×1.25 is WRONG. Tiers A30/B25/C20,
B default, admin-only. Cost/margin/tier NEVER on external surfaces."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_costs import (  # noqa: E402
    BLUELINX_COSTS, CONFIDENTIAL_KEYS, DEFAULT_TIER, MARGIN_TIER_SEED,
    cost_for, finish_basis_for_color, price_package, redact_external,
    resolve_margin_pct, sell_price,
)
from lp_package import LAP8_ITEM, STARTER_LINE_NAME, assemble_lp_package  # noqa: E402

CFG = {"tiers": dict(MARGIN_TIER_SEED), "default_tier": DEFAULT_TIER,
       "category_overrides": {}, "line_overrides": {}}

MEAS = {
    "siding_with_openings_sqft": 3000, "siding_sqft": 3000,
    "window_count": 14, "entry_door_count": 1, "patio_door_count": 1,
    "outside_corner_lf": 80, "inside_corner_lf": 24, "starter_lf": 180,
    "eaves_lf": 200, "rakes_lf": 100,
}


def _pkg(colors=None, tier=None):
    p = assemble_lp_package(dict(MEAS), colors=colors)
    return price_package(p, CFG, tier)


def _line(pkg, name):
    return next(l for l in pkg["lines"] if l["name"] == name)


# ── margin formula direction (pinned) ──
def test_sell_is_true_margin_not_markup():
    assert sell_price(75.0, 25.0) == 100.00          # cost ÷ 0.75
    assert sell_price(100.0, 25.0) == 133.33
    assert sell_price(100.0, 25.0) != 125.00         # markup ×1.25 is WRONG


def test_tier_seed_values():
    assert MARGIN_TIER_SEED == {"A": 30.0, "B": 25.0, "C": 20.0}
    assert DEFAULT_TIER == "B"


# ── cost keyed by product + finish ──
def test_cost_keyed_product_plus_finish():
    assert cost_for(LAP8_ITEM, "mill") == 21.69
    assert cost_for(LAP8_ITEM, "expertfinish") == 32.54


def test_no_mill_fallback_for_prefinished():
    # 440 4/4"×8" prints NO ExpertFinish price on the sheet
    assert cost_for("440 Series Trim 4/4\" x 8\" x 16'", "expertfinish") is None
    assert cost_for("440 Series Trim 4/4\" x 8\" x 16'", "mill") == 39.50


def test_name_match_case_tolerant_never_fuzzy():
    assert cost_for("Nickel Gap", "mill") == 50.64   # catalog vs sheet caps
    assert cost_for("Nickel Gap 2", "mill") is None  # no fuzzy invention


def test_finish_basis_from_color():
    assert finish_basis_for_color(None) == "mill"
    assert finish_basis_for_color("Quarry Gray") == "expertfinish"
    assert finish_basis_for_color("Primed (paint any color)") == "pending"


# ── resolution order: line > category > tier ──
def test_override_resolution_order():
    cfg = {"tiers": dict(MARGIN_TIER_SEED), "default_tier": "B",
           "category_overrides": {"LP SmartSide Trim": 22.0},
           "line_overrides": {LAP8_ITEM: 18.0}}
    assert resolve_margin_pct(cfg, "B", LAP8_ITEM, "LP Smart Siding") == 18.0
    assert resolve_margin_pct(cfg, "B", "440 Series Trim 4/4\" x 8\" x 16'",
                              "LP SmartSide Trim") == 22.0
    assert resolve_margin_pct(cfg, "B", "other", "other") == 25.0


# ── package pricing integration ──
def test_mill_pricing_default_tier_b():
    pkg = _pkg()
    lap = _line(pkg, LAP8_ITEM)
    assert lap["cost_basis"] == "mill"
    assert lap["unit_cost"] == 21.69
    assert lap["unit_sell"] == round(21.69 / 0.75, 2)
    assert lap["line_sell"] == round(lap["unit_sell"] * lap["qty"], 2)
    assert lap["pricing_status"] == "priced"
    assert pkg["summary"]["pricing"]["tier"] == "B"


def test_expertfinish_selection_changes_cost_basis():
    pkg = _pkg(colors={"all": "Quarry Gray"})
    lap = _line(pkg, LAP8_ITEM)
    assert lap["cost_basis"] == "expertfinish"
    assert lap["unit_cost"] == 32.54
    assert lap["unit_sell"] == round(32.54 / 0.75, 2)


def test_expertfinish_missing_price_is_pending_never_mill():
    pkg = _pkg(colors={"all": "Quarry Gray"})
    # OSC 5/4"×6" and soffit vented print no ExpertFinish price
    for name in ("540 Series OSC 5/4\" x 6\" x 16'", "38 Series Soffit 16 x 16 Vented"):
        l = _line(pkg, name)
        assert l["pricing_status"] == "pending"
        assert l["unit_sell"] is None
        assert "NEVER falls back to mill" in l["cost_pending_reason"]
        assert "unit_cost" not in l


def test_primed_basis_pending_not_mill():
    pkg = _pkg(colors={"all": "Primed (paint any color)"})
    lap = _line(pkg, LAP8_ITEM)
    assert lap["pricing_status"] == "pending"
    assert "primed" in lap["cost_pending_reason"].lower()


def test_tier_a_and_c_reprice():
    a = _line(_pkg(tier="A"), LAP8_ITEM)
    c = _line(_pkg(tier="C"), LAP8_ITEM)
    assert a["unit_sell"] == round(21.69 / 0.70, 2)
    assert c["unit_sell"] == round(21.69 / 0.80, 2)


def test_starter_priced_from_source_sku_at_siding_color_basis():
    pkg = _pkg(colors={"all": "Quarry Gray"})
    st = _line(pkg, STARTER_LINE_NAME)
    assert st["source_sku"] == LAP8_ITEM
    assert st["cost_basis"] == "expertfinish"       # boards come from siding stock
    assert st["unit_cost"] == 32.54
    assert st["line_cost"] == round(32.54 * st["pieces_added"], 2)
    assert st["priced_unit"] == "per ripped source board"


def test_summary_totals_internal():
    pkg = _pkg()
    pr = pkg["summary"]["pricing"]
    priced = [l for l in pkg["lines"] if l.get("pricing_status") == "priced"]
    assert pr["priced_lines"] == len(priced)
    assert pr["total_cost"] == round(sum(l["line_cost"] for l in priced), 2)
    assert pr["total_sell"] == round(sum(l["line_sell"] for l in priced), 2)
    assert pr["total_sell"] > pr["total_cost"]


# ── REDACTION: cost never leaves the server on external surfaces ──
def _assert_no_confidential(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert k not in CONFIDENTIAL_KEYS, f"confidential key '{k}' at {path}"
            _assert_no_confidential(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_no_confidential(v, f"{path}[{i}]")


def test_external_redaction_strips_all_confidential_keys():
    ext = redact_external(_pkg(colors={"all": "Quarry Gray"}))
    _assert_no_confidential(ext)
    lap = next(l for l in ext["lines"] if l["name"] == LAP8_ITEM)
    assert lap["unit_sell"] == round(32.54 / 0.75, 2)   # sell survives
    assert lap["pricing_status"] == "priced"
    assert "total_sell" in ext["summary"]["pricing"]
    assert "total_cost" not in ext["summary"]["pricing"]
    assert "tier" not in ext["summary"]["pricing"]


def test_confidential_keys_cover_cost_margin_tier_and_provenance():
    for k in ("unit_cost", "line_cost", "total_cost", "cost_basis", "margin_pct",
              "tier", "tier_pct", "tiers", "quote_ref", "cost_pending_reason"):
        assert k in CONFIDENTIAL_KEYS


def test_every_bluelinx_row_has_a_mill_or_expertfinish_price():
    for name, prices in BLUELINX_COSTS.items():
        assert prices, name
        assert all(v > 0 for v in prices.values()), name
