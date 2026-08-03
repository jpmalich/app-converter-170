"""COLOR TIER DERIVES FROM THE COLOR — PER ROW (Howard ruled 2026-08-02).
The standalone dropdown is retired (one decision, one control — the class
that mislanded 514 lap pieces). Each row follows ITS OWN picker; a
Standard-color corner prices Standard on an Architectural-siding house.
Conquest is STANDARD ONLY. Empty colors move nothing (byte-identical)."""
import re

from routes.hover import _build_lines
from vinyl_color_tiers import (ARCH_BY_BRAND, BOARD_BATTEN_ARCH, SOFFIT_ARCH,
                               apply_row_color_tiers, brand_key_of)


MEAS = {"siding_sqft": 1400.0, "eaves_lf": 120.0, "rakes_lf": 60.0,
        "overhang_in": 12.0, "outside_corner_count": 4,
        "inside_corner_lf": 25.0}

TWO_TONE = {"siding": "Storm", "outside_corner": "Glacier White",
            "accessories": "Glacier White", "soffit_fascia": "Glacier White"}


def _row(lines, tab, prefix):
    return next((l for l in lines if l.get("tab") == tab
                 and str(l.get("name") or "").startswith(prefix)), None)


def test_two_tone_splits_per_row():
    """THE ruling case: architectural siding + white corners on the SAME
    estimate — the siding row re-lands Architectural, the corner row
    prices Standard."""
    lines = _build_lines({**MEAS, "_row_colors": dict(TWO_TONE)})
    siding = _row(lines, "vinyl", "Charter Oak Architectural color Dutch Lap")
    assert siding, "Storm (Charter Oak architectural) must re-land the siding row"
    assert "derived from Storm" in siding["note"]
    assert _row(lines, "vinyl", "Outside corners Standard color"), \
        "white corners stay Standard on the same estimate"
    assert _row(lines, "vinyl", "Soffit & fascia Charter Oak Standard Color"), \
        "white soffit stays Standard"


def test_each_row_follows_its_own_picker():
    """Soffit color drives soffit rows only; accessories color drives
    inside corners / finish trim / J-channel only."""
    lines = _build_lines({**MEAS, "_row_colors": {
        "siding": "Glacier White", "outside_corner": "Glacier White",
        "accessories": "Storm", "soffit_fascia": "Black"}})
    assert _row(lines, "vinyl", "Charter Oak Standard color Dutch Lap")
    assert _row(lines, "vinyl", "Outside corners Standard color")
    assert _row(lines, "vinyl", "Inside Corners (Siding) Architectural color")
    assert _row(lines, "vinyl", "Finish Trim Architectural color")
    assert _row(lines, "vinyl", '3/4" J-Channel Architectural color')
    assert _row(lines, "vinyl", "Soffit & fascia Charter Oak Architectural color")
    assert _row(lines, "vinyl", '3/4" Soffit J-Channel (Charter Oak) Architectural color')


def test_conquest_is_standard_only():
    """RULING 2: Conquest has ONE tier. Storm sits in Conquest's single
    unlabeled palette — on a Conquest row it derives STANDARD, while the
    same color on a Charter Oak row derives Architectural."""
    lines = [{"tab": "vinyl", "qty": 10.0,
              "name": 'Conquest Standard color Clap 4.5" .040', "note": ""}]
    out = apply_row_color_tiers(lines, {"siding": "Storm"})
    assert out[0]["name"] == 'Conquest Standard color Clap 4.5" .040'
    # accessory rows on a Conquest-only job are Standard too (brand-gated)
    lines2 = [{"tab": "vinyl", "qty": 10.0,
               "name": 'Conquest Standard color Clap 4.5" .040', "note": ""},
              {"tab": "vinyl", "qty": 4.0,
               "name": "Outside corners Standard color", "note": ""}]
    out2 = apply_row_color_tiers(lines2, {"outside_corner": "Storm"})
    assert out2[1]["name"] == "Outside corners Standard color"


def test_empty_or_standard_colors_move_nothing():
    """Byte-identical class: tier is unreachable-by-accident."""
    base = _build_lines(dict(MEAS))
    assert base == _build_lines({**MEAS, "_row_colors": {}})
    all_std = _build_lines({**MEAS, "_row_colors": {
        "siding": "Glacier White", "outside_corner": "",
        "accessories": "Maple", "soffit_fascia": "Natural Linen"}})
    assert [l["name"] for l in base] == [l["name"] for l in all_std]


