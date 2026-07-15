"""Contractor Window Quotes labor divergence — GATE pins (approved 2026-07-15).

Pins:
  • admin boundary: every endpoint 403s without X-Admin-Token
  • compare = side-by-side ISS vs proposed with per-item deltas
  • values HELD: draft starts empty, approve-on-empty is a 400
  • gate: approved_contractor_window_labor() returns {} until approved;
    any draft edit re-opens the gate (status back to draft)
  • no contractor-visible surface consumes draft rates
"""
import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API = "https://app-converter-170.preview.emergentagent.com/api"
TOKEN = os.environ["SUPPLIER_ADMIN_TOKEN"]
H = {"X-Admin-Token": TOKEN}
ITEM = "Window DH/Slider - Pocket Install"  # ISS labor $170


def _mongo():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _gate_value():
    """Run the sanctioned consumer on a per-call loop + client (avoids
    the known Motor closed-loop recurrence in pytest)."""
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    import routes.window_labor_admin as wla

    async def go():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        orig = wla.db
        wla.db = client[os.environ["DB_NAME"]]
        try:
            return await wla.approved_contractor_window_labor()
        finally:
            wla.db = orig
            client.close()

    return asyncio.run(go())


@pytest.fixture(scope="module", autouse=True)
def leave_as_found():
    db = _mongo()
    before = db.admin_settings.find_one({"id": "window_labor_divergence"}, {"_id": 0})
    yield
    db.admin_settings.delete_one({"id": "window_labor_divergence"})
    if before:
        db.admin_settings.insert_one(before)


def test_admin_boundary():
    assert requests.get(f"{API}/admin/window-labor/compare", timeout=15).status_code == 403
    assert requests.put(f"{API}/admin/window-labor/draft", json={"proposed": {ITEM: 200}}, timeout=15).status_code == 403
    assert requests.post(f"{API}/admin/window-labor/approve", timeout=15).status_code == 403


def test_values_held_and_empty_approve_blocked():
    _mongo().admin_settings.delete_one({"id": "window_labor_divergence"})
    r = requests.get(f"{API}/admin/window-labor/compare", headers=H, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["values_held"] is True and d["status"] == "draft"
    assert all(row["proposed_lab"] is None for row in d["rows"])
    assert any(row["name"] == ITEM and row["iss_lab"] == 170.0 for row in d["rows"])
    r = requests.post(f"{API}/admin/window-labor/approve", headers=H, timeout=15)
    assert r.status_code == 400 and "held" in r.json()["detail"].lower()


def test_draft_deltas_and_gate_lifecycle():
    # draft a rate → per-item delta computed
    r = requests.put(f"{API}/admin/window-labor/draft", json={"proposed": {ITEM: 212.5}}, headers=H, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "draft"
    d = requests.get(f"{API}/admin/window-labor/compare", headers=H, timeout=15).json()
    row = next(x for x in d["rows"] if x["name"] == ITEM)
    assert row["proposed_lab"] == 212.5 and row["delta_usd"] == 42.5 and row["delta_pct"] == 25.0
    assert d["values_held"] is False

    # GATE: nothing consumable until approved
    assert _gate_value() == {}

    # approve → consumable
    r = requests.post(f"{API}/admin/window-labor/approve", headers=H, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert _gate_value() == {ITEM: 212.5}

    # any edit re-opens the gate
    r = requests.put(f"{API}/admin/window-labor/draft", json={"proposed": {ITEM: 215}}, headers=H, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "draft"
    assert _gate_value() == {}


def test_draft_validation():
    for bad in ({"proposed": {"Not A Real Item": 100}},
                {"proposed": {ITEM: "lots"}},
                {"proposed": {ITEM: -5}},
                {"proposed": {ITEM: 99999}},
                {}):
        r = requests.put(f"{API}/admin/window-labor/draft", json=bad, headers=H, timeout=15)
        assert r.status_code == 400, bad


def test_null_clears_draft_entry():
    requests.put(f"{API}/admin/window-labor/draft", json={"proposed": {ITEM: None}}, headers=H, timeout=15)
    d = requests.get(f"{API}/admin/window-labor/compare", headers=H, timeout=15).json()
    row = next(x for x in d["rows"] if x["name"] == ITEM)
    assert row["proposed_lab"] is None and d["values_held"] is True
