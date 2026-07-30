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
    'Ascend Composite B&B 12" (add 30% Waste)':
        (IDENTITY, "per SQ; 30% claim == FAMILY_WASTE_DEFAULTS board_batten "
                   "30 (sealed 2026-07-24) — claim matches math"),
    'Ascend 3.5" Outside Corner  - MATTE':
        (MANUAL, "manual swap variant; 5.5\" row is the emitter"),
    'Ascend 5.5" Outside Corner  - MATTE':
        (CONST, "corner LF ÷ 12.5 (12'6\" stick baked, ruled 2026-07-18); "
                "5.5\" width identity"),
    "Ascend - 5.5\" Trim  (16' length)":
        (MANUAL, "16' in name; no derivation exists"),
    'Ascend - J - Channel  (2 per Sq of siding)':
        (STALE_NAME, "F4: math = openings+eaves+rakes ÷ 12.5 (Iter 78f); "
                     "name still claims 2/SQ"),
    '38 Series Lap 3/8" x 8" x 16\'':
        (CONST, "book 11 pcs/sq == curve(face 7.875, 16') — pinned below"),
    "38 Series 4' x 8' Panel":
        (MANUAL, "register #8 manual; 32 ft² enters math ONLY on the gated "
                 "legacy Vertical Panel row; 4x8 selectability awaiting ruling"),
    "38 Series 4' x 10' Panel":
        (CONST, "BB live emitter ÷ 40 == 4×10 nominal — pinned below"),
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
        (CONST, "wrap/ISC/frieze default (Q12 ruled); ÷ 16 == name's 16'"),
    '540 Series Trim 5/4" x 6" x 16\'': (MANUAL, "substitution option, priced"),
    '540 Series Trim 5/4" x 8" x 16\'': (MANUAL, "substitution option, priced"),
    '540 Series Trim 5/4" x 10" x 16\'': (MANUAL, "substitution option, priced"),
    '540 Series Trim 5/4" x 12" x 16\'': (MANUAL, "substitution option, priced"),
    '540 Series OSC 5/4" x 4" x 16\'':
        (MANUAL, "substitution option; retired default"),
    '540 Series OSC 5/4" x 6" x 16\'':
        (CONST, "sealed OSC width (2026-07-24); per-corner ceil(h/16) == 16'"),
    'Trim Coil Aluminum 24" x 50\'': (MANUAL, "no derivation"),
    'Flash tape 3 3/4" x 90\'':
        (MANUAL, "F6: register #8 lists bare 'Flash tape' — registry-name "
                 "drift, that guard is vacuous for this row"),
    '38 Series Soffit 16 x 16 Vented':
        (CONST, "16\" width / 16' length == SOFFIT_PROFILES (21.3 ft², "
                "×1.10 register #6 sealed) — pinned below"),
    '38 Series Soffit 16 x 16 Closed':
        (CONST, "same 21.3 ft² profile; measured-soffit governed"),
    '24 inch CTW soffit':
        (MANUAL, "F6: register #8 lists '24\" CTW' — registry-name drift"),
    '24 inch VSSFT':
        (MANUAL, "F6: register #8 lists '24\" VSSFT' — registry-name drift"),
    'PVC Trim Coil (1 per 5 Sq Siding)':
        (STALE_NAME, "F5: manual row; per-5-Sq rule retired Feb 2026 — "
                     ".019 was renamed then, these two were not"),
    'Performance G8 Trim Coil (1 per 5 Sq Siding)':
        (STALE_NAME, "F5: same as PVC row"),
    '3/4" J-Channel Standard color (2 per Sq of siding)':
        (STALE_NAME, "F4: math = openings+eaves+rakes ÷ 12.5; name claims "
                     "2/SQ; 3/4\" is identity"),
    '3/4" J-Channel Architectural color (2 per Sq of siding)':
        (STALE_NAME, "F4: same"),
    '1/2" J-Channel (2 per Sq of siding)':
        (STALE_NAME, "F4: manual row carrying the retired 2/SQ claim"),
    '3/8" Fan Fold': (IDENTITY, "thickness identity; manual qty"),
    '2" Nails 30 lbs (1 per 15 Sq)':
        (CONST, "claim == math: ceil(sqft ÷ 100 ÷ 15) — pinned below"),
    'Dryer Vents 4" (82A014)': (IDENTITY, "each; 4\" identity"),
    '1 1/4" Trim Nails': (IDENTITY, "flat 1/job; size identity"),
    '3/4" Soffit J-Channel (Charter Oak) Standard color':
        (CONST, "(eaves + 2×rakes) ÷ 12.5 baked; 3/4\" identity"),
    '3/4" Soffit J-Channel (Charter Oak) Architectural color':
        (CONST, "same; Architectural twin"),
    '1/2" J-Channel (2 per Sq of siding) White':
        (STALE_NAME, "F4: manual row carrying the retired 2/SQ claim"),
    'Fascia/rake or frieze up to 8" coverage':
        (STALE_NAME, "F3: LF emitter is WIDTH-BLIND — always this ≤8\" band "
                     "even when fascia_width_in is 10/12; no 'over 8\"' twin "
                     "in the vinyl catalog — held for ruling"),
    ".019 Coil (1 per 50' fascia)":
        (STALE_NAME, "F1+F2: name claims flat 50'/roll; Q3 live math is "
                     "width-conditional 100/50 — AND it reads "
                     "m['fascia_width_in'] while the trade spec injects "
                     "'_fascia_width_in', so the divisor is ALWAYS 100"),
    "PVC Trim Coil (1 per 50' fascia)":
        (STALE_NAME, "F1: manual row; claim mismatches Q3 width-conditional"),
    "Performance G8 Trim Coil (1 per 50' fascia)":
        (STALE_NAME, "F1: same as PVC fascia row"),
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
    stale = sorted(n for n, (cls, _) in REGISTER.items() if cls == STALE_NAME)
    assert stale == sorted([
        ".019 Coil (1 per 50' fascia)",
        "PVC Trim Coil (1 per 50' fascia)",
        "Performance G8 Trim Coil (1 per 50' fascia)",
        'PVC Trim Coil (1 per 5 Sq Siding)',
        'Performance G8 Trim Coil (1 per 5 Sq Siding)',
        '3/4" J-Channel Standard color (2 per Sq of siding)',
        '3/4" J-Channel Architectural color (2 per Sq of siding)',
        '1/2" J-Channel (2 per Sq of siding)',
        '1/2" J-Channel (2 per Sq of siding) White',
        'Ascend - J - Channel  (2 per Sq of siding)',
        'Fascia/rake or frieze up to 8" coverage',
    ]), ("STALE_NAME set changed — a rename lands only with Howard's audit "
         "ruling; update the register AND the audit report together")


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


