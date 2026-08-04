"""STALE ROW SWEEP guards (Howard ruled 2026-08-04). The sweep re-derives
machine numbers ONLY: waste settles at each estimate's own stored value,
human-typed quantities survive verbatim, spec fields held.

TIER BINDING (found live during the sweep): Standard/Architectural
variants are the SAME physical row — a machine row whose name differs
from an emitted row only by the tier token was consumed by the rebuild
and must not ride along (3 Degree carried Dutch Lap 47 on BOTH tiers —
a doubled siding count on a ground-truth anchor). Human rows are
untouchable, tier collision or not. Self-cleaning."""
import copy
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
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", "")

DEG3 = "5d7b7f67-c110-4c96-9580-e51db5452e67"  # 3 Degree anchor shape


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture()
def deg3_copy(s):
    from pymongo import MongoClient
    db = MongoClient(_ENV["MONGO_URL"])[_ENV["DB_NAME"]]
    src = db.estimates.find_one({"id": DEG3}, {"_id": 0})
    doc = copy.deepcopy(src)
    doc["id"] = str(uuid.uuid4())
    doc["customer_name"] = f"TEST_SWEEP-{uuid.uuid4().hex[:6]}"
    doc["test_artifact"] = True
    db.estimates.insert_one(dict(doc))
    yield doc["id"], db
    db.estimates.delete_one({"id": doc["id"]})


def _dutch_laps(lines):
    return [(l["name"], l["qty"]) for l in lines if "Dutch Lap" in l.get("name", "")]


def test_tier_renamed_machine_row_never_duplicates(s, deg3_copy):
    """Inject a stale Standard-tier machine row next to the emitted
    Architectural one; the rebuild consumes it — exactly ONE Dutch Lap
    row survives, on the tier the color derives."""
    eid, db = deg3_copy
    est = db.estimates.find_one({"id": eid}, {"_id": 0, "lines": 1})
    stale = None
    for l in est["lines"]:
        if "Architectural color Dutch Lap" in l.get("name", ""):
            stale = dict(l)
            stale["name"] = l["name"].replace("Architectural color", "Standard color")
            stale.pop("item_id", None)
            stale["qty"] = 47.0
    assert stale, "anchor shape must carry the Architectural Dutch Lap row"
    db.estimates.update_one({"id": eid}, {"$push": {"lines": stale}})
    r = s.post(f"{API}/estimates/{eid}/rederive", json={"trigger": "tier-pin"})
    assert r.status_code == 200, r.text
    laps = _dutch_laps(r.json()["lines"])
    assert len(laps) == 1, f"tier duplicate rode along: {laps}"
    assert "Architectural" in laps[0][0]


def test_sweep_holds_waste_and_human_rows(s, deg3_copy):
    """THE ABSOLUTE GUARD: re-derive settles at the estimate's OWN stored
    waste and every human-typed qty survives verbatim."""
    eid, db = deg3_copy
    before = s.get(f"{API}/estimates/{eid}").json()
    r = s.post(f"{API}/estimates/{eid}/rederive", json={"trigger": "sweep-pin"})
    assert r.status_code == 200, r.text
    after = s.get(f"{API}/estimates/{eid}").json()
    assert after.get("waste_pct") == before.get("waste_pct"), \
        "the sweep moved a waste value — per-estimate choice violated"
    hb = sorted((l["name"], l["qty"]) for l in before["lines"]
                if l.get("qty_src") == "human" or l.get("manual"))
    ha = sorted((l["name"], l["qty"]) for l in after["lines"]
                if l.get("qty_src") == "human" or l.get("manual"))
    assert hb == ha and hb, f"a human-typed quantity moved: {hb} -> {ha}"


def test_human_row_survives_even_in_tier_collision(s, deg3_copy):
    """A HUMAN-typed row on the colliding tier name is untouchable —
    tier binding consumes machine rows only."""
    eid, db = deg3_copy
    est = db.estimates.find_one({"id": eid}, {"_id": 0, "lines": 1})
    human = None
    for l in est["lines"]:
        if "Architectural color Dutch Lap" in l.get("name", ""):
            human = dict(l)
            human["name"] = l["name"].replace("Architectural color", "Standard color")
            human.pop("item_id", None)
            human["qty"] = 12.0
            human["qty_src"] = "human"
    db.estimates.update_one({"id": eid}, {"$push": {"lines": human}})
    r = s.post(f"{API}/estimates/{eid}/rederive", json={"trigger": "tier-pin-human"})
    laps = _dutch_laps(r.json()["lines"])
    assert ("Charter Oak Standard color Dutch Lap 4.5\" .046", 12.0) in laps, \
        f"a HUMAN row was consumed by tier binding: {laps}"
