from creds_for_tests import TEST_PASSWORD
"""Split ruling 2026-07-14 — customer-journey event instrumentation.

Pins:
  • quote.viewed logged on accept-page GET; quote.accepted on accept POST
  • qr.scanned logged on /m/ and /r/ public serves (surface-tagged)
  • quote.sent trigger wired (source pin — real email off-limits)
  • CUSTOMER INVISIBILITY: no public response ever mentions tracking
  • tracking[] capped at 500 events (hot QR can't bloat the estimate doc)
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import BASE_URL  # env-derived (un-hardcoded 2026-07-23)
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = TEST_PASSWORD


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def _run_fresh(module, fn_name, *args, **kwargs):
    """Fresh loop + fresh motor client per call — order-independent (the
    process-global db client may be bound to another module's closed loop)."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    old_db = module.db
    module.db = client[os.environ["DB_NAME"]]
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(getattr(module, fn_name)(*args, **kwargs))
    finally:
        module.db = old_db
        loop.close()
        client.close()


def _events(mongo_db, est_id, etype=None):
    doc = mongo_db.estimates.find_one({"id": est_id}, {"tracking": 1}) or {}
    evs = doc.get("tracking") or []
    return [e for e in evs if etype is None or e.get("type") == etype]


def test_accept_page_view_and_accept_events(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Events Accept"}, timeout=15).json()["id"]
    token = "evt-" + uuid.uuid4().hex
    mongo_db.estimates.update_one({"id": est_id}, {"$set": {"accept_token": token}})
    try:
        r = requests.get(f"{API}/public/accept/{token}", timeout=15)
        assert r.status_code == 200, r.text
        # CUSTOMER INVISIBILITY — the response must not reveal tracking
        assert "tracking" not in json.dumps(r.json()).lower()
        viewed = _events(mongo_db, est_id, "quote.viewed")
        assert len(viewed) == 1 and viewed[0]["meta"]["surface"] == "accept_page"
        assert viewed[0]["at"]

        r2 = requests.post(f"{API}/public/accept/{token}", json={"note": ""}, timeout=15)
        assert r2.status_code == 200, r2.text
        assert "tracking" not in json.dumps(r2.json()).lower()
        assert len(_events(mongo_db, est_id, "quote.accepted")) == 1
    finally:
        requests.delete(f"{API}/estimates/{est_id}", timeout=15)
        mongo_db.estimates.delete_one({"id": est_id})
        mongo_db.estimates_trash.delete_one({"id": est_id})


def test_qr_scan_events_material_and_accuracy(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Events QR"}, timeout=15).json()["id"]
    now = datetime.now(timezone.utc)
    m_tok = "evtm-" + uuid.uuid4().hex[:20]
    r_tok = "evtr-" + uuid.uuid4().hex[:20]
    base = {"estimate_id": est_id, "company_id": "evt-co", "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=90)).isoformat(), "revoked": False, "meta": {}}
    mongo_db.lp_material_list_snapshots.insert_one(
        {**base, "token": m_tok, "snapshot": {"lines": [], "summary": {}}, "content_hash": "x"})
    mongo_db.accuracy_report_snapshots.insert_one(
        {**base, "token": r_tok, "html": "<html></html>", "content_hash": "x"})
    try:
        rm = requests.get(f"{API}/public/lp-material-list/{m_tok}", timeout=20)
        assert rm.status_code == 200, rm.text
        assert "tracking" not in json.dumps(rm.json()).lower()
        rr = requests.get(f"{API}/public/accuracy-report/{r_tok}", timeout=20)
        assert rr.status_code == 200, rr.text
        assert "tracking" not in json.dumps(rr.json()).lower()
        scans = _events(mongo_db, est_id, "qr.scanned")
        surfaces = sorted(e["meta"]["surface"] for e in scans)
        assert surfaces == ["accuracy_report", "material_list"], scans
        assert all("expired" not in e["meta"] for e in scans)
        # expired link: scan still logged (callback intel), serve 410s
        mongo_db.lp_material_list_snapshots.update_one(
            {"token": m_tok}, {"$set": {"expires_at": (now - timedelta(days=1)).isoformat()}})
        rexp = requests.get(f"{API}/public/lp-material-list/{m_tok}", timeout=20)
        assert rexp.status_code == 410
        expired = [e for e in _events(mongo_db, est_id, "qr.scanned") if e["meta"].get("expired")]
        assert len(expired) == 1
    finally:
        requests.delete(f"{API}/estimates/{est_id}", timeout=15)
        mongo_db.estimates.delete_one({"id": est_id})
        mongo_db.estimates_trash.delete_one({"id": est_id})
        mongo_db.lp_material_list_snapshots.delete_one({"token": m_tok})
        mongo_db.accuracy_report_snapshots.delete_one({"token": r_tok})


def test_quote_sent_trigger_wired_source_pin():
    src = (Path(__file__).resolve().parent.parent / "routes" / "email.py").read_text()
    send_idx = src.index("resend.Emails.send")
    ret_idx = src.index("return {", send_idx)
    assert 'log_estimate_event(est_id, "quote.sent"' in src[send_idx:ret_idx]


def test_tracking_cap_500(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Events Cap"}, timeout=15).json()["id"]
    try:
        mongo_db.estimates.update_one(
            {"id": est_id},
            {"$set": {"tracking": [{"type": "seed", "at": str(i)} for i in range(499)]}})
        import estimate_events
        for _ in range(3):
            _run_fresh(estimate_events, "log_estimate_event",
                       est_id, "qr.scanned", {"surface": "material_list"})
        evs = _events(mongo_db, est_id)
        assert len(evs) == 500
        assert evs[-1]["type"] == "qr.scanned"   # newest kept, oldest trimmed
        assert evs[0]["at"] == "2"               # first two seeds trimmed
    finally:
        requests.delete(f"{API}/estimates/{est_id}", timeout=15)
        mongo_db.estimates.delete_one({"id": est_id})
        mongo_db.estimates_trash.delete_one({"id": est_id})
