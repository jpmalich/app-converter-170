"""CASILE CLOSE-OUT (rulings 2026-07-24) — founding pins.

1. SEALED CONVENTIONS GOVERN THE TABS: the pre-sealed tab formulas
   (÷16 × %waste) RETIRE. Whole-stick pooling, ISC pooling, and ruled
   waste treatment compute the corner/trim rows. Product widths,
   CONTRACTOR-SPEC confirmed: OSC = 5/4"×6" · fascia/rake trim = 4/4"×8".
2. LABOR IS THE CONTRACTOR'S — v3 ZEROING (sealed 2026-07-24): ALL labor
   defaults are $0 until the contractor fills them. The five provisional
   guesses (98/107/100/138/334) RETIRED ENTIRELY; the gutter $1.00/LF
   machine override ($280 on Jon) zeroed with them. The Price Catalog
   LABOR column is the standing labor home — no new card.
3. PORCH CEILINGS roll into the soffit derivation SERVER-SIDE on rebuild
   (Job-Info entries feed the Vented row — machinery accepts the ruling
   entry without the editor).
4. FAMILY-CHECK TRIPWIRE on readiness: >1 siding family with derived qty
   on the money surface raises a named conflict item.
5. Waste-included discipline: stick rows and ×1.10-inside formulas are
   exempt from the tab bake (the old bake double-wasted soffit 10%-on-10%
   and violated the batten row's own "no waste" note).
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")
from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

CASILE_EST = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def jon_rows(session):
    est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
    return {l["name"]: l for l in est["lines"] if l.get("tab") == "lp_smart"}


class TestSealedConventionsOnTheTab:
    def test_osc_is_6in_whole_stick(self, jon_rows):
        assert "540 Series OSC 5/4\" x 4\" x 16'" not in jon_rows  # retired SKU gone
        osc = jon_rows["540 Series OSC 5/4\" x 6\" x 16'"]
        # PIN AMENDED (Q13 ruled 2026-07-27, 3 Degree Rd sitting): per-
        # corner whole-stick round-up min 1 pc/corner — 20 corners × 1
        # (7.02' avg) = 20; the pooled ÷16 basis (was 9) RETIRES.
        assert osc["qty"] == 20
        assert not osc.get("raw_qty")
        assert (osc.get("mat") or 0) > 0  # catalog-bound, never a None/0 hole

    def test_440_8in_fascia_rake_whole_stick(self, jon_rows):
        t8 = jon_rows["440 Series Trim 4/4\" x 8\" x 16'"]
        assert t8["qty"] == 21            # (184.17 + 136.58) ÷ 16 whole-stick
        assert not t8.get("raw_qty")
        assert (t8.get("mat") or 0) > 0

    def test_440_4in_is_isc_pooling_only(self, jon_rows):
        # PIN AMENDED (Q12 ruled 2026-07-27): 540 5/4"×4" is the LP ISC
        # DEFAULT — the 440 4/4"×4" machine row RETIRES (substitution
        # option only); ISC sticks merge onto the 540 wrap line.
        assert "440 Series Trim 4/4\" x 4\" x 16'" not in jon_rows

    def test_stick_rows_carry_no_extra_bake(self, jon_rows):
        # PIN AMENDED (Q10/Q12/Q13 ruled 2026-07-27): 540-4" = wrap 33 +
        # frieze 23 + ISC 6 per-corner = 62 (was 33 wrap-only).
        assert jon_rows["540 Series Trim 5/4\" x 4\" x 16'"]["qty"] == 62
        # PIN AMENDED (Q9 ruled 2026-07-27): battens @8" o.c. — 2064 ft²
        # ÷ (2/3) = 3096 LF ÷ 16 = 194 (was 97 at the provisional 16").
        assert jon_rows["190 Series Trim 19/32\" x 3\" x 16'"]["qty"] == 194

    def test_soffit_single_waste_and_porch(self, jon_rows):
        # PIN AMENDED (Q14a ruled 2026-07-27): the measured Hover soffit
        # TOTAL governs over the overhang fallback — vented 11→14,
        # closed 8→11 on Jon's measured total (proportional split).
        assert jon_rows["38 Series Soffit 16 x 16 Vented"]["qty"] == 14
        assert jon_rows["38 Series Soffit 16 x 16 Closed"]["qty"] == 11

    def test_one_family_holds(self, jon_rows):
        # B&B family waste 30% (CONTRACTOR-SPEC, sealed 2026-07-24):
        # 2064 ft² ÷ 40 × 1.30 → 68 panels (was 57 at the flat 10%).
        assert jon_rows["38 Series 4' x 10' Panel"]["qty"] == 68
        # lap: absent (qty-0 rows drop on save; the catalog merge renders
        # them at 0) or present at exactly 0 — never a positive residue.
        lap = jon_rows.get('38 Series Lap 3/8" x 8" x 16\'')
        assert lap is None or lap["qty"] == 0


class TestLaborZeroedV3:
    """V3 ZEROING (sealed 2026-07-24): every labor line on the LP walk
    surface shows $0 with the 'contractor sets labor' state — no
    unflagged labor anywhere."""

    def test_five_misc_rows_zeroed_and_flagged(self, jon_rows):
        for name in ("Cap window", "Cap entry door", "Cap patio door",
                     "Cap single garage door", "clean up/ haul away job debris"):
            assert jon_rows[name]["lab"] == 0.0, name
            assert jon_rows[name]["lab_src"] == "pending", name

    def test_gutter_280_zeroed(self, jon_rows):
        # gutter $1.00/LF × 184 + downspout $1.00/LF × 96 = the $280
        assert jon_rows['Gutter 6"']["lab"] == 0.0
        assert jon_rows['Downspout 6"']["lab"] == 0.0

    def test_contractor_edit_still_wins(self, session):
        est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
        rows = {(l.get("tab"), l["name"]): l for l in est["lines"]}
        assert rows[("windows", "Cap window (Windows)")]["lab"] == 20.0

    def test_provisional_rates_retired_entirely(self):
        import lp_conventions
        assert not hasattr(lp_conventions, "PROVISIONAL_LABOR_RATES")
        assert not hasattr(lp_conventions, "LABOR_CONVENTIONS")

    def test_retired_set_carries_both_generations(self):
        from lp_conventions import MISC_LABOR_ROWS, RETIRED_LABOR_DEFAULTS
        # Q1 (ruled 2026-07-27): tear-off + dumpster join MISC_LABOR_ROWS
        # with NO retired machine generations (they never had defaults).
        assert set(RETIRED_LABOR_DEFAULTS) == set(MISC_LABOR_ROWS) - {"tear-off", "dumpster"}
        assert RETIRED_LABOR_DEFAULTS["cap window"] == {25.0, 98.0}
        assert RETIRED_LABOR_DEFAULTS["clean up/ haul away job debris"] == {150.0, 334.0}


class TestPorchCeilingServerSide:
    def test_ruling_entry_recorded(self, session):
        est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
        porches = est.get("porch_ceilings") or []
        assert any(abs((p.get("width_ft") or 0) * (p.get("length_ft") or 0) - 15.5) < 0.01
                   for p in porches), porches

    def test_rebuild_injects_porch_sqft(self):
        src = (BACKEND / "routes" / "hover.py").read_text()
        assert 'scoped["porch_ceiling_sqft"] = porch_sqft' in src
        assert '"porch_ceilings": 1' in src


class TestBookCheckAmendments:
    """2026-07-24 book-check rulings: family-defaulted waste + contractor-
    owned labor (provisional flags)."""

    def test_family_waste_defaults_sealed(self):
        from lp_conventions import FAMILY_WASTE_DEFAULTS, family_waste_default_pct
        assert FAMILY_WASTE_DEFAULTS == {"lap": 10.0, "board_batten": 30.0,
                                         "shake": 15.0, "nickel_gap": 12.0}
        assert family_waste_default_pct("board_batten") == 30.0
        # V3 book-check (sealed 2026-07-24): Shake 15 · Nickel Gap 12.
        assert family_waste_default_pct("shake") == 15.0
        assert family_waste_default_pct("nickel_gap") == 12.0

    def test_jon_field_prefilled_thirty(self, session):
        est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
        assert est["waste_pct"] == 30.0  # ONE visible, editable number

    def test_profile_selection_prefills_family_default(self, session):
        r = session.post(f"{API}/estimates", json={
            "kind": "lp_smart", "customer_name": "ZZ wastefill TEMP",
            "waste_pct": 10.0}, timeout=15)
        eid = r.json()["id"]
        try:
            rr = session.post(f"{API}/estimates/{eid}/default-profile",
                              json={"profile": "board_batten"}, timeout=15)
            assert rr.status_code == 200, rr.text
            est = session.get(f"{API}/estimates/{eid}", timeout=15).json()
            assert est["waste_pct"] == 30.0
        finally:
            session.delete(f"{API}/estimates/{eid}", timeout=15)

    def test_labor_rows_flagged_pending(self, jon_rows):
        for name in ("Cap window", "Cap entry door", "Cap patio door",
                     "Cap single garage door", "clean up/ haul away job debris"):
            assert jon_rows[name]["lab_src"] == "pending", name

    def test_readiness_states_labor_pending(self, session):
        rd = session.get(f"{API}/estimates/{CASILE_EST}/readiness", timeout=90).json()
        pend = [i for i in rd["items"] if i["kind"] == "labor_pending"]
        assert len(pend) == 1 and "contractor sets labor" in pend[0]["label"]
        assert "$0 until you enter your rates" in pend[0]["label"]

    def test_company_rate_endpoint_stores_contractor_rates(self, session):
        # use a name OUTSIDE the five pinned rows so Jon's provisional
        # walk stays exactly as booked (a stored company rate would
        # legitimately clear the flag — that's Jon's move, not the suite's).
        r = session.put(f"{API}/company/labor-rates",
                        json={"name": "ZZ Suite Probe Row", "rate": 125.0}, timeout=15)
        assert r.status_code == 200
        assert r.json()["labor_rates"]["zz suite probe row"] == 125.0
        r2 = session.put(f"{API}/company/labor-rates",
                         json={"name": "ZZ Suite Probe Row", "rate": 0}, timeout=15)
        assert r2.status_code == 200

    def test_ui_flags_and_roundtrip(self):
        acc = (BACKEND.parent / "frontend" / "src" / "components" / "estimate"
               / "SectionAccordion.jsx").read_text()
        assert "contractor sets labor" in acc
        assert "pending-labor-" in acc
        assert "onWheel={(e) => e.currentTarget.blur()}" in acc  # phantom-stamp footgun closed
        ue = (BACKEND.parent / "frontend" / "src" / "lib" / "useEstimate.js").read_text()
        assert 'lab_src: "human"' in ue                       # contractor edit wins
        assert "lab_src: l.lab_src || null" in ue             # save round-trip
        assert "/company/labor-rates" in ue                   # real rates become standing
        # labor-rate toast (AUTHORIZED 2026-07-24): visible confirmation
        assert "standing rate — future estimates will use it" in ue


class TestV3MoneyWalk:
    """WALK V3 pinned figures (lp_smart money surface, labor zeroed):
    mat $20,025.74 + 7% tax $1,401.80 + labor $0 → base $21,427.54;
    30% true margin → homeowner $30,610.77. V3's exact figures govern."""

    def test_lp_smart_walk_figures(self, session):
        est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
        assert est["tax_enabled"] and est["tax_rate"] == 7.0
        assert est["pricing_mode"] == "margin" and est["margin_pct"] == 30.0
        sub_mat = sub_lab = 0.0
        for l in est["lines"]:
            if (l.get("tab") or "vinyl") != "lp_smart":
                continue
            q = float(l.get("qty") or 0)
            sub_mat += q * float(l.get("mat") or 0)
            sub_lab += q * float(l.get("lab") or 0)
        assert round(sub_lab, 2) == 0.0        # labor-honest
        # PIN AMENDED (Q1–Q17 sitting, ruled 2026-07-27) — Jon Casile
        # BEFORE→AFTER walk (named delta, unprinted quote re-derives):
        #   battens 97→194 (Q9 8" o.c.)      +97 × 19.66 = +1907.02
        #   OSC 9→20 (Q13 per-corner)        +11 × 271.69 = +2988.59
        #   540-4" 33→62 (Q10 frieze+Q12 ISC) +29 × 34.30 = +994.70
        #   440-4"×4" 3→0 (Q12 merged)        row retired
        #   soffit V 11→14, C 8→11 (Q14)     +3×85.83 +3×73.50 = +477.99
        #   caulk 2→9, touch-up 1→2 (Q15)    +98.21 +60.96
        #   Tear-Off/Dumpster rows appear qty 0 pending (Q1)
        # sub_mat 20025.74 → 26468.61
        assert round(sub_mat, 2) == 26468.61   # materials-true
        tax = sub_mat * 0.07
        assert round(tax, 2) == 1852.80
        base = sub_mat + tax + sub_lab
        assert round(base, 2) == 28321.41
        sell = base / (1 - 0.30)
        assert round(sell, 2) == 40459.16

    def test_no_unflagged_labor_anywhere_on_walk_surface(self, session):
        est = session.get(f"{API}/estimates/{CASILE_EST}", timeout=30).json()
        for l in est["lines"]:
            if (l.get("tab") or "vinyl") not in ("vinyl", "ascend", "lp_smart"):
                continue
            if float(l.get("lab") or 0) > 0:
                assert (l.get("lab_src") or "") in ("human", "company"), l.get("name")


