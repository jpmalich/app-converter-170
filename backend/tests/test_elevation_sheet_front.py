"""Elevation Sheet FRONT (EL-1) — Phase 1 pins (build directive 2026-07-18).

Pass criteria pinned here:
  • every value data-bound to its named source (sealed key / AI run) —
    the corrected key values appear (8'-10¼", NEVER the old 8.96-derived)
  • openings carry AI-READ tags + door-anchored bbox sills
  • deviation box states both values + tape governs
  • the route is READ-ONLY (zero writes — static + behavioral pin)
  • September protection: renderer route exists standalone; auth-gated
"""
import re
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"   # Mark Letrick EST-373526
LETRICK_RUN = "d66794488ef848509446431b355db8e5"        # archived: elevation-sheet-pin


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def sheet(session):
    r = session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/front", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_auth_required():
    r = requests.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/front", timeout=15)
    assert r.status_code in (401, 403)


def test_wall_binds_corrected_sealed_key(sheet):
    w = sheet["wall"]
    assert w["width_ft"] == 54.0
    assert w["width_label"] == "54'-0\""
    assert w["width_tag"] == "TAPED"
    assert "EST-191890" in w["width_source"]
    # CORRECTED key: 25 × 4.25" = 8.854' = 8'-10¼" — never the 8.96-derived
    assert w["height_ft"] == 8.854
    assert w["height_label"] == "8'-10¼\""
    assert w["height_tag"] == "TAPED-DERIVED"
    assert "25" in w["height_formula"] and "4.25" in w["height_formula"]
    assert w["courses"] == 25 and w["exposure_in"] == 4.25
    assert w["area_sqft"] == 478.1  # computed 54 × 8.854, matches key


def test_old_derivation_absent(sheet):
    import json
    dump = json.dumps(sheet)
    assert "8.96" not in dump
    assert "8'-11½" not in dump  # pre-correction label


def test_deviation_box_tape_governs(sheet):
    d = sheet["deviation"]
    assert d is not None
    assert d["ai_width_ft"] == 50
    assert d["ai_height_ft"] == 8.6
    assert d["ai_counts"] == [22, 23, 24]  # parsed from the run's own per-photo notes
    assert d["governs"] == "tape"
    assert d["delta_width_label"].startswith("-4'")
    assert d["run_short"] == LETRICK_RUN[:8]


def test_openings_positions_and_tags(sheet):
    ops = sheet["openings"]
    assert [o["tag"] for o in ops] == ["W1", "W2", "D1", "W3"]
    assert [o["center_ft"] for o in ops] == [5.5, 24.0, 34.0, 44.0]
    assert all(o["position_tag"] == "AI-READ ✓" for o in ops)
    assert all(o["confirmed"] for o in ops)
    assert not any(o["collision"] for o in ops)
    d1 = next(o for o in ops if o["tag"] == "D1")
    assert d1["sill_in"] == 0.0  # doors sit at grade — anchor by construction
    for o in ops:
        if o["tag"].startswith("W"):
            # door-anchored bbox sills: data-bound, positive, plausible DH range
            assert o["sill_tag"] == "ESTIMATED"
            assert 20 < o["sill_in"] < 48, o
            # opening must fit under the tape-governed wall height
            assert o["sill_in"] + o["height_in"] < 8.854 * 12


def test_geometry_basis_line(sheet):
    gb = sheet["geometry_basis"]
    assert "EST-191890" in gb["walls"] and "tape" in gb["walls"]
    assert LETRICK_RUN[:8] in gb["openings"]
    assert sheet["run"]["run_id"] == LETRICK_RUN


def test_route_is_read_only_static():
    src = (Path(__file__).resolve().parent.parent / "routes" / "elevation_sheets.py").read_text()
    for verb in ("insert_one", "insert_many", "update_one", "update_many",
                 "delete_one", "delete_many", "replace_one", "bulk_write"):
        assert verb not in src, f"elevation_sheets.py performs a write: {verb}"


def test_route_is_read_only_behavioral(session):
    from pymongo import MongoClient
    import os
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    before = db.estimates.find_one({"id": LETRICK_EST}, {"_id": 0})
    session.get(f"{API}/estimates/{LETRICK_EST}/elevation-sheet/front", timeout=30)
    after = db.estimates.find_one({"id": LETRICK_EST}, {"_id": 0})
    assert before == after
    client.close()


def test_pin_run_is_archived_unexpirable():
    from pymongo import MongoClient
    import os
    client = MongoClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    f = db.fixture_runs.find_one({"run_id": LETRICK_RUN}, {"_id": 0, "artifact_reasons": 1})
    assert f is not None, "Letrick run must be TTL-archived (elevation-sheet-pin)"
    assert "elevation-sheet-pin" in (f.get("artifact_reasons") or [])
    client.close()


def test_removed_opening_does_not_render_then_reset(session):
    """Verb machinery e2e: user_removed schedule row (72×60 window, group
    of 1 → raw front-w3) drops from the sheet; reset restores it."""
    key = f"open:{LETRICK_RUN[:8]}:1"
    url = f"{API}/estimates/{LETRICK_EST}/openings-review"
    sheet_url = f"{API}/estimates/{LETRICK_EST}/elevation-sheet/front"
    r = session.post(url, json={"key": key, "action": "remove"}, timeout=20)
    assert r.status_code == 200, r.text
    try:
        s = session.get(sheet_url, timeout=30).json()
        assert [o["tag"] for o in s["openings"]] == ["W1", "W2", "D1"]
        assert not any(o["width_in"] == 72 for o in s["openings"])
        # three-key contract (pin AMENDED by ruling 2026-07-18: {windows, doors, vents})
        assert s["opening_counts"] == {"windows": 2, "doors": 1, "vents": 0}
    finally:
        rr = session.post(url, json={"key": key, "action": "reset"}, timeout=20)
        assert rr.status_code == 200, rr.text
    s = session.get(sheet_url, timeout=30).json()
    assert [o["tag"] for o in s["openings"]] == ["W1", "W2", "D1", "W3"]
