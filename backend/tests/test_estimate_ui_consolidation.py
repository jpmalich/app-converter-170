"""ESTIMATE CONSOLIDATION pins (ruled 2026-07-24).

(a) ONE COLOR HOME — colors live on the Job Info MATERIAL COLORS block;
    the AI Material List ExpertFinish picker row is REMOVED. Job Info
    fields map to LP component groups (siding_color→siding,
    soffit_fascia_color→soffit_fascia, accessories_color→opening_trim+isc,
    outside_corner_color→osc) and mirror to est.lp_colors so every
    existing consumer (preview, freeze/QR, print) reads unchanged.
(b) AI MATERIAL LIST COLLAPSES — the duplicate item/qty table is removed;
    notes/flags strips stay; provenance chips render on group tab lines.
(c) SAFETY — nothing consumed the removed table: print composes from the
    server package (buildLpMaterialListHtml(pkg)), freeze/QR posts
    est.lp_colors server-side, CSV/accept are backend-composed, and the
    customer quote is pinned to never read lpPkg (one_money_surface).
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
PANEL = (FE / "components" / "estimate" / "LpMaterialListPanel.jsx").read_text()
EDITOR = (FE / "pages" / "EstimateEditor.jsx").read_text()
ACCORDION = (FE / "components" / "estimate" / "SectionAccordion.jsx").read_text()
JOBINFO = (FE / "components" / "estimate" / "JobInfoPanel.jsx").read_text()

CASILE_EST = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


class TestOneColorHome:
    def test_picker_row_removed_from_panel(self):
        assert "lp-color-all" not in PANEL
        assert "ColorSelect" not in PANEL
        assert "ExpertFinish picker" in PANEL or "picker" in PANEL  # ruling comment stays

    def test_job_info_mapping_and_mirror(self):
        assert "export function jobInfoLpColors" in PANEL
        assert "m.siding = est.siding_color" in PANEL
        assert "m.soffit_fascia = est.soffit_fascia_color" in PANEL
        assert "m.opening_trim = est.accessories_color" in PANEL
        assert "m.isc = est.accessories_color" in PANEL
        assert "m.osc = est.outside_corner_color" in PANEL
        assert "update({ lp_colors: jobInfoColors })" in PANEL

    def test_job_info_block_is_the_home(self):
        # the MATERIAL COLORS block still carries the LP pickers
        for tid in ("color-siding", "color-accessories",
                    "color-outside-corner", "color-soffit-fascia"):
            assert f'data-testid="{tid}"' in JOBINFO

    def test_preview_api_honors_group_colors(self, session):
        r = session.post(f"{API}/estimates/{CASILE_EST}/lp-package/preview",
                         json={"colors": {"siding": "Snowscape White"}}, timeout=90)
        assert r.status_code == 200, r.text
        assert r.json()["summary"]["group_colors"].get("siding") == "Snowscape White"


class TestListCollapses:
    def test_item_qty_table_removed(self):
        assert "lp-line-" not in PANEL          # per-row testids gone
        assert "lp-material-list-edit-toggle" not in PANEL
        assert "lp-material-list-readonly-hint" not in PANEL
        assert "Substitute with" not in PANEL

    def test_notes_flags_strips_kept(self):
        for tid in ("lp-hover-mapping-flags", "lp-material-unpriced-note",
                    "lp-default-profile-picker", "lp-compare-toggle",
                    "lp-source-chip", "lp-geometry-basis"):
            assert tid in PANEL, tid
        assert "lp-field-verify-card" in PANEL
        assert "<FieldVerifyCard" in PANEL

    def test_provenance_chips_on_group_tab_lines(self):
        assert "prov-chip-" in ACCORDION
        assert "prov-human-" in ACCORDION
        assert "provenance?.[l.name]" in ACCORDION
        assert "lpProvenance" in EDITOR
        assert 'provenance={activeTab === "lp_smart" ? lpProvenance : null}' in EDITOR


class TestNothingConsumedTheRemovedTable:
    """Safety pins: every downstream artifact composes from SERVER data,
    never the removed JSX table."""

    def test_print_composes_from_server_package(self):
        assert "buildLpMaterialListHtml({ pkg: lpPkg" in EDITOR

    def test_freeze_qr_posts_estimate_colors(self):
        assert "lp-material-list/freeze" in EDITOR
        assert "colors: est.lp_colors" in EDITOR

    def test_share_page_reads_frozen_snapshot(self):
        share = (FE / "pages" / "MaterialListShare.jsx").read_text()
        assert "LpMaterialListPanel" not in share  # never the panel DOM

    def test_quote_never_reads_lp_pkg(self):
        # ONE MONEY SURFACE pin lives in test_one_money_surface.py;
        # re-asserted here because the ruling names this consumer.
        import re
        m = re.search(r"const quoteEstimate = useMemo\(\(\) => \{(.*?)\}, \[", EDITOR, re.S)
        assert m and "lpPkg" not in m.group(1)
