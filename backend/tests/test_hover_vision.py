"""Iter 78p — Phase 2 vision verification logic unit tests.

These cover the deterministic parts of `hover_vision`: page detection,
JSON parsing, and warning-building. The actual Claude Vision call is
NOT exercised here (would require a real HOVER PDF + live API). Live
testing happens on the user's next real HOVER upload — the wiring is
defensive (every external call is wrapped in try/except so a vision
failure never breaks the import).
"""
import io

import fitz  # PyMuPDF

from routes.hover_vision import (
    _ELEV_RE,
    _build_warnings,
    _json_from_reply,
    _pct_delta,
    _render_pdf_pages,
)


def test_elev_re_matches_standard_labels():
    assert _ELEV_RE.search("FRONT ELEVATION") is not None
    assert _ELEV_RE.search("Left Elevation") is not None
    assert _ELEV_RE.search("Side A Elevation") is not None
    assert _ELEV_RE.search("Rear Elevation") is not None


def test_elev_re_ignores_unrelated():
    assert _ELEV_RE.search("Roof Plan") is None
    assert _ELEV_RE.search("Window Schedule") is None
    assert _ELEV_RE.search("Front Door") is None  # no "Elevation"


def test_json_from_reply_fenced():
    reply = '```json\n{"a": 1, "b": "x"}\n```'
    assert _json_from_reply(reply) == {"a": 1, "b": "x"}


def test_json_from_reply_with_preface():
    reply = 'Here is the result:\n{"facade_width_ft": 30}'
    assert _json_from_reply(reply) == {"facade_width_ft": 30}


def test_json_from_reply_garbage():
    assert _json_from_reply("not json at all") == {}
    assert _json_from_reply("") == {}


def test_pct_delta_basics():
    # 10 / max(100, 110) × 100 = 9.09%
    assert abs(_pct_delta(100, 110) - 9.0909) < 0.01
    assert _pct_delta(0, 0) == 0
    assert _pct_delta(0, 50) == 100
    assert _pct_delta(100, 100) == 0


