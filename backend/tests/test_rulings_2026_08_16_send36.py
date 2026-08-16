"""SEND-36 (Howard sealed 2026-08-16) — Rulings MM + NN + LL pins.

MM — POSITION MERGE FIRST. Readings whose boxes overlap are ONE
string (parameter-free same-location test: either center inside the
other's box). Prefer the most completely parsed. Two complete readings
disagreeing in value → conflicted, never a dimension. A chain mate must
be a DIFFERENT physical string, established after merge — the Letrick
p8 confirmed error ('0-00' outran its own true reading 30'-0") dies
here, at the merge, not at a value patch.

NN — ZERO TOTAL LENGTH IS NOT A DIMENSION. A 6" dimension is real.

LL — SUM CLOSURE against merged strings: the largest member of an
aligned chain is the total candidate; the chain closes when the rest
sum to it exactly. Residuals are reported, never tolerated away.
"""
import sys

sys.path.insert(0, "/app/backend")

import ocr_geometry as og


def _run(raw, x, y, w, h, axis, src="upright"):
    return {"norm": raw, "raw": raw,
            "loc": {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h},
            "src": src, "axis": axis}


# The Letrick p5/p8 shape: three passes, one physical string.
def _triplet():
    return [
        _run("0-00", 19.46, 53.32, 0.71, 2.26, og.VERTICAL, "upright"),
        _run("0-.00", 19.28, 53.32, 0.76, 2.19, og.VERTICAL, "rot90"),
        _run("30'-0*", 19.41, 53.29, 0.76, 2.06, og.VERTICAL, "rot270"),
    ]


def test_mm_same_location_readings_collapse_to_the_complete_one():
    merged = og.merge_positions(_triplet())
    assert len(merged) == 1
    m = merged[0]
    assert m["raw"] == "30'-0*"          # fully-marked beats fragments
    assert m["merge_count"] == 3
    assert m["merged_srcs"] == ["rot270", "rot90", "upright"]
    assert m["merge_conflict"] is False  # only ONE complete reading


def test_mm_two_complete_readings_disagreeing_is_conflicted():
    runs = [
        _run("30'-0\"", 19.4, 53.3, 0.7, 2.1, og.VERTICAL, "upright"),
        _run("38'-0\"", 19.45, 53.32, 0.7, 2.1, og.VERTICAL, "rot90"),
    ]
    merged = og.merge_positions(runs)
    assert len(merged) == 1
    assert merged[0]["merge_conflict"] is True
    # A conflicted string never enters a dimension path.
    assert og._is_clean_dim(merged[0]) is False


def test_mm_distinct_strings_never_merge():
    runs = [
        _run("30-2", 20.33, 49.6, 0.55, 1.53, og.VERTICAL),
        _run("5'10°", 20.41, 68.38, 0.55, 1.4, og.VERTICAL),  # same column, different spot
    ]
    assert len(og.merge_positions(runs)) == 2


def test_mm_is_idempotent():
    once = og.merge_positions(_triplet())
    twice = og.merge_positions(once)
    assert [r["raw"] for r in twice] == [r["raw"] for r in once]


def test_mm_kills_the_p8_confirmed_error_in_the_probe():
    # The fragment can no longer contend against its own true reading.
    runs = [
        _run("54'-0\"", 50.0, 15.0, 1.5, 1.0, og.HORIZONTAL),
        _run("54'-0\"", 50.0, 75.0, 1.5, 1.0, og.HORIZONTAL),
        _run("30'-0\"", 85.0, 50.0, 0.7, 2.1, og.VERTICAL, "rot270"),
    ] + _triplet()  # the left depth read three ways at one spot
    rep = og.positional_rule_probe(runs)
    assert rep["envelope"]["status"] == "ESTABLISHED"
    assert rep["sides"]["left"]["chosen"]["raw"] == "30'-0*"
    raws = [c["raw"] for c in rep["sides"]["left"]["contenders"]]
    assert "0-00" not in raws and "0-.00" not in raws


