"""d667 reconciliation (ruled 2026-07-16) — NAMED PIN UPDATE (SEND-137,
Howard ruled 2026-08-27).

THE DEFECT THIS FILE EXISTS FOR IS THE SELF-DISAGREEMENT: the per-profile
gable total and the headline gable total must be THE SAME NUMBER (Δ108.6 on
the d667 case when they were not). That is unchanged and is what these pins
still hold.

WHAT CHANGED: the shared number. It was ×0.7 (the C4 angle-cut convention);
it is now ½ × width × rise — the measured triangle. THE 0.70 FACTOR IS
RETIRED: not a fallback, not a waste factor, not a default. Both surfaces
moved together, so the disagreement stays closed at the ruled figure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from measure_staging import GABLE_TRIANGLE_FACTOR
from profile_callouts import breakdown_walls_by_profile


def _headline_gable(walls):
    # mirror the shared walk (measure_staging.walk_walls): ½ × w × rise
    return sum(GABLE_TRIANGLE_FACTOR * float(w["width_ft"])
               * float(w["gable_triangle_height_ft"])
               for w in walls if w.get("gable_triangle_height_ft"))


def test_gable_uses_the_measured_triangle():
    walls = [{"label": "front", "width_ft": 30, "eave_height_ft": 0,
              "siding_pct": 0, "gable_triangle_height_ft": 10.0,
              "body_profile_callout": "lap"}]
    b = breakdown_walls_by_profile(walls)
    # ½ × 30 × 10 = 150 (the retired 0.70 path would give 210)
    assert b["per_profile_sqft"]["lap"] == 150.0
    assert b["per_profile_sqft"]["lap"] != 210.0


def test_d667_self_disagreement_closed():
    # the exact d667 case: two gable ends, 30' wide, heights 8.8 and 9.3
    walls = [
        {"label": "front", "width_ft": 30, "eave_height_ft": 0, "siding_pct": 0,
         "gable_triangle_height_ft": 8.8, "body_profile_callout": "lap"},
        {"label": "back", "width_ft": 30, "eave_height_ft": 0, "siding_pct": 0,
         "gable_triangle_height_ft": 9.3, "body_profile_callout": "lap"},
    ]
    b = breakdown_walls_by_profile(walls)
    per_profile = b["per_profile_sqft"]["lap"]
    headline = _headline_gable(walls)
    # ½ × 30 × (8.8 + 9.3) = 271.5 — ONE number on both surfaces.
    assert round(per_profile, 1) == round(headline, 1) == 271.5
    # the retired 0.70 path produced 380.1 on this case
    assert round(380.1 - per_profile, 1) == 108.6


def test_no_second_gable_formula_remains():
    src = (Path(__file__).resolve().parent.parent / "profile_callouts.py").read_text()
    assert "0.7 * width * gable_h" not in src
    assert "0.5 * width * gable_h" not in src   # the constant is imported
    assert "GABLE_TRIANGLE_FACTOR * width * gable_h" in src
