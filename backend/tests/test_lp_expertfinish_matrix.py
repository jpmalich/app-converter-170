"""ExpertFinish availability matrix pins — DEALER-VERIFIED (Howard,
incl. BlueLinx cross-check): matrix is dealer-true, 'available' =
orderable. Standing ruling: unsupported combos FLAG, never silently
substitute; ambiguity is a GAP, not an assumption."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lp_colors import EXPERTFINISH_CORE_16, NATURALS_COLLECTION, PRIMED, apply_colors
from lp_expertfinish_matrix import (
    MATRIX_STATUS,
    NATURALS_CATALOG_PENDING,
    NATURALS_PROFILES,
    check_combo,
    family_for_item,
)


def test_family_classification():
    assert family_for_item('38 Series Lap 3/8" x 8" x 16\'') == "lap"
    assert family_for_item("LP Starter — field-ripped from siding stock") == "lap"
    assert family_for_item("38 Series Soffit 16 x 16 Vented") == "soffit_12_16"
    assert family_for_item('540 Series OSC 5/4" x 6" x 16\'') == "trim"
    assert family_for_item('440 Series Trim 4/4" x 8" x 16\'') == "trim"
    assert family_for_item("38 Series 4' x 8' Panel") == "panel"
    assert family_for_item("38 Series Vertical Panel") == "vertical"


def test_matrix_is_dealer_verified():
    assert "dealer-verified" in MATRIX_STATUS
    assert "pending" not in MATRIX_STATUS.lower()


def test_lap_and_trim_full_core_palette():
    for c in EXPERTFINISH_CORE_16:
        assert check_combo('38 Series Lap 3/8" x 8" x 16\'', c)["status"] == "available"
        assert check_combo('540 Series Trim 5/4" x 4" x 16\'', c)["status"] == "available"


def test_shakes_and_vertical_regional_flags_cleared():
    # Ruling 3: all ExpertFinish colors, all regions — no gaps left
    for c in EXPERTFINISH_CORE_16:
        assert check_combo("Shake", c)["status"] == "available"
        assert check_combo("38 Series Vertical Panel", c)["status"] == "available"


def test_soffit_16_snowscape_only():
    # published: 12"/16" soffit = Snowscape White ONLY (unchanged by rulings)
    assert check_combo("38 Series Soffit 16 x 16 Vented", "Snowscape White")["status"] == "available"
    r = check_combo("38 Series Soffit 16 x 16 Vented", "Abyss Black")
    assert r["status"] == "unsupported" and "never silently substituted" in r["note"]


def test_panel_garden_sage_resolved_available():
    # Ruling 1: Garden Sage is real and available on panels
    assert check_combo("38 Series 4' x 8' Panel", "Snowscape White")["status"] == "available"
    assert check_combo("38 Series 4' x 8' Panel", "Garden Sage")["status"] == "available"
    assert check_combo("38 Series 4' x 8' Panel", "Redwood Red")["status"] == "unsupported"


def test_naturals_exact_profile_list():
    # Ruling 2: Naturals run in EXACTLY the authoritative profile list
    assert len(NATURALS_PROFILES) == 11
    for prof in ('38 Series Lap 3/8" x 8" x 16\'', "Nickel Gap",
                 '540 Series Trim 5/4" x 12" x 16\'', "38 Series Vertical Panel"):
        assert check_combo(prof, "Weathered Walnut")["status"] == "available"
    # starter follows the lap stock it is ripped from
    assert check_combo("LP Starter — field-ripped from siding stock",
                       "Weathered Walnut")["status"] == "available"
    # outside the list → unsupported (not gap)
    for prof in ("Shake", "38 Series 4' x 8' Panel",
                 "38 Series Soffit 16 x 16 Vented",
                 '440 Series Trim 4/4" x 8" x 16\''):
        r = check_combo(prof, "Weathered Walnut")
        assert r["status"] == "unsupported", prof
        assert "never silently substituted" in r["note"]


def test_naturals_catalog_pending_cleared_after_readd():
    # 2026-06 ruling: 16x16 Closed re-added to the catalog → the pending
    # set is empty and Naturals on it is plainly available
    assert NATURALS_CATALOG_PENDING == frozenset()
    r = check_combo("38 Series Soffit 16 x 16 Closed", "Bonsai Black")
    assert r["status"] == "available"
    assert "dealer-verified" in r["note"]


def test_naturals_profiles_quotable_or_flagged():
    """Ruled catalog cross-check: every Naturals-scoped profile is either
    in the LP catalog (quotable) or in NATURALS_CATALOG_PENDING."""
    import catalog_seed
    names = set()
    for sec in catalog_seed.DEFAULT_SECTIONS:
        for it in sec.get("items", []):
            names.add(it["name"] if isinstance(it, dict) else it)
    for prof in NATURALS_PROFILES:
        assert prof in names or prof in NATURALS_CATALOG_PENDING, (
            f"'{prof}' is Naturals-scoped but neither quotable nor flagged pending")


def test_primed_always_available():
    assert check_combo("38 Series Soffit 16 x 16 Vented", PRIMED)["status"] == "available"


def test_apply_colors_flags_unsupported_never_substitutes():
    lines = [
        {"name": "38 Series Soffit 16 x 16 Vented", "section": "LP SmartSide Soffit"},
        {"name": '38 Series Lap 3/8" x 8" x 16\'', "section": "LP Smart Siding"},
    ]
    _, errors = apply_colors(lines, {"all": "Abyss Black"})
    assert errors == []
    soffit, lap = lines
    # color kept as requested (never substituted), flagged unsupported
    assert soffit["color"] == "Abyss Black"
    assert soffit["color_status"] == "unsupported"
    assert any("UNSUPPORTED COMBINATION" in f for f in soffit["color_flags"])
    # lap in the same color is clean
    assert lap["color_status"] == "available"
    assert "color_flags" not in lap


def test_all_naturals_colors_share_the_profile_scoping():
    for c in NATURALS_COLLECTION:
        assert check_combo("Nickel Gap", c)["status"] == "available"
        assert check_combo("Shake", c)["status"] == "unsupported"
