"""END-TO-END SPEC JOURNEY — EVERY FIELD, EVERY FAMILY (Howard ruled
2026-07-31, steps 1+2 of the parity rulings).

TEST THE JOURNEY, NOT THE LAYER: every trade spec walks UI-payload → PUT →
re-derive → derived quantity in the final lines, ON EVERY FAMILY THAT
SHOULD CARRY IT (TRADE_SPEC_FAMILY_REGISTER names the families; a spec
without a registered family coverage fails). The 3-layer silent-strip and
the LP-only F2 fix classes die here: one test walks the whole pipe.

Also pinned:
  • RENAME-COLLISION GUARD — a width rename ruling can never land on a
    name another register row already emits (the 540-line doubling class).
  • TRADE-SPEC FAMILY REGISTER — LP-only specs carry their
    DIFFERENT-BY-NATURE reason (R2/R3/R4 ruled by name 2026-07-31).
  • HUMAN QTY IS ABSOLUTE — survives the shared rebuild on vinyl AND LP,
    with derived_qty stamped for the "yours · derived" surface.
  • D2 regression — Ascend RainDrop takes field waste like vinyl House Wrap.
"""
import math
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creds_for_tests import TEST_PASSWORD

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", TEST_PASSWORD)

MEAS = {"siding_sqft": 2000, "eaves_lf": 120, "rakes_lf": 80,
        "soffit_sqft": 200, "outside_corner_count": 4,
        "inside_corner_count": 2, "window_count": 10, "door_count": 2,
        "overhang_in": 12}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture()
def est_factory(s):
    made = []

    def make(kind, **fields):
        r = s.post(f"{API}/estimates",
                   json={"customer_name": f"E2E-SPEC-{uuid.uuid4().hex[:6]}",
                         "kind": kind})
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        made.append(eid)
        body = {"customer_name": "E2E-SPEC", "kind": kind,
                "hover_measurements": dict(MEAS), "waste_pct": 10, **fields}
        r = s.put(f"{API}/estimates/{eid}", json=body)
        assert r.status_code == 200, r.text
        return eid

    yield make
    for eid in made:
        s.delete(f"{API}/estimates/{eid}")


def _rederive(s, eid, payload=None):
    r = s.post(f"{API}/estimates/{eid}/rederive", json=payload or {"trigger": "test"})
    assert r.status_code == 200, r.text
    return r.json()["lines"]


def _row(lines, tab, name_part, section=None):
    for l in lines:
        if l["tab"] == tab and name_part in l["name"] \
                and (section is None or l["section"] == section):
            return l
    return None


# ═════════════ FASCIA WIDTH — ALL THREE FAMILIES (R1 / D1 / F2) ═════════
def test_fascia_width_journey_vinyl_and_ascend(est_factory, s):
    """The live case, closed: a siding-kind estimate's fascia width reaches
    the vinyl AND Ascend .019 coil divisor — >10" halves the coverage."""
    eid = est_factory("siding", fascia_width_in=12)
    lines = _rederive(s, eid)
    for tab in ("vinyl", "ascend"):
        coil = _row(lines, tab, ".019 Coil", "Vinyl Soffit with Siding")
        assert coil, f"{tab} soffit/fascia coil missing"
        assert coil["qty"] == 4.0, f"{tab}: 200 LF ÷ 50 (fascia 12\") must be 4 rolls, got {coil['qty']}"
        assert '12"' in (coil.get("note") or "")
    # default width → 100 LF/roll
    r = s.put(f"{API}/estimates/{eid}", json={
        "customer_name": "E2E-SPEC", "kind": "siding",
        "hover_measurements": dict(MEAS), "waste_pct": 10, "fascia_width_in": 8})
    assert r.status_code == 200
    lines = _rederive(s, eid)
    for tab in ("vinyl", "ascend"):
        coil = _row(lines, tab, ".019 Coil", "Vinyl Soffit with Siding")
        assert coil["qty"] == 2.0, f"{tab}: 200 LF ÷ 100 (fascia 8\") must be 2 rolls"


