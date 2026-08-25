"""SEND-128 pins (Howard ruled 2026-08-25) — two things that stand
regardless of how the corroboration lift is ruled:

1. THE SEND-13 AMENDMENT IS REGISTERED, not remembered: the narrowing
   from KILL to FLAG was right for DISPLAY and wrong for QUANTITY.
2. `earned_claim()` reads FAILS_SAFE on the quantity-emitted metric with
   no lane leaking — the plain answer owed, pinned so it cannot drift
   silently.
"""
from foreign_drafter_scoreboard import (CLAIM_FAILS_SAFE, earned_claim,
                                        unattributed_lanes)
from seam_accounting import SEAM_REGISTRY


def test_send13_amendment_is_registered_against_the_send13_entry():
    text = SEAM_REGISTRY["dims_demoted_quote_shared"]
    assert "send-13" in text and "send-128" in text
    # the distinction itself, in the register
    assert "RIGHT FOR DISPLAY" in text and "WRONG FOR QUANTITY" in text
    # and what it cost, in quantities
    assert "1,280.53" in text and "170 LF" in text
    # the consumer split is pointed at, not restated
    assert "dims_unattributed_quantity_refused" in text


def test_fails_safe_is_earned_with_no_lane_leaking():
    assert unattributed_lanes() == {}
    assert earned_claim() == CLAIM_FAILS_SAFE
