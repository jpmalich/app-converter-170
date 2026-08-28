"""DEPRECATED IMPORT PATH — kept for ONE release (SEND-142, 2026-08-28).

The sealed hand-takeoff answer key moved to `sealed_hand_takeoff_key.py`
and its constant is `SEALED_HAND_TAKEOFF_KEY`. This shim only re-exports
that module so any import missed this release keeps working. It holds NO
figure, NO basis line and NO ruling text of its own — there is exactly
one home for the sealed values.
"""
from sealed_hand_takeoff_key import SEALED_HAND_TAKEOFF_KEY

LETRICK_HAND_TAKEOFF_KEY = SEALED_HAND_TAKEOFF_KEY

__all__ = ["SEALED_HAND_TAKEOFF_KEY", "LETRICK_HAND_TAKEOFF_KEY"]
