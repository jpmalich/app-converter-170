"""SEND-140 PINS — THE REFUSAL RECEIPT (Howard ruled 2026-08-27).

  When a gable or a dormer cheek refuses, the mark list already names
  the reason. Add ONE contractor line that says what to tape. Nothing
  else. Use the ACTUAL missing field. Do not invent a number. Do not
  suggest 0.70. Do not point at another photo or another face.

Scope: gables and dormer cheeks in PhotoTakeoffEditor ONLY — no coach for
wall heights, blueprint faces or openings was built, and a pin below says
so.
"""
import pathlib
import re
import sys

sys.path.insert(0, "/app/backend")

import pytest  # noqa: E402

from routes.photo_takeoff import (  # noqa: E402
    _dormer_figure, _gable_figure, _quantities)

EDITOR = pathlib.Path(
    "/app/frontend/src/components/estimate/PhotoTakeoffEditor.jsx")
ROUTE = pathlib.Path("/app/backend/routes/photo_takeoff.py")

IPP = 12.0                      # 12 in/px → pixels read as feet
TRI = [{"x": 0, "y": 8}, {"x": 15, "y": 0}, {"x": 30, "y": 8}]
FLAT = [{"x": 0, "y": 8}, {"x": 15, "y": 8}, {"x": 30, "y": 8}]
PIN = [{"x": 10, "y": 8}, {"x": 10, "y": 0}, {"x": 10, "y": 8}]
QUAD = [{"x": 0, "y": 10}, {"x": 6, "y": 10}, {"x": 6, "y": 0}, {"x": 0, "y": 0}]


def _g(pts, **kw):
    return {"id": "g1", "kind": "gable", "status": "confirmed",
            "points": pts, "label": "front gable", **kw}


def _d(pts, **kw):
    return {"id": "d1", "kind": "dormer", "status": "confirmed",
            "points": pts, "label": "left dormer", **kw}


def _scale():
    return {"span_px": 100.0, "anchor": {"inches": 1200.0}}


ALL_RECEIPTS = [
    _gable_figure(_g(FLAT), [], IPP)["receipt"],
    _gable_figure(_g(PIN), [], IPP)["receipt"],
    _gable_figure(_g(TRI[:2]), [], IPP)["receipt"],
    _gable_figure(_g(TRI), [], None)["receipt"],
    _dormer_figure(_d(QUAD), [], IPP)["cheek_receipt"],
    _dormer_figure(_d(QUAD[:3]), [], IPP)["receipt"],
    _dormer_figure(_d(QUAD), [], None)["receipt"],
]


# ---------------------------------------------------------------------------
# 1. THE LINE, ON THE ACTUAL MISSING FIELD
# ---------------------------------------------------------------------------
def test_a_gable_missing_its_rise_says_measure_the_rise():
    r = _gable_figure(_g(FLAT), [], IPP)["receipt"]
    assert r == ("Measure the rise at the peak on this photo — width is "
                 "known, rise is not.")


def test_a_gable_missing_its_width_says_the_width_not_the_rise():
    """The receipt names what is MISSING, not a generic plea."""
    r = _gable_figure(_g(PIN), [], IPP)["receipt"]
    assert "width is not" in r and "eave points apart" in r
    assert "rise is not" not in r


def test_a_mark_that_is_not_a_triangle_yet_says_so_with_its_own_count():
    r = _gable_figure(_g(TRI[:2]), [], IPP)["receipt"]
    assert r == ("Trace left eave, peak, and right eave — this mark is not "
                 "a triangle yet (2 of 3 points).")


def test_a_photo_with_no_scale_asks_for_the_scale_on_this_photo():
    r = _gable_figure(_g(TRI), [], None)["receipt"]
    assert "Set the scale on this photo" in r
    assert "already drawn" in r          # and does not ask him to re-draw


def test_the_dormer_cheeks_ask_for_the_typed_depth():
    f = _dormer_figure(_d(QUAD), [], IPP)
    assert f["cheek_receipt"] == ("Type the dormer depth in feet — the face "
                                  "is drawn, cheeks cannot be counted "
                                  "without it.")
    # the FACE was measured, so the face itself carries no receipt
    assert f["sqft"] == pytest.approx(60.0)
    assert f["receipt"] is None


def test_a_dormer_that_is_not_a_face_yet_says_so():
    r = _dormer_figure(_d(QUAD[:3]), [], IPP)["receipt"]
    assert "all four corners" in r and "3 of 4 points" in r


