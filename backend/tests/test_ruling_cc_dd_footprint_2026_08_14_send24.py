"""RULINGS CC + DD SYNTHETIC PINS (Howard sealed 2026-08-14 send-24)."""
import sys

sys.path.insert(0, "/app/backend")

from footprint_checks import footprint_closure, garage_side_verdict  # noqa: E402


# ── CC — garage-side contradiction detector ──

def _boni_like():
    # doors → front; garage naming → front + back; elevation labels → absent.
    return {
        "doors": [{"type_hint": "garage", "elevation": "front"},
                  {"type_hint": "garage", "elevation": "front"}],
        "walls": [
            {"label": "front", "height_segments": [
                {"label": "main body 2-story"}, {"label": "garage wing 1-story"}]},
            {"label": "back", "height_segments": [
                {"label": "main body 2-story"}, {"label": "garage wing 1-story"}]},
            {"label": "right", "height_segments": [
                {"label": "main body 2-story"}, {"label": "bonus room section"}]},
        ],
        "roof_planes": [{"label": "garage", "gable_end_faces": []}],
        "elevation_labels": [],
    }


def test_cc_fires_conflict_on_boni_and_names_each_signal():
    # Condition 2: MUST fire on Boni. Clean = broken.
    v = garage_side_verdict(_boni_like())
    assert v["status"] == "CONFLICT"
    assert v["side"] is None
    assert v["conflict"]["garage_doors"] == ["front"]
    assert v["conflict"]["garage_naming"] == ["back", "front"]
    assert v["door_signal_unreliable"] is True  # Ruling BB
    assert "no majority" in v["note"] and "no winner" in v["note"]


def test_cc_single_signal_is_unverified_not_confirmation():
    # Condition 1: absence is not agreement.
    m = {"walls": [{"label": "right", "height_segments": [{"label": "garage bay"}]}],
         "doors": [], "roof_planes": [], "elevation_labels": []}
    v = garage_side_verdict(m)
    assert v["status"] == "UNVERIFIED" and v["side"] is None
    assert "garage_doors" in v["absent"] and "elevation_labels" in v["absent"]


def test_cc_no_majority_vote_two_vs_one_still_refuses():
    m = {"doors": [{"type_hint": "garage", "elevation": "right"}],
         "walls": [{"label": "right", "height_segments": [{"label": "garage bay"}]}],
         "roof_planes": [],
         "elevation_labels": [{"title": "LEFT ELEVATION - GARAGE", "face": "left"}]}
    v = garage_side_verdict(m)
    # doors+naming say right, elevation says left → any two disagree → refuse.
    assert v["status"] == "CONFLICT"


def test_cc_all_agree_is_verified_side_only():
    m = {"doors": [{"type_hint": "garage", "elevation": "right"}],
         "walls": [{"label": "right", "height_segments": [{"label": "garage bay"}]}],
         "roof_planes": [],
         "elevation_labels": [{"title": "RIGHT - GARAGE", "face": "right"}]}
    v = garage_side_verdict(m)
    assert v["status"] == "VERIFIED" and v["side"] == ["right"]
    assert "WHICH SIDE only" in v["note"]


# ── DD — footprint closure ──

def test_dd_right_39_cannot_close_when_left_depth_unread():
    # Boni: right depth = 30+9 = 39 (segments), left depth not read.
    m = {"walls": [
        {"label": "front", "width_ft": 58.0, "height_segments": [
            {"label": "main", "width_ft": 34.0}, {"label": "garage", "width_ft": 24.0}]},
        {"label": "back", "width_ft": 58.0},
        {"label": "left"},  # depth not read
        {"label": "right", "width_ft": None, "height_segments": [
            {"label": "main body 2-story", "width_ft": 30.0},
            {"label": "bonus room section", "width_ft": 9.0}]},
    ]}
    fp = footprint_closure(m)
    assert fp["closes"] is False
    assert "right" in fp["unverified_faces"]
    assert any("right" in r and "cannot be closed" in r for r in fp["failing_relations"])


def test_dd_segments_must_sum_to_face_width():
    m = {"walls": [{"label": "front", "width_ft": 58.0, "height_segments": [
        {"label": "main", "width_ft": 34.0}, {"label": "garage", "width_ft": 20.0}]}]}
    fp = footprint_closure(m)  # 34+20=54 != 58
    assert fp["closes"] is False
    assert any("do not close to the face" in r for r in fp["failing_relations"])


def test_dd_clean_rectangle_closes():
    m = {"walls": [
        {"label": "front", "width_ft": 40.0},
        {"label": "back", "width_ft": 40.0},
        {"label": "left", "width_ft": 30.0},
        {"label": "right", "width_ft": 30.0},
    ]}
    fp = footprint_closure(m)
    assert fp["closes"] is True and not fp["failing_relations"]


def test_dd_front_back_width_mismatch_flagged():
    m = {"walls": [{"label": "front", "width_ft": 58.0},
                   {"label": "back", "width_ft": 52.0}]}
    fp = footprint_closure(m)
    assert fp["closes"] is False
    assert any("does not close on width" in r for r in fp["failing_relations"])
