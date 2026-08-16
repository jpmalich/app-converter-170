"""SEND-30 (Howard sealed 2026-08-16) — coverage + geometry pins.

  1. Rotated-pass runs persist with src + axis tags, boxes mapped back
     to upright page coordinates.
  2. OCR reads EVERY page — the page filter (OCR only where the model
     quoted) is dead; a page with no quotes still persists its runs.
  CORRECTION 1: the axis ratio is normalized by glyph count — raw w/h
     measures string length, not orientation. Verified to separate on
     the full Boni p6 set (21 dim-like runs + the four key strings)
     with ZERO overlap; both 58'-0" rails class HORIZONTAL.
     INDETERMINATE stays first-class (reachable, not impossible).
  CORRECTION 2: the rail-envelope interior/exterior test is 2D — a side
     depth chain (outside on x, inside on y) must class EXTERIOR; a
     y-only envelope would delete the very depths the anchor needs.
     Envelope not establishable → INDETERMINATE, never a default.
  ITEM 5: the positional rule probe REPORTS and never binds.
"""
import io
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, "/app/backend")

import ocr_geometry as og
import routes.ai_blueprint as bp


# ---------------------------------------------------------------------------
# CORRECTION 1 — glyph-normalized axis classifier
# ---------------------------------------------------------------------------

# The verified set: every dimension-like run reported on Boni p6
# (SEND-29) plus the four key strings. (raw, w_pct, h_pct, truth).
_P6_VERIFIED = [
    ("MIN.9'-11/8\"CEILINGHEIGHTONFIRSTFLOOR", 14.67, 1.13, og.HORIZONTAL),
    ("MIN.8'-11/8CEILINGHEIGHTONSECONDFLOOR", 15.52, 1.06, og.HORIZONTAL),
    ("3'-0°", 1.11, 0.80, og.HORIZONTAL),
    ("7'-0°", 0.91, 0.80, og.HORIZONTAL),
    ("15'-0*", 1.11, 0.73, og.HORIZONTAL),
    ("3'-10", 0.55, 1.53, og.VERTICAL),
    ("5'-9%\"", 1.46, 1.00, og.HORIZONTAL),
    ("5'-0", 1.01, 0.80, og.HORIZONTAL),
    ("4'-4°", 0.86, 0.80, og.HORIZONTAL),
    ("5'-0°", 1.06, 0.80, og.HORIZONTAL),
    ("5'0°", 0.86, 0.73, og.HORIZONTAL),
    ("3'-1%", 0.50, 1.73, og.VERTICAL),
    ("3'-0*", 0.55, 1.26, og.VERTICAL),
    ("2'-8", 1.01, 0.80, og.HORIZONTAL),
    ("14'-2*", 0.55, 1.53, og.VERTICAL),
    ("5'-6*", 1.06, 0.80, og.HORIZONTAL),
    ("2'-6°", 1.06, 1.00, og.HORIZONTAL),
    ("16'-0°x8-0*", 2.12, 0.80, og.HORIZONTAL),
    ("9-0°x8'0°", 2.27, 0.93, og.HORIZONTAL),
    ("6'6”", 1.51, 1.00, og.HORIZONTAL),
    ("SCALE:3/16\"=1'-0\"", 6.80, 1.06, og.HORIZONTAL),
    # The four key strings — the discriminator Howard named:
    ("58-0°", 1.31, 0.93, og.HORIZONTAL),   # top width rail (raw ratio 1.41 — below any raw threshold)
    ("58-0°", 1.46, 1.20, og.HORIZONTAL),   # bottom width rail (raw ratio 1.22)
    ("33-11%", 1.92, 0.93, og.HORIZONTAL),  # the interior width
    ("33-5%*", 1.71, 1.00, og.HORIZONTAL),  # the front width segment
]


def _axis(raw, w, h):
    return og.axis_class({"w_pct": w, "h_pct": h}, og.glyph_count(raw))


def test_correction1_separates_the_full_verified_set_zero_overlap():
    # Every run classes to its truth and NONE lands INDETERMINATE —
    # the metric separates; the data was never ambiguous.
    for raw, w, h, truth in _P6_VERIFIED:
        assert _axis(raw, w, h) == truth, (raw, w, h)


def test_correction1_both_58_rails_move_to_horizontal():
    # The raw ratios (1.41, 1.22) sat below the old 1.5 threshold and
    # classed INDETERMINATE. Normalized by glyph count they are plainly
    # HORIZONTAL — the failure that named the correction.
    assert _axis("58-0°", 1.31, 0.93) == og.HORIZONTAL
    assert _axis("58-0°", 1.46, 1.20) == og.HORIZONTAL


