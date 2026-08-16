"""SEND-31 (Howard sealed 2026-08-16) — Rulings HH + II pins.

RULING HH — BARE FORM, GATED ON POSITION NOT VALUE. The true 30'-2"
transcribed as bare "30-2" and the text filter rightly refused it
(digits-hyphen-digits swallows dates). The bare form is admitted ONLY
when position already supports it: axis VERTICAL/HORIZONTAL (never
INDETERMINATE), EXTERIOR by the 2D envelope, chain-aligned with a
fully-marked dimension of the same axis, AND inch component <= 11 (the
notation itself cannot carry 12+ inches — not a picked threshold).
POSITIONS DISAMBIGUATE, VALUES DO NOT. No envelope -> nothing admitted.

RULING II — SCALE NOTES OUT OF RAIL CANDIDACY. A rail candidate carries
NO alphabetic characters beyond the foot/inch marks. SCALE:3/16"=1'-0"
fails on "SCALE" alone. One structural property — deliberately NOT a
blocklist of note types.

ITEM 3 — p6 LEFT prints 30'-0" (Howard read the sheet); p4 prints
30'-2". Two sheets DISAGREE by 2" on one wall. The disagreement is
REPORTED — never averaged, never resolved toward either sheet.
"""
import sys

sys.path.insert(0, "/app/backend")

import ocr_geometry as og


def _run(raw, x, y, w, h, axis, src="upright"):
    return {"norm": raw, "raw": raw,
            "loc": {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h},
            "src": src, "axis": axis}


def _p4_like_fixture():
    """The Foundation-Plan shape: marked rails on all four sides, the
    true left depth present only as bare '30-2' outboard of the marked
    left chain mate 5'10°."""
    return [
        _run("58'-0*", 50.0, 25.0, 1.5, 1.0, og.HORIZONTAL),   # top width rail
        _run("58'-0*", 50.0, 75.0, 1.5, 1.0, og.HORIZONTAL),   # bottom width rail
        _run("5'10°", 20.41, 68.38, 0.55, 1.4, og.VERTICAL),   # marked left chain
        _run("33-0*", 78.98, 50.89, 0.71, 1.73, og.VERTICAL),  # right depth rail
        _run("30-2", 20.33, 49.6, 0.55, 1.53, og.VERTICAL),    # bare true depth
        _run("GARAGE", 66.0, 44.0, 2.0, 1.0, og.HORIZONTAL),
    ]


# ---------------------------------------------------------------------------
# RULING HH — the gate
# ---------------------------------------------------------------------------

def test_hh_bare_form_parses_and_dates_never_do():
    assert og.parse_bare_form("30-2") == (30, 2)
    assert og.parse_bare_form(" 33-11 ") == (33, 11)
    assert og.parse_bare_form("03-26-26") is None   # two hyphens — a date
    assert og.parse_bare_form("30-2*") is None      # marked forms go the marked path
    assert og.parse_bare_form("SCALE") is None


def test_hh_admits_the_true_depth_that_recovered_the_thread():
    adm = og.gated_bare_form_admissions(_p4_like_fixture())
    assert adm["envelope_status"] == "ESTABLISHED"
    raws = [a["run"]["raw"] for a in adm["admitted"]]
    assert raws == ["30-2"]
    a = adm["admitted"][0]
    assert (a["feet"], a["inches"]) == (30, 2)
    assert a["chain_mate"] == "5'10°"


def test_hh_inch_component_over_11_is_refused():
    # Feet-and-inches notation cannot carry 12+ inches — 26 inches is a
    # date fragment (3-26), never a dimension.
    runs = _p4_like_fixture()
    runs.append(_run("3-26", 20.35, 55.0, 0.55, 1.5, og.VERTICAL))
    raws = [a["run"]["raw"] for a in og.gated_bare_form_admissions(runs)["admitted"]]
    assert "3-26" not in raws
    assert "30-2" in raws


def test_hh_interior_bare_form_is_refused():
    runs = _p4_like_fixture()
    runs.append(_run("12-6", 50.0, 50.0, 0.55, 1.5, og.VERTICAL))  # dead center
    raws = [a["run"]["raw"] for a in og.gated_bare_form_admissions(runs)["admitted"]]
    assert "12-6" not in raws