# ---------------------------------------------------------------------------
# 2. A MEASURED FIGURE CARRIES NO RECEIPT
# ---------------------------------------------------------------------------
def test_a_measured_gable_shows_no_receipt():
    f = _gable_figure(_g(TRI), [], IPP)
    assert f["sqft"] == pytest.approx(0.5 * 30.0 * 8.0)
    assert f["receipt"] is None
    assert _quantities([_g(TRI)], _scale())["gable_receipts"] is None


def test_a_counted_cheek_shows_no_receipt():
    f = _dormer_figure(_d(QUAD, depth_ft=2.0), [], IPP)
    assert f["cheek_sqft"] == pytest.approx(40.0)
    assert f["cheek_receipt"] is None
    q = _quantities([_d(QUAD, depth_ft=2.0)], _scale())
    assert q["dormer_receipts"] is None


def test_a_provisional_mark_earns_no_receipt_either():
    """Not confirmed is not refused — it is guidance, and it is already
    named as such."""
    q = _quantities([_g(FLAT, status="provisional")], _scale())
    assert q["gable_receipts"] is None


# ---------------------------------------------------------------------------
# 3. THE RAIL CARRIES ONE LINE PER REFUSED MARK, KEYED BY MARK
# ---------------------------------------------------------------------------
def test_the_rail_names_the_mark_the_line_belongs_to():
    q = _quantities([_g(FLAT), _d(QUAD)], _scale())
    g = q["gable_receipts"]
    d = q["dormer_receipts"]
    assert [r["id"] for r in g] == ["g1"]
    assert [r["id"] for r in d] == ["d1"]
    assert g[0]["label"] == "front gable" and d[0]["label"] == "left dormer"
    assert "rise" in g[0]["receipt"] and "depth" in d[0]["receipt"]
    # ONE sentence each — nothing else was added
    for r in g + d:
        assert r["receipt"].count(".") == 1
        assert set(r.keys()) == {"id", "label", "receipt"}


def test_the_editor_prints_the_servers_line_and_decides_nothing_itself():
    src = EDITOR.read_text()
    assert "photo-takeoff-receipt-" in src
    assert "qty?.gable_receipts" in src and "qty?.dormer_receipts" in src
    # the reason is never re-decided on the client
    for invented in ("Measure the rise", "Type the dormer depth",
                     "Trace left eave"):
        assert invented not in src


# ---------------------------------------------------------------------------
# 4. WHAT THE LINE MAY NEVER DO
# ---------------------------------------------------------------------------
def test_no_receipt_invents_a_number_or_suggests_a_factor():
    for r in ALL_RECEIPTS:
        assert r
        assert "0.7" not in r and "0.70" not in r
        assert "factor" not in r.lower()
        # the only digits allowed are the mark's own point count
        digits = [c for c in r if c.isdigit()]
        assert all(c in "0123456789" for c in digits)
        assert not any(tok in r for tok in ("ft²", "sq ft", "≈", "assume",
                                            "typical", "average"))


def test_no_receipt_points_at_another_photo_or_another_face():
    for r in ALL_RECEIPTS:
        low = r.lower()
        assert "another" not in low
        assert "other photo" not in low and "other face" not in low
        assert "opposite" not in low and "mirror" not in low
        assert "same as" not in low
        # every one of them points at THIS photo / THIS mark
        assert ("this photo" in low or "this mark" in low
                or "the dormer depth" in low)


def test_the_scope_line_holds_no_coach_was_built_for_anything_else():
    """Gables and dormer cheeks ONLY — no wall-height, blueprint-face or
    opening coach was added in this send."""
    src = ROUTE.read_text()
    # the ONLY receipt keys in the whole route are the four this send
    # added, all of them gable/cheek
    assert set(re.findall(r"[a-z_]*receipts?", src)) == {
        "receipt", "receipts", "cheek_receipt", "gable_receipts",
        "dormer_receipts"}   # "receipts" is the local accumulator
    # nothing above the gable helper coaches anything
    assert "receipt" not in src.split("def _gable_figure")[0]


def test_no_money_token_on_the_route():
    src = ROUTE.read_text()
    for bad in ("total_sell", "unit_price", '"mat"', '"lab"', "margin",
                "sell_price"):
        assert bad not in src
