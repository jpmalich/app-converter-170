"""SEND-96 register (Howard, 2026-08-14, verbatim core):

THREE RULINGS: "LETRICK'S CHIMNEY EXTERIOR FACE IS SIDED. Include it.
The rear chase's 54.37 ft² stands, and the p7 'STONE FACADE' note at
x≈62% is not the chase — record that so it does not reopen. BONI'S
150 ft² CHASE REFUSES. No locatable ink supports it. CHASE ROW ON THE
QUOTE — YES, with the basis labelled."

Item 1: "THE CHASE SURFACE MUST STILL EXIST, REFUSED AND BINDABLE ...
a partition that only creates surfaces where ink exists WOULD LEAVE
HOWARD NOWHERE TO DRAW. That is the send-48 lesson repeating."

Item 2: "CUSTOMER-FACING IS WHERE A LAUNDERED BASIS DOES THE MOST
DAMAGE ... A QUOTE CANNOT SHOW TWO NUMBERS ... a chase on a
contested-scale face REFUSES AND BLOCKS THE GATE unless the contest
is resolved."

Item 3: "≈101 ft² is roughly 1 SQ on Letrick ... SAME LANDMINE SHAPE
AS THE 18.0 SQ AND THE GABLE DROP. Warn, never move silently."
"""
import pathlib

from gates import GATE_TIERS, QUOTE_BLOCKING
from routes.pdf_overlay import (_face_ok, _surface_of,
                                apply_overlay_to_takeoff,
                                surface_derived_snapshot)


def test_chase_surfaces_are_bindable_on_every_house():
    """Item 1 — the surface exists, ink or no ink; Howard can draw."""
    for f in ("front", "back", "left", "right"):
        assert _face_ok(f"chase:{f}")
        assert _surface_of(f"chase:{f}") == (f, "chase")
    assert not _face_ok("chase:bogus")


def test_chase_snapshot_refuses_with_a_name_and_binds_at_zero():
    sqft, refusal = surface_derived_snapshot({}, "chase:left")
    assert sqft == 0.0
    assert "no chase is ever derived" in refusal
    # even with a walk detail present, the chase never supersedes it
    est = {"hover_measurements": {"_wall_walk_detail": [
        {"label": "left", "body_sqft": 300.0}]}}
    sqft, refusal = surface_derived_snapshot(est, "chase:left")
    assert sqft == 0.0 and refusal


def _lines():
    return [{"name": 'Ascend Composite Lap Siding 7"', "unit": "SQ",
             "qty": 18.0, "raw_qty": 17.5, "mat": 100, "lab": 50,
             "tab": "ascend", "section": "Ascend Cladding"}]


def _chase_zone(**over):
    z = {"id": "z1", "face_id": "chase:back", "provenance": "human",
         "material_class": "siding", "sqft": 54.37,
         "tier": "derived_chain",
         "basis": ("rear chase width 5'-4\" — supplied by Howard from "
                   "the prints, not read from this drawing — HUMAN "
                   "DIMENSION, never presented as derived")}
    z.update(over)
    return z


def test_clean_chase_zone_becomes_its_own_quote_row_basis_labelled():
    out = apply_overlay_to_takeoff(_lines(), [_chase_zone()])
    rows = [l for l in out if l.get("overlay_chase_line")]
    assert len(rows) == 1
    r = rows[0]
    assert r["name"] == "Chimney Chase — rear"
    assert r["qty"] == 0.54                       # 54.37 ft² → SQ
    assert "supplied by Howard from the prints" in r["note"]
    assert "never presented as derived" in r["note"].lower() or \
        "HUMAN DIMENSION" in r["note"]
    # item 2 of the ORDER: the four corner verticals, visible, unpriced
    assert "4 corner verticals" in r["chase_corner_note"]
    assert "corner count unchanged" in r["chase_corner_note"]
    # the body line is untouched by the chase zone
    body = next(l for l in out if not l.get("overlay_chase_line"))
    assert body["qty"] == 18.0


def test_contested_scale_chase_refuses_and_names_ruling_l():
    z = _chase_zone(tier="contested_pick_larger",
                    basis="chase — this face's scale stays CONTESTED "
                          "(9'-11 vs 9-1⅛)")
    out = apply_overlay_to_takeoff(_lines(), [z])
    r = next(l for l in out if l.get("overlay_chase_line"))
    assert r["qty"] is None                       # never quietly prices
    assert r["not_derivable"] is True
    assert "Ruling L" in r["not_derivable_reason"]
    assert "CONTESTED" in r["not_derivable_reason"]


def test_scaleless_chase_zone_refuses_never_zero():
    out = apply_overlay_to_takeoff(_lines(), [_chase_zone(sqft=None)])
    r = next(l for l in out if l.get("overlay_chase_line"))
    assert r["qty"] is None and r["not_derivable"] is True
    assert "REFUSED" in r["note"]


def test_chase_rows_rebuild_never_duplicate():
    z = _chase_zone()
    once = apply_overlay_to_takeoff(_lines(), [z])
    twice = apply_overlay_to_takeoff(once, [z])
    assert len([l for l in twice if l.get("overlay_chase_line")]) == 1


def test_proposed_chase_zones_feed_no_row():
    out = apply_overlay_to_takeoff(
        _lines(), [_chase_zone(provenance="proposed")])
    assert not [l for l in out if l.get("overlay_chase_line")]


def test_gate_registry_carries_the_chase_code_as_quote_blocking():
    assert GATE_TIERS["chase_contested_scale"] == "quote"
    assert "chase_contested_scale" in QUOTE_BLOCKING
    # the emitted kind is registered too — "chase_refused" rows are
    # quote-tier by creation (a tierless code is a lying gate)
    from gates import KIND_TIERS, tier_for
    assert KIND_TIERS["chase_refused"] == "quote"
    assert tier_for("chase_contested_scale", "chase_refused") == "quote"


def test_structural_readiness_emits_the_blocker_and_propose_refuses():
    src = pathlib.Path(
        "/app/backend/routes/lp_package_routes.py").read_text()
    assert "chase_contested_scale" in src
    assert '"blocking": True' in src
    psrc = pathlib.Path(
        "/app/backend/routes/pdf_overlay.py").read_text()
    # item 1: model-claimed chase with no ink refuses, stays bindable
    assert "no chase ink locatable" in psrc
    assert "stays bindable" in psrc
    # item 3: warn, never move silently
    assert "recovery_warning" in psrc
    # Ruling L on the frontend total
    csrc = pathlib.Path("/app/frontend/src/lib/calc.js").read_text()
    assert "incomplete" in csrc and "Ruling L" in csrc
