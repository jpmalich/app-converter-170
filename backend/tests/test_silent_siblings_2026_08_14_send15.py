"""RULING H — REPAIR THE SILENT SIBLINGS AS ONE CLASS (send-15, 2026-08-14).

'A KILLED OR SUBSET INPUT NEVER PRODUCES A SILENT NUMBER. It produces a
named refusal or a disclosed subset. Silent 0 is the worst available
outcome.' PREFERRED SHAPE: make the SUBSET-AWARE VALUE the only thing a
reader can obtain.

Built this send: the ONE-COPY subset-aware accessors
`wall_width_for_pricing` / `wall_height_for_pricing`, and the two readers
with a disclosure channel wired to them — walk_walls gable (canonical
honesty, resolving the Report-2 disagreement with profile_callouts) and
eaves_from_walls (refuses to silently short the sum). The remaining
readers (base course, batten, corners) are reported in the send-15
register with their build status — see also Ruling G for corners.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from measure_staging import (  # noqa: E402
    wall_width_for_pricing, wall_height_for_pricing,
    walk_walls, eaves_from_walls,
)


def test_accessor_returns_subset_and_names_missing_never_silent_zero():
    w = {"label": "front", "width_ft": None,
         "height_segments": [
             {"label": "main", "width_ft": 20.0},
             {"label": "wing", "width_ft": None}]}
    width, ok, subset, missing = wall_width_for_pricing(w)
    assert width == 20.0 and ok is True and subset is True
    assert missing == ["wing"]


def test_accessor_killed_width_is_not_derivable_names_wall():
    w = {"label": "left", "width_ft": None}
    width, ok, subset, missing = wall_width_for_pricing(w)
    assert width == 0.0 and ok is False
    assert missing == ["left"]


def test_height_accessor_killed_height_is_not_derivable():
    h, ok = wall_height_for_pricing({"label": "back", "height_ft": None})
    assert h == 0.0 and ok is False


def test_walk_walls_gable_discloses_never_silent_zero():
    """A gable-end wall whose width was killed reports the gable NOT
    DERIVABLE and names the wall — never a silent 0 added to gable_sqft."""
    walls = [{"label": "front", "width_ft": None, "height_ft": 10.0,
              "gable_triangle_height_ft": 6.0}]
    res = walk_walls(walls)
    fnd = [f for f in res["faces_not_derivable"] if f.get("surface") == "gable"]
    assert fnd and fnd[0]["label"] == "front"
    assert "not read" in fnd[0]["reason"]


def test_walk_walls_and_breakdown_gable_now_agree_on_honesty():
    """Report-2 disagreement resolved: the DISCLOSING path is canonical.
    A derivable gable still computes; the killed one discloses in BOTH."""
    walls = [{"label": "front", "width_ft": 30.0, "height_ft": 10.0,
              "gable_triangle_height_ft": 6.0}]
    res = walk_walls(walls)
    assert res["gable_sqft"] > 0                       # derivable → computes
    assert not [f for f in res["faces_not_derivable"]
                if f.get("surface") == "gable"]


def test_eaves_refuses_to_silently_short_a_killed_width():
    """A gable-end wall makes eaves = Σ non-gable widths. If a non-gable
    wall's width is killed, the correction is REFUSED (raw read stands),
    never a silently-short corrected number."""
    walls = [
        {"label": "front", "gable_triangle_height_ft": 6.0, "width_ft": 40.0},
        {"label": "left", "gable_triangle_height_ft": 0, "width_ft": None},
        {"label": "right", "gable_triangle_height_ft": 0, "width_ft": 30.0},
    ]
    # raw read (the model's eaves) stands rather than a short 30.
    assert eaves_from_walls(walls, raw_eaves=90.0) == 90.0


def test_eaves_corrects_when_every_contributing_width_is_derivable():
    walls = [
        {"label": "front", "gable_triangle_height_ft": 6.0, "width_ft": 40.0},
        {"label": "left", "gable_triangle_height_ft": 0, "width_ft": 28.0},
        {"label": "right", "gable_triangle_height_ft": 0, "width_ft": 28.0},
    ]
    assert eaves_from_walls(walls, raw_eaves=120.0) == 56.0
