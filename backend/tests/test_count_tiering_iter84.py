"""Iter 79j.84 — Candidate 1c pin tests (pre-registered, Howard-approved).
Deterministic two-tier course counts: same-corner cross-check gates the
enumerated tier; pixel-citation-as-support demotes; consensus never
averages and never takes the higher count; estimated tier excluded from
Δc. Unit tests hit _apply_count_tiering directly; one API test pins the
Δc exclusion end-to-end."""
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import _apply_count_tiering, _PIXEL_SUPPORT_RE  # noqa: E402

BASE_URL = "https://app-converter-170.preview.emergentagent.com"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = "Admin123!"


def _ex(idx, count, corner, reasoning="counted from starter at block line to frieze"):
    return {
        "index": idx,
        "eave_courses_counted": count,
        "count_anchor_corner": corner,
        "eave_reasoning": reasoning,
    }


def _final(walls=("front", "back", "left", "right")):
    return {"walls": [{"label": w, "height_ft": 9.0} for w in walls]}


def _wall(final, label):
    return next(w for w in final["walls"] if w["label"] == label)


# ---------- corner consensus ----------

def test_exact_match_corner_enumerated():
    f = _final()
    _apply_count_tiering(f, [_ex(0, 25, "front_left"), _ex(1, 25, "front_left")])
    c = f["_count_corner_audit"]["corners"]["front_left"]
    assert c["tier"] == "enumerated" and c["value"] == 25
    assert not c.get("possible_partial_top")


def test_differ_by_one_takes_lower_with_partial_top_flag():
    f = _final()
    _apply_count_tiering(f, [_ex(0, 26, "front_left"), _ex(1, 25, "front_left")])
    c = f["_count_corner_audit"]["corners"]["front_left"]
    assert c["tier"] == "enumerated"
    assert c["value"] == 25  # LOWER — never higher, never average
    assert c["possible_partial_top"] is True
    w = _wall(f, "front")
    assert w["eave_courses_counted"] == 25 and w["possible_partial_top"] is True


def test_conflict_over_one_demotes_both_never_picks_one():
    f = _final()
    _apply_count_tiering(f, [_ex(0, 27, "front_left"), _ex(1, 24, "front_left")])
    c = f["_count_corner_audit"]["corners"]["front_left"]
    assert c["tier"] == "estimated"
    assert c["corner_count_conflict"] is True
    assert c["value"] == 24  # lower kept as the takeoff-usable estimate
    w = _wall(f, "front")
    assert w["count_tier"] == "estimated" and w["corner_count_conflict"] is True


def test_single_photo_corner_never_enumerated():
    f = _final()
    _apply_count_tiering(f, [_ex(0, 25, "front_left")])
    c = f["_count_corner_audit"]["corners"]["front_left"]
    assert c["tier"] == "estimated" and c["reason"] == "single_photo"
    assert _wall(f, "front")["count_tier"] == "estimated"


# ---------- pixel-citation gate ----------

def test_pixel_citation_as_support_demotes():
    f = _final()
    _apply_count_tiering(f, [
        _ex(0, 27, "front_left", "27 courses; pixel cross-check agrees (114.75in vs 117in)"),
        _ex(1, 25, "front_left"),
    ])
    c = f["_count_corner_audit"]["corners"]["front_left"]
    # p0 demoted → only 1 clean photo → corner cannot be enumerated
    assert c["tier"] == "estimated" and c["reason"] == "pixel_citation_demotion"
    assert c["photos"][0]["pixel_cited"] is True


def test_flagged_pixel_dispute_does_not_demote():
    assert not _PIXEL_SUPPORT_RE.search(
        "counted 25; a pixel read disagrees (23) — count kept, count_disputed_by_pixel set"
    )
    f = _final()
    _apply_count_tiering(f, [
        _ex(0, 25, "front_left", "25 courses; pixel read disagrees, count kept per rule 5"),
        _ex(1, 25, "front_left"),
    ])
    assert f["_count_corner_audit"]["corners"]["front_left"]["tier"] == "enumerated"


def test_pixel_support_regex_catches_1b_phrasings():
    assert _PIXEL_SUPPORT_RE.search("pixel cross-check agrees")
    assert _PIXEL_SUPPORT_RE.search("consistent with the pixel-scale read")
    assert _PIXEL_SUPPORT_RE.search("pixel measurement confirms the count")
    assert not _PIXEL_SUPPORT_RE.search("pixel cross-check disagrees; count kept")


# ---------- wall stamping ----------

def test_wall_from_two_agreeing_enumerated_corners():
    f = _final()
    _apply_count_tiering(f, [
        _ex(0, 25, "front_left"), _ex(1, 25, "front_left"),
        _ex(2, 25, "front_right"), _ex(3, 25, "front_right"),
    ])
    w = _wall(f, "front")
    assert w["eave_courses_counted"] == 25 and w["count_tier"] == "enumerated"


def test_stepped_side_wall_two_corners_differ_no_single_count():
    # Letrick left wall: front_left corner 25c, rear_left corner 28c —
    # a legit stepped wall, NOT a conflict. No single wall count.
    f = _final()
    _apply_count_tiering(f, [
        _ex(0, 25, "front_left"), _ex(1, 25, "front_left"),
        _ex(2, 28, "rear_left"), _ex(3, 28, "rear_left"),
    ])
    w = _wall(f, "left")
    assert w["count_tier"] == "enumerated"
    assert w["eave_courses_counted"] is None
    assert w["count_segments"] == [25, 28]
    assert not w.get("corner_count_conflict")


