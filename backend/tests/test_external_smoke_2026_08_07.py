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
    s, api = ingress
    ests = s.get(f"{api}/estimates", timeout=20).json()
    sid = next((e["id"] for e in ests if e.get("kind") != "lp_smart"), None)
    if sid is None:
        pytest.skip("no siding estimate to rederive")
    r = s.post(f"{api}/estimates/{sid}/rederive",
               json={"trigger": "ingress-smoke"}, timeout=60)
    assert r.status_code in (200, 409), \
        f"rederive through the ingress broke: {r.status_code}"
