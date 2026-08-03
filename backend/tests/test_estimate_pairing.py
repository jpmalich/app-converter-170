"""DOORS ARE SINGLE-FAMILY · ESTIMATES ARE SELF-CONTAINED (Howard ruled
2026-08-03). The pairing mechanism (/pair, /pair-lp) is RETIRED —
cross-family fill is post-September scope. This file replaced the old
pairing behavior tests with retirement pins: the routes must stay gone."""
import os

import requests
from dotenv import dotenv_values

_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")


def test_pair_route_is_retired():
    """POST /estimates/{id}/pair no longer exists. An existing route
    would answer 401/403 unauthenticated; a retired one answers 404/405."""
    r = requests.post(f"{BASE_URL}/api/estimates/anything/pair")
    assert r.status_code in (404, 405), \
        f"/pair route still mounted: {r.status_code} {r.text[:120]}"


def test_pair_lp_route_is_retired():
    r = requests.post(f"{BASE_URL}/api/estimates/anything/pair-lp")
    assert r.status_code in (404, 405), \
        f"/pair-lp route still mounted: {r.status_code} {r.text[:120]}"