def test_mm_chain_mate_must_be_a_different_physical_string():
    # A bare form whose only "mate" is its own overlapping true reading
    # merges into it — no admission, no self-chaining.
    runs = [
        _run("58'-0\"", 50.0, 15.0, 1.5, 1.0, og.HORIZONTAL),
        _run("58'-0\"", 50.0, 75.0, 1.5, 1.0, og.HORIZONTAL),
        _run("33'-0\"", 85.0, 50.0, 0.7, 2.1, og.VERTICAL),
        _run("12'-0\"", 15.0, 30.0, 0.7, 2.1, og.VERTICAL),
    ] + _triplet()
    adm = og.gated_bare_form_admissions(runs)
    assert [a["run"]["raw"] for a in adm["admitted"]] == []


# ---------------------------------------------------------------------------
# RULING NN
# ---------------------------------------------------------------------------

def test_nn_zero_total_length_is_refused_but_six_inches_is_real():
    base = [
        _run("58'-0\"", 50.0, 15.0, 1.5, 1.0, og.HORIZONTAL),
        _run("58'-0\"", 50.0, 75.0, 1.5, 1.0, og.HORIZONTAL),
        _run("33'-0\"", 85.0, 50.0, 0.7, 2.1, og.VERTICAL),
        _run("12'-0\"", 15.0, 30.0, 0.7, 2.1, og.VERTICAL),  # chain mate col x~15
    ]
    zero = base + [_run("0-0", 15.1, 55.0, 0.6, 1.5, og.VERTICAL)]
    assert [a["run"]["raw"] for a in
            og.gated_bare_form_admissions(zero)["admitted"]] == []
    six = base + [_run("0-6", 15.1, 55.0, 0.6, 1.5, og.VERTICAL)]
    assert [a["run"]["raw"] for a in
            og.gated_bare_form_admissions(six)["admitted"]] == ["0-6"]


# ---------------------------------------------------------------------------
# RULING LL
# ---------------------------------------------------------------------------

def test_ll_chain_closes_when_segments_sum_to_the_total():
    runs = [
        _run("58'-0\"", 50.0, 15.0, 1.5, 1.0, og.HORIZONTAL),
        _run("24'-6\"", 30.0, 15.1, 1.2, 1.0, og.HORIZONTAL),
        _run("33'-6\"", 70.0, 14.9, 1.2, 1.0, og.HORIZONTAL),
    ]
    rep = og.chain_sum_closure(runs)
    assert len(rep) == 1
    assert rep[0]["status"] == "CLOSES"
    assert rep[0]["total_candidate_in"] == 58 * 12


def test_ll_failing_chain_reports_the_residual_not_a_tolerance():
    runs = [
        _run("30'-2\"", 20.0, 40.0, 0.6, 1.5, og.VERTICAL),
        _run("5'-10\"", 20.05, 60.0, 0.6, 1.5, og.VERTICAL),
    ]
    rep = og.chain_sum_closure(runs)
    assert rep[0]["status"] == "FAILS"
    assert rep[0]["residual_in"] == (5 * 12 + 10) - (30 * 12 + 2)


def test_ll_merged_triplicates_do_not_triple_sum():
    # Before MM, three readings of one member would wreck the sum.
    runs = [
        _run("30'-0\"", 19.4, 20.0, 0.6, 1.5, og.VERTICAL),
        _run("15'-0\"", 19.45, 50.0, 0.6, 1.5, og.VERTICAL),
        _run("15'-0\"", 19.42, 50.05, 0.6, 1.5, og.VERTICAL),  # same spot re-read
        _run("15'-0\"", 19.5, 70.0, 0.6, 1.5, og.VERTICAL),
    ]
    rep = og.chain_sum_closure(runs)
    assert rep[0]["status"] == "CLOSES"
    assert rep[0]["segment_sum_in"] == 30 * 12