def test_uncornered_count_stays_estimated():
    f = _final()
    f["walls"][0]["_source_photo_indices"] = [0]
    _apply_count_tiering(f, [_ex(0, 27, None)])
    w = _wall(f, "front")
    assert w["count_tier"] == "estimated" and w["eave_courses_counted"] == 27
    assert f["_count_corner_audit"]["uncornered"][0]["count"] == 27


def test_correlated_error_residual_logged_openly():
    f = _final()
    _apply_count_tiering(f, [_ex(0, 25, "front_left"), _ex(1, 25, "front_left")])
    assert "Correlated-error residual" in f["_count_corner_audit"]["residual_note"]


def test_no_counts_no_stamp():
    f = _final()
    _apply_count_tiering(f, [{"index": 0, "eave_courses_counted": None}])
    assert "_count_corner_audit" not in f


# ---------- Δc exclusion end-to-end ----------

@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    s._user_id = s.get(f"{API}/auth/me", timeout=10).json()["id"]
    yield s


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


def test_estimated_tier_excluded_from_course_delta(admin_session, mongo_db):
    s = admin_session
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Tier Exclusion"}, timeout=15).json()["id"]
    run_id = uuid.uuid4().hex
    mongo_db.ai_measure_runs.insert_one({
        "run_id": run_id, "user_id": s._user_id, "estimate_id": est_id,
        "status": "done", "photo_paths": "", "model_choice": "claude-fable-5",
        "result": {"measurements": {}, "raw_ai": {"walls": [
            {"label": "front", "height_ft": 9.6, "height_ft_source": "direct_consensus",
             "eave_courses_counted": 27, "count_tier": "estimated", "corner_count_conflict": True},
            {"label": "back", "height_ft": 9.9, "height_ft_source": "direct_consensus",
             "eave_courses_counted": 28, "count_tier": "enumerated", "possible_partial_top": True},
        ], "photos": []}},
    })
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check", json={"walls": {
            "front": {"segments": [{"height_ft": 8.96, "courses": 25}], "start_ref": "siding_start"},
            "back": {"segments": [{"height_ft": 9.92, "courses": 28}], "start_ref": "siding_start"},
        }, "dormers": []}, timeout=15)
        r = s.post(f"{API}/estimates/{est_id}/tape-check/score", json={"run_id": run_id}, timeout=15)
        assert r.status_code == 200, r.text
        w = r.json()["entry"]["walls"]
        # estimated tier: count surfaced but NO Δc (excluded from claims)
        assert w["front"]["ai_courses"] == 27
        assert w["front"]["count_tier"] == "estimated"
        assert w["front"]["corner_count_conflict"] is True
        assert "course_delta" not in w["front"]
        # enumerated tier: Δc scored, partial-top flag carried
        assert w["back"]["course_delta"] == 0
        assert w["back"]["count_tier"] == "enumerated"
        assert w["back"]["possible_partial_top"] is True
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_accuracy_pdf_carries_corner_cross_check_table(admin_session, mongo_db):
    """1c ruling item 3 — the accuracy report PDF renders the persisted
    _count_corner_audit as a same-corner cross-check methodology table.
    Self-provisioned (Iter 112): clones the frozen Letrick run (which
    carries a 1c audit) onto a scratch estimate — the original EST-191890
    fixture was deleted from the dashboard, and pins must not depend on
    deletable production data."""
    s = admin_session
    src = mongo_db.ai_measure_runs.find_one(
        {"run_id": "4a009e93eb5348c08cc26bfb935675ce"}, {"_id": 0})
    assert src, "frozen Letrick source run missing"
    est_id = s.post(f"{API}/estimates", json={"customer_name": "1c PDF Pin"},
                    timeout=15).json()["id"]
    run_id = "test-1cpdf-" + uuid.uuid4().hex[:10]
    me = s.get(f"{API}/auth/me", timeout=10).json()
    clone = dict(src)
    clone.update({"run_id": run_id, "estimate_id": est_id, "user_id": me["id"]})
    mongo_db.ai_measure_runs.insert_one(clone)
    try:
        s.put(f"{API}/estimates/{est_id}/tape-check", json={"walls": {
            "front": {"segments": [{"height_ft": 8.96, "courses": 25}], "start_ref": "siding_start"},
            "back": {"segments": [{"height_ft": 9.92, "courses": 28}], "start_ref": "siding_start"},
        }, "dormers": []}, timeout=15)
        sc = s.post(f"{API}/estimates/{est_id}/tape-check/score",
                    json={"run_id": run_id}, timeout=15)
        assert sc.status_code == 200, sc.text
        r = s.get(f"{API}/estimates/{est_id}/tape-check/report-pdf", timeout=60)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        import io
        from pypdf import PdfReader
        text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
        low = text.lower()
        assert "same-corner count cross-check" in low
        assert "correlated-error residual" in low
        assert "enumerated" in low and "estimated" in low
        # Iter 79j.88 — anchor-integrity standing rule always present; the
        # current-validated-baseline line appears only once a valid run has
        # been scored under the CURRENT contract hash (hash bumps empty it).
        assert "anchor-integrity dependency" in low
        from routes.ai_measure import _prompt_version_hash
        h = _prompt_version_hash()
        est = mongo_db.estimates.find_one({"id": est_id}, {"tape_check.history": 1})
        hist = (est.get("tape_check") or {}).get("history") or []
        if any(e.get("prompt_hash") == h for e in hist):
            assert "current validated baseline" in low
        else:
            assert "current validated baseline" not in low
    finally:
        mongo_db.ai_measure_runs.delete_one({"run_id": run_id})
        mongo_db.accuracy_report_snapshots.delete_many({"estimate_id": est_id})
        s.delete(f"{API}/estimates/{est_id}", timeout=15)
