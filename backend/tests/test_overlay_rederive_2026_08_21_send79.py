"""SEND-79 Item 1 pins — THE OVERLAY LAW SURVIVES EVERY REBUILD BY
CONSTRUCTION (authorized).

The defect (SEND-76 RCA): the rederive rebuild merge carried a human
qty verbatim onto FRESH line dicts and dropped every overlay marker —
"a human value with no record of what it replaced" (EST-713272's 18.0
vs ~32 laundering shape). The cure is NOT copying markers across the
merge — a copied marker is one refactor away from being dropped again.
Every rebuild door now RE-RUNS the overlay law (`reapply_overlay_law`)
over the fresh lines before writing them: a re-run law cannot lose
what it recomputes.

Pinned here:
  • THE INVARIANT, LIVE — after a rederive (and a second one), the
    overlay-bound line still knows what it superseded.
  • THE INVARIANT, STRUCTURAL — any function in routes/ that calls the
    shared rebuild and writes lines MUST re-run the law. A future path
    that reintroduces the shortcut fails this pin by existing.
"""
import ast
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creds_for_tests import TEST_PASSWORD  # noqa: E402

_ENV = dotenv_values("/app/backend/.env")
_FE = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")

MEAS = {"siding_sqft": 2000, "eaves_lf": 120, "rakes_lf": 80,
        "soffit_sqft": 200, "outside_corner_count": 4,
        "inside_corner_count": 2, "window_count": 4, "door_count": 1,
        "overhang_in": 12}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    r = sess.post(f"{API}/auth/login",
                  json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return sess


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(_ENV["MONGO_URL"])
    return c[_ENV["DB_NAME"]]


@pytest.fixture()
def rig(s, mongo):
    r = s.post(f"{API}/estimates",
               json={"customer_name": f"SEND79-{uuid.uuid4().hex[:6]}",
                     "kind": "siding"})
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    est = s.get(f"{API}/estimates/{eid}").json()
    r = s.put(f"{API}/estimates/{eid}",
              json={**est, "hover_measurements": dict(MEAS),
                    "waste_pct": 0})
    assert r.status_code == 200, r.text
    yield eid
    mongo.pdf_overlay_polygons.delete_many({"estimate_id": eid})
    s.delete(f"{API}/estimates/{eid}")
    mongo.estimates.delete_many({"id": eid})


def _vinyl(lines):
    return next(l for l in lines
                if (l.get("tab") or "vinyl") == "vinyl"
                and l.get("section") == "Vinyl Siding"
                and l.get("unit") == "SQ")


def test_live_the_superseded_record_survives_every_rederive(s, mongo, rig):
    """The invariant, on the real door: after ANY rederive, an
    overlay-bound line still knows what it superseded — because the
    rederive RE-RUNS the law, it cannot lose the record."""
    eid = rig
    r = s.post(f"{API}/estimates/{eid}/rederive",
               json={"trigger": "send79-pin"})
    assert r.status_code == 200, r.text
    derived = _vinyl(r.json()["lines"])
    assert derived.get("qty_src") != "human"
    baseline = derived["qty"]

    mongo.pdf_overlay_polygons.insert_one({
        "id": f"send79-{uuid.uuid4().hex[:8]}", "estimate_id": eid,
        "page": 1, "face_id": "front", "material_class": "siding",
        "provenance": "human",
        "vertices_pct": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]],
        "sqft": 900.0, "derived_baseline_qty": baseline})

    for nth in (1, 2):   # and it holds through a SECOND rebuild
        r = s.post(f"{API}/estimates/{eid}/rederive",
                   json={"trigger": f"send79-pin-{nth}"})
        assert r.status_code == 200, r.text
        line = _vinyl(r.json()["lines"])
        assert line["qty"] == 9.0, f"rederive #{nth}: zone math lost"
        assert line["qty_src"] == "human"
        assert line["overlay_superseded"] is True, \
            f"rederive #{nth} stripped the overlay markers"
        assert line["superseded_qty"] == baseline, \
            f"rederive #{nth} lost what the human value superseded"
        assert "PDF-OVERLAY" in (line.get("note") or "")

    stored = mongo.estimates.find_one({"id": eid}, {"lines": 1})
    sline = _vinyl(stored["lines"])
    assert sline["overlay_superseded"] is True
    assert sline["superseded_qty"] == baseline


def test_live_a_rederive_with_no_zones_stays_derived(s, rig):
    """No zones → the law is a no-op: the rebuild's own derived lines
    land untouched (nothing invents an overlay record)."""
    r = s.post(f"{API}/estimates/{rig}/rederive",
               json={"trigger": "send79-pin-clean"})
    assert r.status_code == 200, r.text
    line = _vinyl(r.json()["lines"])
    assert line.get("qty_src") != "human"
    assert line.get("overlay_superseded") is None
    assert line.get("superseded_qty") is None


def test_structural_every_rebuild_write_door_reruns_the_law():
    """THE PIN ON THE CLASS, NOT THE MERGE: any function anywhere in
    routes/ that calls the shared rebuild (rebuild_lp_tab_lines) must
    re-run the overlay law before its write. A future door that
    reintroduces the carry-markers shortcut fails here by existing."""
    routes_dir = Path("/app/backend/routes")
    offenders = []
    for py in routes_dir.glob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef,
                                     ast.AsyncFunctionDef)):
                continue
            if node.name in ("rebuild_lp_tab_lines",
                             "reapply_overlay_law"):
                continue
            src = ast.get_source_segment(py.read_text(), node) or ""
            if "rebuild_lp_tab_lines(" not in src:
                continue
            if "reapply_overlay_law" not in src:
                offenders.append(f"{py.name}::{node.name}")
    assert not offenders, (
        "rebuild door(s) write lines without re-running the overlay "
        f"law: {offenders}")


def test_structural_the_law_reruns_not_marker_copying():
    """The cure is BY CONSTRUCTION: reapply_overlay_law delegates to
    apply_overlay_to_takeoff (the one law), and no rebuild merge copies
    overlay markers across by hand."""
    src = Path("/app/backend/routes/pdf_overlay.py").read_text()
    fn = src[src.index("async def reapply_overlay_law"):]
    fn = fn[:fn.index("\nasync def ")]
    assert "apply_overlay_to_takeoff(" in fn
    hover = Path("/app/backend/routes/hover.py").read_text()
    merge = hover[hover.index('if (old.get("qty_src") or "") == "human"'):]
    merge = merge[:400]
    for marker in ("overlay_superseded", "superseded_qty",
                   "overlay_sqft"):
        assert marker not in merge, (
            "the merge copies overlay markers by hand — the ruled cure "
            "is re-running the law, not copying")
