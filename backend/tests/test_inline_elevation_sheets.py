"""INLINE ELEVATION SHEETS pins (ruled 2026-07-24).

(1) NEW SECTION on the estimate page: ELEVATION SHEETS mounts
    automatically once a completed AI run exists — NOT gated on Apply
    (sheets render from the run regardless). EL-1..4 as tabs, the SAME
    SheetSvg the sheet pages use (identical by construction), read-only,
    sized to the page, with "Print all 4 sheets" + an open-full-page
    link per sheet. No run yet → the NAMED empty state, never a dead
    section.
(2) THE MODAL BECOMES SECONDARY: sheet/source links inside the AI
    Measure modal (FieldVerifyCard) open in NEW TABS — the modal never
    unmounts; the five-click resume-and-scroll path is RETIRED.
(3) One behavior everywhere — fresh estimates, fixtures, photo path
    generally (the panel probes the sheet endpoint; the endpoint's
    no-run 404 is the mount condition's other half).
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

FE = BACKEND.parent / "frontend" / "src"
PANEL = (FE / "components" / "estimate" / "ElevationSheetsPanel.jsx").read_text()
EDITOR = (FE / "pages" / "EstimateEditor.jsx").read_text()
FVC = (FE / "components" / "estimate" / "FieldVerifyCard.jsx").read_text()

LETRICK = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"   # photo path — completed AI run
CASILE = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"    # hover path — NO AI run


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return s


class TestInlinePanelPins:
    def test_editor_mounts_the_section(self):
        assert "ElevationSheetsPanel" in EDITOR
        assert "<ElevationSheetsPanel est={est} />" in EDITOR

    def test_mount_condition_not_gated_on_apply(self):
        # the panel probes the sheet endpoint per wall — never reads any
        # Apply/derive state; renders from the run regardless
        assert "elevation-sheet/${w}" in PANEL
        assert "NOT gated on" in PANEL
        for token in ("lpPkg", "applied", "lp_derived"):
            assert token not in PANEL, token

    def test_named_empty_state_never_a_dead_section(self):
        assert 'data-testid="elevation-sheets-empty"' in PANEL
        assert "no completed AI measurement run yet" in PANEL
        assert "no Apply needed" in PANEL

    def test_tabs_print_all_and_open_full_page(self):
        assert "elevation-sheet-tab-${w}" in PANEL
        assert 'data-testid="elevation-sheets-print-all"' in PANEL
        assert "Print all 4 sheets" in PANEL
        assert "elevation-sheets-open-full-${active}" in PANEL
        # same renderer as the sheet pages — identical by construction
        assert 'import { SheetSvg } from "@/pages/ElevationSheet"' in PANEL
        # new tabs for the full-page/print flows
        assert PANEL.count('target="_blank"') >= 2


class TestModalBecomesSecondary:
    def test_modal_links_open_new_tabs(self):
        # every sheet/source link is a plain anchor with target=_blank —
        # the AI Measure modal never unmounts (resume-and-scroll RETIRED)
        assert "<Link" not in FVC
        assert 'from "react-router-dom"' not in FVC
        assert FVC.count('target="_blank"') >= 3
        for tid in ("field-verify-source-link",
                    "field-verify-elevation-sheet-link-",
                    "field-verify-elevation-sheets-print-all"):
            assert tid in FVC, tid
        assert "the modal stays put" in FVC


class TestMountConditionLive:
    def test_photo_estimate_serves_sheets(self, session):
        r = session.get(f"{API}/estimates/{LETRICK}/elevation-sheet/front", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["sheet"] == "front" and d["sheet_code"] == "EL-1"

    def test_no_run_estimate_gets_named_404(self, session):
        r = session.post(f"{API}/estimates",
                         json={"customer_name": "zz inline sheets probe"}, timeout=30)
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        try:
            r = session.get(f"{API}/estimates/{eid}/elevation-sheet/front", timeout=60)
            assert r.status_code == 404, r.text
            assert "No completed AI measure run" in r.json()["detail"]
        finally:
            session.delete(f"{API}/estimates/{eid}", timeout=15)

    def test_walls_less_run_still_a_named_404(self, session):
        # Casile is hover-path: its archived photo run carries no walls —
        # the endpoint 404s by name and the panel shows the empty state
        r = session.get(f"{API}/estimates/{CASILE}/elevation-sheet/front", timeout=60)
        assert r.status_code == 404, r.text
        assert "wall" in r.json()["detail"].lower()


class TestRunCompletedRefresh:
    """EST-986945 defect (ruled 2026-07-26): the panel probed once at
    mount, so a run completing while the page was open left the empty
    state stuck until a manual reload. NOT a schema mismatch — the
    endpoint served the new-format run fine. The panel now re-probes on
    the ai-run-completed window event AIMeasureButton dispatches."""

    def test_panel_listens_for_run_completed(self):
        assert 'window.addEventListener("ai-run-completed"' in PANEL
        assert 'window.removeEventListener("ai-run-completed"' in PANEL
        # scoped to this estimate — a run on another tab's estimate is ignored
        assert "e.detail.estimateId !== est.id" in PANEL

    def test_measure_button_dispatches_on_run_success(self):
        aim = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
        assert 'new CustomEvent("ai-run-completed", { detail: { estimateId } })' in aim