class TestFamilyCheckTripwire:
    def test_jon_is_clean(self, session):
        r = session.get(f"{API}/estimates/{CASILE_EST}/readiness", timeout=90)
        assert r.status_code == 200
        kinds = {it["kind"] for it in r.json()["items"]}
        assert "family_conflict" not in kinds

    def test_two_families_trip_the_wire(self, session):
        r = session.post(f"{API}/estimates", json={
            "kind": "lp_smart", "customer_name": "ZZ tripwire TEMP",
            "lines": [
                {"tab": "lp_smart", "section": "LP Smart Siding",
                 "name": '38 Series Lap 3/8" x 8" x 16\'', "unit": "PCS",
                 "qty": 10, "mat": 30.99, "lab": 0},
                {"tab": "lp_smart", "section": "LP Smart Siding",
                 "name": "38 Series 4' x 10' Panel", "unit": "PCS",
                 "qty": 5, "mat": 137.94, "lab": 0},
            ]}, timeout=15)
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        try:
            rr = session.get(f"{API}/estimates/{eid}/readiness", timeout=90)
            items = [it for it in rr.json()["items"] if it["kind"] == "family_conflict"]
            assert len(items) == 1
            assert "Profile owns its family" in items[0]["label"]
            # a HUMAN-typed second family is a choice, never a conflict
            lines = r.json()["lines"]
            lines[0]["qty_src"] = "human"
            session.put(f"{API}/estimates/{eid}", json={"lines": lines}, timeout=15)
            rr2 = session.get(f"{API}/estimates/{eid}/readiness", timeout=90)
            assert not [it for it in rr2.json()["items"] if it["kind"] == "family_conflict"]
        finally:
            session.delete(f"{API}/estimates/{eid}", timeout=15)

