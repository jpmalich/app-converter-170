"""PROFILE OWNS ITS FAMILY — founding pins (P0 regression, ruled 2026-07-24).

THE REGRESSION (Jon Casile, live): the "Restore HOVER lines" path called
/measure/map PROFILE-BLIND → it derived the DEFAULT (lap) family from the
cached measurements → the legacy apply merge ADDED lap rows beside the
mapped B&B rows → 38 Series Lap 251 PCS ($7,778.49) AND 4'×10' Panel
rows priced together on one estimate.
($7,862.58) both summed into the homeowner price. Exact reproduction:
/measure/map on Jon's cached 2064-scope measurements emits lap 228 →
client 10% bake → 251 × $30.99 = $7,778.49 to the penny.

THE RULE (permanent): on a profile-mapped estimate, rebuilds/restores
write the selected family's derived quantities and ZERO every other
siding family's DERIVED quantities (visible qty-0). Human-typed
quantities (qty_src == "human") survive — mixed-material jobs are human
choices, never derivation residue.

FOUNDING STATE (this estimate, pinned): after fix — lap = 0, panels = 68
(B&B family waste 30%, sealed 2026-07-24),
group total = panels only.
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

CASILE_EST = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"  # EST-523061
HOVER_RUN = "8f6f9b5e6bb3422f84e24932addc0a13"
LAP_KEY = {"tab": "lp_smart", "section": "LP Smart Siding",
           "name": "38 Series Lap 3/8\" x 8\" x 16'"}
PANEL_NAME = "38 Series 4' x 10' Panel"
REBUILD_PAYLOAD = {
    "hover_run_id": HOVER_RUN, "profile": "board_batten",
    "facade_scope": {"mode": "custom", "wrap_sqft": 2064,
                     "excluded": {"stucco": 312, "brick": 234}},
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


def _put_lines(session, lines):
    r = session.put(f"{API}/estimates/{CASILE_EST}", json={"lines": lines}, timeout=30)
    assert r.status_code == 200, r.text


def _get_lines(session):
    return session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()["lines"]


def test_measure_map_profile_blind_reproduces_the_regression(session):
    """EVIDENCE PIN: the profile-blind mapper on Jon's cached measurements
    emits the lap family — the exact vector that produced lap 251."""
    est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
    hm = est.get("hover_measurements") or {}
    assert hm.get("siding_sqft") == 2064.0
    # FOUNDING-ERA state: the import stamped _waste_pct 0.0 (draft base
    # quantities; the field baked client-side). Family-waste rebuilds
    # (sealed 2026-07-24) stamp 0.30 — reset so the evidence stays exact.
    hm = {**hm, "_waste_pct": 0.0}
    d = session.post(f"{API}/measure/map", json={"measurements": hm}, timeout=60).json()
    lap = [l for l in d["lines"] if l["name"] == LAP_KEY["name"]]
    assert lap and lap[0]["qty"] == 228  # × 1.10 bake → 251 (Jon's number)


def test_measure_map_with_profile_owns_its_family(session):
    """FIXED PATH: profile=board_batten → NO lap rows, and the lap key is
    named in zero_family_lines so the apply merge zeroes residue."""
    est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
    d = session.post(f"{API}/measure/map",
                     json={"measurements": est["hover_measurements"],
                           "profile": "board_batten"}, timeout=60).json()
    names = {l["name"] for l in d["lines"]}
    assert PANEL_NAME in names
    assert LAP_KEY["name"] not in names
    zeros = {(z["tab"], z["section"], z["name"]) for z in d["zero_family_lines"]}
    assert (LAP_KEY["tab"], LAP_KEY["section"], LAP_KEY["name"]) in zeros


def test_founding_state_rebuild_zeroes_lap_keeps_panels(session):
    """FOUNDING TEST (Jon's exact regression state): seed lap 251 as
    machine residue → rebuild → lap row PRESENT at qty 0, panels 68,
    lp_smart group total counts the panel family only."""
    lines = _get_lines(session)
    lines = [l for l in lines if l.get("name") != LAP_KEY["name"]]
    lines.append({**LAP_KEY, "unit": "PCS", "qty": 251, "raw_qty": 228.0,
                  "mat": 30.99, "lab": 0.0})
    _put_lines(session, lines)
    r = session.post(f"{API}/estimates/{CASILE_EST}/hover-lp-run",
                     json=REBUILD_PAYLOAD, timeout=90)
    assert r.status_code == 200, r.text
    after = _get_lines(session)
    lap = [l for l in after if l.get("name") == LAP_KEY["name"]]
    assert lap and lap[0]["qty"] == 0, lap  # zeroed, visible, price kept
    panel = next(l for l in after if l.get("name") == PANEL_NAME)
    assert panel["qty"] == 68  # B&B family waste 30% (sealed 2026-07-24)
    lap_dollars = sum((l.get("qty") or 0) * ((l.get("mat") or 0) + (l.get("lab") or 0))
                      for l in after if "Lap" in str(l.get("name")) and l.get("tab") == "lp_smart")
    assert lap_dollars == 0


def test_human_typed_quantity_survives_rebuild(session):
    """Mixed-material jobs are human choices: a qty_src=human lap row
    survives the B&B rebuild with its quantity intact."""
    lines = [l for l in _get_lines(session) if l.get("name") != LAP_KEY["name"]]
    lines.append({**LAP_KEY, "unit": "PCS", "qty": 12, "mat": 30.99, "lab": 0.0,
                  "qty_src": "human"})
    _put_lines(session, lines)
    r = session.post(f"{API}/estimates/{CASILE_EST}/hover-lp-run",
                     json=REBUILD_PAYLOAD, timeout=90)
    assert r.status_code == 200, r.text
    after = _get_lines(session)
    lap = next(l for l in after if l.get("name") == LAP_KEY["name"])
    assert lap["qty"] == 12 and lap.get("qty_src") == "human"
    # restore the founding state: machine residue → rebuild zeroes it
    lines = [l for l in _get_lines(session) if l.get("name") != LAP_KEY["name"]]
    lines.append({**LAP_KEY, "unit": "PCS", "qty": 251, "mat": 30.99, "lab": 0.0})
    _put_lines(session, lines)
    session.post(f"{API}/estimates/{CASILE_EST}/hover-lp-run",
                 json=REBUILD_PAYLOAD, timeout=90)
    final = next(l for l in _get_lines(session) if l.get("name") == LAP_KEY["name"])
    assert final["qty"] == 0


def test_restore_flow_wires_profile_and_zero_list():
    """JSX pins: restore sends the estimate's mapped profile; the apply
    merge zeroes zero_family_lines unless qty_src is human."""
    src = (BACKEND.parent / "frontend" / "src" / "components" / "estimate"
           / "HoverImportButton.jsx").read_text()
    assert "profile: est?.default_siding_profile" in src
    assert "zero_family_lines" in src
    assert 'qty_src !== "human"' in src
    ue = (BACKEND.parent / "frontend" / "src" / "lib" / "useEstimate.js").read_text()
    assert 'qty_src: "human"' in ue


def test_qty_src_and_raw_qty_survive_the_editor_round_trip():
    """JSX pins (found 2026-07-24, same defect family): the editor's
    load-merge and save payload used to STRIP raw_qty + qty_src — the
    human-survival machinery was dead through the UI and any full save
    wiped raw_qty (waste recompute basis) server-side."""
    ue = (BACKEND.parent / "frontend" / "src" / "lib" / "useEstimate.js").read_text()
    assert "raw_qty: saved && saved.raw_qty != null" in ue     # load-merge keeps
    assert "qty_src: (saved && saved.qty_src) || null" in ue   # load-merge keeps
    assert "raw_qty: l.raw_qty ?? null" in ue                  # save payload sends
    assert "qty_src: l.qty_src || null" in ue                  # save payload sends
    assert '(l.qty || 0) > 0 || l.qty_src === "human"' in ue   # human zero survives save


def test_waste_display_never_added_back_into_base():
    """calc.js pin: waste is IN the qty — wasteAdd is display only. The
    dormant `wasted = subMat + wasteAdd` add-on would have double-counted
    waste dollars the moment raw_qty flowed through the editor."""
    calc = (BACKEND.parent / "frontend" / "src" / "lib" / "calc.js").read_text()
    assert "const wasted = subMat;" in calc
    assert "subMat + wasteAdd" not in calc
