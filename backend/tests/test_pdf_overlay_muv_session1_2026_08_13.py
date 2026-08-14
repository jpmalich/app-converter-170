"""MATERIAL ZONE LAYER — MUV SESSION 2 (Howard ruled 2026-08-13
pro-quotes replies 5, 6, 7).

Session 2 pins the THREE LAWS Howard ruled before S2 could ship:

  A. REPLACE, NEVER ADD + the superseded derived value STAYS VISIBLE
     and MARKED SUPERSEDED.
  B. A human value is a FUNCTION of its polygons — delete one → the sum
     recomputes; delete the last on a (face_id, material_class) → the
     override RETIRES and the derived value RETURNS. PINNED BOTH
     DIRECTIONS: a delete leaving an override standing fails the build,
     and a retirement that does not restore the derived value fails the
     build.
  C. The scale is READ FROM THE SHEET, never defaulted. The 3/16"
     constant is GONE. No scale for a polygon's view → area REFUSED
     (sqft None), line flagged `overlay_scale_unreadable`, derived value
     untouched.

Plus the unchanged Session-1 contracts (seam registered, validation).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seam_accounting import SEAM_REGISTRY  # noqa: E402
from routes.pdf_overlay import (  # noqa: E402
    apply_overlay_to_takeoff,
    polygon_sqft_from_scale,
    _face_ok,
    _validate_polygon,
    MATERIAL_CLASSES,
    PolygonWriteIn,
)


# A calibration that maps the FULL page width (normalised 0→1) to a
# known real length. With page_w_px == page_h_px == 1000 and real_ft
# spanning the whole width, feet-per-pixel is deterministic and every
# area below is exact — NO baked scale constant anywhere.
FULL_WIDTH_SCALE = {"p1": [0.0, 0.0], "p2": [1.0, 0.0],
                    "real_ft": 40.0, "source": "calibration"}
PAGE_PX = (1000.0, 1000.0)  # (w, h)


# ---------- (A) SEAM registered --------------------------------------

def test_pdf_overlay_polygon_write_seam_is_registered():
    """The write is a boundary crossing (drawing → structured
    takeoff → protected ledger). Every crossing declares its class."""
    assert "pdf_overlay_polygon_write" in SEAM_REGISTRY
    text = SEAM_REGISTRY["pdf_overlay_polygon_write"].lower()
    assert "human entry" in text
    assert "qty_src=human" in text
    assert "protected_estimate_ledger" in text


# ---------- (C) scale math is evidence-grounded, never constant ------

def test_area_is_computed_from_the_calibration_not_a_constant():
    """A polygon spanning the full page under a 40ft-wide calibration on
    a square 1000×1000 page is 40ft × 40ft = 1600 ft². The number falls
    out of the EVIDENCE (the calibration), not a baked 3/16" scale."""
    full = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    area = polygon_sqft_from_scale(full, FULL_WIDTH_SCALE, *PAGE_PX)
    assert area is not None
    assert abs(area - 1600.0) < 1.0, f"got {area}"


def test_area_scales_with_the_calibration_length():
    """Halving the real_ft on the SAME calibration span quarters the
    area — proof the number tracks the evidence, not a constant."""
    full = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    big = polygon_sqft_from_scale(full, FULL_WIDTH_SCALE, *PAGE_PX)
    half_scale = {**FULL_WIDTH_SCALE, "real_ft": 20.0}
    small = polygon_sqft_from_scale(full, half_scale, *PAGE_PX)
    assert abs(small * 4 - big) < 0.1


def test_area_ignores_winding_order():
    ccw = [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]
    cw = list(reversed(ccw))
    a = polygon_sqft_from_scale(ccw, FULL_WIDTH_SCALE, *PAGE_PX)
    b = polygon_sqft_from_scale(cw, FULL_WIDTH_SCALE, *PAGE_PX)
    assert a is not None and b is not None
    assert abs(a - b) < 1e-6


