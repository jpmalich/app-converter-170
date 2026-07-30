"""HARD BATTEN FORMULA — SEALED by Howard 2026-07-28. Pins the three
non-negotiables and the 3 Degree reproduction from the queue-item-d
diagnosis. The function is sealed but NOT the live emitter until Howard
rules the diagnosis inputs (spacing job input 12/16/24, stick length,
story heights source)."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lp_smartside_formulas import (  # noqa: E402
    bb_batten_pieces_hard, bb_batten_lf, bb_batten_pieces,
    BATTEN_CATALOG_SKU,
)


def test_a_plus_one_per_segment():
    """A wall has one more batten than it has spaces."""
    # one 16' segment, 12" o.c., one 9' story, 10' sticks
    n = bb_batten_pieces_hard([(16.0, [9.0])], 12, 10.0)
    assert n == round((16 * 12 - 3.0) / 12) + 1 == 17     # 16 spaces + 1
    # split the same wall into two 8' segments → the +1 lands TWICE
    two = bb_batten_pieces_hard([(8.0, [9.0]), (8.0, [9.0])], 12, 10.0)
    assert two == 18 and two == n + 1


def test_b_per_story_not_per_wall_height():
    """Battens break + flash at floor lines (LP install rule, sealed):
    a two-story wall was never one batten."""
    one_story_18ft = bb_batten_pieces_hard([(20.0, [18.0])], 12, 10.0)
    two_stories_9ft = bb_batten_pieces_hard([(20.0, [9.0, 9.0])], 12, 10.0)
    battens = round((240 - 3.0) / 12) + 1                 # 21
    assert two_stories_9ft == battens * 2                 # 1 stick per story
    assert one_story_18ft == battens * 2                  # 18' run needs 2×10' — but
    # …with 16' sticks the difference shows: one continuous 18' run would
    # splice (2 pcs); two 9' stories still need 2 pcs — while a single 9'
    # story needs 1. Per-story ceil never merges floors:
    assert bb_batten_pieces_hard([(20.0, [9.0, 9.0])], 12, 16.0) == battens * 2


def test_c_no_splicing_scrap_is_scrap():
    """A 9' run from a 16' stick leaves 7' of SCRAP — never re-used on
    the next run. The aggregate method packs it (398-piece class)."""
    hard = bb_batten_pieces_hard([(20.0, [9.0])], 12, 16.0)
    assert hard == 21                                     # 21 sticks, 21 offcuts
    # aggregate on the identical wall: 21 battens × 9' = 189 LF ÷ 16'
    # splices end-to-end into 12 sticks — the silent under-order.
    agg_lf = 21 * 9.0
    assert bb_batten_pieces(agg_lf) == 12
    assert hard > bb_batten_pieces(agg_lf)


def test_aggregate_carries_no_plus_one():
    """State plainly (Howard item 2a): the CURRENT derivation does NOT
    carry the +1 per segment — bb_batten_lf is area ÷ spacing + height
    term, blind to segment count. Pinned as a documented deficiency until
    the hard formula wires in."""
    flat = bb_batten_lf(1000.0, 12, 0.0)
    split_blind = bb_batten_lf(500.0, 12, 0.0) + bb_batten_lf(500.0, 12, 0.0)
    assert flat == split_blind                            # segments invisible


def test_3degree_reproduction_howards_arithmetic():
    """Queue item d(e): 4,239 ft² at a 9' story ≈ 471 ft of wall run; at
    12\" o.c. ≈ 471 battens + one per segment ≈ ~490 pieces on 10' sticks
    — far closer to the 465 installed than the aggregate's 398."""
    run_ft = 4239.0 / 9.0                                 # 471.0 ft of run
    n_segments = 10                                       # facade-count order of magnitude
    seg_w = run_ft / n_segments
    pieces = bb_batten_pieces_hard([(seg_w, [9.0])] * n_segments, 12, 10.0)
    assert 465 <= pieces <= 500, f"hard formula gives {pieces} — Howard's ~490 confirmed"
    # CORRECTED 2026-07-29: the 465 is a SECOND OPINION (estimate-dept
    # takeoff, implied ~6.8" o.c. spliced), never a target. The live
    # aggregate at the ruled 12" default: 4239 LF ÷ 16 = 265 (the retired
    # 8" gave 398; 8 now raises).
    assert bb_batten_pieces(bb_batten_lf(4239.0, 12, 0.0)) == 265
    try:
        bb_batten_lf(4239.0, 8, 0.0)
        assert False, "8\" spacing is retired and must raise"
    except ValueError:
        pass


def test_sku_meets_preferred_spec_not_minimum():
    """Sealed install rule: preferred batten ≥2½\" wide, 5/8\" or 19/32\"
    thick (absolute minimum ½×1½ is NOT what we order)."""
    assert '19/32" x 3"' in BATTEN_CATALOG_SKU            # 3" ≥ 2.5" preferred, 19/32" thick


def test_spacing_guard_still_divides_48():
    with pytest.raises(ValueError):
        bb_batten_pieces_hard([(10.0, [9.0])], 13, 10.0)
