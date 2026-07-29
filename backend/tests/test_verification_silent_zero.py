"""SILENT-ZERO-VERIFICATION DETECTOR — sealed by Howard 2026-07-29.

THE CLASS (verification_integrity_register.md): A VERIFICATION STEP THAT
FINDS NOTHING MUST NOT RENDER AS A PASS. Found via the 92-of-92 audit:
the Phase 2/Deep Verify page finder matched only "<label> Elevation"
titles; the current Hover format uses bare compass tokens — every
surviving run doc (incl. every real import) carried ZERO drawing pages
and the import rendered CLEAN, no banner, no named state, since 24 June.

Detector, not a note: these pins fail the suite if a verification pass
regains the ability to find nothing silently.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND = Path(__file__).resolve().parent.parent
REGISTER = Path("/app/memory/verification_integrity_register.md")


def test_zero_page_vision_pass_is_loud_on_the_import():
    """The hover worker MUST append a named warning when the vision pass
    yields no per-elevation data (zero pages / all calls failed) AND when
    it raises — never a silent except-pass."""
    src = (BACKEND / "routes" / "hover.py").read_text()
    assert src.count('"code": "vision_zero_pages"') >= 2, (
        "both the empty-result branch and the exception branch must emit "
        "the vision_zero_pages warning")
    assert "DRAWING VERIFICATION DID NOT RUN" in src
    # the warning lands in the same `warnings` list the import result
    # carries — the UI banner renders result.warnings unconditionally
    block = src.split('vision_warns, per_elev_drawing = await run_vision_pass')[1][:2000]
    assert 'warnings.append' in block


def test_s2_elevation_read_zero_pages_is_named_not_empty():
    """The S2 straight-on read returns a NAMED error state on zero pages
    — never an empty-but-ok shape."""
    from routes.hover_elevation_read import read_elevation_geometry  # noqa: F401
    src = (BACKEND / "routes" / "hover_elevation_read.py").read_text()
    assert '"error": "no elevation pages found in the PDF"' in src


def test_register_carries_the_named_class():
    text = REGISTER.read_text()
    flat = " ".join(text.split()).lower()
    assert "silent-zero-verification" in flat
    assert "92" in text and "must not render as a pass" in flat


def test_no_bare_except_pass_around_verification_calls():
    """No verification call site may swallow its failure without emitting
    a warning: every `except` in the vision-verify stage names the class."""
    src = (BACKEND / "routes" / "hover.py").read_text()
    stage = src.split('await _set_stage("vision-verify")')[1]
    stage = stage.split("result_payload = {")[0]
    for m in re.finditer(r"except Exception as e:", stage):
        window = stage[m.end():m.end() + 500]
        assert "vision_zero_pages" in window or "warnings.append" in window, (
            "vision-verify stage swallows a failure without a named warning")
