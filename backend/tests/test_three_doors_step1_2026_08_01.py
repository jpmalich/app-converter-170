"""STEP 1 SEALS — Three Doors build (Howard ruled 2026-08-01).
ONE aggregation copy: ONE gable formula all doors · door_count lands on every
door · ONE window-openings builder (paired by shared UUID) · full precision at
intake (round once, at the order layer) · no second copy of the walk anywhere.

NAMED PIN UPDATE (SEND-137, Howard ruled 2026-08-27): the sealed factor moves
from 0.70 to ½ — the measured triangle. STEP 1'S INVARIANT IS UNCHANGED and is
what these pins hold: ONE formula, both doors, no second copy."""
import inspect

from measure_staging import (GABLE_TRIANGLE_FACTOR, walk_walls,
                             bucket_openings, build_paired_openings)
from routes.ai_measure import _aggregate_to_hover_shape as photo_agg
from routes.ai_blueprint import _aggregate_to_hover_shape as bp_agg


def test_gable_factor_is_the_measured_triangle():
    assert GABLE_TRIANGLE_FACTOR == 0.5


def test_same_gable_same_area_both_ai_doors():
    """The door divergence stays CLOSED: identical wall reads yield
    identical gable credit through photo and blueprint (no pitch)."""
    walls = [{"label": "front", "width_ft": 32, "height_ft": 9,
              "gable_triangle_height_ft": 6, "siding_pct_this_wall": 100,
              "_source_photo_indices": [0],
              "width_ft_source": "direct_ref",
              "height_ft_source": "direct_single_reading"}]
    p = photo_agg({"walls": [dict(w) for w in walls], "openings": []})
    b = bp_agg({"walls": [dict(w) for w in walls], "windows": [], "doors": []})
    expect = 0.5 * 32 * 6
    assert p["_ai_gable_sqft"] == round(expect, 1)
    assert b["_ai_gable_sqft"] == round(expect, 1)
    assert p["siding_sqft"] == b["siding_sqft"] == 32 * 9 + expect


def test_door_count_lands_on_both_ai_doors():
    """Finding 6 (ruled): entry+patio+garage SUM lands — caulk + J-blocks
    read it. Silent zero retired on photo and blueprint."""
    p = photo_agg({"walls": [], "openings": [], "openings_schedule": [
        {"type": "window", "count": 2, "width_in": 36, "height_in": 54},
        {"type": "entry_door", "count": 1, "width_in": 36, "height_in": 80},
        {"type": "patio_door", "count": 1, "width_in": 72, "height_in": 80},
        {"type": "garage_door", "count": 2, "width_in": 96, "height_in": 84}]})
    assert p["door_count"] == 4
    b = bp_agg({"walls": [], "windows": [],
                "doors": [{"type_hint": "entry", "qty": 1, "width_in": 36, "height_in": 80},
                          {"type_hint": "garage double", "qty": 1, "width_in": 192, "height_in": 84}]})
    assert b["door_count"] == 2


def test_full_precision_at_intake():
    """Ruling 7: no door rounds on the way in — 9'7" stays 9.583…'."""
    h = 9 + 7 / 12.0
    p = photo_agg({"walls": [{"label": "front", "width_ft": 33.3, "height_ft": h}],
                   "openings": []})
    assert p["siding_sqft"] == 33.3 * h            # not round(x, 1)
    b = bp_agg({"walls": [{"label": "front", "width_ft": 33.3, "height_ft": h}],
                "windows": [], "doors": [], "eaves_lf": 70.333})
    assert b["siding_sqft"] == 33.3 * h
    assert b["eaves_lf"] == 70.333


def test_one_paired_openings_builder():
    """Finding 10b (ruled): ONE builder, vero+mezzo paired by shared UUID
    in both dims mode (hover/blueprint) and style mode (photo)."""
    v, z = build_paired_openings(windows=[{"id": "W1", "width_in": 44, "height_in": 40}])
    assert len(v) == len(z) == 1 and v[0]["id"] == z[0]["id"]
    assert v[0]["product_type"] == "Vero 2-Lite Slider"
    assert z[0]["product_type"] == "Mezzo 2-Lite Slider"
    v2, z2 = build_paired_openings(schedule=[
        {"type": "window", "count": 1, "width_in": 36, "height_in": 60,
         "style": "Twin Double Hung", "elevation": "front"}])
    assert len(v2) == len(z2) == 2                 # qty multiplier honored
    assert all(a["id"] == b["id"] for a, b in zip(v2, z2))
    assert v2[0]["ai_style"] == "Twin Double Hung"


def test_no_second_copy_of_the_walk():
    """No-fourth-copy constraint: neither AI door carries its own gable
    math or intake rounding on engine keys any more."""
    for mod_fn in (photo_agg, bp_agg):
        src = inspect.getsource(mod_fn)
        assert "0.5 * width" not in src and "0.5 * _wft" not in src
        assert "0.7 * width_ft * gable_h" not in src
        assert 'round(siding_sqft, 1)' not in src
        assert "walk_walls" in src and "bucket_openings" in src


def test_shared_walk_and_buckets_math():
    w = walk_walls([{"width_ft": 30, "height_ft": 8.5,
                     "gable_triangle_height_ft": 8.5,
                     "siding_pct_this_wall": 0.85}])   # fraction defense
    assert w["siding_sqft"] == 30 * 8.5 * 0.85
    assert w["gable_sqft"] == 0.5 * 30 * 8.5
    bk = bucket_openings([{"type": "entry_door", "count": 2, "width_in": 36, "height_in": 80}])
    assert bk["door_count"] == 2 and bk["opening_count"] == 2
    assert bk["opening_perimeter_lf"] == 2 * 2 * ((36 + 80) / 12.0)
