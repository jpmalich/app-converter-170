from creds_for_tests import TEST_PASSWORD
"""Compare-profiles toggle (approved 2026-07-16) — ships under the
geometry-source standing rule.

Pins:
  • one endpoint, ONE named geometry: both variants carry the SAME
    geometry_basis (same run, same binding)
  • alternative forced to board_batten: 4×10 panels + 190 Series battens
    compose; lap + starter do NOT (panels start on the ledge — ruled)
  • nothing persists: derivation is per-request (estimate untouched)
  • invalid alt_profile is refused (422)
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API = "https://app-converter-170.preview.emergentagent.com/api"
EST_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"  # letrick (lap house)

PANEL = "38 Series 4' x 10' Panel"
BATTEN = '190 Series Trim 19/32" x 3" x 16\''
LAP = '38 Series Lap 3/8" x 8" x 16\''


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


@pytest.fixture(scope="module")
def compare(session):
    r = session.post(f"{API}/estimates/{EST_ID}/lp-package/compare", json={}, timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


def _named(pkg):
    return {l["name"]: l for l in pkg["lines"] if (l.get("qty") or 0) > 0}


class TestCompareProfiles:
    def test_one_named_geometry_both_variants(self, compare):
        gb = compare["geometry_basis"]
        assert gb and gb["binding"] in ("applied-stamp", "explicit-run", "latest-run", "paired-latest")
        assert compare["current"]["geometry_basis"] == gb
        assert compare["alternative"]["geometry_basis"] == gb
        assert compare["current"]["run_id"] == compare["alternative"]["run_id"] == gb["run_id"]

    def test_alternative_composes_bb_ruled_lines(self, compare):
        alt = _named(compare["alternative"])
        assert PANEL in alt, "B&B panels missing"
        assert BATTEN in alt, "battens missing"
        assert LAP not in alt, "lap must not compose on the forced B&B variant"
        assert not any("starter" in n.lower() for n in alt), "RULED: no starter on B&B"

    def test_current_keeps_lap_and_starter(self, compare):
        cur = _named(compare["current"])
        assert LAP in cur
        assert any("starter" in n.lower() for n in cur)
        assert PANEL not in cur and BATTEN not in cur

    def test_shared_lines_identical(self, compare):
        cur, alt = _named(compare["current"]), _named(compare["alternative"])
        shared = set(cur) & set(alt)
        assert len(shared) >= 10
        for n in shared:
            assert cur[n]["qty"] == alt[n]["qty"], n
            assert cur[n].get("line_sell") == alt[n].get("line_sell"), n

    def test_invalid_alt_profile_refused(self, session):
        r = session.post(f"{API}/estimates/{EST_ID}/lp-package/compare",
                         json={"alt_profile": "stucco"}, timeout=30)
        assert r.status_code == 422

    def test_nothing_persists(self, session, compare):
        # a fresh preview after compare still derives the ORIGINAL lap composition
        r = session.post(f"{API}/estimates/{EST_ID}/lp-package/preview", json={}, timeout=60)
        assert r.status_code == 200
        names = _named(r.json())
        assert LAP in names and PANEL not in names
