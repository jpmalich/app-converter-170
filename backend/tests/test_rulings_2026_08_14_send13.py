"""RULINGS REGISTER — SEND-13 (2026-08-14).

WHY THIS FILE EXISTS (the process fix Howard asked for). Three ruled items
have gone missing between sends because the register only reliably
captures a ruling that ARRIVES AS AN EXPLICIT ITEM — a rule stated inside
a paragraph, as a clause of an answer to another question, never became
its own pin, so nothing failed when it was not built and the handoff
carried it forward as "done". Segment-level partial derivability was ruled
as a clause of the front-segment answer and vanished exactly this way.

THE FIX, DEMONSTRATED HERE: every ruling in a send — numbered OR
mid-paragraph — enters the register the moment it is made, carrying the
ruling's WORDS in a docstring. A ruling that is HELD (cannot be built yet)
enters as a VISIBLE skip that names why, so a held ruling can never
silently evaporate: it shows up in every run as an un-built, on-the-record
ruling. The suite is the register; a ruling with no pin is a ruling that
does not exist to the next agent.

This file cross-checks that send-13's three rulings are on the record.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes.ai_blueprint as ab  # noqa: E402
from measure_staging import wall_body_gross_sqft  # noqa: E402


def test_ruling_1_shared_source_is_a_flag_not_a_kill():
    """RULING (send-13 §1): a shared printed quote is a REAL located
    dimension and OFTEN correct; it SURVIVES and feeds money, carrying a
    loud flag naming all consumers. AMENDED send-14 D: the front+back
    overall width is the legitimate opposing-facade share → PLAIN rail,
    not a conflict. Enforced in depth by test_send10/11; registered here
    so the ruling itself is on the record."""
    raw = {
        "walls": [{"label": "front", "width_ft": 58.0},
                  {"label": "back", "width_ft": 58.0}],
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 58.0, "page": 6, "from": "58'-0\""},
            "walls.back.width_ft": {"v": 58.0, "page": 6, "from": "58'-0\""},
        },
    }
    ab._one_source_one_path_guard(raw)
    assert raw["walls"][0]["width_ft"] == 58.0      # survives
    assert not raw.get("_dim_unverified")           # not a kill
    assert (raw["_dim_shared_source"][0]["conflicting"]) is False


def test_ruling_2_segment_level_partial_derivability_is_built():
    """RULING (ruled earlier as a clause of the front-segment answer,
    BUILT send-13 §2): a wall with one segment killed reports the known
    segment's area, names the other not-derivable, and the total is a
    subset — no all-or-nothing fallback to the top-level rectangle.
    Enforced in depth by test_segment_partial_derivability; registered
    here because THIS is the ruling that went missing three sends running.
    """
    w = {"label": "front", "width_ft": None, "height_ft": None,
         "height_segments": [
             {"label": "main", "width_ft": 20.0, "height_ft": 10.0},
             {"label": "wing", "width_ft": None, "height_ft": 10.0}]}
    gross, used, deriv = wall_body_gross_sqft(w)
    assert gross == 200.0 and deriv["subset"] is True
    assert deriv["not_derivable"][0]["label"] == "wing"


@pytest.mark.skip(reason=(
    "ruling:held: HELD RULING (send-13 §3 part 2, ON THE RECORD, NOT YET "
    "BUILT): a page mistyped schedule/cover that actually carries drawn "
    "geometry must be re-checked against its own feet-inch dimension-token "
    "count and treated as a drawing. WHAT WOULD UNHOLD IT: a REAL plan set "
    "with genuine schedule/cover pages to pick a non-invented threshold "
    "(Boni has none). The signal and a report already exist: "
    "ab._feet_inch_dim_tokens + scripts/drawn_geometry_token_report.py. "
    "Un-skip and pin the threshold when the real plan set arrives. This "
    "skip is the register refusing to let a held ruling vanish."))
def test_ruling_3_schedule_cover_content_override():
    raise AssertionError("held — see skip reason")
