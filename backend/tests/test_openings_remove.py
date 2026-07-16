from creds_for_tests import TEST_PASSWORD
"""'Not present' removal verb + extraction-spend admin line (ruled 2026-07-15).

Pins:
  • a removed opening appears NOWHERE in counts, trim math (540 wrap,
    starter entry-width deduction), or quote surfaces
  • removal is provenance-logged (user_removed, by/at) and revertible
  • the phantom B×1 on the cloned comparison run is the ruled test fixture
  • extraction spend is ADMIN BOUNDARY ONLY (leak-scan: no cost data on
    contractor surfaces)
"""
import json
import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = TEST_PASSWORD
SOURCE_RUN = "2a2e8a1227d145a588b71387903e1320"  # comparison run1_opus (11 windows)
FIXTURE_RUN_ID = "test-bp-remove-fixture"
EST_ID = "db82ec7a-3177-406d-a602-927255e9e10e"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


# ── Unit: _apply_openings_review removal semantics ────────────────────

def _items(*rows):
    out = []
    for i, r in enumerate(rows):
        out.append({"key": f"open:x:{i}", "index": i, "elevation": r.get("elevation", "front"),
                    "type": r["type"], "count": r.get("count", 1),
                    "status": r.get("status", "unconfirmed"),
                    "corrected_type": r.get("corrected_type")})
    return out


def test_removed_window_leaves_counts_and_schedule():
    from routes.lp_package_routes import _apply_openings_review
    meas = {
        "window_count": 11, "entry_door_count": 2,
        "_ai_openings_schedule": [
            {"type": "window", "count": 10},
            {"type": "window", "count": 1},   # the phantom
            {"type": "entry_door", "count": 2, "width_in": 36},
        ],
    }
    items = _items(
        {"type": "window", "count": 10},
        {"type": "window", "count": 1, "status": "user_removed"},
        {"type": "entry_door", "count": 2},
    )
    adj, summary = _apply_openings_review(meas, items)
    assert adj["window_count"] == 10
    assert len(adj["_ai_openings_schedule"]) == 2
    assert all(r.get("count") != 1 or r["type"] != "window" for r in adj["_ai_openings_schedule"])
    assert summary["removed"] == 1 and summary["removals"]
    # source measurements untouched (revertibility = derive-time only)
    assert meas["window_count"] == 11 and len(meas["_ai_openings_schedule"]) == 3


def test_removed_entry_door_leaves_starter_deduction():
    """Trim-math pin: starter deduction iterates the schedule directly —
    a removed entry door must not deduct its width."""
    from routes.lp_package_routes import _apply_openings_review
    meas = {
        "entry_door_count": 2,
        "_ai_openings_schedule": [
            {"type": "entry_door", "count": 1, "width_in": 36},
            {"type": "entry_door", "count": 1, "width_in": 36},
        ],
    }
    items = _items(
        {"type": "entry_door", "count": 1},
        {"type": "entry_door", "count": 1, "status": "user_removed"},
    )
    adj, _ = _apply_openings_review(meas, items)
    assert adj["entry_door_count"] == 1
    ded = sum(r["width_in"] / 12.0 for r in adj["_ai_openings_schedule"]
              if r["type"] == "entry_door")
    assert ded == 3.0  # one 36" door, not two


def test_corrected_row_retypes_in_schedule():
    from routes.lp_package_routes import _apply_openings_review
    meas = {"entry_door_count": 2, "patio_door_count": 0,
            "_ai_openings_schedule": [
                {"type": "entry_door", "count": 1, "width_in": 36},
                {"type": "entry_door", "count": 1, "width_in": 72},
            ]}
    items = _items(
        {"type": "entry_door", "count": 1},
        {"type": "entry_door", "count": 1, "status": "user_corrected",
         "corrected_type": "patio_door"},
    )
    adj, summary = _apply_openings_review(meas, items)
    assert adj["entry_door_count"] == 1 and adj["patio_door_count"] == 1
    assert adj["_ai_openings_schedule"][1]["type"] == "patio_door"
    assert summary["corrected"] == 1


def test_items_carry_delete_guard_info():
    from routes.lp_package_routes import _openings_items
    run = {"run_id": "x" * 16, "page_paths": "", "result": {"measurements": {
        "_ai_openings_schedule": [
            {"type": "entry_door", "count": 1, "size_label": "36×80", "locations": []},
            {"type": "vent", "count": 1, "size_label": "12×12", "locations": []},
        ]}}}
    items = _openings_items(run, None)
    assert any("starter" in c for c in items[0]["carries"])
    assert items[1]["carries"] == []


