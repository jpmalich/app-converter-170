"""STALE PAGE DETECTION (Howard ruled 2026-08-09, after the false
data-loss report): "SOMETHING WAS OUT OF DATE AND NOTHING REPORTED IT.
DETECT A CLIENT-VERSUS-SERVER BUILD MISMATCH AND SAY SO."

One version string served at GET /api/version; the client remembers the
version it loaded with, re-checks on focus and on an interval, and a
mismatch prints the client/server pair with a refresh prompt. The seam
is REGISTERED (client_build_stale) — a surface silently disagreeing with
its own backend is a seam like any other.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_version  # noqa: E402
import seam_accounting  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestVersionSource:
    def test_version_is_stable_and_nonempty(self):
        v = build_version.get_build_version()
        assert isinstance(v, str) and v
        assert build_version.get_build_version() == v  # computed ONCE

    def test_version_is_the_git_commit_when_git_exists(self):
        import subprocess
        head = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(BACKEND.parent)
        ).decode().strip()
        assert build_version.get_build_version() == head

    def test_endpoint_is_wired_under_api(self):
        src = (BACKEND / "server.py").read_text()
        assert '@app.get("/api/version")' in src
        assert "get_build_version" in src


class TestSeamRegistered:
    def test_client_build_stale_is_a_registered_seam(self):
        assert "client_build_stale" in seam_accounting.SEAM_REGISTRY
        assert "version pair" in seam_accounting.SEAM_REGISTRY[
            "client_build_stale"]


class TestClientContract:
    def test_banner_checks_on_focus_and_never_fires_on_network_noise(self):
        src = (FRONTEND / "components" / "BuildMismatchBanner.jsx").read_text()
        assert 'api.get("/version")' in src
        assert '"focus"' in src
        assert "never fires the banner" in src  # catch swallows, no banner
        assert "build-mismatch-banner" in src
        assert "build-mismatch-refresh" in src

    def test_banner_mounts_on_every_route(self):
        src = (FRONTEND / "App.js").read_text()
        assert "<BuildMismatchBanner />" in src

    def test_banner_prints_the_version_pair_en_and_es(self):
        d = (FRONTEND / "lib" / "dictionaries.js").read_text()
        assert d.count('"build.stale.msg"') == 2  # EN + ES
        for line in d.splitlines():
            if '"build.stale.msg"' in line:
                assert "{client}" in line and "{server}" in line


class TestRunIdentityOnTheCard:
    """Howard ruled 2026-08-09 send 6: reference runs by ESTIMATE NUMBER +
    RUN TIMESTAMP, and the run id lives ON THE CARD — a walk instruction
    must never cost a round trip."""

    def test_status_payload_carries_run_identity(self):
        src = (BACKEND / "routes" / "ai_blueprint.py").read_text()
        assert 'result_payload["readback"]["run"]' in src

    def test_card_prints_the_identity(self):
        src = (FRONTEND / "components" / "estimate"
               / "BlueprintReadBackCard.jsx").read_text()
        assert "bp-rb-run-identity" in src

    def test_identity_label_en_and_es(self):
        d = (FRONTEND / "lib" / "dictionaries.js").read_text()
        assert d.count('"bp.rb.run"') == 2


class TestAccentUngated:
    def test_card_mounts_on_the_estimate_page(self):
        src = (FRONTEND / "pages" / "EstimateEditor.jsx").read_text()
        assert "PerElevationBreakdownCard" in src
        assert "ACCENT INJECTION WORKS ON EVERY DOOR" in src

    def test_empty_breakdown_is_named_not_silent(self):
        src = (FRONTEND / "components" / "estimate"
               / "PerElevationBreakdownCard.jsx").read_text()
        assert "per-elev-empty" in src
        assert "if (!perElevation.length) return null" not in src
