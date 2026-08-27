"""SEND-138 PINS — THE GABLE RE-SEAL (Howard ruled 2026-08-27).

  Re-seal the 367.5 hand takeoff to the triangle.
  367.5 was written as w × h × 0.70. The sealed number is now the same
  walls at ½ × width × rise.  367.5 × (0.5/0.7) = 262.5
  Register 262.5 as the sealed gable total for that takeoff.
  367.5 is retired as a target. Nothing tunes toward 367.5.

  (And: do NOT rederive the eleven 0.70 estimates. No sweep.)

NO JOB NAME IS INTRODUCED. These pins speak of THE SEALED FIXTURE and
reach it through the portable `sealed_key` flag and the key module that
already existed; no customer name is added to code by this send, and a
pin below enforces that.
"""
import pathlib
import sys

sys.path.insert(0, "/app/backend")

from letrick_hand_takeoff_key import LETRICK_HAND_TAKEOFF_KEY as SEALED

KEY_MODULE = pathlib.Path("/app/backend/letrick_hand_takeoff_key.py")
CONSUMER = pathlib.Path("/app/backend/routes/lp_package_routes.py")


# ---------------------------------------------------------------------------
# 1. THE SEALED GABLE TOTAL IS 262.5, AND IT IS A REGISTERED VALUE
# ---------------------------------------------------------------------------
def test_the_sealed_gable_total_is_registered_at_262_5():
    """It is a VALUE on the sealed fixture, not a remark in a comment —
    a figure nothing reads cannot be re-sealed."""
    assert SEALED["inputs"]["gables_sqft"] == 262.5


def test_the_two_faces_and_their_width_times_rise_produce_it():
    """Two gable ends, one per side face, each 30.0' wide × 8.75' rise."""
    per_end = 0.5 * 30.0 * 8.75
    assert per_end == 131.25
    assert 2 * per_end == SEALED["inputs"]["gables_sqft"]
    # Howard's own arithmetic, to the penny.
    assert round(367.5 * (0.5 / 0.7), 4) == 262.5


def test_the_faces_are_confirmed_by_the_seals_own_rakes():
    """The seal proves its own gable geometry: 4 rakes = 2 gable ends, and
    the rake length reproduces the 15' half-width and the 8.75' rise. No
    outside read is borrowed to justify the re-seal."""
    inp = SEALED["inputs"]
    assert inp["rakes_lf"] == 69.6                 # 4 × 17.4
    rake = (15.0 ** 2 + 8.75 ** 2) ** 0.5          # half-width, rise
    assert abs(rake - 17.4) < 0.05
    assert abs(4 * rake - inp["rakes_lf"]) < 0.2


def test_the_basis_states_the_formula_and_the_two_ends():
    b = SEALED["bases"]["gables_sqft"]
    assert b["basis"] == "DERIVED"
    f = b["formula"]
    assert "2 gable ends" in f and "½ × 30.0'" in f and "8.75'" in f
    assert "262.5" in f
    assert "retired as a target" in f


# ---------------------------------------------------------------------------
# 2. 367.5 IS RETIRED AS A TARGET — NOTHING EXPECTS IT
# ---------------------------------------------------------------------------
def test_no_sealed_value_and_no_consumer_still_carries_367_5():
    """367.5 may appear only where it is NAMED AS RETIRED history, never
    as a live figure a surface reads or a pin expects."""
    for v in SEALED["inputs"].values():
        assert v != 367.5
    for line in SEALED["lines"]:
        assert line.get("qty") != 367.5
    src = CONSUMER.read_text()
    # the consumer keeps NO copy of the figure; where the number appears at
    # all it appears inside the sentence that RETIRES it.
    assert '"sqft": 367.5' not in src
    for ln in src.splitlines():
        if "367.5" in ln:
            assert "0.70-era" in ln and "retired" in src[src.index(ln):
                                                        src.index(ln) + 400]
    hist = KEY_MODULE.read_text()
    for marker in ("367.5 → 262.5", "the 0.70-era gable"):
        assert marker in hist            # retired, and recorded as retired


