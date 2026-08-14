"""FRACTION SKELETON INTO THE EXISTENCE TEST — SEND-12 (2026-08-14).

Howard's ruling 2: the OCR engine cannot read the stacked ½ / ¼ glyphs at
all, so a printed-and-true 24'-0 1/2" misses on its full norm and dies at
the EXISTENCE step (marked fabricated/unverified) though it is on the
page. The fraction-STRIPPED skeleton (24'-0") is tried as a fallback at
the existence layer; a skeleton hit sets precision="ocr",
located_via="fraction_skeleton", rides the _skeleton_located breadcrumb
and the info rail — never counted as fabricated. "The fractions rest on
the read's transcription."

TWO HARD GUARDS PINNED (the ruling, not a preference):
  * FRACTIONS-ONLY STRIP — never a whole digit. 24'-0" carries no
    fraction, so it produces NO skeleton and can NEVER skeleton-match
    2'-0" (a 12× error wearing a located chip). The magnitude risk stays
    bounded because the stripped part is always a fraction of an inch.
  * AMBIGUOUS SKELETON NEVER LOCATES — if two distinct full quotes on a
    page share a skeleton (24'-0 1/2" and 24'-0 1/4" → 24'-0"), or the
    skeleton matches multiple distinct runs, NEITHER may locate. Same
    principle as one-source-one-path: when you cannot tell which, you do
    not pick.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import routes.ai_blueprint as ab  # noqa: E402
from routes.ai_blueprint import build_blueprint_readback  # noqa: E402


# ---------- (A) the strip is fractions-only, never a digit ----------

def test_whole_inch_quote_has_no_skeleton():
    """A quote with no fraction produces NO skeleton — so it can never be
    resurrected against a smaller printed number."""
    assert ab._fraction_skeleton("24'-0\"") is None
    assert ab._fraction_skeleton("30'-0\"") is None
    assert ab._fraction_skeleton("58'-0\"") is None


def test_skeleton_strips_only_the_fraction_never_a_digit():
    """24'-0 1/2" → 24'-0" (same whole-inch norm), NEVER 2'-0". The
    magnitude is bounded: every whole digit survives the strip."""
    sk = ab._fraction_skeleton("24'-0 1/2\"")
    assert sk is not None
    assert ab._ocr_norm(sk) == ab._ocr_norm("24'-0\"")
    # The 12× error the guard forbids: skeleton must NOT collapse to 2'-0".
    assert ab._ocr_norm(sk) != ab._ocr_norm("2'-0\"")
    # Two-digit denominators strip too, still fractions-only.
    assert ab._ocr_norm(ab._fraction_skeleton("9'-11 15/16\"")) == \
        ab._ocr_norm("9'-11\"")


def test_skeleton_only_removes_fraction_tokens():
    """Property guard: re-inserting the removed span must be a pure
    \\d+/\\d+ fraction token — proving no digit outside a fraction is
    ever dropped."""
    import re
    for q in ("24'-0 1/2\"", "9'-11 15/16\"", "34'-6 3/4\""):
        sk = ab._fraction_skeleton(q)
        # Everything the skeleton dropped is matched by the fraction RE.
        assert re.sub(r"\s*\d+/\d+\s*\"?", "", q) == sk


# ---------- helpers to render a real raster the OCR engine reads ----------

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


# ---------- (B) the skeleton LOCATES at the existence test ----------

def test_stacked_fraction_dim_locates_by_skeleton_on_a_drawing():
    """24'-0 1/2" is quoted; the page prints only the whole inch 24-0
    (OCR cannot read the ½). The existence test rescues it by skeleton —
    precision ocr, located_via fraction_skeleton, NAMED on the
    breadcrumb, and NOT in the miss list."""
    ev = {"walls.front.width_ft":
          {"v": 24.5, "page": 1, "from": "24'-0 1/2\"",
           "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "FRONT ELEVATION",
         "useful_for": "elevation"}]}
    page = _page([(300, 120, "24-0")])
    ab._ocr_locate_evidence(ev, [page], raw)
    e = ev["walls.front.width_ft"]
    assert e["precision"] == "ocr", "skeleton must rescue a stacked-fraction dim"
    assert e.get("located_via") == "fraction_skeleton"
    assert e["loc"] is not None
    skl = raw.get("_skeleton_located") or []
    assert any(d["path"] == "walls.front.width_ft" for d in skl)
    misses = raw.get("_ocr_quote_misses") or []
    assert not any(m["path"] == "walls.front.width_ft" for m in misses)


# ---------- (C) ambiguous skeleton never locates ----------

def test_shared_skeleton_on_a_page_locates_neither():
    """24'-0 1/2" and 24'-0 1/4" both skeleton to 24'-0". With one 24-0
    printed, a skeleton hit cannot tell which quote it found — NEITHER
    locates; both stay misses."""
    ev = {
        "walls.front.width_ft":
            {"v": 24.5, "page": 1, "from": "24'-0 1/2\"",
             "loc": None, "precision": None},
        "walls.back.width_ft":
            {"v": 24.25, "page": 1, "from": "24'-0 1/4\"",
             "loc": None, "precision": None},
    }
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "FRONT & REAR ELEVATIONS",
         "useful_for": "elevation"}]}
    page = _page([(300, 120, "24-0")])
    ab._ocr_locate_evidence(ev, [page], raw)
    assert ev["walls.front.width_ft"]["precision"] is None
    assert ev["walls.back.width_ft"]["precision"] is None
    misses = {m["path"] for m in (raw.get("_ocr_quote_misses") or [])}
    assert "walls.front.width_ft" in misses
    assert "walls.back.width_ft" in misses
    assert not (raw.get("_skeleton_located") or [])


def test_skeleton_matching_two_distinct_runs_does_not_locate():
    """One quote, but its skeleton (24'-0") matches TWO distinct printed
    24-0 runs on the page — a skeleton hit cannot pick one. Refused."""
    ev = {"walls.front.width_ft":
          {"v": 24.5, "page": 1, "from": "24'-0 1/2\"",
           "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "FRONT ELEVATION",
         "useful_for": "elevation"}]}
    page = _page([(200, 120, "24-0"), (800, 360, "24-0")])
    ab._ocr_locate_evidence(ev, [page], raw)
    assert ev["walls.front.width_ft"]["precision"] is None
    assert not (raw.get("_skeleton_located") or [])


def test_non_fraction_absent_quote_is_not_resurrected():
    """A whole-inch quote absent from the page (the fabricated 39'-0"
    sides) carries no fraction, so no skeleton exists — it dies correctly
    even though the sheet is presence-only."""
    ev = {"walls.left.width_ft":
          {"v": 39.0, "page": 1, "from": "39'-0\"",
           "loc": None, "precision": None}}
    raw = {"sheets_identified": [
        {"page": 1, "sheet_title": "LEFT ELEVATION",
         "useful_for": "elevation"}]}
    page = _page([(300, 120, "24-0")])  # only 24-0 on the page
    ab._ocr_locate_evidence(ev, [page], raw)
    e = ev["walls.left.width_ft"]
    assert e["precision"] is None
    assert e["loc"] is None
    assert not (raw.get("_skeleton_located") or [])


# ---------- (D) the info rail FIRES and NAMES the leniency ----------

def test_skeleton_located_fires_the_named_info_rail():
    """A skeleton locate must reach the card as an INFO rail named
    'dim_located_by_skeleton' — never silent."""
    raw = {"_skeleton_located": [
        {"path": "walls.front.width_ft", "page": 9,
         "from": "24'-0 1/2\"", "skeleton": "240"}]}
    rb = build_blueprint_readback(raw)
    f = next(x for x in rb["rail"] if x["code"] == "dim_located_by_skeleton")
    assert f["level"] == "info"
    assert "fractions rest on the read" in f["text"]
