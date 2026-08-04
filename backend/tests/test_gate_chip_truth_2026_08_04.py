"""GATE CHIP TRUTH (Howard ruled 2026-08-04). Found on the demo dry run:
the estimate chips said QUOTE GATE — CLEAR while the quote modal was
PRINT-BLOCKED ×4 — two surfaces disagreeing about whether he can quote.
ONE readiness truth: both surfaces derive from the SAME generator
(_readiness_items) — same reasons, same count, cannot diverge."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"

DEMO_KEY = "letrick_demo"  # id changes on every /demo/reset — resolve live


@pytest.fixture(scope="module")
def demo_id():
    from pymongo import MongoClient
    dbc = MongoClient(_ENV["MONGO_URL"])[_ENV["DB_NAME"]]
    e = dbc.estimates.find_one({"demo_key": DEMO_KEY}, {"id": 1})
    assert e, "demo fixture missing — run POST /api/demo/reset"
    return e["id"]


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com"),
                        "password": _ENV["ADMIN_PASSWORD"]})
    assert r.status_code == 200, r.text
    return sess


def _chip_blockers(s, eid):
    g = s.get(f"{API}/estimates/{eid}/gates").json()
    return sorted(i["code"] for i in g["quote"]["blocking"])


def _modal_blockers(s, eid):
    r = s.get(f"{API}/estimates/{eid}/readiness").json()
    return sorted(i["code"] for i in r["items"] if i.get("blocking"))


def test_chips_and_modal_agree_on_the_demo_fixture(s, demo_id):
    chips, modal = _chip_blockers(s, demo_id), _modal_blockers(s, demo_id)
    assert chips == modal, \
        f"two surfaces disagree again — chips {chips} vs modal {modal}"


def test_chips_and_modal_agree_on_a_fresh_estimate(s):
    r = s.post(f"{API}/estimates",
               json={"customer_name": f"TEST_GATE-{uuid.uuid4().hex[:6]}",
                     "kind": "lp_smart"})
    eid = r.json()["id"]
    try:
        assert _chip_blockers(s, eid) == _modal_blockers(s, eid)
    finally:
        s.delete(f"{API}/estimates/{eid}")


def test_one_generator_feeds_both_surfaces():
    """SOURCE PIN: evaluate_gates builds its quote tier FROM
    _readiness_items — not from a second parallel generator."""
    src = open("/app/backend/routes/lp_package_routes.py").read()
    gates_fn = src[src.index("async def evaluate_gates"):]
    gates_fn = gates_fn[:gates_fn.index("\n@router", 1)]
    assert "_readiness_items(est_id, user)" in gates_fn, \
        "evaluate_gates grew its own quote-blocker generator — one truth violated"
    ready_fn = src[src.index("async def _readiness_items"):]
    ready_fn = ready_fn[:ready_fn.index("\nasync def ", 10)]
    assert "quote_gate_blockers(est, measurements)" in ready_fn, \
        "readiness no longer folds the gates.py quote blockers — modal would under-report"
