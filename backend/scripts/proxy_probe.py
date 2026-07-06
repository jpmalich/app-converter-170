"""
Emergent LiteLLM proxy latency probe — 3 parallel large calls per model.

Purpose
-------
Iter 79j.51 followup: Emergent support suspects that `claude-fable-5`
may not be in the proxy's documented model list, and that unlisted
models may be falling into a throttled default bucket. That would
explain the payload-driven serialization we saw in production.

This probe is a controlled test — isolated from the app — that
fires 3 concurrent LlmChat.send_message calls with an intentionally
LARGE text prompt (no images, so we don't mix Phase A vision cost
into the numbers) against each model and reports wall clock time.

Usage
-----
    python -m backend.scripts.proxy_probe

The script prints per-call latencies and total wall time for each
model. It NEVER writes to the DB, and it does NOT touch the app's
running LLM traffic — safe to run any time on preview.

Do NOT change the app's model based on results. Per user gate, this
is a probe only; red-house validation still gates all feature work.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

# Make backend importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

MODELS_TO_PROBE = [
    ("claude-fable-5", "anthropic", "claude-fable-5"),
    ("claude-sonnet-4-5", "anthropic", "claude-sonnet-4-5"),
]

# Payload roughly the size of a Phase B reconciliation prompt — big
# enough to actually stress serialization but small enough to run
# cheaply. ~4KB of prompt text.
LARGE_PROMPT = (
    "You are a roofing / siding measurement reconciler. Below is a "
    "synthetic per-photo extraction batch — please write a long, "
    "detailed JSON blob (up to ~4000 tokens) that lists the wall "
    "elevations, dormers, and openings you would report for a "
    "hypothetical two-story colonial house with 4 elevations, 3 "
    "dormers on the front slope, 2 dormers on the back slope, 22 "
    "windows, and 2 doors. Include exact linear feet for each "
    "elevation trim and each dormer perimeter, and explain your "
    "reconciliation choices in prose after the JSON. Do NOT be "
    "terse — we are stress-testing the proxy, so please produce "
    "the fullest response you can. Aim for the max_tokens ceiling.\n\n"
    + ("Elevation stub payload: " + ("x" * 100) + "\n") * 40
)

CONCURRENCY = 3
MAX_TOKENS = 4000

SYSTEM = (
    "You are a verbose measurement reconciliation assistant. When "
    "asked to reconcile, produce a long JSON + prose response near "
    "the max_tokens ceiling."
)


async def _one_call(label: str, provider: str, model: str, api_key: str, call_idx: int) -> dict:
    """Single LlmChat.send_message with a fresh session."""
    t0 = time.time()
    session_id = f"proxy-probe-{label}-{call_idx}-{uuid.uuid4().hex[:6]}"
    try:
        chat = (
            LlmChat(api_key=api_key, session_id=session_id, system_message=SYSTEM)
            .with_model(provider, model)
            .with_params(max_tokens=MAX_TOKENS)
        )
        reply = await chat.send_message(UserMessage(text=LARGE_PROMPT))
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "call_idx": call_idx,
            "ok": True,
            "latency_ms": elapsed_ms,
            "reply_chars": len(reply or ""),
        }
    except Exception as e:  # noqa: BLE001 - we want to observe everything
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            "call_idx": call_idx,
            "ok": False,
            "latency_ms": elapsed_ms,
            "error": f"{type(e).__name__}: {str(e)[:200]}",
        }


async def probe_model(label: str, provider: str, model: str, api_key: str) -> dict:
    print(f"\n=== Probing {label} ({provider}/{model}) — {CONCURRENCY} parallel calls ===")
    wall_t0 = time.time()
    results = await asyncio.gather(
        *[_one_call(label, provider, model, api_key, i) for i in range(CONCURRENCY)]
    )
    wall_ms = int((time.time() - wall_t0) * 1000)
    for r in results:
        if r["ok"]:
            print(f"  call {r['call_idx']}: OK  latency={r['latency_ms']}ms  chars={r['reply_chars']}")
        else:
            print(f"  call {r['call_idx']}: FAIL latency={r['latency_ms']}ms  err={r['error']}")
    print(f"  --> total wall time: {wall_ms}ms ({wall_ms/1000:.1f}s)")
    return {"label": label, "wall_ms": wall_ms, "results": results}


async def main() -> None:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise SystemExit("EMERGENT_LLM_KEY missing in env — cannot probe proxy.")
    print(
        f"Proxy probe start · EMERGENT_LLM_KEY suffix=...{api_key[-6:]} "
        f"· concurrency={CONCURRENCY} · max_tokens={MAX_TOKENS}"
    )
    summaries = []
    for label, provider, model in MODELS_TO_PROBE:
        summaries.append(await probe_model(label, provider, model, api_key))
        # small breather so back-to-back runs don't inherit each
        # other's proxy queue state
        await asyncio.sleep(2)
    print("\n=== Summary ===")
    for s in summaries:
        oks = sum(1 for r in s["results"] if r["ok"])
        avg = (
            sum(r["latency_ms"] for r in s["results"]) / max(1, len(s["results"]))
        )
        print(
            f"  {s['label']:<24} wall={s['wall_ms']/1000:5.1f}s  "
            f"ok={oks}/{len(s['results'])}  avg_call={avg/1000:5.1f}s"
        )


if __name__ == "__main__":
    asyncio.run(main())
