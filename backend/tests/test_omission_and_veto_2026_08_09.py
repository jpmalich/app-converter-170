"""OMISSION CHECK · ADJACENT-RUN JOINING · SHORT-QUOTE VETO · DOOR SIGNAL
(Howard's build order 2026-08-09 send 3, items 1/2/3/5).

1. OMISSION — "THE EVIDENCE LAYER IS ONE-DIRECTIONAL… E2 DOES print and
   is absent from the read." Schedule-code / door-mark tokens inside the
   schedule's table region (anchored by the rows we DID read) with no
   counterpart in the read flag LOUD as omissions. Fewer than two anchors
   leaves the region undecidable — skipped, never guessed.
2. JOINING — OCR fragments fraction-heavy cells; a CORRECT quote was
   killed by tokenization. Same-line runs join so multi-token quotes can
   locate. "An instrument that kills good data is a defect, not a virtue."
3. VETO — a quote of ≤2 characters carries NO SURVIVAL WEIGHT in the
   fabrication drop rule (the E1 "3'-0\"→30" veto class). The mark keeps
   its weight — it is the row's identity.
5. DOOR SIGNAL — the product-code column read BY MACHINE: a schedule line
   carrying the row's mark AND an interior marker is INTERIOR regardless
   of the model's own label. HOLLOW CORE cannot wear an exterior label.

PURITY: E1/E2/SH3056/9-1/5/1 etc. are evidence for rulings and parser
fixtures — never constants or targets in production code.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _del1, _join_adjacent_runs, _ocr_norm, _ocr_verify_marks,
    build_blueprint_readback,
)

PAYLOADS = [b"p1", b"p2"]


def _page(norms=None, boxed=None):
    return {"norms": norms or [], "boxed": boxed or []}


def _fake(pages):
    return lambda page: pages.get(page)


def _door(mk, size="", code="", pages=None):
    d = {"id": mk, "printed_size": size, "product_code": code,
         "width_in": 36, "height_in": 80, "qty": 1,
         "type_hint": "entry", "exterior_evidence": "elevation"}
    if pages is not None:
        d["schedule_pages"] = pages
    return d


class TestAdjacentRunJoining:
    def test_fragments_on_one_line_join(self):
        runs = [("21112", "2'-11 1/2\"", (10, 100, 60, 112)),
                ("X41112", "x 4'-11 1/2\"", (66, 100, 130, 112))]
        joined = _join_adjacent_runs(runs)
        assert any(j[0] == "21112X41112" for j in joined)

    def test_distant_or_other_line_runs_never_join(self):
        runs = [("21112", "a", (10, 100, 60, 112)),
                ("X41112", "b", (400, 100, 460, 112)),   # 340px gap ≫ 3×h
                ("SH3050", "c", (10, 400, 60, 412))]     # other line
        joined = _join_adjacent_runs(runs)
        assert joined == []

    def test_fraction_kill_class_survives_with_joining(self):
        # The A/B/C class from run 76203e6a: the size prints, OCR
        # fragments it, joining lets the quote locate — dims live.
        w = {"id": "A", "printed_size": "2'-11 1/2\" x 4'-11 1/2\"",
             "qty": 9, "width_in": 35.5, "height_in": 59.5,
             "schedule_pages": [1]}
        raw = {"windows": [w]}
        norms = ["A", "21112", "X41112", "21112X41112"]  # joined present
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=norms)}))
        assert raw["windows"][0]["width_in"] == 35.5
        assert raw["windows"][0]["printed_size"]
        assert "_mark_quote_misses" not in raw


class TestShortQuoteVeto:
    def test_two_char_quote_has_no_survival_weight(self):
        # E1's own case: mark misses; its size "3'-0\"" → "30" trivially
        # matches a dimension run ELSEWHERE. Under the veto the row DROPS.
        raw = {"doors": [_door("E1", size="3'-0\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["30", "E2", "90X80"])}))
        assert raw["doors"] == []
        assert raw["_marks_dropped_not_located"][0]["mark"] == "E1"

    def test_mark_keeps_its_weight(self):
        # The mark is the row's identity — a located mark still saves.
        raw = {"doors": [_door("G2", size="9'-2\" x 8'-0\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["G2", "90X80"])}))
        assert len(raw["doors"]) == 1  # survives; the size quote dies
        assert raw["doors"][0]["width_in"] is None

    def test_long_quote_still_saves(self):
        raw = {"doors": [_door("E9", size="16'-0\" x 8'-0\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["160X80"])}))
        assert len(raw["doors"]) == 1


class TestOmissionCheck:
    def _boxed_sheet(self):
        # A schedule column: SH3050 (read), SH3040 (read), SH3056 (NOT
        # read — the omission), E2 (door mark, NOT read), plus a grid
        # bubble far outside the region.
        return _page(
            norms=["SH3050", "SH3040", "SH3056", "E2", "K9"],
            boxed=[("SH3050", (100, 100, 160, 112)),
                   ("SH3040", (100, 130, 160, 142)),
                   ("SH3056", (100, 160, 160, 172)),
                   ("E2", (100, 220, 120, 232)),
                   ("K9", (900, 900, 920, 912))])

    def test_unread_rows_inside_region_flag_loud(self):
        raw = {"windows": [
            {"id": "A", "product_code": "SH 3-0_5-0", "qty": 9,
             "printed_size": "", "schedule_pages": [1]},
            {"id": "B", "product_code": "SH 3-0_4-0", "qty": 1,
             "printed_size": "", "schedule_pages": [1]}],
            "doors": [_door("E3", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: self._boxed_sheet()}))
        toks = {o["token"] for o in raw["_schedule_omissions"]}
        assert "SH3056" in toks   # the C-family row the read never carried
        assert "E2" in toks       # the door row the read never carried
        assert "K9" not in toks   # outside the table region
        rb = build_blueprint_readback(raw)
        f = next(x for x in rb["rail"] if x["code"] == "schedule_row_omitted")
        assert f["level"] == "loud" and "SH3056" in f["text"]

    def test_one_glyph_ocr_drift_is_not_an_omission(self):
        # SH340 is SH3040 with a dropped glyph — a row we DID read.
        assert _del1("SH340", "SH3040")
        raw = {"windows": [
            {"id": "B", "product_code": "SH 3-0_4-0", "qty": 1,
             "printed_size": "", "schedule_pages": [1]},
            {"id": "A", "product_code": "SH 3-0_5-0", "qty": 9,
             "printed_size": "", "schedule_pages": [1]}]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["SH3040", "SH3050", "SH340"],
                      boxed=[("SH3040", (100, 100, 160, 112)),
                             ("SH3050", (100, 130, 160, 142)),
                             ("SH340", (100, 160, 150, 172))])}))
        assert "_schedule_omissions" not in raw

    def test_fewer_than_two_anchors_is_undecidable_not_guessed(self):
        raw = {"windows": [
            {"id": "A", "product_code": "SH 3-0_5-0", "qty": 9,
             "printed_size": "", "schedule_pages": [1]}]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["SH3050", "SH3056"],
                      boxed=[("SH3050", (100, 100, 160, 112)),
                             ("SH3056", (100, 130, 160, 142))])}))
        assert "_schedule_omissions" not in raw


class TestFractionSkeleton:
    def test_true_print_with_unreadable_fractions_survives(self):
        # The A/B class from the live re-kill: the ½ glyphs ARE printed
        # (Howard read the sheet) but the OCR engine cannot read them —
        # the whole-inch skeleton locates the quote, NAMED as such.
        w = {"id": "A", "printed_size": "2'-11 1/2\" x 4'-11 1/2\"",
             "qty": 9, "width_in": 35.5, "height_in": 59.5,
             "schedule_pages": [1]}
        raw = {"windows": [w]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["A", "211411"])}))  # x-less digit skeleton
        assert raw["windows"][0]["width_in"] == 35.5
        assert raw["_skeleton_matches"][0]["mark"] == "A"
        rb = build_blueprint_readback(raw)
        f = next(x for x in rb["rail"] if x["code"] == "skeleton_match")
        assert f["level"] == "info"

    def test_skeleton_still_kills_a_wrong_quote(self):
        # The C class: the quote says 5'-0 where the sheet prints 5'-5 —
        # the skeleton does NOT match and the quote dies.
        w = {"id": "C", "printed_size": "2'-11 1/2\" x 5'-0 1/2\"",
             "qty": 5, "width_in": 35.5, "height_in": 60.5,
             "schedule_pages": [1]}
        raw = {"windows": [w]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["C", "211X55", "21155"])}))
        assert raw["windows"][0]["width_in"] is None
        assert "_skeleton_matches" not in raw


class TestDoorMarkNoiseFilter:
    def test_grid_bubbles_are_not_door_omissions(self):
        # RR1 / X17 / K40 are section tags, not door rows — a door-mark
        # candidate must share an initial letter with the read's own
        # door marks (E, G here). NAMED LIMIT: a whole letter family the
        # read never carried is beyond this instrument.
        raw = {"doors": [
            _door("E3", size="", code="", pages=[1]),
            _door("G1", size="", code="", pages=[1])]}
        boxed = [("E3", (100, 100, 120, 112)),
                 ("G1", (100, 130, 120, 142)),
                 ("E2", (100, 160, 120, 172)),
                 ("RR1", (100, 190, 130, 202)),
                 ("X17", (100, 220, 130, 232)),
                 ("K40", (100, 250, 130, 262))]
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=[b[0] for b in boxed], boxed=boxed)}))
        toks = {o["token"] for o in raw.get("_schedule_omissions") or []}
        assert toks == {"E2"}


class TestDoorSignalByMachine:
    def test_hollow_core_cannot_wear_an_exterior_label(self):
        raw = {"doors": [_door("E4", size="3'-0\" x 6'-8\"", pages=[1]),
                         _door("E3", size="3'-0\" x 6'-8\"", pages=[1])]}
        norms = [_ocr_norm("E4 3068 HOLLOW CORE").replace(" ", ""),
                 "E43068HOLLOWCORE", "E3", "30X68", "E4"]
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=norms)}))
        marks = [d["id"] for d in raw["doors"]]
        assert marks == ["E3"]
        sig = raw["_interior_signal_dropped"][0]
        assert sig["mark"] == "E4" and sig["marker"] == "HOLLOWCORE"
        assert raw["_seam_ledger"]["interior_signal_dropped"]["items"] == [
            "doors:E4"]
        rb = build_blueprint_readback(raw)
        f = next(x for x in rb["rail"]
                 if x["code"] == "interior_signal_machine")
        assert f["level"] == "loud" and "E4" in f["text"]

    def test_marker_without_the_mark_never_drops(self):
        # The marker printing SOMEWHERE is not evidence about THIS row.
        raw = {"doors": [_door("E3", size="3'-0\" x 6'-8\"", pages=[1])]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["E3", "30X68", "D53068HOLLOWCORE"])}))
        assert len(raw["doors"]) == 1
