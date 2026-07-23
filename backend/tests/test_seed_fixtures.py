"""SEED CONVERSION pins (Howard's consolidated ruling 2026-07-23, item 5 / 3b).

  • FULL PARITY export exists: manifest + docs + blob pack, checksums valid
  • company-slot split per the ruling condition: doug jones / haugh /
    round-two = "test" slot (separate test company on prod); red house /
    LP pair / Letrick = "demo" slot
  • protection survives the seed round-trip: every exported estimate
    carries protected: True
  • human rungs transport verbatim (red house tape_check with the 33+1cut
    human count rides inside the exported doc)
  • no password hashes in the export (secrets live only in env)
  • the seed runner's verify mode = the morning-of PROVISIONING GATE:
    exit 0 + GREEN on a provisioned environment
  • suite un-hardcoded: no test file carries the preview host literal —
    api_base derives from env (suite runs against ANY environment)
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
FIXTURES = BACKEND / "fixtures"
sys.path.insert(0, str(BACKEND))

EXPECTED_SLOTS = {
    "673707d5-9b7e-4d8f-8eaf-63c86820f611": "demo",
    "e452a988-83b8-4e6e-9537-1223d0ecbf6f": "demo",
    "8f95c9c2-add9-416a-92f3-786a4ea2ce83": "demo",
    "db82ec7a-3177-406d-a602-927255e9e10e": "test",
    "48231310-3872-4d4e-b657-35ade10c1cb8": "test",
    "d78cd3b4-a65c-4238-8d16-7827b131a85c": "test",
}


def _manifest():
    return json.loads((FIXTURES / "manifest.json").read_text())


def _estimates():
    return json.loads((FIXTURES / "docs" / "estimates.json").read_text())


def test_manifest_full_parity_and_counts():
    m = _manifest()
    assert m["scope"] == "FULL_PARITY"
    assert m["counts"]["estimates"] == 6
    assert m["counts"]["blobs"] == len(m["blobs"]) > 0
    assert m["counts"]["blobs_missing_at_export"] == []


def test_company_slot_split_per_ruling():
    slots = {e["id"]: e["company_slot"] for e in _estimates()}
    assert slots == EXPECTED_SLOTS


def test_protection_survives_seed_round_trip():
    for e in _estimates():
        assert e.get("protected") is True, f"{e['id'][:8]} exported unprotected"


def test_human_rungs_transport_verbatim():
    red = next(e for e in _estimates() if e["id"].startswith("673707d5"))
    seg = red["tape_check"]["walls"]["left"]["segments"][0]
    assert seg["courses"] == 33 and seg["cut_courses"] == 1
    assert red["tape_check"]["history"], "scored accuracy history must transport"


def test_no_password_hashes_in_export():
    acc = (FIXTURES / "docs" / "accounts.json").read_text()
    assert "password_hash" not in acc


def test_blob_pack_integrity():
    m = _manifest()
    for name, meta in m["blobs"].items():
        p = FIXTURES / "blobs" / name
        assert p.exists(), f"pack missing {name}"
        assert hashlib.sha256(p.read_bytes()).hexdigest() == meta["sha256"], name


def test_provisioning_gate_green_on_this_env():
    r = subprocess.run([sys.executable, str(BACKEND / "seed" / "seed_runner.py"), "verify"],
                       capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "PROVISIONING GATE: GREEN" in r.stdout


def test_creds_slot_split_available():
    from creds_for_tests import (FIXTURE_DEMO_EMAIL, FIXTURE_TEST_EMAIL,
                                 TEST_EMAIL)
    assert FIXTURE_DEMO_EMAIL and FIXTURE_TEST_EMAIL
    # preview default: both resolve to the same account (no split here)
    assert FIXTURE_DEMO_EMAIL == TEST_EMAIL


def test_suite_host_unhardcoded():
    host = "https://app-converter-170" + ".preview.emergentagent.com"
    offenders = [p.name for p in Path(__file__).parent.glob("test_*.py")
                 if host in p.read_text().replace('"https://app-converter-170" + ".preview', "")]
    assert offenders == [], offenders
    import api_base
    assert api_base.API.endswith("/api") and api_base.BASE_URL.startswith("http")
