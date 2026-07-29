"""hover_vision after the 2026-07-29 retirement (Howard's ruling).

Phase 2 vision-verify + Phase 3 Deep Verify are RETIRED — the straight-on
S2 elevation read (hover_elevation_read.py) is the single verification
pass. This module keeps only the legacy-format page renderer + JSON
helper the S2 read imports. These tests pin the survivors AND the
retirement itself.
"""
import sys
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND = Path(__file__).resolve().parent.parent

from routes import hover_vision  # noqa: E402
from routes.hover_vision import (  # noqa: E402
    _ELEV_RE,
    _json_from_reply,
    _render_pdf_pages,
)


def test_elev_re_matches_legacy_labels():
    assert _ELEV_RE.search("FRONT ELEVATION") is not None
    assert _ELEV_RE.search("Left Elevation") is not None
    assert _ELEV_RE.search("Side A Elevation") is not None
    assert _ELEV_RE.search("Rear Elevation") is not None


def test_elev_re_ignores_current_format_and_unrelated():
    # current Hover format uses bare compass tokens — the LEGACY finder
    # does not match them; hover_elevation_read._find_view_pages does.
    assert _ELEV_RE.search("FRONT") is None
    assert _ELEV_RE.search("FRONT-RIGHT") is None
    assert _ELEV_RE.search("Roof Measurements") is None
    assert _ELEV_RE.search("Elevation Certificate") is None


def test_render_pdf_pages_finds_legacy_pages_only():
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((72, 72), "Front Elevation")
    p = doc.new_page()
    p.insert_text((72, 72), "OPENINGS Windows")
    pages = _render_pdf_pages(doc.tobytes())
    assert [(pg["page_num"], pg["label"]) for pg in pages] == [(1, "Front")]


def test_json_from_reply_strips_fences_and_preface():
    assert _json_from_reply('```json\n{"a": 1}\n```') == {"a": 1}
    assert _json_from_reply('Here you go:\n{"b": 2} trailing') == {"b": 2}
    assert _json_from_reply("no json here") == {}
    assert _json_from_reply("") == {}


def test_deep_verify_is_retired():
    """RETIREMENT PIN: the retired surface must not creep back. Scale-bar
    pixel re-derivation was deliberately NOT carried over — a pixel-derived
    number arguing with a printed callout reopens the sealed provenance
    door."""
    for name in ("run_vision_pass", "deep_verify_elevation",
                 "reconcile_deep_verify", "_build_warnings",
                 "_read_one_elevation", "VISION_PROMPT",
                 "DEEP_VERIFY_PROMPT"):
        assert not hasattr(hover_vision, name), f"{name} must stay retired"
    hover_src = (BACKEND / "routes" / "hover.py").read_text()
    assert "hover-deep-verify" not in hover_src
    assert "hover_page_cache" not in hover_src
    assert "deep_verify_cache_key" not in hover_src
    # the replacement is wired: S2 read at import, results on the run doc
    assert "read_elevation_geometry" in hover_src
    assert '"elevation_read": elevation_read' in hover_src
    startup_src = (BACKEND / "startup.py").read_text()
    assert "hover_page_cache.create_index" not in startup_src
    fe = Path("/app/frontend/src/components/estimate/HoverImportButton.jsx").read_text()
    assert "runDeepVerify" not in fe and "deep_verify_cache_key" not in fe
