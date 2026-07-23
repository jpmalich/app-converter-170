from creds_for_tests import TEST_PASSWORD
"""Appendage dimension editing (ruled 2026-07-15) — render-only rule's
second half.

Pins:
  • assumed dims still NEVER reach quantities (no state → no override)
  • user_measured height re-derives 540 OSC stick math on all surfaces
  • disagreement vs AI-attributed face area is FLAGGED, never averaged
  • revert restores assumed state and strips the dimension from math
  • blueprint dims are OFFER-and-confirm only (user_confirmed_from_blueprint)
Fixture per ruling: letrick 7-14-26 7pm chase height.
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

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
EST_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"  # letrick 7-14-26 7pm (photo)
BP_EST_ID = "db82ec7a-3177-406d-a602-927255e9e10e"  # has blueprint runs
KEY = "appendage:right"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s
    for f in ("height_ft", "depth_ft"):  # leave estimate as found
        s.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims",
               json={"key": KEY, "field": f, "action": "revert"}, timeout=15)


def _preview(session, est_id=EST_ID):
    r = session.post(f"{API}/estimates/{est_id}/lp-package/preview", json={}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _osc_line(pkg):
    return next(l for l in pkg["lines"] if "OSC" in l["name"])


# ── Unit: overlay + pin (assumed never enters math) ───────────────────

CHASE_OSC = {"type": "outside", "locator": "chimney chase near-side outside corner",
             "walls": ["right"], "tier": "estimated"}
PLAIN_OSC = {"type": "outside", "locator": "plain house corner", "walls": ["right"], "tier": "confirmed"}
CHASE_ISC = {"type": "inside", "locator": "chimney chase near-side inside corner", "walls": ["right"], "tier": "estimated"}


def test_assumed_dims_never_set_override():
    from routes.lp_package_routes import _apply_appendage_dims
    out = _apply_appendage_dims([CHASE_OSC], None)
    assert "height_override_ft" not in out[0]
    out = _apply_appendage_dims([CHASE_OSC], {})
    assert "height_override_ft" not in out[0]


def test_user_measured_height_targets_chase_osc_only():
    from routes.lp_package_routes import _apply_appendage_dims
    state = {KEY: {"height_ft": {"value": 18.9, "status": "user_measured"}}}
    chase_back_osc = {"type": "outside", "locator": "chase right outer edge",
                      "walls": ["back"], "tier": "confirmed"}
    out = _apply_appendage_dims([CHASE_OSC, PLAIN_OSC, CHASE_ISC, chase_back_osc], state)
    assert out[0]["height_override_ft"] == 18.9 and out[0]["height_source"] == "user_measured"
    assert "height_override_ft" not in out[1]  # plain corner untouched
    assert "height_override_ft" not in out[2]  # ISC (chase meets wall) untouched
    # feature-scoped: the chase's adjacent-wall OSC edge rises too (C4)
    assert out[3]["height_override_ft"] == 18.9


def test_corner_height_honors_override():
    from lp_package import _corner_height_ft
    loc = {**CHASE_OSC, "height_override_ft": 18.9}
    assert _corner_height_ft(loc, {"right": 8.6}, 8.6) == 18.9
    assert _corner_height_ft(CHASE_OSC, {"right": 8.6}, 8.6) == 8.6


def test_disagreement_flagged_never_averaged():
    from routes.lp_package_routes import _appendage_dim_flags
    meas = {"_ai_appendage_sqft": 130.0}
    ok = {KEY: {"height_ft": {"value": 18.9, "status": "user_measured"}}}
    assert _appendage_dim_flags(meas, ok) == []
    absurd = {KEY: {"height_ft": {"value": 60.0, "status": "user_measured"}}}
    flags = _appendage_dim_flags(meas, absurd)
    assert len(flags) == 1 and "flagged, not averaged" in flags[0]


# ── E2E on the ruled letrick fixture ──────────────────────────────────

def test_chase_height_rederives_osc_sticks(session, ):
    base = _osc_line(_preview(session))
    base_qty = base["qty"]

    r = session.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims",
                     json={"key": KEY, "field": "height_ft", "value": 18.9}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "user_measured" and body["by"] and body["at"]

    pkg = _preview(session)
    line = _osc_line(pkg)
    # Howard's ruled cross-check: the sealed key counts 8 OSC sticks —
    # chase feature at true height (2×18.9 → 3 sticks) + 5 singleton
    # house corners = 8.
    assert line["qty"] == 8, f"OSC sticks must hit the key's 8 ({base_qty} → {line['qty']})"
    assert "user-measured height" in line["note"]
    assert pkg["appendage_dim_flags"] == []
    assert pkg["appendage_dims"][KEY]["height_ft"]["value"] == 18.9

    # journey-logged
    mongo = MongoClient(os.environ["MONGO_URL"])
    est = mongo[os.environ["DB_NAME"]].estimates.find_one({"id": EST_ID}, {"tracking": 1})
    evs = [t for t in est["tracking"] if t["type"] == "appendage.measured"]
    assert evs and evs[-1]["meta"]["value"] == 18.9
    mongo.close()

    # revert strips the dimension from math
    r = session.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims",
                     json={"key": KEY, "field": "height_ft", "action": "revert"}, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "assumed"
    after = _osc_line(_preview(session))
    assert after["qty"] == base_qty
    # PIN AMENDED (chase ratification ruling, 2026-07-19): the estimate now
    # PERMANENTLY carries user-measured appendage:back chase dims (taped
    # 19.552'), so the note legitimately keeps "user-measured height" after
    # this test reverts its own appendage:right entry. The revert itself is
    # still pinned via qty == base_qty and the entry's removal above.
    assert "user-measured height" in after["note"]


def test_absurd_height_flags_on_preview(session):
    r = session.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims",
                     json={"key": KEY, "field": "height_ft", "value": 60}, timeout=15)
    assert r.status_code == 200
    try:
        flags = _preview(session)["appendage_dim_flags"]
        assert flags and "disagrees with the AI-attributed face area" in flags[0]
    finally:
        session.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims",
                     json={"key": KEY, "field": "height_ft", "action": "revert"}, timeout=15)


def test_validation_rejects_bad_input(session):
    # PIN AMENDED BY RULING 2026-07-22: width_ft JOINS the machinery
    # (tape-upgrade path for the ASSUMED standard chase width) — the
    # closed-contract refusal now pins on a genuinely unknown field.
    for bad in ({"key": "appendage:roof", "field": "height_ft", "value": 10},
                {"key": KEY, "field": "girth_ft", "value": 10},
                {"key": KEY, "field": "height_ft", "value": 400},
                {"key": KEY, "field": "height_ft", "value": "tall"}):
        r = session.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims", json=bad, timeout=15)
        assert r.status_code == 400, bad
    ok = session.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims",
                      json={"key": KEY, "field": "width_ft", "value": 10}, timeout=15)
    assert ok.status_code == 200, ok.text  # ruled 2026-07-22
    session.post(f"{API}/estimates/{EST_ID}/lp-appendage-dims",
                 json={"key": KEY, "field": "width_ft", "action": "revert"}, timeout=15)


# ── Blueprint offer-and-confirm ───────────────────────────────────────

def test_blueprint_offers_surface_on_bp_estimate(session):
    r = session.get(f"{API}/estimates/{BP_EST_ID}/lp-appendage-dims", timeout=15)
    assert r.status_code == 200
    offers = r.json()["offers"]
    assert offers, "blueprint estimate must offer print-derived dims"
    chase = offers[0]
    assert chase["key"].startswith("appendage:") and chase["height_ft"]


def test_photo_only_estimate_offers_nothing(session):
    r = session.get(f"{API}/estimates/{EST_ID}/lp-appendage-dims", timeout=15)
    assert r.status_code == 200 and r.json()["offers"] == []


def test_accept_from_blueprint_tags_confirmed(session):
    r = session.post(f"{API}/estimates/{BP_EST_ID}/lp-appendage-dims",
                     json={"key": "appendage:back", "field": "height_ft",
                           "value": 22.0, "source": "blueprint"}, timeout=15)
    assert r.status_code == 200
    try:
        assert r.json()["status"] == "user_confirmed_from_blueprint"
    finally:
        session.post(f"{API}/estimates/{BP_EST_ID}/lp-appendage-dims",
                     json={"key": "appendage:back", "field": "height_ft", "action": "revert"}, timeout=15)