def test_no_scale_refuses_conversion_returns_none():
    """Law C: no scale for the view → REFUSE. Never a defaulted number."""
    full = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    assert polygon_sqft_from_scale(full, None, *PAGE_PX) is None
    assert polygon_sqft_from_scale(full, FULL_WIDTH_SCALE, None, None) is None
    bad = {"p1": [0, 0], "p2": [0, 0], "real_ft": 40.0}  # zero-length span
    assert polygon_sqft_from_scale(full, bad, *PAGE_PX) is None
    zero_ft = {"p1": [0, 0], "p2": [1, 0], "real_ft": 0.0}
    assert polygon_sqft_from_scale(full, zero_ft, *PAGE_PX) is None


def test_degenerate_polygon_returns_none():
    assert polygon_sqft_from_scale([], FULL_WIDTH_SCALE, *PAGE_PX) is None
    assert polygon_sqft_from_scale([[0.1, 0.1]], FULL_WIDTH_SCALE, *PAGE_PX) is None


def test_printed_scale_pins_howard_rear_wall_to_1160_sqft():
    """PIN (Howard walk 2026-08-13): his rear wall is 58'-0" x 20'-0" =
    1,160 ft². At the printed 3/16"=1'-0" (in_per_ft=0.1875) on a page
    rendered at 144 DPI, ft_per_px = 1/(0.1875·144) = 1/27. A polygon of
    that wall's pixel extent MUST come back at ~1,160 ft² — printed
    geometry, a CHECK not a target. This is the chain that replaced the
    unreliable AI-endpoint calibration that read ~13x high."""
    dpi = 144.0
    in_per_ft = 3.0 / 16.0
    ft_per_px = 1.0 / (in_per_ft * dpi)          # 0.037037 ft/px
    w_px = 58.0 / ft_per_px                        # 1566 px
    h_px = 20.0 / ft_per_px                        # 540 px
    page_w, page_h = 3456.0, 2592.0
    x0, y0 = 0.1, 0.1
    x1 = x0 + w_px / page_w
    y1 = y0 + h_px / page_h
    verts = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    scale = {"mode": "printed_scale", "in_per_ft": in_per_ft, "dpi": dpi}
    area = polygon_sqft_from_scale(verts, scale, page_w, page_h)
    assert area is not None
    assert abs(area - 1160.0) < 5.0, f"expected ~1160, got {area}"


def test_printed_scale_refuses_without_dpi():
    """No recorded render DPI (a scan) → the printed-scale path REFUSES,
    it does not guess a DPI (Law C — a wrong DPI is invisible)."""
    verts = [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]]
    assert polygon_sqft_from_scale(
        verts, {"mode": "printed_scale", "in_per_ft": 0.1875, "dpi": None},
        3456.0, 2592.0) is None
    assert polygon_sqft_from_scale(
        verts, {"mode": "printed_scale", "in_per_ft": None, "dpi": 144.0},
        3456.0, 2592.0) is None


# ---------- (A) apply: REPLACE + SUPERSEDE ---------------------------

def _base_lines():
    # The REAL takeoff shape (EST-886440): ONE aggregate siding body line
    # in SQUARES, plus accessory (LF, excluded) and an ascend-tab line
    # (excluded — MUV binds the vinyl tab).
    return [
        {"tab": "vinyl", "section": "Vinyl Siding",
         "name": "Charter Oak", "unit": "SQ",
         "qty": 44.0, "raw_qty": 44.0, "qty_src": "derived"},
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": "J-channel", "unit": "LF",
         "qty": 133.0, "raw_qty": 133.0, "qty_src": "derived"},
        {"tab": "ascend", "section": "Vinyl Siding",
         "name": "Ascend", "unit": "SQ",
         "qty": 40.0, "raw_qty": 40.0, "qty_src": "derived"},
    ]


def _siding_line(out):
    return next(l for l in out
                if l["tab"] == "vinyl" and l["section"] == "Vinyl Siding")


