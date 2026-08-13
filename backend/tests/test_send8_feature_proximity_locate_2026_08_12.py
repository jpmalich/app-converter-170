"""SEND-8 FEATURE-PROXIMITY GATE + UNVERIFIED-NULL (Howard ruled
2026-08-12 send-8 item 1).

VERBATIM RULING: "A LOCATING MATCH MUST SIT NEAR THE FEATURE IT CLAIMS
TO DIMENSION, not merely somewhere on the same page." A quote that
matches anywhere on the page is not evidence — it can be a real dim on
a different feature (the E1 "30" bug one field over), or a
hallucination that happens to share glyphs with something else.

TWO PARTS:

  1. THE FEATURE-PROXIMITY GATE — the located rect's centre must sit
     within radius of a feature-anchor run on the same page. No
     anchor visible on the page ⇒ the locate refuses. `_ocr_quote_misses`
     records `reason` naming why.

  2. UNVERIFIED-NULL — a path whose evidence has NO locating source
     after the gate ran is treated as fabrication. The value NULLS.
     Evidence-or-null, extended from "no quote" to "quote we could
     not verify near the feature it claims to dim."

The pre-send-8 pins on `_ocr_locate_evidence` still hold; the gate
sits on top of them and refuses matches farther from the feature
anchor than the radius.
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
)

# ---------- (A) feature-anchor derivation ----------


def test_anchor_from_wall_path():
    assert _feature_anchors_for_path("walls.front.width_ft") == ["FRONT"]


def test_anchor_from_roof_plane_path():
    assert _feature_anchors_for_path(
        "roof_planes.garage.wall_height_ft") == ["GARAGE"]


def test_anchor_from_segment_path():
    assert _feature_anchors_for_path(
        "walls.front.segments.main body 2-story.width_ft"
    ) == ["FRONT", "MAIN", "BODY", "2STORY"]


def test_bare_scalar_has_no_anchor():
    """A path with no feature name (a global scalar) yields no
    anchors — the gate does not apply."""
    assert _feature_anchors_for_path("eave_overhang_in") == []


def test_gutter_run_path_anchors_on_side():
    assert _feature_anchors_for_path("gutter_runs.back.lf") == ["BACK"]


# ---------- (B) the OCR locate proximity gate ----------

def _page(text_at_pixel: list[tuple[int, int, str]],
          size=(1000, 400)) -> bytes:
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    for (x, y, t) in text_at_pixel:
        d.text((x, y), t, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def anchor_present_and_absent():
    """One quote whose FRONT anchor is on the page within radius; one
    whose GARAGE anchor is nowhere on the same page → gate refuses."""
    ev = {
        "walls.front.width_ft": {"v": 58.0, "page": 1, "from": "58'-0\"",
                                 "loc": None, "precision": None},
        "roof_planes.garage.wall_height_ft": {
            "v": 9.9, "page": 1, "from": "9'-11 1/8\"",
            "loc": None, "precision": None},
    }
    raw = {}
    # Page 1: 58-0 near a FRONT anchor. 9-11 1-8 sits elsewhere with
    # NO GARAGE anchor anywhere — the current-mainline mechanism
    # would have located it, the gate now refuses.
    page = _page([(100, 80, "58-0"), (150, 200, "FRONT"),
                  (700, 300, "9-11 1-8")])
    _ocr_locate_evidence(ev, [page], raw)
    return ev, raw


def test_gate_accepts_quote_near_its_feature_anchor(
        anchor_present_and_absent):
    ev, _raw = anchor_present_and_absent
    e = ev["walls.front.width_ft"]
    assert e["precision"] == "ocr", (
        "58-0 near FRONT anchor — gate accepts")
    assert e["loc"] is not None


def test_gate_refuses_quote_when_no_anchor_on_page(
        anchor_present_and_absent):
    ev, raw = anchor_present_and_absent
    e = ev["roof_planes.garage.wall_height_ft"]
    assert e["loc"] is None
    assert e["precision"] is None
    misses = raw["_ocr_quote_misses"]
    m = next(m for m in misses
             if m["path"] == "roof_planes.garage.wall_height_ft")
    assert "no feature anchor" in m["reason"].lower()
    assert "GARAGE" in m["reason"]


def test_gate_refuses_quote_matched_far_from_anchor():
    """Anchor present on page BUT the quote's match sits outside the
    proximity radius → refused with a gate reason. Uses a LABELLED
    feature path (roof_planes.garage.*) — send-9 relaxes cardinal
    wall paths to sheet-scope, but labelled features keep the tight
    radius the send-8 gate installed."""
    ev = {
        "roof_planes.garage.wall_height_ft": {
            "v": 9.9, "page": 1, "from": "9'-11 1-8\"",
            "loc": None, "precision": None},
    }
    raw = {}
    # Radius = 30% of max(w,h) = 600 pixels here. GARAGE anchor at
    # (100,100); the quote at (1800,1900) — >2400px away, outside
    # radius; refuses.
    page = _page([(100, 100, "GARAGE"), (1800, 1900, "9-11 1-8")],
                 size=(2000, 2000))
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["roof_planes.garage.wall_height_ft"]
    assert e["loc"] is None and e["precision"] is None
    misses = raw["_ocr_quote_misses"]
    m = next(m for m in misses
             if m["path"] == "roof_planes.garage.wall_height_ft")
    assert m["reason"], "gate refusal must name a reason"


def test_gate_disabled_for_bare_scalar_paths():
    """A bare scalar (no feature name) has no anchor → the gate
    doesn't apply → the legacy `_ocr_match` decides. A quote absent
    from OCR still misses; a quote found anywhere on the page
    locates."""
    ev = {
        "eave_overhang_in": {"v": 12.0, "page": 1, "from": "12'-0\"",
                             "loc": None, "precision": None},
    }
    raw = {}
    page = _page([(500, 200, "12-0")])
    _ocr_locate_evidence(ev, [page], raw)
    e = ev["eave_overhang_in"]
    assert e["precision"] == "ocr", (
        "bare-scalar path: gate disabled, legacy locator accepts")


# ---------- (C) unverified-null propagation ----------

def test_null_unverified_wall_width():
    """A wall-width path whose only src refused the gate (no anchor) →
    the wall's `width_ft` on the raw becomes None + value/quote/reason
    preserved on `_dim_unverified` so the card can show it MARKED
    unverified (send-9 item 3: showing 58'-0" as absent when it is
    printed and true is a different lie from the one we are fixing)."""
    raw = {
        "walls": [{"label": "front", "width_ft": 58.0}],
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 58.0, "page": 1,
                                     "from": "58'-0\""}
        },
        "_ocr_quote_misses": [{
            "path": "walls.front.width_ft", "page": 1,
            "from": "58'-0\"", "rotations_checked": True,
            "reason": "no feature anchor ['FRONT'] on page",
        }],
    }
    _null_unverified_quotes(raw)
    assert raw["walls"][0]["width_ft"] is None
    unv = raw.get("_dim_unverified") or []
    rec = next(r for r in unv if r["path"] == "walls.front.width_ft")
    assert rec["value"] == 58.0
    assert "58'-0\"" in rec["quotes"]
    assert "no feature anchor" in rec["reason"]
    assert "walls.front.width_ft" not in raw["_dim_evidence"]


def test_null_fabricated_quote_lands_in_dim_fabricated():
    """A quote whose norm is not present in OCR anywhere on the page —
    the string does not exist on the set. Fabricated. Killed. Value
    on the raw nulls, `_dim_fabricated` carries the killed record."""
    raw = {
        "roof_planes": [{"label": "garage", "wall_height_ft": 9.5}],
        "_dim_evidence": {
            "roof_planes.garage.wall_height_ft": {
                "v": 9.5, "page": 1,
                "from": "9'-6\" garage wall"}
        },
        "_ocr_quote_misses": [{
            "path": "roof_planes.garage.wall_height_ft", "page": 1,
            "from": "9'-6\" garage wall", "rotations_checked": True,
            "reason": "quote norm not present in OCR on page",
        }],
    }
    _null_unverified_quotes(raw)
    assert raw["roof_planes"][0]["wall_height_ft"] is None
    fab = raw.get("_dim_fabricated") or []
    rec = next(r for r in fab
               if r["path"] == "roof_planes.garage.wall_height_ft")
    assert rec["value"] == 9.5
    assert "9'-6\" garage wall" in rec["quotes"]
    # Under this branch _dim_unverified is untouched.
    assert not raw.get("_dim_unverified")


def test_null_unverified_roof_plane_wall_height():
    """The Boni class: wall_height_ft on a roof plane refused (matched
    but out of radius) → the plane's `wall_height_ft` becomes None
    and the record rides `_dim_unverified` (real string, unconfirmed
    near feature)."""
    raw = {
        "roof_planes": [
            {"label": "garage", "wall_height_ft": 9.5,
             "gable_ends": 1}
        ],
        "_dim_evidence": {
            "roof_planes.garage.wall_height_ft": {
                "v": 9.5, "page": 1,
                "from": "9'-6\" garage wall"}
        },
        "_ocr_quote_misses": [{
            "path": "roof_planes.garage.wall_height_ft", "page": 1,
            "from": "9'-6\" garage wall", "rotations_checked": True,
            "reason": ("quote matched but no candidate within 1500px "
                       "of feature anchor ['GARAGE']"),
        }],
    }
    _null_unverified_quotes(raw)
    assert raw["roof_planes"][0]["wall_height_ft"] is None
    unv = raw.get("_dim_unverified") or []
    assert any(r["path"] == "roof_planes.garage.wall_height_ft"
               for r in unv)


def test_null_unverified_leaves_located_srcs_alone():
    """A derived src[] with SOME locates is not nulled — a partial
    evidence chain still carries evidence and stays."""
    raw = {
        "walls": [{"label": "front", "height_ft": 20.0}],
        "_dim_evidence": {
            "walls.front.height_ft": {
                "v": 20.0, "calc": "9-11 + 8-1",
                "srcs": [
                    {"page": 1, "from": "9'-11\"",
                     "loc": {"x_pct": 5, "y_pct": 5,
                             "w_pct": 1, "h_pct": 1},
                     "precision": "ocr"},
                    {"page": 1, "from": "8'-1\""},  # unlocated
                ]}
        },
        "_ocr_quote_misses": [{
            "path": "walls.front.height_ft", "page": 1,
            "from": "8'-1\"", "rotations_checked": True,
            "reason": "quote not found on page",
        }],
    }
    _null_unverified_quotes(raw)
    # walls.front.height_ft still has a located src — do not null.
    assert raw["walls"][0]["height_ft"] == 20.0


# ---------- (D) send-6 hole closed ----------

def test_send6_per_plane_fields_walk_the_evidence_pipeline():
    """SEND-8 REGRESSION CLOSER: the per-plane wall_height_ft and
    overhang_in I added on SEND-6 must enter `_normalize_evidence`
    like every other dim, so the locator can actually see them."""
    from routes.ai_blueprint import _enforce_evidence_or_null
    raw = {
        "roof_planes": [
            {"label": "garage",
             "overhang_in": {"v": 12, "page": 11, "from": "1'-0\""},
             "wall_height_ft": {"v": 9.5, "page": 1,
                                "from": "9'-6\" garage wall"}},
        ],
    }
    _enforce_evidence_or_null(raw)
    ev = raw.get("_dim_evidence") or {}
    assert "roof_planes.garage.overhang_in" in ev
    assert "roof_planes.garage.wall_height_ft" in ev
    # And the value normalises to a plain number.
    assert raw["roof_planes"][0]["overhang_in"] == 12
    assert raw["roof_planes"][0]["wall_height_ft"] == 9.5
