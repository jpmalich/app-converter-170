"""SEND-137 PINS — THE GABLE RULING (Howard, 2026-08-27).

  Measure the gable for what it is. Do not use 0.70.
  Area = ½ × width × rise when width and rise exist on that face.
  That is the gable wall.
  0.70 × width × rise is retired. It is not a fallback, not a waste
  factor, not a default, not a "close enough" on an untraced gable.
  AN UNTRACED GABLE HAS NO AREA. It refuses until the triangle is
  measured or Howard draws it.
  The panel (recomputeFromWalls) and the backend must print the same
  number. After this send both use ½, or both refuse.

NOTHING HERE IS TUNED toward 8.4, 370, 172.8, 367.5, 621.1 or any job's
existing gable total: every arithmetic pin uses invented round numbers
(30 × 10 walls, rise 8, 40 ft fronts).
"""
import pathlib
import re
import sys

sys.path.insert(0, "/app/backend")

import pytest  # noqa: E402

from measure_staging import (  # noqa: E402
    GABLE_BASES, GABLE_BASIS_MEASURED_TRIANGLE,
    GABLE_BASIS_RETIRED_FIELD_FACTOR, GABLE_TRIANGLE_FACTOR,
    gable_claim_without_rise, walk_walls)

PANEL = pathlib.Path(
    "/app/frontend/src/components/estimate/AIMeasureButton.jsx")
STAGING = pathlib.Path("/app/backend/measure_staging.py")
PROFILE = pathlib.Path("/app/backend/profile_callouts.py")


def _wall(label="front", width=30.0, height=10.0, rise=8.0, **kw):
    w = {"label": label, "width_ft": width, "height_ft": height,
         "gable_triangle_height_ft": rise,
         "_source_photo_indices": [0],
         "width_ft_source": "direct_ref",
         "height_ft_source": "direct_single_reading"}
    w.update(kw)
    return w


# ---------------------------------------------------------------------------
# 1. THE FORMULA — ½ × width × rise, and nothing else
# ---------------------------------------------------------------------------
def test_the_factor_is_one_half_and_the_word_0_70_is_gone_from_it():
    assert GABLE_TRIANGLE_FACTOR == 0.5
    src = STAGING.read_text()
    assert "GABLE_FACTOR = 0.70" not in src
    assert "GABLE_FACTOR" not in src.replace("GABLE_TRIANGLE_FACTOR", "")


def test_a_measured_gable_is_the_triangle():
    out = walk_walls([_wall()])
    assert out["gable_sqft"] == pytest.approx(0.5 * 30.0 * 8.0)   # 120.0
    row = out["detail"][0]
    assert row["gable_basis"] == GABLE_BASIS_MEASURED_TRIANGLE
    assert row["gable_refusal"] is None


def test_the_convention_label_names_the_triangle_and_the_retirement():
    conv = walk_walls([_wall()])["detail"][0]["gable_convention"]
    assert "½ × width × rise" in conv
    assert "RETIRED" in conv


def test_no_surface_multiplies_a_gable_by_zero_point_seven():
    """The factor cannot come back in through a second copy."""
    for p in (STAGING, PROFILE,
              pathlib.Path("/app/backend/routes/ai_measure.py"),
              pathlib.Path("/app/backend/routes/ai_blueprint.py"),
              pathlib.Path("/app/backend/routes/hover.py"),
              pathlib.Path("/app/backend/lp_package.py")):
        src = p.read_text()
        for bad in ("0.7 * width", "0.70 * width", "0.7 * g_width",
                    "0.70 * g_width", "0.7 * float(width",
                    "GABLE_BOOK_FACTOR = ", "GABLE_BASIS_FIELD_FACTOR ="):
            assert bad not in src, f"{p.name}: {bad!r}"


# ---------------------------------------------------------------------------
# 2. AN UNTRACED GABLE HAS NO AREA — it refuses, it never takes a factor
# ---------------------------------------------------------------------------
def test_a_null_rise_refuses_by_name_and_writes_no_area():
    """A rise asked for and returned NULL is 'not visible' — which is not
    the 0 that means eave-only. No area, and the gap is named."""
    w = _wall(rise=None)
    out = walk_walls([w])
    assert out["gable_sqft"] == 0.0
    row = out["detail"][0]
    assert row["gable_sqft"] is None            # refusal, never a 0 figure
    assert row["gable_basis"] is None
    reason = row["gable_refusal"]
    assert "REFUSED" in reason and "null" in reason
    named = [f for f in out["faces_not_derivable"]
             if f.get("surface") == "gable"]
    assert named and named[0]["label"] == "front"


def test_an_eave_only_wall_stays_silent_and_a_hip_house_earns_no_refusal():
    """A 0 is an ANSWER (this wall ends in an eave) and an absent field
    claims no gable. Neither is a refusal — the rule adds no noise."""
    eave_only = walk_walls([_wall(rise=0)])
    assert eave_only["gable_sqft"] == 0.0
    assert eave_only["detail"][0]["gable_refusal"] is None
    assert not [f for f in eave_only["faces_not_derivable"]
                if f.get("surface") == "gable"]
    bare = {"label": "front", "width_ft": 30.0, "height_ft": 10.0}
    out = walk_walls([bare])
    assert out["detail"][0]["gable_refusal"] is None
    assert out["faces_not_derivable"] == []


