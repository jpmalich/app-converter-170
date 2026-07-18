"""Vinyl-conventions batch (3+4+5), ruled 2026-07-18 — region/context split.

PINS:
- no pooled J on multi-region jobs
- no starter on B&B compositions ever
- shake starter #65516000 never prices as clap (own product; pricing
  pending Howard's master-catalog diff approval)
- clap starter keeps 12'6" (÷ 12.5)
- single-profile jobs keep today's pooled behavior (regression)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from routes.hover import (  # noqa: E402
    _region_split_active, _region_context_lines, _build_lines,
    HOVER_MAPPING_SPEC,
)
import catalog_seed  # noqa: E402

MIXED = {
    "siding_sqft": 2068, "eaves_lf": 108, "rakes_lf": 69.6, "starter_lf": 165,
    "window_count": 10, "entry_door_count": 1, "patio_door_count": 1,
    "garage_door_count": 0, "opening_perimeter_lf": 574.33,
    "_per_profile_sqft": {"lap": 1840, "shake": 168, "board_batten": 60},
    "_per_profile_base_lf": {"lap": 130, "board_batten": 22},
    "_per_profile_gable_break_lf": {"shake": 38},
}
SINGLE = {
    "siding_sqft": 2068, "eaves_lf": 108, "rakes_lf": 69.6, "starter_lf": 165,
    "window_count": 10, "entry_door_count": 1, "patio_door_count": 1,
    "garage_door_count": 0, "opening_perimeter_lf": 574.33,
}


def _vinyl(lines):
    return [l for l in lines if l.get("tab") == "vinyl"]


def test_split_activates_only_on_multi_region():
    assert _region_split_active(MIXED) is True
    assert _region_split_active(SINGLE) is False
    assert _region_split_active({**SINGLE, "_per_profile_sqft": {"lap": 2068}}) is False


def test_no_pooled_j_or_starter_or_ft_on_multi_region():
    names = [l["name"] for l in _vinyl(_build_lines(MIXED))]
    assert "Starter" not in names
    assert '3/4" J-Channel Standard color (2 per Sq of siding)' not in names
    assert "Finish Trim Standard color" not in names


def test_no_starter_on_bb_ever_and_base_is_j():
    lines = {l["name"]: l for l in _region_context_lines(MIXED)}
    assert not any("board_batten" in n and n.startswith("Starter") for n in lines)
    bb = lines['3/4" J-Channel Standard color — B&B base']
    assert bb["qty"] == 2  # 22 LF ÷ 12.5 → 2
    assert "NO starter" in bb["note"]
    assert "product color" in bb["note"]


def test_shake_starter_own_product_never_clap():
    lines = {l["name"]: l for l in _region_context_lines(MIXED)}
    sh = lines["Pelican Bay Shake Starter — shake region"]
    assert sh["base_item"] == "Pelican Bay Shake Starter"
    assert sh["base_item"] != "Starter"
    assert sh["qty"] == 4  # 38 LF gable break ÷ 12.5 → 4
    assert "65516000" in sh["note"]
    assert "never priced as clap" in sh["note"]


def test_clap_starter_keeps_12_6_and_door_deduction():
    lines = {l["name"]: l for l in _region_context_lines(MIXED)}
    clap = lines["Starter — lap body"]
    # base 130+22+... total_base = 152; door_ded = 0 (152 < 165 → no ded)
    # clap net = 130 → ceil(130/12.5) = 11
    assert clap["qty"] == 11
    assert "12'6\"" in clap["note"]
    assert clap["base_item"] == "Starter"


def test_j_and_ft_context_split_with_region_colors():
    lines = {l["name"]: l for l in _region_context_lines(MIXED)}
    assert '3/4" J-Channel Standard color — window/door' in lines
    rg = lines['3/4" J-Channel Standard color — rake/gable']
    assert rg["qty"] == 6  # 69.6 ÷ 12.5 → 6
    assert "shake gable region" in rg["note"]
    assert "Finish Trim Standard color — eave run" in lines
    assert "Finish Trim Standard color — window perimeter" in lines


def test_single_profile_keeps_pooled_rows_regression():
    names = [l["name"] for l in _vinyl(_build_lines(SINGLE))]
    assert "Starter" in names
    assert '3/4" J-Channel Standard color (2 per Sq of siding)' in names
    assert "Finish Trim Standard color" in names
    assert not any("—" in n and ("body" in n or "region" in n) for n in names)


def test_missing_base_lf_never_pools_silently():
    m = {**MIXED, "_per_profile_base_lf": {}, "_per_profile_gable_break_lf": {}}
    lines = {l["name"]: l for l in _region_context_lines(m)}
    sh = lines["Pelican Bay Shake Starter — shake region"]
    bb = lines['3/4" J-Channel Standard color — B&B base']
    assert sh["qty"] == 0 and "⚠" in sh["note"]
    assert bb["qty"] == 0 and "⚠" in bb["note"]
    clap = lines["Starter — lap body"]
    assert clap["qty"] == 14  # whole-house 165 ÷ 12.5 fallback, noted
    assert "older run" in clap["note"]


def test_catalog_shake_starter_pricing_pending_pin():
    assert "Pelican Bay Shake Starter" in catalog_seed.ITEM_AMI
    assert catalog_seed.ITEM_AMI["Pelican Bay Shake Starter"] == "65516000"
    # pricing pending: NOT in any price dict (mat seeds 0); never clap's 7.64
    src = Path(catalog_seed.__file__).read_text()
    assert "'Pelican Bay Shake Starter': 7.64" not in src
    assert '"Pelican Bay Shake Starter": 7.64' not in src


def test_stale_div10_comment_synced():
    src = (Path(__file__).resolve().parents[1] / "routes/hover.py").read_text()
    assert "LF ÷ 10 (per Howard)" not in src
    assert 'clap' in src and "12'6" in src
