"""Iter 79j.70 — bbox restore + per-dormer routing unit tests.

The text-only reconciler emits {0,0,0,0} bbox placeholders (pixel bboxes
are stripped from its payload). `_restore_bboxes_from_phase_a` re-joins
final openings to their Phase A pixel bboxes and normalizes them by the
compressed-photo dims stamped at extraction time. Fixtures mirror the
2026-07-08 validation run (ec289060c8...).
"""
import sys

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")

from routes.ai_measure import _restore_bboxes_from_phase_a  # noqa: E402


def make_extractions():
    return [
        {
            "index": 0, "_photo_idx": 0, "_image_w": 1280, "_image_h": 960,
            "openings_this_photo": [
                {"opening_id": "front-w1", "type": "window", "width_in": 48,
                 "along_wall_ft": 13.3, "bbox": [713, 340, 165, 118]},
                {"opening_id": "front-gd1", "type": "garage_door", "width_in": 97,
                 "along_wall_ft": 6.9, "bbox": [368, 672, 335, 260]},
            ],
        },
        {
            "index": 2, "_photo_idx": 2, "_image_w": 1200, "_image_h": 900,
            "openings_this_photo": [
                {"opening_id": "left-d1-w1", "type": "window", "width_in": 49,
                 "along_wall_ft": 14.0, "bbox": [300, 200, 100, 70]},
            ],
        },
        {
            "index": 6, "_photo_idx": 6, "_image_w": 1000, "_image_h": 750,
            "openings_this_photo": [
                {"opening_id": "right-w1", "type": "window", "width_in": 30,
                 "along_wall_ft": 5.0, "bbox": [100, 300, 50, 90]},
                # id mismatch target for positional fallback
                {"opening_id": "right-wX", "type": "window", "width_in": 32,
                 "along_wall_ft": 12.0, "bbox": [500, 310, 55, 92]},
            ],
        },
        # photo without dims (legacy persisted extraction)
        {
            "index": 7, "_photo_idx": 7,
            "openings_this_photo": [
                {"opening_id": "right-w1-upper", "type": "window", "width_in": 48,
                 "along_wall_ft": 7.7, "bbox": [400, 100, 120, 80]},
            ],
        },
    ]


ZERO = {"x": 0, "y": 0, "w": 0, "h": 0}


def make_final():
    return {
        "openings": [
            {"opening_id": "front-w1", "type": "window", "wall": "front",
             "photo_idx": 0, "width_in": 48, "along_wall_ft": 13.3,
             "on_dormer": False, "bbox": dict(ZERO)},
            # reconciler-suffixed id → suffix-strip match
            {"opening_id": "right-w1-p6", "type": "window", "wall": "right",
             "photo_idx": 6, "width_in": 30, "along_wall_ft": 5.0,
             "on_dormer": False, "bbox": dict(ZERO)},
            # id not present anywhere → positional fallback in photo 6
            {"opening_id": "merged-right-2", "type": "window", "wall": "right",
             "photo_idx": 6, "width_in": 32, "along_wall_ft": 12.4,
             "on_dormer": False, "bbox": dict(ZERO)},
            # dormer opening, wall matches dormer face directly
            {"opening_id": "left-d1-w1", "type": "window", "wall": "left",
             "photo_idx": 2, "width_in": 49, "along_wall_ft": 14.0,
             "on_dormer": True, "bbox": dict(ZERO)},
            # dormer opening, photo has NO dims → bbox dropped, face via photo map
            {"opening_id": "right-w1-upper", "type": "window", "wall": "upper",
             "photo_idx": 7, "width_in": 48, "along_wall_ft": 7.7,
             "on_dormer": True, "bbox": dict(ZERO)},
            # nothing matches at all → zero bbox must become None
            {"opening_id": "ghost", "type": "entry_door", "wall": "back",
             "photo_idx": 4, "width_in": 36, "along_wall_ft": 9.0,
             "on_dormer": False, "bbox": dict(ZERO)},
        ],
        "dormers": [
            {"face": "left", "width_ft": 17, "_source_photo_indices": [2, 3, 1]},
            {"face": "right", "width_ft": 15, "_source_photo_indices": [7]},
        ],
    }


def run():
    final = make_final()
    _restore_bboxes_from_phase_a(final, make_extractions())
    return {o["opening_id"]: o for o in final["openings"]}


def test_exact_id_match_normalizes_bbox():
    o = run()["front-w1"]
    assert o["_bbox_source"] == "phase_a_id"
    assert o["bbox_photo_idx"] == 0
    b = o["bbox"]
    assert abs(b["x"] - 713 / 1280) < 1e-9
    assert abs(b["y"] - 340 / 960) < 1e-9
    assert abs(b["w"] - 165 / 1280) < 1e-9
    assert abs(b["h"] - 118 / 960) < 1e-9


def test_suffix_stripped_id_match():
    o = run()["right-w1-p6"]
    assert o["_bbox_source"] == "phase_a_id"
    assert o["bbox_photo_idx"] == 6
    assert abs(o["bbox"]["x"] - 100 / 1000) < 1e-9


def test_positional_fallback_match():
    o = run()["merged-right-2"]
    assert o["_bbox_source"] == "phase_a_position"
    assert abs(o["bbox"]["x"] - 500 / 1000) < 1e-9


def test_unmatched_zero_bbox_dropped():
    o = run()["ghost"]
    assert o["bbox"] is None
    assert "_bbox_source" not in o


def test_photo_without_dims_drops_bbox_but_routes_face():
    o = run()["right-w1-upper"]
    assert o["bbox"] is None          # no dims on photo 7 → can't normalize
    assert o["dormer_face"] == "right"  # routed via dormer _source_photo_indices


def test_dormer_face_from_wall_label():
    o = run()["left-d1-w1"]
    assert o["dormer_face"] == "left"
    assert o["_bbox_source"] == "phase_a_id"
    assert o["bbox_photo_idx"] == 2


def test_no_openings_key_is_noop():
    final = {"walls": []}
    _restore_bboxes_from_phase_a(final, make_extractions())
    assert final == {"walls": []}
