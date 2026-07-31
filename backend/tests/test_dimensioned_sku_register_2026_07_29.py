"""DIMENSIONED-SKU REGISTER + DETECTOR (Howard ordered 2026-07-29).

Doctrine: every catalog SKU whose NAME carries a dimension (width, length,
thickness, coverage, spacing) or a FORMULA CLAIM ("2 per Sq", "1 per 50'
fascia") must be EXPLICITLY registered as one of:
  SPEC       — dimension selectable via a declared, validated model field
  CONST      — ruled/baked constant; name-constant == math-constant (pinned)
  IDENTITY   — dimension is product identity; qty math never uses it
  MANUAL     — catalog-only row, no derivation (register #8 class)
  STALE_NAME — the name claims math the live derivation does not use;
               NAMED here, held for Howard's one-pass audit ruling
A dimensioned SKU that is not registered FAILS THE SUITE. A registered
name that leaves the catalog FAILS THE SUITE (no ghost guards — the
'24" CTW' registry-drift lesson). Audit report:
/app/memory/dimensioned_sku_audit_2026-07-29.md
"""
import re
from pathlib import Path

from catalog_seed import SECTION_LAYOUT
from lp_conventions import (
    FASCIA_WIDTHS_IN, LAP_FACE_IN, LP_OSC_SKUS, LP_TRIM_SKUS,
    TRIM_STICK_LEN_FT, fascia_item_for_width, pieces_per_square,
    reveal_from_face,
)
import lp_smartside_formulas as lpf
from lp_package import LAP8_ITEM, SIDING_BOARD_LEN_FT, _stick_len_ft

DIM_RE = re.compile(
    r"\d+\s*(?:\"|'|/\d|inch\b|in\b|ft\b)"
    r"|\d+\s*[xX]\s*\d+"
    r"|per\s+\d+"
    r"|per\s+Sq",
    re.IGNORECASE,
)

SPEC, CONST, IDENTITY, MANUAL, STALE_NAME = (
    "SPEC", "CONST", "IDENTITY", "MANUAL", "STALE_NAME")

_VINYL_LAP_IDENTITY = {
    f"{fam} {tier} color {prof} {dim}": (
        IDENTITY, "sold per SQ (area ÷ 100); width/gauge is product identity")
    for fam, dims in (
        ("Conquest", ['Clap 4.5" .040', 'Dutch lap 4.5" .040']),
        ("Coventry", ['Clap 4" .042', 'Dutch lap 4" .042',
                      'Clap 5" .042', 'Dutch lap 5" .042']),
        ("Odyssey", ['Clap 4" .044', 'Dutch Lap 4" .044',
                     'Clap 5" .044', 'Dutch Lap 5" .044']),
        ("Charter Oak", ['Clap 4.5" .046', 'Dutch Lap 4.5" .046']),
    )
    for tier in ("Standard", "Architectural")
    for prof, dim in [d.split(" ", 1) for d in dims]
}

