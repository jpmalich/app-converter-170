"""Blueprint shakedown P1 — composition cut + extraction conformance pins
(ruled 2026-07-14, trace: /app/memory/blueprint_composition_trace.md).

Pins:
  • THE CUT: blueprint-sourced LP derivation goes through assemble_lp_package
    (via _load_run picking up ai_blueprint_runs) — no cross-domain items,
    integer quantities (extends the iter97 mixed-fixture pins to
    blueprint-sourced estimates)
  • worker emits NO raw lp_smart lines (engine-owned tab)
  • blueprint-applied endpoint archives the run (24h TTL defusal)
  • aggregator: pitch-computed gable, starter = perimeter − 3'/entry,
    appendage faces in siding area, per-elevation opening placement
    (defaults flagged), door-class residual logged
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = "Admin123!"
# Howard's original shakedown upload (e4afda3a64a54439b02b5c609dda0b69)
# was lost to the 24h ai_blueprint_runs TTL before archival (2026-07-16).
# Repointed to comparison run1_opus — same blueprint, validated Opus 4.5,
# restored into fixture_runs (no TTL) from /app/memory/bp_comparison_runs.
SHAKEDOWN_RUN_ID = "2a2e8a1227d145a588b71387903e1320"

CROSS_DOMAIN = ("j-channel", "j channel", "finish trim", "coil")


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


# ── Aggregator conformance (extraction-fix analogues) ────────────────

def _agg(raw):
    from routes.ai_blueprint import _aggregate_to_hover_shape
    return _aggregate_to_hover_shape(raw)


def _base_raw(**over):
    raw = {
        "walls": [
            {"label": "front", "width_ft": 50, "height_ft": 9, "gable_triangle_height_ft": 0},
            {"label": "back", "width_ft": 50, "height_ft": 9, "gable_triangle_height_ft": 0},
            {"label": "left", "width_ft": 30, "height_ft": 9, "gable_triangle_height_ft": 8.5},
            {"label": "right", "width_ft": 30, "height_ft": 9, "gable_triangle_height_ft": 8.5},
        ],
        "windows": [], "doors": [],
        "eaves_lf": 100, "rakes_lf": 62, "starter_lf": 100,
        "avg_wall_height_ft": 9,
    }
    raw.update(over)
    return raw


def test_gable_pitch_computed_over_drawing_scaled():
    m = _agg(_base_raw(roof_pitch="7/12"))
    prov = m.get("_gable_pitch_provenance") or []
    assert len(prov) == 2
    assert prov[0]["computed_ft"] == 8.75    # (30/2) × 7/12 — the June finding
    assert prov[0]["scaled_ft"] == 8.5
    # gable area uses the computed rise: 2 × 0.5×30×8.75 = 262.5
    m_noptch = _agg(_base_raw())
    assert m["siding_sqft"] - m_noptch["siding_sqft"] == pytest.approx(7.5, abs=0.2)


def test_starter_reports_raw_perimeter_engine_owns_deduction():
    raw = _base_raw(doors=[{"width_in": 36, "height_in": 80, "qty": 1, "type_hint": "entry", "elevation": "front"}])
    m = _agg(raw)
    # aggregator reports RAW perimeter 160 — the ENGINE deducts entry
    # widths (pre-deducting here double-deducts downstream)
    assert m["starter_lf"] == 160.0
    assert "engine deducts" in m["_starter_basis"]


def test_appendage_faces_join_siding_area():
    raw = _base_raw(appendages=[{
        "wall": "back", "kind": "chimney_chase", "width_ft": 6, "depth_ft": 2,
        "height_ft": 24, "extends_above_roofline": True, "position_frac": 0.36,
        "faces_sqft": 145.5,
    }], avg_wall_height_ft=9.5)
    base = _agg(_base_raw())
    m = _agg(raw)
    assert m["siding_sqft"] - base["siding_sqft"] == pytest.approx(145.5, abs=0.1)
    assert m["_ai_appendage_faces"] == ["back chimney chase (146 ft²)"]
    # feature-pooled OSC basis: 2×24 + 2×(24−9.5) = 77 LF
    assert m["_ai_osc_features"] == [{"label": "back chimney chase", "lf": 77.0}]


def test_opening_placement_from_elevation_defaults_flagged():
    raw = _base_raw(windows=[
        {"width_in": 36, "height_in": 48, "qty": 2, "type_hint": "double_hung", "elevation": "back"},
        {"width_in": 36, "height_in": 48, "qty": 1, "type_hint": "slider", "elevation": "unknown"},
    ])
    m = _agg(raw)
    walls = [o["wall"] for o in raw["openings"]]
    assert walls == ["back", "back", "front"]
    assert raw["openings"][0]["placement_source"] == "elevation"
    assert raw["openings"][2]["placement_source"] == "default"
    assert m["_opening_placement_defaulted"] == 1


def test_door_class_residual_logged():
    raw = _base_raw(doors=[
        {"width_in": 36, "height_in": 80, "qty": 1, "type_hint": "entry", "elevation": "front"},
        {"width_in": 36, "height_in": 80, "qty": 1, "type_hint": "entry", "elevation": "back"},
    ])
    m = _agg(raw)
    assert m.get("_door_class_residual") is True
    assert "class residual" in m.get("_ai_notes", "")


# ── THE CUT (composition) ─────────────────────────────────────────────

def test_worker_strips_lp_smart_lines_source_pin():
    src = (Path(__file__).resolve().parent.parent / "routes" / "ai_blueprint.py").read_text()
    assert '!= "lp_smart"' in src, "worker must strip engine-owned lp_smart rows"


def test_blueprint_run_derives_through_engine(admin_session, mongo_db):
    """Extends the iter97 mixed-fixture pins to blueprint-sourced estimates:
    fake blueprint run (cloned from Howard's shakedown) on a fresh LP
    estimate → /lp-package/preview must serve THROUGH the engine —
    no cross-domain items, integer quantities, no rake-driven soffit."""
    s = admin_session
    src = mongo_db.ai_blueprint_runs.find_one({"run_id": SHAKEDOWN_RUN_ID}, {"_id": 0}) \
        or mongo_db.fixture_runs.find_one({"run_id": SHAKEDOWN_RUN_ID}, {"_id": 0})
    assert src, "shakedown blueprint run missing"
    est_id = s.post(f"{API}/estimates", json={"customer_name": "BP Cut", "kind": "lp_smart"}, timeout=15).json()["id"]
    run_id = "test-bpcut-" + uuid.uuid4().hex[:10]
    mongo_db.ai_blueprint_runs.insert_one({**src, "run_id": run_id, "estimate_id": est_id})
    try:
        r = s.post(f"{API}/estimates/{est_id}/lp-package/preview", json={}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        pkg = r.json()
        assert pkg.get("run_id") == run_id, "engine did not pick up the blueprint run"
        names = [str(l.get("name", "")).lower() for l in pkg.get("lines", [])]
        for bad in CROSS_DOMAIN:
            assert not any(bad in n for n in names), f"cross-domain item on LP package: {bad}"
        for l in pkg.get("lines", []):
            q = l.get("qty")
            if isinstance(q, (int, float)):
                assert float(q) == int(q), f"fractional qty {q} on {l.get('name')}"
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
        mongo_db.estimates.delete_one({"id": est_id})
        mongo_db.estimates_trash.delete_one({"id": est_id})
        mongo_db.ai_blueprint_runs.delete_one({"run_id": run_id})
        mongo_db.fixture_runs.delete_one({"run_id": run_id})


def test_blueprint_applied_archives_run(admin_session, mongo_db):
    s = admin_session
    src = mongo_db.ai_blueprint_runs.find_one({"run_id": SHAKEDOWN_RUN_ID}, {"_id": 0}) \
        or mongo_db.fixture_runs.find_one({"run_id": SHAKEDOWN_RUN_ID}, {"_id": 0})
    assert src
    est_id = s.post(f"{API}/estimates", json={"customer_name": "BP Applied", "kind": "lp_smart"}, timeout=15).json()["id"]
    run_id = "test-bpapp-" + uuid.uuid4().hex[:10]
    mongo_db.ai_blueprint_runs.insert_one({**src, "run_id": run_id, "estimate_id": est_id})
    try:
        r = s.post(f"{API}/estimates/{est_id}/lp-package/blueprint-applied", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["archived_run_id"] == run_id
        arch = mongo_db.fixture_runs.find_one({"run_id": run_id})
        assert arch and "blueprint-apply" in (arch.get("artifact_reasons") or [])
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
        mongo_db.estimates.delete_one({"id": est_id})
        mongo_db.estimates_trash.delete_one({"id": est_id})
        mongo_db.ai_blueprint_runs.delete_one({"run_id": run_id})
        mongo_db.fixture_runs.delete_one({"run_id": run_id})


def test_source_governance_photo_outranks_unapplied_blueprint(admin_session, mongo_db):
    """Demo hazard pin: a merely-PREVIEWED blueprint run must never switch
    the composition source. Photo-latest governs until blueprint-APPLY
    stamps lp_source_run_id."""
    s = admin_session
    photo_src = mongo_db.fixture_runs.find_one({"run_id": "4a009e93eb5348c08cc26bfb935675ce"}, {"_id": 0})
    bp_src = mongo_db.ai_blueprint_runs.find_one({"run_id": SHAKEDOWN_RUN_ID}, {"_id": 0}) \
        or mongo_db.fixture_runs.find_one({"run_id": SHAKEDOWN_RUN_ID}, {"_id": 0})
    assert photo_src and bp_src
    photo_src.pop("artifact_reasons", None)
    est_id = s.post(f"{API}/estimates", json={"customer_name": "BP Gov", "kind": "lp_smart"}, timeout=15).json()["id"]
    p_id = "test-bpgov-p-" + uuid.uuid4().hex[:8]
    b_id = "test-bpgov-b-" + uuid.uuid4().hex[:8]
    mongo_db.ai_measure_runs.insert_one({**photo_src, "run_id": p_id, "estimate_id": est_id})
    mongo_db.ai_blueprint_runs.insert_one({**bp_src, "run_id": b_id, "estimate_id": est_id})
    try:
        r = s.post(f"{API}/estimates/{est_id}/lp-package/preview", json={}, timeout=30)
        assert r.status_code == 200 and r.json()["run_id"] == p_id, \
            f"unapplied blueprint run shadowed the photo run: {r.json().get('run_id')}"
        ra = s.post(f"{API}/estimates/{est_id}/lp-package/blueprint-applied", json={"run_id": b_id}, timeout=15)
        assert ra.status_code == 200 and ra.json()["archived_run_id"] == b_id
        r2 = s.post(f"{API}/estimates/{est_id}/lp-package/preview", json={}, timeout=30)
        assert r2.status_code == 200 and r2.json()["run_id"] == b_id, "applied stamp did not govern"
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
        mongo_db.estimates.delete_one({"id": est_id})
        mongo_db.estimates_trash.delete_one({"id": est_id})
        mongo_db.ai_measure_runs.delete_one({"run_id": p_id})
        mongo_db.ai_blueprint_runs.delete_one({"run_id": b_id})
        mongo_db.fixture_runs.delete_many({"run_id": {"$in": [p_id, b_id]}})


# ── 3D-layer fixes (addendum 6/7/8) — source pins ─────────────────────

FE = Path("/app/frontend/src/components/estimate/HouseModel3D.jsx")


def test_pitch_ladder_is_integer_c2_parity():
    src = FE.read_text()
    assert "ROOF_PITCHES = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]" in src
    assert 'pitchSource = ' in src and '"printed"' in src


def test_derived_pitch_never_wears_print_badge():
    src = FE.read_text()
    # derived-on-blueprint badge must be the amber verify treatment
    assert "Derived — verify" in src
    # blueprint appendages come from the structured payload, photo shape never
    assert "deriveBlueprintAppendages" in src
    assert "openingPlacementDefaulted" in src


# ── Confirm-openings ratification for blueprint (ruling 2026-07-15) ──
# Window-regression disposition: mechanism was a schedule-qty
# cross-attribution misread (B×4 + phantom B×1) = stochasticity → the
# human-ratify layer serves both front doors. Blueprint runs emit
# _ai_openings_schedule with sheet refs in place of photo crops.

def test_openings_schedule_emitted_with_sheet_refs():
    raw = _base_raw(
        windows=[
            {"id": "B", "width_in": 36, "height_in": 60, "qty": 4, "type_hint": "double_hung", "elevation": "front"},
            {"id": "A", "width_in": 48, "height_in": 48, "qty": 1, "type_hint": "casement", "elevation": "left"},
        ],
        doors=[{"id": "E1", "width_in": 36, "height_in": 80, "qty": 1, "type_hint": "entry", "elevation": "front"}],
        sheets_identified=[
            {"page": 5, "sheet_title": "FOUNDATION PLAN", "useful_for": "floor_plan"},
            {"page": 7, "sheet_title": "FIRST FLOOR PLAN", "useful_for": "schedule"},
        ],
    )
    m = _agg(raw)
    sched = m["_ai_openings_schedule"]
    assert len(sched) == 3
    win_rows = [r for r in sched if r["type"] == "window"]
    assert sum(r["count"] for r in win_rows) == 5
    # schedule sheet page 7 → 0-based idx 6 on every row
    assert all(r["locations"] and r["locations"][0]["photo_idx"] == 6 for r in sched)
    door = next(r for r in sched if r["type"] == "entry_door")
    assert door["mark"] == "E1" and "E1" in door["size_label"]


def test_openings_schedule_falls_back_to_floor_plan_sheet():
    raw = _base_raw(
        windows=[{"id": "B", "width_in": 36, "height_in": 60, "qty": 2, "type_hint": "double_hung", "elevation": "back"}],
        sheets_identified=[{"page": 3, "sheet_title": "FLOOR PLAN", "useful_for": "floor_plan"}],
    )
    sched = _agg(raw)["_ai_openings_schedule"]
    assert sched[0]["locations"][0]["photo_idx"] == 2


def test_openings_items_resolve_blueprint_page_paths():
    from routes.lp_package_routes import _openings_items
    run = {
        "run_id": "bp-test-ruling-1234",
        "page_paths": "bp_a.jpg,bp_b.jpg",
        "result": {"measurements": {"_ai_openings_schedule": [
            {"elevation": "front", "type": "window", "style": "", "width_in": 36,
             "height_in": 60, "count": 4, "size_label": "B · 36×60 in",
             "locations": [{"photo_idx": 1, "bbox": None}]},
        ]}},
    }
    items = _openings_items(run, None)
    assert len(items) == 1
    assert items[0]["photo_url"] == "/api/uploads/bp_b.jpg"
    assert items[0]["status"] == "unconfirmed"
