"""WASTE RE-DERIVES LIVE (Howard ruled 2026-08-03). Found live on
EST-803966: estimate panel 138 ($19,035.72 built on it), material list
106 — the waste field changed 30→0 and the estimate did not move. The
frozen-number class. RULING: waste is a spec field; it re-derives the
estimate live through the same /rederive door every other spec field
uses; both surfaces read ONE panel quantity. Self-cleaning."""
import math
import os
import re
import uuid

import pytest
import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", "")

SR_PATH = "/app/frontend/src/components/estimate/SettingsRow.jsx"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture()
def lp_est(s):
    """Disposable lp_smart estimate shaped like EST-803966: board-batten
    measurements stored, LP tab lines materialized via /rederive."""
    made = []
    r = s.post(f"{API}/estimates",
               json={"customer_name": f"TEST_WASTE-{uuid.uuid4().hex[:6]}",
                     "kind": "lp_smart"})
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    made.append(eid)
    src = s.get(f"{API}/estimates/a71531e4-9e0e-4b3d-a6e3-e2e6005739d4").json()
    meas = src.get("hover_measurements")
    assert meas, "EST-803966 must carry stored measurements"
    r = s.put(f"{API}/estimates/{eid}",
              json={"hover_measurements": meas, "waste_pct": 30,
                    "default_siding_profile": src.get("default_siding_profile"),
                    "batten_spacing_in": src.get("batten_spacing_in"),
                    "fascia_width_in": src.get("fascia_width_in"),
                    "panel_size": src.get("panel_size"),
                    "wrap_trim_width_in": src.get("wrap_trim_width_in"),
                    "overhang_in": src.get("overhang_in")})
    assert r.status_code == 200, r.text
    # default_siding_profile is set by the LP flow (not the generic PUT —
    # silent-strip by design); seed it the way real LP estimates carry it.
    from pymongo import MongoClient
    db = MongoClient(_ENV["MONGO_URL"])[_ENV["DB_NAME"]]
    db.estimates.update_one(
        {"id": eid},
        {"$set": {"default_siding_profile": src.get("default_siding_profile")}})
    # Clone the governing run so the Material List surface composes on the
    # disposable exactly as it does on EST-803966.
    run = db.ai_measure_runs.find_one(
        {"run_id": "hover-2e9e987a69b9-board_batten"}, {"_id": 0})
    assert run, "EST-803966 governing run must exist"
    run["run_id"] = f"test-waste-{uuid.uuid4().hex[:8]}"
    run["estimate_id"] = eid
    run["test_artifact"] = True
    db.ai_measure_runs.insert_one(dict(run))
    yield eid
    db.ai_measure_runs.delete_one({"run_id": run["run_id"]})
    for e in made:
        s.delete(f"{API}/estimates/{e}")


def _panel_qty(lines):
    row = next((l for l in lines
                if l.get("name") == "38 Series 4' x 10' Panel"), None)
    return row["qty"] if row else None


def test_rederive_reads_the_current_waste_field(s, lp_est):
    """30% → ceil(sqft×1.30÷40); 0% → ceil(sqft÷40). The SAME door,
    the CURRENT field, every call."""
    sqft = s.get(f"{API}/estimates/{lp_est}").json()["hover_measurements"]["siding_sqft"]
    r30 = s.post(f"{API}/estimates/{lp_est}/rederive",
                 json={"trigger": "spec-save", "waste_pct": 30})
    assert r30.status_code == 200, r30.text
    assert _panel_qty(r30.json()["lines"]) == math.ceil(sqft * 1.30 / 40 - 1e-9)
    s.put(f"{API}/estimates/{lp_est}", json={"waste_pct": 0})
    r0 = s.post(f"{API}/estimates/{lp_est}/rederive",
                json={"trigger": "spec-save", "waste_pct": 0})
    assert _panel_qty(r0.json()["lines"]) == math.ceil(sqft / 40 - 1e-9)


def test_both_surfaces_read_one_panel_quantity(s, lp_est):
    """ONE SOURCE: after a waste change re-derives, the stored estimate
    line and the material-list composition carry the SAME panel count —
    at 30 and at 0."""
    for pct in (30, 0):
        s.put(f"{API}/estimates/{lp_est}", json={"waste_pct": pct})
        s.post(f"{API}/estimates/{lp_est}/rederive",
               json={"trigger": "spec-save", "waste_pct": pct})
        est_q = _panel_qty(s.get(f"{API}/estimates/{lp_est}").json()["lines"])
        pkg = s.post(f"{API}/estimates/{lp_est}/lp-package/preview", json={})
        assert pkg.status_code == 200, pkg.text
        ml_q = _panel_qty(pkg.json()["lines"])
        assert est_q == ml_q, (
            f"waste {pct}%: estimate says {est_q}, material list says {ml_q}"
            " — the frozen-number class is back")


