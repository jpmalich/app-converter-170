"""ACCEPTANCE BAR LINES (f) + (a) (sealed by Howard 2026-08-07).

(f) The standing detectors are NAMED in the bar and present: registry
    round-trip, purity/evidence-constant detectors, suite determinism.
(a) Howard sealed the agent's rewrite VERBATIM: "every family derives
    through every door with no unexplained line and no fixture drift;
    deltas against second opinions are RECORDED with a cause, NEVER
    SCORED." Battens 265-vs-465 and 540-trim 100-vs-142 stay recorded
    deltas with causes — they are not a grade.
"""
from pathlib import Path

TESTS = Path(__file__).resolve().parent
MEMORY = TESTS.parents[1] / "memory"

STANDING_DETECTORS = (
    "test_spec_registry_roundtrip_2026_08_06.py",   # pipe integrity
    "test_corner_gutter_rulings_2026_08_06.py",     # purity + evidence constants
    "test_suite_determinism_2026_08_07.py",         # deterministic traffic
    "test_acceptance_four_column_2026_07_28.py",    # family × door walk
    "test_bar_d_lines_explain_2026_08_07.py",       # every line explains itself
)


def test_f_standing_detectors_named_and_present():
    missing = [f for f in STANDING_DETECTORS if not (TESTS / f).exists()]
    assert not missing, f"bar line (f): standing detectors gone: {missing}"


def test_a_second_opinion_deltas_recorded_with_cause_never_scored():
    table = (MEMORY / "acceptance_table_2026_07_28.md").read_text()
    for line in table.splitlines():
        if "delta" not in line.lower():
            continue
        assert ("vs" in line or "—" in line or "OPEN" in line), (
            "bar line (a): a recorded delta without a named cause is a "
            f"grade in disguise: {line[:120]}")


def test_a_no_second_opinion_number_is_an_assertion_target():
    """The 465-battens trap, pinned: the four-column suite may RECORD
    the second-opinion numbers but never asserts equality to them."""
    src = (TESTS / "test_acceptance_four_column_2026_07_28.py").read_text()
    for barred in ("== 465", "== 142"):
        assert barred not in src, (
            f"bar line (a): second opinion became a scored target ({barred})")