REGISTER: dict[str, tuple[str, str]] = {
    **_VINYL_LAP_IDENTITY,
    'vertical board and batten Standard color 7"':
        (IDENTITY, "per SQ; 7\" identity"),
    'vertical board and batten Architectural color 7"':
        (IDENTITY, "per SQ; 7\" identity"),
    'Pelican Bay Shakes 9"': (IDENTITY, "per SQ; 9\" identity"),
    'Ascend Composite Lap Siding 7"': (IDENTITY, "per SQ; 7\" identity"),
    'Ascend Composite B&B 12"':
        (IDENTITY, "per SQ; 30% claim == FAMILY_WASTE_DEFAULTS board_batten "
                   "30 (sealed 2026-07-24) — claim matches math"),
    'Ascend 3.5" Outside Corner  - MATTE':
        (MANUAL, "manual swap variant; 5.5\" row is the emitter"),
    'Ascend 5.5" Outside Corner  - MATTE':
        (CONST, "corner LF ÷ 12.5 (12'6\" stick baked, ruled 2026-07-18); "
                "5.5\" width identity"),
    "Ascend - 5.5\" Trim  (16' length)":
        (MANUAL, "16' in name; no derivation exists"),
    'Ascend - J - Channel':
        (CONST, "math = openings+eaves+rakes ÷ 12.5 (Iter 78f); '(2 per Sq)' "
                "suffix stripped per naming seal 2026-07-30"),
    '38 Series Lap 3/8" x 8" x 16\'':
        (CONST, "book 11 pcs/sq == curve(face 7.875, 16') — pinned below"),
    "38 Series 4' x 8' Panel":
        (SPEC, "panel_size trade spec (ruled 2026-07-30): 4x8 = 32 ft² — "
               "changes COUNT and SKU; left register #8 the day it grew "
               "the spec-gated derivation"),
    "38 Series 4' x 10' Panel":
        (SPEC, "panel_size DEFAULT (40 ft²) — pinned below"),
    '190 Series Trim 19/32" x 3" x 16\'':
        (CONST, "3\" == hard-formula batten width; 16' == stock length; "
                "SPACING is the trade spec (not in the name)"),
    '440 Series Trim 4/4" x 4" x 16\'':
        (SPEC, "width == fascia_width_in trade spec (4–12, default 8)"),
    '440 Series Trim 4/4" x 6" x 16\'': (SPEC, "fascia_width_in variant"),
    '440 Series Trim 4/4" x 8" x 16\'': (SPEC, "fascia_width_in DEFAULT"),
    '440 Series Trim 4/4" x 10" x 16\'': (SPEC, "fascia_width_in variant"),
    '440 Series Trim 4/4" x 12" x 16\'': (SPEC, "fascia_width_in variant"),
    '540 Series Trim 5/4" x 4" x 16\'':
        (SPEC, "wrap_trim_width_in DEFAULT (Q12); ÷ 16 == name's 16'"),
    '540 Series Trim 5/4" x 6" x 16\'': (SPEC, "wrap_trim_width_in variant"),
    '540 Series Trim 5/4" x 8" x 16\'': (SPEC, "wrap_trim_width_in variant"),
    '540 Series Trim 5/4" x 10" x 16\'': (SPEC, "wrap_trim_width_in variant"),
    '540 Series Trim 5/4" x 12" x 16\'': (SPEC, "wrap_trim_width_in variant"),
    '540 Series OSC 5/4" x 4" x 16\'':
        (MANUAL, "substitution option; retired default"),
    '540 Series OSC 5/4" x 6" x 16\'':
        (CONST, "sealed OSC width (2026-07-24); per-corner ceil(h/16) == 16'"),
    'Trim Coil Aluminum 24" x 50\'': (MANUAL, "no derivation"),
    'Flash tape 3 3/4" x 90\'':
        (MANUAL, "F6 CLOSED 2026-07-30: register #8 now carries this exact "
                 "string; resolution pinned"),
    '38 Series Soffit 16 x 16 Vented':
        (CONST, "16\" width / 16' length == SOFFIT_PROFILES (21.3 ft², "
                "×1.10 register #6 sealed) — pinned below"),
    '38 Series Soffit 16 x 16 Closed':
        (CONST, "same 21.3 ft² profile; measured-soffit governed"),
    '24 inch CTW soffit':
        (MANUAL, "F6 CLOSED 2026-07-30: register #8 renamed to this string"),
    '24 inch VSSFT':
        (MANUAL, "F6 CLOSED 2026-07-30: register #8 renamed to this string"),
    '3/4" J-Channel Standard color':
        (CONST, "math = openings+eaves+rakes ÷ 12.5; 3/4\" identity; "
                "'(2 per Sq)' suffix stripped per naming seal 2026-07-30"),
    '3/4" J-Channel Architectural color': (CONST, "same; Architectural twin"),
    '3/8" Fan Fold': (IDENTITY, "thickness identity; manual qty"),
    '1/2" J-Channel':
        (IDENTITY, "manual row; 1/2\" identity — '(2 per Sq)' suffix "
                   "stripped per naming seal 2026-07-30"),
    '1/2" J-Channel White':
        (IDENTITY, "manual row; colour twin — suffix stripped 2026-07-30"),
    '2" Nails 30 lbs':
        (CONST, "ruled 1-per-15-SQ constant lives in the derivation "
                "(÷100÷15, pinned below); claim suffix stripped 2026-07-30"),
    'Dryer Vents 4" (82A014)': (IDENTITY, "each; 4\" identity"),
    '1 1/4" Trim Nails': (IDENTITY, "flat 1/job; size identity"),
    '3/4" Soffit J-Channel (Charter Oak) Standard color':
        (CONST, "(eaves + rakes) ÷ 12.5 — rakes ONCE (R1 ruled 2026-07-30; "
                "2×rakes retired); 3/4\" identity"),
    '3/4" Soffit J-Channel (Charter Oak) Architectural color':
        (CONST, "same; Architectural twin"),
    'Gutter 6"': (IDENTITY, "LF-driven; 6\" identity"),
    'Downspout 6"': (IDENTITY, "LF-driven; 6\" identity"),
    'Cut out 4x4 section of wall and insulate': (IDENTITY, "each"),
    'Vero - Sliding glass door 60" x 80"': (IDENTITY, "size = product; each"),
    'Vero - Sliding glass door 72" x 80"': (IDENTITY, "size = product; each"),
    'Vero - Sliding glass door 96" x 80"': (IDENTITY, "size = product; each"),
    "Vinyl Sliding Glass Door (5' & 6' width)":
        (IDENTITY, "width band selects the labor price row; manual pick"),
    "Vinyl Sliding Glass Door (8' width -or- a sliding door that needs to "
    "be field assembled)": (IDENTITY, "width band; manual pick"),
    "Oversize Vinyl Door - (greater than 8' width)":
        (IDENTITY, "width band; manual pick"),
}


