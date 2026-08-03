"""CONQUEST PHANTOMS RETIRED (Howard ruled 2026-08-03): Conquest is
STANDARD ONLY. The two priced Architectural Conquest rows were phantoms —
soft-deleted to catalog_retired.py (full records, recoverable). These pins
FAIL the suite if an Architectural Conquest row ever reappears on a live
surface, or if any derivation can bind a tier that brand does not have."""
import catalog_ids
import catalog_seed
from catalog_retired import RETIRED_ROWS


def test_no_architectural_conquest_on_any_live_surface():
    src = open(catalog_seed.__file__.replace(".pyc", ".py")).read()
    assert "'Conquest Architectural" not in src, \
        "an Architectural Conquest row reappeared in catalog_seed.py"
    assert not any("Conquest Architectural" in name
                   for name in catalog_seed.ITEM_META), "ITEM_META phantom"
    assert not any("Conquest Architectural" in name
                   for name in catalog_seed.PER_TIER_PRICES), "price phantom"
    assert not any("Conquest Architectural" in str(k)
                   for k in catalog_ids.ITEM_IDS), "id-register phantom"


def test_built_tiers_carry_no_architectural_conquest():
    """No bump, rename or tier build can bind to the phantoms — they are
    absent from every assembled tier."""
    for tier in ("whole-sale", "Contractor", "Builder-Dealer", "one-opp"):
        for section in catalog_seed.build_tier_sections(tier):
            for item in section.get("items") or []:
                assert "Conquest Architectural" not in (item.get("name") or ""), \
                    f"phantom surfaced in built tier {tier}"


def test_tier_derivation_can_never_emit_architectural_conquest():
    """Conquest resolves to Standard ONLY — the derivation has no
    architectural set for the brand, so no color can swap a Conquest row."""
    from vinyl_color_tiers import ARCH_BY_BRAND, apply_row_color_tiers
    assert "conquest" not in ARCH_BY_BRAND
    every_arch_color = set().union(*ARCH_BY_BRAND.values())
    for color in every_arch_color:
        out = apply_row_color_tiers(
            [{"tab": "vinyl", "qty": 10.0, "note": "",
              "name": 'Conquest Standard color Clap 4.5" .040'}],
            {"siding": color})
        assert out[0]["name"] == 'Conquest Standard color Clap 4.5" .040'


def test_retired_backup_is_recoverable():
    """Soft-delete, not erasure — both records preserved verbatim with
    prices, item numbers and ids, same spirit as the estimate purge."""
    assert len(RETIRED_ROWS) == 2
    names = {r["name"] for r in RETIRED_ROWS}
    assert names == {'Conquest Architectural color Clap 4.5" .040',
                     'Conquest Architectural color Dutch lap 4.5" .040'}
    for r in RETIRED_ROWS:
        assert r["per_tier_prices"]["whole-sale"] == 113.94
        assert r["item_id"].startswith("itm-")
        assert r["item_number"] and r["ruling"]
