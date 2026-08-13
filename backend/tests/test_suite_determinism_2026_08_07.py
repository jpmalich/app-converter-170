"""SUITE DETERMINISM (Howard ruled 2026-08-07, open item 3): "flaky
tests are broken tests." Live-HTTP tests erroring through the preview
ingress under full-suite load do not get to live as a watch item — the
suite talks to the server it sits beside (localhost), deterministically.
TEST_API_EXTERNAL=1 deliberately points the suite at the public URL for
manual e2e verification only.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_suite_traffic_is_local_and_deterministic():
    if os.environ.get("TEST_API_EXTERNAL"):
        pytest.skip("cadence:external: deliberate external run")
    import api_base
    assert ("localhost" in api_base.BASE_URL
            or "127.0.0.1" in api_base.BASE_URL), (
        f"suite traffic rides the ingress again ({api_base.BASE_URL}) — "
        "the green-but-broken flake class returns with it")


def test_conftest_pins_the_local_base_before_collection():
    src = (Path(__file__).resolve().parent / "conftest.py").read_text()
    assert "TEST_API_EXTERNAL" in src
    assert "localhost:8001" in src


def test_local_server_actually_answers():
    """The determinism ruling only holds if the local server is really
    there — a suite that silently skips HTTP is worse than a flake."""
    import requests
    import api_base
    r = requests.get(f"{api_base.API}/auth/login", timeout=10)
    assert r.status_code in (405, 422), \
        "local server not answering — HTTP tests would all fail honestly"
