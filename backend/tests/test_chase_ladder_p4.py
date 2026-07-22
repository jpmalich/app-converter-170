"""P4 GENERIC CHIMNEY pins (ruled + ratified 2026-07-21).

Ratified contractor-spec constants:
  • ASSUMED standard chase depth = 30" (bottom rung, TAPED > ESTIMATED > ASSUMED)
  • ASSUMED height fallback (no run height read) = grade → drawn ridge + 2'-0"
    (ridge-relative, never a fixed-feet guess)
Both tagged ASSUMED, upgradeable by tape (appendage dims user_measured) or a
photo-derived read.

Also pinned: chase DETECTION from run corner reads (defect retired: doug
jones's chase had confirmed corner reads but no accent → nothing drew), and
the AMENDED collision guard (flag-always, suppress-never) live on doug's
back sheet where the chase genuinely overlaps W2.
"""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from routes.elevation_sheets import (  # noqa: E402
    CHASE_CODE_MIN_ABOVE_RIDGE_FT,
    STANDARD_CHASE_DEPTH_IN,
    _chase_dims_ladder,
)

API = "https://app-converter-170.preview.emergentagent.com/api"
DOUG_EST = "db82ec7a-3177-406d-a602-927255e9e10e"


def test_ratified_constants():
    """CONTRACTOR-SPEC (Howard, ratified 2026-07-21) — changing either
    value requires a new ratification, not a code edit."""
    assert STANDARD_CHASE_DEPTH_IN == 30.0
    assert CHASE_CODE_MIN_ABOVE_RIDGE_FT == 2.0


def test_ladder_assumed_rungs():
    rl = {"kind": "eave_ridge", "ridge_ft": 18.7}
    out = _chase_dims_ladder({}, [0.3, 0.42], 50.0, rl)
    assert out["width_in"] == 72.0
    assert out["width_tag"] == "ESTIMATED (photo-scaled)"
    assert out["depth_in"] == 30.0 and out["depth_tag"].startswith("ASSUMED (standard depth")
    assert out["height_in"] == round((18.7 + 2.0) * 12.0, 1)  # ridge-relative
    assert out["height_tag"].startswith("ASSUMED (ridge +")


def test_ladder_tape_upgrade_wins():
    """user_measured appendage dims outrank ASSUMED — the upgrade path."""
    est = {"lp_appendage_dims": {"appendage:back": {
        "depth_ft": {"value": 2.58, "status": "user_measured"},
        "height_ft": {"value": 19.55, "status": "user_measured"}}}}
    out = _chase_dims_ladder(est, [0.3, 0.42], 50.0, {"ridge_ft": 18.7})
    assert out["depth_in"] == round(2.58 * 12.0, 1)
    assert out["depth_tag"] == "TAPED (user-measured)"
    assert out["height_in"] == round(19.55 * 12.0, 1)
    assert out["height_tag"] == "TAPED (user-measured)"


def test_ladder_assumed_status_never_overrides():
    """'assumed' status entries set NO override — the ladder's own
    ASSUMED rungs govern (standing appendage-dims rule)."""
    est = {"lp_appendage_dims": {"appendage:back": {
        "depth_ft": {"value": 4.0, "status": "assumed"}}}}
    out = _chase_dims_ladder(est, None, None, None)
    assert out["depth_in"] == 30.0 and "width_in" not in out and "height_in" not in out


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com", "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


def _sheet(session, which):
    r = session.get(f"{API}/estimates/{DOUG_EST}/elevation-sheet/{which}", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_doug_back_chase_draws_at_ladder_dims(session):
    """ACCEPTANCE SHEET — PIN AMENDED BY RULING 2026-07-22 (confirmation-
    weighted geometry; doug is the FOUNDING EXAMPLE, see register).
    BEFORE: width 72\" ESTIMATED from the min/max of ALL reads (the 0.3
    left edge is UNCONFIRMED, 1 sighting) → artifact overlap with W2.
    AFTER: the CONFIRMED right edge (0.42 → 21'-0\") anchors; the chase
    extends left by the ratified ASSUMED standard width 48\" → 17'–21',
    CLEAR of W2 per human ground truth; the unconfirmed read renders as
    the flagged comparison band."""
    s = _sheet(session, "back")
    ch = s["chase"]
    assert ch is not None and ch["dims_tag"] == "LADDER"
    assert ch["center_ft"] == 19.0  # 21' confirmed edge − 48"/2
    assert ch["width_in"] == 48.0
    assert ch["width_tag"].startswith("ASSUMED (standard width")
    assert ch["depth_in"] == 30.0 and ch["depth_tag"].startswith("ASSUMED (standard depth")
    ridge = s["roofline"]["ridge_ft"]
    assert ch["height_in"] == round((ridge + 2.0) * 12.0, 1)
    assert ch["height_tag"].startswith("ASSUMED (ridge +")
    assert "anchored on CONFIRMED right-edge read" in ch["position"]
    assert "UNCONFIRMED" in ch["ai_band"]["note"]
    assert "comparison only" in ch["ai_band"]["note"]
    assert not ch.get("suppressed")


def test_doug_back_no_artifact_collision(session):
    """PIN AMENDED BY RULING 2026-07-22 — BEFORE: W2 × CHASE 22¾\" overlap
    flagged (an artifact of the unconfirmed-read span). AFTER: the
    confirmation-weighted chase (17'–21') sits CLEAR of W2 (13'-11"–16'-11")
    — no collision, matching human ground truth. Flag-always/suppress-never
    guard semantics remain pinned in the LBR unit tests."""
    s = _sheet(session, "back")
    assert [c for c in s["collisions"] if "CHASE" in c["elements"]] == []
    w2 = next(o for o in s["openings"] if o["tag"] == "W2")
    assert not w2.get("collision")
    assert not s["chase"].get("collision")


def test_doug_side_profiles_present_with_rung_tags(session):
    """Side profiles ALWAYS drawn where the chase projects (spec C) —
    at the best-known depth rung, tagged with that rung."""
    for which in ("left", "right"):
        s = _sheet(session, which)
        p = s["chase_profile"]
        assert p is not None, which
        assert p["depth_in"] == 30.0
        assert p["depth_tag"].startswith("ASSUMED (standard depth"), which
        assert p["height_tag"].startswith("ASSUMED (ridge +"), which
        assert p["dims_tag"] == "ASSUMED"
        assert "projects from the back wall" in p["anchor"], which


def test_doug_front_no_chase_no_profile(session):
    """No chase evidence on the front wall — nothing invents one."""
    s = _sheet(session, "front")
    assert s["chase"] is None and s["chase_profile"] is None