def test_the_consumer_reads_the_sealed_value_never_a_second_copy():
    src = CONSUMER.read_text()
    assert 'inp["gables_sqft"]' in src


# ---------------------------------------------------------------------------
# 3. THE DEPENDENTS MOVED WITH IT — A DERIVED TOTAL MAY NOT OUTLIVE ITS INPUT
# ---------------------------------------------------------------------------
def test_the_raw_total_sums_the_re_sealed_components():
    inp = SEALED["inputs"]
    assert inp["walls_gables_sqft"] == 1842.3
    assert inp["raw_sqft"] == 1994.7
    assert abs(inp["walls_gables_sqft"] + inp["chase_outer_sqft"]
               + inp["chase_sides_sqft"] - inp["raw_sqft"]) <= 0.05
    # the gable is the ONLY thing that moved: chase figures untouched.
    assert inp["chase_outer_sqft"] == 51.37
    assert inp["chase_sides_sqft"] == 101.02


def test_the_sealed_lap_line_re_derives_from_the_new_raw():
    import math
    inp = SEALED["inputs"]
    lap = next(l for l in SEALED["lines"] if "38 Series Lap" in l["item"])
    squares = inp["raw_sqft"] / 100.0
    assert lap["qty"] == math.ceil(squares * (1 + inp["waste"]) * 11)
    assert lap["qty"] == 242


def test_nothing_but_area_moved_in_the_seal():
    """LF and count lines read no gable area and must be UNCHANGED."""
    inp = SEALED["inputs"]
    assert (inp["eaves_lf"], inp["rakes_lf"], inp["fascia_rake_lf"],
            inp["perimeter_lf"], inp["starter_lf"]) == (
                108.0, 69.6, 177.6, 168.0, 165.0)
    qty = {l["item"]: l["qty"] for l in SEALED["lines"]}
    assert qty["540 Series OSC 5/4\" x 6\" x 16'"] == 8
    assert qty["440 Series 4/4\" x 4\" ISC"] == 2
    assert qty["LP Soffit"] == 108


# ---------------------------------------------------------------------------
# 4. NO JOB NAME ENTERS CODE, AND NO SWEEP HAPPENED
# ---------------------------------------------------------------------------
def test_this_pin_file_names_no_customer_and_the_gate_stays_portable():
    """The fixture is reached by the portable `sealed_key` flag, never by
    matching an estimate number or a customer name at runtime."""
    src = CONSUMER.read_text()
    assert 'est.get("sealed_key") != "letrick_v3"' in src
    assert "customer_name" not in src.split("_apply_key_bound_areas")[1][:2000]
    # This file refers to THE SEALED FIXTURE. The legacy name may appear
    # ONLY where the pre-existing module is imported or its path named —
    # no new customer name is introduced by this send.
    needle = "letr" + "ick"          # built, so this line is not a hit
    for ln in pathlib.Path(__file__).read_text().splitlines():
        if needle in ln.lower() and "needle" not in ln:
            assert ("import" in ln or "KEY_MODULE" in ln
                    or "sealed_key" in ln
                    or f"{needle}_hand_takeoff_key.py" in ln), ln
    assert "SEALED FIXTURE" in pathlib.Path(__file__).read_text()


def test_the_ruling_against_the_rederive_sweep_is_recorded():
    """Ruling 1 of SEND-138: the eleven 0.70 estimates are NOT rederived.
    Nothing in the tree performs a bulk gable rewrite."""
    for p in pathlib.Path("/app/backend/routes").glob("*.py"):
        src = p.read_text()
        for bad in ("update_many", "rederive_all", "gable_sweep"):
            if bad in src:
                assert "gable" not in src.split(bad)[0][-400:].lower(), (
                    f"{p.name}: a bulk write sits next to gable logic")
