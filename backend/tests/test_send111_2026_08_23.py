"""SEND-111 pins — the X-Ruler ruling registered, the refusal law
WIDENED (the trio + qty null are server-owned at the client-shaped
doors, exactly as chase rows are), and the QR field sheet.

The RCA (SEND-110 §3) found the law RAN on the stripped payload and
chase rows were immune because the law owns them; the refusal trio was
lost because it did not. Fix ruled 2026-08-14: widen what the law owns
— not a guard beside it.
"""
import sys
import uuid

import pytest
import requests

sys.path.insert(0, "/app/backend")
from api_base import API  # env-derived
from creds_for_tests import TEST_PASSWORD


# ── the register carries the ruling ──────────────────────────────────

def test_register_carries_residual_and_noise_floor():
    from ocr_geometry import RULINGS_REGISTER
    findings = "\n".join(RULINGS_REGISTER["findings"])
    assert "REGISTERED AS NAMED" in findings
    assert "REJECTED" in findings and "+10 ft" in findings
    assert "ELEVATION NOISE FLOOR" in findings
    assert "3.8%" in findings and "9.36 y-%" in findings and "9.73 y-%" in findings
    assert "sub-4%" in findings


# ── the refusal law, unit pins ────────────────────────────────────────

def _refused_row(**over):
    row = {"tab": "lp_smart", "section": "Seamless Gutter",
           "name": "Gutter 5in", "unit": "LF", "mat": 2, "lab": 1,
           "qty": None, "qty_src": None,
           "not_derivable": True,
           "not_derivable_reason": "no verified wall height",
           "not_derivable_code": "RULING_V_NO_VERIFIED_HEIGHT",
           "note": "REFUSED — Ruling V"}
    row.update(over)
    return row


def test_stripped_trio_reseats_and_null_never_launders_to_zero():
    from routes.pdf_overlay import apply_refusal_law
    stored = [_refused_row()]
    incoming = [{"tab": "lp_smart", "section": "Seamless Gutter",
                 "name": "Gutter 5in", "unit": "LF", "mat": 2, "lab": 1,
                 "qty": 0, "qty_src": None}]   # the fifth member's shape
    out = apply_refusal_law(stored, incoming)
    assert len(out) == 1
    assert out[0]["not_derivable"] is True
    assert out[0]["not_derivable_code"] == "RULING_V_NO_VERIFIED_HEIGHT"
    assert out[0]["not_derivable_reason"] == "no verified wall height"
    assert out[0]["qty"] is None               # null, never 0


def test_explicit_human_qty_supersedes_the_null_trio_still_rides():
    from routes.pdf_overlay import apply_refusal_law
    out = apply_refusal_law(
        [_refused_row()],
        [{"tab": "lp_smart", "section": "Seamless Gutter",
          "name": "Gutter 5in", "qty": 42, "qty_src": "human"}])
    assert out[0]["qty"] == 42                 # Law A — human governs
    assert out[0]["not_derivable"] is True     # provenance stays visible


def test_client_cannot_mint_a_refusal():
    from routes.pdf_overlay import apply_refusal_law
    stored = [{"tab": "vinyl", "section": "Vinyl Siding",
               "name": "D4 Panel", "qty": 12}]
    out = apply_refusal_law(
        stored,
        [{"tab": "vinyl", "section": "Vinyl Siding", "name": "D4 Panel",
          "qty": 12, "not_derivable": True,
          "not_derivable_reason": "client-invented"}])
    assert "not_derivable" not in out[0]
    assert "not_derivable_reason" not in out[0]


def test_client_cannot_clear_by_dropping_the_row():
    from routes.pdf_overlay import apply_refusal_law
    out = apply_refusal_law([_refused_row()], [])
    assert len(out) == 1                       # the law re-ADDS what it owns
    assert out[0]["not_derivable"] is True
    assert out[0]["qty"] is None


def test_chase_rows_pass_through_untouched_overlay_law_owns_them():
    from routes.pdf_overlay import apply_refusal_law
    chase_stored = {"tab": "vinyl", "section": "Vinyl Siding",
                    "name": "Chimney Chase — rear",
                    "overlay_chase_line": True, "not_derivable": True,
                    "qty": None}
    fresh_chase = {"tab": "vinyl", "section": "Vinyl Siding",
                   "name": "Chimney Chase — rear",
                   "overlay_chase_line": True, "qty": 2.1}
    out = apply_refusal_law([chase_stored], [fresh_chase])
    assert out == [fresh_chase]                # verbatim, no re-seat, no re-add


# ── structural pin: BOTH client-shaped doors run the widened law ─────

def test_both_client_doors_call_the_refusal_law():
    src = open("/app/backend/routes/estimates.py").read()
    assert src.count("reapply_refusal_law(est_id") == 2  # PUT + PATCH
    # rebuild doors stay authoritative — no rebuild path calls it
    for f in ("routes/hover.py", "routes/lp_package_routes.py"):
        assert "reapply_refusal_law" not in open(f"/app/backend/{f}").read()


# ── live pins over HTTP (disposable estimate, cleaned up) ─────────────

@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": "hhunt6677@yahoo.com",
                     "password": TEST_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip("env:live_auth: test login unavailable")
    return s


@pytest.fixture()
def disposable(sess):
    r = sess.post(f"{API}/estimates", json={
        "customer_name": f"SEND111 disposable {uuid.uuid4().hex[:6]}",
        "address": "1 Disposable Way"}, timeout=15)
    assert r.status_code == 200, r.text
    est = r.json()
    yield est
    sess.delete(f"{API}/estimates/{est['id']}", timeout=15)


def test_live_put_cannot_strip_the_trio(sess, disposable):
    import os
    from dotenv import load_dotenv
    from pymongo import MongoClient
    load_dotenv("/app/backend/.env")
    db = MongoClient(os.environ["MONGO_URL"],
                     serverSelectionTimeoutMS=2000)[os.environ["DB_NAME"]]
    eid = disposable["id"]
    db.estimates.update_one({"id": eid}, {"$set": {"lines": [_refused_row()]}})
    # the fifth member's exact move: trio gone, qty laundered to 0
    r = sess.put(f"{API}/estimates/{eid}", json={"lines": [
        {"tab": "lp_smart", "section": "Seamless Gutter",
         "name": "Gutter 5in", "unit": "LF", "mat": 2, "lab": 1,
         "qty": 0}]}, timeout=20)
    assert r.status_code == 200, r.text
    rows = r.json()["lines"]
    assert len(rows) == 1
    assert rows[0]["not_derivable"] is True
    assert rows[0]["not_derivable_code"] == "RULING_V_NO_VERIFIED_HEIGHT"
    assert rows[0]["qty"] is None


def test_live_field_sheet_serves_qr_and_cards(sess, disposable):
    eid = disposable["id"]
    r = sess.get(f"{API}/estimates/{eid}/pdf-overlay/field-sheet",
                 params={"app_url": "https://example.test"}, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["estimate_id"] == eid
    assert isinstance(d["cards"], list)
    assert d["qr_estimate"]["link"] == f"https://example.test/estimate/{eid}"
    assert d["qr_estimate"]["png"].startswith("data:image/png;base64,")
    # no frozen material list on a fresh estimate — reason, never a mint
    assert d["qr_material_list"]["png"] is None
    assert "freeze" in d["qr_material_list"]["reason"]
    # a field sheet carries no quantity
    assert "quantity" in d["note"]
