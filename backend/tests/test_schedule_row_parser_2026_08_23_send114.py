"""SEND-114 pins — THE SCHEDULE ROW PARSER (rows, not strings).

The row is the evidence: a count cell that will not OCR can still be
located BY ITS ROW. Where a count cannot be established from its row it
REFUSES naming the mark — never a collapse to 1 (a floor that looks
like a count produced the 4; honoring unverified claims produced the
20). Doors and windows stay separate; the E3 class (exterior door rows
the model missed) is recovered from the printed row itself.

Stored-OCR pins run against the two houses' latest runs READ-ONLY on
deep copies — no estimate is written. A CHECK, NEVER A TARGET: the pins
below pin observed parser behavior; nothing tunes toward 16, 4 or 526.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, "/app/backend")


# ── register pin ──────────────────────────────────────────────────────

def test_register_carries_the_count_cell_finding():
    from ocr_geometry import RULINGS_REGISTER
    f = "\n".join(RULINGS_REGISTER["findings"])
    assert "VERIFICATION MECHANISM COULD NOT REACH IT" in f
    assert "NOT AN ARGUMENT TO WEAKEN THE POLICY" in f
    assert "schedule ROW needs its own locator" in f
    assert "never collapses to 1" in f
    assert "NAMED UNPLACED BUCKET" in f


# ── synthetic-table unit pins ─────────────────────────────────────────

def _u(raw, x, y, w=1.5, h=0.35):
    return {"raw": raw, "norm": raw.upper().replace(" ", ""),
            "src": "upright",
            "loc": {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h}}


def _ot(rows):
    return {"1": {"page_w": 1000, "page_h": 800, "runs": rows}}


def _window_table(count_cells):
    rows = [_u("WINDOW SCHEDULE", 10, 50),
            _u("OPENING ID", 10, 52), _u("PRODUCT CODE", 14, 52),
            _u("SIZE", 20, 52), _u("COUNT", 26, 52),
            _u("LIBRARY NAME", 30, 52),
            _u("A", 10, 53), _u("SH 3-0_5-0", 14, 53),
            _u("2'-11\"x4'-11\"", 20, 53), _u("HUNG", 30, 53),
            _u("B", 10, 54.2), _u("SH 3-0_4-0", 14, 54.2),
            _u("2'-11\"x3'-11\"", 20, 54.2), _u("HUNG", 30, 54.2)]
    rows += count_cells
    return _ot(rows)


def test_row_read_count_governs_and_empty_cell_refuses():
    from schedule_read import read_schedule_counts
    raw = {"_ocr_text_by_page": _window_table([_u("9", 26, 53)]),
           "windows": [{"id": "A", "product_code": "SH 3-0_5-0"},
                       {"id": "B", "product_code": "SH 3-0_4-0"}],
           "doors": []}
    read_schedule_counts(raw)
    a, b = raw["windows"]
    assert a["qty"] == 9 and a["_row_count"] == 9      # row cell = evidence
    assert b["qty"] == 0 and b.get("_count_unread") is True   # NEVER 1
    unread = raw["_schedule_count_unread"]
    assert unread[0]["mark"] == "B"
    assert "empty" in unread[0]["reason"]


def test_ambiguous_count_cell_refuses():
    from schedule_read import read_schedule_counts
    raw = {"_ocr_text_by_page": _window_table(
               [_u("9", 26, 53), _u("2", 27.5, 53.1)]),
           "windows": [{"id": "A", "product_code": "SH 3-0_5-0"}],
           "doors": []}
    read_schedule_counts(raw)
    assert raw["windows"][0].get("_count_unread") is True
    assert "ambiguous" in raw["_schedule_count_unread"][0]["reason"]


def test_locator_verified_cells_stand_untouched():
    from schedule_read import read_schedule_counts
    raw = {"_ocr_text_by_page": _window_table([]),
           "windows": [{"id": "A", "product_code": "SH 3-0_5-0",
                        "qty": 2, "count_by_page": {"1": 2}}],
           "doors": []}
    read_schedule_counts(raw)
    assert raw["windows"][0]["qty"] == 2
    assert "_count_unread" not in raw["windows"][0]


def test_no_count_column_means_no_jurisdiction():
    from schedule_read import read_schedule_counts
    ot = _ot([_u("WINDOW SCHEDULE", 10, 50), _u("SIZE", 20, 52),
              _u("2'-11\"x4'-11\"", 20, 53)])
    raw = {"_ocr_text_by_page": ot,
           "windows": [{"id": "A", "qty": None}], "doors": []}
    read_schedule_counts(raw)
    assert raw["windows"][0]["qty"] is None            # legacy stands
    assert not raw.get("_schedule_count_unread")


def test_e3_class_door_row_recovered_and_interior_rows_never():
    from schedule_read import read_schedule_counts
    ot = _ot([_u("DOOR SCHEDULE", 10, 50),
              _u("SIZE", 16, 52), _u("TYPE", 24, 52),
              _u("E2", 10, 53), _u("3'-0\"x6'-8\"", 16, 53),
              _u("PANEL FRONT DOOR", 24, 53),
              _u("E3", 10, 54.2), _u("6'-0\"x6'-8\"", 16, 54.2),
              _u("SLDING DOOR Right Hand Glass", 24, 54.2),
              _u("E4", 10, 55.4), _u("2'-6\"", 16, 55.4),
              _u("2-6 HOLLOW CORE", 24, 55.4)])
    raw = {"_ocr_text_by_page": ot, "windows": [],
           "doors": [{"id": "E2", "qty": 1, "count_by_page": {"1": 1}}]}
    read_schedule_counts(raw)
    marks = [d["id"] for d in raw["doors"]]
    assert "E3" in marks and "E4" not in marks         # interior excluded
    e3 = next(d for d in raw["doors"] if d["id"] == "E3")
    assert e3["_row_recovered"] is True
    assert e3["type_hint"] == "sliding_glass_patio"
    assert e3["qty"] == 1                # one row = one door (no count col)
    assert e3.get("width_in") == 72.0 and e3.get("height_in") == 80.0
    assert raw["_schedule_rows_recovered"][0]["mark"] == "E3"


# ── stored-OCR pins (both houses, read-only deep copies) ─────────────

def _stored_raw(eid):
    from dotenv import load_dotenv
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"],
                     serverSelectionTimeoutMS=3000)[os.environ["DB_NAME"]]
    run = db.ai_blueprint_runs.find_one({"estimate_id": eid,
                                         "status": "done"},
                                        sort=[("created_at", -1)])
    if not run:
        pytest.skip("env:fixture_data: stored blueprint run absent")
    raw = copy.deepcopy((run.get("result") or {}).get("raw_ai") or {})
    if not raw.get("_ocr_text_by_page") and raw.get("_ocr_text_ref"):
        raw["_ocr_text_by_page"] = (db.ai_blueprint_ocr.find_one(
            {"run_id": raw["_ocr_text_ref"]},
            {"pages": 1}) or {}).get("pages")
    return raw


def test_letrick_rows_read_1_4_3_and_refuse_c_f():
    from schedule_read import read_schedule_counts
    raw = _stored_raw("264b6230-5d0f-49ea-b07d-8d33a537f293")
    read_schedule_counts(raw)
    got = {c["mark"]: c["count"] for c in raw["_schedule_row_counts"]}
    assert got == {"A": 1, "B": 4, "D": 3}
    refused = {u["mark"] for u in raw["_schedule_count_unread"]}
    assert refused == {"C", "F"}


def test_boni_windows_refuse_honestly_and_e3_recovers():
    from schedule_read import read_schedule_counts
    raw = _stored_raw("65bcb89d-8291-4b84-920c-7b503273f332")
    read_schedule_counts(raw)
    refused = {u["mark"] for u in raw["_schedule_count_unread"]
               if u["kind"] == "windows"}
    assert refused == {"A", "B", "C", "D"}     # count cells not in OCR
    rec = raw.get("_schedule_rows_recovered") or []
    assert [m["mark"] for m in rec] == ["E3"]
    doors = [d["id"] for d in raw["doors"]]
    assert set(doors) >= {"E2", "G1", "G2", "E3"}   # 4 exterior — sealed 4


# ── the wiring is structural ─────────────────────────────────────────

def test_pipeline_wiring_and_no_floor():
    src = open("/app/backend/routes/ai_blueprint.py").read()
    assert "read_schedule_counts(raw)" in src
    assert "schedule_count_unread" in src        # flags disclosed
    assert "openings_unplaced" in src            # named unplaced bucket
    d = open("/app/frontend/src/lib/dictionaries.js").read()
    for code in ("schedule_count_unread", "schedule_row_recovered",
                 "openings_unplaced"):
        assert d.count(f"bp.rb.consistency.{code}") == 2   # EN + ES
