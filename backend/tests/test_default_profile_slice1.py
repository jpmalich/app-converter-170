"""Slice 1 — Job-level default siding profile (ruled 2026-07-16).

Pins:
  • single-profile job requires ZERO annotations — the default composes
    every wall (forced whole-house re-expression on the same geometry)
  • annotation overrides beat the default where present (multi-profile
    extraction split is left untouched)
  • no intake path composes a profile the estimate didn't select or
    confirm: lap is never silently forced; the default field drives it
  • Hover→engine mapping contract: deliberate field passthrough, pending
    flags for unmappable basis, NO approximation; B&B forces starter 0
  • LP SmartSide only: non-LP kinds are refused (no cosmetic labels)
"""
from creds_for_tests import TEST_PASSWORD
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API = "https://app-converter-170.preview.emergentagent.com/api"
EST_ID = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"  # letrick (lap, LP-kind)

PANEL = "38 Series 4' x 10' Panel"
LAP = '38 Series Lap 3/8" x 8" x 16\''


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s
    # restore: letrick fixture stays profile-less (lap via engine default)
    s.post(f"{API}/estimates/{EST_ID}/default-profile", json={"profile": None}, timeout=15)


def _named(pkg):
    return {l["name"]: l for l in pkg["lines"] if (l.get("qty") or 0) > 0}


class TestApplyDefaultProfileUnit:
    def test_no_default_is_untouched(self):
        from routes.lp_package_routes import _apply_default_profile
        m = {"siding_sqft": 1000, "_per_profile_sqft": {"lap": 1000}}
        assert _apply_default_profile(m, {}) is m

    def test_single_profile_needs_zero_annotations(self):
        from routes.lp_package_routes import _apply_default_profile
        m = {"siding_sqft": 1000, "_per_profile_sqft": {"lap": 1000}, "starter_lf": 120}
        out = _apply_default_profile(m, {"default_siding_profile": "board_batten"})
        assert out["_per_profile_sqft"] == {"board_batten": 1000.0}
        assert out["_force_profile_lines"] is True
        assert out["starter_lf"] == 0  # ruled: no starter on B&B

    def test_annotations_beat_the_default(self):
        from routes.lp_package_routes import _apply_default_profile
        m = {"siding_sqft": 1000,
             "_per_profile_sqft": {"lap": 700, "shake": 300}}  # annotated mixed job
        out = _apply_default_profile(m, {"default_siding_profile": "board_batten"})
        assert out["_per_profile_sqft"] == {"lap": 700, "shake": 300}

    def test_unknown_profile_ignored(self):
        from routes.lp_package_routes import _apply_default_profile
        m = {"siding_sqft": 1000, "_per_profile_sqft": {"lap": 1000}}
        assert _apply_default_profile(m, {"default_siding_profile": "stucco"}) is m


class TestHoverMappingContractUnit:
    def test_passthrough_and_flags(self):
        from routes.lp_package_routes import _hover_mapping_contract
        hover = {"siding_sqft": 2000, "outside_corner_count": 6, "outside_corner_lf": 110,
                 "eaves_lf": 150, "rakes_lf": 90, "starter_lf": 140, "window_count": 12,
                 "roof_sqft": 3000}  # roof is NOT in the contract
        m, flags = _hover_mapping_contract(hover, "board_batten")
        assert m["siding_sqft"] == 2000 and m["outside_corner_lf"] == 110
        assert "roof_sqft" not in m, "unmapped fields must not leak through"
        assert m["_per_profile_sqft"] == {"board_batten": 2000.0}
        assert m["starter_lf"] == 0
        codes = [f["code"] for f in flags]
        assert codes == ["corner_locators", "batten_wall_heights", "opening_schedule"]
        assert all(f["label"] and f["verify"] for f in flags)

    def test_lap_has_no_batten_flag(self):
        from routes.lp_package_routes import _hover_mapping_contract
        _, flags = _hover_mapping_contract({"siding_sqft": 1500, "starter_lf": 100}, "lap")
        assert "batten_wall_heights" not in [f["code"] for f in flags]


