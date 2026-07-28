"""QUOTE GATE vs ORDER GATE — two-tier flag doctrine (Howard ruled
2026-07-29, refining 2026-07-28 lists + three corrections).

QUOTE blocks customer surfaces (email, Accept @ mint, PDF, freeze, QR):
  facade_scope unresolved-zero · area_conservation breach ·
  siding_family_conflict · no_siding_on_siding_job ·
  labor_pending_contractor (correction: moved to QUOTE).
ORDER blocks material release / PO / truck:
  batten_wall_heights · corner_locators · opening_schedule ·
  opening_facade_attribution (correction: placed in ORDER) ·
  porch_ceiling_implied (correction: informational → ORDER).

UNASSIGNED-FLAG DETECTOR: every literal flag code / readiness kind
emitted anywhere in the backend must hold a registry row — a new flag
without a tier FAILS this suite at creation time.
"""
import re
import sys
import uuid
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import API  # noqa: E402
from gates import (GATE_TIERS, KIND_TIERS, ORDER_BLOCKING, QUOTE_BLOCKING,
                   quote_gate_blockers, tier_for)

BACKEND = Path("/app/backend")


# ── THE DETECTOR — an unassigned flag fails the suite ────────────────────
def test_every_emitted_flag_code_has_a_tier():
    code_pat = re.compile(r'"code":\s*"([a-z_]+)"')
    kind_pat = re.compile(r'"kind":\s*"([a-z_]+)"')
    sources = [BACKEND / "routes" / "lp_package_routes.py",
               BACKEND / "routes" / "hover.py",
               BACKEND / "gates.py"]
    unassigned = []
    for p in sources:
        txt = p.read_text()
        for c in set(code_pat.findall(txt)):
            if c not in GATE_TIERS and c not in KIND_TIERS:
                unassigned.append(f"{p.name}: code={c}")
        for k in set(kind_pat.findall(txt)):
            # readiness "kind" values tier through KIND_TIERS; package-line
            # derivation kinds (osc, isc, starter…) are not flags.
            if k in ("osc", "isc", "starter", "fascia_rake", "osc_lf",
                     "osc_hover_lf", "osc_corner_walk", "isc_corner_walk"):
                continue
            if k not in KIND_TIERS and k not in GATE_TIERS:
                unassigned.append(f"{p.name}: kind={k}")
    assert not unassigned, (
        "UNASSIGNED FLAG(S) — every flag is assigned to exactly ONE gate "
        f"tier at creation (ruled 2026-07-29): {sorted(unassigned)}")


def test_checklist_codes_all_assigned():
    from routes.lp_package_routes import _FLAG_CODES
    for c in _FLAG_CODES:
        assert tier_for(c) in ("quote", "order")


# ── tier assignments pinned exactly per the rulings ──────────────────────
def test_tier_assignments_sealed():
    assert QUOTE_BLOCKING == {
        "facade_scope_unresolved_zero", "area_conservation_breach",
        "siding_family_conflict", "no_siding_on_siding_job",
        "labor_pending_contractor"}
    assert ORDER_BLOCKING == {
        "batten_wall_heights", "corner_locators", "opening_schedule",
        "opening_facade_attribution", "porch_ceiling_implied"}
    # the three corrections, named
    assert GATE_TIERS["labor_pending_contractor"] == "quote"
    assert GATE_TIERS["opening_facade_attribution"] == "order"
    assert GATE_TIERS["porch_ceiling_implied"] == "order"
    # a tierless code raises — the runtime keyerror the detector prevents
    with pytest.raises(KeyError):
        tier_for("some_future_flag_nobody_assigned")


# ── QUOTE blockers, evaluated from estimate lines + measurements ─────────
def _lp_line(name, qty, **kw):
    return {"tab": "lp_smart", "section": "LP Smart Siding", "name": name,
            "unit": "PCS", "qty": qty, **kw}


def test_quote_blocker_siding_family_conflict():
    est = {"kind": "lp_smart", "lines": [
        _lp_line('38 Series Lap 3/8" x 8" x 16\'', 100),
        _lp_line("38 Series 4' x 10' Panel", 68)]}
    codes = {i["code"] for i in quote_gate_blockers(est)}
    assert "siding_family_conflict" in codes
    # human-typed rows are choices, never residue
    est["lines"][1]["qty_src"] = "human"
    codes = {i["code"] for i in quote_gate_blockers(est)}
    assert "siding_family_conflict" not in codes


def test_quote_blocker_no_siding_on_siding_job():
    est = {"kind": "lp_smart", "lines": [
        {"tab": "lp_smart", "section": "LP Siding Accessories",
         "name": "J blocks", "unit": "Each", "qty": 4}]}
    codes = {i["code"] for i in quote_gate_blockers(est)}
    assert "no_siding_on_siding_job" in codes
    est["lines"].append(_lp_line("38 Series 4' x 10' Panel", 68))
    codes = {i["code"] for i in quote_gate_blockers(est)}
    assert "no_siding_on_siding_job" not in codes


