"""CLOBBER-TRAP CLASS — founding pins (ruled 2026-07-24, register entry).

THE DEFECT CLASS: silent field-default corruption on partial updates.
`PUT /estimates/{id}` dumped the full EstimateIn model with
exclude_none=True — every field with a non-None DEFAULT (39 of 64:
kind="siding", lines=[], waste_pct=0, margin_pct=30.0, tax_rate=7.0,
status_label="draft", every color="") was written on EVERY partial PUT,
clobbering stored values the caller never mentioned.

THE EVIDENCE (Jon Casile, live): EST-523061 was created lp_smart-kind and
materialized 7 Hover→LP runs on Jul 23–24 (tracking log). A lines-only
PUT flipped kind → "siding", after which the rebuild endpoint 400'd on
Jon's own estimate ("LP SmartSide only").

THE RULE (permanent): a partial update writes ONLY the fields explicitly
sent (model_fields_set). The class dies as a class, not a field.
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")
from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture()
def temp_estimate(session):
    r = session.post(f"{API}/estimates", json={
        "kind": "lp_smart", "customer_name": "ZZ clobber-pin TEMP",
        "margin_pct": 42.5, "waste_pct": 8, "tax_rate": 6.25,
        "status_label": "sent", "siding_color": "Snowscape White",
        "lines": [{"tab": "lp_smart", "section": "S", "name": "row",
                   "unit": "PCS", "qty": 3, "mat": 1.0, "lab": 0.0}],
    }, timeout=15)
    assert r.status_code == 200, r.text
    est = r.json()
    yield est
    session.delete(f"{API}/estimates/{est['id']}", timeout=15)


def test_lines_only_put_does_not_flip_kind(session, temp_estimate):
    """THE JON VECTOR: a lines-only PUT must not rewrite kind to 'siding'."""
    eid = temp_estimate["id"]
    r = session.put(f"{API}/estimates/{eid}",
                    json={"lines": temp_estimate["lines"]}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "lp_smart"


def test_partial_put_clobbers_nothing_it_did_not_send(session, temp_estimate):
    """CLASS PIN: money knobs, status, colors, and LINES survive a PUT
    that only touched notes."""
    eid = temp_estimate["id"]
    r = session.put(f"{API}/estimates/{eid}", json={"notes": "hi"}, timeout=15)
    assert r.status_code == 200, r.text
    after = r.json()
    assert after["notes"] == "hi"
    assert after["margin_pct"] == 42.5
    assert after["waste_pct"] == 8
    assert after["tax_rate"] == 6.25
    assert after["status_label"] == "sent"
    assert after["siding_color"] == "Snowscape White"
    assert len(after["lines"]) == 1 and after["lines"][0]["qty"] == 3


def test_explicitly_sent_fields_still_write(session, temp_estimate):
    eid = temp_estimate["id"]
    r = session.put(f"{API}/estimates/{eid}",
                    json={"margin_pct": 15.0, "customer_name": "ZZ renamed TEMP"},
                    timeout=15)
    assert r.status_code == 200, r.text
    after = r.json()
    assert after["margin_pct"] == 15.0
    assert after["customer_name"] == "ZZ renamed TEMP"
    assert after["kind"] == "lp_smart"  # untouched


def test_kind_is_identity_immutable_on_update(session, temp_estimate):
    """2nd Jon flip (same day): a stale client's full-payload autosave
    replayed kind onto the healed estimate. RULE: kind is identity —
    PUT and PATCH both IGNORE it post-create."""
    eid = temp_estimate["id"]
    r = session.put(f"{API}/estimates/{eid}", json={"kind": "windows"}, timeout=15)
    assert r.status_code == 200 and r.json()["kind"] == "lp_smart"
    r = session.patch(f"{API}/estimates/{eid}", json={"kind": "siding"}, timeout=15)
    assert r.status_code == 200 and r.json()["kind"] == "lp_smart"


def test_editor_payload_never_sends_kind():
    """JSX pin: the editor's full-payload save omits kind entirely."""
    ue = (BACKEND.parent / "frontend" / "src" / "lib" / "useEstimate.js").read_text()
    assert "kind: source.kind" not in ue


def test_guard_is_the_fields_set_include():
    """CODE PIN: the guard is include=model_fields_set — the whole default
    surface (39 defaulted fields) is covered by construction, so new model
    fields can never re-open the trap."""
    src = (BACKEND / "routes" / "estimates.py").read_text()
    assert "include=body.model_fields_set" in src
