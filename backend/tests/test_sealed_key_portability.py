"""SEALED-KEY PORTABILITY pins (ruled 2026-07-26).

The two sealed-key runtime gates match the portable `sealed_key` doc
flag ("letrick_v3"), never an estimate number. Sweep: no runtime route
code compares against any EST-* estimate number. Sealed VALUES stay in
letrick_hand_takeoff_key.py (code), never in the estimate doc.
"""
import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
LP_PKG = (BACKEND / "routes" / "lp_package_routes.py").read_text()
SHEETS = (BACKEND / "routes" / "elevation_sheets.py").read_text()


def test_gates_use_sealed_key_flag():
    assert 'est.get("sealed_key") != "letrick_v3"' in LP_PKG
    assert 'est.get("sealed_key") != "letrick_v3"' in SHEETS
    assert 'est.get("estimate_number") != "EST-373526"' not in LP_PKG
    assert 'est.get("estimate_number") != "EST-373526"' not in SHEETS


def test_gate_projections_carry_sealed_key():
    # _load_run (lp_package) + the sheet endpoint must project the flag
    # or the gate silently never opens
    assert '"sealed_key": 1' in LP_PKG
    assert '"sealed_key": 1' in SHEETS


def test_no_runtime_estimate_number_matching():
    pat = re.compile(r'estimate_number"[\]\)]?\s*(?:==|!=)\s*"(?:DEMO-|EST-)')
    for f in (BACKEND / "routes").glob("*.py"):
        hits = [ln for ln in f.read_text().splitlines() if pat.search(ln)]
        assert not hits, f"runtime estimate-number match in {f.name}: {hits}"


def test_letrick_fixture_carries_sealed_key():
    docs = json.loads((BACKEND / "fixtures" / "docs" / "estimates.json").read_text())
    letrick = next(e for e in docs if e.get("estimate_number") == "EST-373526")
    assert letrick.get("sealed_key") == "letrick_v3"


def test_sealed_values_stay_in_code_not_doc():
    docs = json.loads((BACKEND / "fixtures" / "docs" / "estimates.json").read_text())
    letrick = next(e for e in docs if e.get("estimate_number") == "EST-373526")
    for k in ("raw_sqft", "exposure_in", "chase_outer_sqft", "eaves_lf"):
        assert k not in letrick, f"sealed value {k} must live in letrick_hand_takeoff_key.py only"
