"""STEP 2 — DROPPED-FIELD REGISTERS ON ALL THREE DOORS (Howard ruled
2026-08-01, ruling 5 + ruling 6 "source provides it → engine consumes it").
Same alarm as Hover's Class B, now on blueprint + photo:
  · a field the aggregator emits with NO register entry FAILS
  · a register field the aggregator stops emitting (a DROP) FAILS
  · named consumers must exist in code (spot-checked at the source level)
  · writer-key == reader-key pinned for footprint_perimeter_ft (named item)
Detection only — this file changes NO derivation and NO dollar."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from door_field_register import (BLUEPRINT_FIELD_REGISTER, PHOTO_FIELD_REGISTER,
                                 CONSUMED, NOT_CONSUMED)
from hover_field_register import HOVER_FIELD_REGISTER
from routes.ai_measure import _aggregate_to_hover_shape as photo_agg
from routes.ai_blueprint import _aggregate_to_hover_shape as bp_agg

# Rich fixtures: every source-suppliable field present, so every register
# key must land. A landing that stops happening = a DROP = red build.
PHOTO_RAW = {
    "walls": [{"label": "front", "width_ft": 32, "height_ft": 9,
               "gable_triangle_height_ft": 6}],
    "openings": [{"type": "window", "width_in": 36, "height_in": 54, "wall": "front"}],
    "openings_schedule": [
        {"type": "window", "count": 2, "width_in": 36, "height_in": 54, "style": "Double Hung"},
        {"type": "entry_door", "count": 1, "width_in": 36, "height_in": 80},
        {"type": "vent", "count": 1, "width_in": 12, "height_in": 18}],
    "corner_locations": [{"type": "outside"}, {"type": "outside"}, {"type": "inside"}],
    "eaves_lf": 70, "rakes_lf": 30, "starter_lf": 100, "inside_corner_lf": 9,
    "shutter_count": 2, "avg_wall_height_ft": 9, "story_count": 2,
}
BP_RAW = {
    "walls": [{"label": "front", "width_ft": 32, "height_ft": 9,
               "gable_triangle_height_ft": 6}],
    "windows": [{"id": "W1", "qty": 2, "width_in": 36, "height_in": 54, "elevation": "front"}],
    "doors": [{"type_hint": "entry", "qty": 1, "width_in": 36, "height_in": 80}],
    "eaves_lf": 70, "rakes_lf": 30, "avg_wall_height_ft": 9, "story_count": 2,
    "outside_corner_count": 4, "outside_corner_lf": 36,
    "inside_corner_count": 1, "inside_corner_lf": 9,
    "soffit_sqft": 120, "level_frieze_lf": 70, "sloped_frieze_lf": 30,
    "drip_edge_lf": 95, "total_trim_sqft": 40, "footprint_area_sqft": 900,
    "address": "123 Main St", "vent_count": 1, "shutter_count": 2,
    "opening_facade_assignments": [{"id": "W1", "facade": "brick"}],
}


def _engine_keys(m):
    return {k for k in m if not k.startswith("_")}


def test_photo_register_no_unregistered_field_and_no_drop():
    m = photo_agg(dict(PHOTO_RAW))
    emitted = _engine_keys(m)
    unregistered = emitted - set(PHOTO_FIELD_REGISTER)
    assert not unregistered, f"NEW photo field(s) with no register ruling: {sorted(unregistered)}"
    dropped = set(PHOTO_FIELD_REGISTER) - emitted
    assert not dropped, f"photo door DROPPED registered field(s): {sorted(dropped)}"


def test_blueprint_register_no_unregistered_field_and_no_drop():
    m = bp_agg(dict(BP_RAW))
    emitted = _engine_keys(m)
    unregistered = emitted - set(BLUEPRINT_FIELD_REGISTER)
    assert not unregistered, f"NEW blueprint field(s) with no register ruling: {sorted(unregistered)}"
    dropped = set(BLUEPRINT_FIELD_REGISTER) - emitted
    assert not dropped, f"blueprint door DROPPED registered field(s): {sorted(dropped)}"


def test_every_entry_has_named_consumer_or_reason():
    for reg in (BLUEPRINT_FIELD_REGISTER, PHOTO_FIELD_REGISTER):
        for field, entry in reg.items():
            if entry["status"] == CONSUMED:
                assert entry.get("consumed_by"), f"{field}: CONSUMED with no consumer named"
            else:
                assert entry["status"] == NOT_CONSUMED and entry.get("reason"), \
                    f"{field}: not-consumed with no reason"


# ── Named item: FOOTPRINT-PERIMETER KEY FIX — writer-key == reader-key ──
def test_footprint_perimeter_writer_key_equals_reader_key():
    import routes.lp_package_routes as lpr
    reader_src = inspect.getsource(lpr)
    assert '"footprint_perimeter_ft"' in reader_src or "'footprint_perimeter_ft'" in reader_src
    b = bp_agg(dict(BP_RAW))
    assert b.get("footprint_perimeter_ft") == 32.0, \
        "blueprint must WRITE the key the batten machinery READS"
    p = photo_agg(dict(PHOTO_RAW))
    assert p.get("footprint_perimeter_ft") == 32.0


# ── Landings behave (supplied → consumed, never re-typed) ───────────────
def test_blueprint_printed_figures_land():
    b = bp_agg(dict(BP_RAW))
    assert b["soffit_sqft"] == 120 and b["level_frieze_lf"] == 70
    assert b["sloped_frieze_lf"] == 30 and b["drip_edge_lf"] == 95
    assert b["total_trim_sqft"] == 40 and b["footprint_area_sqft"] == 900
    assert b["address"] == "123 Main St"
    assert b["opening_facade_assignments"] == [{"id": "W1", "facade": "brick"}]
    assert b["window_bottom_width_total_lf"] == 2 * 36 / 12.0
    # not-printed figures stay ABSENT (never a zero pretending to be read)
    b2 = bp_agg({"walls": [], "windows": [], "doors": []})
    for k in ("soffit_sqft", "level_frieze_lf", "drip_edge_lf", "address",
              "window_bottom_width_total_lf", "footprint_perimeter_ft"):
        assert k not in b2


def test_photo_detected_figures_land():
    p = photo_agg(dict(PHOTO_RAW))
    assert p["outside_corner_count"] == 2 and p["inside_corner_count"] == 1
    assert p["footprint_perimeter_ft"] == 32.0
    assert p["window_bottom_width_total_lf"] == 2 * 36 / 12.0
    # no corner-location machinery → counts stay ABSENT (pooled fallback,
    # never an invented zero)
    p2 = photo_agg({"walls": [], "openings": [], "openings_schedule": []})
    assert "outside_corner_count" not in p2 and "inside_corner_count" not in p2


def test_photo_corner_counts_activate_per_corner_rules():
    """Finding 7 (ruled): with counts landed, Q13 min-1-per-corner fires on
    the photo door — the pooled ÷16 the 261 Haugh finding retired."""
    from routes.hover import _osc_lp_pcs
    m = {"outside_corner_lf": 35.0, "outside_corner_count": 4}
    assert _osc_lp_pcs(m) == 4          # per-corner min-1, not ceil(35/16)=3


def test_hover_wbw_entry_corrected_10e():
    entry = HOVER_FIELD_REGISTER["window_bottom_width_total_lf"]
    assert entry["status"] == CONSUMED
    assert "FINISH TRIM" in str(entry["consumed_by"])
    assert "FICTION" in str(entry["consumed_by"])  # the wrong-aim is on the record


def test_registers_are_detection_only():
    """Rider 2 binds on all three doors: importing the registers changes no
    derivation — the register module carries no functions, only rulings."""
    import door_field_register as dfr
    fns = [n for n, o in vars(dfr).items() if callable(o)]
    assert fns == [], f"register module must stay declarative, found: {fns}"
