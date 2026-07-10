"""Iter 79j.77 — count-boundary candidate 1: siding-start (not grade) is
the course-count origin. Pins the prompt contract so a regression can't
silently revert to grade-to-eave."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import _build_phase_a_prompt, PER_PHOTO_EXTRACT_PROMPT  # noqa: E402


def _prompt(**kw):
    defaults = dict(
        photo_idx=0, address=None, reference_dim=None,
        brick_course_in=None, siding_exposure_in=4.25,
        annotation_hint="",
    )
    defaults.update(kw)
    return _build_phase_a_prompt(**defaults)


def test_rule5_counts_from_siding_start_not_grade():
    p = PER_PHOTO_EXTRACT_PROMPT
    # Iter 79j.81 superseded the wording: boundary is now "first course
    # on the starter, at the top of the block line" (count-first contract)
    assert "the one on the starter" in p
    assert "siding start line" in p
    assert "COUNT the courses from grade" not in p
    assert "count lap courses from grade" not in p


def test_rule5_prohibition_covers_count_and_inches():
    flat = PER_PHOTO_EXTRACT_PROMPT.replace("\n   ", " ")
    assert "NEVER include exposed foundation" in flat
    assert "not in the course count and not as added inches" in flat
    assert "siding-start-to-eave, NOT grade-to-eave" in flat


def test_rule5_occlusion_fallback_never_grade():
    p = PER_PHOTO_EXTRACT_PROMPT
    assert "start_line_occluded" in p
    flat = p.replace("\n   ", " ")
    assert "never fall back to measuring from grade" in flat


def test_exposure_injection_line_uses_start_line():
    p = _prompt()
    # Iter 79j.81 superseded: injection now enumerates from the starter
    assert "first course on the starter (top of the block line)" in p
    assert "NEVER add exposed foundation/membrane/parging below the siding start" in p
    assert "never fall back to grade" in p


def test_schema_declares_start_line_occluded_field():
    assert '"start_line_occluded"' in PER_PHOTO_EXTRACT_PROMPT


def test_no_exposure_no_injection():
    p = _prompt(siding_exposure_in=None)
    assert "SIDING EXPOSURE =" not in p
