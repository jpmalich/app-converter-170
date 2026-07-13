"""Iter 79j.93/.94 — September LP package assembly pins.
Ruled LP trim system: OSC whole-sticks-per-location; 440 4/4"×4" per ISC
location; 440 4/4"×8" fascia+rake; composition guard (J/finish trim/coil
= composition bugs on LP-native); pendings flagged never defaulted."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_conventions import FASCIA_RAKE_ITEM, ISC_TRIM_ITEM  # noqa: E402
from lp_package import (  # noqa: E402
    OSC_ITEM, STARTER_LINE_NAME, assemble_lp_package, corner_sticks_for_length,
    isc_from_corner_locations, osc_from_corner_locations,
)

LETRICK_HEIGHTS = {"front": 8.5, "back": 10.3, "left": 8.3, "right": 8.5}


def _loc(walls, tier="confirmed", elevated=False, ctype="outside"):
    return {"type": ctype, "walls": walls, "tier": tier, "elevated": elevated}


def _letrick_locations():
    # locators mirror real run payloads — C4 feature grouping keys off
    # the appendage marker ("chase"/"chimney") in the locator text
    return [
        _loc(["front", "left"]),
        _loc(["front", "right"]),
        _loc(["back", "left"]),
        _loc(["back", "right"]),
        {**_loc(["back"]), "locator": "chimney chase front-left edge"},
        {**_loc(["back"]), "locator": "chimney chase front-right edge"},
        {**_loc(["back"], tier="unconfirmed"), "locator": "chimney chase drift residual"},
        {**_loc(["back"], ctype="inside"), "locator": "chase left junction"},
        {**_loc(["back"], ctype="inside", tier="unconfirmed"), "locator": "chase right junction"},
    ]


MEAS = {"siding_sqft": 1832.7, "outside_corner_lf": 37.6, "inside_corner_lf": 40.0,
        "_ai_avg_wall_height_ft": 8.9, "eaves_lf": 108.0, "rakes_lf": 73.4,
        "opening_count": 12, "window_count": 10, "entry_door_count": 2,
        "opening_perimeter_lf": 219.3, "starter_lf": 168.0}


def test_osc_feature_pooled_sticks():
    # C4 RULED (2026-07-13, supersedes whole-stick-per-location): house
    # corners are singleton features (1 stick each ≤16'); the chase's 3
    # edges pool as ONE feature: 3 × 10.3 = 30.9 → ceil(30.9/16) = 2.
    # 4 + 2 = 6 (per-location stick-starts rejected doctrine).
    osc = osc_from_corner_locations(
        [l for l in _letrick_locations() if l["type"] == "outside"], LETRICK_HEIGHTS, 8.9)
    assert osc["osc_count"] == 7
    assert osc["qty"] == 6
    assert osc["amber"] == 1
    assert "CONFIRMED" in osc["note"]  # 16' (192") stick length ruled
    assert "field verify" in osc["note"]


def test_osc_over_stick_splice_and_round_up_pooled():
    # RULED (uniform splice, reaffirmed by C4): two 18.5' chase corners
    # = one feature = 2 full sticks + ceil(5/16) = 3, not 4
    osc = osc_from_corner_locations(
        [{**_loc(["back"]), "locator": "chase edge A"},
         {**_loc(["back"]), "locator": "chase edge B"}], {"back": 18.5}, 8.9)
    assert osc["qty"] == 3  # not 4 (full-stick-per-segment rejected)
    assert "splice-and-round-up" in osc["note"]


def test_osc_chimney_key_fixture_c4():
    # Sealed-key chimney (C4 acceptance): 2 full-height 18.91' edges +
    # 2 above-roofline ~8.59' edges pool as one appendage feature:
    # 1+1 full + ceil((2.91+2.91+8.59+8.59)/16) = 2+2 = 4 sticks.
    from lp_package import corner_sticks_for_length
    assert corner_sticks_for_length([18.91, 18.91, 8.59, 8.59], 16.0) == 4


def test_isc_sticks_per_location():
    isc = isc_from_corner_locations(_letrick_locations(), LETRICK_HEIGHTS, 8.9)
    assert isc["isc_count"] == 2
    assert isc["qty"] == 2
    assert isc["amber"] == 1


def test_osc_inside_corners_never_counted():
    assert osc_from_corner_locations(
        [_loc(["back"], ctype="inside")], LETRICK_HEIGHTS, 8.9) is None


def test_osc_elevated_flagged_full_wall_height():
    osc = osc_from_corner_locations(
        [_loc(["left"], tier="unconfirmed", elevated=True)], LETRICK_HEIGHTS, 8.9)
    assert osc["elevated"] == 1
    assert "full wall height" in osc["note"]


def test_assemble_ruled_trim_system():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    by = {l["name"]: l for l in pkg["lines"]}
    assert by[OSC_ITEM]["qty"] == 6  # C4 feature pooling (4 house + chase 2)
    # 440 4/4"×4" is ISC-only now (horizontal runs superseded by 4/4"×8")
    assert by[ISC_TRIM_ITEM]["qty"] == 2
    assert "ISC locations" in by[ISC_TRIM_ITEM]["note"]
    # 440 4/4"×8" fascia + rake (C4 waste-scope: no % waste on stick-count
    # lines): (108 + 73.4) = 181.4 ÷ 16 = 11.34 → 12
    assert by[FASCIA_RAKE_ITEM]["qty"] == 12
    assert "splice-and-round-up total sticks (ruled" in by[FASCIA_RAKE_ITEM]["note"]
    assert pkg["summary"]["osc_source"] == "c3_corner_locations"


def test_lp_soffit_eaves_only_per_system_table():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    names = {l["name"] for l in pkg["lines"]}
    assert "38 Series Soffit 16 x 16 Closed" not in names  # rake soffit = cross-system on LP
    vented = next(l for l in pkg["lines"] if l["name"] == "38 Series Soffit 16 x 16 Vented")
    assert "eaves only" in vented["note"]
    assert any("rake boards" in s for s in pkg["summary"]["system_table_enforced"])


def test_assemble_composition_guard_strips_coil():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    names = {l["name"] for l in pkg["lines"]}
    assert not any("coil" in n.lower() for n in names)  # coil = composition bug
    # iter97: .019 Coil auto-add RETIRED AT SOURCE (hover LP spec) — the
    # guard no longer has anything to strip; it stays as defense-in-depth
    assert not pkg["summary"]["composition_guard_removed"]
    # J blocks are mounting blocks, NOT J-channel — must survive the guard
    assert "J blocks" in names


def test_assemble_install_auto_adds_survive():
    pkg = assemble_lp_package(MEAS, None, None)
    names = {l["name"] for l in pkg["lines"]}
    for expected in ("Touch up kits", "OSI Quad Max Caulking"):
        assert expected in names


def test_assemble_fallback_without_corner_locations():
    pkg = assemble_lp_package(MEAS, None, None)
    by = {l["name"]: l for l in pkg["lines"]}
    assert by[OSC_ITEM]["qty"] == 3  # ceil(37.6/16) whole-piece
    assert pkg["summary"]["osc_source"] == "outside_corner_lf"


def test_assemble_whole_piece_everywhere_and_lp_only():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    for l in pkg["lines"]:
        assert l["tab"] == "lp_smart"
        assert isinstance(l["qty"], int)


def test_assemble_pendings_surfaced():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    pend = " ".join(pkg["summary"]["pending_confirmations"])
    assert "ExpertFinish matrix" in pend
    assert "BlueLinx" in pend
    assert len(pkg["summary"]["pending_confirmations"]) == 2  # six-ruling block reconciled


def test_wrap_doors_three_side_ruled():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    from lp_conventions import WRAP_TRIM_ITEM
    wrap = next(l for l in pkg["lines"] if l["name"] == WRAP_TRIM_ITEM)
    # 10 windows × 14 + 2 entry × 18 (21 − 3' sill, 3-SIDE ruled) = 176 → 11
    assert wrap["qty"] == 11
    assert "3-SIDE" in wrap["note"]
    assert "garage" not in wrap["note"]  # no garage doors on Letrick


# ── Howard rulings: default width, starter line, substitution ──

def test_default_osc_is_howards_six_inch():
    assert 'x 6"' in OSC_ITEM
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    osc_lines = [l for l in pkg["lines"] if "540 Series OSC" in l["name"]]
    assert len(osc_lines) == 1 and osc_lines[0]["name"] == OSC_ITEM


def test_starter_line_always_present_non_sku():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS)
    st = next(l for l in pkg["lines"] if l["name"] == STARTER_LINE_NAME)
    # C4 (ruled): starter deducts ENTRY-class door widths (2 doors ×
    # 3' fallback = 6'); sliders sit on starter. 168 − 6 = 162.
    assert st["unit"] == "LF" and st["qty"] == 162
    # rip yield RULED FINAL: 3 strips/board = 48 LF/board → ceil(162/48) = 4
    assert st["pieces_added"] == 4 and st["non_sku"] is True
    assert "ripped from" in st["note"] and "48 LF/board" in st["note"]
    # Letrick lap cushion = 220 − 219.84 = 0.16 pc → thin-margin annotation fires
    assert "THIN WASTE MARGIN" in st["note"]
    assert any("starter rips" in f for f in pkg["summary"]["flags"])


def test_corner_sticks_recompute_on_stick_length():
    # ruling's example: a 10.44' corner is 1×16' stick but 2×10' sticks
    assert corner_sticks_for_length([10.44], 16.0) == 1
    assert corner_sticks_for_length([10.44], 10.0) == 2


def test_substitution_rederives_with_provenance():
    other_osc = '540 Series OSC 5/4" x 4" x 16\''
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS,
                              substitutions={OSC_ITEM: other_osc})
    line = next(l for l in pkg["lines"] if l["name"] == other_osc)
    assert line["substituted_from"] == OSC_ITEM
    assert line["qty"] == 6  # same 16' stick → same count (C4 feature-pooled), RE-DERIVED
    assert "RE-DERIVED from stored geometry" in line["note"]
    assert pkg["summary"]["substitution_errors"] == []


def test_substitution_free_text_refused():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS,
                              substitutions={OSC_ITEM: "Bob's Discount Corner 20'"})
    assert any("no free-text SKUs" in e for e in pkg["summary"]["substitution_errors"])
    assert any(l["name"] == OSC_ITEM for l in pkg["lines"])  # default untouched


def test_starter_dedicated_rip_substitution():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS,
                              substitutions={STARTER_LINE_NAME: "dedicated-rip"})
    st = next(l for l in pkg["lines"] if l["name"] == STARTER_LINE_NAME)
    assert st["pieces_added"] == 11  # ceil(162 ÷ 16') — re-derived, not hand-typed
    assert "dedicated-rip" in st["note"]
