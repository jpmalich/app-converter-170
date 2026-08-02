"""STEP 6 SEALS — Three Doors build (Howard ruled 2026-08-01).
FOUR PHOTO FILL-IN BOXES, photo door ONLY: soffit_sqft, drip_edge_lf,
total_trim_sqft, frieze presence-toggle. A box only FILLS A HOLE — never
overrides a measured value; inert on hover and blueprint blobs (finding 6:
never ask the contractor to re-type a number the source gave). Frieze LF
derives from the measured eave/rake runs — no number re-typing. ONE copy
(measure_staging.fold_photo_fillins) serves both fold points."""
import inspect

import pytest
from pydantic import ValidationError

from measure_staging import fold_photo_fillins
from models import EstimateIn


PHOTO = {"_source": "photo", "siding_sqft": 1400.0,
         "eaves_lf": 120.0, "rakes_lf": 60.0}
EST = {"photo_soffit_sqft": 250.0, "photo_drip_edge_lf": 180.0,
       "photo_total_trim_sqft": 90.0, "photo_frieze_present": True}


def test_fillins_land_on_photo_source():
    out = fold_photo_fillins(dict(PHOTO), dict(EST))
    assert out["soffit_sqft"] == 250.0
    assert out["drip_edge_lf"] == 180.0
    assert out["total_trim_sqft"] == 90.0
    assert "fill-in" in out["_soffit_sqft_basis"]
    assert "fill-in" in out["_drip_edge_lf_basis"]
    assert "fill-in" in out["_total_trim_sqft_basis"]


def test_frieze_toggle_derives_from_measured_runs():
    """Presence toggle only — level = eaves, sloped = rakes. The est dict
    carries NO frieze LF anywhere: the engine derives it (no re-typing)."""
    assert not any("frieze_lf" in k for k in EST)
    out = fold_photo_fillins(dict(PHOTO), dict(EST))
    assert out["level_frieze_lf"] == 120.0
    assert out["sloped_frieze_lf"] == 60.0
    assert "eaves 120" in out["_frieze_basis"]
    assert "rakes 60" in out["_frieze_basis"]


def test_photo_door_only_inert_on_hover_and_blueprint():
    """The trap named on acceptance: a box that reaches a hover or
    blueprint derivation is the silent-key class all over again."""
    hover_blob = {"siding_sqft": 1400.0, "eaves_lf": 120.0,
                  "soffit_sqft": 300.0}  # hover blobs carry no _source
    assert fold_photo_fillins(dict(hover_blob), dict(EST)) == hover_blob
    bp_blob = {**hover_blob, "_source": "blueprint"}
    assert fold_photo_fillins(dict(bp_blob), dict(EST)) == bp_blob


def test_never_overrides_a_measured_value():
    """Fills a hole ONLY — a measured value outranks the box."""
    measured = {**PHOTO, "soffit_sqft": 310.0, "level_frieze_lf": 88.0}
    out = fold_photo_fillins(dict(measured), dict(EST))
    assert out["soffit_sqft"] == 310.0
    assert "_soffit_sqft_basis" not in out
    # measured frieze present → toggle is inert on BOTH segments
    assert out["level_frieze_lf"] == 88.0
    assert "sloped_frieze_lf" not in out
    assert "_frieze_basis" not in out
    # the other two holes still fill
    assert out["drip_edge_lf"] == 180.0
    assert out["total_trim_sqft"] == 90.0


def test_empty_zero_or_absent_boxes_are_inert():
    out = fold_photo_fillins(dict(PHOTO), {})
    assert "soffit_sqft" not in out and "drip_edge_lf" not in out
    assert "level_frieze_lf" not in out
    out2 = fold_photo_fillins(dict(PHOTO), {
        "photo_soffit_sqft": 0, "photo_drip_edge_lf": None,
        "photo_total_trim_sqft": "", "photo_frieze_present": False})
    assert "soffit_sqft" not in out2 and "total_trim_sqft" not in out2
    assert "level_frieze_lf" not in out2


def test_fold_is_idempotent():
    once = fold_photo_fillins(dict(PHOTO), dict(EST))
    twice = fold_photo_fillins(dict(once), dict(EST))
    assert once == twice


