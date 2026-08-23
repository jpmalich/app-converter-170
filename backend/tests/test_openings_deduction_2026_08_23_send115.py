"""SEND-115 RULING 1 (Howard ruled 2026-08-23) — DEDUCT OPENINGS, AND
SHOW THE DEDUCTION.

Full area, no threshold. `siding_with_openings_sqft` now carries the NET
(gross − openings) on blueprint jobs that read openings; the takeoff
line prints what was deducted AND what refused; the deduction lands at
AGGREGATE (openings_unplaced) and says so — never attributed per face.
A refused count or size contributes 0 ft², never a guess."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import _aggregate_to_hover_shape  # noqa: E402
from routes.hover import HOVER_MAPPING_SPEC, _openings_ded_note  # noqa: E402

WALLS = [{"label": "front", "width_ft": 40, "height_ft": 10},
         {"label": "back", "width_ft": 40, "height_ft": 10},
         {"label": "left", "width_ft": 25, "height_ft": 10},
         {"label": "right", "width_ft": 25, "height_ft": 10}]


def _spec(item_frag: str):
    rows = [s for s in HOVER_MAPPING_SPEC if item_frag in str(s.get("item"))]
    assert len(rows) == 1
    return rows[0]


def test_openings_deduct_full_area_net_carried():
    m = _aggregate_to_hover_shape({
        "walls": [dict(w) for w in WALLS],
        "windows": [{"id": "A", "qty": 2, "width_in": 36, "height_in": 60}],
        "doors": [{"id": "E1", "qty": 1, "width_in": 36, "height_in": 80,
                   "type_hint": "entry", "exterior_evidence": "schedule_row"}],
    })
    # 2×(3×5) + 1×(3×6.667) = 30 + 20 = 50 ft², no threshold
    d = m["_openings_deduction"]
    assert d["deducted_sqft"] == 50.0
    assert d["complete"] is True and d["refused"] == []
    assert m["siding_with_openings_sqft"] == d["net_sqft"]
    assert d["net_sqft"] == round(d["gross_sqft"] - 50.0, 1)
    assert m["opening_sqft"] == 50.0


def test_refused_count_contributes_nothing_and_is_named():
    m = _aggregate_to_hover_shape({
        "walls": [dict(w) for w in WALLS],
        "windows": [
            {"id": "A", "qty": 2, "width_in": 36, "height_in": 60},
            {"id": "C", "qty": 0, "_count_unread": True,
             "width_in": 36, "height_in": 60},
        ],
        "_schedule_count_unread": [
            {"kind": "windows", "mark": "C",
             "reason": "count cell empty in OCR at the located row"}],
    })
    d = m["_openings_deduction"]
    assert d["deducted_sqft"] == 30.0, "the refused mark added NOTHING"
    assert d["complete"] is False
    assert [r["mark"] for r in d["refused"]] == ["C"]
    assert d["refused"][0]["why"] == "count cell unreadable"


def test_refused_size_contributes_zero_and_is_named():
    m = _aggregate_to_hover_shape({
        "walls": [dict(w) for w in WALLS],
        "doors": [
            {"id": "G1", "qty": 1, "width_in": 192, "height_in": 96,
             "type_hint": "garage", "exterior_evidence": "schedule_row"},
            {"id": "G2", "qty": 1, "type_hint": "garage",
             "exterior_evidence": "schedule_row"},   # size refused
        ],
    })
    d = m["_openings_deduction"]
    assert d["deducted_sqft"] == 128.0
    assert d["complete"] is False
    ref = {r["mark"]: r["why"] for r in d["refused"]}
    assert ref == {"G2": "size refused — contributes 0 ft²"}


def test_no_openings_read_no_deduction_record_none_field():
    """The 2026-08-08 no-alias pin survives BY SCOPE: nothing read ⇒
    nothing deducted ⇒ the field stays None, no gross number ever poses
    as a +10% HOVER basis."""
    m = _aggregate_to_hover_shape({"walls": [dict(w) for w in WALLS]})
    assert m["siding_with_openings_sqft"] is None
    assert "_openings_deduction" not in m


def test_takeoff_line_prints_deduction_refusals_and_aggregate_statement():
    m = {"siding_sqft": 2000.0, "siding_with_openings_sqft": 1852.0,
         "_openings_deduction": {
             "deducted_sqft": 148.0, "gross_sqft": 2000.0,
             "net_sqft": 1852.0, "complete": False,
             "refused": [
                 {"kind": "windows", "mark": "A", "why": "count cell unreadable"},
                 {"kind": "windows", "mark": "B", "why": "count cell unreadable"},
                 {"kind": "windows", "mark": "C", "why": "count cell unreadable"},
                 {"kind": "windows", "mark": "D", "why": "count cell unreadable"},
                 {"kind": "doors", "mark": "G2",
                  "why": "size refused — contributes 0 ft²"}]}}
    s = _spec("Charter Oak Standard color Dutch Lap")
    assert s["extract"](m) == 18.5, "the line prices the NET"
    note = s["note"](m)
    assert "OPENINGS DEDUCTED 148 ft²" in note
    assert "4 window marks refused (A, B, C, D) — count cell unreadable" in note
    assert "1 door mark refused (G2) — size refused" in note
    assert "DEDUCTION INCOMPLETE" in note
    assert "not attributed per face (openings unplaced)" in note
    assert "+10%" not in note, "no false HOVER claim over a blueprint net"


def test_complete_deduction_says_so():
    note = _openings_ded_note({"_openings_deduction": {
        "deducted_sqft": 50.0, "gross_sqft": 1300.0, "net_sqft": 1250.0,
        "complete": True, "refused": []}})
    assert "OPENINGS DEDUCTED 50 ft²" in note
    assert "Deduction complete — every schedule count read" in note
    assert "INCOMPLETE" not in note


def test_lp_lap_line_carries_the_deduction_note_and_prices_net():
    import lp_package as lp
    m = {"siding_sqft": 2000.0, "siding_with_openings_sqft": 1852.0,
         "_waste_pct": 0.0,
         "_openings_deduction": {
             "deducted_sqft": 148.0, "gross_sqft": 2000.0,
             "net_sqft": 1852.0, "complete": True, "refused": []}}
    pkg = lp.assemble_lp_package(dict(m))
    lap = next(l for l in pkg["lines"] if l["name"] == lp.LAP8_ITEM)
    assert "OPENINGS DEDUCTED 148 ft²" in (lap.get("note") or "")
    assert lap["math"]["base_qty"] == round(1852.0 / 100.0 * 11, 2), \
        "lap prices the NET basis, same basis the note names"
    # WITHOUT a deduction record the basis is untouched (hover jobs
    # byte-identical): same measurements minus the record ⇒ gross basis.
    pkg2 = lp.assemble_lp_package(
        {"siding_sqft": 2000.0, "siding_with_openings_sqft": 2068.0,
         "_waste_pct": 0.0})
    lap2 = next(l for l in pkg2["lines"] if l["name"] == lp.LAP8_ITEM)
    assert lap2["math"]["base_qty"] == round(2000.0 / 100.0 * 11, 2)


def test_unplaced_flag_copy_states_aggregate_not_per_face():
    src = (Path(__file__).resolve().parents[2]
           / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")
    keys = re.findall(
        r'"bp\.rb\.consistency\.openings_unplaced":\s*"([^"]+)"', src)
    assert len(keys) == 2, "EN + ES copies"
    assert "lands at AGGREGATE" in keys[0]
    assert "not attributed per face" in keys[0]
    assert "AGREGADO" in keys[1]