def test_bb_live_emitter_is_4x10_at_40_legacy_vertical_is_4x8_at_32():
    from routes.hover import _PROFILE_SKU_MAP, _lp_profile_sku_entry
    with lpf.override_flag(True):
        sku, unit, cov = _lp_profile_sku_entry("board_batten")
    assert sku == "38 Series 4' x 10' Panel" and cov == 40.0
    assert lpf.BB_PANEL_SIZES_SQFT["4x10"] == 40.0 == lpf.BB_PANEL_COVERAGE_SQFT
    legacy = _PROFILE_SKU_MAP[("board_batten", "lp_smart")]
    assert legacy == ('38 Series Vertical Panel', "PCS", 32.0)
    assert lpf.BB_PANEL_SIZES_SQFT["4x8"] == 32.0  # divergence NAMED, gated


def test_batten_sku_width_matches_hard_formula_default():
    m = re.search(r'x\s*(\d+)"\s*x', lpf.BATTEN_CATALOG_SKU)
    import inspect
    sig = inspect.signature(lpf.bb_batten_pieces_hard)
    assert float(m.group(1)) == sig.parameters["batten_width_in"].default == 3.0


def test_fascia_width_variants_stay_inside_the_ruled_product_table():
    for w in FASCIA_WIDTHS_IN:
        assert fascia_item_for_width(w) in LP_TRIM_SKUS


def test_nails_claim_matches_live_math():
    src = (Path(__file__).resolve().parent.parent / "routes" / "hover.py"
           ).read_text()
    i = src.index('2\\" Nails 30 lbs (1 per 15 Sq)')
    assert "/ 100.0 / 15)" in src[i:i + 400], \
        "nails derivation moved off the name's 1-per-15-SQ claim"


def test_fascia_coil_width_conditional_still_live_as_audited():
    src = (Path(__file__).resolve().parent.parent / "routes" / "hover.py"
           ).read_text()
    i = src.index(".019 Coil (1 per 50' fascia)")
    block = src[i:i + 700]
    assert '100.0 if float(m.get("fascia_width_in") or 8) <= 10 else 50.0' \
        in block, ("F2 pin: the audited state changed — if this was FIXED "
                   "(key or name), land it only with Howard's audit ruling "
                   "and update F1/F2 in the register + report")


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
