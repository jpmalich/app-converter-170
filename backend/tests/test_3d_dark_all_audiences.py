"""3D DARK FOR ALL AUDIENCES + FIELD VERIFY REHOMING (Howard, approved
2026-07-20). Asserted-absence pins, same pattern as the audience wording
split:

1. One flag governs: RENDER_3D_ENABLED = false in featureFlags.js.
2. Every HouseModel3D mount (LP panel, AI Measure, Blueprint) is guarded
   by the flag; AcceptHouse3D (customer) is guarded; the quote (email +
   modal) carries NO picture block at all (removed, not flagged — ruled
   NONE). DEMO mode inherits the contractor mounts, so it is covered by
   the same guards.
3. No visible "3D" toggle while dark: both tab labels read "Field
   Verify" behind the flag.
4. Tape workflow NEVER dark: FieldVerifyCard hosts TapeCheckPanel + the
   taped-dims editor (identical write paths) and is mounted in all three
   hosts unconditionally.
5. Source-blueprints entry rides the Field Verify card (blueprint-path
   estimates only — link renders only when a run, live or archived,
   exists).
6. Code preserved for re-entry: HouseModel3D / AcceptHouse3D files
   intact and still exporting.
"""
import re
from pathlib import Path

FE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"

FLAGS = (FE / "lib" / "featureFlags.js").read_text()
FVC = (FE / "components" / "estimate" / "FieldVerifyCard.jsx").read_text()
LP = (FE / "components" / "estimate" / "LpMaterialListPanel.jsx").read_text()
AIM = (FE / "components" / "estimate" / "AIMeasureButton.jsx").read_text()
BPM = (FE / "components" / "estimate" / "BlueprintMeasureButton.jsx").read_text()
ACCEPT = (FE / "pages" / "AcceptPage.jsx").read_text()
QUOTE_JS = (FE / "lib" / "emailQuote.js").read_text()
QUOTE_MODAL = (FE / "components" / "QuoteModal.jsx").read_text()


def test_pin1_single_flag_off():
    assert "export const RENDER_3D_ENABLED = false;" in FLAGS


def test_pin2_every_house3d_mount_flag_guarded():
    for name, src in (("LpMaterialListPanel", LP), ("AIMeasureButton", AIM),
                      ("BlueprintMeasureButton", BPM)):
        assert "<HouseModel3D" in src, f"{name}: 3D code must be PRESERVED"
        for m in re.finditer(r"<HouseModel3D", src):
            window = src[max(0, m.start() - 400):m.start()]
            assert "RENDER_3D_ENABLED" in window, (
                f"{name}: found a HouseModel3D mount not guarded by the flag")


def test_pin2b_customer_accept_view_guarded_and_quote_pictureless():
    assert "RENDER_3D_ENABLED && d.house3d ?" in ACCEPT
    assert "<AcceptHouse3D" in ACCEPT  # preserved for re-entry
    # quote: NO picture — removed outright per the NONE ruling
    assert "model3d_png_url" not in QUOTE_JS
    assert "model3dBlock" not in QUOTE_JS
    assert "model3d_png_url" not in QUOTE_MODAL
    assert "quote-3d-model-block" not in QUOTE_MODAL


def test_pin3_no_visible_3d_toggle_while_dark():
    for src in (AIM, BPM):
        assert '{RENDER_3D_ENABLED ? "3D Model" : "Field Verify"}' in src


def test_pin4_tape_workflow_never_dark():
    assert "TapeCheckPanel" in FVC
    assert "/lp-appendage-dims" in FVC  # identical dims write path
    assert "DimEditRow" in FVC          # re-mounted, not rebuilt
    for name, src in (("LpMaterialListPanel", LP), ("AIMeasureButton", AIM),
                      ("BlueprintMeasureButton", BPM)):
        assert "<FieldVerifyCard" in src, f"{name}: Field Verify card missing"
        for m in re.finditer(r"<FieldVerifyCard", src):
            window = src[max(0, m.start() - 300):m.start()]
            assert "RENDER_3D_ENABLED &&" not in window.split("<FieldVerifyCard")[-1], (
                f"{name}: FieldVerifyCard must NOT sit behind the 3D flag")


def test_pin5_source_blueprints_entry_rides_the_card():
    assert 'data-testid="field-verify-source-blueprints-link"' in FVC
    assert "/measure/ai-blueprint/latest-for-estimate/" in FVC  # bp-path only
    assert "source-sheets" in FVC
    # the entry lives on the card, nowhere else on app surfaces
    assert "source-sheets" not in (FE / "components" / "estimate" / "JobInfoPanel.jsx").read_text()


def test_pin6_no_route_renders_3d():
    app = (FE / "App.js").read_text()
    assert "House3D" not in app and "house3d" not in app
