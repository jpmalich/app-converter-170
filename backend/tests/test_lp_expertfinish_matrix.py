"""ExpertFinish availability matrix pins — PUBLISHED-INGESTED 2026-07-13
(lpcorp.com; dealer/BlueLinx verification by Howard pending). Standing
ruling: unsupported combos FLAG, never silently substitute; ambiguity is
a GAP, not an assumption."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lp_colors import EXPERTFINISH_CORE_16, PRIMED, apply_colors
from lp_expertfinish_matrix import check_combo, family_for_item


def test_family_classification():
    assert family_for_item('38 Series Lap 3/8" x 8" x 16\'') == "lap"
    assert family_for_item("LP Starter — field-ripped from siding stock") == "lap"
    assert family_for_item("38 Series Soffit 16 x 16 Vented") == "soffit_12_16"
    assert family_for_item('540 Series OSC 5/4" x 6" x 16\'') == "trim"
    assert family_for_item('440 Series Trim 4/4" x 8" x 16\'') == "trim"
    assert family_for_item("38 Series 4' x 8' Panel") == "panel"
    assert family_for_item("38 Series Vertical Panel") == "vertical"


def test_lap_and_trim_full_core_palette():
    for c in EXPERTFINISH_CORE_16:
        assert check_combo('38 Series Lap 3/8" x 8" x 16\'', c)["status"] == "available"
        assert check_combo('540 Series Trim 5/4" x 4" x 16\'', c)["status"] == "available"


def test_soffit_16_snowscape_only():
    # published: 12"/16" soffit = Snowscape White ONLY
    assert check_combo("38 Series Soffit 16 x 16 Vented", "Snowscape White")["status"] == "available"
    r = check_combo("38 Series Soffit 16 x 16 Vented", "Abyss Black")
    assert r["status"] == "unsupported" and "never silently substituted" in r["note"]


def test_panel_published_vs_ambiguous():
    assert check_combo("38 Series 4' x 8' Panel", "Snowscape White")["status"] == "available"
    assert check_combo("38 Series 4' x 8' Panel", "Garden Sage")["status"] == "gap"
    assert check_combo("38 Series 4' x 8' Panel", "Redwood Red")["status"] == "unsupported"


def test_naturals_are_gaps_everywhere():
    # Naturals per-product availability not published → gap, never assumed
    assert check_combo('38 Series Lap 3/8" x 8" x 16\'', "Weathered Walnut")["status"] == "gap"


def test_primed_always_available():
    assert check_combo("38 Series Soffit 16 x 16 Vented", PRIMED)["status"] == "available"


def test_matrix_is_open_until_dealer_verification_lands():
    """State correction pin: the matrix is NOT closed — Howard's
    dealer-reality verification is pending; entries stay unverified."""
    from lp_expertfinish_matrix import MATRIX_STATUS, VERIFICATION_PENDING
    assert "OPEN" in MATRIX_STATUS and "pending" in MATRIX_STATUS
    joined = " ".join(VERIFICATION_PENDING).lower()
    for item in ("garden sage", "naturals", "shakes/vertical",
                 "trim sizes-per-color", "bluelinx", "stocked-vs-published"):
        assert item in joined
    # trim shows available but carries the pending qualifier in its note
    assert "pending" in check_combo('440 Series Trim 4/4" x 8" x 16\'',
                                    "Snowscape White")["note"]


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
