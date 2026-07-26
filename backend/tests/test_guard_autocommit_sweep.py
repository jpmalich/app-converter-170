"""GUARD AUTO-COMMIT SWEEP (authorized by Howard 2026-07-26).

Fails any handback if commits since the last CLEAN stamp touched
backend/ or frontend/ CODE without a ruled message. Platform
auto-commits ("auto-commit for <job>") are landing-only — the June-27
class (code-carrying auto-commits that bypassed the discipline) dies
permanently.

Runtime data paths are excluded (backend/uploads is written by the app
at runtime and swept into platform auto-commits during normal use).
Escape hatch: a hash listed in memory/ratified_commits.txt (one per
line, comment allowed after whitespace) is treated as ratified by
ruling.
"""
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
LOG = REPO / "memory" / "handback_green_log.md"
RATIFIED = REPO / "memory" / "ratified_commits.txt"

CODE_PREFIXES = ("backend/", "frontend/")
EXCLUDED_PREFIXES = (
    "backend/uploads/",      # runtime photo/blueprint data
    "backend/fixtures/blobs/",
    "frontend/build/",
    "frontend/node_modules/",
)


def _git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, timeout=60)


def _last_stamp_hash():
    lines = [ln for ln in LOG.read_text().splitlines() if ln.startswith("- ")]
    if not lines:
        return None
    parts = [p.strip() for p in lines[-1].split("·")]
    return parts[1] if len(parts) > 1 else None


def _ratified():
    if not RATIFIED.exists():
        return set()
    out = set()
    for ln in RATIFIED.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.add(ln.split()[0])
    return out


def _is_code(path):
    if not path.startswith(CODE_PREFIXES):
        return False
    return not path.startswith(EXCLUDED_PREFIXES)


def test_no_unruled_code_commits_since_last_stamp():
    stamp = _last_stamp_hash()
    assert stamp, "handback_green_log.md carries no stamp line"
    if _git("cat-file", "-e", f"{stamp}^{{commit}}").returncode != 0:
        # stamp predates a rollback / rewritten history — nothing to sweep
        return
    r = _git("log", "--format=%H%x00%s", f"{stamp}..HEAD")
    assert r.returncode == 0, r.stderr
    ratified = _ratified()
    offenders = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        sha, subject = line.split("\x00", 1)
        if not subject.startswith("auto-commit"):
            continue  # ruled message — passes
        if sha[:7] in {h[:7] for h in ratified} or sha in ratified:
            continue
        files = _git("show", "--name-only", "--format=", sha).stdout.splitlines()
        touched = [f for f in files if f.strip() and _is_code(f.strip())]
        if touched:
            offenders.append(f"{sha[:9]} '{subject[:40]}' touched: {touched[:5]}")
    assert not offenders, (
        "UNRULED code-carrying auto-commit(s) since last stamp — land through "
        "the handback discipline or get a ruling (memory/ratified_commits.txt):\n"
        + "\n".join(offenders)
    )