# ── E2E: the ruled fixture — phantom B×1 on the cloned comparison run ──

@pytest.fixture(scope="module")
def phantom_fixture(mongo_db):
    # fixture_runs fallback: comparison runs outlive the 24h TTL there
    # (restored 2026-07-16 after TTL loss — artifact pin).
    src = mongo_db.ai_blueprint_runs.find_one({"run_id": SOURCE_RUN}, {"_id": 0}) \
        or mongo_db.fixture_runs.find_one({"run_id": SOURCE_RUN}, {"_id": 0})
    assert src, "comparison run1_opus missing"
    src.pop("artifact_reasons", None)
    from routes.ai_blueprint import _aggregate_to_hover_shape
    meas = _aggregate_to_hover_shape(dict(src["result"]["raw_ai"]))
    src["result"]["measurements"] = {**src["result"]["measurements"],
                                     "_ai_openings_schedule": meas["_ai_openings_schedule"]}
    src["run_id"] = FIXTURE_RUN_ID
    mongo_db.ai_blueprint_runs.delete_many({"run_id": FIXTURE_RUN_ID})
    mongo_db.ai_blueprint_runs.insert_one(src)
    yield meas["_ai_openings_schedule"]
    mongo_db.ai_blueprint_runs.delete_many({"run_id": FIXTURE_RUN_ID})
    mongo_db.estimates.update_one({"id": EST_ID}, {"$unset": {"lp_openings_review": ""}})