def test_hh_indeterminate_axis_is_refused():
    runs = _p4_like_fixture()
    runs.append(_run("11-6", 20.35, 55.0, 0.55, 1.5, og.INDETERMINATE))
    raws = [a["run"]["raw"] for a in og.gated_bare_form_admissions(runs)["admitted"]]
    assert "11-6" not in raws


def test_hh_no_chain_mate_is_refused():
    # Exterior and vertical but alone on its column — not on a chain.
    runs = _p4_like_fixture()
    runs.append(_run("10-6", 10.0, 40.0, 0.55, 1.5, og.VERTICAL))
    raws = [a["run"]["raw"] for a in og.gated_bare_form_admissions(runs)["admitted"]]
    assert "10-6" not in raws


def test_hh_no_envelope_admits_nothing_never_a_default():
    runs = [_run("30-2", 20.33, 49.6, 0.55, 1.53, og.VERTICAL),
            _run("5'10°", 20.41, 68.38, 0.55, 1.4, og.VERTICAL)]
    adm = og.gated_bare_form_admissions(runs)
    assert adm["envelope_status"] == og.INDETERMINATE
    assert adm["admitted"] == []


def test_hh_probe_left_now_returns_the_admitted_depth_and_reports_it():
    rep = og.positional_rule_probe(_p4_like_fixture())
    assert rep["binds"] is False
    assert [g["raw"] for g in rep["gated_bare_admitted"]] == ["30-2"]
    left = rep["sides"]["left"]
    assert left["chosen"]["raw"] == "30-2"
    # The marked chain mate is visible in contention, not erased.
    assert "5'10°" in [c["raw"] for c in left["contenders"]]
    # RIGHT is untouched by the admission.
    assert rep["sides"]["right"]["chosen"]["raw"] == "33-0*"


# ---------------------------------------------------------------------------
# RULING II — rail candidacy
# ---------------------------------------------------------------------------

def test_ii_scale_note_is_never_a_rail():
    assert og.is_rail_candidate("SCALE:3/16\"=1'-0\"") is False
    assert og.is_rail_candidate("58-0°") is True
    assert og.is_rail_candidate("5'10°") is True
    # The door-size annotation carries an alphabetic 'x' — not a rail.
    assert og.is_rail_candidate("16'-0°x8-0*") is False
    # Structural, not a blocklist: any note text fails the same way.
    assert og.is_rail_candidate("MIN.9'-11/8\"CEILINGHEIGHT") is False


def test_ii_envelope_bottom_rail_recovers_the_true_width_rail():
    runs = _p4_like_fixture()
    # The polluter from the live sheets: the SCALE note BELOW the true
    # bottom rail. Before II it became the bottom rail and inflated y_hi.
    runs.append(_run("SCALE:3/16\"=1'-0\"", 32.0, 80.0, 6.8, 1.06,
                     og.HORIZONTAL))
    env = og.rail_envelope(runs)
    assert env["status"] == "ESTABLISHED"
    assert env["rails"]["bottom"] == "58'-0*"
    assert env["y_hi"] == 75.0


def test_ii_alphabetic_dims_still_class_interior_exterior():
    # II removes notes from RAIL CANDIDACY only — a dimension-like note
    # still gets an interior/exterior verdict against the envelope.
    runs = _p4_like_fixture()
    env = og.rail_envelope(runs)
    note = _run("MIN.9'-11/8\"CEILINGHEIGHT", 45.0, 50.0, 10.0, 1.0,
                og.HORIZONTAL)
    assert og.interior_exterior(note, env) == og.INTERIOR


def test_ii_rails_all_alphabetic_means_indeterminate():
    runs = [
        _run("SCALE:3/16\"=1'-0\"", 32.0, 80.0, 6.8, 1.06, og.HORIZONTAL),
        _run("MIN.9'-11/8\"CEILING", 40.0, 20.0, 10.0, 1.0, og.HORIZONTAL),
        _run("30-2", 20.33, 49.6, 0.55, 1.53, og.VERTICAL),
        _run("33-0", 78.98, 50.89, 0.71, 1.73, og.VERTICAL),
    ]
    env = og.rail_envelope(runs)
    assert env["status"] == og.INDETERMINATE
