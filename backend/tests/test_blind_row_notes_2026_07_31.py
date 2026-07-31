"""BLIND-ROW NOTES (Howard ruled 2026-07-31, queue step 2).

The ~39 hand-filled manual rows (manual_rows_census_2026-07-30.txt) are
structurally invisible to every derivation-note mechanism — a note cannot
ride a line that is never emitted. The contractor_note field is theirs:
human-owned, survives every re-derive, prints on the material list.

Also seals the FRONTEND HALF of the silent-strip class found while
building this: useEstimate.js buildPayload whitelisted line keys and
dropped note/_waste_included/qty_pending on every browser autosave.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creds_for_tests import TEST_PASSWORD

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", TEST_PASSWORD)

MEAS = {"siding_sqft": 2000, "eaves_lf": 120, "rakes_lf": 80,
        "soffit_sqft": 200, "outside_corner_count": 4,
        "inside_corner_count": 2, "window_count": 10, "door_count": 2,
        "overhang_in": 12}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture()
def est_factory(s):
    made = []

    def make(kind, **fields):
        r = s.post(f"{API}/estimates",
                   json={"customer_name": f"TEST_NOTE-{uuid.uuid4().hex[:6]}",
                         "kind": kind})
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        made.append(eid)
        r = s.put(f"{API}/estimates/{eid}",
                  json={"hover_measurements": dict(MEAS), "waste_pct": 10, **fields})
        assert r.status_code == 200, r.text
        return eid

    yield make
    for eid in made:
        s.delete(f"{API}/estimates/{eid}")


def _rederive(s, eid):
    r = s.post(f"{API}/estimates/{eid}/rederive", json={"trigger": "test"})
    assert r.status_code == 200, r.text
    return r.json()["lines"]


def _row(lines, tab, name, section=None):
    for l in lines:
        if l.get("tab") == tab and l.get("name") == name \
                and (section is None or l.get("section") == section):
            return l
    return None


# ═══════════ THE JOURNEY — note survives every re-derive ═══════════════
def test_blind_row_note_survives_rederive(est_factory, s):
    """A hand-filled blind row (never emitted by any derivation) carries a
    contractor note through PUT → re-derive verbatim."""
    eid = est_factory("siding")
    lines = _rederive(s, eid)
    lines.append({"tab": "vinyl", "section": "Siding Accessories",
                  "name": "J-blocks - Split Blocks (82A009)", "unit": "Each",
                  "qty": 4, "qty_src": "human", "mat": 13.49, "lab": 0,
                  "contractor_note": "east wall, beside the meter box"})
    r = s.put(f"{API}/estimates/{eid}", json={"lines": lines})
    assert r.status_code == 200, r.text
    after = _rederive(s, eid)
    jb = _row(after, "vinyl", "J-blocks - Split Blocks (82A009)")
    assert jb, "hand-filled blind row must survive the re-derive"
    assert jb.get("qty") == 4 and jb.get("qty_src") == "human"
    assert jb.get("contractor_note") == "east wall, beside the meter box"


def test_note_on_derived_row_survives_rebuild(est_factory, s):
    """contractor_note is HUMAN-OWNED even on a derivation-owned row: the
    rebuild regenerates qty + machine note but inherits the human note
    (same inheritance as mat/lab/ami_part)."""
    eid = est_factory("siding")
    lines = _rederive(s, eid)
    hw = _row(lines, "vinyl", "House Wrap")
    assert hw, "House Wrap must derive on a vinyl siding job"
    hw["contractor_note"] = "wrap the bay window seam twice"
    r = s.put(f"{API}/estimates/{eid}", json={"lines": lines})
    assert r.status_code == 200, r.text
    after = _rederive(s, eid)
    hw2 = _row(after, "vinyl", "House Wrap")
    assert hw2.get("contractor_note") == "wrap the bay window seam twice"
    assert "roll" in (hw2.get("note") or "").lower(), \
        "machine derivation note stays machine-owned (regenerated)"


# ═══════════ MODEL — declared, bounded, never silently stripped ════════
def test_contractor_note_is_a_declared_model_field():
    from models import EstimateLine
    assert "contractor_note" in EstimateLine.model_fields, \
        "contractor_note must be DECLARED — extra='allow' passthrough is " \
        "how the silent-strip class starts"


def test_contractor_note_length_bound(est_factory, s):
    eid = est_factory("siding")
    r = s.put(f"{API}/estimates/{eid}", json={"lines": [
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": "J-blocks - Split Blocks (82A009)", "unit": "Each",
         "qty": 1, "qty_src": "human", "mat": 13.49, "lab": 0,
         "contractor_note": "x" * 501}]})
    assert r.status_code == 422, "501-char note must bound-fail, not truncate silently"


# ═══════════ SURFACES — print + payload (frontend halves) ══════════════
def test_material_list_prints_the_note():
    js = Path("/app/frontend/src/lib/materialList.js").read_text()
    assert "contractor_note" in js and "note-row" in js, \
        "the printed material list must render contractor_note under the row"
    assert "nota del contratista" in js, "ES print label required"


def test_build_payload_carries_the_note_fields():
    """FRONTEND SILENT-STRIP SEAL: the autosave payload whitelist must
    carry every derivation/provenance line field the backend round-trips.
    Found live 2026-07-31: note/_waste_included/qty_pending were dropped
    on every browser autosave."""
    js = Path("/app/frontend/src/lib/useEstimate.js").read_text()
    for key in ("note: l.note", "contractor_note: l.contractor_note",
                "_waste_included: l._waste_included",
                "qty_pending: l.qty_pending",
                "pricing_source: l.pricing_source"):
        assert key in js, f"buildPayload must send {key.split(':')[0]} — silent-strip class"
    # MERGE LAYER: the catalog merge rebuilds line objects on every load —
    # it must carry the same fields or the next autosave writes the loss.
    for key in ("note: (saved && saved.note)",
                "contractor_note: (saved && saved.contractor_note)",
                "_waste_included: saved && saved._waste_included"):
        assert key in js, f"catalog merge must carry {key.split(':')[0]}"


def test_editor_has_the_note_ui():
    jsx = Path("/app/frontend/src/components/estimate/SectionAccordion.jsx").read_text()
    for tid in ("contractor-note-btn-", "contractor-note-input-", "contractor-note-block-"):
        assert tid in jsx, f"note UI testid {tid} missing"
