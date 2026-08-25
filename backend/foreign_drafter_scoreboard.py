"""SEND-125 registry, METRIC CHANGED SEND-127 (Howard ruled 2026-08-25) —
FOREIGN-DRAFTER QUANTITY EMITTED. The earned claim is COMPUTED FROM THESE
FIGURES and never asserted in prose.

WHY THE METRIC CHANGED: SEND-125 counted FACES DERIVED. Dart then emitted
1,280.53 ft² of gable and 170 LF of starter with ZERO faces derived — a
faces metric scores that read 0/4 and calls it fails-safe. "Fails safe"
means NO QUANTITY LEAVES WITHOUT ATTRIBUTION, ON ANY LANE. So the metric
is quantity emitted: unattributed quantity is the leak, attributed
quantity is the read.

A foreign drafter is a set whose sheets were not drawn by the drafters
the pipeline was built against. House names are DATA (registry
precedent: fixture_figures.py), never operative logic.
"""

CLAIM_NEITHER = "neither claim is earned — quantity leaked without attribution"
CLAIM_FAILS_SAFE = "fails safe on unfamiliar sets"
CLAIM_READS = "reads unfamiliar sets"

FOREIGN_DRAFTER_SCOREBOARD = {
    "tanis": {
        "sealed": True,
        # {lane: quantity} — quantity that left with its attribution
        # unestablished. Empty is the only fails-safe state.
        "unattributed_quantity_emitted": {},
        # {lane: quantity} — quantity that left WITH attribution AND
        # inside tolerance against the sealed truth.
        "attributed_quantity_emitted": {},
    },
    "dart": {
        "sealed": True,
        "unattributed_quantity_emitted": {},
        "attributed_quantity_emitted": {},
    },
}

# What SEND-126's scored read emitted BEFORE the SEND-127 attribution
# split — kept as the record of the leak the metric was blind to.
PRE_SEND127_LEAK = {
    "dart": {"gable_sqft": 1280.53, "starter_lf": 170.0,
             "footprint_perimeter_ft": 170.0, "rakes_lf": 136.0},
}

# The read-claim needs MORE THAN ONE foreign drafter emitting attributed
# quantity — one set is an anecdote.
MIN_DRAFTERS_EMITTING = 2


def _board(board=None) -> dict:
    return FOREIGN_DRAFTER_SCOREBOARD if board is None else board


def unattributed_lanes(board=None) -> dict:
    """{drafter: {lane: qty}} for every drafter still leaking."""
    return {d: e["unattributed_quantity_emitted"]
            for d, e in _board(board).items()
            if e["unattributed_quantity_emitted"]}


def drafters_emitting(board=None) -> int:
    return sum(1 for e in _board(board).values()
               if e["attributed_quantity_emitted"])


def earned_claim(board=None) -> str:
    """The claim the FIGURES support — the only place it may come from."""
    if unattributed_lanes(board):
        return CLAIM_NEITHER
    if drafters_emitting(board) >= MIN_DRAFTERS_EMITTING:
        return CLAIM_READS
    return CLAIM_FAILS_SAFE


def read_claim_earned(board=None) -> bool:
    return earned_claim(board) == CLAIM_READS


def fails_safe_earned(board=None) -> bool:
    return earned_claim(board) in (CLAIM_FAILS_SAFE, CLAIM_READS)
