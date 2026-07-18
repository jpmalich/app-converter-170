"""261 Haugh round-two fix order — PINNED (rulings 2026-07-17).

Pins:
  • facade scope: wrap-only enters as siding_sqft; excluded types named;
    never silently sum all facade types; basis label names the scope
  • openings: Hover net composes as-is; basis label names the convention
  • soffit: measured per-surface basis governs — full total composes,
    ceilings → closed (porch-ceiling), Closed row survives on LP
  • 540 trim: HOVER-path measured perimeter − door bottoms (doors 3-side);
    photo/blueprint keep Iter 57ee constants (per-source convention)
  • OSC: HOVER-path measured corner LF ÷ 16; waste default 10% never 0
  • coil never composes on LP-routed surfaces
"""
from creds_for_tests import TEST_PASSWORD
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API = "https://app-converter-170.preview.emergentagent.com/api"
HAUGH_RUN = "7c6194d46b91444990b6910a175b12ff"  # re-ingested 2026-07-18 (TTL 2nd-instance re-arm; archives on first hover-lp-run)
LETRICK = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"

RULED = {
    "facade_scope": {"mode": "wrap_only", "wrap_sqft": 2064,
                     "excluded": {"stucco": 312, "brick": 234}},
    "soffit_breakdown": {"eaves_sqft": 216, "rakes_sqft": 164, "ceilings_sqft": 83},
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "hhunt6677@yahoo.com", "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


@pytest.fixture(scope="module")
def pkg(session):
    r = session.post(f"{API}/estimates", json={"kind": "lp_smart", "customer_name": "ZZ haugh-pin TEMP"}, timeout=15)
    temp = r.json()["id"]
    rr = session.post(f"{API}/estimates/{temp}/hover-lp-run",
                      json={"hover_run_id": HAUGH_RUN, "profile": "lap", **RULED}, timeout=30)
    if rr.status_code == 404 and "run not found" in rr.text:
        # hover_import_runs carries a 24h TTL (ttl_audit_report.md) — the
        # Haugh substrate expires between sessions. Pins stand; substrate
        # restores by re-uploading the 261 Haugh Hover PDF.
        session.delete(f"{API}/estimates/{temp}", timeout=15)
        pytest.skip("Haugh hover run TTL-expired (hover_import_runs 24h TTL) — re-upload the 261 Haugh Hover PDF to restore the pin substrate")
    assert rr.status_code == 200, rr.text
    p = session.post(f"{API}/estimates/{temp}/lp-package/preview", json={}, timeout=60).json()
    yield p
    session.delete(f"{API}/estimates/{temp}", timeout=15)


def _line(pkg, prefix):
    return next(l for l in pkg["lines"] if l["name"].startswith(prefix))


class TestRoundTwoPins:
    def test_unit_contract_scope_and_waste(self):
        from routes.lp_package_routes import _hover_mapping_contract
        m, _ = _hover_mapping_contract(
            {"siding_sqft": 2610, "starter_lf": 300}, "lap",
            facade_scope=RULED["facade_scope"],
            soffit_breakdown=RULED["soffit_breakdown"])
        assert m["siding_sqft"] == 2064
        assert m["_facade_scope"]["measured_total"] == 2610
        assert m["_facade_scope"]["excluded"] == {"stucco": 312, "brick": 234}
        assert m["_waste_pct"] == 0.10  # never silently 0
        assert m["_soffit_vented_sqft"] == 216
        assert m["_soffit_closed_sqft"] == 247
        assert m["_hover_source"] is True

    def test_basis_names_scope_and_openings_convention(self, pkg):
        label = pkg["geometry_basis"]["label"]
        assert "wrap-only scope 2064 of 2610" in label
        assert "stucco 312" in label and "brick 234" in label
        assert "openings: Hover net" in label

    def test_lap_248_wrap_only_ceil_once(self, pkg):
        assert _line(pkg, "38 Series Lap")["qty"] == 248

    def test_540_measured_perimeter_doors_3_side(self, pkg):
        l = _line(pkg, '540 Series Trim 5/4" x 4"')
        assert l["qty"] == 33
        assert "574.33" in l["note"] and "door bottoms" in l["note"]

    def test_osc_measured_lf_basis(self, pkg):
        l = _line(pkg, "540 Series OSC")
        assert l["qty"] == 9
        assert "140.33" in l["note"]

    def test_soffit_full_measured_total_composes(self, pkg):
        vented = _line(pkg, "38 Series Soffit 16 x 16 Vented")
        closed = _line(pkg, "38 Series Soffit 16 x 16 Closed")
        assert vented["qty"] == 12 and "216" in vented["note"]
        assert closed["qty"] == 13
        assert "ceiling 83" in closed["note"], "porch-ceiling mechanism named"

    def test_coil_never_composes_on_lp(self, pkg):
        assert not any("Coil" in l["name"] for l in pkg["lines"])

    def test_fascia_rake_unchanged(self, pkg):
        assert _line(pkg, '440 Series Trim 4/4" x 8"')["qty"] == 21

    def test_letrick_photo_path_untouched(self, session):
        """Per-source convention: photo runs keep Iter 57ee constants."""
        d = session.post(f"{API}/estimates/{LETRICK}/lp-package/preview", json={}, timeout=60).json()
        assert d["summary"]["pricing"]["total_sell"] == 11055.71
        l540 = _line(d, '540 Series Trim 5/4" x 4"')
        assert "MEASURED opening perimeter" not in l540["note"]


class TestRoundTwoFollowUps:
    """Follow-up rulings (2026-07-18): waste display sync, ISC measured-LF
    pooling with the ≤16' validity caveat, facade-breakdown picker schema."""

    def test_prompt_schema_pins_facade_breakdown(self):
        from routes.hover import PROMPT_TEMPLATE
        assert '"facade_breakdown"' in PROMPT_TEMPLATE
        for k in ("stucco_sqft", "brick_sqft", "stone_sqft", "metal_sqft"):
            assert k in PROMPT_TEMPLATE
        assert "never sum different materials" in PROMPT_TEMPLATE.lower()

    def test_contract_wrap_default_from_breakdown_never_silent_sum(self):
        from routes.lp_package_routes import _hover_mapping_contract
        m, flags = _hover_mapping_contract(
            {"siding_sqft": 2610,
             "facade_breakdown": {"siding_sqft": 2064, "stucco_sqft": 312,
                                  "brick_sqft": 234}},
            "lap")
        assert m["siding_sqft"] == 2064  # wrap default, NOT the 2610 sum
        assert m["_facade_scope"]["mode"] == "wrap_only"
        assert m["_facade_scope"]["excluded"] == {"stucco": 312, "brick": 234}
        assert any(f.get("code") == "facade_scope" for f in flags)

    def test_contract_explicit_picker_choice_overrides_default(self):
        from routes.lp_package_routes import _hover_mapping_contract
        m, _ = _hover_mapping_contract(
            {"siding_sqft": 2610,
             "facade_breakdown": {"siding_sqft": 2064, "stucco_sqft": 312,
                                  "brick_sqft": 234}},
            "lap",
            facade_scope={"mode": "custom", "wrap_sqft": 2376,
                          "excluded": {"brick": 234}})
        assert m["siding_sqft"] == 2376  # stucco explicitly included
        assert m["_facade_scope"]["excluded"] == {"brick": 234}

    def test_isc_measured_lf_pooling_cut_stock_yield(self):
        from lp_package import assemble_lp_package
        pkg = assemble_lp_package({"_hover_source": True,
                                   "inside_corner_count": 6,
                                   "inside_corner_lf": 36})
        l = _line(pkg, '440 Series Trim 4/4" x 4"')
        assert l["qty"] == 3  # pooled ceil(36 ÷ 16) — NOT 6 per-corner sticks
        assert "cut-stock yield" in l["note"]

    def test_isc_tall_corners_revert_to_splice_round_up(self):
        from lp_package import assemble_lp_package
        pkg = assemble_lp_package({"_hover_source": True,
                                   "inside_corner_count": 2,
                                   "inside_corner_lf": 36})  # 18' each > 16'
        l = _line(pkg, '440 Series Trim 4/4" x 4"')
        assert l["qty"] == 4  # 2 × ceil(18 ÷ 16) — validity caveat holds
        assert "splice-and-round-up" in l["note"]
        assert "cut-stock" not in l["note"]

    def test_waste_display_matches_application(self):
        from lp_package import assemble_lp_package
        from lp_smartside_formulas import DEFAULT_WASTE
        d = assemble_lp_package({"_hover_source": True, "siding_sqft": 1000})
        assert d["summary"]["waste_pct_applied"] == DEFAULT_WASTE  # 0.10, never silently 0
        z = assemble_lp_package({"_hover_source": True, "siding_sqft": 1000,
                                 "_waste_pct": 0.0})
        assert z["summary"]["waste_pct_applied"] == 0.0  # explicit override mirrors too

    def test_preview_endpoint_surfaces_waste_applied(self, pkg):
        assert pkg["summary"]["waste_pct_applied"] == 0.10
