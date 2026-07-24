"""CAPTURE-GUIDANCE pins (approved 2026-07-24, extraction-variance
report follow-through). The photo checklist carries the three lines
covering the fresh red-house run's dominant miss causes:
  1. full-wall reference on ONE plane (main wall, never a dormer face)
  2. square-on frames per wall
  3. pin windows — including dormer windows
Content is contractor-facing copy; these pins keep it from silently
regressing out of the checklist."""
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" /
       "components" / "estimate" / "AIMeasureButton.jsx").read_text()


def test_ref_plane_tip_pinned():
    assert 'data-testid="ai-measure-onboarding-tip-ref-plane"' in SRC
    assert "Wall refs live on the MAIN wall plane" in SRC
    assert "never across a" in SRC and "dormer, pop-up, or porch face" in SRC


def test_square_on_tip_pinned():
    assert "All 4 elevations, square-on" in SRC
    assert "shoot the wall flat, not from a corner angle" in SRC


def test_pin_windows_tip_pinned():
    assert 'data-testid="ai-measure-onboarding-tip-pin-windows"' in SRC
    assert "especially any window up in the roof" in SRC
    assert "on the correct face (dormer vs. wall)" in SRC
