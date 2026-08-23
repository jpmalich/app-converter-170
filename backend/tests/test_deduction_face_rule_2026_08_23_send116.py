"""SEND-116 ITEM 1 (Howard ruled 2026-08-23) — AN OPENING MAY ONLY
DEDUCT FROM A GROSS THAT INCLUDES THE FACE IT SITS ON.

Boni live: gross 200 ft² (chimney chase only, every wall face refused)
minus 198.5 ft² of house-wide schedule openings = net 1.5 ft² on a
33-square house. Dart: gross 0 − 165 FLOORED AT 0 — a silent zero.
Without placement an opening's face is unknown, so the deduction needs
EVERY face in the gross: when any face refuses, THE DEDUCTION REFUSES,
naming both the openings and the faces. No floor anywhere: openings
meeting/exceeding a fully-derived gross refuses as a read inconsistency."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import _aggregate_to_hover_shape  # noqa: E402
from routes.hover import _openings_ded_note  # noqa: E402

DERIVED = [{"label": "front", "width_ft": 40, "height_ft": 10},
           {"label": "back", "width_ft": 40, "height_ft": 10},
           {"label": "left", "width_ft": 25, "height_ft": 10},
           {"label": "right", "width_ft": 25, "height_ft": 10}]
ONE_REFUSED = [dict(w) for w in DERIVED[:3]] + [
    {"label": "right", "width_ft": 25, "height_ft": None}]
WIN = [{"id": "A", "qty": 2, "width_in": 36, "height_in": 60}]  # 30 ft²


def test_any_refused_face_refuses_the_whole_deduction():
    m = _aggregate_to_hover_shape(
        {"walls": [dict(w) for w in ONE_REFUSED],
         "windows": [dict(w) for w in WIN]})
    d = m["_openings_deduction"]
    assert d["deduction_refused"] is True
    assert d["refusal_class"] == "faces_refused"
    assert "right" in d["faces_refused"]
    assert d["openings_sqft_read"] == 30.0
    assert "net_sqft" not in d and "deducted_sqft" not in d, \
        "a refused deduction carries NO number wearing the net's label"
    assert m["siding_with_openings_sqft"] is None
    assert m["siding_sqft"] > 0, "the partial gross itself still reports"


def test_refused_deduction_note_names_openings_and_faces():
    m = _aggregate_to_hover_shape(
        {"walls": [dict(w) for w in ONE_REFUSED],
         "windows": [dict(w) for w in WIN]})
    note = _openings_ded_note(m)
    assert "OPENINGS DEDUCTION REFUSED" in note
    assert "30 ft² of openings read" in note
    assert "right" in note
    assert "may only deduct from a gross that includes its face" in note
    assert "nothing deducted" in note
    assert "Deduction complete" not in note
    assert "OPENINGS DEDUCTED " not in note


def test_no_floor_openings_exceeding_derived_gross_refuse():
    """The dart shape with faces DERIVED: openings ≥ gross is a read
    inconsistency — refused and named, never max(net, 0)."""
    m = _aggregate_to_hover_shape(
        {"walls": [{"label": "front", "width_ft": 2, "height_ft": 10}],
         "windows": [dict(w) for w in WIN]})   # gross 20 < openings 30
    d = m["_openings_deduction"]
    assert d["deduction_refused"] is True
    assert d["refusal_class"] == "openings_exceed_gross"
    assert m["siding_with_openings_sqft"] is None
    note = _openings_ded_note(m)
    assert "meet or exceed the derived gross" in note
    assert "reads disagree" in note


def test_all_faces_derived_deduction_still_applies():
    m = _aggregate_to_hover_shape(
        {"walls": [dict(w) for w in DERIVED],
         "windows": [dict(w) for w in WIN]})
    d = m["_openings_deduction"]
    assert not d.get("deduction_refused")
    assert d["deducted_sqft"] == 30.0
    assert m["siding_with_openings_sqft"] == d["net_sqft"] == \
        d["gross_sqft"] - 30.0


def test_refused_deduction_still_names_mark_refusals():
    m = _aggregate_to_hover_shape(
        {"walls": [dict(w) for w in ONE_REFUSED],
         "windows": [dict(w) for w in WIN] + [
             {"id": "C", "qty": 0, "_count_unread": True,
              "width_in": 36, "height_in": 60}],
         "_schedule_count_unread": [
             {"kind": "windows", "mark": "C",
              "reason": "count cell empty in OCR at the located row"}]})
    note = _openings_ded_note(m)
    assert "OPENINGS DEDUCTION REFUSED" in note
    assert "1 window mark refused (C) — count cell unreadable" in note