def test_legacy_color_tier_field_is_dead():
    """The retired dropdown's value is IGNORED — no estimate-wide swap."""
    lines = _build_lines({**MEAS, "_color_tier": "architectural"})
    assert _row(lines, "vinyl", "Charter Oak Standard color Dutch Lap")
    assert not any("Architectural" in (l.get("name") or "") for l in lines)


def test_architectural_row_binds_architectural_item_id():
    """Rename runs BEFORE ID stamping — the arch row carries the arch
    identity, not the standard row's id wearing a new name."""
    std = _row(_build_lines(dict(MEAS)), "vinyl", "Charter Oak Standard color Dutch Lap")
    arch = _row(_build_lines({**MEAS, "_row_colors": dict(TWO_TONE)}),
                "vinyl", "Charter Oak Architectural color Dutch Lap")
    assert std.get("item_id") and arch.get("item_id")
    assert std["item_id"] != arch["item_id"]


def test_backend_sets_match_frontend_palettes():
    """SYNC PIN: the pricing sets in vinyl_color_tiers.py mirror the
    dropdown source (colorOptions.js). A color added to one file without
    the other FAILS here — the rot detector."""
    js = open("/app/frontend/src/lib/colorOptions.js").read()

    def collection(label_re, scope=js):
        m = re.search(label_re + r'.*?colors:\s*\[(.*?)\]', scope, re.S)
        assert m, f"palette not found: {label_re}"
        return frozenset(re.findall(r'"([^"]+)"', m.group(1)))

    assert collection(r'label:\s*"Coventry Architectural Color Collection"') == ARCH_BY_BRAND["coventry"]
    assert collection(r'label:\s*"Odyssey Plus Architectural Color Collection"') == ARCH_BY_BRAND["odyssey"]
    assert collection(r'label:\s*"Charter Oak Architectural Color Collection"') == ARCH_BY_BRAND["charter"]
    # multiple palettes reuse the "(premium)" label — scope to the
    # SOFFIT_COLOR_GROUPS block, the one the soffit picker renders
    soffit_block = js[js.index("SOFFIT_COLOR_GROUPS"):]
    assert collection(r'label:\s*"Architectural Color Collection \(premium\)"',
                      soffit_block) == SOFFIT_ARCH
    bb_block = js[js.index("BOARD_BATTEN_COLOR_GROUPS"):js.index("SOFFIT_COLOR_GROUPS")]
    assert collection(r'label:\s*"Architectural Color Collection \(premium\)"',
                      bb_block) == BOARD_BATTEN_ARCH
    # Conquest ships ONE collection — no architectural label exists
    assert 'label: "Conquest Architectural' not in js
    assert "conquest" not in ARCH_BY_BRAND


def test_board_batten_row_follows_its_own_picker():
    """Found during build: the B&B profile row has its own picker
    (board_batten_color) and an Architectural twin — it follows ITS OWN
    picker, never the accessories color."""
    lines = [{"tab": "vinyl", "qty": 12.0,
              "name": 'vertical board and batten Standard color 7"', "note": ""}]
    out = apply_row_color_tiers([dict(l) for l in lines],
                                {"board_batten": "Storm", "accessories": "Glacier White"})
    assert out[0]["name"] == 'vertical board and batten Architectural color 7"'
    out2 = apply_row_color_tiers([dict(l) for l in lines],
                                 {"board_batten": "Glacier White", "accessories": "Storm"})
    assert out2[0]["name"] == 'vertical board and batten Standard color 7"'


def test_brand_key_mirrors_frontend():
    assert brand_key_of('Conquest Standard color Clap 4.5" .040') == "conquest"
    assert brand_key_of('Coventry Standard color Clap 4" .042') == "coventry"
    assert brand_key_of('Odyssey Standard color Clap 4" .044') == "odyssey"
    assert brand_key_of('Charter Oak Standard color Dutch Lap 4.5" .046') == "charter"
    assert brand_key_of("Soffit & fascia Charter Oak Standard Color") is None
    assert brand_key_of("Outside corners Standard color") is None
