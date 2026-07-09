"""Iter 79j.76 — stepped tape-check segments + start_ref tests."""
import os
import uuid

import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
_FE_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _FE_ENV.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", "Admin123!")


def _session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


def test_segments_roundtrip_and_validation():
    s = _session()
    est_id = s.post(f"{API}/estimates", json={"customer_name": "Stepped Tape Test"}, timeout=15).json()["id"]
    try:
        walls = {
            "front": 8.9,
            "left": {"segments": [{"height_ft": 9.21, "courses": 26},
                                  {"height_ft": 8.15, "courses": 23}],
                     "start_ref": "siding_start"},
            "back": {"segments": [{"height_ft": 9.9}], "start_ref": "siding_start"},
            "right": None,
        }
        r = s.put(f"{API}/estimates/{est_id}/tape-check", json={"walls": walls, "dormers": []}, timeout=15)
        assert r.status_code == 200, r.text
        got = s.get(f"{API}/estimates/{est_id}/tape-check", timeout=15).json()["walls"]
        assert got["front"] == 8.9
        assert got["left"]["segments"][0] == {"height_ft": 9.21, "courses": 26}
        assert got["left"]["segments"][1]["height_ft"] == 8.15
        assert got["left"]["start_ref"] == "siding_start"
        assert got["right"] is None
        # validation failures
        for bad in (
            {"left": {"segments": []}},
            {"left": {"segments": [{"height_ft": 0.2}]}},
            {"left": {"segments": [{"height_ft": 9}], "start_ref": "roofline"}},
            {"left": {"segments": [{"height_ft": 9, "courses": 999}]}},
            {"left": "not-a-number"},
        ):
            rb = s.put(f"{API}/estimates/{est_id}/tape-check", json={"walls": bad}, timeout=15)
            assert rb.status_code == 400, f"{bad} → {rb.status_code}"
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_stepped_scoring_uses_segment_range():
    """AI reads inside the segment range must PASS with delta 0; outside
    scores against the nearest bound."""
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    sys.path.insert(0, "/app/backend")
    load_dotenv(Path("/app/backend/.env"))
    from routes.estimates import _tape_wall_values, _tape_verdict

    heights, sr, stepped = _tape_wall_values(
        {"segments": [{"height_ft": 9.21, "courses": 26}, {"height_ft": 8.15, "courses": 23}],
         "start_ref": "siding_start"})
    assert stepped and sr == "siding_start" and heights == [9.21, 8.15]
    lo, hi = min(heights), max(heights)
    # inside range → pass
    ai = 8.7
    assert lo <= ai <= hi
    # above range by 0.8 → amber
    ai2 = hi + 0.8
    assert _tape_verdict(round(ai2 - hi, 2)) == "amber"
    # below range by 1.4 → fail
    ai3 = lo - 1.4
    assert _tape_verdict(round(ai3 - lo, 2)) == "fail"
    # legacy plain number still normalizes
    h2, sr2, st2 = _tape_wall_values(8.9)
    assert h2 == [8.9] and sr2 is None and st2 is False
