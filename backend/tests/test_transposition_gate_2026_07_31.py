"""TRANSPOSITION GATE (Howard ruled 2026-07-31).

His uploaded price page landed House Wrap and RainDrop CROSSED (each
carrying the other's roll dollar) and NOTHING in the app caught it — only
his own sanity check. THE RULE, pinned here: a price write that moves
past the ×3 threshold without an explicit human confirm FAILS. The diff
preview names the magnitude ("House Wrap $11.55 → $336.13 (+2810%)") in
red; the gate lives on the same price-integrity surface as the age chip
(price_age.py) and covers BOTH write surfaces: bulk apply and the
single-cell tier editor.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")

from api_base import API
from price_age import MAGNITUDE_THRESHOLD, annotate_magnitude, magnitude_flag, magnitude_pct

ADMIN_TOKEN = os.environ.get("SUPPLIER_ADMIN_TOKEN", "")
H = {"X-Admin-Token": ADMIN_TOKEN}


# ═══════════ THE MATH — one gate, both directions ═══════════════════════
class TestGateMath:
    def test_threshold_is_three(self):
        assert MAGNITUDE_THRESHOLD == 3.0

    @pytest.mark.parametrize("old,new,flagged", [
        (10.0, 29.9, False),   # just under ×3
        (10.0, 30.0, True),    # exactly ×3 — gate
        (10.0, 3.34, False),   # just above ÷3
        (10.0, 3.33, True),    # ÷3 — gate (a crossed CHEAP row too)
        (10.0, 0.0, True),     # zeroing a live price — confirm it
        (0.0, 500.0, False),   # first price on an unpriced row: no basis
        (10.0, 12.0, False),   # ordinary move rides free
    ])
    def test_boundaries(self, old, new, flagged):
        assert magnitude_flag(old, new) is flagged

    def test_the_howard_row(self):
        # The defect this gate exists for: the transposed wrap entry.
        assert magnitude_flag(11.55, 336.13) is True
        assert magnitude_pct(11.55, 336.13) == 2810.2

    def test_annotate_stamps_preview_rows(self):
        rows = annotate_magnitude([{"old": 11.55, "new": 336.13},
                                   {"old": 22.12, "new": 23.00}])
        assert rows[0]["magnitude_flag"] is True and rows[0]["pct"] == 2810.2
        assert rows[1]["magnitude_flag"] is False


# ═══════════ THE JOURNEY — both write surfaces refuse, then obey ════════
@pytest.fixture()
def gate_tier():
    """Throwaway tier doc, created + deleted around each test."""
    from pymongo import MongoClient

    tid = f"TEST_GATE-{uuid.uuid4().hex[:8]}"
    doc = {"id": tid, "name": f"TEST_GATE tier {tid[-4:]}",
           "sections": [{"title": "Siding Accessories",
                         "items": [{"name": "House Wrap", "unit": "ROLL",
                                    "mat": 10.0, "lab": 5.0}]}]}
    coll = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].price_tiers
    coll.insert_one(dict(doc))
    yield doc
    coll.delete_many({"id": tid})


def _mat(tier_id):
    t = requests.get(f"{API}/admin/tiers/{tier_id}", headers=H).json()
    return t["sections"][0]["items"][0]["mat"]


def _change(tier, new, confirmed=False):
    return {"tier_id": tier["id"], "tier_name": tier["name"],
            "section": "Siding Accessories", "name": "House Wrap",
            "unit": "ROLL", "field": "mat", "old": 10.0, "new": new,
            "confirmed": confirmed}


def test_bulk_apply_refuses_unconfirmed_then_obeys(gate_tier):
    r = requests.post(f"{API}/admin/pricing/apply",
                      json={"changes": [_change(gate_tier, 35.0)]}, headers=H)
    assert r.status_code == 409, r.text
    gate = r.json()["detail"]["magnitude_gate"]
    assert gate[0]["name"] == "House Wrap" and gate[0]["pct"] == 250.0
    assert _mat(gate_tier["id"]) == 10.0, "NOTHING may write on a refused batch"

    r = requests.post(f"{API}/admin/pricing/apply",
                      json={"changes": [_change(gate_tier, 35.0, confirmed=True)]}, headers=H)
    assert r.status_code == 200 and r.json()["applied"] == 1, r.text
    assert _mat(gate_tier["id"]) == 35.0


def test_bulk_apply_gate_checks_live_value_not_posted_old(gate_tier):
    """A stale/forged 'old' cannot sneak a ×3 move past the gate."""
    c = _change(gate_tier, 35.0)
    c["old"] = 34.0  # claims a small move; live value is 10.0 → ×3.5
    r = requests.post(f"{API}/admin/pricing/apply", json={"changes": [c]}, headers=H)
    assert r.status_code == 409, "gate must re-derive against the LIVE stored value"
    assert _mat(gate_tier["id"]) == 10.0


def test_bulk_apply_ordinary_move_rides_free(gate_tier):
    r = requests.post(f"{API}/admin/pricing/apply",
                      json={"changes": [_change(gate_tier, 12.0)]}, headers=H)
    assert r.status_code == 200 and r.json()["applied"] == 1, r.text
    assert _mat(gate_tier["id"]) == 12.0


def test_tier_editor_refuses_unconfirmed_then_obeys(gate_tier):
    sections = [{"title": "Siding Accessories",
                 "items": [{"name": "House Wrap", "unit": "ROLL",
                            "mat": 57.0, "lab": 5.0}]}]
    r = requests.put(f"{API}/admin/tiers/{gate_tier['id']}",
                     json={"sections": sections}, headers=H)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["magnitude_gate"][0]["pct"] == 470.0
    assert _mat(gate_tier["id"]) == 10.0, "the editor write must not half-land"

    r = requests.put(f"{API}/admin/tiers/{gate_tier['id']}",
                     json={"sections": sections, "confirm_magnitude": True}, headers=H)
    assert r.status_code == 200, r.text
    assert _mat(gate_tier["id"]) == 57.0


# ═══════════ SURFACES — the red row + confirm live in the UI ════════════
def test_diff_preview_renders_the_gate():
    js = Path("/app/frontend/src/components/admin/PricingUpdatePanel.jsx").read_text()
    for needle in ("magnitude-gate-banner", "magnitude-confirm-", "magnitude_flag",
                   "onApply(confirmed)"):
        assert needle in js, f"diff preview must carry the gate UI: {needle}"


def test_tier_editor_sends_the_confirm():
    js = Path("/app/frontend/src/pages/BrandingAdmin.jsx").read_text()
    assert "confirm_magnitude" in js and "magnitude_gate" in js, \
        "tier editor must handle the 409 and re-send with the human's confirm"