def test_quote_blocker_labor_pending():
    est = {"kind": "siding", "lines": [
        {"tab": "vinyl", "section": "Vinyl Siding", "name": "Charter Oak lap",
         "unit": "SQ", "qty": 20, "lab_src": "pending"}]}
    codes = {i["code"] for i in quote_gate_blockers(est)}
    assert "labor_pending_contractor" in codes
    est["lines"][0]["lab_src"] = "human"
    assert "labor_pending_contractor" not in {
        i["code"] for i in quote_gate_blockers(est)}


def test_quote_blocker_facade_zero_and_conservation():
    est = {"kind": "siding", "lines": [
        {"tab": "vinyl", "section": "Vinyl Siding", "name": "x",
         "unit": "SQ", "qty": 20}]}
    m = {"_facade_scope": {"wrap_sqft": 0.0, "measured_total": 3187.0},
         "_area_conservation": {"measured_total_sqft": 3187.0,
                                "sided_sqft": 0.0, "excluded_sqft": 2064.0,
                                "flagged_sqft": 0.0}}
    codes = {i["code"] for i in quote_gate_blockers(est, m)}
    assert "facade_scope_unresolved_zero" in codes
    assert "area_conservation_breach" in codes
    # resolved scope + conserved ledger clears both
    m2 = {"_facade_scope": {"wrap_sqft": 1123.0, "measured_total": 3187.0},
          "_area_conservation": {"measured_total_sqft": 3187.0,
                                 "sided_sqft": 1123.0, "excluded_sqft": 2064.0,
                                 "flagged_sqft": 0.0}}
    codes = {i["code"] for i in quote_gate_blockers(est, m2)}
    assert not codes & {"facade_scope_unresolved_zero", "area_conservation_breach"}


# ── the customer surfaces enforce the gate (HTTP) ────────────────────────
@pytest.fixture(scope="module")
def session():
    from creds_for_tests import TEST_EMAIL, TEST_PASSWORD
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture()
def gated_estimate(session):
    """TEST_ estimate with a labor-pending siding row → QUOTE-blocked."""
    r = session.post(f"{API}/estimates", json={
        "customer_name": f"TEST_gates_{uuid.uuid4().hex[:6]}",
        "kind": "lp_smart",
        "lines": [{"tab": "lp_smart", "section": "LP Smart Siding",
                   "name": '38 Series Lap 3/8" x 8" x 16"', "unit": "PCS",
                   "qty": 100, "mat": 10, "lab": 0, "lab_src": "pending"}],
    }, timeout=15)
    assert r.status_code == 200, r.text
    est = r.json()
    yield est
    session.delete(f"{API}/estimates/{est['id']}", timeout=15)


def test_gates_endpoint_and_quote_surfaces_block(session, gated_estimate):
    eid = gated_estimate["id"]
    g = session.get(f"{API}/estimates/{eid}/gates", timeout=30).json()
    assert g["quote"]["blocked"] is True
    codes = {i["code"] for i in g["quote"]["blocking"]}
    assert "labor_pending_contractor" in codes
    # PDF blocked with the structured 409
    r = session.post(f"{API}/estimates/{eid}/pdf",
                     json={"recipient_email": "x@example.com",
                           "html_quote": "<html>x</html>"}, timeout=30)
    assert r.status_code == 409, r.text
    d = r.json()["detail"]
    assert d["gate"] == "quote"
    assert any(b["code"] == "labor_pending_contractor" for b in d["blocking"])
    # email blocked at the same door (Accept token mints there)
    r = session.post(f"{API}/estimates/{eid}/email",
                     json={"recipient_email": "x@example.com",
                           "html_quote": "<html>x</html>"}, timeout=30)
    assert r.status_code == 409, r.text
    # order release refused while labor still pending? labor is QUOTE-tier
    # — the ORDER gate judges only its own items; with no run there are
    # no open order flags, release passes.
    r = session.post(f"{API}/estimates/{eid}/order-release", json={}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["order_released"]["by"]


def test_quote_clears_when_labor_filled(session, gated_estimate):
    eid = gated_estimate["id"]
    est = session.get(f"{API}/estimates/{eid}", timeout=15).json()
    est["lines"][0]["lab"] = 55.0
    est["lines"][0]["lab_src"] = "human"
    r = session.put(f"{API}/estimates/{eid}", json=est, timeout=15)
    assert r.status_code == 200, r.text
    g = session.get(f"{API}/estimates/{eid}/gates", timeout=30).json()
    assert g["quote"]["blocked"] is False, g["quote"]["blocking"]
