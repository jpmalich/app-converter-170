"""Demo reset pins — Letrick showcase staging (ruled 2026-06):
specified state, hard isolation, idempotency."""
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
ADMIN_PASSWORD = "Admin123!"


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


def test_demo_reset_specified_state_and_isolation(admin_session, mongo_db):
    s = admin_session
    # isolation baseline: every non-demo estimate must be byte-identical
    # after reset (the original Letrick source estimate was deleted from
    # the dashboard — the reset is now self-contained on the frozen run)
    others_before = {
        e["id"]: e for e in mongo_db.estimates.find(
            {"demo_key": {"$ne": "letrick_demo"}}, {"_id": 0})
    }

    r = s.post(f"{API}/demo/reset", timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()

    # (1) staged showcase: scored tape check, LP composition, palette, QR links
    assert d["estimate_number"] == "DEMO-LETRICK"
    assert d["tape_check_scored"]["history_entries"] == 1
    assert d["tape_check_scored"]["accuracy_pct"] is not None
    assert d["package_lines"] > 15 and d["stored_lines_seeded"] > 15
    assert d["colors"]["siding"] == "Quarry Gray"
    assert d["share_links"]["material_list"].startswith("/m/")
    assert d["share_links"]["accuracy_report"].startswith("/r/")
    assert requests.get(
        f"{API}/public/lp-material-list/{d['share_links']['material_list'].split('/m/')[1]}",
        timeout=30).status_code == 200
    assert requests.get(
        f"{API}/public/accuracy-report/{d['share_links']['accuracy_report'].split('/r/')[1]}",
        timeout=30).status_code == 200

    # (2) SPECIFIED state: ambers unratified, substitution available,
    # confirm-openings populated
    assert len(d["ambers_unratified"]) >= 1
    assert all(a["status"] == "unverified" for a in d["ambers_unratified"])
    assert len(d["substitutable_lines"]) >= 1
    assert d["openings_review"]["items"] >= 1
    assert d["openings_review"]["unconfirmed"] == d["openings_review"]["items"]

    # (4) built to run with LP-native mode ON: the demo is pure lp_smart;
    # the GLOBAL mode switch is never mutated by reset (isolation) —
    # readout reports the current state
    assert isinstance(d["lp_native_mode"], bool)

    # (3) hard isolation: every non-demo estimate byte-identical after reset
    others_after = {
        e["id"]: e for e in mongo_db.estimates.find(
            {"demo_key": {"$ne": "letrick_demo"}}, {"_id": 0})
    }
    assert others_after == others_before

    # (5) idempotent: second click → same staged content, ONE demo estimate
    d2 = s.post(f"{API}/demo/reset", timeout=120).json()
    for k in ("estimate_number", "run_id", "lp_native_mode", "pricing_tier",
              "colors", "ambers_unratified", "openings_review",
              "substitutable_lines", "package_lines", "stored_lines_seeded"):
        assert d2[k] == d[k], k
    assert mongo_db.estimates.count_documents({"demo_key": "letrick_demo"}) == 1
    # first reset's demo docs were wiped — no orphans
    assert mongo_db.ai_measure_runs.count_documents({"estimate_id": d["estimate_id"]}) == 0
    assert mongo_db.accuracy_report_snapshots.count_documents({"estimate_id": d["estimate_id"]}) == 0
    assert mongo_db.lp_material_list_snapshots.count_documents({"estimate_id": d["estimate_id"]}) == 0


def test_demo_reset_mutates_zero_global_state(admin_session, mongo_db):
    """Pin (ruled 2026-06, after the lp_native_mode violation): a demo
    reset touches NOTHING outside the flagged demo estimate's documents —
    no settings, no company docs, no tier definitions."""
    def snapshot():
        return {
            "settings": sorted(
                mongo_db.settings.find({}, {"_id": 0}),
                key=lambda x: str(x.get("id"))),
            "companies": sorted(
                mongo_db.companies.find({}, {"_id": 0}),
                key=lambda x: str(x.get("id"))),
            "price_tiers": sorted(
                mongo_db.price_tiers.find({}, {"_id": 0}),
                key=lambda x: str(x.get("id"))),
        }

    before = snapshot()
    r = admin_session.post(f"{API}/demo/reset", timeout=120)
    assert r.status_code == 200, r.text
    after = snapshot()
    assert after["settings"] == before["settings"]
    assert after["companies"] == before["companies"]
    assert after["price_tiers"] == before["price_tiers"]
