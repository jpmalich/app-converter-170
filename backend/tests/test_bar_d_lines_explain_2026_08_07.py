"""ACCEPTANCE BAR LINE (d) — EVERY LINE EXPLAINS ITSELF (sealed by
Howard 2026-08-07, built FIRST per the sealed order): every emitted
line on every family carries a note that names its INPUTS and
CONVENTION — formula chips, not prose. A number the app cannot explain
does not print. This is what makes bar line (c) affordable.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from routes.hover import _build_lines  # noqa: E402
from test_boni_rulings_2026_08_05 import _boni_measurements  # noqa: E402

RICH = {
    **_boni_measurements(167, 99),
    "outside_corner_count": 8,
    "outside_corner_lf": 126,
    "_osc_corner_heights_ft": [10, 10, 6, 18, 6, 6, 15.5, 18],
    "_osc_heights_source": "blueprint_dimensioned",
    "_gutter_runs": [{"label": "front", "lf": 58},
                     {"label": "back", "lf": 58},
                     {"label": "porch", "lf": 10}],
}

# A note "explains itself" when it carries at least one number AND one
# formula/convention token — an input and how it was used.
_TOKENS = ("÷", "×", "+", "=", "LF", "sqft", "SQ", "pcs", "per", "stick",
           "run", "corner", "ruled", "perimeter", "count", "ceil")


def _explains(note: str) -> bool:
    return bool(note) and bool(re.search(r"\d", note)) and any(
        t in note for t in _TOKENS)


def _walk(measurements, label):
    lines = _build_lines(measurements)
    assert lines, f"{label}: nothing derived"
    unexplained = [
        f'{l.get("tab")}|{l.get("name")}' for l in lines
        if not _explains(str(l.get("note") or ""))]
    assert not unexplained, (
        f"{label}: lines printing numbers they cannot explain "
        f"(bar line d): {unexplained}")
    return lines


def test_every_line_explains_itself_flag_off():
    lines = _walk(dict(RICH), "integral-J OFF")
    tabs = {l.get("tab") or "vinyl" for l in lines}
    assert {"vinyl", "ascend"} <= tabs, \
        "walk must cover both interlocking families"


def test_every_line_explains_itself_flag_on():
    _walk({**RICH, "_windows_integral_j": True}, "integral-J ON")


def test_every_line_explains_itself_sparse_read():
    """A sparse read (photo door with little signal) still explains
    every line it does print."""
    _walk({"siding_with_openings_sqft": 1400, "eaves_lf": 90,
           "rakes_lf": 40, "window_count": 4, "door_count": 1},
          "sparse read")


def test_lp_lines_explain_themselves():
    lines = _build_lines(dict(RICH))
    lp = [l for l in lines if l.get("tab") == "lp_smart"]
    if not lp:
        import pytest
        pytest.skip("env:fixture_data: LP rows not emitted for this fixture — LP notes "
                    "guarded by the 261 Haugh pins")
    bad = [l["name"] for l in lp if not _explains(str(l.get("note") or ""))]
    assert not bad, f"LP lines without an explanation: {bad}"
