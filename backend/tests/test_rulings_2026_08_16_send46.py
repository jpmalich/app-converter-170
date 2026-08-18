"""SEND-46 (Howard sealed 2026-08-16) — register pins.

CENSUS FINDING registered with figures named: Boni 20.0 unreconstructable
(9'-11" + 8'-1 1/2" = 18.04, second string never located); Letrick fans
one string across four faces. Model heights demoted to hypothesis — may
be SHOWN, may never feed a quantity.
DP-1 sealed (siding band = FIRST FLOOR → plate/soffit; DERIVED when
established). DP-2/DP-3 = ONE named open (elevation segment x-extents).
DP-4 sealed (walkout footer = suspicion only). DP-5 sealed (close the
joist band by subtraction with residual 0, else refuse — no convention).
"""
import sys

sys.path.insert(0, "/app/backend")

import ocr_geometry as og


def test_census_finding_registered_with_figures():
    f = " ".join(og.RULINGS_REGISTER["findings"])
    assert "20.0" in f and "18.04" in f
    assert "NEVER LOCATED" in f
    assert "9'-11 1/8\"" in f
    assert "DEMOTED TO HYPOTHESIS" in f
    assert "NEVER feed a quantity" in f


def test_dp1_dp4_dp5_sealed():
    s = " ".join(og.RULINGS_REGISTER["sealed"])
    assert "DP-1" in s and "FIRST FLOOR" in s and "DERIVED" in s
    assert "does not need resolving for height" in s
    assert "DP-4" in s and "SUSPICION of STEP" in s
    assert "DP-5" in s and "subtraction" in s and "residual 0" in s


def test_dp2_dp3_one_named_open_and_joist_open():
    opens = " ".join(og.RULINGS_REGISTER["named_open"])
    assert "elevation segment x-extents" in opens
    assert "not a single column" in opens
    assert "no tiebreak" in opens
    assert "joist band" in opens
    assert "do not invent a convention" in opens.lower()
