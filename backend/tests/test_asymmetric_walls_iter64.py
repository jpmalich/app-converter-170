"""Iter 79j.64 — Asymmetric-wall fixes, pinned against red-house tape truth.

Red-house tape (Jul 8 2026, contractor sketch in /app/memory):
  LEFT wall 10.3125 ft uniform · RIGHT wall 7.1875 ft uniform ·
  FRONT/BACK are 27 ft gable ends carrying a 39" step over the last
  13'4" · dormers 15.0 / 15.0 ft · knee walls 4.06 ft.

Three defects fixed in this iter:
  1. `outside_corner_lf` was `4 × avg_wall_height_ft` — a symmetry
     assumption. True corner LF = 2×10.31 + 2×7.19 = 35.0 (corner posts
     stand at eave lines; on a gable-ended house the corner height is
     the adjoining EAVE-side wall's height).
  2. The <7 ft "nonsense" clamp silently overwrote genuinely short walls
     with the global average. Right wall tapes 7.19 ft — one slightly-low
     read and the clamp would have erased real asymmetry. Now only <4 ft
     junk (story-units, 0.7-ft fractions) is replaced; 4-7 ft readings
     are kept and flagged `_height_flag: below_typical_range`.
  3. `_derive_pin_gap_hints` flagged BOTH red-house dormers as
     "unanchored" even though each width was anchored to a contractor
     wall bar (Run 3 false positives). Two dead detection paths:
     the source-photos lookup used keys that never existed
     (`source_photos` vs the real `_source_photo_indices`), and the
     anchor-text regex never scanned `_per_photo_readings[].notes`
     where the citation actually lives.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv(Path("/app/backend/.env"))

from routes.ai_measure import (  # noqa: E402
    _aggregate_to_hover_shape,
    _corner_lf_from_walls,
    _derive_pin_gap_hints,
)


def _wall(label, h, gable=0.0, width=27.0):
    return {
        "label": label,
        "width_ft": width,
        "height_ft": h,
        "gable_triangle_height_ft": gable,
        "siding_pct_this_wall": 100,
    }


# ---------------------------------------------------------------------------
# 1. Per-corner outside corner LF
# ---------------------------------------------------------------------------

class TestCornerLfFromWalls:
    def test_red_house_tape_truth(self):
        """Gable front/back + eave left/right → corners follow the
        eave-side walls: 2×10.3125 + 2×7.1875 = 35.0 exactly."""
        walls = [
            _wall("front", 8.77, gable=9.0),   # stepped gable end — area-avg height
            _wall("back", 8.77, gable=8.5),
            _wall("left", 10.3125, width=37),
            _wall("right", 7.1875, width=37),
        ]
        assert _corner_lf_from_walls(walls) == 35.0

    def test_run3_compressed_reads_still_beat_avg_formula(self):
        """Even Run 3's compressed reads (left 9.0 / right 8.5) give
        2×9.0 + 2×8.5 = 35.0 vs tape 35.0 — the old 4×avg gave 35.6."""
        walls = [
            _wall("front", 8.5, gable=9.0),
            _wall("back", 9.3, gable=8.5),
            _wall("left", 9.0, width=37),
            _wall("right", 8.5, width=37),
        ]
        assert _corner_lf_from_walls(walls) == 35.0

    def test_hip_roof_uses_min_of_adjacent(self):
        """No gable ends (hip) → each corner takes min(adjacent)."""
        walls = [
            _wall("front", 9.0),
            _wall("back", 9.0),
            _wall("left", 10.0, width=37),
            _wall("right", 8.0, width=37),
        ]
        # corners: f-l min(9,10)=9, f-r min(9,8)=8, b-l 9, b-r 8 → 34
        assert _corner_lf_from_walls(walls) == 34.0

    def test_missing_wall_returns_zero_for_fallback(self):
        walls = [_wall("front", 9.0), _wall("left", 9.0)]
        assert _corner_lf_from_walls(walls) == 0.0

    def test_unmeasured_height_returns_zero(self):
        walls = [
            _wall("front", 9.0), _wall("back", 9.0),
            _wall("left", 9.0), _wall("right", 0),
        ]
        assert _corner_lf_from_walls(walls) == 0.0

    def test_aggregate_overrides_claude_corner_estimate(self):
        """_aggregate_to_hover_shape prefers per-corner math over the
        raw AI outside_corner_lf when all 4 walls carry heights."""
        raw = {
            "walls": [
                _wall("front", 8.5, gable=9.0),
                _wall("back", 9.3, gable=8.5),
                _wall("left", 10.3125, width=37),
                _wall("right", 7.1875, width=37),
            ],
            "openings": [],
            "avg_wall_height_ft": 8.9,
            "outside_corner_lf": 36.0,   # Claude's 4×avg-ish guess
            "story_count": 1.5,
        }
        m = _aggregate_to_hover_shape(raw)
        assert m["outside_corner_lf"] == 35.0

    def test_aggregate_falls_back_to_claude_when_wall_missing(self):
        raw = {
            "walls": [
                _wall("front", 8.5, gable=9.0),
                _wall("left", 10.0, width=37),
            ],
            "openings": [],
            "avg_wall_height_ft": 8.9,
            "outside_corner_lf": 36.0,
            "story_count": 1.5,
        }
        m = _aggregate_to_hover_shape(raw)
        assert m["outside_corner_lf"] == 36.0


# ---------------------------------------------------------------------------
# 2. Clamp-to-amber: 4-7 ft kept + flagged; <4 ft still replaced
# ---------------------------------------------------------------------------

class TestShortWallClamp:
    def test_genuinely_short_wall_is_kept_and_flagged(self):
        """A 6.5 ft read must NOT be overwritten with the 8.9 avg."""
        w = _wall("right", 6.5, width=37)
        raw = {
            "walls": [w],
            "openings": [],
            "avg_wall_height_ft": 8.9,
            "story_count": 1,
        }
        m = _aggregate_to_hover_shape(raw)
        # area math used the real 6.5, not the avg
        assert m["siding_sqft"] == round(37 * 6.5, 1)
        assert w["_height_flag"] == "below_typical_range"
        assert "verify with tape" in w["_reconciliation_note"]

    def test_red_house_right_wall_7_19_untouched(self):
        """7.19 ft is above the flag band — kept clean, no flag."""
        w = _wall("right", 7.1875, width=37)
        raw = {"walls": [w], "openings": [], "avg_wall_height_ft": 8.9, "story_count": 1}
        m = _aggregate_to_hover_shape(raw)
        assert m["siding_sqft"] == round(37 * 7.1875, 1)
        assert "_height_flag" not in w

    def test_story_unit_junk_still_replaced(self):
        """1.0 (story-units) is junk → replaced by the global avg."""
        w = _wall("front", 1.0)
        raw = {"walls": [w], "openings": [], "avg_wall_height_ft": 8.9, "story_count": 1}
        m = _aggregate_to_hover_shape(raw)
        assert m["siding_sqft"] == round(27 * 8.9, 1)

    def test_fraction_junk_still_replaced(self):
        w = _wall("front", 0.7)
        raw = {"walls": [w], "openings": [], "avg_wall_height_ft": 0, "story_count": 1.5}
        m = _aggregate_to_hover_shape(raw)
        assert m["siding_sqft"] == round(27 * 12.0, 1)   # 1.5-story default


# ---------------------------------------------------------------------------
# 3. Pin-gap unanchored-dormer false positives (Run 3 regression)
# ---------------------------------------------------------------------------

def _hints(dormers, annotations=None):
    return _derive_pin_gap_hints(
        annotations=annotations,
        walls=[],
        dormers=dormers,
        orphaned_walls=[],
        empty_photos=[],
    )


class TestUnanchoredDormerFalsePositives:
    RUN3_LEFT = {
        "face": "left",
        "width_ft": 15.5,
        "width_source": "direct_single_reading",
        "_source_photo_indices": [1, 2],
        "_per_photo_readings": [
            {"photo_idx": 1, "approx_width_ft": 18, "role": "rejected",
             "notes": "rejected for width — corner shot"},
            {"photo_idx": 2, "approx_width_ft": 15.5, "role": "width",
             "notes": "direct LEFT elevation, anchored to 444\" wall bar"},
        ],
        "_reconciliation_note": "width 15.5 ft is the only valid direct reading",
    }
    RUN3_RIGHT = {
        "face": "right",
        "width_ft": 16.5,
        "width_source": "direct_single_reading",
        "_source_photo_indices": [6, 7],
        "_per_photo_readings": [
            {"photo_idx": 6, "approx_width_ft": 16.5, "role": "width",
             "notes": "direct RIGHT elevation, 180\" bar scale, dormer window full-front"},
            {"photo_idx": 7, "approx_width_ft": 11, "role": "rejected",
             "notes": "rejected for width — foreshortened"},
        ],
        "_reconciliation_note": "kept photo 6's direct 16.5 ft",
    }

    def test_run3_dormers_no_longer_flagged(self):
        """Exact Run 3 payload shape — both dormers cited wall bars in
        their kept width reading's notes. Zero unanchored hints."""
        hints = _hints([self.RUN3_LEFT, self.RUN3_RIGHT])
        assert [h for h in hints if h["kind"] == "unanchored_dormer_width"] == []

    def test_scale_ref_new_shape_credits_source_photos(self):
        """No text citation, but photo 2 carries a wizard-shape
        `_scale_refs` entry ({inches}) → anchored via photo lookup."""
        d = {
            "face": "left", "width_ft": 15.5,
            "width_source": "direct_single_reading",
            "_source_photo_indices": [2],
            "_per_photo_readings": [
                {"photo_idx": 2, "approx_width_ft": 15.5, "role": "width",
                 "notes": "direct read"},
            ],
        }
        ann = {"_scale_refs": {"2": {"p1_x": 0.1, "p2_x": 0.9, "inches": 444}}}
        hints = _hints([d], annotations=ann)
        assert [h for h in hints if h["kind"] == "unanchored_dormer_width"] == []

    def test_scale_ref_old_annotator_shape_credits_source_photos(self):
        """ProfileAnnotator shape ({px_height, real_ft}) counts too."""
        d = {
            "face": "right", "width_ft": 16.5,
            "width_source": "direct_single_reading",
            "_source_photo_indices": [6],
            "_per_photo_readings": [
                {"photo_idx": 6, "approx_width_ft": 16.5, "role": "width",
                 "notes": "direct read"},
            ],
        }
        ann = {"_scale_refs": {"6": {"px_height": 224, "real_ft": 15.0}}}
        hints = _hints([d], annotations=ann)
        assert [h for h in hints if h["kind"] == "unanchored_dormer_width"] == []

    def test_truly_unanchored_dormer_still_fires_with_photo_idxs(self):
        """A dormer with no citation anywhere and no scale refs must
        still fire — and now carries its real source photo indices."""
        d = {
            "face": "left", "width_ft": 14.0,
            "width_source": "direct_single_reading",
            "_source_photo_indices": [1, 2],
            "_per_photo_readings": [
                {"photo_idx": 2, "approx_width_ft": 14.0, "role": "width",
                 "notes": "estimated from siding courses"},
            ],
        }
        hints = _hints([d])
        un = [h for h in hints if h["kind"] == "unanchored_dormer_width"]
        assert len(un) == 1
        assert un[0]["source_photo_idxs"] == [1, 2]

    def test_rejected_reading_anchor_does_not_count(self):
        """Anchor words in a REJECTED reading's notes must not credit
        the kept width (the kept read is what needs the anchor)."""
        d = {
            "face": "right", "width_ft": 12.0,
            "width_source": "direct_single_reading",
            "_source_photo_indices": [3],
            "_per_photo_readings": [
                {"photo_idx": 7, "approx_width_ft": 18, "role": "rejected",
                 "notes": "rejected — WALL_REF bar was in this frame but shot too oblique"},
                {"photo_idx": 3, "approx_width_ft": 12.0, "role": "width",
                 "notes": "eyeballed from ridge proportion"},
            ],
        }
        hints = _hints([d])
        assert len([h for h in hints if h["kind"] == "unanchored_dormer_width"]) == 1
