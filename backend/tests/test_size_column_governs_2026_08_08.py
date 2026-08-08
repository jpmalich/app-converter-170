"""THE SIZE COLUMN GOVERNS + MARK-SUMMING + DOOR EXCLUSIONS (Howard
ruled 2026-08-08, read off the printed Boni schedules).

"THE SIZE COLUMN IS THE DIMENSION. THE PRODUCT CODE IS A FAMILY LABEL.
Use the code to identify the unit, never to compute one." Every unit
prints ~half an inch under its code's nominal — converting SH 3-0_5-0
to 36x60 while 2'-11 1/2" x 4'-11 1/2" sits in the next column is the
printed-dims-sacred rule being violated by converting a label.

"MARK A APPEARS ON BOTH SHEETS. SUM ACROSS SHEETS BY MARK." The Mark B
bug was CROSS-SHEET MARK MERGING — D's dimensions attached to B's mark
— not glyph misreading.

"EXTERIOR IS E2, E3, G1, G2. NOTHING ELSE. 'HOLLOW CORE' and 'Garage to
House Door' are readable exclusion signals sitting in the product code
column." And garage doors PRINT 8'-0" — the carried 7' was a guess
('appears' = admission of no source).

PURITY: the printed figures below are parser-input examples and flag
fixtures, never constants, defaults, or formula targets.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _parse_printed_size, check_read_consistency,
)

DICT_TEXT = (Path(__file__).resolve().parents[2]
             / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")


# ---- the parser reads the SIZE column's own format ----

def test_size_column_feet_inch_fraction_strings_parse_exactly():
    assert _parse_printed_size("2'-11 1/2\" x 4'-11 1/2\"") == (35.5, 59.5)
    assert _parse_printed_size("2'-11 1/2\" x 3'-11 1/2\"") == (35.5, 47.5)
    assert _parse_printed_size("2'-3 1/2\" x 3'-5 1/2\"") == (27.5, 41.5)
    assert _parse_printed_size("16'-0\" x 8'-0\"") == (192.0, 96.0)
    assert _parse_printed_size("9'-0\" X 8'-0\"") == (108.0, 96.0)


def test_every_pre_ruling_format_still_parses():
    assert _parse_printed_size("3-0x5-0") == (36.0, 60.0)
    assert _parse_printed_size("3050") == (36.0, 60.0)
    assert _parse_printed_size("2-4_5-4") == (28.0, 64.0)
    assert _parse_printed_size("SH 2-4_3-4") == (28.0, 40.0)
    assert _parse_printed_size("3-6 5-0") == (42.0, 60.0)
    assert _parse_printed_size("") is None
    assert _parse_printed_size("garbage") is None


# ---- the contract: size column governs, code is a label, marks sum ----

def test_the_prompt_carries_the_size_column_ruling():
    for must in ("THE SIZE COLUMN GOVERNS", "FAMILY LABEL",
                 '"product_code"', "SUM MARKS ACROSS SHEETS",
                 '"schedule_pages"', "sum counts BY MARK across sheets"):
        assert must in SYSTEM_PROMPT, f"prompt lost the ruling: {must!r}"


def test_the_prompt_carries_the_door_exclusion_signals():
    for must in ("HOLLOW CORE", "Garage to House",
                 "PRODUCT-CODE COLUMN IS THE EXCLUSION SIGNAL",
                 "DOOR SIZES COME FROM PRINT", "ADMISSION OF"):
        assert must in SYSTEM_PROMPT, f"prompt lost the ruling: {must!r}"


# ---- cross-sheet mark merge is a NAMED flag ----

def _flags(raw):
    return check_read_consistency(raw)


def test_one_mark_two_printed_sizes_flags_the_merge():
    raw = {"windows": [
        {"id": "B", "printed_size": "SH 3-0_4-0", "width_in": 35.5,
         "height_in": 47.5, "qty": 1},
        {"id": "b", "printed_size": "SH 2-4_3-6", "width_in": 27.5,
         "height_in": 41.5, "qty": 1},
    ]}
    f = next(x for x in _flags(raw) if x["code"] == "mark_size_conflict")
    assert f["level"] == "loud"
    assert f["vars"]["mark"] == "B"
    assert "SH 2-4_3-6" in f["vars"]["sizes"] and "SH 3-0_4-0" in f["vars"]["sizes"]


def test_one_mark_on_two_sheets_with_one_size_is_clean():
    raw = {"windows": [
        {"id": "A", "printed_size": "SH 3-0_5-0", "width_in": 35.5,
         "height_in": 59.5, "qty": 9, "schedule_pages": [6, 7]},
    ]}
    assert all(x["code"] != "mark_size_conflict" for x in _flags(raw))


# ---- door sizes reproduce their printed parse ----

def test_the_guessed_garage_door_height_flags_loudly():
    """The live failure class: schedule prints 16'-0\" x 8'-0\", the read
    carried 192x84 off an 'appears to be 16x7' guess."""
    raw = {"doors": [{"id": "G1", "printed_size": "16'-0\" x 8'-0\"",
                      "width_in": 192, "height_in": 84, "qty": 1}]}
    f = next(x for x in _flags(raw) if x["code"] == "door_size_parse_mismatch")
    assert f["vars"]["parsed"] == "192×96"
    assert f["vars"]["carried"] == "192×84"


def test_a_door_carrying_its_printed_parse_is_clean():
    raw = {"doors": [{"id": "G2", "printed_size": "9'-0\" x 8'-0\"",
                      "width_in": 108, "height_in": 96, "qty": 1}]}
    assert all(x["code"] != "door_size_parse_mismatch" for x in _flags(raw))


def test_flag_strings_exist_in_both_languages():
    assert DICT_TEXT.count('"bp.rb.consistency.mark_size_conflict"') == 2
    assert DICT_TEXT.count('"bp.rb.consistency.door_size_parse_mismatch"') == 2
