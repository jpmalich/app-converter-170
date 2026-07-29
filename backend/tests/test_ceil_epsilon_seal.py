"""CEIL + IEEE754 — EPSILON LIVES IN THE CEIL (Howard, owed item 2b,
sealed 2026-07-29).

THE CLASS: 100 × 1.1 = 110.00000000000001 in IEEE754. A straight ceil on
that artifact returns 111 — a phantom stick nobody cuts (the 110.5
regression's sibling). THE SEAL: every ceil that lands a COUNT subtracts
the epsilon INSIDE the ceil (`ceil(x - 1e-9)`), every line, both
emitters, backend and frontend. A line whose raw × waste is a
MATHEMATICAL integer comes back as that integer — never integer+1.

Proven live before the fix: bb_batten_pieces(Σ 310.4×10 = 3104.0000000000005)
returned 195 sticks for a mathematically-exact 194.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND = Path("/app/backend")
SRC = Path("/app/frontend/src")

# Every module whose ceils land counts (money path). Display-only
# geometry (ElevationDrawing.jsx, elevation3D.js batten strokes) is
# exempt BY NAME — those ceils draw pixels, not orders.
BACKEND_MONEY_MODULES = [
    BACKEND / "routes" / "hover.py",
    BACKEND / "routes" / "lp_package_routes.py",
    BACKEND / "lp_package.py",
    BACKEND / "lp_smartside_formulas.py",
    BACKEND / "services.py",
]
FRONTEND_MONEY_MODULES = [
    SRC / "lib" / "wasteLogic.js",
    SRC / "lib" / "useRecalcSoffitOnOverhang.js",
    SRC / "components" / "estimate" / "PorchCeilingsCard.jsx",
    SRC / "components" / "estimate" / "ISSHoverImportButton.jsx",
]


def _naked_ceils(text: str, call: str) -> list[str]:
    out, i = [], 0
    while True:
        j = text.find(call + "(", i)
        if j < 0:
            return out
        k = j + len(call) + 1
        depth, m = 1, k
        while depth and m < len(text):
            c = text[m]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            m += 1
        inner = text[k:m - 1]
        if "1e-9" not in inner:
            line_no = text.count("\n", 0, j) + 1
            out.append(f"L{line_no}: {call}({inner[:60]}…)")
        i = m


def test_no_naked_ceil_in_any_count_landing_module():
    offenders = []
    for p in BACKEND_MONEY_MODULES:
        for hit in _naked_ceils(p.read_text(), "math.ceil"):
            offenders.append(f"{p.name} {hit}")
    for p in FRONTEND_MONEY_MODULES:
        for hit in _naked_ceils(p.read_text(), "Math.ceil"):
            offenders.append(f"{p.name} {hit}")
    assert not offenders, (
        "NAKED CEIL landing a count (epsilon lives IN the ceil — sealed "
        f"2026-07-29): {offenders}")


def test_frontend_round_up_whole_carries_epsilon():
    js = (SRC / "lib" / "wasteLogic.js").read_text()
    assert "Math.ceil(x - 1e-9)" in js  # roundUpWhole — the ONE frontend rounder


# ── numeric pins: a mathematical integer comes back as THAT integer ──────
def test_mathematical_integer_never_returns_integer_plus_one():
    from routes.hover import _bake_tab_waste
    from lp_smartside_formulas import (bb_batten_pieces, lap_pieces_book,
                                       pieces_needed)
    # Howard's case: 100 × 1.1 = 110.000…01 → 110, not 111 — both emitters
    row = {"tab": "vinyl", "section": "Vinyl Siding", "name": "x",
           "unit": "SQ", "qty": 100.0}
    assert _bake_tab_waste([dict(row)], 10)[0]["qty"] == 110.0
    # panel emitter: 1000 ft² ÷ 10 ft²/pc × 1.1 = mathematically 110
    assert pieces_needed(1000.0, 10.0, 0.10) == 110
    # the live batten artifact: Σ(310.4 × 10) = 3104.0000000000005 LF ÷ 16
    noisy_lf = sum([310.4] * 10)
    assert noisy_lf != 3104.0            # the artifact is real
    assert bb_batten_pieces(noisy_lf) == 194   # was 195 before the seal
    assert bb_batten_pieces(3104.0) == 194
    # lap book stays exact where it was exact
    assert lap_pieces_book(2000.0, waste=0.30) == 286


def test_epsilon_never_rounds_a_true_fraction_down():
    """The epsilon only strips noise ≤ 1e-9 — a real fractional stick
    still buys the next whole one."""
    from lp_smartside_formulas import bb_batten_pieces, pieces_needed
    assert bb_batten_pieces(3104.1) == 195
    assert pieces_needed(1001.0, 10.0, 0.10) == 111   # 110.11 → 111