def test_correction1_axis_filter_alone_kills_both_wrong_anchor_candidates():
    assert _axis("33-11%", 1.92, 0.93) == og.HORIZONTAL
    assert _axis("33-5%*", 1.71, 1.00) == og.HORIZONTAL


def test_correction1_cuts_sit_inside_the_observed_gap():
    # Verticals top out at 0.087, horizontals start at 0.212 on the
    # verified set; the pinned cuts sit strictly inside that gap.
    assert 0.087 < og.AXIS_VERTICAL_MAX < og.AXIS_HORIZONTAL_MIN < 0.212


def test_correction1_indeterminate_stays_first_class():
    # A classifier that never says "I cannot tell" is the coin flip
    # again. A box in the gap band must land INDETERMINATE.
    assert og.axis_class({"w_pct": 0.15, "h_pct": 1.0}, 1) == og.INDETERMINATE
    # Degenerate inputs refuse too — never a guessed axis.
    assert og.axis_class({"w_pct": 0, "h_pct": 1.0}, 5) == og.INDETERMINATE
    assert og.axis_class({"w_pct": 1.0, "h_pct": 1.0}, 0) == og.INDETERMINATE


# ---------------------------------------------------------------------------
# CORRECTION 2 — 2D rail envelope
# ---------------------------------------------------------------------------

def _run(raw, x, y, w, h, axis):
    return {"norm": raw, "raw": raw,
            "loc": {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h},
            "src": "upright", "axis": axis}


def _rails_fixture():
    return [
        _run("58'-0\"", 50.0, 18.0, 1.5, 1.0, og.HORIZONTAL),   # top width rail
        _run("58'-0\"", 50.0, 70.0, 1.5, 1.0, og.HORIZONTAL),   # bottom width rail
        _run("30'-2\"", 7.0, 40.0, 0.6, 1.6, og.VERTICAL),      # left depth rail
        _run("33'-0\"", 80.0, 44.0, 0.6, 1.6, og.VERTICAL),     # right depth rail
    ]


def test_correction2_envelope_established_from_the_four_rails():
    env = og.rail_envelope(_rails_fixture())
    assert env["status"] == "ESTABLISHED"
    assert env["x_lo"] == pytest.approx(7.6)
    assert env["x_hi"] == pytest.approx(80.0)
    assert env["y_lo"] == pytest.approx(19.0)
    assert env["y_hi"] == pytest.approx(70.0)


def test_correction2_interior_means_inside_on_both_axes():
    env = og.rail_envelope(_rails_fixture())
    inner = _run("33'-11 1/2\"", 45.0, 40.0, 1.9, 0.9, og.HORIZONTAL)
    assert og.interior_exterior(inner, env) == og.INTERIOR


def test_correction2_side_depth_chain_is_exterior_not_interior():
    # THE INVERSION GUARD: a side depth sits outside the footprint on x
    # while its y falls between the width rails. y-only would call it
    # INTERIOR and delete the very dimension the anchor needs.
    env = og.rail_envelope(_rails_fixture())
    depth = _run("33'-0\"", 85.0, 40.0, 0.6, 1.6, og.VERTICAL)
    assert og.interior_exterior(depth, env) == og.EXTERIOR
    # The rails themselves are exterior dimensions.
    assert og.interior_exterior(_rails_fixture()[3], env) == og.EXTERIOR


def test_correction2_missing_rail_means_indeterminate_never_a_default():
    runs = _rails_fixture()[:3]  # right depth rail missing
    env = og.rail_envelope(runs)
    assert env["status"] == og.INDETERMINATE
    assert "vertical" in env["reason"]
    dead_center = _run("5'-0\"", 45.0, 45.0, 1.0, 0.8, og.HORIZONTAL)
    # Neither default-to-exterior nor default-to-interior.
    assert og.interior_exterior(dead_center, env) == og.INDETERMINATE


def test_correction2_crossing_rails_refuse_the_envelope():
    runs = [
        _run("10'-0\"", 50.0, 40.0, 1.5, 1.0, og.HORIZONTAL),
        _run("12'-0\"", 50.0, 40.5, 1.5, 1.0, og.HORIZONTAL),
        _run("8'-0\"", 40.0, 30.0, 0.6, 1.6, og.VERTICAL),
        _run("9'-0\"", 40.2, 50.0, 0.6, 1.6, og.VERTICAL),
    ]
    env = og.rail_envelope(runs)
    assert env["status"] == og.INDETERMINATE
    assert "cross" in env["reason"]


# ---------------------------------------------------------------------------
# ITEM 5 — the positional rule probe REPORTS, never binds
# ---------------------------------------------------------------------------

