"""FILL-IN HISTORY (Howard ruled 2026-08-03): who typed each fill-in
value and when — a disputed soffit number traces to a person and a date.
Server-stamped on PUT/PATCH; only CHANGED values append (an autosave
replaying the same value is not a decision). Self-cleaning: every
estimate this file creates is deleted at the end."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", "")


@pytest.fixture(scope="module")
def base_url():
    return BASE_URL


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{BASE_URL}/api/auth/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture()
def est_factory(s):
    made = []

    def make(kind="siding"):
        r = s.post(f"{BASE_URL}/api/estimates",
                   json={"customer_name": f"TEST_FILLIN-{uuid.uuid4().hex[:6]}",
                         "kind": kind})
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        made.append(eid)
        return eid

    yield make
    for eid in made:
        s.delete(f"{BASE_URL}/api/estimates/{eid}")


def _history(s, base, eid):
    r = s.get(f"{base}/api/estimates/{eid}").json()
    return r.get("photo_fillin_history") or []


def test_fillin_change_traces_to_person_and_date(est_factory, s, base_url):
    eid = est_factory("siding")
    s.put(f"{base_url}/api/estimates/{eid}",
          json={"photo_soffit_sqft": 250, "photo_frieze_present": True})
    hist = _history(s, base_url, eid)
    fields = {h["field"] for h in hist}
    assert fields == {"photo_soffit_sqft", "photo_frieze_present"}
    for h in hist:
        assert h["by"] and "@" in h["by"], "history must name a person"
        assert h["at"], "history must carry a date"
    soffit = next(h for h in hist if h["field"] == "photo_soffit_sqft")
    assert soffit["value"] == 250 and soffit["prev"] is None


def test_replaying_the_same_value_appends_nothing(est_factory, s, base_url):
    eid = est_factory("siding")
    s.put(f"{base_url}/api/estimates/{eid}", json={"photo_soffit_sqft": 250})
    s.put(f"{base_url}/api/estimates/{eid}", json={"photo_soffit_sqft": 250})
    assert len(_history(s, base_url, eid)) == 1
    # a change DOES append, carrying the previous value
    s.put(f"{base_url}/api/estimates/{eid}", json={"photo_soffit_sqft": 300})
    hist = _history(s, base_url, eid)
    assert len(hist) == 2
    assert hist[-1]["prev"] == 250 and hist[-1]["value"] == 300


def test_non_fillin_saves_append_nothing(est_factory, s, base_url):
    eid = est_factory("siding")
    s.put(f"{base_url}/api/estimates/{eid}",
          json={"customer_name": "History Noise Check", "waste_pct": 10})
    assert _history(s, base_url, eid) == []
