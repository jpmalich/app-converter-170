"""SEND-38 (Howard sealed 2026-08-16) — Ruling XX ADOPTED + TT/UU/VV/WW.

XX — equal left/right depths make attribution IMMATERIAL; it NEVER
overrides closure (the pin that keeps the ruling safe rather than
convenient); unequal depths still require the anchor or a refusal;
"different depths + no garage" is a NAMED OPEN that refuses today.

TT — corrected LL: segments on the inner line sum to the total on the
next rail out; fraction loss declared, never a tolerance; reports only.
UU — the INDETERMINATE band is the observed gap on merged data.
VV — foot/inch marks normalize by Unicode confusable CLASS.
WW — a depth candidate must lie ON the side's established rail line.
"""
import sys

sys.path.insert(0, "/app/backend")

import ocr_geometry as og


def _run(raw, x, y, w, h, axis, src="upright"):
    return {"norm": raw, "raw": raw,
            "loc": {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h},
            "src": src, "axis": axis}


def _letrick_like():
    return [
        _run("54'-0\"", 50.0, 15.0, 1.5, 1.0, og.HORIZONTAL),
        _run("54'-0\"", 50.0, 75.0, 1.5, 1.0, og.HORIZONTAL),
        _run("30'-0\"", 10.0, 45.0, 0.7, 2.1, og.VERTICAL),
        _run("30'-0*", 90.0, 45.0, 0.7, 2.1, og.VERTICAL),
    ]


def _boni_like():
    return [
        _run("58'-0\"", 50.0, 15.0, 1.5, 1.0, og.HORIZONTAL),
        _run("58'-0\"", 50.0, 75.0, 1.5, 1.0, og.HORIZONTAL),
        _run("30-2", 10.0, 45.0, 0.6, 1.6, og.VERTICAL),
        _run("30'-0\"", 10.05, 60.0, 0.6, 1.6, og.VERTICAL),
        _run("33'-0\"", 90.0, 45.0, 0.7, 2.1, og.VERTICAL),
    ]


# ---------------------------------------------------------------------------
# RULING XX
# ---------------------------------------------------------------------------

def test_xx_equal_pair_is_immaterial_and_carries_no_quantity():
    v = og.attribution_verdict(_letrick_like())
    assert v["status"] == "IMMATERIAL"
    assert v["depth"] == {"feet": 30, "inches": 0}
    assert v["pair"]["left"]["parsed"] == (30, 0)
    assert v["pair"]["right"]["parsed"] == (30, 0)
    # No derivability claim of any kind rides on the verdict.
    assert "area" not in str(sorted(v.keys()))
    assert "derivable" not in str(sorted(v.keys()))


def test_xx_closure_pin_is_explicit_on_every_verdict():
    # The clause that makes the ruling safe rather than convenient.
    for fixture in (_letrick_like(), _boni_like()):
        v = og.attribution_verdict(fixture)
        assert "NEVER OVERRIDES CLOSURE" in v["closure_pin"]
        assert "EE still blocks" in v["closure_pin"]


def test_xx_unequal_pair_is_material_anchor_or_refuse():
    v = og.attribution_verdict(_boni_like())
    assert v["status"] == "MATERIAL"
    assert "anchor" in v["why"]


def test_xx_no_candidate_on_a_side_means_no_pair_refusal_stands(monkeypatch):
    # STRUCTURAL NOTE: with an ESTABLISHED envelope each side's rail is
    # always its own candidate, so NO_PAIR is unreachable geometrically —
    # the branch is pinned defensively against a degenerate probe.
    real = og.positional_rule_probe

    def one_sided(runs):
        rep = real(runs)
        rep["sides"]["right"]["chosen"] = None
        return rep

    monkeypatch.setattr(og, "positional_rule_probe", one_sided)
    v = og.attribution_verdict(_letrick_like())
    assert v["status"] == "NO_PAIR"
    assert "refusal stands" in v["why"]


def test_xx_no_envelope_is_indeterminate():
    v = og.attribution_verdict([_letrick_like()[0]])
    assert v["status"] == og.INDETERMINATE


def test_xx_named_open_stays_registered():
    v = og.attribution_verdict(_letrick_like())
    assert "no garage" in v["named_open"]
    assert "REFUSES" in v["named_open"]


def test_exact_positional_tie_is_named_never_a_list_order_coin_flip():
    # The Boni p4 LEFT truth after merge: segment and total at the SAME
    # outermost x. The probe must say TIE, not pick by list order.
    runs = [
        _run("58'-0\"", 50.0, 15.0, 1.5, 1.0, og.HORIZONTAL),
        _run("58'-0\"", 50.0, 75.0, 1.5, 1.0, og.HORIZONTAL),
        _run("5'-10\"", 20.33, 68.4, 0.55, 1.5, og.VERTICAL),
        _run("30'-2\"", 20.33, 49.6, 0.55, 1.5, og.VERTICAL),
        _run("33'-0\"", 90.0, 45.0, 0.7, 2.1, og.VERTICAL),
    ]
    pr = og.positional_rule_probe(runs)
    left = pr["sides"]["left"]
    assert left["chosen"] is None
    assert set(left["tie"]) == {"5'-10\"", "30'-2\""}
    v = og.attribution_verdict(runs)
    assert v["status"] == og.INDETERMINATE
    assert "tie" in v["why"]


