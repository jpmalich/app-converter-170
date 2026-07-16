from creds_for_tests import TEST_PASSWORD
"""Iter 79j.74 — /estimates/{id}/model3d-snapshot endpoint tests."""
import os
import uuid

import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
_FE_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _FE_ENV.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", TEST_PASSWORD)


def _session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


def _make_estimate(s):
    r = s.post(f"{API}/estimates", json={"customer_name": "Snapshot Test"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_snapshot_roundtrip_and_validation():
    s = _session()
    est_id = _make_estimate(s)
    try:
        url = f"/api/uploads/{uuid.uuid4().hex}.png"
        r = s.put(f"{API}/estimates/{est_id}/model3d-snapshot", json={"url": url}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["model3d_png_url"] == url
        # persisted on the estimate document
        est = s.get(f"{API}/estimates/{est_id}", timeout=15).json()
        assert est["model3d_png_url"] == url
        # rejects non-upload URLs and traversal
        for bad in ("https://evil.example/x.png", "/api/uploads/../../etc/passwd",
                    "/etc/passwd", "/api/uploads/a/b.png", ""):
            rb = s.put(f"{API}/estimates/{est_id}/model3d-snapshot", json={"url": bad}, timeout=15)
            assert rb.status_code == 400, f"{bad!r} → {rb.status_code}"
        # 404 for someone else's / missing estimate
        r404 = s.put(f"{API}/estimates/{uuid.uuid4().hex}/model3d-snapshot", json={"url": url}, timeout=15)
        assert r404.status_code == 404
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_snapshot_requires_auth():
    r = requests.put(
        f"{API}/estimates/{uuid.uuid4().hex}/model3d-snapshot",
        json={"url": "/api/uploads/x.png"}, timeout=15,
    )
    assert r.status_code in (401, 403)
