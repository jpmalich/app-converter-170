"""Accept-page interactive 3D (ruled 2026-07-15) — asserted-absence pins.

Pins:
  • customer payload carries a sanitized house3d — NO per-feature
    verification chips, NO internal state labels (tier / amber /
    user_* statuses / verify metadata), NO cost keys
  • ratified state pre-applied server-side: user_removed corners gone,
    user_relocated corners carry the corrected wall
  • trust carried ONCE — aggregate attestation line (count, initials,
    date), outcomes-not-history
  • softened homeowner footnote flag (on_site_note), never flag vocabulary
Fixture: letrick 7-14-26 7pm (photo run, chase on back wall).
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
from clone_util import clone_estimate, drop_clone
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD
EST_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"  # letrick 7-14-26 7pm — READ-ONLY clone source (SEND-107)
TOKEN = "pin-accept-3d-letrick"

FORBIDDEN = (
    '"tier"', '"status"', '"amber"', "user_measured", "user_relocated",
    "user_removed", "unverified", "cost_usd", "lp_field_verify",
    "verified_by", "verified_at", '"photo_idxs"', '"sightings"',
    "_reconciliation", "token_usage", "relocated_to",
)


def _mongo():
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# SEND-107: this file wrote accept_token + lp_field_verify DIRECTLY onto
# the real Mark Letrick estimate. All writes now land on a disposable
# clone (runs copied so house3d resolves); the token binds the clone.
@pytest.fixture(scope="module", autouse=True)
def clone_ctx():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com",
                     "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    cid = clone_estimate(s, API, EST_ID, copy_runs=True)
    _mongo().estimates.update_one({"id": cid}, {"$set": {"accept_token": TOKEN}})
    yield cid
    drop_clone(s, API, cid)


def _get(token=TOKEN):
    r = requests.get(f"{API}/public/accept/{token}", timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


def test_house3d_present_and_sanitized(clone_ctx):
    d = _get()
    h = d.get("house3d")
    assert h, "accept payload must carry the sanitized 3D block"
    assert h["raw_ai"]["walls"] and h["measurements"]
    corners = h["raw_ai"]["corner_locations"]
    assert corners, "letrick has chase corners"
    for c in corners:
        assert set(c.keys()) <= {"locator", "type", "walls", "position_frac"}
    blob = json.dumps(d)
    for term in FORBIDDEN:
        assert term not in blob, f"asserted-absence violated: {term}"


def test_softened_footnote_flag(clone_ctx):
    # letrick has amber chase corners with no ratification → footnote on
    d = _get()
    assert d.get("on_site_note") is True


def test_attestation_aggregate_only(clone_ctx):
    db = _mongo()
    key = "corner:osc:chimney-chase-near-side-outside-corner"
    now = datetime.now(timezone.utc).isoformat()
    db.estimates.update_one({"id": clone_ctx}, {"$set": {f"lp_field_verify.{key}": {
        "status": "verified", "by": "hhunt6677@yahoo.com", "at": now}}})
    try:
        d = _get()
        a = d.get("attestation")
        assert a and a["count"] == 1 and a["initials"] == "HH" and a["date"] == now[:10]
        # per-feature statuses stay absent even WITH a ratified location
        blob = json.dumps(d)
        for term in FORBIDDEN:
            assert term not in blob, f"asserted-absence violated post-ratify: {term}"
    finally:
        db.estimates.update_one({"id": clone_ctx}, {"$unset": {f"lp_field_verify.{key}": ""}})


def test_no_attestation_when_nothing_confirmed(clone_ctx):
    d = _get()
    assert d.get("attestation") is None


def test_removed_corner_leaves_customer_render(clone_ctx):
    db = _mongo()
    key = "corner:osc:chimney-chase-near-side-outside-corner"
    db.estimates.update_one({"id": clone_ctx}, {"$set": {f"lp_field_verify.{key}": {
        "status": "user_removed", "by": "hhunt6677@yahoo.com",
        "at": datetime.now(timezone.utc).isoformat()}}})
    try:
        d = _get()
        locs = [c["locator"] for c in d["house3d"]["raw_ai"]["corner_locations"]]
        assert "chimney chase near-side outside corner" not in locs
        assert d.get("attestation") is None  # removal is not a confirmation
    finally:
        db.estimates.update_one({"id": clone_ctx}, {"$unset": {f"lp_field_verify.{key}": ""}})