def _preview(session):
    r = session.post(f"{API}/estimates/{EST_ID}/lp-package/preview",
                     json={"run_id": FIXTURE_RUN_ID}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _wrap_note(pkg):
    for l in pkg.get("lines") or []:
        note = str(l.get("note") or "")
        if "windows 4-side" in note:
            return note
    return ""


def test_phantom_b_removal_e2e(session, phantom_fixture):
    pkg = _preview(session)
    assert "(11×14')" in _wrap_note(pkg), _wrap_note(pkg)
    items = pkg["openings_review"]["items"]
    phantom = next(it for it in items
                   if it["type"] == "window" and it["count"] == 1
                   and it["size_label"].startswith("B"))
    assert phantom["carries"], "delete-guard info missing on window item"

    # remove — provenance-logged
    r = session.post(f"{API}/estimates/{EST_ID}/openings-review",
                     json={"key": phantom["key"], "action": "remove"}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "user_removed" and body["by"] and body["at"]

    # pin: removed opening appears nowhere in counts / trim math / quote surface
    pkg2 = _preview(session)
    assert "(10×14')" in _wrap_note(pkg2), _wrap_note(pkg2)
    orv = pkg2["openings_review"]
    assert orv["removed"] == 1 and orv["removals"]
    it2 = next(it for it in orv["items"] if it["key"] == phantom["key"])
    assert it2["status"] == "user_removed" and it2["by"] and it2["at"]

    # revertible
    r = session.post(f"{API}/estimates/{EST_ID}/openings-review",
                     json={"key": phantom["key"], "action": "reset"}, timeout=15)
    assert r.status_code == 200
    pkg3 = _preview(session)
    assert "(11×14')" in _wrap_note(pkg3)
    assert pkg3["openings_review"]["removed"] == 0


# ── Extraction-spend line: admin boundary + leak-scan ─────────────────

def test_admin_lp_estimates_carry_extraction_spend():
    token = os.environ["SUPPLIER_ADMIN_TOKEN"]
    r = requests.get(f"{API}/admin/lp-estimates", headers={"X-Admin-Token": token}, timeout=30)
    assert r.status_code == 200
    rows = r.json()["estimates"]
    assert rows and all("extraction_spend_usd" in e and "extraction_runs" in e for e in rows)
    tracked = [e for e in rows if e["id"] == EST_ID]
    if tracked:  # comparison runs carry live telemetry → spend must be > 0
        assert tracked[0]["extraction_runs"] >= 6
        assert tracked[0]["extraction_spend_usd"] > 0


def test_leak_scan_no_cost_data_on_contractor_preview(session, phantom_fixture):
    r = session.post(f"{API}/estimates/{EST_ID}/lp-package/preview",
                     json={"run_id": FIXTURE_RUN_ID}, timeout=30)
    assert r.status_code == 200
    text = r.text
    for needle in ("extraction_spend", "token_usage", "dealer_cost", "margin_pct", "cost_usd"):
        assert needle not in text, f"leak-scan: {needle} on contractor surface"


# ── Cost redaction ruling (2026-07-15): run payloads carry no cost keys ──

COST_NEEDLES = ('"cost_usd"', '"cost_estimate_usd"', '"token_usage"',
                '"_usage"', '"_reconciliation_usage"')
LETRICK_EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"


def _assert_no_cost(text, surface):
    for needle in COST_NEEDLES:
        assert needle not in text, f"leak-scan: {needle} on {surface}"


def test_blueprint_status_redacts_cost(session):
    r = session.get(f"{API}/measure/ai-blueprint/status/{SOURCE_RUN}", timeout=30)
    assert r.status_code == 200
    assert (r.json().get("result") or {}).get("measurements")  # results intact
    _assert_no_cost(r.text, "blueprint status")


def test_photo_status_and_latest_redact_cost(session):
    r = session.get(f"{API}/measure/ai-measure/latest-for-estimate/{LETRICK_EST}", timeout=30)
    assert r.status_code == 200
    _assert_no_cost(r.text, "photo latest-for-estimate")
    run_id = (r.json().get("run") or {}).get("run_id")
    if run_id:
        r2 = session.get(f"{API}/measure/ai-measure/status/{run_id}", timeout=30)
        assert r2.status_code == 200
        _assert_no_cost(r2.text, "photo status")


def test_history_and_debug_runs_redact_cost(session):
    r = session.get(f"{API}/measure/ai-measure/history/{LETRICK_EST}", timeout=30)
    assert r.status_code == 200 and "runs" in r.json()
    _assert_no_cost(r.text, "model-comparison history")
    r2 = session.get(f"{API}/measure/ai-measure/debug-runs/{LETRICK_EST}", timeout=30)
    assert r2.status_code == 200
    _assert_no_cost(r2.text, "debug run picker")


def test_db_telemetry_untouched_by_redaction(mongo_db):
    # Redaction is response-side only — the admin spend line reads the DB
    # (fixture_runs archive after the 24h live-collection TTL).
    doc = mongo_db.ai_blueprint_runs.find_one({"run_id": SOURCE_RUN}) \
        or mongo_db.fixture_runs.find_one({"run_id": SOURCE_RUN})
    assert (doc["result"].get("cost_usd") or 0) > 0
    assert doc["result"].get("token_usage")


# ── Journey-log ratify events (approved 2026-07-15) ──────────────────

def test_ratify_events_append_to_tracking(session, phantom_fixture, mongo_db):
    pkg = _preview(session)
    item = next(it for it in pkg["openings_review"]["items"] if it["type"] == "window")
    for action, ev in (("remove", "opening.removed"), ("reset", "opening.reset")):
        r = session.post(f"{API}/estimates/{EST_ID}/openings-review",
                         json={"key": item["key"], "action": action}, timeout=15)
        assert r.status_code == 200
        est = mongo_db.estimates.find_one({"id": EST_ID}, {"tracking": 1})
        evs = [t for t in (est.get("tracking") or []) if t.get("type") == ev]
        assert evs and evs[-1]["meta"]["key"] == item["key"] and evs[-1]["meta"]["by"]


# ── Whole-board starter pin (traced 2026-07-15 — not a violation; pinned) ──

def test_starter_prices_whole_boards_only(session):
    import math
    r = session.post(f"{API}/estimates/{LETRICK_EST}/lp-package/preview", json={}, timeout=30)
    assert r.status_code == 200
    ripped = [l for l in r.json()["lines"]
              if l.get("priced_unit") == "per ripped source board" and l.get("pricing_status") == "priced"]
    assert ripped, "no rip-priced lines on the letrick preview"
    for l in ripped:
        pcs = l["pieces_added"]
        assert isinstance(pcs, int) and pcs >= 1
        assert abs(l["line_sell"] - round(l["unit_sell"] * pcs, 2)) < 0.005, l["name"]
        d = (l.get("_derivation") or {})
        if d.get("kind") == "starter" and d.get("starter_lf"):
            assert pcs == math.ceil(d["starter_lf"] / 48.0)
