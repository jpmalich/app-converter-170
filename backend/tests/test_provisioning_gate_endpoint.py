"""PROVISIONING-GATE ENDPOINT pins (Howard's ruling 2026-07-23).

HARD CONDITION pinned: supplier-admin authentication REQUIRED — the gate
reports environment internals and is NEVER public/unauthed. Same for the
seed-apply trigger (prod has no shell; apply executes via this machinery).
"""
import os
import sys
import time
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api_base import API  # noqa: E402

_ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
ADMIN_TOKEN = (os.environ.get("SUPPLIER_ADMIN_TOKEN")
               or _ENV.get("SUPPLIER_ADMIN_TOKEN", ""))


def test_gate_unauthed_403():
    assert requests.get(f"{API}/admin/provisioning-gate", timeout=20).status_code == 403
    r = requests.get(f"{API}/admin/provisioning-gate",
                     headers={"X-Admin-Token": "wrong-token"}, timeout=20)
    assert r.status_code == 403


def test_seed_apply_unauthed_403():
    assert requests.post(f"{API}/admin/seed-apply", timeout=20).status_code == 403


@pytest.mark.skipif(not ADMIN_TOKEN, reason="SUPPLIER_ADMIN_TOKEN not configured")
def test_gate_authed_reports_checks():
    r = requests.get(f"{API}/admin/provisioning-gate",
                     headers={"X-Admin-Token": ADMIN_TOKEN}, timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] in ("GREEN", "RED")
    assert body["green"] + body["red"] == len(body["checks"]) >= 50


@pytest.mark.skipif(not ADMIN_TOKEN, reason="SUPPLIER_ADMIN_TOKEN not configured")
def test_seed_apply_authed_idempotent_then_gate_green():
    r = requests.post(f"{API}/admin/seed-apply",
                      headers={"X-Admin-Token": ADMIN_TOKEN}, timeout=60)
    assert r.status_code == 200, r.text
    for _ in range(60):
        g = requests.get(f"{API}/admin/provisioning-gate",
                         headers={"X-Admin-Token": ADMIN_TOKEN}, timeout=120).json()
        if g["last_apply"].get("state") in ("done", "failed"):
            break
        time.sleep(2)
    assert g["last_apply"]["state"] == "done", g["last_apply"]
    # insert-only holds: drift may be REPORTED (live fixtures legitimately
    # evolve after export — machinery churn), but nothing is overwritten
    # and the gate stays GREEN
    assert "drift_reported" in g["last_apply"]["report"]
    assert g["status"] == "GREEN"
