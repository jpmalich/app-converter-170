"""Iter 79j.86 — Model bake-off infrastructure pins (pre-run, Howard's GO).
Zero prompt changes; per-phase model plumbing; actual token telemetry;
usage-probe exclusion from accuracy scoring."""
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    _resolve_model, _price_for_model_id, _cost_from_usage,
    _aggregate_token_usage, _prompt_version_hash,
)

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = "Admin123!"


def test_prompt_contract_untouched_by_infra():
    # updated to the Candidate 2 contract hash (pitch ladder expansion —
    # the only prompt change since 1c; bake-off infra changed nothing).
    assert _prompt_version_hash() == "53f2bfa3344b1057"


def test_haiku_registered():
    key, provider, name = _resolve_model("claude-haiku-4-5")
    assert (key, provider, name) == ("claude-haiku-4-5", "anthropic", "claude-haiku-4-5-20251001")


def test_price_lookup_strips_date_suffix():
    assert _price_for_model_id("claude-opus-4-5-20251101") == {"input": 5.00, "output": 25.00}
    assert _price_for_model_id("claude-haiku-4-5-20251001") == {"input": 1.00, "output": 5.00}
    assert _price_for_model_id("claude-fable-5") == {"input": 10.00, "output": 50.00}
    assert _price_for_model_id("claude-sonnet-4-6") == {"input": 3.00, "output": 15.00}
    assert _price_for_model_id("unknown-model") is None


def test_aggregate_token_usage():
    final = {"_reconciliation_usage": {"input_tokens": 12000, "output_tokens": 9000, "thinking_tokens": 2000, "calls": 1}}
    extractions = [
        {"_usage": {"input_tokens": 5000, "output_tokens": 800}},
        {"_usage": {"input_tokens": 5100, "output_tokens": 900}},
        {"no_usage": True},
    ]
    tu = _aggregate_token_usage(final, extractions)
    assert tu["phase_a"] == {"input_tokens": 10100, "output_tokens": 1700, "calls": 2}
    assert tu["phase_b"]["input_tokens"] == 12000
    assert _aggregate_token_usage({}, [{}]) is None


def test_cost_from_usage_actuals():
    cfg = {"phase_a": "claude-sonnet-4-6", "phase_b": "claude-fable-5"}
    tu = {
        "phase_a": {"input_tokens": 40000, "output_tokens": 8000, "calls": 8},
        "phase_b": {"input_tokens": 12000, "output_tokens": 10000, "calls": 1},
    }
    c = _cost_from_usage(cfg, tu)
    assert c["phase_a"] == round(0.04 * 3 + 0.008 * 15, 4)   # 0.24
    assert c["phase_b"] == round(0.012 * 10 + 0.01 * 50, 4)  # 0.62
    assert c["total"] == round(c["phase_a"] + c["phase_b"], 4)
    assert _cost_from_usage(cfg, None) is None


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    s._user_id = s.get(f"{API}/auth/me", timeout=10).json()["id"]
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def test_usage_probe_run_refused_by_scoring(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Probe Exclusion"}, timeout=15).json()["id"]
    run_id = uuid.uuid4().hex
    mongo_db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": s._user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "usage_probe": True,
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.0, "height_ft_source": "direct_consensus"},
        ], "photos": []}},
    })
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check", json={"walls": {
            "front": {"segments": [{"height_ft": 8.96}], "start_ref": "siding_start"},
        }, "dormers": []}, timeout=15)
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 400, r.text
        assert "probe" in r.json()["detail"].lower()
        # accuracy history untouched
        h = s.get(f"{API}/estimates/{est_id}/tape-check", timeout=15).json()["history"]
        assert h == []
        # latest-for-estimate never surfaces the probe
        latest = s.get(f"{API}/measure/ai-measure/latest-for-estimate/{est_id}", timeout=15).json()
        run_field = (latest or {}).get("run") if isinstance(latest, dict) else None
        assert not run_field or run_field.get("run_id") != run_id
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
