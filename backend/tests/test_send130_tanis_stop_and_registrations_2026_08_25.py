"""SEND-130 pins (Howard ruled 2026-08-25).

The Tanis query answered, and the four registrations that came out of the
sweep and the lift pinned so they cannot quietly drift:

1. Where the line-work read stops, PER FACE, as a named five-step chain —
   CARVE → DATUM PAIR → SEGMENTS → FENCE → OUTLINE — so a later change
   cannot silently move the stop.
2. THE MARK BELONGS TO THE FIGURE, NOT THE FACE.
3. WIDTH refuses body AND gable; HEIGHT refuses the BODY only.
4. THE LIFT DID NOT ADVANCE GENERALITY, as predicted — Letrick's recovery
   is not movement on the reads claim.
5. The front overread is explained and two independent routes agree on the
   SEND-110 residual shape.
"""
import attribution_lift as lift
import measure_staging as staging
from foreign_drafter_scoreboard import (CLAIM_FAILS_SAFE, earned_claim,
                                        drafters_emitting)
from ocr_geometry import RULINGS_REGISTER

FINDINGS = "\n".join(RULINGS_REGISTER["findings"])


def test_the_five_step_chain_is_registered_with_where_tanis_stops():
    for step in ("CARVE", "DATUM PAIR", "SEGMENTS", "FENCE", "OUTLINE"):
        assert step in FINDINGS, step
    # three carved faces stop at the datum pair with the outline READY
    assert "DATUM PAIR FAILED" in FINDINGS
    assert "31,841" in FINDINGS and "27,566" in FINDINGS
    # the left face fails one step earlier, in dart's class
    assert "CARVE FAILED" in FINDINGS
    # and the three re-OCR scales are on the record, not just the verdict
    for scale in ("x2", "x4", "x6"):
        assert scale in FINDINGS, scale
    assert "NOT a resolution problem" in FINDINGS


def test_the_mark_belongs_to_the_figure_not_the_face():
    assert "THE MARK BELONGS TO THE FIGURE, NOT THE FACE" in FINDINGS
    assert "CLEARS, NAMED" in FINDINGS


def test_the_width_height_asymmetry_is_stated_not_implied():
    assert "UNATTRIBUTED WIDTH refuses BODY AND GABLE" in FINDINGS
    assert "HEIGHT refuses the BODY ONLY" in FINDINGS
    # and the code does what the register says
    walls = [{"label": "left", "width_ft": 30.0, "height_ft": 9.0,
              "gable_triangle_height_ft": 8.0}]
    body_only = staging.walk_walls(
        walls, unattributed_faces={"left": {"reason": "height unowned",
                                            "_scope": "body"}})
    assert body_only["gable_sqft"] > 0, "a gable reads no height"
    whole_face = staging.walk_walls(
        walls, unattributed_faces={"left": {"reason": "width unowned",
                                            "_scope": "face"}})
    assert whole_face["gable_sqft"] == 0.0 and whole_face["siding_sqft"] == 0.0


def test_the_lift_is_registered_as_not_advancing_generality():
    assert "THE LIFT DID NOT ADVANCE GENERALITY, AS PREDICTED" in FINDINGS
    assert "1,402.62" in FINDINGS and "ALREADY working" in FINDINGS
    # the claim itself has not moved: no foreign drafter emits
    assert drafters_emitting() == 0
    assert earned_claim() == CLAIM_FAILS_SAFE
    # and corroboration cannot reach a house with no first read
    v = lift.evaluate(56.0, {"status": "NOT_ATTEMPTED",
                             "reason": "no elevation drawing located"})
    assert v["lifted"] is False and v["delta_ft"] is None


def test_the_front_overread_explanation_ties_to_the_send110_residual():
    assert "THE FRONT OVERREAD IS EXPLAINED" in FINDINGS
    assert "+0.73" in FINDINGS and "-0.59" in FINDINGS and "-0.33" in FINDINGS
    assert "over on front/back, under on sides" in FINDINGS
    assert "fix stays" in FINDINGS and "declined" in FINDINGS
