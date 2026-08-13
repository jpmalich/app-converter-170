"""SEND-9 ANCHOR RECALIBRATION + REFUSED-vs-FABRICATED
(Howard ruled 2026-08-12 send-9).

Verbatim: "A text anchor works for a labelled feature. 'GARAGE' is a
word printed on the page, so a garage wall height can anchor to it.
A WALL WIDTH HAS NO LABEL. 58'-0\" sits under the drawing with no
text near it. The right anchor for those is the ELEVATION VIEW REGION
the path belongs to, not a token."

Same ruling: "Refused is not fabricated, and the card must say which."

Two calibrations:
  a) Cardinal wall paths (walls.front.*, gutter_runs.back.lf, etc.)
     are SHEET-SCOPED — the whole sheet is the feature when its title
     names the direction. Any match on the page qualifies.
  b) A refusal whose reason is "quote norm not present in OCR" is
     FABRICATED (killed on `_dim_fabricated`); a refusal whose reason
     is anchor/proximity is UNVERIFIED (kept on `_dim_unverified` for
     the card, nulled on raw so it does not feed money).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _feature_anchors_for_path,
    _null_unverified_quotes,
    _ocr_locate_evidence,
    _path_is_sheet_scoped,
    build_blueprint_readback,
)


# ---------- (A) sheet-scoping decision ----------

def test_cardinal_wall_path_is_sheet_scoped():
    for p in ("walls.front.width_ft", "walls.back.width_ft",
              "walls.left.height_ft", "walls.right.height_ft",
              "gutter_runs.front.lf", "gutter_runs.back.lf"):
        assert _path_is_sheet_scoped(p), p


def test_labelled_feature_path_is_not_sheet_scoped():
    for p in ("roof_planes.garage.wall_height_ft",
              "roof_planes.entry.rake_lf",
              "roof_planes.bonus room.eave_lf",
              "porch.porch_width_ft"):
        assert not _path_is_sheet_scoped(p), p


def test_wall_segment_path_is_not_sheet_scoped():
    """A segment path carries its own sub-label — GARAGE WING is a
    text feature within the elevation, tighter radius applies."""
    p = "walls.front.segments.garage wing 1-story.width_ft"
    assert _feature_anchors_for_path(p) == [
        "FRONT", "GARAGE", "WING", "1STORY"]
    # Non-cardinal anchors mixed in — NOT sheet-scoped.
    assert not _path_is_sheet_scoped(p)


def test_bare_scalar_still_disables_gate():
    assert _path_is_sheet_scoped("eave_overhang_in") is False
    assert _feature_anchors_for_path("eave_overhang_in") == []


# ---------- (B) sheet-scope on the OCR locate ----------

def _page(text_at: list[tuple[int, int, str]], size=(1000, 400)) -> bytes:
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    for (x, y, t) in text_at:
        d.text((x, y), t, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_wall_width_locates_via_sheet_title_even_when_far_from_word():
    """SEND-9 calibration: walls.front.width_ft on a page whose TITLE
    contains FRONT → the whole page is the feature. The quote sits
    at the top; the FRONT ELEVATION title sits at the bottom, well
    beyond the tight-radius threshold — locate ACCEPTS anyway."""
    ev = {"walls.front.width_ft":
          {"v": 58.0, "page": 1, "from": "58'-0\"",
           "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "FRONT ELEVATION",
         "useful_for": "elevation"}]}
    # Page with 58-0 at the top; no FRONT word anywhere on the page
    # itself. Under send-8 tight-radius, this would have refused.
    page = _page([(200, 80, "58-0")])
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["walls.front.width_ft"]
    assert e["precision"] == "ocr", (
        "sheet-scoped: sheet_title carries FRONT → any match on this "
        "page qualifies")
    assert e["loc"] is not None


def test_wall_width_locates_via_ocr_direction_word_on_page():
    """Same rule, other branch: sheet_title unhelpful, but the page
    itself carries FRONT ELEVATION as a title bar. Sheet-scoped still
    accepts because the direction word IS on the page's pixels."""
    ev = {"walls.left.width_ft":
          {"v": 39.0, "page": 1, "from": "39'-0\"",
           "loc": None, "precision": None}}
    raw = {}
    page = _page([(300, 80, "39-0"),
                  (100, 250, "LEFT ELEVATION")])
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["walls.left.width_ft"]
    assert e["precision"] == "ocr"


def test_wall_width_refuses_when_direction_word_missing_from_sheet():
    """Sheet-scoped without sheet_title AND without the direction
    word on the page AND the sheet is not an elevation/floor_plan →
    refused. This is the wall path being read off a schedule sheet
    or detail — the read was wrong about which sheet the quote is
    on."""
    ev = {"walls.back.width_ft":
          {"v": 58.0, "page": 1, "from": "58'-0\"",
           "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "WINDOW SCHEDULE",
         "useful_for": "schedule"}]}
    page = _page([(300, 80, "58-0")])  # no BACK / REAR word
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["walls.back.width_ft"]
    assert e["loc"] is None
    assert e["precision"] is None
    m = raw["_ocr_quote_misses"][0]
    assert "cardinal anchor" in m["reason"] or "not on sheet" in m["reason"]


