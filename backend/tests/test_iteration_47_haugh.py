"""Iteration 47 — Live integration tests for LP SmartSide Hover Round-Two follow-ups.

Cases:
 A. Temporary estimate: hover-lp-run default -> preview shows waste_pct_applied=0.10 + geometry_basis.label
 B. Same, with facade_scope custom (wrap 2376 sqft, excluded brick 234)
 C. Regression: LETRICK photo-path preview still 11055.71 + waste_pct_applied=0.10
"""
import math
import os
import requests
import pytest
from pathlib import Path
from dotenv import dotenv_values

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE}/api"

_ENV = dotenv_values(Path("/app/backend/.env"))
EMAIL = _ENV.get("ADMIN_EMAIL") or "hhunt6677@yahoo.com"
PASSWORD = _ENV.get("ADMIN_PASSWORD")

HOVER_RUN_ID = "7c6194d46b91444990b6910a175b12ff"  # re-ingested 2026-07-18 (TTL 2nd-instance re-arm)
LETRICK_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    assert PASSWORD, "ADMIN_PASSWORD missing from backend/.env"
    r = s.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:200]}"
    # persist bearer if returned
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    tok = body.get("access_token") or body.get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def temp_est(sess):
    # Create temp LP SmartSide estimate; prefix ZZ per contract
    payload = {
        "kind": "lp_smart",
        "customer_name": "ZZ_ITER47_HAUGH_TEMP",
        "address": "TEST ONLY - safe to delete",
    }
    r = sess.post(f"{API}/estimates", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"create estimate: {r.status_code} {r.text[:300]}"
    est = r.json()
    eid = est.get("id") or est.get("_id") or est.get("estimate_id")
    assert eid, f"no id in response: {est}"
    yield eid
    # cleanup
    try:
        sess.delete(f"{API}/estimates/{eid}", timeout=30)
    except Exception:
        pass


def _run_lp_hover(sess, eid, facade_scope=None):
    body = {"hover_run_id": HOVER_RUN_ID, "profile": "lap"}
    if facade_scope is not None:
        body["facade_scope"] = facade_scope
    r = sess.post(f"{API}/estimates/{eid}/hover-lp-run", json=body, timeout=90)
    if r.status_code == 404 and "run not found" in r.text:
        # hover_import_runs 24h TTL — substrate restores by re-uploading
        # the 261 Haugh Hover PDF (see ttl_audit_report.md).
        pytest.skip("Haugh hover run TTL-expired — re-upload the 261 Haugh Hover PDF to restore the pin substrate")
    return r


def _preview(sess, eid):
    r = sess.post(f"{API}/estimates/{eid}/lp-package/preview", json={}, timeout=60)
    return r


def test_A_default_hover_lp_run_waste_and_basis(sess, temp_est):
    r = _run_lp_hover(sess, temp_est)
    assert r.status_code == 200, f"hover-lp-run: {r.status_code} {r.text[:400]}"
    p = _preview(sess, temp_est)
    assert p.status_code == 200, f"preview: {p.status_code} {p.text[:400]}"
    data = p.json()
    summary = data.get("summary") or {}
    wpa = summary.get("waste_pct_applied")
    assert wpa is not None, f"summary.waste_pct_applied missing; keys={list(summary.keys())}"
    assert abs(float(wpa) - 0.10) < 1e-6, f"waste_pct_applied={wpa}, expected 0.10"
    # geometry_basis label present somewhere in response
    gb = data.get("geometry_basis") or summary.get("geometry_basis")
    if gb is None:
        # look inside lines
        lines = data.get("lines") or data.get("materials") or []
        for l in lines:
            if isinstance(l, dict) and (l.get("geometry_basis") or (l.get("meta") or {}).get("geometry_basis")):
                gb = l.get("geometry_basis") or l["meta"]["geometry_basis"]
                break
    assert gb is not None, f"geometry_basis missing entirely. resp keys={list(data.keys())}"
    label = gb.get("label") if isinstance(gb, dict) else None
    assert label, f"geometry_basis.label empty: gb={gb}"


def test_B_facade_scope_custom_2376(sess, temp_est):
    scope = {"mode": "custom", "wrap_sqft": 2376, "excluded": {"brick": 234}}
    r = _run_lp_hover(sess, temp_est, facade_scope=scope)
    assert r.status_code == 200, f"hover-lp-run scoped: {r.status_code} {r.text[:400]}"
    p = _preview(sess, temp_est)
    assert p.status_code == 200
    data = p.json()
    # Find lap qty
    lines = data.get("lines") or data.get("materials") or []
    lap = None
    for l in lines:
        name = ((l.get("name") or "") + " " + (l.get("kind") or "") + " " + (l.get("category") or "")).lower()
        if "lap" in name or "smartside lap" in name or (l.get("profile") == "lap"):
            lap = l
            break
    assert lap is not None, f"no lap line found. lines={[l.get('name') for l in lines][:15]}"
    qty = lap.get("qty") or lap.get("quantity")
    # PIN AMENDED (lap unification ruling, 2026-07-19): book 11 pcs/sq
    # sealed; PDF 9.17 retired. Hover ruled waste 10% explicit.
    expected = math.ceil(2376 * 1.10 / 100 * 11)  # = 288 (was 286 under PDF divisor)
    assert qty == expected, f"lap qty={qty} expected {expected} (ceil(2376×1.10÷100×11))"
    # geometry basis label names 'scope 2376' or similar 2376 mention
    txt = str(data)
    assert "2376" in txt, "geometry basis / label should mention 2376 scope"


def test_C_letrick_photo_regression(sess):
    """LETRICK photo-path estimate preview: total_sell 12195.12 and waste_pct_applied 0.10.
    PIN AMENDED (chase ratification ruling, 2026-07-19): OSC 7→8 → 11327.40.
    PIN AMENDED (item-3 ratification, 2026-07-19): chase faces swap → lap 230 → 11420.37.
    PIN AMENDED (lap unification ruling, 2026-07-19): area key-bound 2099.7, book 11 pcs/sq,
    waste = contractor's field (Letrick estimate waste_pct = 10 → applied 0.10, no longer a
    baked default) → lap 255 = sealed key EXACTLY — total_sell 12195.12."""
    p = _preview(sess, LETRICK_ID)
    assert p.status_code == 200, f"letrick preview: {p.status_code} {p.text[:400]}"
    data = p.json()
    summary = data.get("summary") or {}
    pricing = summary.get("pricing") or {}
    total = pricing.get("total_sell") or summary.get("total_sell") or data.get("total_sell")
    assert total is not None, f"no total_sell; summary keys={list(summary.keys())} pricing={pricing}"
    assert abs(float(total) - 12195.12) < 0.01, f"total_sell={total}, expected 12195.12"
    wpa = summary.get("waste_pct_applied")
    assert wpa is not None, "summary.waste_pct_applied missing on letrick"
    assert abs(float(wpa) - 0.10) < 1e-6, f"waste_pct_applied={wpa}"
