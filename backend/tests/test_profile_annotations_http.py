"""Iter 78z — HTTP/auth tests for the ProfileAnnotator endpoints and the
`_aggregate_to_hover_shape` worker integration."""
from __future__ import annotations
from creds_for_tests import TEST_PASSWORD

import os
import sys
from pathlib import Path

import pytest
import requests

# Allow importing backend modules for the direct unit test on
# `_aggregate_to_hover_shape`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Use the same external URL the frontend uses.
FRONTEND_ENV = Path(__file__).resolve().parent.parent.parent / "frontend" / ".env"
BASE_URL = None
if FRONTEND_ENV.exists():
    for line in FRONTEND_ENV.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASS = TEST_PASSWORD


# ---------------------------------------------------------------------------
# Auth + estimate fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def admin_session():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL not found")
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def estimate_id(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/estimates", timeout=15)
    assert r.status_code == 200, r.text
    items = r.json()
    if not items:
        # Seed one if none exist
        r2 = admin_session.post(
            f"{BASE_URL}/api/estimates",
            json={"customer": {"name": "TEST_Annotator"}, "items": []},
            timeout=15,
        )
        assert r2.status_code in (200, 201), r2.text
        return r2.json()["id"]
    return items[0]["id"]


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------
class TestProfileAnnotationEndpoints:
    """GET/PUT /api/estimates/{id}/profile-annotations CRUD."""

    def test_get_returns_empty_default(self, admin_session, estimate_id):
        # Reset first so prior runs don't leak
        admin_session.put(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            json={"annotations": {}},
            timeout=30,
        )
        r = admin_session.get(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "annotations" in body
        assert isinstance(body["annotations"], dict)
        assert body["annotations"] == {}

    def test_put_then_get_roundtrip(self, admin_session, estimate_id):
        payload = {
            "annotations": {
                "0": [
                    {
                        "id": "box-1",
                        "elevation_label": "front",
                        "profile": "shake",
                        "sqft": 60,
                        "x_norm": 0.1, "y_norm": 0.1,
                        "w_norm": 0.2, "h_norm": 0.2,
                    }
                ]
            }
        }
        r = admin_session.put(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            json=payload, timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        r2 = admin_session.get(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            timeout=30,
        )
        assert r2.status_code == 200, r2.text
        got = r2.json()["annotations"]
        assert "0" in got
        assert len(got["0"]) == 1
        box = got["0"][0]
        assert box["profile"] == "shake"
        assert box["sqft"] == 60
        assert box["elevation_label"] == "front"

        # Cleanup
        admin_session.put(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            json={"annotations": {}},
            timeout=30,
        )


class TestProfileAnnotationAuth:
    """Auth + validation."""

    def test_get_unauthenticated(self, estimate_id):
        r = requests.get(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            timeout=30,
        )
        assert r.status_code in (401, 403), r.text

    def test_put_unauthenticated(self, estimate_id):
        r = requests.put(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            json={"annotations": {}}, timeout=30,
        )
        assert r.status_code in (401, 403), r.text

    def test_get_wrong_est_id(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/estimates/does-not-exist-xyz/profile-annotations",
            timeout=30,
        )
        assert r.status_code == 404, r.text

    def test_put_wrong_est_id(self, admin_session):
        r = admin_session.put(
            f"{BASE_URL}/api/estimates/does-not-exist-xyz/profile-annotations",
            json={"annotations": {}}, timeout=30,
        )
        assert r.status_code == 404, r.text

    def test_put_missing_annotations_key(self, admin_session, estimate_id):
        r = admin_session.put(
            f"{BASE_URL}/api/estimates/{estimate_id}/profile-annotations",
            json={"oops": "no annotations key"}, timeout=30,
        )
        assert r.status_code == 400, r.text


# ---------------------------------------------------------------------------
# Worker-integration unit test — call _aggregate_to_hover_shape directly
# ---------------------------------------------------------------------------
class TestAggregateToHoverShapeAnnotations:
    """Confirm `_aggregate_to_hover_shape` accepts annotations and the
    overlay flows through to `_per_profile_sqft` and the elevation's
    accents list."""

    def test_annotation_injects_shake_accent_on_lap_house(self):
        from routes.ai_measure import _aggregate_to_hover_shape

        # Fake Claude raw output: pure-lap house, front + right elevations,
        # each with a single wall row.
        raw = {
            "walls": [
                {
                    "label": "front", "width_ft": 30, "height_ft": 9,
                    "wall_body_profile_callout": "lap",
                    "siding_pct_this_wall": 100,
                    "gable_triangle_height_ft": 0,
                    "dormer_face_sqft": 0, "openings": [],
                },
                {
                    "label": "right", "width_ft": 25, "height_ft": 9,
                    "wall_body_profile_callout": "lap",
                    "siding_pct_this_wall": 100,
                    "gable_triangle_height_ft": 0,
                    "dormer_face_sqft": 0, "openings": [],
                },
            ],
            "openings_schedule": [],
            "missing_elevations": [],
        }

        annotations = {
            "0": [
                {
                    "elevation_label": "front",
                    "profile": "shake",
                    "sqft": 60,
                }
            ]
        }

        measurements = _aggregate_to_hover_shape(raw, annotations=annotations)

        per_profile = measurements.get("_per_profile_sqft") or {}
        assert "shake" in per_profile, f"got per_profile={per_profile}"
        assert per_profile["shake"] == pytest.approx(60.0)
        # Lap should still exist (original walls untouched outside box)
        assert "lap" in per_profile and per_profile["lap"] > 0

        per_elev = measurements.get("_per_elevation_breakdown") or []
        front = next((e for e in per_elev if (e.get("label") or "").lower() == "front"), None)
        assert front is not None, f"no front elevation in {per_elev}"
        accents = front.get("accents") or []
        # The shake annotation should have been appended as an accent
        # row on the front elevation.
        assert any(
            (a.get("profile") or "").lower() == "shake"
            and abs(float(a.get("sqft") or 0) - 60.0) < 0.01
            for a in accents
        ), f"shake accent missing in {accents}"

    def test_no_annotations_passthrough(self):
        from routes.ai_measure import _aggregate_to_hover_shape

        raw = {
            "walls": [
                {
                    "label": "front", "width_ft": 30, "height_ft": 9,
                    "wall_body_profile_callout": "lap",
                    "siding_pct_this_wall": 100,
                    "gable_triangle_height_ft": 0,
                    "dormer_face_sqft": 0, "openings": [],
                },
            ],
            "openings_schedule": [],
        }
        m1 = _aggregate_to_hover_shape(raw, annotations=None)
        m2 = _aggregate_to_hover_shape(raw, annotations={})

        # Without annotations only lap should be present
        for m in (m1, m2):
            ppro = m.get("_per_profile_sqft") or {}
            assert set(ppro.keys()) <= {"lap"}, f"unexpected profiles in {ppro}"
