"""BUILD VERSION (Howard ruled 2026-08-09): a loaded page older than the
deployed build must SAY SO. One version string, computed once at import —
the git commit when available, a process-start stamp otherwise (a restart
without git is a redeploy for our purposes; prompting a refresh is right)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _compute() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_ROOT), stderr=subprocess.DEVNULL, timeout=5,
        ).decode().strip()
    except Exception:
        return f"t{int(time.time())}"


BUILD_VERSION = _compute()


def get_build_version() -> str:
    return BUILD_VERSION
