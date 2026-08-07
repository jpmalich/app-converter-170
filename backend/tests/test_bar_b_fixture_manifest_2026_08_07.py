"""ACCEPTANCE BAR LINE (b) — FIXTURE MANIFEST (sealed by Howard
2026-08-07, ruled BEFORE (c)): sha256 of the derived line-set per
anchor, one file, one test. HOWARD'S REQUIREMENT IS PART OF THE
RULING: on breakage this test NAMES which line moved and by how much —
a hash that only says "something changed" is a tax.

Regeneration is DELIBERATE: when a ruling legitimately moves an anchor,
run scripts_update_fixture_manifest.py and commit citing the ruling.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts_update_fixture_manifest import (  # noqa: E402
    MANIFEST, build_manifest,
)


def test_anchor_fixtures_hash_identical_with_named_drift():
    assert MANIFEST.exists(), \
        "fixture manifest missing — run scripts_update_fixture_manifest.py"
    recorded = json.loads(MANIFEST.read_text())
    current = build_manifest()
    assert set(recorded) == set(current), (
        f"anchor set changed: {sorted(set(recorded) ^ set(current))}")
    for name in recorded:
        if recorded[name]["sha256"] == current[name]["sha256"]:
            continue
        old, new = recorded[name]["lines"], current[name]["lines"]
        drift = []
        for key in sorted(set(old) | set(new)):
            a, b = old.get(key), new.get(key)
            if a != b:
                drift.append(f"{key}: {a} → {b}")
        raise AssertionError(
            f"ANCHOR DRIFT on {name} — {len(drift)} line(s) moved:\n  "
            + "\n  ".join(drift)
            + "\nIf a RULING moved these, regenerate the manifest and "
              "commit citing it. Unruled drift is the defect this pin exists for.")
