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

from api_base import API  # env-derived (un-hardcoded 2026-07-23)
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
        # PIN AMENDED (hover waste unification, ruled 2026-07-20): the
        # contract no longer injects a silent 0.10 — hover-lp-run writes
        # 10.0 into the estimate's visible waste_pct field and the field
        # governs (_apply_contractor_waste). Explicit override still wins.
        assert "_waste_pct" not in m
        m_ovr, _ = _hover_mapping_contract(
            {"siding_sqft": 2610}, "lap", waste_pct=0.15)
        assert m_ovr["_waste_pct"] == 0.15
        assert m["_soffit_vented_sqft"] == 216
        assert m["_soffit_closed_sqft"] == 247
        assert m["_hover_source"] is True

    def test_basis_names_scope_and_openings_convention(self, pkg):
        label = pkg["geometry_basis"]["label"]
        assert "wrap-only scope 2064 of 2610" in label
        assert "stucco 312" in label and "brick 234" in label
        assert "openings: Hover net" in label

    def test_lap_250_wrap_only_book_formula(self, pkg):
        """PIN AMENDED (lap unification 2026-07-19; hover waste unification
        2026-07-20): piece formula sealed to the book — 11 pcs/sq.
        Wrap-only scope 2064 ft² × 1.10 (waste from the estimate's visible
        field — hover-lp-run writes 10.0 there on import) ÷ 100 × 11 =
        249.74 → 250. Ceil once."""
        assert _line(pkg, "38 Series Lap")["qty"] == 250

    def test_540_measured_perimeter_doors_3_side(self, pkg):
        """PIN AMENDED (Q10/Q12 ruled 2026-07-27): wrap 33 (measured perim
        574.33 − door bottoms ÷ 16) + FRIEZE consumed (level 215.67 →14 +
        sloped 129.83 →9 = 23, per-segment Q16) + ISC merged onto the same
        SKU (6 corners × per-corner round-up = 6, Q12/Q13) = 62."""
        l = _line(pkg, '540 Series Trim 5/4" x 4"')
        assert l["qty"] == 62
        assert "574.33" in l["note"] and "door bottoms" in l["note"]
        assert "FRIEZE (Q10" in l["note"] and "ISC 6" in l["note"]

    def test_osc_measured_lf_basis(self, pkg):
        """PIN AMENDED (Q13 ruled 2026-07-27): per-corner whole-stick
        round-up, min 1 pc/corner — 20 corners × 1 (7.02' avg) = 20;
        flat ÷16 pooling (was 9) retired."""
        l = _line(pkg, "540 Series OSC")
        assert l["qty"] == 20
        assert "per-corner whole-stick round-up" in l["note"]

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
        """Per-source convention: photo runs keep Iter 57ee constants.
        PIN AMENDED (chase ratification ruling, 2026-07-19): taped chase
        height 19.552' entered via the appendage machinery re-derives OSC
        7→8 sticks (per the ruled 2026-07-15 dims machinery — matches the
        sealed key's 8), moving total_sell 11055.71 → 11327.40.
        PIN AMENDED AGAIN (item-3 chase-siding ratification, ruled
        (item-3, ruled 2026-07-19): TAPED chase faces supersede the AI's
        130 ft² attribution (swap) → lap 227 → 230, total 11420.37.
        PIN AMENDED AGAIN (lap unification ruling, 2026-07-19): area
        key-bound 2099.7 (geometry-source rule extends to materials),
        book 11 pcs/sq sealed, waste to the contractor's field (Letrick
        field = 10%) → lap 230 → 255 (+25 × $30.99 = +$774.75) —
        total_sell 11420.37 → 12195.12. App line now equals the sealed
        key's 255 EXACTLY — residual zero.
        PIN AMENDED AGAIN (master-sheet binding, ruled 2026-07-23, Casile
        founding example): sheet-bound rows (gutter run) now price from
        the company master sheet + overrides instead of pending — 8 rows
        +852.40 (Gutter 6\" 100×4.25 + Downspout 46×3.80 + elbow/end cap/
        hangars/mitre/pipe clips/sealant) → total_sell 13047.52. Cap
        window / Cap entry door / cleanup stay pending ($0.00 on every
        tier sheet — escalated by name, never placeholder).
        ONE MONEY SURFACE (2026-07-23): contractor preview is unpriced —
        this dollar pin rides the supplier-admin cost-preview.
        AMENDED AGAIN (labor conventions, Howard's prices 2026-07-23):
        the escalated rows bind from his standing defaults — Cap window
        9×98 + Cap entry door 2×107 + cleanup 334 = +1430.00 → 14477.52
        (close-out labor prices, ruled 2026-07-24).
        AMENDED AGAIN (V3 ZEROING, sealed 2026-07-24): ALL labor = $0
        until the contractor fills it — the +1430.00 conventions RETIRE
        (misc rows price $0, labor is the contractor's) and the healed
        gutter/downspout $1.00/LF machine lab overrides drop −146.00
        (Gutter 100×3.25 + Downspout 46×2.80) → total_sell 12901.52.
        AMENDED AGAIN (Q12 ruled 2026-07-27, 3 Degree Rd sitting): ISC
        default re-SKUs 440 4/4"×4" → 540 5/4"×4" (merged onto the wrap
        line) — Letrick's 2 ISC sticks reprice at the 540 rate →
        total_sell 12901.52 → 13037.21 (+135.69).
        AMENDED AGAIN (register #5 CAULK ruled 2026-07-28): flat 2/job
        RETIRED — LP non-B&B = 1 tube per SQUARE (SmartSide butt joints
        take sealant). Letrick key-bound 2099.7 ft² = 21 SQ → OSI Quad
        Max 2 → 21 tubes (+19 × $14.03 = +$266.57) → total_sell
        13037.21 → 13303.78. B&B jobs hold at the sealed 1/23 sticks
        (Casile unchanged at 9 — pinned in test_casile_closeout).
        SALES UNIT (ruled 2026-07-31): downspout LF → 10' sticks moved
        Letrick 46 LF ($128.80) → 5 sticks ($140.00): 13303.78 → 13314.98."""
        import os
        tok = os.environ.get("TEST_ADMIN_TOKEN") or os.environ.get("SUPPLIER_ADMIN_TOKEN", "")
        d = session.post(f"{API}/admin/estimates/{LETRICK}/lp-package/cost-preview",
                         json={}, headers={"X-Admin-Token": tok}, timeout=60).json()
        assert d["summary"]["pricing"]["total_sell"] == 13314.98
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

    def test_isc_per_corner_round_up_q13(self):
        """Q13 (ruled 2026-07-27): PER-CORNER whole-stick round-up, min 1
        pc/corner — measured-LF cut-stock pooling RETIRED. ISC lands on
        the 540-4" SKU (Q12) merged with the wrap line."""
        from lp_package import assemble_lp_package
        pkg = assemble_lp_package({"_hover_source": True,
                                   "inside_corner_count": 6,
                                   "inside_corner_lf": 36})
        l = _line(pkg, '540 Series Trim 5/4" x 4"')
        assert l["qty"] == 6  # 6 × max(1, ceil(6 ÷ 16)) — NOT pooled 3
        assert "per-corner whole-stick round-up" in l["note"]
        assert "cut-stock" not in l["note"]

    def test_isc_tall_corners_two_sticks_each_q13(self):
        from lp_package import assemble_lp_package
        pkg = assemble_lp_package({"_hover_source": True,
                                   "inside_corner_count": 2,
                                   "inside_corner_lf": 36})  # 18' each > 16'
        l = _line(pkg, '540 Series Trim 5/4" x 4"')
        assert l["qty"] == 4  # 2 × ceil(18 ÷ 16) = 4
        assert "per-corner whole-stick round-up" in l["note"]

    def test_waste_display_matches_application(self):
        """Display-sync invariant (ruled 2026-07-18) holds under the
        no-silent-waste seal (ruled 2026-07-19): assemble reports exactly
        what it applied. Missing _waste_pct now applies AND reports 0
        (DEFAULT_WASTE auto-default RETIRED — waste is the contractor's);
        the Hover ruled 10% default is set EXPLICITLY at the hover
        boundary (routes/hover.py) and still surfaces as 0.10 end-to-end
        (see test_preview_endpoint_surfaces_waste_applied)."""
        from lp_package import assemble_lp_package
        d = assemble_lp_package({"_hover_source": True, "siding_sqft": 1000})
        assert d["summary"]["waste_pct_applied"] == 0.0  # applied 0, reported 0 — in sync
        z = assemble_lp_package({"_hover_source": True, "siding_sqft": 1000,
                                 "_waste_pct": 0.0})
        assert z["summary"]["waste_pct_applied"] == 0.0  # explicit override mirrors too

    def test_preview_endpoint_surfaces_waste_applied(self, pkg):
        assert pkg["summary"]["waste_pct_applied"] == 0.10
