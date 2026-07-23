from creds_for_tests import TEST_PASSWORD
"""Geometry-source naming — STANDING RULE (Howard, 2026-07-16).

Pins:
  • every LP derivation response carries geometry_basis (source, run_id,
    binding, label) — no derivation silently binds to a latest-run
  • binding is always NAMED from the closed set
  • an applied stamp (lp_source_run_id) reports binding=applied-stamp/pinned
  • an explicit run_id reports binding=explicit-run
  • tape overlays (user_measured dims) are counted and named in the label
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
EST_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"  # letrick (photo run)

BINDINGS = {"applied-stamp", "explicit-run", "latest-run", "paired-latest"}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


def _preview(session, body=None):
    r = session.post(f"{API}/estimates/{EST_ID}/lp-package/preview", json=body or {}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


class TestGeometryBasisNamed:
    def test_preview_carries_geometry_basis(self, session):
        pkg = _preview(session)
        gb = pkg.get("geometry_basis")
        assert gb, "geometry_basis missing — derivation bound silently"
        assert gb["source"] in ("photo", "blueprint", "hover")
        assert gb["run_id"] == pkg["run_id"]
        assert gb["binding"] in BINDINGS
        assert gb["kind"] in ("photo", "blueprint")

    def test_label_states_run_and_binding(self, session):
        gb = _preview(session)["geometry_basis"]
        rid8 = str(gb["run_id"])[:8]
        assert rid8 in gb["label"]
        assert "extraction run" in gb["label"]
        # binding named in human words — pinned or unpinned is always visible
        assert ("pinned" in gb["label"]) or ("unpinned" in gb["label"]) or ("explicit run" in gb["label"])

    def test_explicit_run_id_reports_explicit_binding(self, session):
        base = _preview(session)
        pkg = _preview(session, {"run_id": base["run_id"]})
        gb = pkg["geometry_basis"]
        assert gb["binding"] == "explicit-run"
        assert gb["run_id"] == base["run_id"]
        assert gb["pinned"] is False

    def test_pinned_flag_matches_binding(self, session):
        gb = _preview(session)["geometry_basis"]
        assert gb["pinned"] == (gb["binding"] == "applied-stamp")

    def test_unit_label_composition(self):
        from routes.lp_package_routes import _geometry_basis
        est = {
            "lp_appendage_dims": {
                "appendage:back": {"height_ft": {"status": "user_measured", "value": 18.9}},
            },
            "lp_field_verify": {"k1": {"status": "verified"}},
            "lp_source_run_id": "abc123",
        }
        run = {"run_id": "abc123def456", "page_paths": None}
        gb = _geometry_basis(est, run, "applied-stamp")
        assert gb["pinned"] is True
        assert gb["taped_dims"] == 1
        assert gb["confirmed_locations"] == 1
        assert gb["label"] == (
            "photo extraction run abc123de — pinned (applied) · 1 taped dim · 1 field-confirmed"
        )

    def test_unit_latest_run_is_named_unpinned(self):
        from routes.lp_package_routes import _geometry_basis
        gb = _geometry_basis({}, {"run_id": "d66794488ef8"}, "latest-run")
        assert gb["pinned"] is False
        assert "latest run — unpinned" in gb["label"]
