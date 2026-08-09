"""COUNT COLUMN GOVERNS + PROFILE SELECTION ON EVERY DOOR (Howard ruled
2026-08-08/09).

COUNT: "The schedule prints COUNT; read it. Do not count symbols on a
plan." Printed counts on Boni: A 9 (2+7) · B 1 · C 5 · D 1 = SIXTEEN;
the rerun said 23. DO NOT TUNE TO 16 — the check pins that a carried
qty must equal the sum of the COUNT cells the read itself named.

PROFILE: "A contractor chooses the siding profile on ANY estimate —
blueprint, Hover, or photo — and the surface cannot be tied to a
completed measurement run." And A DEFAULTED PROFILE PRINTS AS
DEFAULTED — a default is an unstated assumption, the thing this product
exists to eliminate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import EstimateIn  # noqa: E402
from routes.ai_blueprint import SYSTEM_PROMPT, check_read_consistency  # noqa: E402
from routes.hover import HOVER_MAPPING_SPEC  # noqa: E402

DICT_TEXT = (Path(__file__).resolve().parents[2]
             / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")


# ---- the count column ----

def test_prompt_carries_the_count_column_ruling():
    for must in ("THE COUNT COLUMN GOVERNS COUNTS",
                 "NEVER count window symbols", '"count_by_page"'):
        assert must in SYSTEM_PROMPT, f"prompt lost the ruling: {must!r}"


def test_qty_ignoring_the_named_count_cells_flags_loudly():
    raw = {"windows": [{"id": "A", "qty": 12,
                        "count_by_page": {"6": 2, "7": 7}}]}
    f = next(x for x in check_read_consistency(raw)
             if x["code"] == "count_column_mismatch")
    assert f["level"] == "loud"
    assert f["vars"]["summed"] == "9" and f["vars"]["carried"] == "12"


def test_qty_equal_to_its_count_cells_is_clean():
    raw = {"windows": [{"id": "A", "qty": 9,
                        "count_by_page": {"6": 2, "7": 7}}]}
    assert all(x["code"] != "count_column_mismatch"
               for x in check_read_consistency(raw))


def test_a_read_naming_no_count_cells_is_not_accused():
    raw = {"windows": [{"id": "A", "qty": 12}]}
    assert all(x["code"] != "count_column_mismatch"
               for x in check_read_consistency(raw))


def test_count_flag_strings_exist_in_both_languages():
    assert DICT_TEXT.count('"bp.rb.consistency.count_column_mismatch"') == 2


# ---- profile selection on every door ----

def test_the_choice_field_survives_the_put_projection_seam():
    """The PUT model declaration is silent-truncation instance #1 —
    the field must be IN the model or every save drops it."""
    assert "siding_profile_choice" in EstimateIn.model_fields
    m = EstimateIn(siding_profile_choice={"name": "Odyssey", "at": "2026-08-09"})
    assert m.siding_profile_choice["name"] == "Odyssey"


def test_the_default_siding_note_prints_as_defaulted():
    rows = [s for s in HOVER_MAPPING_SPEC
            if "Charter Oak Standard color Dutch Lap" in str(s.get("item"))]
    note = rows[0]["note"]({"siding_sqft": 3990})
    assert "PROFILE DEFAULTED — not a choice" in note
    assert "pick the profile on the estimate" in note


def test_profile_chip_strings_exist_in_both_languages():
    for key in ("sp.defaulted", "sp.chosen", "sp.stale", "sp.choose",
                "sp.pickTitle", "sp.none"):
        assert DICT_TEXT.count(f'"{key}"') == 2, f"{key} must exist EN+ES"
    en = DICT_TEXT.split('"sp.defaulted": "')[1].split('",')[0]
    assert "not chosen" in en, "the defaulted chip must say it was not a choice"


def test_the_chip_is_not_gated_behind_a_measurement_run():
    src = (Path(__file__).resolve().parents[2]
           / "frontend/src/components/estimate/SidingProfileChip.jsx"
           ).read_text(encoding="utf-8")
    for banned in ("_per_elevation_breakdown", "run_id", "ai-blueprint",
                   "latest-for-estimate"):
        assert banned not in src, \
            f"profile selection must not reference {banned!r} — it works on every door"
    editor = (Path(__file__).resolve().parents[2]
              / "frontend/src/pages/EstimateEditor.jsx").read_text(encoding="utf-8")
    assert "SidingProfileChip" in editor, "the chip must be mounted on the estimate editor"
