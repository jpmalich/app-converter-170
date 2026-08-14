"""RULINGS REGISTER — SEND-14 (2026-08-14).

Per Ruling C (sealed this send): one register file per send, ruling WORDS
verbatim in the docstring, held rulings as visible named skips. Send-14
carried two rulings (C and D); the rest of the send was report-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes.ai_blueprint as ab  # noqa: E402
from routes.ai_blueprint import build_blueprint_readback  # noqa: E402


def test_ruling_C_register_discipline_is_permanent():
    """RULING C (send-14, SEALED): 'ONE REGISTER FILE PER SEND. Every
    ruling in that send becomes a pin in it, whether the ruling arrived
    as a numbered item or as a clause inside a paragraph. The RULING
    WORDS go in the docstring, verbatim. A ruling that is HELD enters as
    a VISIBLE NAMED SKIP stating why it is held and what would unhold it.
    A ruling that cannot be expressed as a pin is reported NOT BUILT in
    the handback. THE SUMMARY TRANSPORTS WHAT THE TESTS ENFORCE, NOT WHAT
    PROSE SAID.'

    Materially in place: the send-13 register exists and carries its held
    ruling as a skip; this send-14 register exists."""
    tests_dir = Path(__file__).resolve().parent
    assert (tests_dir / "test_rulings_2026_08_14_send13.py").exists()
    src = (tests_dir / "test_rulings_2026_08_14_send13.py").read_text()
    # the held ruling is on the record as a visible named skip
    assert "pytest.mark.skip" in src
    assert "HELD RULING" in src


def test_ruling_D_58ft_front_back_share_lands_on_the_PLAIN_rail():
    """RULING D (send-14): 'Correct predicate is PHYSICAL IMPOSSIBILITY:
    two features that cannot both hold that value... An overall dimension
    serving two opposing facades goes to the plain dims_shared_source
    rail with its consumers named.'

    THIS IS THE NAMED PIN Ruling D asked for: 58'-0" serving front AND
    back width is NOT a conflict — it is the house — so it rides the
    PLAIN rail."""
    raw = {
        "walls": [{"label": "front", "width_ft": 58.0},
                  {"label": "back", "width_ft": 58.0}],
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 58.0, "page": 9, "from": "58'-0\""},
            "walls.back.width_ft": {"v": 58.0, "page": 9, "from": "58'-0\""},
        },
    }
    ab._one_source_one_path_guard(raw)
    rec = raw["_dim_shared_source"][0]
    assert rec["conflicting"] is False, "front/back overall is NOT a conflict"
    rb = build_blueprint_readback(raw)
    codes = {r["code"] for r in rb["rail"]}
    assert "dims_shared_source" in codes           # plain rail carries it
    assert "dims_shared_source_conflict" not in codes


def test_ruling_D_physically_impossible_shares_fire_the_conflict_rail():
    """RULING D (send-14): 'Two walls' heights on a house with differing
    wall heights. A wall height and a dormer height. A width and a
    height. Those go to dims_shared_source_conflict.'"""
    # width vs height — a width is not a height
    assert ab._shared_attribution_conflict(
        ["walls.front.width_ft", "walls.front.height_ft"]) is True
    # two walls' heights — cannot be assumed equal
    assert ab._shared_attribution_conflict(
        ["walls.front.height_ft", "walls.back.height_ft"]) is True
    # a wall height and a dormer height
    assert ab._shared_attribution_conflict(
        ["walls.front.height_ft", "dormers.front.dormer_height_ft"]) is True
    # opposing-facade widths — legitimate, PLAIN
    assert ab._shared_attribution_conflict(
        ["walls.front.width_ft", "walls.back.width_ft"]) is False
    # a width and a same-span gutter LF — both horizontal, PLAIN
    assert ab._shared_attribution_conflict(
        ["walls.front.width_ft", "gutter_runs.front.lf"]) is False