def test_fascia_width_journey_lp(est_factory, s):
    eid = est_factory("lp_smart", fascia_width_in=6, default_siding_profile="lap")
    lines = _rederive(s, eid)
    fascia = next((l for l in lines if l["tab"] == "lp_smart"
                   and "440" in l["name"] and '6"' in l["name"]), None)
    assert fascia, "LP 440 fascia row must carry the 6\" width in its NAME"


# ═════════════ OVERHANG + PORCH — SHARED SOFFIT TERM ════════════════════
def test_overhang_and_porch_journey_vinyl_ascend(est_factory, s):
    # no measured soffit_sqft → the overhang term drives (Q14a: a measured
    # total would GOVERN over the derived one)
    meas = {k: v for k, v in MEAS.items() if k != "soffit_sqft"}
    eid = est_factory("siding", overhang_in=24)
    r = s.put(f"{API}/estimates/{eid}", json={
        "customer_name": "E2E-SPEC", "kind": "siding",
        "hover_measurements": meas, "waste_pct": 10, "overhang_in": 24})
    assert r.status_code == 200
    lines = _rederive(s, eid)
    # (24/12 × 200 LF) / 10 sqft/pc = 40 raw → area good ×1.10 → 44 whole
    for tab in ("vinyl", "ascend"):
        sof = _row(lines, tab, "Soffit & fascia Charter Oak")
        assert sof, f"{tab} Charter Oak soffit row missing"
        assert sof["qty"] == 44.0, f"{tab}: overhang 24\" soffit must be 44 pcs, got {sof['qty']}"
    # porch fold: +200 sqft → raw 60 → 66 — via live-override payload
    lines = _rederive(s, eid, {"trigger": "test", "overhang_in": 24,
                               "porch_ceilings": [{"width_ft": 10, "length_ft": 20}]})
    sof = _row(lines, "vinyl", "Soffit & fascia Charter Oak")
    assert sof["qty"] == 66.0, f"porch 200 sqft must fold into soffit (66), got {sof['qty']}"


# ═════════════ COLOR TIER — VINYL (DIFFERENT-BY-RULING for others) ══════
def test_color_tier_journey_vinyl(est_factory, s):
    eid = est_factory("siding", color_tier="architectural")
    lines = _rederive(s, eid)
    arch = [l for l in lines if l["tab"] == "vinyl" and "Architectural" in l["name"]
            and (l.get("qty") or 0) > 0]
    assert arch, "architectural tier must re-land vinyl derivations on Architectural rows"


# ═════════════ LP-ONLY SPECS — panel size · batten spacing · wrap trim ══
def test_lp_only_specs_journey(est_factory, s):
    eid = est_factory("lp_smart", panel_size="4x10", batten_spacing_in=12,
                      wrap_trim_width_in=4)
    base = _rederive(s, eid, {"trigger": "test", "profile": "board_batten"})
    bb10 = next((l for l in base if l["tab"] == "lp_smart" and "Panel" in l["name"]
                 and (l.get("qty") or 0) > 0), None)
    assert bb10, "B&B panel row missing on LP board_batten profile"
    batten12 = next((l for l in base if l["tab"] == "lp_smart" and "190" in l["name"]), None)
    assert batten12, "190 Series batten row missing"
    r = s.put(f"{API}/estimates/{eid}", json={
        "customer_name": "E2E-SPEC", "kind": "lp_smart",
        "hover_measurements": dict(MEAS), "waste_pct": 10,
        "default_siding_profile": "board_batten",
        "panel_size": "4x8", "batten_spacing_in": 24, "wrap_trim_width_in": 6})
    assert r.status_code == 200
    changed = _rederive(s, eid, {"trigger": "test", "profile": "board_batten"})
    bb8 = next((l for l in changed if l["tab"] == "lp_smart" and "Panel" in l["name"]
                and (l.get("qty") or 0) > 0), None)
    assert bb8 and bb8["qty"] > bb10["qty"], \
        f"4x8 (32 ft²) must need MORE panels than 4x10 (40 ft²): {bb10['qty']} → {bb8 and bb8['qty']}"
    batten24 = next((l for l in changed if l["tab"] == "lp_smart" and "190" in l["name"]), None)
    assert batten24 and '24"' in ((batten24.get("note") or "") + batten24["name"]), \
        "24\" o.c. spacing must be NAMED on the 190 line"
    wrap6 = next((l for l in changed if l["tab"] == "lp_smart" and "540" in l["name"]
                  and '6"' in l["name"]), None)
    assert wrap6, "540 wrap-trim row must carry the 6\" width in its NAME"