def test_put_cannot_silent_strip_the_boxes():
    """F2 class pin — the four fields are DECLARED on EstimateIn so a PUT
    round-trip preserves them (the buildPayload guard is the sibling)."""
    e = EstimateIn(photo_soffit_sqft=250, photo_drip_edge_lf=180,
                   photo_total_trim_sqft=90, photo_frieze_present=True)
    d = e.model_dump(exclude_none=True)
    assert d["photo_soffit_sqft"] == 250.0
    assert d["photo_drip_edge_lf"] == 180.0
    assert d["photo_total_trim_sqft"] == 90.0
    assert d["photo_frieze_present"] is True
    # Optional-None default: a partial PUT never clobbers stored values.
    assert "photo_soffit_sqft" not in EstimateIn().model_dump(exclude_none=True)


def test_negative_fillin_rejected():
    with pytest.raises(ValidationError):
        EstimateIn(photo_soffit_sqft=-1)
    with pytest.raises(ValidationError):
        EstimateIn(photo_drip_edge_lf=-0.5)


def test_one_copy_both_fold_points():
    """No-fourth-copy doctrine: both fold points call the ONE shared
    function; neither re-implements the fill-in math."""
    from routes.hover import rebuild_lp_tab_lines
    from routes.lp_package_routes import _apply_contractor_waste
    assert "fold_photo_fillins" in inspect.getsource(rebuild_lp_tab_lines)
    assert "fold_photo_fillins" in inspect.getsource(_apply_contractor_waste)


def test_engine_consumes_the_filled_soffit():
    """The filled hole reaches a real derivation: vinyl soffit pieces are
    MEASURED total ÷ 10 when soffit_sqft lands (register: Q14a measured
    soffit governs). Without the box the same photo blob derives soffit
    from eaves/rakes × overhang instead."""
    from routes.hover import _build_lines
    blob = {**PHOTO, "overhang_in": 12.0}
    without = _build_lines(fold_photo_fillins(dict(blob), {}))
    with_box = _build_lines(fold_photo_fillins(dict(blob), dict(EST)))

    def _soffit_qty(lines):
        return next(float(l["qty"]) for l in lines
                    if l.get("tab") == "vinyl"
                    and str(l.get("name") or "").lower().startswith("soffit & fascia"))
    assert _soffit_qty(without) == 18   # eaves/rakes × overhang fallback
    assert _soffit_qty(with_box) == 25  # MEASURED 250 ft² ÷ 10 ft²/pc governs


# ── Step-6 minor fix-its (ruled 10a + 10c, 2026-08-01) ───────────────────

def test_photo_eaves_recompute_on_gabled_house():
    """Fix-it 10a: the blueprint door's defensive eaves rule extends to
    photo through the ONE shared rule — models return the full floor-plan
    perimeter as eaves; on a gabled house gutters run the NON-gable walls
    only."""
    from routes.ai_measure import _aggregate_to_hover_shape as photo_agg
    m = photo_agg({"walls": [
        {"label": "front", "width_ft": 40, "height_ft": 9,
         "gable_triangle_height_ft": 6},          # gable end — no gutter
        {"label": "back", "width_ft": 40, "height_ft": 9},
        {"label": "left", "width_ft": 25, "height_ft": 9},
    ], "openings": [], "eaves_lf": 130})           # raw = full perimeter
    assert m["eaves_lf"] == 65                     # non-gable widths only


def test_photo_opening_basis_unified_to_schedule():
    """Fix-it 10c: opening ft² and counts read the SAME basis (the
    reconciled schedule) — the deduped list serves legacy sessions only."""
    from routes.ai_measure import _aggregate_to_hover_shape as photo_agg
    sched = [{"type": "window", "count": 3, "width_in": 36, "height_in": 54}]
    m = photo_agg({"walls": [], "openings": [
        {"type": "window", "width_in": 36, "height_in": 54}],  # deduped: 1
        "openings_schedule": sched})
    assert m["window_count"] == 3
    assert m["opening_sqft"] == 3 * (36 * 54) / 144.0  # schedule ft², not dedupe ft²