def test_probe_reports_chosen_and_contenders_and_never_binds():
    runs = _rails_fixture() + [
        _run("3 CAR GARAGE", 66.0, 44.0, 4.3, 1.1, og.HORIZONTAL),
        _run("14'-2\"", 61.5, 52.0, 0.6, 1.5, og.VERTICAL),  # interior on x
        _run("33'-0\"", 85.0, 40.0, 0.6, 1.6, og.VERTICAL),  # outboard depth
    ]
    rep = og.positional_rule_probe(runs)
    assert rep["binds"] is False
    assert rep["envelope"]["status"] == "ESTABLISHED"
    assert any(l["side"] == "right" for l in rep["labels"])
    right = rep["sides"]["right"]
    # Outermost vertical EXTERIOR on the garage side: the 85.0 depth —
    # it also becomes the envelope's right rail, so the 80.0 dim moves
    # inboard and classes INTERIOR.
    assert right["chosen"]["raw"] == "33'-0\""
    assert right["chosen"]["loc"]["x_pct"] == 85.0
    # What it nearly returned is VISIBLE, not silent: the interior
    # verticals on that side are listed, never quietly dropped.
    excluded = [e["raw"] for e in right["excluded_interior"]]
    assert "14'-2\"" in excluded
    assert "33'-0\"" in excluded  # the 80.0 dim, now inboard
    assert "14'-2\"" not in [c["raw"] for c in right["contenders"]]


def test_probe_indeterminate_envelope_is_a_real_answer():
    rep = og.positional_rule_probe([_rails_fixture()[0]])
    assert rep["result"] == og.INDETERMINATE
    assert rep["reason"]
    assert rep["binds"] is False


# ---------------------------------------------------------------------------
# ITEMS 1+2 — persistence contract of _ocr_locate_evidence
# ---------------------------------------------------------------------------

def test_map_rot_box_matches_the_pinned_inline_formulas():
    rect, w, h = (20, 8, 40, 13), 100, 80
    assert bp._map_rot_box(rect, 1, w, h) == (100 - 1 - 13, 20, 100 - 1 - 8, 40)
    assert bp._map_rot_box(rect, 3, w, h) == (8, 80 - 1 - 40, 13, 80 - 1 - 20)


def _page_payload(w=100, h=80):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def _fake_ocr_runs(arr):
    hh, ww = arr.shape[:2]
    if (ww, hh) == (100, 80):  # upright orientation
        return [("580", "58'-0\"", (10, 5, 30, 10))]
    return [("330", "33'-0\"", (20, 8, 40, 13))]  # rotated orientation


def test_every_page_persists_even_without_quotes(monkeypatch):
    # SEND-30 item 2: the page filter is dead. Page 2 carries no model
    # quote and STILL persists its runs — which pages get OCR'd is no
    # longer a function of what the model happened to say.
    monkeypatch.setattr(bp, "_ocr_runs", _fake_ocr_runs)
    evidence = {"walls.front.width_ft":
                {"srcs": [{"from": "58'-0\"", "page": 1, "precision": None}]}}
    raw = {}
    bp._ocr_locate_evidence(evidence, [_page_payload(), _page_payload()], raw)
    blob = raw["_ocr_text_by_page"]
    assert set(blob) == {"1", "2"}
    assert blob["2"]["runs"], "quote-less page must still persist its runs"
    # Coverage is visible for every page.
    assert set(raw["_ocr_page_coverage_chars"]) == {"1", "2"}


def test_rotated_runs_persist_with_src_axis_and_upright_mapped_boxes(monkeypatch):
    monkeypatch.setattr(bp, "_ocr_runs", _fake_ocr_runs)
    raw = {}
    bp._ocr_locate_evidence({}, [_page_payload()], raw)
    runs = raw["_ocr_text_by_page"]["1"]["runs"]
    srcs = sorted(r["src"] for r in runs)
    assert srcs == ["rot270", "rot90", "upright"]
    assert all("axis" in r for r in runs)
    rot90 = next(r for r in runs if r["src"] == "rot90")
    # (20,8,40,13) in rot90 coords maps to (86,20,91,40) upright on a
    # 100x80 page → x 86%, y 25%, w 5%, h 25% — tall-narrow, VERTICAL.
    assert rot90["loc"] == {"x_pct": 86.0, "y_pct": 25.0,
                            "w_pct": 5.0, "h_pct": 25.0}
    assert rot90["axis"] == og.VERTICAL
    up = next(r for r in runs if r["src"] == "upright")
    assert up["axis"] == og.HORIZONTAL  # wide-short 58'-0" box


def test_empty_evidence_still_reads_every_page(monkeypatch):
    # The old guard returned before any OCR when the model quoted
    # nothing at all. Coverage must not depend on the model.
    monkeypatch.setattr(bp, "_ocr_runs", _fake_ocr_runs)
    raw = {}
    bp._ocr_locate_evidence(None, [_page_payload()], raw)
    assert "1" in raw["_ocr_text_by_page"]