def _poly(face, klass, sqft, pid="p1", baseline=44.0):
    return {"id": pid, "page": 1, "face_id": face, "material_class": klass,
            "vertices_pct": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]],
            "sqft": sqft, "derived_baseline_qty": baseline}


def test_apply_replaces_and_marks_superseded():
    """Law A: a siding polygon REPLACES the aggregate siding qty (does
    NOT add), converts ft²→SQUARES (900 ft² = 9 SQ), stamps
    qty_src=human, and KEEPS the app's number on `superseded_qty`."""
    out = apply_overlay_to_takeoff(
        _base_lines(), [_poly("front", "siding", 900.0)])
    sid = _siding_line(out)
    assert sid["qty_src"] == "human"
    assert sid["qty"] == 9.0                      # 900 ft² / 100 = 9 SQ; REPLACED
    assert sid["overlay_superseded"] is True
    assert sid["superseded_qty"] == 44.0          # app's number kept
    assert sid["overlay_sqft"] == 900.0
    assert "PDF-OVERLAY" in sid.get("note", "")
    # Accessory (LF) + ascend-tab lines are NOT touched.
    for l in out:
        if l is sid:
            continue
        assert l["qty_src"] == "derived"


def test_apply_sums_multiple_polygons_and_flags_merged():
    """Two zones on the class SUM their ft² and the line flags
    `overlay_merged` so the sheet says the numbers were merged."""
    out = apply_overlay_to_takeoff(
        _base_lines(),
        [_poly("front", "siding", 300.0, "a"),
         _poly("front", "siding", 200.0, "b")])
    sid = _siding_line(out)
    assert sid["overlay_sqft"] == 500.0
    assert sid["qty"] == 5.0
    assert sid["overlay_merged"] is True
    assert sid["overlay_polygon_count"] == 2


def test_delete_last_polygon_retires_override_and_restores_derived():
    """Law B forward: with NO polygons left, the override RETIRES and the
    app's number RETURNS — walk-bar item 7."""
    superseded = apply_overlay_to_takeoff(
        _base_lines(), [_poly("front", "siding", 900.0)])
    retired = apply_overlay_to_takeoff(superseded, [])
    sid = _siding_line(retired)
    assert sid["qty"] == 44.0
    assert sid["qty_src"] == "derived"
    assert "overlay_superseded" not in sid
    assert "superseded_qty" not in sid
    assert "PDF-OVERLAY" not in (sid.get("note") or "")


def test_no_line_keeps_an_override_after_its_polygons_are_gone():
    """Law B failing-build pin: NO line may wear qty_src=human or carry
    `overlay_superseded` once its polygons are gone."""
    superseded = apply_overlay_to_takeoff(
        _base_lines(), [_poly("front", "siding", 900.0)])
    retired = apply_overlay_to_takeoff(superseded, [])
    for l in retired:
        assert "overlay_superseded" not in l, l
    assert _siding_line(retired)["qty_src"] == "derived"


def test_retirement_restores_the_exact_derived_value_not_a_default():
    """Law B other-direction pin: retirement restores the EXACT baseline,
    never a default/zero."""
    original = _base_lines()
    superseded = apply_overlay_to_takeoff(original, [_poly("front", "siding", 99900.0)])
    retired = apply_overlay_to_takeoff(superseded, [])
    assert _siding_line(retired)["qty"] == _siding_line(original)["qty"]
    assert _siding_line(retired)["qty_src"] == "derived"


def test_delete_one_of_several_recomputes_the_sum():
    """Law B middle: with one of two polygons removed, the override stays
    but the sum RECOMPUTES from what remains."""
    two = apply_overlay_to_takeoff(
        _base_lines(),
        [_poly("front", "siding", 300.0, "a"),
         _poly("back", "siding", 200.0, "b")])
    assert _siding_line(two)["overlay_sqft"] == 500.0
    one = apply_overlay_to_takeoff(two, [_poly("front", "siding", 300.0, "a")])
    sid = _siding_line(one)
    assert sid["overlay_sqft"] == 300.0
    assert sid["qty"] == 3.0
    assert sid["qty_src"] == "human"
    assert sid.get("overlay_merged") is False


