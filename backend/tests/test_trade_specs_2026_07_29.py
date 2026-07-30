"""TRADE SPECS — sealed by Howard 2026-07-29.

A SPEC is the contractor telling the app what he is installing (fascia
width, batten spacing, shake reveal). A CHECK is the app asking the
contractor to verify its own work — not legitimate. Specs: default
applied silently, no gate, no flag — but the MATERIAL LIST PRINTS THE
VALUE ON THE LINE (fascia width changes WHICH SKU gets ordered).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lp_conventions import (DEFAULT_FASCIA_WIDTH_IN, FASCIA_RAKE_ITEM,
                            FASCIA_WIDTHS_IN, batten_takeoff_flags,
                            fascia_item_for_width)
from lp_package import assemble_lp_package
from routes.hover import _build_lines

BATTEN_ITEM = '190 Series Trim 19/32" x 3" x 16\''


def _find(lines, name):
    return next((l for l in lines if l.get("name") == name
                 and l.get("tab") == "lp_smart"), None)


def test_fascia_item_for_width():
    assert FASCIA_WIDTHS_IN == (4, 6, 8, 10, 12)
    assert DEFAULT_FASCIA_WIDTH_IN == 8
    assert fascia_item_for_width(8) == FASCIA_RAKE_ITEM
    assert fascia_item_for_width(None) == FASCIA_RAKE_ITEM
    assert fascia_item_for_width(10) == '440 Series Trim 4/4" x 10" x 16\''
    assert fascia_item_for_width(4) == '440 Series Trim 4/4" x 4" x 16\''
    # invalid width falls back silently to the default
    assert fascia_item_for_width(7) == FASCIA_RAKE_ITEM
    assert fascia_item_for_width("junk") == FASCIA_RAKE_ITEM


def test_fascia_width_prints_on_the_tab_line():
    m = {"eaves_lf": 100.0, "rakes_lf": 50.0, "_fascia_width_in": 10}
    lines = _build_lines(m)
    assert _find(lines, FASCIA_RAKE_ITEM) is None
    row = _find(lines, '440 Series Trim 4/4" x 10" x 16\'')
    assert row is not None
    assert 'fascia width 10"' in row["note"] and "trade spec" in row["note"]
    # default width: original SKU, no spec note appended
    lines8 = _build_lines({"eaves_lf": 100.0, "rakes_lf": 50.0})
    row8 = _find(lines8, FASCIA_RAKE_ITEM)
    assert row8 is not None and "fascia width" not in (row8["note"] or "")


def test_fascia_width_prints_on_the_package_line_single_row():
    m = {"siding_sqft": 1000, "eaves_lf": 100.0, "rakes_lf": 50.0,
         "_fascia_width_in": 6, "_waste_pct": 0.30}
    pkg = assemble_lp_package(m)
    rows = [l for l in pkg["lines"]
            if str(l["name"]).startswith('440 Series Trim 4/4"')]
    assert len(rows) == 1, rows
    assert rows[0]["name"] == '440 Series Trim 4/4" x 6" x 16\''
    assert 'fascia width 6"' in rows[0]["note"]


def test_batten_spacing_default_12_and_delta_named_when_moved():
    base = {"_per_profile_sqft": {"board_batten": 1600}}
    d12 = _find(_build_lines(dict(base)), BATTEN_ITEM)
    # 1600 ÷ 1 = 1600 LF → 100 pcs @ 12" default
    assert d12["qty"] == 100
    assert 'trade spec, default 12"' in d12["note"]
    assert "DELTA" not in d12["note"]
    d16 = _find(_build_lines({**base, "_batten_spacing_in": 16}), BATTEN_ITEM)
    # 1600 ÷ (16/12) = 1200 LF → 75 pcs — delta NAMED explicitly
    assert d16["qty"] == 75
    assert "DELTA vs 12\" default: -25 pcs" in d16["note"]
    d24 = _find(_build_lines({**base, "_batten_spacing_in": 24}), BATTEN_ITEM)
    assert d24["qty"] == 50
    # retired/invalid spacing falls back to the 12" default silently
    d8 = _find(_build_lines({**base, "_batten_spacing_in": 8}), BATTEN_ITEM)
    assert d8["qty"] == 100


def test_batten_spacing_is_a_spec_not_a_flag():
    assert batten_takeoff_flags(None) == []


def test_spec_fields_survive_the_put_model():
    """CLASS CAUGHT BY HOWARD 2026-07-29 (binding audit): a spec field not
    declared on EstimateIn is SILENTLY STRIPPED by the PUT model — the UI
    saves, nothing persists, the derivation never sees it. Every trade
    spec must be a declared, validated model field."""
    from models import EstimateIn
    fields = EstimateIn.model_fields
    assert "batten_spacing_in" in fields
    assert "fascia_width_in" in fields
    assert "shake_reveal_in" in fields
    # PANEL SIZE + WRAP TRIM WIDTH (Howard ruled 2026-07-30) — same class
    assert "panel_size" in fields
    assert "wrap_trim_width_in" in fields
    # bounds enforced at the door
    import pytest
    with pytest.raises(Exception):
        EstimateIn.model_validate({"customer_name": "x", "batten_spacing_in": 8})
    with pytest.raises(Exception):
        EstimateIn.model_validate({"customer_name": "x", "fascia_width_in": 7})
    with pytest.raises(Exception):
        EstimateIn.model_validate({"customer_name": "x", "panel_size": "4x12"})
    with pytest.raises(Exception):
        EstimateIn.model_validate({"customer_name": "x", "wrap_trim_width_in": 5})
    ok = EstimateIn.model_validate(
        {"customer_name": "x", "batten_spacing_in": 16, "fascia_width_in": 10,
         "panel_size": "4x8", "wrap_trim_width_in": 6})
    assert ok.batten_spacing_in == 16 and ok.fascia_width_in == 10
    assert ok.panel_size == "4x8" and ok.wrap_trim_width_in == 6


def test_every_width_variant_sku_binds_to_a_priced_row():
    """DIMENSIONED-SKU CLASS (Howard 2026-07-29): a dimension that is
    selectable but whose SKU does not bind to a price is not actually
    selectable. Binding is normalized-string name match (sheet_norm) —
    fragile by nature, so every emitted width variant is pinned against
    the tier sheet here; a name drift fails the suite."""
    import os
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    from pymongo import MongoClient
    from lp_costs import sheet_norm
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    tier = db.price_tiers.find_one({}, {"_id": 0, "sections": 1})
    assert tier, "no tier sheet seeded"
    sheet_names = {sheet_norm(it.get("name") or "")
                   for sec in tier.get("sections") or []
                   for it in sec.get("items") or []}
    for w in FASCIA_WIDTHS_IN:
        assert sheet_norm(fascia_item_for_width(w)) in sheet_names, \
            f'440 width {w}" SKU does not bind'
        assert sheet_norm(f'540 Series Trim 5/4" x {w}" x 16\'') in sheet_names, \
            f'540 width {w}" SKU does not bind'
