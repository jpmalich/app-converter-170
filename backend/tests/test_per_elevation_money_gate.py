"""PER-ELEVATION SPLITS → LP MONEY GATE (Howard 2026-07-26: propose-first).

Facts pinned here, stated plainly (corrected after full trace):
ALREADY RULED + WIRED (not gated, pinned in place):
  - /measure/map mapper (routes/hover.py) emits per-profile quote lines
    for vinyl/ascend/lp_smart tabs from `_per_profile_sqft`
    (Iter 78z Campbell directive; 78ab LP coverage; 79j.71 conflict
    tripwire; compare-profiles ruling 2026-07-16).
  - lp_package_routes.py: default-profile inheritance ONLY
    (_force_profile_measurements writes / _apply_default_profile reads,
    ruled slice 1; B&B starter OFF ruled+pinned).
  - lp_package.py: shake 540-series trim bump ONLY (ruled 2026-07-17).
THE UNRULED GAP (this gate): mixed-family splits do NOT reach the LP
PACKAGE materialize siding lines — that wiring waits on Howard's ruling
on memory/proposals/per_elevation_splits_lp_money_proposal.md. Any NEW
consumption point in the LP package path trips this gate.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
LP_ROUTES = (BACKEND / "routes" / "lp_package_routes.py").read_text()
LP_PKG = (BACKEND / "lp_package.py").read_text()
HOVER = (BACKEND / "routes" / "hover.py").read_text()


def test_lp_package_split_consumption_frozen_at_ruled_set():
    # lp_package_routes: exactly the 2 default-profile-inheritance touches
    assert LP_ROUTES.count("_per_profile_sqft") == 2, (
        "per-profile consumption in lp_package_routes.py changed — "
        "new LP-money wiring requires Howard's ruling on the splits proposal"
    )
    # lp_package: exactly the 1 ruled shake 540-bump read
    assert LP_PKG.count("_per_profile_sqft") == 1, (
        "per-profile consumption in lp_package.py changed — "
        "new LP-money wiring requires Howard's ruling on the splits proposal"
    )
    # the raw breakdown never enters the LP package path at all
    for src, name in ((LP_ROUTES, "lp_package_routes.py"), (LP_PKG, "lp_package.py")):
        assert "_per_elevation_breakdown" not in src, (
            f"_per_elevation_breakdown entered {name} — requires ruling"
        )


def test_ruled_iter78z_mapper_path_still_stands():
    # the already-ruled consumption stays exactly where it is
    assert "_per_profile_sqft" in HOVER
    assert "_per_profile_composition" in HOVER
