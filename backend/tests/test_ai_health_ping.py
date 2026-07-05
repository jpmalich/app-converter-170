"""Iter 79j.45 — AI Measure health-ping classifier.

The `/api/measure/ai-measure/health` endpoint has three duties:
  1. Distinguish budget-exceeded from generic outages so the UI can
     surface actionable copy (not the same red banner for both).
  2. Return "ambiguous" for anything unrecognised — a broken health
     check MUST NOT be able to hard-lock the product.
  3. Cache 45s server-side so we don't pay for a ping every keystroke.

These tests pin (1) and (2) at the pure-function boundary. (3) is
covered by inspection of `_AI_HEALTH_CACHE` in the endpoint code —
untested here to avoid coupling to global state during CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import _classify_health_error  # noqa: E402


def test_budget_exceeded_variants_map_to_budget_exceeded():
    for msg in [
        "OpenAIException - Budget has been exceeded! Current cost: 54.05",
        "budget exceeded",
        "Max budget: 52.401",
        "LITELLM: BUDGET HAS BEEN EXCEEDED for user X",
    ]:
        status, detail = _classify_health_error(msg)
        assert status == "budget_exceeded", f"{msg!r} → {status}"
        assert "top up" in detail.lower() or "add balance" in detail.lower()


def test_timeout_and_network_variants_map_to_unavailable():
    for msg in [
        "TimeoutError",
        "timeout after 5s",
        "Connection refused",
        "network unreachable",
        "read timed out",
        "DNS resolution failed",
    ]:
        status, _detail = _classify_health_error(msg)
        assert status == "unavailable", f"{msg!r} → {status}"


def test_unknown_error_is_ambiguous_not_budget():
    """A broken health check must NEVER masquerade as a budget error —
    the ambiguous bucket keeps the Run button enabled so a real bug in
    the health path can't disable the product."""
    for msg in [
        "Some new litellm error we haven't seen",
        "unexpected internal server condition",
        "",
        "the fridge is on fire",
    ]:
        status, detail = _classify_health_error(msg)
        assert status == "ambiguous", f"{msg!r} → {status}"
        assert "budget" not in detail.lower()


def test_ambiguous_detail_carries_truncated_raw_error():
    """The ambiguous bucket surfaces the raw error string so the
    contractor (or Howard) can screenshot it and file a ticket."""
    long_err = "banana " * 300
    _status, detail = _classify_health_error(long_err)
    assert "banana" in detail
    # Truncated so it doesn't blow up a toast layout.
    assert len(detail) < 400
