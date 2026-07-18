"""GEOMETRY-FIT GATE pins (ruled 2026-07-18).

Standing rule: no low-fit render reaches a customer surface unlabeled.
Fit confidence derives from the renderer's own self-check triggers;
contractor surfaces keep the render + diagnostic banner as-is."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from routes.public import _house3d_fit_low  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]


def _walls(*gable_labels):
    labels = ("front", "left", "back", "right")
    return {"walls": [
        {"label": l, "gable_triangle_height_ft": 5.0 if l in gable_labels else 0}
        for l in labels
    ]}


def test_adjacent_gables_are_low_fit():
    # 261 Haugh canonical: gables on left+back — no single ridge serves both
    assert _house3d_fit_low(_walls("left", "back")) is True
    assert _house3d_fit_low(_walls("front", "left")) is True


def test_opposite_gables_and_no_gables_fit_ok():
    assert _house3d_fit_low(_walls("left", "right")) is False
    assert _house3d_fit_low(_walls("front", "back")) is False
    assert _house3d_fit_low(_walls("left")) is False
    assert _house3d_fit_low(_walls()) is False


def test_low_roof_confidence_is_low_fit():
    m = _walls("left", "right")
    m["roof_type_confidence"] = 0.3
    assert _house3d_fit_low(m) is True
    m["roof_type_confidence"] = 0.9
    assert _house3d_fit_low(m) is False


def test_accept_page_labels_low_fit():
    """Customer Accept page: low-fit 3D renders ONLY behind the labeled
    simplified-representation state."""
    jsx = (_ROOT / "frontend/src/pages/AcceptPage.jsx").read_text()
    assert 'data-testid="accept-3d-fit-label"' in jsx
    assert "d.house3d.fit_low" in jsx
    assert 't("accept.model3d.fitNote")' in jsx


def test_quote_email_and_modal_label_low_fit():
    js = (_ROOT / "frontend/src/lib/emailQuote.js").read_text()
    assert "estimate.model3d_fit_low" in js
    assert 't("email.model3dFitNote")' in js
    modal = (_ROOT / "frontend/src/components/QuoteModal.jsx").read_text()
    assert 'data-testid="quote-3d-fit-note"' in modal
    assert "Simplified representation — not to scale/shape." in modal


def test_asserted_wording_both_languages():
    d = (_ROOT / "frontend/src/lib/dictionaries.js").read_text()
    assert "Simplified representation — not to scale/shape." in d
    assert "Representación simplificada — no a escala ni forma real." in d
    for key in ("accept.model3d.fitNote", "email.model3dFitNote",
                "accept.model3d.simplifiedTitle", "email.model3dSimplifiedTitle"):
        assert d.count(f'"{key}"') == 2, f"{key} missing EN or ES entry"


def test_fit_low_rides_the_snapshot_end_to_end():
    """Capture (renderer banner triggers) → save endpoint → estimate doc."""
    h3d = (_ROOT / "frontend/src/components/estimate/HouseModel3D.jsx").read_text()
    assert "fit_low: bannerMessages.length > 0" in h3d
    aim = (_ROOT / "frontend/src/components/estimate/AIMeasureButton.jsx").read_text()
    assert "fit_low: !!meta?.fit_low" in aim
    est = (_ROOT / "backend/routes/estimates.py").read_text()
    assert '"model3d_fit_low": bool(body.fit_low)' in est
    pub = (_ROOT / "backend/routes/public.py").read_text()
    assert '"fit_low": _house3d_fit_low(raw)' in pub


def test_contractor_surface_keeps_diagnostic_render():
    """Contractor 3D keeps the render + banner (diagnostic there) — the
    gate suppresses/labels CUSTOMER surfaces only."""
    h3d = (_ROOT / "frontend/src/components/estimate/HouseModel3D.jsx").read_text()
    assert "ai-measure-3d-ridge-mismatch-banner" in h3d


# ── smashed-walls defect (ruled 2026-07-18, rides on the fit gate) ───
def test_unplaceable_geometry_omitted_with_count_never_at_origin():
    """Geometry the vocabulary cannot place is NEVER rendered at default/
    overlapping coordinates — omitted with a count in the schematic
    label. Honest absence replaces garbage placement."""
    h3d = (_ROOT / "frontend/src/components/estimate/HouseModel3D.jsx").read_text()
    assert "not drawn — house exceeds model vocabulary" in h3d
    assert "unplaced.count += 1" in h3d
    # the old fall-through that drew unknown facades at (0,0,0) is dead
    assert "default: break;" not in h3d.split("Position each wall around the footprint")[1].split("userData.facadeId")[0]


def test_no_two_walls_render_at_coincident_coordinates():
    """Pin (asserted wording): post-build sweep removes + counts any
    wall/appendage landing on an occupied frame."""
    h3d = (_ROOT / "frontend/src/components/estimate/HouseModel3D.jsx").read_text()
    assert "no two walls render at coincident coordinates" in h3d
    assert "seenFrames" in h3d
    # unplaced-count warning feeds bannerMessages → rides fit_low to
    # customer surfaces via the snapshot gate
    assert "fit_low: bannerMessages.length > 0" in h3d

# ── smashed-walls WIDENED (ruled 2026-07-18 round 2) ─────────────────
def test_interpenetrating_opening_rects_are_omitted_and_counted():
    """The eye catches overlap, not just exact coincidence: opening rects
    that interpenetrate beyond OPENING_OVERLAP_FRAC of the smaller rect
    (photo duplicates flattened onto one wall plane) are omitted +
    counted per facade, and the count rides the warnings banner."""
    h3d = (_ROOT / "frontend/src/components/estimate/HouseModel3D.jsx").read_text()
    assert "OPENING_OVERLAP_FRAC" in h3d
    assert "omittedOpenings" in h3d
    assert "overlapping placements exceed the model vocabulary" in h3d
    # priority: reconciler-verified (along_wall_ft) beats bbox-only
    assert "verified: alongFt != null" in h3d


def test_opening_omission_is_render_only_never_touches_takeoff():
    """The sweep lives in autoSpace (3D placement only) — measurements,
    lines, and the openings schedule are untouched."""
    h3d = (_ROOT / "frontend/src/components/estimate/HouseModel3D.jsx").read_text()
    # sweep is inside autoSpace, whose output only feeds facade.openings
    seg = h3d.split("const prio")[1].split("return { placed, omitted }")[0]
    assert "OPENING_OVERLAP_FRAC" in seg
    # no writes to preview.measurements / lines anywhere in the sweep
    assert "measurements" not in seg
    assert ".lines" not in seg
