"""SEND-115 LIVE BUG PIN (dart 8-23-2026 7am) — a REFUSED height must
RENDER as refusal, never crash the sheet.

The dart read (different drafter — third-plan-set candidate) refused
every wall height (evidence-or-null working on a foreign plan set). The
elevation-sheet renderer then crashed: `fmt_ftin(None)` TypeError → 500
on all four faces → the panel's catch showed "no completed AI
measurement run yet" — a refusal surface masking a crash. Fixed at the
call site: height_label mirrors width_label's None guard ("—")."""
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402
from api_base import API  # noqa: E402

DART_EST = "7caeff94-7167-4ca6-8a03-4808e9dd57a9"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL or "hhunt6677@yahoo.com",
                     "password": TEST_PASSWORD},
               timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.mark.parametrize("which", ["front", "left", "back", "right"])
def test_refused_height_renders_dash_never_500(session, which):
    r = session.get(f"{API}/estimates/{DART_EST}/elevation-sheet/{which}",
                    timeout=30)
    if r.status_code == 404:
        pytest.skip("env:fixture_estimate: dart estimate absent")
    assert r.status_code == 200, f"{which}: {r.status_code} {r.text[:200]}"
    wall = r.json().get("wall") or {}
    if wall.get("height_ft") is None:
        assert wall.get("height_label") == "—", \
            "a refused height prints refusal, never a fabricated figure"


def test_height_label_none_guard_is_structural():
    """The call site guards None exactly like width_label — the crash
    class cannot silently return."""
    src = (Path(__file__).resolve().parent.parent
           / "routes/elevation_sheets.py").read_text(encoding="utf-8")
    assert ('"height_label": (fmt_ftin(height_ft)\n'
            '                             if height_ft is not None else "—")'
            in src)
