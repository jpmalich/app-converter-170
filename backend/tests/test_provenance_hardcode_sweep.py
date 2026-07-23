"""Provenance-hardcode rule + elevation-sheet generality/collapse pins
(ruled 2026-07-20).

THE RULE, pinned verbatim: no provenance, confirmation, or ratification
text may ever be hardcoded — every such string derives from the
ratification/provenance record it describes, or it does not render.

Defect that created the rule (integrity register, 2026-07-20): the
generic chase corner-read fallback in elevation_sheets.py hardcoded
"immediately left of D1 — human photo-confirmed (ruled 2026-07-19)" —
Letrick's ratification — onto ANY estimate's chase; doug jones' back
sheet drew a human confirmation that never occurred.

Also pinned here (same ruling):
  • collision-callout collapse: >3 flagged pairs → ONE summary block;
    the collapse never hides a flag, only stacks it — API data stays
    FULL, every affected schedule row keeps its own flag.
  • elevation-sheet entry point on Field Verify: EL-1..EL-4 links,
    photo estimates only, one link per wall the run carries; named
    empty-state chip when the substrate can't render — never a dead link.
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
DOUG_EST = "db82ec7a-3177-406d-a602-927255e9e10e"      # doug jones EST-510771
HAUGH_EST = "48231310-3872-4d4e-b657-35ade10c1cb8"     # 261 haugh photo EST-067615

ROOT = Path(__file__).resolve().parent.parent.parent
BINDER = (ROOT / "backend" / "routes" / "elevation_sheets.py").read_text()
SHEET_JSX = (ROOT / "frontend" / "src" / "pages" / "ElevationSheet.jsx").read_text()
FVC_JSX = (ROOT / "frontend" / "src" / "components" / "estimate" / "FieldVerifyCard.jsx").read_text()

GENERIC_NOTES = {
    # PIN AMENDED BY RULING 2026-07-22 (confirmation-weighted geometry):
    # the fr-path vocabulary now names the READ TIER — "confirmed" refers
    # to multi-sighting corner reads, never to human confirmation. The
    # ratified human wording remains dr-path-only (record-guarded).
    "position from confirmed run corner reads — untaped",
    "position anchored on confirmed corner read — untaped",
    "no confirmed corner read — glyph not drawn",
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


# ---------- source pins: the hardcoded-provenance rule ----------

def test_no_hardcoded_human_confirmation_in_binder():
    """The leak string class is gone from the binder — the only human-
    confirmation wording left ("CONFIRMED (human, photo)") sits on the
    dr / dr_b paths, which require the ratify record to exist."""
    assert "human photo-confirmed" not in BINDER
    assert any(n in BINDER for n in GENERIC_NOTES)


def test_dr_guard_still_carries_the_ratified_wording():
    """The ratified paths are record-guarded, not deleted: both fire only
    when _door_relative_chase_center returns a record."""
    assert BINDER.count('CONFIRMED (human, photo)') >= 2
    assert "_door_relative_chase_center" in BINDER


def test_frontend_sheet_derives_taped_stamp_not_hardcoded_date():
    assert "ratified: sealed key amendment 2026-07-19" not in SHEET_JSX
    assert "chase.taped_stamp" in SHEET_JSX
    assert "human photo-confirmed" not in SHEET_JSX


def test_binder_sends_taped_stamp_from_the_key_record():
    assert '"taped_stamp": cd["taped"]' in BINDER


# ---------- functional: generic path renders honest provenance ----------

def test_doug_jones_back_chase_claims_no_human_confirmation(session):
    r = session.get(f"{API}/estimates/{DOUG_EST}/elevation-sheet/back", timeout=30)
    assert r.status_code == 200, r.text
    assert "human photo-confirmed" not in r.text
    ch = r.json()["chase"]
    if ch is not None and ch.get("position_tag") != "CONFIRMED (human, photo)":
        # no ratify record on this estimate → an honest tier-vocabulary note
        assert ch.get("position_note") in GENERIC_NOTES
        assert "D1" not in str(ch.get("position_note"))
        assert "human" not in str(ch.get("position_note"))


def test_doug_jones_sheets_are_run_basis_no_sealed_key(session):
    """Generality pin (ruled PASS 2026-07-20): non-Letrick photo estimates
    render every wall from run data, labeled — no TAPED wall tags."""
    for which in ("front", "left", "back", "right"):
        r = session.get(f"{API}/estimates/{DOUG_EST}/elevation-sheet/{which}", timeout=30)
        assert r.status_code == 200, f"{which}: {r.text}"
        s = r.json()
        w = s["wall"]
        assert w["width_tag"] != "TAPED"
        assert w["height_tag"] != "TAPED-DERIVED"
        assert w["segments"] is None
        assert "AI run" in s["geometry_basis"]["walls"]
        assert "sealed key" not in s["geometry_basis"]["walls"]


# ---------- collapse: never hides a flag, only stacks it ----------

def test_haugh_front_api_data_stays_full_under_collapse(session):
    """The collapse is VIEW-level only: the route keeps returning every
    flagged pair, and every affected opening stays collision-flagged."""
    r = session.get(f"{API}/estimates/{HAUGH_EST}/elevation-sheet/front", timeout=30)
    assert r.status_code == 200, r.text
    s = r.json()
    assert len(s["collisions"]) > 3          # the flooding fixture
    flagged_tags = {e for c in s["collisions"] if not c["suppressed"] for e in c["elements"]}
    for o in s["openings"]:
        if o["tag"] in flagged_tags:
            assert o["collision"] is True, f"{o['tag']} lost its flag"


def test_sheet_jsx_collapse_wiring():
    assert "elevation-collision-collapse" in SHEET_JSX
    assert "flaggedCols.length > 3" in SHEET_JSX
    # suppression callouts always render in full
    assert "colCollapsed ? suppressedCols : collisions" in SHEET_JSX
    # per-row schedule flags + legend
    assert "elevation-schedule-collision-" in SHEET_JSX
    assert "elevation-schedule-collision-legend" in SHEET_JSX
    # per-opening on-drawing flag and the banner survive the collapse
    assert "POSITION UNVERIFIED" in SHEET_JSX
    assert "elevation-collision-banner" in SHEET_JSX


# ---------- entry point: honest links, named empty state ----------

def test_field_verify_elevation_sheet_chooser_wiring():
    assert 'data-testid={`field-verify-elevation-sheet-link-${w}`}' in FVC_JSX
    assert 'data-testid="field-verify-elevation-sheets-empty"' in FVC_JSX
    # photo-door gate + per-wall link derivation (never a dead link)
    assert 'door === "photo"' in FVC_JSX
    assert 'aiRun?.status === "done"' in FVC_JSX
    assert "raw_ai?.walls" in FVC_JSX
    # source-view door untouched
    assert 'data-testid="field-verify-source-link"' in FVC_JSX