# ---------------------------------------------------------------------------
# RULING WW
# ---------------------------------------------------------------------------

def test_ww_off_rail_projection_is_excluded_structurally():
    # The chimney shape: vertical, exterior on y (above the top rail),
    # mid-sheet on x — off every side rail line.
    runs = _letrick_like() + [
        _run("2'-7\"", 50.0, 8.0, 0.7, 1.7, og.VERTICAL)]
    pr = og.positional_rule_probe(runs)
    for side in ("left", "right"):
        raws = [c["raw"] for c in pr["sides"][side]["contenders"]]
        assert "2'-7\"" not in raws
    # Visible, never silent.
    off = (pr["sides"]["left"]["excluded_off_rail"]
           + pr["sides"]["right"]["excluded_off_rail"])
    assert "2'-7\"" in [r["raw"] for r in off]
    # And XX still reads the pair as equal — the projection never
    # becomes a depth.
    assert og.attribution_verdict(runs)["status"] == "IMMATERIAL"


def test_ww_rail_line_chain_mates_stay_in_contention():
    pr = og.positional_rule_probe(_boni_like())
    left_raws = [c["raw"] for c in pr["sides"]["left"]["contenders"]]
    assert "30-2" in left_raws and "30'-0\"" in left_raws


# ---------------------------------------------------------------------------
# RULINGS UU + VV
# ---------------------------------------------------------------------------

def test_uu_band_is_the_observed_gap_on_merged_data():
    assert og.AXIS_VERTICAL_MAX == 0.1143
    assert og.AXIS_HORIZONTAL_MIN == 0.212


def test_vv_prime_glyph_size_pair_now_counts_two_tokens():
    # The Letrick p7 polluter: second foot mark rendered as PRIME.
    raw = "2'-11%2\"\u00d7 4\u2032-11/\""
    assert og.dimension_token_count(raw) == 2
    assert og.is_rail_candidate(raw) is False


def test_vv_confusable_class_covers_the_family_not_one_glyph():
    for mark in "\u2018\u2019\u0060\u00b4\u2032":
        assert og.is_dimension_like(f"33{mark}-0\"") is True
    for mark in "\u201c\u201d\u2033":
        assert og.normalize_marks(f"5{mark}").endswith('"')


# ---------------------------------------------------------------------------
# RULING TT
# ---------------------------------------------------------------------------

def test_tt_inner_segments_sum_to_the_total_on_the_next_rail_out():
    runs = [
        # outer left rail: the total, alone on its line
        _run("30'-2\"", 8.0, 45.0, 0.6, 1.6, og.VERTICAL),
        # inner line: segments
        _run("24'-4\"", 12.0, 30.0, 0.6, 1.6, og.VERTICAL),
        _run("5'-10\"", 12.05, 60.0, 0.6, 1.6, og.VERTICAL),
        # right half so the mid-line splits the halves as on a sheet
        _run("33'-0\"", 90.0, 45.0, 0.6, 1.6, og.VERTICAL),
    ]
    rep = [e for e in og.tt_closure(runs)
           if e["axis"] == og.VERTICAL and e["half"] == "low"]
    assert len(rep) == 1
    assert rep[0]["status"] == "CLOSES"
    assert rep[0]["total_in"] == 30 * 12 + 2
    assert rep[0]["segment_sum_in"] == 30 * 12 + 2


def test_tt_fraction_loss_is_declared_never_a_tolerance():
    runs = [
        _run("30'-2\"", 8.0, 45.0, 0.6, 1.6, og.VERTICAL),
        _run("24'-4%\"", 12.0, 30.0, 0.6, 1.6, og.VERTICAL),   # ½ lost
        _run("5'-9%\"", 12.05, 60.0, 0.6, 1.6, og.VERTICAL),   # ½ lost
        _run("33'-0\"", 90.0, 45.0, 0.6, 1.6, og.VERTICAL),
    ]
    rep = [e for e in og.tt_closure(runs)
           if e["axis"] == og.VERTICAL and e["half"] == "low"]
    assert rep[0]["status"] == "FAILS"          # 24'4 + 5'9 = 30'1, not 30'2
    assert rep[0]["residual_in"] == -1          # the exact residual, reported
    assert set(rep[0]["declared_fraction_uncertainty"]) == {"24'-4%\"", "5'-9%\""}


def test_tt_reports_never_gates():
    import inspect
    src = inspect.getsource(og.tt_closure)
    assert "REPORTS, NEVER GATES" in src
