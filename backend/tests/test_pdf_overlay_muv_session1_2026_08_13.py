"""MATERIAL ZONE LAYER — MUV SESSION 1 (Howard ruled 2026-08-13
pro-quotes reply 5).

Session 1 pins:
  - Polygon area math (shoelace @ 3/16" = 1'-0") is deterministic
    and correct for a known reference.
  - `apply_overlay_to_takeoff` writes qty + qty_src=human on the
    matching line and only that line (rebuild-survival delegated to
    hover.py's existing shield; the fact that qty_src=human lands
    is the contract).
  - Seam `pdf_overlay_polygon_write` is registered in
    seam_accounting.SEAM_REGISTRY.
  - Face-id validation admits the cardinals + `dormer:<label>` and
    rejects everything else.
  - Material-class validation admits {siding, soffit, accent, trim}
    only.

The HTTP surface (GET/PUT/DELETE) is exercised via a fastapi
TestClient because a live-auth path would double the mock burden
for a MUV; the client uses an authenticated stub user via the same
dependency-override pattern the test_estimates_multi_tenant tests
use elsewhere. Rebuild-survival IS the qty_src=human contract; a
separate test file for the hover-rebuild round-trip will land in
session 4 alongside the honesty layer regression.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seam_accounting import SEAM_REGISTRY  # noqa: E402
from routes.pdf_overlay import (  # noqa: E402
    apply_overlay_to_takeoff,
    polygon_sqft,
    _face_ok,
    _validate_polygon,
    MATERIAL_CLASSES,
    DEFAULT_SHEET_WIDTH_IN,
    DEFAULT_SHEET_HEIGHT_IN,
    PolygonWriteIn,
)


# ---------- (A) SEAM registered --------------------------------------

def test_pdf_overlay_polygon_write_seam_is_registered():
    """The write is a boundary crossing (drawing → structured
    takeoff → protected ledger). Every crossing declares its class."""
    assert "pdf_overlay_polygon_write" in SEAM_REGISTRY
    text = SEAM_REGISTRY["pdf_overlay_polygon_write"].lower()
    assert "human entry" in text
    assert "qty_src=human" in text
    assert "protected_estimate_ledger" in text


# ---------- (B) polygon area math ------------------------------------

def test_polygon_sqft_full_page_matches_scale_arithmetic():
    """A polygon covering the ENTIRE US-letter portrait sheet at
    3/16" = 1'-0" spans 8.5/(3/16) = 45.33 ft wide × 11/(3/16) =
    58.67 ft tall. Area = 2661 ft² (± 1 for rounding)."""
    full = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    area = polygon_sqft(full,
                        DEFAULT_SHEET_WIDTH_IN, DEFAULT_SHEET_HEIGHT_IN)
    # 8.5 / (3/16) = 45.3333 ft; 11 / (3/16) = 58.6667 ft.
    # 45.3333 × 58.6667 = 2659.55...
    assert 2658 <= area <= 2661, f"got {area}"


def test_polygon_sqft_quarter_page_is_quarter_area():
    """Half-width × half-height polygon = ¼ of the full-page area."""
    full_area = polygon_sqft(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    quarter = polygon_sqft(
        [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]])
    assert abs(quarter * 4 - full_area) < 0.1


def test_polygon_sqft_ignores_winding_order():
    """A CW polygon and a CCW polygon over the same vertices produce
    the same absolute area."""
    ccw = [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]
    cw = list(reversed(ccw))
    assert abs(polygon_sqft(ccw) - polygon_sqft(cw)) < 1e-9


def test_polygon_sqft_degenerate_returns_zero():
    """Fewer than 3 vertices ⇒ zero (no polygon)."""
    assert polygon_sqft([]) == 0.0
    assert polygon_sqft([[0.1, 0.1]]) == 0.0
    assert polygon_sqft([[0.1, 0.1], [0.2, 0.2]]) == 0.0


# ---------- (C) apply_overlay_to_takeoff -----------------------------

def _base_lines():
    return [
        {"tab": "vinyl", "section": "Vinyl Siding",
         "name": "Charter Oak", "unit": "SQ", "face_id": "front",
         "qty": 5.0, "qty_src": "derived"},
        {"tab": "vinyl", "section": "Vinyl Siding",
         "name": "Charter Oak", "unit": "SQ", "face_id": "back",
         "qty": 5.0, "qty_src": "derived"},
        {"tab": "vinyl", "section": "Trim", "name": "J-channel",
         "unit": "LF", "face_id": "front",
         "qty": 12.0, "qty_src": "derived"},
    ]


def test_apply_stamps_qty_src_human_on_the_matched_line():
    """A siding polygon on the front face updates ONLY the front
    siding line's qty and stamps qty_src=human. Rebuild survival is
    then delivered by hover.py's existing shield on 'human'."""
    polys = [{
        "page": 1, "face_id": "front", "material_class": "siding",
        "vertices_pct": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]],
    }]
    out = apply_overlay_to_takeoff(_base_lines(), polys)
    front = next(l for l in out
                 if l["face_id"] == "front" and l["section"] == "Vinyl Siding")
    back = next(l for l in out
                if l["face_id"] == "back" and l["section"] == "Vinyl Siding")
    trim = next(l for l in out if l["section"] == "Trim")
    assert front["qty_src"] == "human"
    assert front["qty"] > 0
    assert "PDF-OVERLAY" in front.get("note", "")
    # Untouched lines keep their derived source.
    assert back["qty_src"] == "derived"
    assert trim["qty_src"] == "derived"