def test_an_upstream_rise_refusal_carries_through():
    out = walk_walls([_wall(rise=0, _gable_rise_refusal="no plate datum")])
    assert out["detail"][0]["gable_sqft"] is None
    assert "no plate datum" in out["detail"][0]["gable_refusal"]


def test_the_claim_helper_reads_evidence_only():
    assert gable_claim_without_rise({"gable_triangle_height_ft": None})
    assert gable_claim_without_rise({"gable_triangle_height_ft": 0}) is None
    assert gable_claim_without_rise({}) is None
    # a profile callout is NOT a rise claim: a hip-zeroed wall keeps its
    # callout and must not start refusing.
    assert gable_claim_without_rise(
        {"gable_triangle_height_ft": 0,
         "gable_profile_callout": "shake"}) is None


def test_a_width_refusal_still_refuses_the_gable():
    out = walk_walls([_wall(width_ft=None)])
    assert out["detail"][0]["gable_sqft"] is None
    assert "width not read" in out["detail"][0]["gable_refusal"]


# ---------------------------------------------------------------------------
# 3. THE PANEL AND THE STORED FIGURE PRINT THE SAME NUMBER
# ---------------------------------------------------------------------------
def test_the_panels_coefficient_is_read_from_the_file_and_equals_the_backends():
    """The live parity pin. The panel's gable line is READ OUT OF THE
    SOURCE and its coefficient compared to the backend constant — the ~40%
    disagreement cannot come back silently."""
    src = PANEL.read_text()
    m = re.search(r"gableSqft \+= ([0-9.]+) \* width \* gableH", src)
    assert m, "the panel's gable formula moved — re-read this pin"
    assert float(m.group(1)) == GABLE_TRIANGLE_FACTOR
    assert "0.7 * width" not in src and "0.70 * width" not in src


def test_the_panel_and_the_walk_agree_on_an_invented_house():
    """Same walls through both surfaces: the panel's arithmetic, evaluated
    exactly as the file writes it, equals the backend's stored figure."""
    walls = [_wall("front", 40.0, 10.0, 8.0), _wall("back", 40.0, 10.0, 8.0),
             _wall("left", 20.0, 10.0, 0), _wall("right", 20.0, 10.0, 0)]
    backend = walk_walls([dict(w) for w in walls])
    coeff = float(re.search(r"gableSqft \+= ([0-9.]+) \* width \* gableH",
                            PANEL.read_text()).group(1))
    panel = sum(coeff * float(w["width_ft"])
                * float(w["gable_triangle_height_ft"] or 0)
                for w in walls
                if (w["gable_triangle_height_ft"] or 0) > 0)
    assert backend["gable_sqft"] == pytest.approx(panel)
    assert backend["gable_sqft"] == pytest.approx(2 * 0.5 * 40.0 * 8.0)  # 320


def test_the_per_profile_split_cannot_disagree_with_the_headline():
    """profile_callouts was a THIRD copy of the same number at 0.7 — it
    now measures the same triangle, so the split and the headline agree."""
    from profile_callouts import breakdown_walls_by_profile
    walls = [_wall("front", 30.0, 10.0, 8.0)]
    out = breakdown_walls_by_profile([dict(w) for w in walls])
    total = sum(out["per_profile_sqft"].values())
    walk = walk_walls([dict(w) for w in walls])
    assert total == pytest.approx(walk["siding_sqft"] + walk["gable_sqft"])


def test_the_per_profile_split_names_the_same_untraced_refusal():
    from profile_callouts import breakdown_walls_by_profile
    out = breakdown_walls_by_profile([_wall(rise=None)])
    gab = [f for f in out["faces_not_derivable"]
           if f.get("surface") == "gable"]
    assert gab and "REFUSED" in gab[0]["reason"]


# ---------------------------------------------------------------------------
# 4. THE STORED PAST IS NAMED, NEVER SILENTLY REPRINTED
# ---------------------------------------------------------------------------
def test_a_stored_retired_basis_is_recognised_and_named_stale():
    from measure_staging import gable_basis_label
    assert GABLE_BASIS_RETIRED_FIELD_FACTOR not in GABLE_BASES
    lab = gable_basis_label(GABLE_BASIS_RETIRED_FIELD_FACTOR)
    assert "STALE" in lab and "re-derived" in lab


def test_both_ai_doors_walk_the_same_shared_math():
    """No door may grow its own gable arithmetic again."""
    import inspect
    from routes.ai_blueprint import _aggregate_to_hover_shape as bp
    from routes.ai_measure import _aggregate_to_hover_shape as photo
    for fn in (photo, bp):
        src = inspect.getsource(fn)
        assert "walk_walls" in src
        assert "0.5 *" not in src and "0.7 *" not in src
