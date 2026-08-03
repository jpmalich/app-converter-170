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


# ---- FILL-IN HISTORY VIEW (Howard ruled 2026-08-03, second pass) ---------
# The trail is VISIBLE on each fill-in box — read-only display of the
# stored metadata; the view writes nothing and never touches the value.

SR_PATH = "/app/frontend/src/components/estimate/SettingsRow.jsx"


def test_history_view_renders_trail_and_per_box_stamp():
    src = open(SR_PATH).read()
    assert 'data-testid="photo-fillin-history"' in src, "trail view missing"
    assert "provenanceChip" in src, "per-box who/when stamp missing"
    assert '"pf.lastSet"' in src or "'pf.lastSet'" in src
    for tid in ('provenanceChip(f.key, f.tid)',
                'provenanceChip("photo_frieze_present", "photo-frieze")'):
        assert tid in src, f"a fill-in box lost its provenance stamp: {tid}"


def test_history_view_is_read_only():
    """The view reads photo_fillin_history and writes NOTHING — no save,
    update, or state mutation may originate from the history trail or
    the per-box provenance chip."""
    src = open(SR_PATH).read()
    start = src.index('data-testid="photo-fillin-history"')
    trail = src[start:src.index("</details>", start)]
    chip_start = src.index("const provenanceChip")
    chip = src[chip_start:src.index("};", chip_start)]
    for name, block in (("trail", trail), ("provenance chip", chip)):
        for writer in ("saveSpec(", "update(", "onChange", "onClick",
                       "axios", "fetch(", ".put(", ".post("):
            assert writer not in block, \
                f"history {name} grew a write path: {writer}"


def test_history_view_keys_exist_both_languages():
    js = open("/app/frontend/src/lib/dictionaries.js").read()
    en, es = js[js.index("en: {"):js.index("  es: {")], js[js.index("  es: {"):]
    for key in ("pf.history", "pf.lastSet"):
        assert f'"{key}":' in en, f"missing from en: {key}"
        assert f'"{key}":' in es, f"missing from es: {key}"
