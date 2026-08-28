"""SEND-141 PINS — A REFUSED ROW SHOWS NO NUMBER (Howard ruled 2026-08-27).

  If the mark is refused, the quantity cell is blank or an em dash.
  Never 0, never 0.0, never 0 ft².
  The receipt line stays. The reason stays.
  A measured gable still prints ½ × width × rise.
  The 0 you see today is the flat polygon's pixel area. It is not a
  takeoff. Do not promote it. Do not write it to the estimate.

Scope: the PhotoTakeoffEditor mark list — gables and dormer cheeks first,
and the same rule applied to a refused siding / non-siding / opening row.
No new coach was added.
"""
import pathlib
import re
import sys

sys.path.insert(0, "/app/backend")

import pytest  # noqa: E402

from routes.photo_takeoff import (_dormer_figure, _gable_figure,  # noqa: E402
                                  _quantities)

ROUTE = pathlib.Path("/app/backend/routes/photo_takeoff.py")

# SEND-142 NAMED PIN UPDATE: the rail split moved this text into
# ./phototakeoff/*; the pin reads the WHOLE surface, same question.
from phototakeoff_surface import editor_surface  # noqa: E402

EDITOR = pathlib.Path(
    "/app/frontend/src/components/estimate/PhotoTakeoffEditor.jsx")
SRC = editor_surface()

IPP = 12.0
TRI = [{"x": 0, "y": 8}, {"x": 15, "y": 0}, {"x": 30, "y": 8}]
FLAT = [{"x": 0, "y": 8}, {"x": 15, "y": 8}, {"x": 30, "y": 8}]
QUAD = [{"x": 0, "y": 10}, {"x": 6, "y": 10}, {"x": 6, "y": 0}, {"x": 0, "y": 0}]


def _g(pts, **kw):
    return {"id": "g1", "kind": "gable", "status": "confirmed",
            "points": pts, "label": "front gable", **kw}


def _d(pts, **kw):
    return {"id": "d1", "kind": "dormer", "status": "confirmed",
            "points": pts, "label": "left dormer", **kw}


def _scale():
    return {"span_px": 100.0, "anchor": {"inches": 1200.0}}


# ---------------------------------------------------------------------------
# 1. ONE PLACE DECIDES WHAT A QUANTITY CELL MAY SAY
# ---------------------------------------------------------------------------
def test_the_cell_is_decided_in_one_helper_used_by_both_surfaces():
    """The mark row and the tag on the shape print the SAME number, so
    they must ask the SAME question — otherwise the 0 comes back on one
    of them."""
    assert "const qtyCell = (m, a) =>" in SRC
    assert SRC.count("qtyCell(m, a)") == 2          # the row and the tag
    # nothing prints a bare area figure any more
    assert "`${a} ft²`}" not in SRC.replace('return `${a} ft²`;', "")


def test_the_helper_refuses_zero_by_construction():
    body = SRC.split("const qtyCell = (m, a) =>")[1].split("};")[0]
    assert 'm.status === "refused"' in body
    assert "figureRefused(m.id)" in body
    assert "!(a > 0)" in body                       # 0 and 0.0 both fail
    assert 'return "—"' in body
    # the number is the LAST thing it can say, never the first
    assert body.index('return "—"') < body.index("${a} ft²")


def test_a_face_refusal_blanks_the_cell_and_a_cheek_refusal_does_not():
    """SEND-140 kept the drawn dormer FACE figure while its cheeks
    refused. That must survive: only a FACE-level refusal blanks."""
    body = SRC.split("const figureRefused = (id) =>")[1].split("};")[0]
    assert "row.refusal" in body
    assert "cheek_refusal" not in body


def test_no_ft2_figure_anywhere_prints_a_zero():
    """Every ft² figure on the panels goes through ft2(), which answers an
    em dash when there is no figure."""
    assert "const ft2 = (v) => (v > 0 ? `${v.toFixed(1)} ft²` : \"—\");" in SRC
    for leaked in ("grossAreaFt.toFixed(1)} ft²",
                   "Number(m.depth_ft)).toFixed(1)} ft²"):
        assert leaked not in SRC, leaked


def test_the_receipt_and_the_reason_stay_on_the_row():
    assert "photo-takeoff-receipt-" in SRC
    assert "{m.refused_reason}" in SRC


def test_no_new_coach_was_added():
    assert set(re.findall(r"[a-z_]*receipts?", SRC)) == {
        "receipt", "gable_receipts", "dormer_receipts"}


# ---------------------------------------------------------------------------
# 2. THE SERVER NEVER OFFERS A ZERO TO PRINT IN THE FIRST PLACE
# ---------------------------------------------------------------------------
def test_a_refused_gable_figure_is_none_not_zero():
    f = _gable_figure(_g(FLAT), [], IPP)
    assert f["sqft"] is None and f["gross_sqft"] is None
    assert f["refusal"] and f["receipt"]


def test_a_refused_gable_lane_is_none_not_zero():
    q = _quantities([_g(FLAT)], _scale())
    assert q["gable_sqft"] is None
    assert q["gable_rows"][0]["sqft"] is None
    assert q["gable_rows"][0]["refusal"]


def test_a_cheek_with_no_depth_is_none_while_its_face_stands():
    f = _dormer_figure(_d(QUAD), [], IPP)
    assert f["cheek_sqft"] is None
    assert f["sqft"] == pytest.approx(60.0)         # the face was drawn
    assert f["refusal"] is None                     # face did not refuse


def test_a_measured_gable_still_prints_the_half_number():
    q = _quantities([_g(TRI)], _scale())
    assert q["gable_sqft"] == pytest.approx(0.5 * 30.0 * 8.0)
    assert q["gable_rows"][0]["refusal"] is None


# ---------------------------------------------------------------------------
# 3. NOTHING WRITES A ZERO ONTO THE ESTIMATE FROM A REFUSAL
# ---------------------------------------------------------------------------
def test_the_lane_a_refusal_feeds_is_none_so_apply_has_no_zero_to_write():
    """Apply only ever sees what the lane produced. A refusal produces
    None, so there is no 0 in the estimate's future."""
    q = _quantities([_g(FLAT), _d(QUAD)], _scale())
    assert q["gable_sqft"] is None
    assert q["dormer_cheek_sqft"] is None
    assert q["siding_sqft"] is None
    # the drawn dormer FACE is a real measurement and still stands
    assert q["dormer_face_sqft"] == pytest.approx(60.0)


def test_apply_totals_a_lane_only_when_something_was_measured():
    """Structural: the totals loop accumulates ONLY on `is not None` and
    emits the key as None unless a live figure arrived — a lane cannot be
    talked into a 0 by a refusal."""
    src = ROUTE.read_text()
    loop = src.split("async def apply_photo_takeoff")[1]
    for guard in ('if qty.get("gable_sqft") is not None:',
                  'if qty.get("dormer_cheek_sqft") is not None:'):
        assert guard in loop, guard
    for emit in ('"photo_gable_sqft": round(tot_gable, 2) if live_gable else None',
                 '"photo_dormer_cheek_sqft": (round(tot_dormer_cheek, 2)'):
        assert emit in loop, emit


def test_the_route_never_defaults_a_lane_to_zero():
    src = pathlib.Path("/app/backend/routes/photo_takeoff.py").read_text()
    for bad in ('"photo_gable_sqft": 0', '"gable_sqft": 0.0',
                'gable_sqft") or 0', 'or 0.0,'):
        assert bad not in src, bad
