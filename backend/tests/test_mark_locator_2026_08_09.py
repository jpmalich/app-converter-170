"""MARKS FACE THE LOCATOR TOO (Howard's build order 2026-08-09, item 2).

The schedule rerun carried "an E1 exterior entry that Howard's sheet
read does not hold (exterior = E2,E3,G1,G2 only)" and "G2 9'-2" vs
printed 9'-0"". The OCR locator built for dimensions now verifies
schedule-row quotes: a row NONE of whose quotes locate on its sheets
(all rotations) is a fabrication and is DROPPED; a located row whose
printed size cannot be found has that quote KILLED — its parse never
reaches the takeoff.

HARD SEPARATION STANDS: OCR supplies existence, never value. An engine
failure is never evidence of fabrication — rows stand.

PURITY: E1 / G2 / 9'-2" are the live-fire evidence for the ruling,
never constants or assertion targets in production code.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _ocr_norm, _ocr_verify_marks, build_blueprint_readback,
)

PAYLOADS = [b"page1", b"page2"]


def _runs(page_norms):
    def runs_for_page(page):
        return page_norms.get(page, [])
    return runs_for_page


def _door(mk, size, code="", pages=None, ev="elevation"):
    d = {"id": mk, "printed_size": size, "product_code": code,
         "width_in": 110, "height_in": 96, "qty": 1,
         "type_hint": "entry", "exterior_evidence": ev}
    if pages is not None:
        d["schedule_pages"] = pages
    return d


class TestFabricatedRowDropped:
    def test_e1_with_no_locatable_quote_is_dropped(self):
        # Neither "E1" nor its claimed size prints anywhere — fabricated.
        raw = {"doors": [_door("E1", "3'-0\" x 6'-8\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs(
            {1: [_ocr_norm("E2"), _ocr_norm("G2"), _ocr_norm("9'-0\"")]}))
        assert raw["doors"] == []
        d = raw["_marks_dropped_not_located"][0]
        assert d["mark"] == "E1" and d["kind"] == "doors"
        assert d["rotations_checked"] is True
        assert raw["_seam_ledger"]["marks_dropped_not_located"]["items"] == [
            "doors:E1"]

    def test_row_with_one_locating_quote_survives(self):
        # The mark locates even though the size doesn't — the row stays;
        # only the size quote dies (next class).
        raw = {"doors": [_door("G2", "9'-2\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs(
            {1: [_ocr_norm("G2"), _ocr_norm("9'-0\"")]}))
        assert len(raw["doors"]) == 1

    def test_windows_face_the_locator_too(self):
        raw = {"windows": [{"id": "Z9", "printed_size": "5'-0\" x 5'-0\"",
                            "qty": 1, "width_in": 60, "height_in": 60,
                            "schedule_pages": [2]}]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs(
            {2: [_ocr_norm("A"), _ocr_norm("3'-0\" x 5'-0\"")]}))
        assert raw["windows"] == []


class TestFabricatedSizeQuoteKilled:
    def test_g2_9_2_not_on_sheet_dims_nulled(self):
        # G2 locates; the quoted 9'-2" does not (the sheet prints 9'-0").
        # The quote is killed: dims null, the claim survives in the
        # register, the parse never reaches the takeoff.
        raw = {"doors": [_door("G2", "9'-2\" x 8'-0\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs(
            {1: [_ocr_norm("G2"), _ocr_norm("9'-0\" x 8'-0\"")]}))
        d = raw["doors"][0]
        assert d["width_in"] is None and d["height_in"] is None
        assert d["printed_size"] == ""
        assert d["printed_size_not_located"] == "9'-2\" x 8'-0\""
        m = raw["_mark_quote_misses"][0]
        assert (m["mark"], m["field"]) == ("G2", "printed_size")
        assert raw["_seam_ledger"]["mark_size_quotes_nulled"]["items"] == [
            "doors:G2"]

    def test_locating_size_untouched(self):
        raw = {"doors": [_door("G1", "16'-0\" x 8'-0\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs(
            {1: [_ocr_norm("G1"), _ocr_norm("16'-0\" x 8'-0\"")]}))
        d = raw["doors"][0]
        assert d["width_in"] == 110 and d["printed_size"]
        assert "_mark_quote_misses" not in raw


class TestOcrFailureIsNeverEvidence:
    def test_engine_failure_leaves_rows_standing(self):
        raw = {"doors": [_door("E9", "9'-9\" x 9'-9\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS,
                          runs_for_page=lambda page: None)
        assert len(raw["doors"]) == 1
        assert "_marks_dropped_not_located" not in raw

    def test_row_without_quotes_skipped(self):
        raw = {"windows": [{"qty": 2, "width_in": 36, "height_in": 60}]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs({}))
        assert len(raw["windows"]) == 1


class TestNamedOnTheCard:
    def test_rail_names_drop_and_quote_miss_loud(self):
        raw = {"doors": [_door("E1", "3'-0\" x 6'-8\"", pages=[1]),
                         _door("G2", "9'-2\" x 8'-0\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs(
            {1: [_ocr_norm("G2"), _ocr_norm("9'-0\" x 8'-0\"")]}))
        rb = build_blueprint_readback(raw)
        by_code = {f["code"]: f for f in rb["rail"]}
        assert by_code["mark_not_located"]["level"] == "loud"
        assert "E1" in by_code["mark_not_located"]["text"]
        assert by_code["mark_quote_miss"]["level"] == "loud"
        assert "9'-2" in by_code["mark_quote_miss"]["text"]

    def test_mark_matching_is_prefix_not_containment(self):
        # "E1" must not be located by "E2..." runs; a merged schedule
        # row starting with the mark does locate it.
        raw = {"doors": [_door("E1", "", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_runs(
            {1: [_ocr_norm("E2 3-0 6-8"), _ocr_norm("WE1X")]}))
        assert raw["doors"] == []
        raw2 = {"doors": [_door("E1", "", pages=[1])]}
        _ocr_verify_marks(raw2, PAYLOADS, runs_for_page=_runs(
            {1: [_ocr_norm("E1 3-0 6-8 HOLLOW")]}))
        assert len(raw2["doors"]) == 1
