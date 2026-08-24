"""COLD-START HONESTY PIN (Howard's bug report 2026-08-24).

The preview pod restarts between sessions; while it boots the ingress
answers 502/404 for EVERY /api route. The client used to read that burst
as "no data" and print "NEEDS A COMPLETED BLUEPRINT READ" over reads that
were DONE (dart and Tanis both had completed runs with page images on
disk) — a 502 wearing "no run"'s clothes, the SEND-115 lesson client-side.

THE RULE, pinned structurally: a failure only retries when the /version
probe confirms the WHOLE TREE is down (then the original request never
reached the app, so a replay can never double-fire a write); a real
answer from a live backend passes through untouched; the banner NAMES the
state while retrying — silence would mean nothing is wrong."""
from pathlib import Path

FRONT = Path(__file__).resolve().parents[2] / "frontend/src"


def test_api_client_carries_the_health_gated_retry():
    src = (FRONT / "lib/api.js").read_text(encoding="utf-8")
    assert "async function _backendIsDown()" in src
    assert "${API}/version" in src, "the probe hits a route that ALWAYS exists"
    assert "throw error; // backend is up — the answer is real" in src, \
        "a real 404/502 from a live backend is never retried into a lie"
    assert "cfg.__noRetry" in src, "callers can opt out (the /version poll)"
    assert "[404, 502, 503, 504]" in src
    assert "pq:backend-down" in src and "pq:backend-up" in src


def test_version_poll_opts_out_of_its_own_retry():
    src = (FRONT / "components/BuildMismatchBanner.jsx").read_text(
        encoding="utf-8")
    assert '__noRetry: true' in src


def test_banner_is_mounted_and_speaks_both_languages():
    app = (FRONT / "App.js").read_text(encoding="utf-8")
    assert "<ServerWakingBanner />" in app
    banner = (FRONT / "components/ServerWakingBanner.jsx").read_text(
        encoding="utf-8")
    assert 'data-testid="server-waking-banner"' in banner
    assert 't("server.waking.msg")' in banner
    dic = (FRONT / "lib/dictionaries.js").read_text(encoding="utf-8")
    assert dic.count('"server.waking.msg":') == 2, "EN + ES"
