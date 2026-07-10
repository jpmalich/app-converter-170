"""Iter 79j.78 — empty-extraction diagnostics: when a Phase A response
is judged empty, the raw excerpt + stop_reason + text length persist on
the photo record so the failure class is diagnosable."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import _stamp_empty_diagnostics, _is_empty_extraction  # noqa: E402


def test_empty_extraction_persists_excerpt():
    parsed = {"index": 3, "walls_visible": [], "openings_this_photo": []}
    assert _is_empty_extraction(parsed)
    out = _stamp_empty_diagnostics(parsed, '{"walls_visible": []}', "end_turn")
    assert out["_stop_reason"] == "end_turn"
    assert out["_raw_text_len"] == len('{"walls_visible": []}')
    assert out["_raw_response_excerpt"] == '{"walls_visible": []}'


def test_non_empty_extraction_skips_excerpt():
    parsed = {"index": 0, "walls_visible": ["front"], "eave_height_ft_observed": 9.6}
    assert not _is_empty_extraction(parsed)
    long_text = "x" * 1000
    out = _stamp_empty_diagnostics(parsed, long_text, "end_turn")
    assert "_raw_response_excerpt" not in out
    assert out["_raw_text_len"] == 1000


def test_excerpt_capped_at_400_chars():
    parsed = {"index": 1, "walls_visible": []}
    out = _stamp_empty_diagnostics(parsed, "y" * 5000, "max_tokens")
    assert len(out["_raw_response_excerpt"]) == 400
    assert out["_stop_reason"] == "max_tokens"


def test_none_stop_reason_and_empty_text():
    parsed = {"index": 2, "walls_visible": []}
    out = _stamp_empty_diagnostics(parsed, "", None)
    assert out["_stop_reason"] is None
    assert out["_raw_text_len"] == 0
    assert out["_raw_response_excerpt"] == ""
