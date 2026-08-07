"""BLUEPRINT READ-BACK CARD pins (Howard authorized 2026-08-06 — first
build off demo-lock).

The card is DISPLAY-ONLY: `build_blueprint_readback` reads the run's raw
extraction and returns visibility flags. These pins hold:
1. THE ACCEPTANCE — a raw reproducing the ORIGINAL Boni read shows all
   three misses at a glance (garage gable invisible, phantom porch
   ceiling, corner walk failing/averaged).
2. READ-ONLY GUARANTEE — the builder never mutates the raw it reads, and
   the endpoint enrichment adds a key without touching the result.
3. A healthy read renders QUIET — no loud flags on the ruled geometry.
"""
import copy
import sys

sys.path.insert(0, "/app/backend")

from routes.ai_blueprint import build_blueprint_readback, _with_readback  # noqa: E402

BONI_WALLS = [
    {"label": "front", "width_ft": 58, "height_ft": 18},
    {"label": "back", "width_ft": 58, "height_ft": 18},
    {"label": "left", "width_ft": 39, "height_ft": 18, "gable_triangle_height_ft": 11.5},
    {"label": "right", "width_ft": 39, "height_ft": 18, "gable_triangle_height_ft": 11.5},
]


def _original_boni_read():
    """Reproduces the pre-correction Boni read state: no roof planes, a
    phantom porch ceiling with no plane, a corner walk that misses the
    wing (9 outside vs installed 11 breaks the out−in=4 invariant)."""
    return {
        "walls": [dict(w) for w in BONI_WALLS],
        "doors": [{"id": "G1", "type_hint": "garage"}, {"id": "G2", "type_hint": "garage"}],
        "roof_planes": None,
        "roof_pitch": "7/12",
        "eaves_lf": 116, "rakes_lf": 82,
        "outside_corner_count": 9, "inside_corner_count": 2,
        "outside_corner_lf": 108, "inside_corner_lf": 36,
        "avg_wall_height_ft": 12,
        "porch_ceiling_sqft": 150,  # the phantom — a ceiling with no plane
        "footprint_area_sqft": 2351,
        "notes": "",
    }


def test_original_boni_read_shows_all_three_misses():
    rb = build_blueprint_readback(_original_boni_read())
    # MISS 1 — garage gable invisible: no planes at all → LOUD + banner
    assert rb["no_planes"] is True
    assert rb["garage_banner"] is True
    assert any(f["code"] == "no_planes" and f["level"] == "loud" for f in rb["rail"])
    # MISS 2 — phantom porch: a ceiling figure with NO porch plane
    assert rb["porch"]["status"] == "phantom_ceiling"
    assert rb["porch"]["ceiling_sqft"] == 150
    # MISS 3 — corners: 9 − 2 ≠ 4 → invariant FAILS on the card
    assert rb["corners"]["invariant_ok"] is False
    # and the wing check names the projecting garage the walk missed
    assert rb["wing_check"]["flag"] is True


def test_gable_blind_garage_plane_flags_loudly():
    """The e162c54a shape: garage plane present but rake 0 / no gable
    ends — exactly how the garage gable went invisible on a plane-carrying
    read."""
    raw = _original_boni_read()
    raw["roof_planes"] = [
        {"label": "main", "eave_lf": 116, "rake_lf": 82, "gable_ends": 2,
         "is_porch": False, "porch_ceiling_sqft": 0},
        {"label": "garage", "eave_lf": 50, "rake_lf": 0, "gable_ends": 0,
         "is_porch": False, "porch_ceiling_sqft": 0},
    ]
    rb = build_blueprint_readback(raw)
    g = [p for p in rb["planes"] if p["label"] == "garage"][0]
    assert g["gable_blind"] is True
    assert rb["garage_banner"] is True  # gable-blind garage still banners
    m = [p for p in rb["planes"] if p["label"] == "main"][0]
    assert m["gable_blind"] is False


def test_averaged_corner_basis_is_named():
    """count × avg height (the 261 Haugh smell) gets the AVERAGED chip;
    a per-corner sum gets the per-corner chip."""
    raw = _original_boni_read()
    raw.update({"outside_corner_count": 6, "inside_corner_count": 2,
                "outside_corner_lf": 108, "avg_wall_height_ft": 18})
    rb = build_blueprint_readback(raw)
    assert rb["corners"]["basis"] == "averaged"
    assert rb["corners"]["invariant_ok"] is True
    raw["outside_corner_lf"] = 126  # per-corner summed (main tall + garage short)
    rb2 = build_blueprint_readback(raw)
    assert rb2["corners"]["basis"] == "per_corner"


