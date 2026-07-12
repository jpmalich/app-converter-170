"""Iter 79j.82 — empty class 3 (per-photo LLM timeout) salvage pass.
A photo killed by the per-photo budget or the wave cap gets ONE
sequential retry with a fresh budget, outside the wave scheduler.
Recovered photos flow into Phase B with real data + a
`_timeout_retry_attempted` provenance stamp."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))



def test_salvage_retry_recovers_timed_out_photo(monkeypatch):
    asyncio.run(_salvage_body(monkeypatch))


async def _salvage_body(monkeypatch):
    from routes import ai_measure

    monkeypatch.setenv("AI_MEASURE_PER_PHOTO_TIMEOUT", "2")
    monkeypatch.setenv("AI_MEASURE_TIMEOUT_RETRY_BUDGET", "15")

    attempts = {"1": 0}

    async def fake_extract_one_photo(*, photo_idx, raw_bytes, **_kw):
        if photo_idx == 0:
            return {
                "index": 0, "_photo_idx": 0,
                "walls_visible": ["front"],
                "eave_height_ft_observed": 9.0,
            }
        attempts["1"] += 1
        if attempts["1"] == 1:
            await asyncio.sleep(10)  # first attempt hangs past the 2s budget
        return {
            "index": 1, "_photo_idx": 1,
            "walls_visible": ["right"],
            "eave_height_ft_observed": 8.1,
        }

    async def fake_reconcile(*, extractions, **_kw):
        # BOTH photos reach Phase B with real data — no empties.
        assert len(extractions) == 2
        assert not [e for e in extractions if e.get("_empty_extraction")]
        return {"walls": [], "openings": [], "photos": []}

    async def set_stage(stage):
        pass

    monkeypatch.setattr(ai_measure, "_extract_one_photo", fake_extract_one_photo)
    monkeypatch.setattr(ai_measure, "_reconcile_extractions", fake_reconcile)
    monkeypatch.setattr(ai_measure, "db", AsyncMock())

    # live-module call — see test_phase_a_resilience note on stale bindings
    final, extractions = await ai_measure._run_two_phase_pipeline(
        run_id="test-salvage-xyz",
        api_key="test-key",
        user_id="test-user",
        image_payloads=[("image/jpeg", b"p0"), ("image/jpeg", b"p1")],
        model_provider="anthropic",
        model_name="claude-3-5-sonnet-20241022",
        address=None,
        reference_dim=None,
        brick_course_in=None,
        siding_exposure_in=None,
        annotation_hint="",
        set_stage=set_stage,
    )

    assert attempts["1"] == 2, "salvage pass must retry the timed-out photo exactly once"
    assert extractions[1].get("walls_visible") == ["right"]
    assert extractions[1].get("_timeout_retry_attempted") is True
    assert not extractions[1].get("_empty_extraction")
    assert not extractions[1].get("_extraction_error")
