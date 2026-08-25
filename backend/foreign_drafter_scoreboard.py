"""SEND-125 registry (Howard authorized 2026-08-24) — FOREIGN-DRAFTER
DERIVED-VS-TOTAL. The earned claim is COMPUTED FROM THESE FIGURES and
never asserted in prose.

A foreign drafter is a set whose sheets were not drawn by the drafters
the pipeline was built against. Quantities only: `derived` counts the
faces/figures the pipeline actually DERIVED on that set; `total` is the
measurable set it was scored against. Refusals are not derivations.

House names here are DATA (registry precedent: fixture_figures.py),
never operative logic.
"""

CLAIM_FAILS_SAFE = "fails safe on unfamiliar sets"
CLAIM_READS = "reads unfamiliar sets"

FOREIGN_DRAFTER_SCOREBOARD = {
    "tanis": {"derived": 0, "total": 4, "sealed": True},
    # dart: SEALED 2026-08-24, scored read ff0d596e the same day —
    # 0 of 4 faces derived (3 widths returned from LOCATED but
    # MIS-ASSIGNED glyphs, all outside tolerance; 4 heights refused).
    "dart": {"derived": 0, "total": 4, "sealed": True},
}

# The read-claim is earned only when MORE THAN ONE foreign drafter shows
# real derivation — one set deriving is an anecdote, the same bar the
# fixture registry holds Tanis to.
MIN_DRAFTERS_DERIVING = 2


def derived_total() -> tuple[int, int]:
    d = sum(e["derived"] for e in FOREIGN_DRAFTER_SCOREBOARD.values())
    t = sum(e["total"] for e in FOREIGN_DRAFTER_SCOREBOARD.values())
    return d, t


def drafters_deriving(board: dict | None = None) -> int:
    board = FOREIGN_DRAFTER_SCOREBOARD if board is None else board
    return sum(1 for e in board.values() if e["derived"] > 0)


def earned_claim(board: dict | None = None) -> str:
    """The claim the FIGURES support — the only place it may come from."""
    if drafters_deriving(board) >= MIN_DRAFTERS_DERIVING:
        return CLAIM_READS
    return CLAIM_FAILS_SAFE


def read_claim_earned(board: dict | None = None) -> bool:
    return earned_claim(board) == CLAIM_READS
