"""SEND-74 pins — GABLE BASIS is a strict BINARY (Howard, verbatim):

  TRACED      → the drawn triangle's true area, NO field factor.
  NOT TRACED  → area × 0.70 field factor (safety margin for an
                approximate gable measurement).

Every gable quantity carries EXACTLY ONE of the two bases — never
both, never neither, never a third — and the label rides the quantity
to the sheet, the read-back card and the money line. The 0.70 stays a
FIELD fudge factor for un-traced gables; a traced gable is exact. Two
gables on one house priced on different bases must be tellable apart.
"""
import sys

sys.path.insert(0, "/app/backend")
from measure_staging import (  # noqa: E402
    GABLE_BASES, GABLE_BASIS_FIELD_FACTOR, GABLE_BASIS_TRACED,
    GABLE_FACTOR, gable_basis_label, walk_walls)

import pytest  # noqa: E402


def _wall(label="left", width=30.0, height=9.0, rise=5.0):
    return {"label": label, "width_ft": width, "height_ft": height,
            "gable_ends": 1, "gable_triangle_height_ft": rise}


def test_the_basis_vocabulary_is_exactly_two_values():
    assert GABLE_BASES == {GABLE_BASIS_TRACED, GABLE_BASIS_FIELD_FACTOR}
    with pytest.raises(ValueError):
        gable_basis_label("pure_geometry")     # no third basis exists


def test_the_mandated_sentences_verbatim():
    assert gable_basis_label(GABLE_BASIS_FIELD_FACTOR) == (
        "gable not traced — 0.70 field factor applied (safety margin "
        "for an approximate gable measurement)")
    assert gable_basis_label(GABLE_BASIS_TRACED, 129.98) == (
        "gable traced from the drawing — 129.98 ft², no field factor")
    # traced with no evidence scale still says NO FIELD FACTOR
    assert "no field factor" in gable_basis_label(GABLE_BASIS_TRACED)


def test_a_derived_gable_carries_the_field_factor_basis_and_the_math():
    """The derived path never traces: its gable quantity is
    0.70 × width × rise and says so."""
    r = walk_walls([_wall()])
    row = next(d for d in r["detail"] if d["label"] == "left")
    assert row["gable_sqft"] == pytest.approx(GABLE_FACTOR * 30.0 * 5.0)
    assert row["gable_basis"] == GABLE_BASIS_FIELD_FACTOR
    assert row["gable_basis_label"] == gable_basis_label(
        GABLE_BASIS_FIELD_FACTOR)


def test_a_gable_quantity_carries_exactly_one_basis_never_both():
    r = walk_walls([_wall()])
    row = next(d for d in r["detail"] if d["label"] == "left")
    assert row["gable_basis"] in GABLE_BASES
    lab = row["gable_basis_label"]
    assert ("no field factor" in lab) != ("0.70 field factor" in lab)


def test_a_refusing_gable_is_not_a_quantity_and_carries_no_basis():
    w = _wall()
    w["width_ft"] = None                      # width killed → refusal
    r = walk_walls([w])
    row = next(d for d in r["detail"] if d["label"] == "left")
    assert row["gable_sqft"] is None
    assert row["gable_basis"] is None
    assert row["gable_basis_label"] is None
    assert row["gable_refusal"]


def test_the_money_line_says_the_field_factor_basis():
    """When walk gables contribute to the siding quantity, every siding
    SQ money line carries the mandated sentence."""
    from routes.hover import _build_lines
    m = {"siding_sqft": 1500.0, "siding_with_openings_sqft": 1500.0,
         "_wall_walk_detail": [
             {"label": "left", "gable_sqft": 105.0,
              "gable_basis": GABLE_BASIS_FIELD_FACTOR}]}
    lines = _build_lines(m)
    sq = [l for l in lines if l.get("unit") == "SQ"
          and l.get("section") in ("Vinyl Siding", "Ascend Cladding",
                                   "LP Smart Siding")]
    assert sq, "no siding SQ lines emitted"
    for l in sq:
        assert ("gable not traced — 0.70 field factor applied"
                in (l.get("note") or "")), l.get("name")


def test_the_money_line_stays_silent_when_no_gable_contributed():
    from routes.hover import _build_lines
    m = {"siding_sqft": 1500.0, "siding_with_openings_sqft": 1500.0,
         "_wall_walk_detail": [{"label": "left", "gable_sqft": None}]}
    for l in _build_lines(m):
        assert "0.70 field factor" not in (l.get("note") or "")


def test_a_bound_gable_zone_names_no_field_factor_on_the_money_line():
    """A drawn/confirmed gable zone binds at its TRUE area — the money
    line says so (the other half of the binary)."""
    from routes.pdf_overlay import apply_overlay_to_takeoff
    lines = [{"section": "Vinyl Siding", "name": "siding", "unit": "SQ",
              "qty": 20.0, "mat": 100.0, "lab": 0.0}]
    polys = [{"material_class": "siding", "face_id": "gable:left",
              "provenance": "human", "sqft": 130.0,
              "derived_baseline_qty": 20.0,
              "surface_derived_sqft": 1.05, "surface_refusal": None}]
    out = apply_overlay_to_takeoff(lines, polys)
    note = out[0].get("note") or ""
    assert "gable zone bound at its drawn area — no field factor" in note
    assert "0.70" not in note


def test_traced_proposals_carry_the_traced_basis_structurally():
    """The propose path stamps gable_basis on every gable proposal:
    gable_outline → TRACED with the mandated sentence leading the
    notice; gable_rectangle → the derived figure alongside carries the
    FIELD FACTOR basis (a starting shape is not a quantity)."""
    import pathlib
    src = pathlib.Path("/app/backend/routes/pdf_overlay.py").read_text()
    assert '"gable_basis": g_basis_kind' in src
    assert '"gable_basis_label": g_basis_lab' in src
    assert "gable_basis_label(GABLE_BASIS_TRACED" in src
    assert "gable_basis_label(GABLE_BASIS_FIELD_FACTOR)" in src


def test_the_sheet_components_carry_the_basis_label():
    import pathlib
    src = pathlib.Path(
        "/app/backend/routes/blueprint_elevation.py").read_text()
    # both gable components (primary + wing) say the basis
    assert src.count('"gable_basis": GABLE_BASIS_FIELD_FACTOR') == 2
