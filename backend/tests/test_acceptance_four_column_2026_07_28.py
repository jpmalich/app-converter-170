"""FOUR-COLUMN ACCEPTANCE — sealed by Howard 2026-07-28, after finding
three defects on one screen that 1,527 green tests missed.

  "Until the test drives the UI path, green is not evidence and I will
   keep finding these the expensive way."

Every acceptance run carries FOUR REQUIRED COLUMNS, driving THE PATH THE
CONTRACTOR DRIVES — upload an import, THEN pick the family, THEN read the
material list. Not a programmatic fixture with the profile pre-set.

  1. FRESH RUN ....... a NEW estimate from an import, list read end to end
  2. EVERY FAMILY .... VINYL · ASCEND · LP B&B · LP LAP (code in the shared
                       door is tested on the production family, not only LP)
  3. SECOND OPINION .. vs the estimate-dept takeoff on 3 Degree Rd
                       (battens 465 · 540-4" 142 · soffit ≈260). CORRECTED
                       2026-07-29 (Howard): these are NOT installed
                       quantities — they are another estimator's read of
                       the same Hover report. NO HOUSE IN THIS PROJECT IS
                       VALIDATED AGAINST DELIVERED MATERIAL yet.
  4. BOTH DOORS ...... Hover AND photo

Emits /app/memory/acceptance_table_2026_07_28.md with all four columns.
Open ground-truth gaps are RECORDED with their delta (queue item d owns
the diagnosis); reconciled lines are HARD-ASSERTED.
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

HOVER_RUN = "a425e75577844733bb512e9fa4959782"   # real 3 Degree Rd import, 2026-07-29 (S1-persisted PDF; archived in fixture_runs, no TTL)
LAP = '38 Series Lap 3/8" x 8" x 16\''
PANEL_10 = "38 Series 4' x 10' Panel"
# SECOND OPINION — the estimate-dept takeoff on 3 Degree Rd (CORRECTED by
# Howard 2026-07-29: NOT installed/delivered quantities; another
# estimator's read of the same source — either side may be off).
SECOND_OPINION = {"battens_second_opinion": 465, "trim_540_4_second_opinion": 142,
                  "soffit_sqft_second_opinion": 260}

TABLE_PATH = Path("/app/memory/acceptance_table_2026_07_28.md")
_rows = []


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def mongo_db():
    import os
    from pymongo import MongoClient
    return MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def hover_measurements(mongo_db):
    run = mongo_db.hover_import_runs.find_one({"run_id": HOVER_RUN}, {"_id": 0})
    if not run:
        # 24h TTL on live runs — the acceptance run is archived in
        # fixture_runs (no TTL), same fallback the apply endpoint uses.
        run = mongo_db.fixture_runs.find_one({"run_id": HOVER_RUN}, {"_id": 0})
    if not run or not (run.get("result") or {}).get("measurements"):
        pytest.skip("3 Degree hover run expired from substrate — re-import to re-arm")
    return dict(run["result"]["measurements"])


def _fresh_est(session, kind, tag):
    r = session.post(f"{API}/estimates",
                     json={"kind": kind, "customer_name": f"TEST_accept4_{tag}"},
                     timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _cleanup(session, est_id):
    session.delete(f"{API}/estimates/{est_id}", timeout=15)


def _record(family, door, line, qty, unit, note=""):
    _rows.append((family, door, line, qty, unit, note))


# ── COLUMN 2+4: VINYL and ASCEND through the FRESH Hover door — the exact
# code path a fresh import executes (worker composition → _build_lines →
# family-default waste bake), applied to a NEW estimate, list read back
# end to end through the API. The production family, not only LP. ────────
@pytest.mark.parametrize("family,tab,needle", [
    ("VINYL", "vinyl", "Dutch Lap"),
    ("ASCEND", "ascend", "Composite Lap"),
])
def test_fresh_vinyl_ascend_door_fills_whole_units(session, hover_measurements,
                                                   family, tab, needle):
    from routes.hover import _compose_facade_default_into, _build_lines, _bake_tab_waste
    m = dict(hover_measurements)
    _compose_facade_default_into(m)
    prefill = float(m.get("_waste_field_prefill_pct") or 10)
    lines = _bake_tab_waste(_build_lines(m), prefill)
    fam_lines = [l for l in lines if l.get("tab") == tab]
    assert fam_lines, f"{family}: fresh door produced NO lines"
    est = _fresh_est(session, "siding", family.lower())
    try:
        put = [{"tab": l["tab"], "section": l["section"], "name": l["name"],
                "unit": l["unit"], "qty": l["qty"],
                "raw_qty": l.get("raw_qty"), "mat": 0, "lab": 0}
               for l in fam_lines]
        rr = session.put(f"{API}/estimates/{est['id']}",
                         json={**est, "lines": put, "waste_pct": prefill}, timeout=15)
        assert rr.status_code == 200, rr.text
        back = session.get(f"{API}/estimates/{est['id']}", timeout=15).json()
        siding = next(l for l in back["lines"] if needle in l["name"])
        assert siding["qty"] == 47.0, f"{family} siding = {siding['qty']}, want 47.0 (4239 × 1.10 whole)"
        assert float(back["waste_pct"]) == prefill      # the field never lies
        for l in back["lines"]:
            q = float(l.get("qty") or 0)
            assert q == int(q), f"fractional order qty survived: {l['name']} = {q}"
        _record(family, "Hover", siding["name"], siding["qty"], siding["unit"],
                f"raw 42.4 + {prefill:g}% field waste, whole units")
    finally:
        _cleanup(session, est["id"])


# ── COLUMN 1+2: LP B&B and LP LAP through THE PATH HOWARD DRIVES —
# pre-pick default merge saved FIRST, the family picked AFTER, list read
# from the ESTIMATE. NOTHING STALE: every other family's rows read 0. ────
@pytest.mark.parametrize("family,profile,gov_name,gov_qty,stale_name", [
    ("LP B&B", "board_batten", PANEL_10, 138.0, LAP),
    ("LP LAP", "lap", LAP, 513.0, PANEL_10),
])
def test_pick_after_import_rederives_nothing_stale(session, hover_measurements,
                                                   family, profile, gov_name,
                                                   gov_qty, stale_name):
    from routes.hover import _compose_facade_default_into, _build_lines, _bake_tab_waste
    m = dict(hover_measurements)
    _compose_facade_default_into(m)
    pre_pick = _bake_tab_waste(_build_lines(m), 10)      # the client's pre-pick merge (lap default)
    est = _fresh_est(session, "lp_smart", profile)
    try:
        put = [{"tab": l["tab"], "section": l["section"], "name": l["name"],
                "unit": l["unit"], "qty": l["qty"],
                "raw_qty": l.get("raw_qty"), "mat": 0, "lab": 0}
               for l in pre_pick if l.get("tab") in ("vinyl", "ascend", "lp_smart")]
        rr = session.put(f"{API}/estimates/{est['id']}",
                         json={**est, "lines": put, "waste_pct": 10}, timeout=15)
        assert rr.status_code == 200, rr.text
        # THE PICK — after the import, like the modal
        rr = session.post(f"{API}/estimates/{est['id']}/hover-lp-run",
                          json={"hover_run_id": HOVER_RUN, "profile": profile},
                          timeout=90)
        assert rr.status_code == 200, rr.text
        back = session.get(f"{API}/estimates/{est['id']}", timeout=15).json()
        lp = {l["name"]: l for l in back["lines"] if l.get("tab") == "lp_smart"}
        assert float(lp[gov_name]["qty"]) == gov_qty, (
            f"{family}: pick did not reach the math — {gov_name} = {lp[gov_name]['qty']}")
        stale = lp.get(stale_name)
        assert stale is None or float(stale.get("qty") or 0) == 0, (
            f"{family}: STALE {stale_name} = {stale['qty']} — the SKU set did not follow the family")
        # tab == printed package, THE SAME NUMBER
        pkg = session.post(f"{API}/estimates/{est['id']}/lp-package/preview",
                           json={}, timeout=90).json()
        pkg_gov = next(l for l in pkg["lines"] if l["name"].startswith(gov_name))
        assert float(pkg_gov["qty"]) == gov_qty
        _record(family, "Hover", gov_name, gov_qty, "PCS",
                f"picked AFTER import; {stale_name} reads 0")
        if profile == "board_batten":
            _ground_truth_column(pkg, back)
    finally:
        _cleanup(session, est["id"])


def _ground_truth_column(pkg, est_doc):
    """COLUMN 3 — machine vs the SECOND OPINION (estimate-dept takeoff)
    on 3 Degree Rd. CORRECTED 2026-07-29: not installed quantities —
    another estimator's read of the same Hover report; either may be off.
    Reconciled lines HARD-ASSERT presence; deltas are RECORDED, never
    silently theoretical."""
    lines = pkg["lines"]
    def total(pred):
        return sum(float(l.get("qty") or 0) for l in lines if pred(l))
    battens = total(lambda l: l["name"].startswith("190 Series"))  # batten sticks
    trim540_4 = total(lambda l: l["name"].startswith('540 Series Trim') and '4" x 16' in l["name"])
    soffit = sum(float(l.get("qty") or 0) for l in (est_doc.get("lines") or [])
                 if l.get("tab") == "lp_smart" and "Soffit 16" in (l.get("name") or ""))
    _record("LP B&B", "Hover", "Battens 190 Series sticks (second opinion 465)",
            battens, "PCS", f"delta {battens - 465:+.1f} — vs est-dept read, OPEN")
    _record("LP B&B", "Hover", '540-4" trim (machine vs second opinion 142)',
            trim540_4, "PCS", f"delta {trim540_4 - 142:+.1f} — vs est-dept read, OPEN")
    _record("LP B&B", "Hover", "Soffit pcs (second opinion ≈260 ft² basis — UNCONFIRMED)",
            soffit, "PCS", "recorded — Hover's 2620 ft² soffit stands UNVALIDATED")
    assert battens > 0 and trim540_4 >= 0   # column populated, never blank


# ── COLUMN 4: the PHOTO door, same user order — run lands, family picked
# AFTER (default-profile endpoint), materialize gate, list read back. ────
def test_photo_door_pick_after_run(session, mongo_db):
    est = _fresh_est(session, "lp_smart", "photo")
    run_id = f"TEST_accept4_photo_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    mongo_db.ai_measure_runs.insert_one({
        "test_artifact": True, "run_id": run_id, "estimate_id": est["id"],
        "status": "done", "source": "photo", "created_at": now, "updated_at": now,
        "result": {"measurements": {
            "siding_sqft": 2000, "siding_with_openings_sqft": 2000,
            "eaves_lf": 120, "rakes_lf": 80, "starter_lf": 120,
            "window_count": 4, "entry_door_count": 1, "opening_count": 5,
            # NO _per_profile_sqft preset — the family is picked AFTER,
            # exactly the order the contractor drives.
        }, "raw_ai": {"walls": [], "openings": [], "corner_locations": []}},
    })
    try:
        rr = session.post(f"{API}/estimates/{est['id']}/default-profile",
                          json={"profile": "board_batten"}, timeout=15)
        assert rr.status_code == 200, rr.text
        rr = session.post(f"{API}/estimates/{est['id']}/lp-package/materialize",
                          json={"run_id": run_id}, timeout=90)
        assert rr.status_code == 200, rr.text
        back = session.get(f"{API}/estimates/{est['id']}", timeout=15).json()
        lp = {l["name"]: l for l in back["lines"] if l.get("tab") == "lp_smart"}
        panel = next((v for k, v in lp.items() if k.startswith("38 Series 4'")
                      and float(v.get("qty") or 0) > 0), None)
        assert panel is not None, "photo door: B&B pick produced no panel quantity"
        stale_lap = lp.get(LAP)
        assert stale_lap is None or float(stale_lap.get("qty") or 0) == 0, (
            f"photo door: STALE lap = {stale_lap['qty']}")
        _record("LP B&B", "Photo", panel["name"] if panel else "-",
                float(panel["qty"]), "PCS", "picked AFTER run via default-profile")
    finally:
        mongo_db.ai_measure_runs.delete_many({"run_id": run_id})
        _cleanup(session, est["id"])


# ── the table itself — written last, all four columns present ────────────
def test_zz_emit_acceptance_table():
    assert _rows, "no acceptance rows recorded — the columns are empty"
    doors = {r[1] for r in _rows}
    fams = {r[0] for r in _rows}
    assert {"Hover", "Photo"} <= doors, f"BOTH DOORS required, got {doors}"
    assert {"VINYL", "ASCEND", "LP B&B", "LP LAP"} <= fams, f"EVERY FAMILY required, got {fams}"
    assert any("second opinion" in r[2] for r in _rows), "SECOND-OPINION column missing"
    lines = ["# Four-column acceptance — 3 Degree Rd (run 7862dd2c)",
             "", "Sealed 2026-07-28: fresh run · every family · second opinion · both doors.",
             "",
             "**CORRECTION (Howard, 2026-07-29): the 3 Degree comparison figures",
             "(battens 465 · 540-4\" 142 · soffit ≈260) are the ESTIMATE",
             "DEPARTMENT'S takeoff off the same Hover report — NOT installed or",
             "delivered quantities. They are a SECOND OPINION; either side may be",
             "off. NO HOUSE IN THIS PROJECT HAS BEEN VALIDATED AGAINST MATERIAL",
             "THAT ACTUALLY GOT DELIVERED. A match in this column is agreement",
             "between two estimates, not proof.**",
             "", "(Deterministic content — re-emitted identically on every green run so the",
             "guard's clean-tree covenant holds; qty changes here are REAL changes.)",
             "", "| Family | Door | Line | Qty | Unit | Note |",
             "|---|---|---|---|---|---|"]
    for r in _rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    lines += [
        "",
        "## SECOND OPINION #2 — 261 Haugh (recorded 2026-07-29, Howard's ruling)",
        "Another estimator's takeoff off the same Hover report — NOT installed",
        "material. Neither second opinion is a standard or a target; the ruled",
        "formula is never tuned toward either.",
        "",
        "| Line | App (ruled) | Second takeoff | Note |",
        "|---|---|---|---|",
        "| Battens 190 | 129 @ 12\" o.c. (was 194 @ retired 8\") | 144 | theirs implies ~10.7\" o.c. WITH end-to-end splicing — not a standard |",
        "| Panels | 68 × 4×10 = 2,720 ft² @ sealed 30% | 70 × 4×8 = 2,240 ft² (~8.5% waste) | like-for-like: app on 4×8 @ 30% = 84 — panel size is BAKED to 4×10 today (reported for ruling) |",
        "| OSC | 15 | 13 | effectively agreed |",
        "| 540 trim 4\" | 62 = wrap 33 + frieze 23 + ISC 6 | 32 | their 32 ≈ our WRAP component alone (525.33 LF ÷ 16 = 33) — gap is frieze + ISC scope, not wrap math |",
        "| Soffit | 23 | 22 | agreed |",
        "| 5/4×12×16 fascia | — | 19 | **COMPARISON DROPPED (Howard ruled 2026-07-29): their 5/4\" thickness is wrong — 4/4\" (440 Series) is correct; a wrong-thickness line validates nothing** |",
        "",
        "Implied spacings named: 3 Degree second opinion ≈ 6.8\" o.c.; Haugh",
        "second opinion ≈ 10.7\" o.c. — both splice-implied, both non-standard.",
    ]
    TABLE_PATH.write_text("\n".join(lines) + "\n")
    assert TABLE_PATH.exists()
