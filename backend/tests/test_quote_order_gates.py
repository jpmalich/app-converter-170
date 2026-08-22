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
    # labor_pending_contractor removed from blocking (re-ruled 2026-07-29):
    # labor is N/A or >$0 — anything else is UNDECIDED, one line, a count,
    # NEVER a block.
    # photo_fillin_unset ADDED by ruling 2026-08-02: an unset photo
    # fill-in box is SCOPE NOT SET, never $0 — hard quote block, the
    # silent-zero class (a nudge you can click past is how the zero
    # reaches a homeowner).
    # footprint_does_not_close ADDED by Ruling EE 2026-08-14 send-25: a
    # face that fails DD footprint closure is NOT DERIVABLE and hard-blocks
    # the quote — pricing a face against a check that says it cannot be
    # closed is the exact silent number EE exists to stop.
    # chase_contested_scale ADDED by SEND-96 item 2: a chimney-chase row
    # on a CONTESTED-scale face refuses — an unverifiable quantity must
    # not quietly price; Ruling L makes the total INCOMPLETE.
    assert QUOTE_BLOCKING == {
        "facade_scope_unresolved_zero", "area_conservation_breach",
        "siding_family_conflict", "no_siding_on_siding_job",
        "photo_fillin_unset", "footprint_does_not_close",
        "chase_contested_scale"}
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


def test_quote_labor_undecided_one_line_never_blocks():
    """Re-ruled 2026-07-29: labor is N/A or >$0 — anything else is
    UNDECIDED, surfaced as ONE line with a COUNT (no row list), and it
    does NOT block."""
    est = {"kind": "siding", "lines": [
        {"tab": "vinyl", "section": "Vinyl Siding", "name": "Charter Oak lap",
         "unit": "SQ", "qty": 20, "lab_src": "pending"},
        {"tab": "vinyl", "section": "Siding Accessories", "name": "Starter",
         "unit": "PCS", "qty": 12, "lab_src": "pending"}]}
    items = quote_gate_blockers(est)
    labor = next(i for i in items if i["code"] == "labor_pending_contractor")
    assert labor["blocking"] is False
    assert "2 row(s)" in labor["label"]
    assert "Charter Oak" not in labor["label"]   # a count, not a list
    est["lines"][0]["lab_src"] = "human"
    est["lines"][1]["lab_src"] = "human"
    assert not [i for i in quote_gate_blockers(est)
                if i["code"] == "labor_pending_contractor"]


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
    """TEST_ estimate with TWO families carrying derived qty → QUOTE-blocked
    (family conflict). Labor no longer blocks (re-ruled 2026-07-29)."""
    r = session.post(f"{API}/estimates", json={
        "customer_name": f"TEST_gates_{uuid.uuid4().hex[:6]}",
        "kind": "lp_smart",
        "lines": [
            {"tab": "lp_smart", "section": "LP Smart Siding",
             "name": '38 Series Lap 3/8" x 8" x 16"', "unit": "PCS",
             "qty": 100, "mat": 10, "lab": 0, "lab_src": "pending"},
            {"tab": "lp_smart", "section": "LP Smart Siding",
             "name": "38 Series 4' x 10' Panel", "unit": "PCS",
             "qty": 68, "mat": 10, "lab": 5},
        ],
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
    assert "siding_family_conflict" in codes
    # labor is present as info — one line, a count, never blocking
    labor = [i for i in g["quote"]["items"]
             if i["code"] == "labor_pending_contractor"]
    assert labor and labor[0]["blocking"] is False
    assert "labor_pending_contractor" not in codes
    # PDF blocked with the structured 409
    r = session.post(f"{API}/estimates/{eid}/pdf",
                     json={"recipient_email": "x@example.com",
                           "html_quote": "<html>x</html>"}, timeout=30)
    assert r.status_code == 409, r.text
    d = r.json()["detail"]
    assert d["gate"] == "quote"
    assert any(b["code"] == "siding_family_conflict" for b in d["blocking"])
    # email blocked at the same door (Accept token mints there)
    r = session.post(f"{API}/estimates/{eid}/email",
                     json={"recipient_email": "x@example.com",
                           "html_quote": "<html>x</html>"}, timeout=30)
    assert r.status_code == 409, r.text
    # ORDER gate judges only its own items; with no run there are no open
    # order flags, release passes.
    r = session.post(f"{API}/estimates/{eid}/order-release", json={}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["order_released"]["by"]


def test_quote_clears_when_conflict_resolved(session, gated_estimate):
    eid = gated_estimate["id"]
    est = session.get(f"{API}/estimates/{eid}", timeout=15).json()
    est["lines"][1]["qty"] = 0          # second family zeroed — one family stands
    r = session.put(f"{API}/estimates/{eid}", json=est, timeout=15)
    assert r.status_code == 200, r.text
    g = session.get(f"{API}/estimates/{eid}/gates", timeout=30).json()
    assert g["quote"]["blocked"] is False, g["quote"]["blocking"]
    # labor UNDECIDED still rides as the non-blocking one-liner
    labor = [i for i in g["quote"]["items"]
             if i["code"] == "labor_pending_contractor"]
    assert labor and labor[0]["blocking"] is False


# ── PLAIN TRADE LANGUAGE (Howard ruled 2026-07-29) ───────────────────────
def test_stored_flag_labels_sanitized_at_serve_time():
    """Older imports stored labels carrying doctrine tags and ANOTHER
    customer's address. The serve-time choke point strips both — no seal
    dates, no ruling tags, no cross-estimate references reach the UI."""
    from routes.lp_package_routes import _checklist_flags, _plain_label
    run = {"hover_mapping_flags": [
        {"code": "corner_locators",
         "label": ("corner sticks — averages HIDE tall corners (never-average "
                   "rule sealed 2026-07-28, P3 precedent; 261 Haugh: an 18'5\" "
                   "corner takes 2 sticks). Tape tall corners"),
         "verify": "Walk the corners (P3 precedent)"},
        {"code": "opening_facade_attribution",
         "label": ("OPENING↔FACADE ATTRIBUTION UNAVAILABLE (Class C sealed "
                   "2026-07-28): 35 openings cannot be attributed")},
        {"code": "porch_ceiling_implied",
         "label": "porch ceilings IMPLIED (Q2 ruled 2026-07-27): soffit 2620"},
    ]}
    served = _checklist_flags(run, {})
    joined = " ".join((f.get("label") or "") + " " + (f.get("verify") or "")
                      for f in served)
    for banned in ("sealed 20", "ruled 20", "261 Haugh", "P3 precedent",
                   "Class C"):
        assert banned not in joined, f"doctrine/cross-estimate leak: {banned}"
    assert "OPENINGS NOT TIED TO WALLS" in joined
    assert "PORCH CEILINGS LIKELY" in joined
    # sanitizer is idempotent on already-plain wording
    plain = "Tape tall corners on the walk — close with the taped heights."
    assert _plain_label(plain) == plain