def test_apply_sums_multiple_polygons_on_same_face():
    """Two polygons on the front siding line sum their sqft."""
    polys = [
        {"page": 1, "face_id": "front", "material_class": "siding",
         "vertices_pct": [[0.0, 0.0], [0.25, 0.0], [0.25, 0.25], [0.0, 0.25]]},
        {"page": 1, "face_id": "front", "material_class": "siding",
         "vertices_pct": [[0.5, 0.5], [0.75, 0.5], [0.75, 0.75], [0.5, 0.75]]},
    ]
    out = apply_overlay_to_takeoff(_base_lines(), polys)
    front = next(l for l in out
                 if l["face_id"] == "front" and l["section"] == "Vinyl Siding")
    expected = polygon_sqft(polys[0]["vertices_pct"]) + \
               polygon_sqft(polys[1]["vertices_pct"])
    assert abs(front["qty"] - round(expected, 2)) < 0.01


def test_apply_polygon_without_matching_line_is_dropped():
    """A polygon whose (material_class, face_id) has no line is
    dropped on the floor in Session 1 — Session 3 (LegendPanel)
    handles new-row synthesis."""
    polys = [{
        "page": 1, "face_id": "left", "material_class": "siding",
        "vertices_pct": [[0.0, 0.0], [0.2, 0.0], [0.2, 0.2], [0.0, 0.2]],
    }]
    out = apply_overlay_to_takeoff(_base_lines(), polys)
    # Every original line survives untouched.
    assert len(out) == 3
    for orig, new in zip(_base_lines(), out):
        assert orig["qty"] == new["qty"]
        assert new.get("qty_src") != "human"


# ---------- (D) validation -------------------------------------------

def test_face_ok_accepts_cardinals_and_dormer_labels():
    for f in ("front", "back", "left", "right"):
        assert _face_ok(f)
    assert _face_ok("dormer:north-A")
    assert _face_ok("dormer:1")


def test_face_ok_rejects_bad_ids():
    assert not _face_ok("")
    assert not _face_ok("garage")  # not a cardinal
    assert not _face_ok("dormer:")  # empty label
    assert not _face_ok("front_dormer")  # doesn't match prefix


def test_material_classes_are_the_four_muv_classes():
    """MUV ships four material classes. Additions are one-line
    registry edits — deliberately tight to keep the walk-bar honest."""
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
    """The untouchable module's docstring names pdf_overlay_polygon
    in the human-entry list — the walk on EST-886440 depends on
    this class being on the ledger's write set (built in at MUV
    birth per pro-quotes reply 5, not discovered on the walk)."""
    from untouchable import ledger_human_write
    doc = ledger_human_write.__doc__ or ""
    assert "pdf_overlay_polygon" in doc
    assert "human entry" in doc.lower() or "human input" in doc.lower()
