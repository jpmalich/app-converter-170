"""Unit tests for the HOVER window-style guessing heuristic.

HOVER PDF reports give us the rough opening dimensions (W × H) per window
but NEVER tell us if the window is double-hung, slider, casement, or
picture. `_guess_vero_product_type` picks a sensible default from those
two numbers. Contractors override per-opening on the preview modal.

These tests pin the boundary cases so future edits to the rules don't
silently regress the bias toward DH that Howard wants.
"""
import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "vinyl_estimator")

import pytest

from routes.hover import _guess_vero_product_type as g


@pytest.mark.parametrize("w,h,expected", [
    # Casement = TRULY small (kitchen above-sink, bath transom).
    (24, 36, "Vero 1-Lite Casement"),
    (22, 30, "Vero 1-Lite Casement"),
    (28, 36, "Vero 1-Lite Casement"),
    # Classic DH proportions (taller than wide, < 40")
    (29, 51, "Vero Double Hung"),
    (30, 60, "Vero Double Hung"),
    (24, 47, "Vero Double Hung"),
    (31, 65, "Vero Double Hung"),
    # Tall narrow DH-ish (h > w) — even if w >= 40
    (40, 60, "Vero Double Hung"),
    (49, 62, "Vero Double Hung"),
    # 2-Lite slider: wider than tall, 40"-59"
    (48, 36, "Vero 2-Lite Slider"),
    (40, 30, "Vero 2-Lite Slider"),
    (50, 40, "Vero 2-Lite Slider"),
    # 3-Lite slider: very wide, wider than tall
    (60, 36, "Vero 3-Lite Slider"),
    (72, 48, "Vero 3-Lite Slider"),
    (66, 49, "Vero 3-Lite Slider"),
    # Picture: large + square fixed glass
    (60, 60, "Vero Picture"),
    (72, 72, "Vero Picture"),
    (50, 50, "Vero Picture"),
    # Degenerates
    (0, 0, "Vero Double Hung"),
    (None, 50, "Vero Double Hung"),  # type: ignore
])
def test_guess_vero_product_type(w, h, expected):
    assert g(w, h) == expected


def test_guess_handles_string_input():
    """Defensive — JSON sometimes serialises numbers as strings."""
    assert g("48", "36") == "Vero 2-Lite Slider"
