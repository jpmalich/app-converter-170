"""ROTATED-TEXT LOCATOR + COMPUTED-IS-DERIVED (Howard ruled 2026-08-08
send 5, after the free second read found fiction on day one).

"Until rotation is covered, 'OCR missed it' and 'the model invented it'
ARE INDISTINGUISHABLE, and that distinction decides whether the
evidence layer can be trusted at all."

The rotated re-check of the eleven (run 82bd3a5e) resolved it: the
printed COMPONENTS of the stack locate in rotated orientation
(9'-11 1/8" found on sheet 1) while the 20'-0" total appears NOWHERE in
any orientation. The model fabricated the quote.

RULED: IF A VALUE IS COMPUTED, IT IS DERIVED. A stacked height routes
through {v, calc, srcs[]} with each component carrying its own printed
quote. A COMPUTED NUMBER WEARING A QUOTE IS A LIE WITH A CITATION.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _ocr_locate_evidence,
)


def _vertical_page(text: str) -> bytes:
    """Text drawn horizontally, then the whole canvas rotated 90° — the
    print is vertical on the page, the way plan height dims sit on an
    elevation's dimension chain."""
    img = Image.new("RGB", (1000, 400), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    d.text((100, 100), text, fill="black", font=font)
    img = img.transpose(Image.ROTATE_90)   # 400 wide × 1000 tall, vertical text
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def rotated_located():
    ev = {"walls.left.height_ft": {"v": 19.0, "page": 1, "from": "19'-0\"",
                                   "loc": None, "precision": None},
          "walls.back.height_ft": {"v": 20.0, "page": 1, "from": "20'-0\"",
                                   "loc": None, "precision": None}}
    raw = {}
    _ocr_locate_evidence(ev, [_vertical_page("19-0")], raw)
    return ev, raw


def test_vertical_print_locates_with_the_box_mapped_back_upright(rotated_located):
    ev, _raw = rotated_located
    e = ev["walls.left.height_ft"]
    assert e["precision"] == "ocr", "vertical print must locate via the rotated pass"
    loc = e["loc"]
    assert loc is not None
    # upright page is 400 wide × 1000 tall; the box must sit inside it
    assert 0 <= loc["x_pct"] <= 100 and 0 <= loc["y_pct"] <= 100
    assert loc["w_pct"] > 0 and loc["h_pct"] > 0
    # vertical text: taller than wide once mapped back upright
    # (pixel terms: page is 400 wide × 1000 tall)
    assert loc["h_pct"] * 1000 > loc["w_pct"] * 400, "a vertical run maps to a tall box"
    # THE RULING: location only.
    assert e["v"] == 19.0 and e["from"] == "19'-0\""


def test_a_quote_absent_in_every_orientation_is_the_named_contradiction(rotated_located):
    ev, raw = rotated_located
    e = ev["walls.back.height_ft"]
    assert e["loc"] is None and e["precision"] is None
    m = next(x for x in raw["_ocr_quote_misses"]
             if x["path"] == "walls.back.height_ft")
    assert m["rotations_checked"] is True, \
        "the miss must attest that rotation was ruled out — that is what " \
        "separates 'OCR missed it' from 'the model invented it'"


def test_the_computed_is_derived_ruling_is_in_the_contract():
    for must in ("IF A VALUE IS COMPUTED, IT IS DERIVED",
                 "A COMPUTED NUMBER WEARING A QUOTE IS A LIE WITH A CITATION",
                 "PRINTED AS SUCH on the page"):
        assert must in SYSTEM_PROMPT, f"prompt lost the ruling: {must!r}"