def test_waste_roundtrip_is_byte_identical(s, lp_est):
    """Flip 30 → 0 → 30 through the rederive door: the lines come back
    byte-identical — nothing but waste moved, and it moved back."""
    def snap(pct):
        s.put(f"{API}/estimates/{lp_est}", json={"waste_pct": pct})
        r = s.post(f"{API}/estimates/{lp_est}/rederive",
                   json={"trigger": "spec-save", "waste_pct": pct})
        return r.json()["lines"]
    first = snap(30)
    snap(0)
    again = snap(30)
    assert first == again, "waste round-trip moved a number that is not waste"


@pytest.fixture()
def haugh_copy(s):
    """Byte-copy of 261 Haugh — the estimate carrying a CLOSED
    ceiling_dedup flag (duplicate 40 sqft), where the compounding was
    caught. Fixture untouched; copy deleted."""
    from pymongo import MongoClient
    db = MongoClient(_ENV["MONGO_URL"])[_ENV["DB_NAME"]]
    src = db.estimates.find_one(
        {"id": "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"}, {"_id": 0})
    assert (src.get("lp_flag_checklist") or {}).get(
        "ceiling_dedup", {}).get("status") == "closed"
    doc = dict(src)
    doc["id"] = str(uuid.uuid4())
    doc["customer_name"] = f"TEST_WASTE-haugh-{uuid.uuid4().hex[:6]}"
    db.estimates.insert_one(dict(doc))
    yield doc["id"], db
    db.estimates.delete_one({"id": doc["id"]})


def test_ceiling_dedup_fold_does_not_compound(s, haugh_copy):
    """REGRESSION (found 2026-08-03): every /rederive call was
    re-deducting duplicate_sqft from the already-deducted soffit
    (423→383→343→…) because the endpoint persists its own scoped output.
    The fold now deducts from the PRE-DEDUP base — call it five times,
    the measurement does not move."""
    eid, db = haugh_copy
    seen = []
    for _ in range(5):
        r = s.post(f"{API}/estimates/{eid}/rederive",
                   json={"trigger": "spec-save", "waste_pct": 30})
        assert r.status_code == 200, r.text
        m = db.estimates.find_one(
            {"id": eid}, {"_id": 0, "hover_measurements.soffit_sqft": 1})
        seen.append(m["hover_measurements"]["soffit_sqft"])
    assert len(set(seen)) == 1, f"soffit_sqft compounding again: {seen}"
    assert seen[0] == 423.0, f"dedup base wrong: {seen[0]} (463 hover − 40 dup)"


def test_haugh_shape_waste_roundtrip_byte_identical(s, haugh_copy):
    """Howard's acceptance on the Haugh shape: flip waste 30 → 0 → 30
    through the rederive door — lines byte-identical; nothing but waste
    moved, and it moved back."""
    eid, _db = haugh_copy
    def snap(pct):
        s.put(f"{API}/estimates/{eid}", json={"waste_pct": pct})
        return s.post(f"{API}/estimates/{eid}/rederive",
                      json={"trigger": "spec-save", "waste_pct": pct}).json()["lines"]
    first = snap(30)
    snap(0)
    again = snap(30)
    assert first == again, "Haugh-shape waste round-trip moved a non-waste number"


def test_waste_field_is_wired_to_the_rederive_door():
    """FRONTEND PIN: updateWastePct calls /rederive with the new pct —
    the client-only recompute (raw_qty rows) is no longer the only path.
    lp_smart is gated on derived rows existing (dollars on apply)."""
    src = open(SR_PATH).read()
    fn = src[src.index("const updateWastePct"):]
    fn = fn[:fn.index("const recomputeAllNow")]
    assert "/rederive" in fn, "waste field lost its rederive wiring — frozen again"
    assert "waste_pct: newPct" in fn
    assert re.search(r'est\.kind === "lp_smart" && hasLpDerived', fn), \
        "a waste change must never materialize LP lines as a side effect"
    assert "recomputeWasteQtys" in fn, "instant raw_qty recompute dropped"
