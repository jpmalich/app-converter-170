"""d667 reconciliation (ruled 2026-07-16): per-profile gable math conforms
to the C4 ×0.7 convention — the 0.5 true-triangle path is removed.

Pins:
  • breakdown_walls_by_profile gables use ×0.7 (not ×0.5)
  • the per-profile gable total equals the headline path's gable total —
    the intra-run self-disagreement (Δ108.6 on the d667 case) is closed
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from profile_callouts import breakdown_walls_by_profile


def _headline_gable(walls):
    # mirror apply_roof_type_material_math (ai_measure.py): 0.7 × w × h
    return sum(0.7 * float(w["width_ft"]) * float(w["gable_triangle_height_ft"])
               for w in walls if w.get("gable_triangle_height_ft"))


def test_gable_uses_070_convention():
    walls = [{"label": "front", "width_ft": 30, "eave_height_ft": 0,
              "siding_pct": 0, "gable_triangle_height_ft": 10.0,
              "body_profile_callout": "lap"}]
    b = breakdown_walls_by_profile(walls)
    # 0.7 × 30 × 10 = 210 (the removed 0.5 path would give 150)
    assert b["per_profile_sqft"]["lap"] == 210.0
    assert b["per_profile_sqft"]["lap"] != 150.0


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
    assert round(per_profile, 1) == round(headline, 1) == 380.1
    # the old 0.5 path produced 271.5 — a 108.6 sqft gap vs headline
    assert round(per_profile - 271.5, 1) == 108.6


def test_no_half_triangle_path_remains():
    src = (Path(__file__).resolve().parent.parent / "profile_callouts.py").read_text()
    assert "0.5 * width * gable_h" not in src
