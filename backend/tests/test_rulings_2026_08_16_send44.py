"""SEND-44 (Howard sealed 2026-08-16) — the register pin.

RULED OUT: multi-structure support inside one estimate — a detached
garage / outbuilding is its OWN estimate. Registered so it can never
reappear as an assumption.
NAMED OPEN (beside the others): two footprints drawn on one sheet —
separate estimates keep the takeoffs apart, not the drawings apart.
Report-only; not built against.
"""
import sys

sys.path.insert(0, "/app/backend")

import ocr_geometry as og


def test_register_multi_structure_is_ruled_out():
    ruled = " ".join(og.RULINGS_REGISTER["ruled_out"])
    assert "multi-structure" in ruled
    assert "OWN estimate" in ruled


def test_register_named_opens_stay_visible():
    opens = " ".join(og.RULINGS_REGISTER["named_open"])
    assert "segment-vs-total" in opens
    assert "different depths + no garage" in opens
    assert "joist sheets" in opens
    assert "two footprints" in opens