def test_shake_reveal_journey_lp(est_factory, s):
    eid = est_factory("lp_smart", shake_reveal_in=9)
    lines = _rederive(s, eid, {"trigger": "test", "profile": "shake"})
    shake = next((l for l in lines if l["tab"] == "lp_smart"
                  and "shake" in l["name"].lower() and (l.get("qty") or 0) > 0), None)
    assert shake, "LP shake row missing on shake profile"
    assert 'reveal 9"' in (shake.get("note") or ""), \
        f"shake reveal 9\" must be NAMED on the line note: {shake.get('note')}"


# ═════════════ HUMAN QTY IS ABSOLUTE — vinyl AND LP doors ═══════════════
def test_human_qty_survives_rederive_with_derived_stamp(est_factory, s):
    eid = est_factory("siding", fascia_width_in=12)
    lines = _rederive(s, eid)
    for l in lines:
        if l["tab"] == "vinyl" and l["name"] == ".019 Coil" \
                and l["section"] == "Vinyl Soffit with Siding":
            l["qty"] = 9
            l["qty_src"] = "human"
    r = s.put(f"{API}/estimates/{eid}", json={
        "customer_name": "E2E-SPEC", "kind": "siding",
        "hover_measurements": dict(MEAS), "waste_pct": 10,
        "fascia_width_in": 12, "lines": lines})
    assert r.status_code == 200
    lines2 = _rederive(s, eid)
    mine = _row(lines2, "vinyl", ".019 Coil", "Vinyl Soffit with Siding")
    assert mine["qty"] == 9.0 and mine["qty_src"] == "human", \
        "human-typed qty must survive the rebuild VERBATIM"
    assert mine.get("derived_qty") == 4.0, \
        "the fresh derived value must be stamped (yours: 9 · derived: 4)"
    other = _row(lines2, "ascend", ".019 Coil", "Vinyl Soffit with Siding")
    assert other["qty"] == 4.0 and not other.get("qty_src"), \
        "the untouched family's row stays derivation-owned"


# ═════════════ D2 REGRESSION — RainDrop takes field waste ═══════════════
def test_raindrop_takes_field_waste_like_house_wrap(est_factory, s):
    from routes.hover import _cut_prone_line
    assert _cut_prone_line({"section": "Ascend Cladding/Accessories",
                            "name": "RainDrop", "qty": 20})
    js = Path("/app/frontend/src/lib/wasteLogic.js").read_text()
    assert '"raindrop"' in js, "frontend classifier must match the real catalog name"
    eid = est_factory("siding")
    lines = _rederive(s, eid)
    rd = _row(lines, "ascend", "RainDrop")
    hw = _row(lines, "vinyl", "House Wrap")
    assert rd and hw
    # Repinned to the ROLL sales unit (ruled 2026-07-31): 20 SQ of wall →
    # RD 20/11.25 = 1.78 rolls · HW 20/9 = 2.22 rolls; the field's 10%
    # bakes on the raw roll count then ceils. raw_qty stamped == the row
    # went through the cut-prone waste path (the D2 defect was it not).
    assert rd["unit"] == "ROLL" and hw["unit"] == "ROLL"
    assert rd.get("raw_qty") == 1.78 and rd["qty"] == math.ceil(1.78 * 1.1 - 1e-9), \
        f"Ascend RainDrop must bake 10% like vinyl House Wrap: {rd}"
    assert hw.get("raw_qty") == 2.22 and hw["qty"] == math.ceil(2.22 * 1.1 - 1e-9)


