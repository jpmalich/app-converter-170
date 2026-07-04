"""Iter 79j.42 — ANTHROPIC_API_KEY direct-routing.

When the backend env sets ANTHROPIC_API_KEY, all Anthropic-provider
Claude calls (main worker, rerun, cross-check, OCR-scale) must use
that key and bypass the Emergent LiteLLM proxy. Every other provider
(Gemini, OpenAI) keeps using EMERGENT_LLM_KEY.

Never exposed on the frontend — this is a backend-only routing switch.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/routes")
load_dotenv(Path("/app/backend/.env"))


def _reload_module():
    """Reload routes.ai_measure so `_pick_llm_api_key` sees whatever
    env we set in the test. Cheap because the module is <5 MB."""
    if "routes.ai_measure" in sys.modules:
        del sys.modules["routes.ai_measure"]
    return importlib.import_module("routes.ai_measure")


def test_pick_llm_api_key_ignores_anthropic_direct_when_disabled(monkeypatch):
    """Iter 79j.44 — Direct-key routing is currently DISABLED. Even
    when ANTHROPIC_API_KEY is set on the .env, the helper MUST return
    the Emergent proxy key. Re-enable only after a standalone
    api.anthropic.com test call succeeds in isolation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-12345")
    monkeypatch.setenv("EMERGENT_LLM_KEY", "sk-emergent-fallback")
    m = _reload_module()
    key, source = m._pick_llm_api_key("anthropic")
    assert key == "sk-emergent-fallback"
    assert source == "emergent_proxy"


def test_pick_llm_api_key_falls_back_to_emergent_when_anthropic_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("EMERGENT_LLM_KEY", "sk-emergent-fallback")
    m = _reload_module()
    key, source = m._pick_llm_api_key("anthropic")
    assert key == "sk-emergent-fallback"
    assert source == "emergent_proxy"


def test_pick_llm_api_key_never_uses_anthropic_for_gemini(monkeypatch):
    """Gemini calls MUST go through the Emergent proxy even when
    ANTHROPIC_API_KEY is set — the direct route is Anthropic-only."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-be-used")
    monkeypatch.setenv("EMERGENT_LLM_KEY", "sk-emergent-key")
    m = _reload_module()
    key, source = m._pick_llm_api_key("gemini")
    assert key == "sk-emergent-key"
    assert source == "emergent_proxy"


def test_pick_llm_api_key_never_uses_anthropic_for_openai(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-not-be-used")
    monkeypatch.setenv("EMERGENT_LLM_KEY", "sk-emergent-key")
    m = _reload_module()
    key, source = m._pick_llm_api_key("openai")
    assert key == "sk-emergent-key"
    assert source == "emergent_proxy"


def test_pick_llm_api_key_returns_none_when_both_missing(monkeypatch):
    """Callers must handle a missing key with a 500 response — this
    lets the helper stay side-effect-free and testable."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("EMERGENT_LLM_KEY", raising=False)
    m = _reload_module()
    key, source = m._pick_llm_api_key("anthropic")
    assert key is None
    assert source == "emergent_proxy"


def test_pick_llm_api_key_ignores_whitespace_only_anthropic(monkeypatch):
    """Someone typing `ANTHROPIC_API_KEY=` with no value or trailing
    whitespace should NOT accidentally trigger the direct route."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    monkeypatch.setenv("EMERGENT_LLM_KEY", "sk-emergent-key")
    m = _reload_module()
    key, source = m._pick_llm_api_key("anthropic")
    assert key == "sk-emergent-key"
    assert source == "emergent_proxy"


def test_anthropic_key_env_never_referenced_by_frontend():
    """Belt-and-braces check: no frontend file may read
    ANTHROPIC_API_KEY. The key is backend-only — leaking it into a
    client bundle would ship it to every browser."""
    frontend_src = Path("/app/frontend/src")
    hits = []
    for py in frontend_src.rglob("*"):
        if py.suffix not in {".js", ".jsx", ".ts", ".tsx", ".html", ".env"}:
            continue
        try:
            text = py.read_text(errors="ignore")
        except Exception:
            continue
        if "ANTHROPIC_API_KEY" in text:
            hits.append(str(py))
    assert hits == [], (
        f"ANTHROPIC_API_KEY leaked into frontend files: {hits}. "
        "This env var must NEVER be readable from the browser bundle."
    )
    # And it must not be in the frontend .env either.
    fe_env = Path("/app/frontend/.env")
    if fe_env.exists():
        assert "ANTHROPIC_API_KEY" not in fe_env.read_text()
