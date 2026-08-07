"""ACCEPTANCE BAR LINE (b) — FIXTURE MANIFEST regenerator (sealed by
Howard 2026-08-07). Run DELIBERATELY when a RULING legitimately moves
anchor lines; commit the new manifest citing the ruling. The paired
test names any drifted line and its amount — a hash that only says
"something changed" is a tax Howard ruled against paying.

Usage: cd /app/backend && python scripts_update_fixture_manifest.py
"""
import hashlib
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/backend/tests")

from routes.hover import _build_lines  # noqa: E402
from test_boni_rulings_2026_08_05 import _boni_measurements  # noqa: E402

MANIFEST = Path("/app/memory/fixture_manifest.json")


def anchors() -> dict:
    boni = _boni_measurements(167, 99)
    return {
        "boni_read_2026_08_05": dict(boni),
        "boni_read_integral_j_on": {**boni, "_windows_integral_j": True},
    }


def canonical_lines(m: dict) -> dict:
    return {f'{l.get("tab") or "vinyl"}|{l.get("name")}': float(l.get("qty") or 0)
            for l in _build_lines(dict(m))}


def build_manifest() -> dict:
    out = {}
    for name, m in anchors().items():
        lines = canonical_lines(m)
        blob = json.dumps(lines, sort_keys=True).encode()
        out[name] = {"sha256": hashlib.sha256(blob).hexdigest(),
                     "lines": lines}
    return out


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build_manifest(), indent=1,
                                   sort_keys=True) + "\n")
    print(f"manifest written: {MANIFEST}")