def _catalog_names() -> set[str]:
    return {it for _sec, _sh, items in SECTION_LAYOUT for it in items}


def test_every_dimensioned_sku_is_registered():
    unregistered = sorted(
        n for n in _catalog_names()
        if DIM_RE.search(n) and n not in REGISTER)
    assert not unregistered, (
        "DIMENSIONED SKU(S) NOT REGISTERED — every dimension in a SKU name "
        "must be an explicit trade-spec input, a ruled constant, product "
        "identity, or a named manual/stale row (Howard 2026-07-29). "
        f"Register these in test_dimensioned_sku_register_2026_07_29.py "
        f"with a ruling: {unregistered}")


def test_register_carries_no_ghost_names():
    ghosts = sorted(set(REGISTER) - _catalog_names())
    assert not ghosts, (
        "REGISTER entries no longer in the catalog — a guard on a name "
        f"that doesn't exist protects nothing ('24\" CTW' lesson): {ghosts}")


def test_stale_name_rows_stay_named_never_silent():
    """Howard #6 (2026-07-30): the strip list LANDED — every formula-claim
    suffix left the app names (the sheet keeps its parentheticals). The
    class stays registered so any FUTURE name that welds a rate back into
    a SKU must be explicitly ruled here before the suite goes green."""
    stale = sorted(n for n, (cls, _) in REGISTER.items() if cls == STALE_NAME)
    assert stale == [], (
        "STALE_NAME set must stay EMPTY after the 2026-07-30 strip ruling — "
        f"a new name-claims-math row needs Howard's ruling: {stale}")


# ───────────── name-constant == math-constant coupling pins ─────────────

def test_every_16ft_stick_sku_parses_to_the_math_constant():
    for sku in (*LP_TRIM_SKUS, *LP_OSC_SKUS, lpf.BATTEN_CATALOG_SKU, LAP8_ITEM):
        assert _stick_len_ft(sku) == 16.0, f"{sku}: name length != 16'"
    assert TRIM_STICK_LEN_FT == SIDING_BOARD_LEN_FT == \
        lpf.BATTEN_STOCK_LENGTH_FT == 16.0


def test_lap8_name_width_reproduces_the_book_11():
    reveal = reveal_from_face(LAP_FACE_IN['8" Lap'])
    assert pieces_per_square(reveal, 16) == 11 == lpf.LAP_PCS_PER_SQUARE


