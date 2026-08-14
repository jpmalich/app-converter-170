"""DRAWN-GEOMETRY CLASSIFICATION — SEND-12 (2026-08-14).

Howard's ruling 3: the enumerated {elevation, floor_plan} list excluded
pages that plainly carry drawn geometry — a joist plan / detail / mech /
elec page types as "other" (never a named drawing kind), and page 9's
genuinely-printed dims died at existence because "other" was excluded.

A sheet that carries drawn geometry prints its dimensions AS geometry,
never beside a text label, so the tight label-bound proximity radius is a
broken instrument on it and presence-only applies. The drawing kinds are
elevation, floor_plan, roof and other. Only SCHEDULE (table) and COVER
(title page) keep the tight radius; an UNCLASSIFIED sheet ("") also stays
strict rather than loosen an unknown that might be a mistyped table.

(The content-based override that re-checks a schedule/cover page against
its own dimension-token count is HELD — it needs a real plan set with
schedule/cover pages to pick a non-invented threshold. See
scripts/drawn_geometry_token_report.py.)
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import routes.ai_blueprint as ab  # noqa: E402

SEG = "walls.front.segments.main body 2-story.width_ft"


def test_geometry_kinds_truth_table():
    for kind in ("elevation", "floor_plan", "roof", "other"):
        assert ab._sheet_carries_geometry(kind) is True, kind
    for kind in ("schedule", "cover", ""):
        assert ab._sheet_carries_geometry(kind) is False, kind


def test_segment_dim_is_presence_only_on_every_drawing_kind():
    # A joist plan / detail typed "other" or "roof" is now a drawing —
    # the exact page-9 rescue.
    assert ab._sheet_scoped_for(SEG, "other") is True
    assert ab._sheet_scoped_for(SEG, "roof") is True
    assert ab._sheet_scoped_for(SEG, "elevation") is True
    assert ab._sheet_scoped_for(SEG, "floor_plan") is True
    # Tables and title pages keep the tight radius; unknown stays strict.
    assert ab._sheet_scoped_for(SEG, "schedule") is False
    assert ab._sheet_scoped_for(SEG, "cover") is False
    assert ab._sheet_scoped_for(SEG, "") is False


def _page(text_at, size=(1200, 500)) -> bytes:
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


def test_dim_on_an_other_page_locates_presence_only():
    """Page-9 case: a segment dim printed on a page typed "other" (a
    joist/detail sheet) locates on presence alone — no MAIN BODY label
    beside it."""
    ev = {SEG: {"v": 34.0, "page": 1, "from": "34'-0\"",
                "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "SECOND FLOOR JOIST PLAN",
         "useful_for": "other"}]}
    page = _page([(300, 120, "34-0")])
    ab._ocr_locate_evidence(ev, [page], raw)
    assert ev[SEG]["precision"] == "ocr"


def test_same_dim_on_a_schedule_page_stays_label_bound():
    """No regression: the SAME dim on a schedule page with no label
    nearby is still refused — the loosening did not reach tables."""
    ev = {SEG: {"v": 34.0, "page": 1, "from": "34'-0\"",
                "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "WINDOW SCHEDULE",
         "useful_for": "schedule"}]}
    page = _page([(300, 120, "34-0")])
    ab._ocr_locate_evidence(ev, [page], raw)
    assert ev[SEG]["precision"] is None
    assert ev[SEG]["loc"] is None
