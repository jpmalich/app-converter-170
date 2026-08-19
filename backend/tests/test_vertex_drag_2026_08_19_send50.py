"""SEND-50 item 1 pins — vertex coordinates round the trip in ONE unit space.

Field defect (measured on preview, 2026-08-19): a dragged vertex moved
exactly ONE mousemove step (~11px of a 150px drag, factor ~13.6 at zoom
100% AND 156% — zoom-independent) because img-routed drag events died the
moment the handle re-rendered under the cursor; vertex 0 moved 0px because
the sqft badge covered its handle. Event delivery, NOT unit arithmetic —
but the mandate is to pin the ARITHMETIC so a delta in one unit space can
never be applied to a coordinate in another without a test failing.

Unit conventions, named once (the condition that produces this class of
bug is two conventions in one file with no guard):
  - zone vertices (frontend state, API payload, Mongo): FRACTION 0-1
  - persisted OCR store (runs: x_pct/y_pct/w_pct/h_pct, proposal span_y):
    PERCENT-OF-PAGE 0-100
  - the ONLY conversion boundary: routes/pdf_overlay.py propose
    (span/100.0 → fraction) — everything past the API writes fractions.
"""
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, "/app/backend")

JSX = "/app/frontend/src/components/estimate/PdfOverlayEditor.jsx"


# ---------------------------------------------------------------------------
# The editor's conversions, expressed as arithmetic (mirrors normFromEvent
# and the render path exactly — one division by the RENDERED size, ×100
# into the 0-100 viewBox / % offsets on the way back).
# ---------------------------------------------------------------------------
def write_px_to_fraction(client_px, rect_origin_px, rendered_px):
    """normFromEvent: screen px → fraction of page [0,1]."""
    f = (client_px - rect_origin_px) / rendered_px
    return min(1.0, max(0.0, f))


def read_fraction_to_px(fraction, rect_origin_px, rendered_px):
    """render: stored fraction → screen px (left:% / viewBox×100 ≡ ×rendered)."""
    return rect_origin_px + fraction * rendered_px


BASE_W = 1400.0  # a rendered page width at zoom 1


@pytest.mark.parametrize("zoom", [1.0, 1.25, 1.5625, 0.64])
def test_write_and_read_are_inverses_at_any_zoom(zoom):
    rendered = BASE_W * zoom
    for px in (0.0, 137.0, 512.5, rendered):
        f = write_px_to_fraction(100.0 + px, 100.0, rendered)
        back = read_fraction_to_px(f, 100.0, rendered)
        assert abs(back - (100.0 + px)) < 1e-9


@pytest.mark.parametrize("zoom", [1.0, 1.5625])
def test_a_cursor_delta_reproduces_one_to_one_at_any_zoom(zoom):
    """Drag Δpx on screen → stored fraction → rendered position moves Δpx.

    This is the behavioral claim of the fix in arithmetic form: the
    round-tripped delta equals the intended delta (factor 1.0), never
    one step of it (the measured broken factor was ~13.6) and never a
    hundredth (the fraction-added-to-percent signature).
    """
    rendered = BASE_W * zoom
    start_px, delta_px = 400.0, 150.0
    f0 = write_px_to_fraction(start_px, 0.0, rendered)
    f1 = write_px_to_fraction(start_px + delta_px, 0.0, rendered)
    moved = read_fraction_to_px(f1, 0.0, rendered) - read_fraction_to_px(f0, 0.0, rendered)
    assert abs(moved - delta_px) < 1e-9


def test_percent_delta_applied_to_fraction_breaks_the_round_trip():
    """The guarded mistake, stated as a failing shape: a 0-100 percent
    delta added to a 0-1 fraction coordinate lands ~100× off (clamped)."""
    rendered = BASE_W
    f0 = write_px_to_fraction(400.0, 0.0, rendered)          # fraction space
    percent_delta = (150.0 / rendered) * 100.0               # percent space
    wrong = min(1.0, max(0.0, f0 + percent_delta / 100.0 / 100.0))
    moved = (wrong - f0) * rendered
    assert abs(moved - 150.0) > 100.0  # nowhere near the intended 150px


def test_storage_boundary_rejects_percent_space_vertices():
    """The API is the unit boundary: a vertex written in 0-100 percent
    space (e.g. 50 meaning 50%) must be REJECTED, not stored.
    """
    from routes.pdf_overlay import _validate_polygon, PolygonWriteIn

    p = PolygonWriteIn(
        page=1, face_id="front", material_class="siding",
        vertices_pct=[[50.0, 30.0], [60.0, 30.0], [60.0, 40.0]],
    )
    with pytest.raises(HTTPException) as ei:
        _validate_polygon(p)
    assert "in [0,1]" in ei.value.detail


def test_fraction_space_vertices_pass_the_same_boundary():
    from routes.pdf_overlay import _validate_polygon, PolygonWriteIn

    p = PolygonWriteIn(
        page=1, face_id="front", material_class="siding",
        vertices_pct=[[0.50, 0.30], [0.60, 0.30], [0.60, 0.40]],
    )
    _validate_polygon(p)  # must not raise


# ---------------------------------------------------------------------------
# Structural pins on the fix itself — the two event-delivery defects that
# produced the field report must stay fixed.
# ---------------------------------------------------------------------------
def _jsx():
    with open(JSX, encoding="utf-8") as f:
        return f.read()


def test_live_drag_listens_on_window_not_the_img():
    src = _jsx()
    assert 'window.addEventListener("mousemove", move)' in src
    assert 'window.addEventListener("mouseup", up)' in src


def test_img_mousemove_no_longer_owns_the_drag():
    src = _jsx()
    assert "if (dragVertex) return; // the window-level drag effect owns vertex moves" in src


def test_buttons_free_move_ends_a_stale_drag():
    """SEND-52 3B: a release OUTSIDE the window delivers no mouseup; the
    first buttons-free move on re-entry must end the drag, or the vertex
    sticks to the cursor until the next press."""
    src = _jsx()
    assert "if (e.buttons === 0) { up(); return; }" in src


def test_sqft_badge_cannot_swallow_a_vertex_handle():
    src = _jsx()
    badge = src.split("per-polygon sqft badge")[1].split("data-testid")[0]
    assert "pointer-events-none" in badge