def test_soffit_16x16_name_matches_profile_math():
    p = lpf.SOFFIT_PROFILES['16" Soffit']
    assert p["length_ft"] == 16
    assert round(p["length_ft"] * p["actual_width_in"] / 12.0, 1) == \
        p["coverage_sqft_per_pc"] == 21.3


def test_bb_panel_spec_governs_sku_and_count_legacy_4x8_path_deleted():
    from routes.hover import _PROFILE_SKU_MAP, _lp_profile_sku_entry
    with lpf.override_flag(True):
        sku, unit, cov = _lp_profile_sku_entry("board_batten")
        sku8, _, cov8 = _lp_profile_sku_entry("board_batten", {"_panel_size": "4x8"})
    assert sku == "38 Series 4' x 10' Panel" and cov == 40.0
    assert sku8 == "38 Series 4' x 8' Panel" and cov8 == 32.0  # COUNT moves
    assert lpf.BB_PANEL_SIZES_SQFT["4x10"] == 40.0 == lpf.BB_PANEL_COVERAGE_SQFT
    # F7 (ruled 2026-07-30): the gated-legacy 4×8 Vertical Panel rows are
    # DELETED — no path may divide by 32 without the 4x8 spec selected.
    assert ("board_batten", "lp_smart") not in _PROFILE_SKU_MAP
    assert ("vertical", "lp_smart") not in _PROFILE_SKU_MAP


def test_batten_sku_width_matches_hard_formula_default():
    m = re.search(r'x\s*(\d+)"\s*x', lpf.BATTEN_CATALOG_SKU)
    import inspect
    sig = inspect.signature(lpf.bb_batten_pieces_hard)
    assert float(m.group(1)) == sig.parameters["batten_width_in"].default == 3.0


def test_fascia_width_variants_stay_inside_the_ruled_product_table():
    for w in FASCIA_WIDTHS_IN:
        assert fascia_item_for_width(w) in LP_TRIM_SKUS


def test_nails_per_15_sq_math_still_live():
    src = (Path(__file__).resolve().parent.parent / "routes" / "hover.py"
           ).read_text()
    i = src.index('2\\" Nails 30 lbs')
    # ruled 2026-07-31: round → ceil per whole-units; the 15-SQ constant stands
    assert "/ 100.0 / 15" in src[i:i + 500], \
        "nails derivation moved off the ruled 1-per-15-SQ constant"


def test_fascia_coil_width_conditional_reads_the_spec_key():
    """F2 FIXED (Howard ruled 2026-07-30): the width-conditional divisor
    reads _fascia_width_in — the EXACT key the trade spec injects. 12"
    fascia → 50 LF/roll; default → 100. Whole units land at the order
    layer (R3), so the fractional raw ratio is asserted via raw_qty."""
    from routes.hover import _build_lines

    def coil_fascia(m):
        return [l for l in _build_lines(m)
                if l["name"] == ".019 Coil"
                and l["section"] == "Vinyl Soffit with Siding"
                and l["tab"] == "vinyl"][0]

    m = {"siding_sqft": 2000, "eaves_lf": 100, "rakes_lf": 100, "window_count": 0}
    assert coil_fascia(m)["qty"] == 2.0                              # 200/100
    assert coil_fascia({**m, "_fascia_width_in": 12})["qty"] == 4.0  # 200/50


def test_mezzo_bucket_labels_match_their_bounds():
    from mezzo_catalog import MEZZO_BUCKETS
    for pt, buckets in MEZZO_BUCKETS.items():
        for b in buckets:
            assert b["label"] == f"{b['min_ui']}-{b['max_ui']} UI", \
                f"{pt}: label {b['label']} != bounds {b['min_ui']}-{b['max_ui']}"


def test_vero_bucket_labels_parse_to_their_own_bounds():
    from vero_catalog import parse_bucket_label
    assert parse_bucket_label("Min-73") == (0, 73)
    assert parse_bucket_label("0-101") == (0, 101)
    assert parse_bucket_label("161-170") == (161, 170)
