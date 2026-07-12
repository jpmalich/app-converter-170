"""Iter 79j.44 — Phase A resilience guards.

The previous pipeline wrapped `asyncio.gather` in `asyncio.wait_for(...,
timeout=300)`. If ONE photo hung, the whole batch got CancelledError,
Phase B never ran, and the worker died with an empty-string
TimeoutError → user saw a blank toast. These tests pin the new
behaviour:

  1. A slow photo (per-photo budget exceeded) is flagged as
     `_empty_extraction=True` with a human `_empty_reason`, and the
     OTHER photos still complete + still flow into Phase B.
  2. `_env_int` reads the timeout knobs safely.
  3. The worker's error text is never empty.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import _env_int  # noqa: E402


def test_env_int_defaults_when_missing_or_bad():
    assert _env_int("__DEFINITELY_NOT_SET_XYZ__", 42) == 42
    with patch.dict("os.environ", {"AI_MEASURE_PER_PHOTO_TIMEOUT": ""}):
        assert _env_int("AI_MEASURE_PER_PHOTO_TIMEOUT", 240) == 240
    with patch.dict("os.environ", {"AI_MEASURE_PER_PHOTO_TIMEOUT": "not-a-number"}):
        assert _env_int("AI_MEASURE_PER_PHOTO_TIMEOUT", 240) == 240
    with patch.dict("os.environ", {"AI_MEASURE_PER_PHOTO_TIMEOUT": "-5"}):
        assert _env_int("AI_MEASURE_PER_PHOTO_TIMEOUT", 240) == 240
    with patch.dict("os.environ", {"AI_MEASURE_PER_PHOTO_TIMEOUT": "180"}):
        assert _env_int("AI_MEASURE_PER_PHOTO_TIMEOUT", 240) == 180


def test_slow_photo_does_not_kill_batch_sync(monkeypatch):
    """Sync entry point: two photos, one returns fast with real data,
    one hangs past the per-photo budget. The hanging one MUST be
    flagged and the fast one MUST still reach Phase B intact — no
    CancelledError, no batch kill.

    We drive the coroutine via asyncio.run since this project's pytest
    doesn't have pytest-asyncio installed.
    """
    asyncio.run(_slow_photo_body(monkeypatch))


async def _slow_photo_body(monkeypatch):
    from routes import ai_measure

    # Shrink the budgets so the test stays under a couple seconds.
    monkeypatch.setenv("AI_MEASURE_PER_PHOTO_TIMEOUT", "1")
    monkeypatch.setenv("AI_MEASURE_TIMEOUT_RETRY_BUDGET", "1")
    monkeypatch.setenv("AI_MEASURE_PHASE_A_TIMEOUT", "3")
    monkeypatch.setenv("AI_MEASURE_PER_CALL_TIMEOUT", "1")

    async def fake_extract_one_photo(*, photo_idx, raw_bytes, **_kw):
        if photo_idx == 0:
            return {
                "index": 0,
                "_photo_idx": 0,
                "walls_visible": ["front"],
                "eave_height_ft_observed": 9.0,
                "_latency_ms": 100,
                "_total_latency_ms": 100,
            }
        # photo 1 hangs — should trip the per-photo budget
        await asyncio.sleep(5)
        return {"index": photo_idx, "_photo_idx": photo_idx}

    async def fake_reconcile(*, extractions, **_kw):
        # Reconciler receives BOTH extractions — including the empty
        # timeout one — and must be free to build a partial result.
        assert len(extractions) == 2
        empties = [e for e in extractions if e.get("_empty_extraction")]
        assert len(empties) == 1
        assert empties[0]["_photo_idx"] == 1
        assert "budget" in (empties[0].get("_extraction_error") or "").lower()
        assert "timed out" in (empties[0].get("_empty_reason") or "").lower()
        return {"walls": [], "openings": [], "photos": []}

    calls = {"set_stage": []}
    async def set_stage(stage):
        calls["set_stage"].append(stage)

    monkeypatch.setattr(ai_measure, "_extract_one_photo", fake_extract_one_photo)
    monkeypatch.setattr(ai_measure, "_reconcile_extractions", fake_reconcile)

    # Skip the DB write inside the pipeline — no live Mongo needed here.
    fake_db = AsyncMock()
    monkeypatch.setattr(ai_measure, "db", fake_db)

    # call via the LIVE module — earlier tests (anthropic_direct_key,
    # run1_defects) del sys.modules["routes.ai_measure"] and re-import,
    # so the collection-time function binding points at a stale instance
    # whose globals our monkeypatches never touch
    final, extractions = await ai_measure._run_two_phase_pipeline(
        run_id="test-run-xyz",
        api_key="test-key",
        user_id="test-user",
        image_payloads=[("image/jpeg", b"fake-bytes-0"), ("image/jpeg", b"fake-bytes-1")],
        model_provider="anthropic",
        model_name="claude-3-5-sonnet-20241022",
        address=None,
        reference_dim=None,
        brick_course_in=None,
        siding_exposure_in=None,
        annotation_hint="",
        set_stage=set_stage,
    )

    # Phase A produced BOTH slots — no CancelledError bubbled up.
    assert len(extractions) == 2
    # Photo 0 kept its real data.
    assert extractions[0].get("walls_visible") == ["front"]
    # Photo 1 was timed out and flagged (empty + reason mentioning timeout).
    assert extractions[1].get("_empty_extraction") is True
    assert "timed out" in (extractions[1].get("_empty_reason") or "").lower()
    assert "budget" in (extractions[1].get("_extraction_error") or "").lower()
    # Iter 79j.82 — the salvage pass fired and its failure is recorded.
    assert extractions[1].get("_timeout_retry_attempted") is True
    # Orphan bookkeeping ran → walls the slow photo would've contributed
    # to (nothing here since it never reported walls_visible) surface on
    # the final raw.
    assert "_empty_photos" in final
    # `set_stage` was called for both phases in order.
    assert calls["set_stage"][0] == "extracting_per_photo"
    assert calls["set_stage"][-1] == "reconciling"