def test_wall_width_accepts_on_floor_plan_regardless_of_direction():
    """SEND-9 addendum: a floor plan shows ALL four walls at once with
    no per-direction label. When the sheet's `useful_for` is
    `floor_plan`, cardinal wall paths accept any match on the page —
    the sheet TYPE is enough anchor for wall dimensions of any wall.
    Live Boni case: 58'-0" for walls.back.width_ft is quoted from the
    FIRST FLOOR PLAN (page 6), not from an elevation."""
    ev = {"walls.back.width_ft":
          {"v": 58.0, "page": 1, "from": "58'-0\"",
           "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "FIRST FLOOR PLAN",
         "useful_for": "floor_plan"}]}
    page = _page([(300, 80, "58-0")])  # no BACK / REAR word
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["walls.back.width_ft"]
    assert e["precision"] == "ocr"


def test_back_wall_locates_when_sheet_title_says_rear():
    """SEND-9 addendum: BACK ↔ REAR is a cardinal synonym.
    'FRONT & REAR ELEVATIONS' anchors a walls.back.* quote."""
    ev = {"walls.back.height_ft":
          {"v": 20.0, "page": 1, "from": "20'-0\"",
           "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "FRONT & REAR ELEVATIONS",
         "useful_for": "elevation"}]}
    page = _page([(300, 80, "20-0")])
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["walls.back.height_ft"]
    assert e["precision"] == "ocr"


def test_labelled_feature_still_uses_tight_radius():
    """A GARAGE / PORCH / ENTRY label sitting on the page but far
    from the quote refuses — the send-8 contract holds for labelled
    features (a run of GARAGE on the area table does not anchor a
    quote drawn on the opposite side of the sheet)."""
    ev = {"roof_planes.garage.wall_height_ft":
          {"v": 9.9, "page": 1, "from": "9'-11 1-8\"",
           "loc": None, "precision": None}}
    raw = {}
    page = _page(
        [(100, 100, "GARAGE"), (1800, 1900, "9-11 1-8")],
        size=(2000, 2000))
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["roof_planes.garage.wall_height_ft"]
    assert e["loc"] is None
    assert "of feature anchor" in raw["_ocr_quote_misses"][0]["reason"]


# ---------- (C) build_blueprint_readback surfaces unverified vs fabricated ----------

def test_readback_carries_unverified_and_fabricated_records():
    raw = {
        "walls": [{"label": "front", "width_ft": None}],
        "roof_planes": [],
        "_dim_unverified": [{
            "path": "walls.front.width_ft", "value": 58.0,
            "quotes": ["58'-0\""],
            "reason": "no feature anchor ['FRONT'] on page"}],
        "_dim_fabricated": [{
            "path": "roof_planes.garage.wall_height_ft", "value": 9.5,
            "quotes": ["9'-6\" garage wall"],
            "reason": "quote norm not present in OCR on page"}],
    }
    rb = build_blueprint_readback(raw)
    # The two lists ride the readback under distinct keys.
    assert rb.get("dim_unverified"), (
        "unverified records must reach the readback so the card shows "
        "the number MARKED unverified instead of pretending we do not know")
    assert rb.get("dim_fabricated")
    unv_paths = {r["path"] for r in rb["dim_unverified"]}
    fab_paths = {r["path"] for r in rb["dim_fabricated"]}
    assert "walls.front.width_ft" in unv_paths
    assert "roof_planes.garage.wall_height_ft" in fab_paths


def test_rail_fires_dims_unverified_code_when_records_present():
    raw = {
        "walls": [{"label": "front"}], "roof_planes": [],
        "_dim_unverified": [{
            "path": "walls.front.width_ft", "value": 58.0,
            "quotes": ["58'-0\""], "reason": "no anchor"}],
    }
    rb = build_blueprint_readback(raw)
    codes = {r["code"]: r for r in rb["rail"]}
    assert "dims_unverified" in codes
    assert codes["dims_unverified"]["level"] == "warn"
    assert "walls.front.width_ft" in codes["dims_unverified"]["text"]


def test_rail_fires_dims_fabricated_code_when_records_present():
    raw = {
        "walls": [], "roof_planes": [{"label": "garage"}],
        "_dim_fabricated": [{
            "path": "roof_planes.garage.wall_height_ft", "value": 9.5,
            "quotes": ["9'-6\""], "reason": "not in OCR"}],
    }
    rb = build_blueprint_readback(raw)
    codes = {r["code"]: r for r in rb["rail"]}
    assert "dims_fabricated" in codes
    assert codes["dims_fabricated"]["level"] == "loud"
    assert "roof_planes.garage.wall_height_ft" in (
        codes["dims_fabricated"]["text"])
