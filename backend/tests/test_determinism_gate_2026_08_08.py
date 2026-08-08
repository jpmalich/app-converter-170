"""DETERMINISM GATE (Howard ruled 2026-08-08 — built AFTER evidence-or-null,
by dependency, not preference: the gate compares two reads and
evidence-or-null changes what a read contains. Built against the
pre-null schema, the gate's first act is to certify a guess — two reads
both returning an invented 10.0' on an undimensioned wall would chip
"Two reads agreed": stable, confident, and invented.

THE GATE REPORTS STABILITY, NEVER CORRECTNESS. "Two reads agreed" and
"matches the printed dimension" must never print as the same chip.
With nulls in the schema the gate separates STABLY READ from STABLY
ABSTAINED — the only distinction it exists to draw.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _enforce_evidence_or_null, _with_readback, compute_read_stability,
)

SRC = (Path(__file__).resolve().parents[1] / "routes/ai_blueprint.py"
       ).read_text(encoding="utf-8")
DICT_TEXT = (Path(__file__).resolve().parents[2]
             / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")


def _boni(corners=8, eaves=167.0):
    return {"outside_corner_count": corners, "inside_corner_count": 4,
            "eaves_lf": eaves, "rakes_lf": 89.0, "starter_lf": 190.0,
            "outside_corner_lf": 150.0, "avg_wall_height_ft": 19.0,
            "windows": [{"qty": 2}, {"qty": 1}], "doors": [{"qty": 1}],
            "roof_planes": [{"gable_ends": 1}, {"gable_ends": 0}],
            "gutter_runs": [{"label": "front", "lf": 60}]}


def test_identical_reads_are_stable():
    s = compute_read_stability(_boni(), _boni())
    assert s["stable"] is True
    assert all(c["match"] for c in s["counts"])
    assert all(d["within"] for d in s["dims"])


def test_the_boni_corner_drift_flags_loudly():
    """The exact case that mandated the gate: corner count 10 on one
    read, 6 on the next, at temperature 0."""
    s = compute_read_stability(_boni(corners=10), _boni(corners=6))
    assert s["stable"] is False
    c = next(x for x in s["counts"] if x["name"] == "outside corners")
    assert (c["a"], c["b"], c["match"]) == (10, 6, False)


def test_dims_agree_within_tolerance_and_not_beyond():
    assert compute_read_stability(_boni(eaves=167.0),
                                  _boni(eaves=167.4))["stable"] is True
    s = compute_read_stability(_boni(eaves=167.0), _boni(eaves=175.0))
    assert s["stable"] is False
    d = next(x for x in s["dims"] if x["name"] == "eaves LF")
    assert d["within"] is False


def test_a_value_meeting_a_null_is_a_disagreement_never_agreement():
    a, b = _boni(), _boni()
    b["starter_lf"] = None
    s = compute_read_stability(a, b)
    assert s["stable"] is False
    d = next(x for x in s["dims"] if x["name"] == "starter LF")
    assert d["within"] is False and d["b"] is None


def test_two_nulls_are_stably_abstained_not_agreement_on_a_number():
    a, b = _boni(), _boni()
    a["starter_lf"] = None
    b["starter_lf"] = None
    s = compute_read_stability(a, b)
    assert "starter LF" in s["abstained"]
    assert all(x["name"] != "starter LF" for x in s["dims"]), \
        "an abstention never sits in the agreed-dims table"
    assert s["stable"] is True, \
        "stably abstained does not break stability — it is named instead"


def _walled(height):
    return _enforce_evidence_or_null(
        {**_boni(),
         "walls": [{"label": "back",
                    "width_ft": {"v": 58, "page": 2, "from": "58'-0\""},
                    "height_ft": height}]})


def test_stably_read_vs_stably_guessed_the_back_garage_case():
    """Two reads both abstaining on the back wall height = STABLY
    ABSTAINED (named, still needs a human). Under the pre-null schema
    two invented 10.0s would have chipped as agreement — the exact
    failure the build order exists to prevent."""
    a = _walled(None)
    b = _walled(None)
    s = compute_read_stability(a, b)
    assert "walls.back.height_ft" in s["abstained"]
    assert all(e["name"] != "walls.back.height_ft" for e in s["evidenced"])
    # evidenced-and-equal path DOES count as agreement
    e = next(x for x in s["evidenced"] if x["name"] == "walls.back.width_ft")
    assert e["within"] is True


def test_evidenced_once_and_null_once_is_a_disagreement():
    a = _walled({"v": 20.5, "page": 3, "from": "plate stack 20'-6\""})
    b = _walled(None)
    s = compute_read_stability(a, b)
    e = next(x for x in s["evidenced"] if x["name"] == "walls.back.height_ft")
    assert e["within"] is False and e["b"] is None
    assert s["stable"] is False


def test_evidenced_values_disagreeing_flag():
    a = _walled({"v": 20.5, "page": 3, "from": "20'-6\""})
    b = _walled({"v": 14.4, "page": 3, "from": "14'-5\""})
    s = compute_read_stability(a, b)
    e = next(x for x in s["evidenced"] if x["name"] == "walls.back.height_ft")
    assert e["within"] is False
    assert s["stable"] is False


# ---- wiring pins ----

def test_stability_rides_the_readback_never_persisted_into_it():
    out = _with_readback(
        {"raw_ai": {**_boni(), "roof_pitch": "7/12"}},
        stability={"stable": True, "counts": [], "dims": [],
                   "evidenced": [], "abstained": []})
    assert out["readback"]["stability"]["stable"] is True
    out2 = _with_readback({"raw_ai": {**_boni()}})
    assert "stability" not in (out2.get("readback") or {})


def test_worker_computes_stability_after_the_evidence_seam():
    seam = SRC.index("raw = _enforce_evidence_or_null(raw)")
    gate = SRC.index("stability = compute_read_stability(prev_raw, raw)")
    assert seam < gate, ("the gate must compare POST-enforcement reads — "
                         "built pre-null it certifies guesses")
    assert '"stability": stability,' in SRC, "stability must persist on the run doc"


def test_the_agreed_chip_never_claims_correctness():
    assert DICT_TEXT.count('"bp.rb.stability.agreed"') == 2, "EN+ES"
    assert DICT_TEXT.count('"bp.rb.stability.mismatch"') == 2
    assert DICT_TEXT.count('"bp.rb.stability.abstained"') == 2
    assert "stability, not correctness" in DICT_TEXT
    assert "no es exactitud" in DICT_TEXT
    assert "matches the printed dimension" not in DICT_TEXT.split(
        '"bp.rb.stability.agreed": "')[1].split('",')[0].replace(
        "against the printed dimension", ""), \
        "agreement must never print as a printed-dimension match"