def _make_pdf_with_label(label: str) -> bytes:
    """Build a tiny PDF containing one page with the given text label so
    we can exercise `_render_pdf_pages` without shipping a real HOVER."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # US Letter
    page.insert_text((72, 100), label, fontsize=24)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_render_pdf_pages_finds_elevation():
    pdf = _make_pdf_with_label("Front Elevation")
    pages = _render_pdf_pages(pdf)
    assert len(pages) == 1
    assert pages[0]["label"] == "Front"
    assert pages[0]["png_bytes"]


def test_render_pdf_pages_skips_non_elevation():
    pdf = _make_pdf_with_label("Roof Plan")
    pages = _render_pdf_pages(pdf)
    assert pages == []


def test_render_pdf_pages_caps_at_six():
    """Even if the PDF has many elevation pages, only `MAX_ELEVATION_PAGES`
    should render (cost control)."""
    # Real HOVER reports can have up to 8 distinct elevation labels
    # (Front, Back, Left, Right, Side A–D). Stuff 8 in to verify the cap.
    labels = ["Front", "Back", "Left", "Right",
              "Side A", "Side B", "Side C", "Side D"]
    doc = fitz.open()
    for lbl in labels:
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 100), f"{lbl} Elevation", fontsize=24)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    pages = _render_pdf_pages(buf.getvalue())
    assert len(pages) == 6


def test_render_pdf_pages_handles_bad_pdf():
    assert _render_pdf_pages(b"not a pdf") == []


def test_build_warnings_flags_per_elevation_mismatch():
    vision_results = [
        {"elevation_label": "Front", "siding_sqft": 600,
         "gross_wall_sqft": 700, "confidence": "high"},
    ]
    measurements = {
        "siding_sqft": 1000,
        "per_elevation_siding": {"Front": 500},
    }
    warns = _build_warnings(vision_results, measurements)
    codes = {w["code"] for w in warns}
    assert "vision_elev_delta_front" in codes


def test_build_warnings_no_flag_when_close():
    vision_results = [
        {"elevation_label": "Front", "siding_sqft": 505,
         "gross_wall_sqft": 600, "confidence": "high"},
    ]
    measurements = {
        "siding_sqft": 500,
        "per_elevation_siding": {"Front": 500},
    }
    warns = _build_warnings(vision_results, measurements)
    codes = {w["code"] for w in warns}
    assert "vision_elev_delta_front" not in codes


def test_build_warnings_flags_total_delta():
    """Even without per-elevation breakdown, total siding drawing-vs-text
    delta should be flagged."""
    vision_results = [
        {"elevation_label": "Front", "siding_sqft": 800, "gross_wall_sqft": 800, "confidence": "high"},
        {"elevation_label": "Back", "siding_sqft": 800, "gross_wall_sqft": 800, "confidence": "high"},
    ]
    measurements = {"siding_sqft": 1000}  # drawings sum 1600 vs text 1000
    warns = _build_warnings(vision_results, measurements)
    codes = {w["code"] for w in warns}
    assert "vision_total_delta" in codes


def test_build_warnings_info_when_no_text_total():
    """If text didn't extract siding_sqft, we still surface what the
    drawings showed (info-level)."""
    vision_results = [
        {"elevation_label": "Front", "siding_sqft": 600, "gross_wall_sqft": 700, "confidence": "high"},
    ]
    warns = _build_warnings(vision_results, {})
    codes = {w["code"] for w in warns}
    assert "vision_drawings_sum_info" in codes
    assert next(w for w in warns if w["code"] == "vision_drawings_sum_info")["level"] == "info"


# ─── Iter 78q — Phase 3 Deep Verify reconcile tests ─────────────────────────
from routes.hover_vision import reconcile_deep_verify  # noqa: E402


def test_reconcile_deep_verify_3way_compare():
    deep = {
        "label": "Front",
        "scale_bar_found": True,
        "scale_bar_label_ft": 20,
        "measured_width_ft": 30,
        "measured_height_ft": 18,
        "measured_gross_wall_sqft": 540,
        "confidence": "high",
        "notes": "",
    }
    measurements = {"per_elevation_siding": {"Front": 500}}
    phase2 = {"gross_wall_sqft": 600, "siding_sqft": 540}
    out = reconcile_deep_verify(deep, measurements, phase2)
    assert out["label"] == "Front"
    assert out["measured_gross_wall_sqft"] == 540
    assert out["phase2_gross_wall_sqft"] == 600
    assert out["text_area_sqft"] == 500
    # Delta vs phase2 gross 600: |540-600|/600 = 10%
    assert out["delta_vs_phase2"] == "Δ 10%"
    # Delta vs text 500: |540-500|/540 = 7%
    assert out["delta_vs_text"] == "Δ 7%"
    assert out["scale_bar_found"] is True


def test_reconcile_deep_verify_no_text_area():
    """When text didn't break out per-elevation, text_area = 0 and the
    delta_vs_text shows as a dash."""
    deep = {
        "label": "Front",
        "scale_bar_found": True,
        "measured_gross_wall_sqft": 540,
    }
    out = reconcile_deep_verify(deep, {}, {"gross_wall_sqft": 600})
    assert out["text_area_sqft"] == 0
    assert out["delta_vs_text"] == "—"
    assert out["delta_vs_phase2"] == "Δ 10%"


# ─── Iter 78r — extended cross-check tests ──────────────────────────────────


def test_eaves_delta_flagged_when_sum_diverges():
    """Drawings sum to 150 LF of facade widths but text says 100 LF eaves."""
    vision_results = [
        {"elevation_label": "Front", "facade_width_ft": 50, "siding_sqft": 0, "gross_wall_sqft": 0},
        {"elevation_label": "Back",  "facade_width_ft": 50, "siding_sqft": 0, "gross_wall_sqft": 0},
        {"elevation_label": "Left",  "facade_width_ft": 25, "siding_sqft": 0, "gross_wall_sqft": 0},
        {"elevation_label": "Right", "facade_width_ft": 25, "siding_sqft": 0, "gross_wall_sqft": 0},
    ]
    warns = _build_warnings(vision_results, {"eaves_lf": 100})
    codes = {w["code"] for w in warns}
    assert "vision_eaves_delta" in codes


def test_eaves_no_flag_when_close():
    vision_results = [
        {"elevation_label": "Front", "facade_width_ft": 26, "siding_sqft": 0, "gross_wall_sqft": 0},
        {"elevation_label": "Back",  "facade_width_ft": 26, "siding_sqft": 0, "gross_wall_sqft": 0},
        {"elevation_label": "Left",  "facade_width_ft": 25, "siding_sqft": 0, "gross_wall_sqft": 0},
        {"elevation_label": "Right", "facade_width_ft": 25, "siding_sqft": 0, "gross_wall_sqft": 0},
    ]
    warns = _build_warnings(vision_results, {"eaves_lf": 100})  # drawings: 102
    codes = {w["code"] for w in warns}
    assert "vision_eaves_delta" not in codes


def test_rakes_delta_flagged():
    """Drawings show 80 LF of rake but text says 50."""
    vision_results = [
        {"elevation_label": "Left",  "rake_lf_on_face": 40, "siding_sqft": 0, "gross_wall_sqft": 0, "facade_width_ft": 0},
        {"elevation_label": "Right", "rake_lf_on_face": 40, "siding_sqft": 0, "gross_wall_sqft": 0, "facade_width_ft": 0},
    ]
    warns = _build_warnings(vision_results, {"rakes_lf": 50})
    codes = {w["code"] for w in warns}
    assert "vision_rakes_delta" in codes


def test_overhang_delta_flagged():
    """Job uses 12" overhang (=1 ft) but drawings label 24" (=2 ft)."""
    vision_results = [
        {"elevation_label": "Front", "soffit_depth_ft": 2.0, "siding_sqft": 0, "gross_wall_sqft": 0, "facade_width_ft": 0},
    ]
    warns = _build_warnings(vision_results, {"overhang_in": 12})
    codes = {w["code"] for w in warns}
    assert "vision_overhang_delta" in codes


def test_window_count_delta_flagged():
    """Drawings show 10 distinct labeled windows but text says 5."""
    vision_results = [
        {"elevation_label": "Front",
         "window_dims": [{"width_ft": 3, "height_ft": 4} for _ in range(10)],
         "siding_sqft": 0, "gross_wall_sqft": 0, "facade_width_ft": 0},
    ]
    warns = _build_warnings(vision_results, {"window_count": 5})
    codes = {w["code"] for w in warns}
    assert "vision_window_count_delta" in codes


def test_window_perim_delta_flagged():
    """Drawings labeled 4 windows at 4'×5' (= 18 LF perim each, total 72)
    but text windows[] has them at 3'×4' (= 14 LF perim, total 56). Delta = 22%."""
    vision_results = [
        {"elevation_label": "Front",
         "window_dims": [{"width_ft": 4, "height_ft": 5} for _ in range(4)],
         "siding_sqft": 0, "gross_wall_sqft": 0, "facade_width_ft": 0},
    ]
    text_windows = [{"width_in": 36, "height_in": 48} for _ in range(4)]
    warns = _build_warnings(vision_results, {"windows": text_windows})
    codes = {w["code"] for w in warns}
    assert "vision_window_perim_delta" in codes


def test_extended_checks_silent_when_drawings_omit_fields():
    """If Phase 2 didn't extract rake/soffit/window data, no new warnings fire."""
    vision_results = [
        {"elevation_label": "Front", "siding_sqft": 500, "gross_wall_sqft": 500, "facade_width_ft": 0},
    ]
    warns = _build_warnings(vision_results, {
        "eaves_lf": 100, "rakes_lf": 100, "overhang_in": 12,
        "windows": [{"width_in": 36, "height_in": 48}],
    })
    extended_codes = {"vision_eaves_delta", "vision_rakes_delta",
                      "vision_overhang_delta", "vision_window_count_delta",
                      "vision_window_perim_delta"}
    assert extended_codes.isdisjoint({w["code"] for w in warns})


