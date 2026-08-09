"""THE COUNT COLUMN GOVERNS COUNTS — ENFORCED (Howard ruled 2026-08-08,
correction 2026-08-09 send c).

Both halves, stated plainly:
  "DO NOT count symbols on floor plans, ever."
  "DO sum the printed COUNT COLUMN across sheets when the same mark
   appears on more than one."
"Mark A is printed on BOTH sheets: count 2 on sheet 6, count 7 on
sheet 7. THE CORRECT TOTAL IS NINE. A per-sheet mark row is not a
distinct mark."
"If a sheet's schedule prints no count for a mark, that sheet
contributes nothing — flag it, don't estimate."

The prompt rule alone left the rerun at 23 vs the printed 16 — this
suite pins the SEAM enforcement: the backend rewrites qty from the
printed cells, merges per-sheet rows, zeroes unread counts, and
accounts every move.

PURITY: 2/7/9/16 and the marks below are evidence for the ruling and
parser-input fixtures — never constants, defaults, or formula targets.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _aggregate_to_hover_shape, _enforce_count_column,
    build_blueprint_readback,
)


def _win(mk, qty, cbp=None, pages=None, size="", elev="unknown"):
    w = {"id": mk, "qty": qty, "width_in": 36, "height_in": 60,
         "printed_size": size, "type_hint": "single_hung",
         "elevation": elev}
    if cbp is not None:
        w["count_by_page"] = cbp
    if pages is not None:
        w["schedule_pages"] = pages
    return w


class TestPerSheetRowsMerge:
    def test_mark_a_two_sheets_sums_to_nine(self):
        # 2 on sheet 6 + 7 on sheet 7 = ONE row, qty NINE — never 2, never 7.
        raw = {"windows": [
            _win("A", 2, cbp={"6": 2}, pages=[6]),
            _win("A", 7, cbp={"7": 7}, pages=[7]),
        ]}
        _enforce_count_column(raw)
        assert len(raw["windows"]) == 1
        a = raw["windows"][0]
        assert a["qty"] == 9
        assert a["count_by_page"] == {"6": 2, "7": 7}
        assert a["schedule_pages"] == [6, 7]
        assert raw["_mark_rows_merged"] == ["windows:A"]
        assert raw["_seam_ledger"]["mark_rows_merged"]["removed"] == 1

    def test_conflicting_printed_sizes_do_not_merge(self):
        # The Mark-B sin: one mark wearing another's dimensions. Rows
        # with disagreeing printed sizes stay separate for a human
        # (mark_size_conflict names them) — never merged.
        raw = {"windows": [
            _win("B", 1, cbp={"6": 1}, size='2\'-11 1/2" x 3\'-11 1/2"'),
            _win("B", 1, cbp={"7": 1}, size='2\'-4" x 3\'-6"'),
        ]}
        _enforce_count_column(raw)
        assert len(raw["windows"]) == 2

    def test_same_sheet_conflicting_cells_flagged(self):
        raw = {"windows": [
            _win("C", 3, cbp={"6": 3}),
            _win("C", 5, cbp={"6": 5}),
        ]}
        _enforce_count_column(raw)
        assert raw["_count_cell_conflicts"][0]["mark"] == "C"
        assert "3 vs 5" in raw["_count_cell_conflicts"][0]["cells"]

    def test_elevation_split_without_cells_untouched(self):
        # The prompt's split-per-elevation rows carry NO count cells —
        # they are NOT per-sheet schedule rows and must survive as-is.
        raw = {"windows": [
            _win("A", 4, elev="front"),
            _win("A", 5, elev="back"),
        ]}
        _enforce_count_column(raw)
        assert len(raw["windows"]) == 2
        assert [w["qty"] for w in raw["windows"]] == [4, 5]


class TestCountCellsGovern:
    def test_symbol_counted_qty_rewritten_from_cells(self):
        # The live failure: the read carried 12 (symbol-counting) while
        # the cells print 2 + 7. The column governs — qty becomes 9 and
        # the rewrite is NAMED, never silent.
        raw = {"windows": [_win("A", 12, cbp={"6": 2, "7": 7})]}
        _enforce_count_column(raw)
        assert raw["windows"][0]["qty"] == 9
        g = raw["_count_column_governed"][0]
        assert (g["mark"], g["carried"], g["governed"]) == ("A", 12, 9)
        assert "sheet 6: 2" in g["cells"] and "sheet 7: 7" in g["cells"]
        assert raw["_seam_ledger"]["count_column_governed"]["items"] == [
            "windows:A 12→9"]

    def test_agreeing_qty_not_flagged(self):
        raw = {"windows": [_win("D", 1, cbp={"7": 1})]}
        _enforce_count_column(raw)
        assert raw["windows"][0]["qty"] == 1
        assert "_count_column_governed" not in raw

    def test_unread_cell_contributes_nothing(self):
        # The schedule prints counts; a mark with no cell is flagged and
        # zeroed — never estimated.
        raw = {"windows": [_win("A", 2, cbp={"6": 2}),
                           _win("E", 4)]}
        _enforce_count_column(raw)
        e = next(w for w in raw["windows"] if w["id"] == "E")
        assert e["qty"] == 0 and e["_count_unread"] is True
        assert raw["_count_cells_unread"] == [
            {"kind": "windows", "mark": "E"}]

    def test_no_cells_anywhere_legacy_untouched_but_named(self):
        raw = {"windows": [_win("A", 4), _win("B", 2)]}
        _enforce_count_column(raw)
        assert [w["qty"] for w in raw["windows"]] == [4, 2]
        assert raw["_count_column_absent"] == ["windows"]

    def test_doors_follow_the_same_ruling(self):
        raw = {"doors": [
            {"id": "G1", "qty": 3, "count_by_page": {"6": 1},
             "type_hint": "garage", "width_in": 192, "height_in": 96,
             "exterior_evidence": "elevation"}]}
        _enforce_count_column(raw)
        assert raw["doors"][0]["qty"] == 1
        assert raw["_count_column_governed"][0]["kind"] == "doors"


class TestUnreadRowsNeverReachTheTakeoff:
    def test_aggregation_skips_count_unread_rows(self):
        raw = {"windows": [_win("A", 2, cbp={"6": 2}), _win("E", 4)],
               "walls": [{"label": "front", "width_ft": 40,
                          "height_ft": 9, "gable_triangle_height_ft": 0}]}
        _enforce_count_column(raw)
        m = _aggregate_to_hover_shape(raw)
        # max(1, ...) must not resurrect the zeroed row as 1.
        assert m["window_count"] == 2
        assert not any(str(o.get("id", "")).startswith("E")
                       for o in m.get("windows") or [])


class TestRulingIsNamedOnTheCard:
    def test_rail_names_governed_unread_conflict_merge(self):
        raw = {"windows": [
            _win("A", 12, cbp={"6": 2}, pages=[6]),
            _win("A", 7, cbp={"7": 7}, pages=[7]),
            _win("E", 4),
        ]}
        _enforce_count_column(raw)
        rb = build_blueprint_readback(raw)
        codes = {f["code"] for f in rb["rail"]}
        assert {"count_column_governed", "count_cells_unread",
                "mark_rows_merged"} <= codes
        loud = {f["code"]: f["level"] for f in rb["rail"]}
        assert loud["count_column_governed"] == "loud"
        assert loud["count_cells_unread"] == "loud"
        assert rb["seams"]["count_column_governed"]["removed"] == 1

    def test_prompt_carries_door_count_cells(self):
        # Doors gained the same COUNT-cell fields as windows.
        d = SYSTEM_PROMPT[SYSTEM_PROMPT.index('"doors"'):]
        assert '"count_by_page"' in d and '"schedule_pages"' in d