def test_healthy_ruled_read_is_quiet():
    raw = _original_boni_read()
    raw.update({
        "roof_planes": [
            {"label": "main", "eave_lf": 116, "rake_lf": 82, "gable_ends": 2,
             "is_porch": False, "porch_ceiling_sqft": 0},
            {"label": "garage", "eave_lf": 36, "rake_lf": 36, "gable_ends": 2,
             "is_porch": False, "porch_ceiling_sqft": 0},
            {"label": "porch", "eave_lf": 15, "rake_lf": 0, "gable_ends": 0,
             "is_porch": True, "porch_ceiling_sqft": 99},
        ],
        "outside_corner_count": 8, "inside_corner_count": 4,
        "outside_corner_lf": 126, "porch_ceiling_sqft": 99,
        "footprint_area_sqft": 2262,
    })
    rb = build_blueprint_readback(raw)
    assert rb["garage_banner"] is False
    assert not any(p["gable_blind"] for p in rb["planes"] if not p["is_porch"])
    assert rb["corners"]["invariant_ok"] is True
    assert rb["corners"]["basis"] == "per_corner"
    assert rb["porch"]["status"] == "plane_read"
    assert rb["wing_check"]["flag"] is False
    assert rb["plane_totals"] == {"eaves_lf": 167.0, "rakes_lf": 118.0, "gable_ends": 4}
    assert not any(f["level"] == "loud" for f in rb["rail"])


def test_readback_is_pure_and_read_only():
    """READ-ONLY GUARANTEE: the builder mutates nothing it reads, and the
    endpoint enrichment only ADDS a sibling key."""
    raw = _original_boni_read()
    before = copy.deepcopy(raw)
    build_blueprint_readback(raw)
    assert raw == before, "readback must never mutate the raw it reads"
    assert build_blueprint_readback(None) is None
    assert build_blueprint_readback({}) is None
    result = {"raw_ai": raw, "measurements": {"eaves_lf": 116}, "lines": [1, 2]}
    enriched = _with_readback(result)
    assert enriched["measurements"] == result["measurements"]
    assert enriched["lines"] == result["lines"]
    assert enriched["raw_ai"] == before
    assert "readback" in enriched
    bare = {"measurements": {}}
    assert _with_readback(bare) is bare, "no raw_ai → response untouched"


def test_roof_pass_provenance_rides_the_rail():
    raw = _original_boni_read()
    raw["_roof_pass"] = {"accepted": {"garage_plane_appended": {}, "corners": {}}}
    rb = build_blueprint_readback(raw)
    merges = [f["text"] for f in rb["rail"] if f["code"] == "roof_pass_merge"]
    assert merges == ["corners", "garage_plane_appended"]


def test_readback_surfaces_corner_heights_and_gutter_runs():
    """Ruled 2026-08-07 (open item 4): the card grades a read BEFORE it
    is applied — per-corner heights and the gutter run inventory must be
    on it when the read carries them, and their absence must be named."""
    raw = _original_boni_read()
    raw["outside_corner_heights_ft"] = [9, 9, None, 14]
    raw["gutter_runs"] = [{"label": "front", "lf": 40},
                          {"label": "back", "lf": 40},
                          {"label": "porch", "lf": 12}]
    rb = build_blueprint_readback(raw)
    assert rb["corners"]["heights_ft"] == [9.0, 9.0, None, 14.0]
    assert rb["corners"]["undimensioned"] == 1
    assert rb["gutter_runs"] == [{"label": "front", "lf": 40.0},
                                 {"label": "back", "lf": 40.0},
                                 {"label": "porch", "lf": 12.0}]
    assert rb["gutter_runs_total"] == 92.0
    # a read WITHOUT them names the absence (old runs stay honest)
    rb0 = build_blueprint_readback(_original_boni_read())
    assert rb0["corners"]["heights_ft"] is None
    assert rb0["gutter_runs"] is None


def test_readback_card_renders_heights_and_runs():
    from pathlib import Path as _P
    card = (_P(__file__).resolve().parents[2] / "frontend" / "src"
            / "components" / "estimate" / "BlueprintReadBackCard.jsx").read_text()
    for tid in ("bp-rb-corner-heights", "bp-rb-heights-undim",
                "bp-rb-gutter-run-list", "bp-rb-gutter-runs-none"):
        assert tid in card, f"read-back card lost {tid}"
    dicts = (_P(__file__).resolve().parents[2] / "frontend" / "src"
             / "lib" / "dictionaries.js").read_text()
    for key in ('"bp.rb.gutterRuns"', '"bp.rb.heights.undim"'):
        assert dicts.count(key) == 2, f"{key} must exist in en AND es"
