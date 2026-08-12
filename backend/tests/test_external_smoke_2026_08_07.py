"""EXTERNAL INGRESS SMOKE (Howard ruled 2026-08-07): moving the suite
to localhost removed the only coverage of the path a real user — and
the demo — travels. CADENCE: this file runs against the PUBLIC ingress
URL as part of every handback (handback_green.sh) and as part of bar
line (h). It self-skips in normal local suite runs so determinism
stands; TEST_API_EXTERNAL=1 activates it.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/app/backend")

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_API_EXTERNAL"),
    reason="ingress smoke runs on the handback cadence (TEST_API_EXTERNAL=1)")


def _external_api():
    from dotenv import dotenv_values
    url = (dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL")
           or "").rstrip("/")
    assert url.startswith("http"), "frontend .env lost the public URL"
    return f"{url}/api"


@pytest.fixture(scope="module")
def ingress():
    import requests
    from creds_for_tests import TEST_EMAIL, TEST_PASSWORD
    api = _external_api()
    s = requests.Session()
    r = s.post(f"{api}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, f"ingress login broken: {r.status_code}"
    return s, api


def test_ingress_auth_cookie_round_trip(ingress):
    s, api = ingress
    r = s.get(f"{api}/estimates", timeout=20)
    assert r.status_code == 200, \
        f"authenticated GET through the ingress broke: {r.status_code}"
    assert isinstance(r.json(), list)


def test_ingress_estimate_read(ingress):
    s, api = ingress
    ests = s.get(f"{api}/estimates", timeout=20).json()
    assert ests, "no estimates visible through the ingress"
    eid = ests[0]["id"]
    r = s.get(f"{api}/estimates/{eid}", timeout=20)
    assert r.status_code == 200 and r.json().get("id") == eid


def test_ingress_rederive_round_trip(ingress):
    """DETERMINISTIC RE-DERIVE (Howard ruled 2026-08-11 send-7): the
    prior version picked an arbitrary estimate off /estimates and
    could hit any of {protected → 423, lines empty → skip, wrong kind
    → skip}. A red test that carries a standing explanation stops
    being looked at (the 3-day gable-census delay proved the class).

    This creates a THROWAWAY vinyl estimate through the same public
    path a contractor travels, walks rederive against it, and cleans
    up. The fixture is unprotected by construction, the response
    contract stands (200 = rederive completed, 409 = gate blocked
    with reason), and the smoke fails only when the public path
    genuinely broke."""
    s, api = ingress
    r = s.post(f"{api}/estimates",
               json={"customer_name": "TEST_ingress_rederive",
                     "address": "TEST_ingress_rederive",
                     "kind": "siding"}, timeout=20)
    assert r.status_code == 200, (
        f"create through the ingress broke: {r.status_code}")
    eid = r.json()["id"]
    try:
        r = s.post(f"{api}/estimates/{eid}/rederive",
                   json={"trigger": "ingress-smoke"}, timeout=60)
        assert r.status_code in (200, 409), (
            f"rederive through the ingress broke: {r.status_code} "
            f"{r.text[:200]}")
    finally:
        s.delete(f"{api}/estimates/{eid}", timeout=20)


def test_ingress_spec_field_put_round_trip(ingress):
    """SPEC-FIELD PUT THROUGH THE PUBLIC URL (Howard ruled 2026-08-07):
    the integral-J toggle failed EXACTLY here — a PUT that toasted Saved
    while the ingress path silently stripped the field. This walks a
    TRADE_SPEC_FAMILY_REGISTER field (overhang_in + fascia_width_in)
    through create → PUT → re-GET on a THROWAWAY estimate, then deletes it."""
    s, api = ingress
    r = s.post(f"{api}/estimates",
               json={"customer_name": "TEST_ingress_spec_put",
                     "address": "TEST_ingress_spec_put"}, timeout=20)
    assert r.status_code == 200, f"create through the ingress broke: {r.status_code}"
    eid = r.json()["id"]
    try:
        r = s.put(f"{api}/estimates/{eid}",
                  json={"overhang_in": 16, "fascia_width_in": 8},
                  timeout=30)
        assert r.status_code == 200, \
            f"spec-field PUT through the ingress broke: {r.status_code} {r.text[:200]}"
        got = s.get(f"{api}/estimates/{eid}", timeout=20)
        assert got.status_code == 200
        body = got.json()
        assert float(body.get("overhang_in") or 0) == 16, \
            "overhang_in did not persist through the public PUT — silent strip"
        assert float(body.get("fascia_width_in") or 0) == 8, \
            "fascia_width_in did not persist through the public PUT — silent strip"
    finally:
        s.delete(f"{api}/estimates/{eid}", timeout=20)
