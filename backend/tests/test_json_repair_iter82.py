"""Iter 79j.82 — blocking stability fix: lenient Phase A JSON parsing.
Both 1b void runs were 3.5KB end_turn responses judged 'empty' by the
strict parser. Pins the repair ladder + diagnosability contract."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import _clean_json_reply, _is_empty_extraction  # noqa: E402

VALID = '{"index": 5, "walls_visible": ["back", "right"], "eave_height_ft_observed": 8.85}'


def test_valid_json_passes_unrepaired():
    out = _clean_json_reply(VALID)
    assert out["index"] == 5 and "_json_repaired" not in out
    assert not _is_empty_extraction(out)


def test_trailing_prose_after_object():
    out = _clean_json_reply(VALID + "\n\nHope this helps! Let me know.")
    assert out["walls_visible"] == ["back", "right"]


def test_leading_prose_and_fences():
    out = _clean_json_reply("Here is the extraction:\n" + VALID)
    assert out["index"] == 5
    out = _clean_json_reply("```json\n" + VALID + "\n```")
    assert out["index"] == 5


def test_trailing_comma_repaired():
    out = _clean_json_reply('{"walls_visible": ["front",], "eave_height_ft_observed": 9.2,}')
    assert out["walls_visible"] == ["front"]
    assert out["_json_repaired"] is True


def test_unescaped_inch_quote_repaired():
    raw = '{"notes": "banner shows a 360" gable-end wall with min 4" clearance", "walls_visible": ["right"]}'
    out = _clean_json_reply(raw)
    assert out["walls_visible"] == ["right"]
    assert out["_json_repaired"] is True
    assert '360" gable-end' in out["notes"]


def test_unparseable_carries_parse_error_and_reads_empty():
    out = _clean_json_reply("I could not analyze this photo.")
    assert "_parse_error" in out
    assert _is_empty_extraction(out)
    out2 = _clean_json_reply('{"walls_visible": [unquoted garbage !!!')
    assert "_parse_error" in out2
    assert _is_empty_extraction(out2)


def test_escaped_inch_quotes_still_fine():
    raw = '{"elevation_reasoning": "a 360\\" gable-end wall faces camera", "walls_visible": ["right"]}'
    out = _clean_json_reply(raw)
    assert "_json_repaired" not in out
    assert '360"' in out["elevation_reasoning"]