class TestDefaultProfileHttp:
    def test_set_default_rederives_bb(self, session):
        r = session.post(f"{API}/estimates/{EST_ID}/default-profile",
                         json={"profile": "board_batten"}, timeout=15)
        assert r.status_code == 200 and r.json()["to"] == "board_batten"
        pkg = session.post(f"{API}/estimates/{EST_ID}/lp-package/preview", json={}, timeout=60).json()
        names = _named(pkg)
        assert PANEL in names and LAP not in names
        assert not any("starter" in n.lower() for n in names)
        assert "profile: Board & Batten" in pkg["geometry_basis"]["label"]

    def test_clear_default_reverts_to_extraction(self, session):
        r = session.post(f"{API}/estimates/{EST_ID}/default-profile",
                         json={"profile": None}, timeout=15)
        assert r.status_code == 200 and r.json()["to"] is None
        pkg = session.post(f"{API}/estimates/{EST_ID}/lp-package/preview", json={}, timeout=60).json()
        names = _named(pkg)
        assert LAP in names and PANEL not in names
        assert "profile:" not in pkg["geometry_basis"]["label"]

    def test_invalid_profile_422(self, session):
        r = session.post(f"{API}/estimates/{EST_ID}/default-profile",
                         json={"profile": "stucco"}, timeout=15)
        assert r.status_code == 422

    def test_non_lp_kind_refused(self, session):
        r = session.post(f"{API}/estimates", json={"kind": "siding", "customer_name": "ZZ profile-pin TEMP"}, timeout=15)
        assert r.status_code == 200
        temp = r.json()["id"]
        try:
            rr = session.post(f"{API}/estimates/{temp}/default-profile",
                              json={"profile": "lap"}, timeout=15)
            assert rr.status_code == 400, "non-LP kinds get NO profile field (slice 1)"
        finally:
            session.delete(f"{API}/estimates/{temp}", timeout=15)


class TestHoverLpRunHttp:
    HOVER_RUN = "45fa194379014a8fae132534041b7ff9"

    def test_materialize_and_basis_named(self, session):
        r = session.post(f"{API}/estimates", json={"kind": "lp_smart", "customer_name": "ZZ hover-lp-run pin TEMP"}, timeout=15)
        assert r.status_code == 200
        temp = r.json()["id"]
        try:
            rr = session.post(f"{API}/estimates/{temp}/hover-lp-run",
                              json={"hover_run_id": self.HOVER_RUN, "profile": "board_batten"}, timeout=30)
            assert rr.status_code == 200, rr.text
            body = rr.json()
            assert body["lp_run_id"].startswith("hover-")
            assert len(body["mapping_flags"]) >= 3
            pkg = session.post(f"{API}/estimates/{temp}/lp-package/preview", json={}, timeout=60).json()
            gb = pkg["geometry_basis"]
            assert gb["kind"] == "hover"
            assert gb["binding"] == "applied-stamp" and gb["pinned"] is True
            assert gb["label"].startswith("Hover import — report ")
            assert pkg["source_label"] == "Hover import"
            pkg_flags = pkg["hover_mapping_flags"]
            assert [f["code"] for f in pkg_flags] == [f["code"] for f in body["mapping_flags"]]
            assert all(f["status"] == "open" for f in pkg_flags)
            names = _named(pkg)
            assert PANEL in names and LAP not in names
        finally:
            session.delete(f"{API}/estimates/{temp}", timeout=15)

    def test_missing_profile_422(self, session):
        r = session.post(f"{API}/estimates", json={"kind": "lp_smart", "customer_name": "ZZ hover-pin2 TEMP"}, timeout=15)
        temp = r.json()["id"]
        try:
            rr = session.post(f"{API}/estimates/{temp}/hover-lp-run",
                              json={"hover_run_id": self.HOVER_RUN}, timeout=15)
            assert rr.status_code == 422, "the import ASKS — no silent lap"
        finally:
            session.delete(f"{API}/estimates/{temp}", timeout=15)