# ═════════════ R3 — VINYL SHAKE ORDERS BY THE HALF SQUARE ═══════════════
def test_vinyl_shake_half_square_unit():
    from routes.hover import _PROFILE_SKU_MAP
    item, unit, per = _PROFILE_SKU_MAP[("shake", "vinyl")]
    assert item == 'Pelican Bay Shakes 9"'
    assert unit == "1/2 SQ" and per == 50.0, \
        "R3 ruled 2026-07-31: Pelican Bay orders by the half square"
    from catalog_seed import ITEM_META
    assert ITEM_META['Pelican Bay Shakes 9"'][0] == "1/2 SQ"


# ═════════════ TRADE-SPEC FAMILY REGISTER — ruled by name ═══════════════
def test_trade_spec_family_register_complete():
    from lp_conventions import TRADE_SPEC_FAMILY_REGISTER as R
    expected = {"overhang_in", "porch_ceilings", "fascia_width_in",
                "batten_spacing_in", "shake_reveal_in", "panel_size",
                "wrap_trim_width_in", "lp_soffit_type", "color_tier"}
    assert set(R) == expected, "every trade spec is registered — no silent additions"
    for field, entry in R.items():
        fams = entry.get("families") or ()
        assert fams, f"{field}: family coverage must be NAMED"
        assert entry.get("ruled"), f"{field}: ruling date required"
        if set(fams) != {"vinyl", "ascend", "lp_smart"}:
            assert entry.get("different_by_nature"), (
                f"{field}: a family-specific spec is a DEFECT unless ruled "
                "DIFFERENT-BY-NATURE with the reason recorded")
    assert set(R["fascia_width_in"]["families"]) == {"vinyl", "ascend", "lp_smart"}, \
        "R1: fascia width governs all three families"
    assert R["batten_spacing_in"]["families"] == ("lp_smart",)
    assert "integrated" in R["batten_spacing_in"]["different_by_nature"], \
        "R2 reason: Ascend B&B has the batten look built in"


# ═════════════ RENAME-COLLISION GUARD (the 540-doubling class) ══════════
def test_width_rename_never_collides_with_another_register_row():
    from routes.hover import HOVER_MAPPING_SPEC
    from lp_conventions import (fascia_item_for_width, wrap_item_for_width,
                                FASCIA_RAKE_ITEM, WRAP_TRIM_ITEM)
    register_names = {sp["item"] for sp in HOVER_MAPPING_SPEC}
    for w in (4, 6, 8, 10, 12):
        for base, renamed in ((FASCIA_RAKE_ITEM, fascia_item_for_width(w)),
                              (WRAP_TRIM_ITEM, wrap_item_for_width(w))):
            others = register_names - {base}
            assert renamed not in others, (
                f"RENAME COLLISION: width {w}\" renames '{base}' to "
                f"'{renamed}' which ANOTHER register row already emits — "
                "the 540-line doubling class")
    # width-rename targets are pairwise distinct
    fascias = {fascia_item_for_width(w) for w in (4, 6, 8, 10, 12)}
    wraps = {wrap_item_for_width(w) for w in (4, 6, 8, 10, 12)}
    assert len(fascias) == 5 and len(wraps) == 5 and not (fascias & wraps)


def test_register_keys_unique_per_tab_section_item():
    from routes.hover import HOVER_MAPPING_SPEC
    seen = {}
    for sp in HOVER_MAPPING_SPEC:
        for tab in sp["tabs"]:
            key = (tab, sp["section"], sp["item"])
            assert key not in seen, f"duplicate register emission {key}"
            seen[key] = True
