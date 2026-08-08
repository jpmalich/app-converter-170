"""OCR-FOR-COORDINATES (Howard ruled 2026-08-08, after grading the live
fire: audit panel PARTIAL — one location box in twenty-two).

"Do not ask the model for boxes again. Run LOCAL OCR over the retained
page rasters, index every text run with its bounding box, then MATCH
THE MODEL'S VERBATIM QUOTE TO THE OCR BOX."

HARD SEPARATION, THE RULING: OCR SUPPLIES LOCATION, NEVER VALUE. It is
never promoted to ground truth (three-class probe rule stands); the
model still does the reading.

FREE SECOND READ: where OCR text and the model's quote disagree, that
is a checkable contradiction at no extra cost — it would have caught
"2-4_5-4" against the printed "3-0_4-0" the day it happened.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _ocr_locate_evidence, _ocr_norm, build_blueprint_readback,
)

SRC = (Path(__file__).resolve().parents[1] / "routes/ai_blueprint.py"
       ).read_text(encoding="utf-8")
DICT_TEXT = (Path(__file__).resolve().parents[2]
             / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")


def test_norm_kills_the_glyph_noise_between_print_and_ocr():
    # 58'-0" comes back from OCR as 58-0° — both normalise to 580.
    assert _ocr_norm("58'-0\"") == "580"
    assert _ocr_norm("58-0°") == "580"
    assert _ocr_norm("2'-11 1/2\"") == "21112"
    assert _ocr_norm(None) == ""


def _page_with(text: str) -> bytes:
    img = Image.new("RGB", (1000, 400), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    d.text((100, 100), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def located():
    ev = {
        "walls.front.width_ft": {"v": 58.0, "page": 1, "from": "58'-0\"",
                                 "loc": None, "precision": None},
        "eave_overhang_in": {"v": 12.0, "page": 1, "from": "99x77 NOWHERE",
                             "loc": None, "precision": None},
        "walls.back.width_ft": {"v": 34.0, "page": 1, "from": "34'-0\"",
                                "loc": {"x_pct": 1, "y_pct": 1,
                                        "w_pct": 1, "h_pct": 1},
                                "precision": "exact"},
    }
    raw = {}
    _ocr_locate_evidence(ev, [_page_with("58-0")], raw)
    return ev, raw


def test_the_quote_gets_a_box_and_the_value_is_never_touched(located):
    ev, _raw = located
    e = ev["walls.front.width_ft"]
    assert e["precision"] == "ocr"
    assert e["loc"] is not None
    assert 0 < e["loc"]["x_pct"] < 50 and 0 < e["loc"]["y_pct"] < 80
    # THE RULING: location only — value and quote untouched.
    assert e["v"] == 58.0
    assert e["from"] == "58'-0\""


def test_a_quote_ocr_cannot_find_is_a_named_contradiction(located):
    ev, raw = located
    e = ev["eave_overhang_in"]
    assert e["loc"] is None and e["precision"] is None, \
        "a miss never invents a box"
    misses = raw.get("_ocr_quote_misses") or []
    assert any(m["path"] == "eave_overhang_in" for m in misses)
    assert all(set(m) == {"path", "page", "from", "rotations_checked"}
               for m in misses), \
        "the miss record carries provenance + the rotation audit, never a value verdict"


def test_exact_text_layer_boxes_are_never_overwritten(located):
    ev, _raw = located
    e = ev["walls.back.width_ft"]
    assert e["precision"] == "exact"
    assert e["loc"] == {"x_pct": 1, "y_pct": 1, "w_pct": 1, "h_pct": 1}


def test_the_contradiction_reaches_the_card():
    rb = build_blueprint_readback(
        {"walls": [], "roof_planes": [], "gutter_runs": [], "windows": [],
         "_ocr_quote_misses": [{"path": "walls.front.width_ft", "page": 3,
                                "from": "58'-0\""}]})
    f = next(x for x in rb["rail"] if x["code"] == "ocr_quote_miss")
    assert f["level"] == "warn"
    assert "58'-0\"" in f["text"] and "sheet 3" in f["text"]


def test_the_ruling_is_in_the_source_and_the_worker_order_is_right():
    assert "OCR SUPPLIES" in SRC and "NEVER VALUE" in SRC
    exact = SRC.index("exact-locate failed")
    ocr = SRC.index("ocr-locate failed")
    assert exact < ocr, "text-layer exact boxes first; OCR fills the rest"


def test_locator_strings_exist_in_both_languages_and_claim_no_value():
    assert DICT_TEXT.count('"bp.va.ocrloc"') == 2
    assert DICT_TEXT.count('"bp.rb.rail.ocr_quote_miss"') == 2
    en = DICT_TEXT.split('"bp.va.ocrloc": "')[1].split('",')[0]
    assert "never from the locator" in en