def test_unconvertible_polygon_refuses_and_flags_the_line():
    """A polygon whose scale could not be read (sqft None) does NOT
    override the line — it keeps the derived value and flags
    `overlay_scale_unreadable`."""
    out = apply_overlay_to_takeoff(
        _base_lines(), [_poly("front", "siding", None)])
    sid = _siding_line(out)
    assert sid["qty"] == 44.0
    assert sid["qty_src"] == "derived"
    assert sid["overlay_scale_unreadable"] is True
    assert "overlay_superseded" not in sid


def test_losing_scale_retires_a_prior_override():
    superseded = apply_overlay_to_takeoff(
        _base_lines(), [_poly("front", "siding", 900.0)])
    lost = apply_overlay_to_takeoff(superseded, [_poly("front", "siding", None)])
    sid = _siding_line(lost)
    assert sid["qty"] == 44.0
    assert sid["qty_src"] == "derived"
    assert sid["overlay_scale_unreadable"] is True


def test_apply_polygon_without_matching_line_is_dropped():
    """A polygon whose class has no matching aggregate line leaves every
    line untouched."""
    lines = [
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": "J-channel", "unit": "LF", "qty": 133.0, "qty_src": "derived"},
    ]
    out = apply_overlay_to_takeoff(lines, [_poly("front", "siding", 900.0)])
    assert len(out) == 1
    assert out[0]["qty"] == 133.0
    assert out[0].get("qty_src") != "human"


# ---------- (D) validation -------------------------------------------

def test_face_ok_accepts_cardinals_and_dormer_labels():
    for f in ("front", "back", "left", "right"):
        assert _face_ok(f)
    assert _face_ok("dormer:north-A")
    assert _face_ok("dormer:1")


def test_face_ok_rejects_bad_ids():
    assert not _face_ok("")
    assert not _face_ok("garage")
    assert not _face_ok("dormer:")
    assert not _face_ok("front_dormer")


def test_material_classes_are_the_four_muv_classes():
    assert MATERIAL_CLASSES == {"siding", "soffit", "accent", "trim"}


def test_validate_polygon_rejects_bad_material_class():
    with pytest.raises(Exception) as ei:
        _validate_polygon(PolygonWriteIn(
            page=1, face_id="front", material_class="lp_smart",
            vertices_pct=[[0, 0], [1, 0], [1, 1]]))
    assert ei.value.status_code == 400


def test_validate_polygon_rejects_bad_face_id():
    with pytest.raises(Exception) as ei:
        _validate_polygon(PolygonWriteIn(
            page=1, face_id="garage", material_class="siding",
            vertices_pct=[[0, 0], [1, 0], [1, 1]]))
    assert ei.value.status_code == 400


def test_validate_polygon_rejects_fewer_than_three_vertices():
    with pytest.raises(Exception) as ei:
        _validate_polygon(PolygonWriteIn(
            page=1, face_id="front", material_class="siding",
            vertices_pct=[[0, 0], [1, 0]]))
    assert ei.value.status_code == 400


def test_validate_polygon_rejects_out_of_range_vertex():
    with pytest.raises(Exception) as ei:
        _validate_polygon(PolygonWriteIn(
            page=1, face_id="front", material_class="siding",
            vertices_pct=[[0, 0], [1.5, 0], [1, 1]]))
    assert ei.value.status_code == 400


# ---------- (E) protected-estimate human-entry rule ------------------

def test_untouchable_names_pdf_overlay_polygon_as_human_entry():
    from untouchable import ledger_human_write
    doc = ledger_human_write.__doc__ or ""
    assert "pdf_overlay_polygon" in doc
    assert "human entry" in doc.lower() or "human input" in doc.lower()
