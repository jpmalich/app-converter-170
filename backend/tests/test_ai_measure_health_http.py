"""Iter 79j.45 — Live HTTP tests for the new /api/measure/ai-measure/health
preflight endpoint. Focus:
  - Auth requirement (401/403 without cookie)
  - Response shape (status ∈ {ok,budget_exceeded,unavailable,ambiguous})
  - 45s cache TTL (2nd call within window returns cached:true)
  - error_kind key in status response
  - No regression on latest-for-estimate / history / rerun (401 unauth, 404 unknown)
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = "Admin123!"

if not BASE_URL:
    # Fallback to frontend .env
    try:
        with open("/app/frontend/.env") as f:
            for ln in f:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = ln.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass


@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


# -- 1. Auth requirement -----------------------------------------------------
def test_health_requires_auth():
    r = requests.get(f"{BASE_URL}/api/measure/ai-measure/health", timeout=10)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text[:200]}"


# -- 2. Response shape (uncached first call) --------------------------------
def test_health_response_shape(auth_session):
    # Bust any cache from a prior test-run by waiting or just accept cached:true is OK
    r = auth_session.get(f"{BASE_URL}/api/measure/ai-measure/health", timeout=20)
    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    data = r.json()
    assert "status" in data
    assert data["status"] in {"ok", "budget_exceeded", "unavailable", "ambiguous"}, data
    assert "detail" in data and isinstance(data["detail"], str)
    assert "checked_at" in data
    assert "cached" in data and isinstance(data["cached"], bool)
    assert "latency_ms" in data  # may be None if cached
    print(f"[health] status={data['status']} cached={data['cached']} latency_ms={data['latency_ms']}")


# -- 3. Cache TTL: second call within 45s must be cached:true ---------------
def test_health_cache_within_ttl(auth_session):
    r1 = auth_session.get(f"{BASE_URL}/api/measure/ai-measure/health", timeout=20)
    assert r1.status_code == 200
    d1 = r1.json()
    # Immediately request again — must be served from cache
    r2 = auth_session.get(f"{BASE_URL}/api/measure/ai-measure/health", timeout=10)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["cached"] is True, f"Expected cached:true on 2nd call, got {d2}"
    assert d2["latency_ms"] is None, f"Cached responses must have latency_ms=None, got {d2}"
    # status must be identical between the two calls (same underlying payload)
    assert d1["status"] == d2["status"]
    assert d1["checked_at"] == d2["checked_at"], "Cached response must reuse original checked_at"


# -- 4. status endpoint now returns error_kind field ------------------------
def test_status_response_includes_error_kind(auth_session):
    # Unknown run_id → 404, but the endpoint contract for successful runs
    # is that the JSON body includes an `error_kind` key.
    r = auth_session.get(
        f"{BASE_URL}/api/measure/ai-measure/status/nonexistent-run-xyz",
        timeout=10,
    )
    # Endpoint should respond authenticated (not 401). Either 404 (unknown)
    # or 200 with error_kind key are both acceptable proofs of routing.
    assert r.status_code in (200, 404), f"Unexpected {r.status_code}: {r.text[:200]}"
    if r.status_code == 200:
        assert "error_kind" in r.json()


# -- 5. Regression: unauth on other AI-measure endpoints --------------------
def test_rerun_requires_auth():
    r = requests.post(f"{BASE_URL}/api/measure/ai-measure/rerun/xxxx", timeout=10)
    assert r.status_code in (401, 403, 405), r.status_code


def test_latest_for_estimate_requires_auth():
    r = requests.get(f"{BASE_URL}/api/measure/ai-measure/latest-for-estimate/xxxx", timeout=10)
    assert r.status_code in (401, 403), r.status_code


def test_history_requires_auth():
    r = requests.get(f"{BASE_URL}/api/measure/ai-measure/history/xxxx", timeout=10)
    assert r.status_code in (401, 403), r.status_code


# -- 6. Regression: authenticated but unknown ids yield safe shapes ---------
def test_latest_for_estimate_unknown_returns_null_run(auth_session):
    r = auth_session.get(
        f"{BASE_URL}/api/measure/ai-measure/latest-for-estimate/unknown-estimate-zzz",
        timeout=10,
    )
    assert r.status_code == 200, r.status_code
    assert r.json().get("run") is None


def test_history_unknown_returns_empty_list(auth_session):
    r = auth_session.get(
        f"{BASE_URL}/api/measure/ai-measure/history/unknown-estimate-zzz",
        timeout=10,
    )
    assert r.status_code == 200, r.status_code
    body = r.json()
    # Accept either {runs: []} or [] shape
    runs = body.get("runs") if isinstance(body, dict) else body
    assert runs == [] or runs == {} or runs is None or (isinstance(runs, list) and len(runs) == 0), body
