"""SEND-143 PINS — THE NAMES ARE OFF, AND PHASE 2 TRIM READS ONLY WHAT WAS
DRAWN (Howard ruled 2026-08-28).

  ITEM 1  finish the name cleanup: registry keys, the gate value, the
          one-release shim, the two test filenames.
  ITEM 2  turn on the linear runs FROM MARKS ALREADY DRAWN — and where no
          mark exists, print the em dash and NAME the missing mark.
  ITEM 0  (reported, then fixed) the SEND-142 storage move left three
          readers looking for the photo on the pod's disk.

Standing rules these pins hold: CONFIRMED marks only · TAPE GOVERNS · every
row states its basis · a refusal is an em dash, NEVER a 0 · no height is
copied from another wall, photo or estimate · the gable rake is a GABLE-ZONE
run and never joins a wall lane · quantity only, no money.
"""
import math
import pathlib
import sys
import uuid

sys.path.insert(0, "/app/backend")

from fixture_figures import FIXTURE_FIGURES, all_fixture_figures  # noqa: E402
from routes.photo_takeoff import (  # noqa: E402
    TRIM_LABELS, TRIM_ORDER, TRIM_REFUSALS, _gable_rake, _j_channel,
    _quantities, _trim_rows)

BACKEND = pathlib.Path("/app/backend")
ROUTE = (BACKEND / "routes" / "photo_takeoff.py").read_text()
TRIM_JSX = pathlib.Path(
    "/app/frontend/src/components/estimate/phototakeoff/TrimPanel.jsx").read_text()

# a 12 in/px photo: one pixel reads as one foot
IPP = 12.0
SCALE = {"span_px": 10.0, "tape_inches": 120.0}          # 12 in/px, TAPE
BOX = [{"x": 0, "y": 0}, {"x": 3, "y": 0}, {"x": 3, "y": 6}, {"x": 0, "y": 6}]
TRI = [{"x": 0, "y": 10}, {"x": 15, "y": 0}, {"x": 30, "y": 10}]
FLAT = [{"x": 0, "y": 10}, {"x": 15, "y": 10}, {"x": 30, "y": 10}]


def _mark(kind, pts, status="confirmed", **kw):
    return {"id": uuid.uuid4().hex, "kind": kind, "points": pts,
            "status": status, "label": kw.pop("label", kind), **kw}


# ---------------------------------------------------------------------------
# ITEM 1 — NO CUSTOMER NAME IS LEFT IN THE REGISTRY, THE GATE OR THE TREE
# ---------------------------------------------------------------------------
def test_the_registry_keys_are_neutral_and_the_figures_did_not_move():
    assert set(FIXTURE_FIGURES) == {"sealed_hand_takeoff", "sealed_fixture_c",
                                    "sealed_fixture_d", "sealed_fixture_e"}
    # the union the purity pin scans is UNCHANGED by either rename
    assert len(all_fixture_figures()) == 28


def test_the_gate_value_carries_no_customer_name():
    for f in ("routes/lp_package_routes.py", "routes/elevation_sheets.py"):
        src = (BACKEND / f).read_text()
        assert 'est.get("sealed_key") != "sealed_v3"' in src
        assert "letrick_v3" not in src
    docs = (BACKEND / "fixtures" / "docs" / "estimates.json").read_text()
    assert '"sealed_key": "sealed_v3"' in docs and "letrick_v3" not in docs


def test_the_one_release_shim_is_gone_and_nothing_imports_it():
    assert not (BACKEND / "letrick_hand_takeoff_key.py").exists()
    import lp_domain_manifest as M
    assert "letrick_hand_takeoff_key.py" not in M.LP_CORE_MODULES
    assert "sealed_hand_takeoff_key.py" in M.LP_CORE_MODULES
    for py in list(BACKEND.glob("*.py")) + list((BACKEND / "routes").glob("*.py")) \
            + list((BACKEND / "tests").glob("*.py")):
        if py.name == pathlib.Path(__file__).name:
            continue
        src = py.read_text()
        assert "import letrick_hand_takeoff_key" not in src, py.name
        assert "from letrick_hand_takeoff_key" not in src, py.name


def test_the_two_test_files_carry_sealed_names():
    t = BACKEND / "tests"
    assert (t / "test_sealed_item3_chase_ratification.py").exists()
    assert (t / "test_sealed_lap_unification_ruling.py").exists()
    assert not (t / "test_letrick_item3_chase_ratification.py").exists()
    assert not (t / "test_letrick_lap_unification_ruling.py").exists()


# ---------------------------------------------------------------------------
# ITEM 2 — J-CHANNEL IS THE PERIMETER OF THE BOX THE CONTRACTOR DREW
# ---------------------------------------------------------------------------
def test_j_channel_measures_the_drawn_box_and_states_its_basis():
    j = _j_channel([_mark("opening", BOX, label="front window")], IPP)
    assert j["lf"] == 18.0                       # 2 × (3 + 6)
    row = j["rows"][0]
    assert row["lf"] == 18.0 and (row["width_ft"], row["height_ft"]) == (3.0, 6.0)
    assert "perimeter of the box drawn on this photo" in row["basis"]
    assert "3.0 ft × 6.0 ft" in row["basis"] and "18.0 LF" in row["basis"]
    assert row["refusal"] is None


def test_a_tap_opening_refuses_j_channel_by_name_and_never_prints_zero():
    j = _j_channel([_mark("opening", [{"x": 5, "y": 5}], shape="point")], IPP)
    assert j["lf"] is None                       # not 0
    r = j["rows"][0]
    assert r["lf"] is None
    assert "tap with no drawn extent" in r["refusal"] and "box it" in r["refusal"]
    for bad in ("0 LF", "typical", "average", "assume", "another"):
        assert bad not in r["refusal"]


def test_an_unconfirmed_opening_carries_no_linear_run():
    j = _j_channel([_mark("opening", BOX, status="provisional")], IPP)
    assert j["lf"] is None and j["rows"] is None


def test_no_scale_refuses_the_run_and_says_the_box_is_drawn():
    j = _j_channel([_mark("opening", BOX)], None)
    assert j["lf"] is None
    assert "no scale on this photo" in j["rows"][0]["refusal"]


def test_two_boxes_sum_and_a_degenerate_box_refuses():
    marks = [_mark("opening", BOX, label="a"), _mark("opening", BOX, label="b"),
             _mark("opening", [{"x": 0, "y": 0}, {"x": 4, "y": 0},
                               {"x": 8, "y": 0}], label="flat")]
    j = _j_channel(marks, IPP)
    assert j["lf"] == 36.0                       # the two real boxes only
    flat = [r for r in j["rows"] if r["label"] == "flat"][0]
    assert flat["lf"] is None and "encloses nothing" in flat["refusal"]


# ---------------------------------------------------------------------------
# ITEM 2 — THE GABLE RAKE IS THE TWO LINES ALREADY DRAWN, AND IT IS GABLE ZONE
# ---------------------------------------------------------------------------
def test_the_rake_is_the_two_drawn_lines_measured_as_drawn():
    r = _gable_rake([_mark("gable", TRI, label="front gable")], [], IPP)
    expect = round(2 * math.hypot(15.0, 10.0), 2)          # 36.06
    assert r["lf"] == expect
    row = r["rows"][0]
    assert "the two rake lines drawn on this photo" in row["basis"]
    assert "span 30.0 ft" in row["basis"] and "rise 10.0 ft" in row["basis"]
    assert row["refusal"] is None


def test_a_refused_triangle_has_no_rake_and_carries_the_same_reason():
    r = _gable_rake([_mark("gable", FLAT)], [], IPP)
    assert r["lf"] is None                                 # not 0
    assert r["rows"][0]["lf"] is None and r["rows"][0]["refusal"]
    # the gable's OWN refusal rides the rake — one reason, not a second one
    assert "NO RISE" in r["rows"][0]["refusal"]
    assert "never a 0" in r["rows"][0]["refusal"]


def test_the_rake_never_joins_a_wall_lane():
    rows, j, r = _trim_rows([_mark("gable", TRI)], [], IPP)
    by = {x["key"]: x for x in rows}
    assert by["gable_rake"]["zone"] == "gable"
    assert by["gable_rake"]["lf"] is not None
    # a measured rake leaves starter, both corners and J-channel untouched
    for k in ("starter", "outside_corner", "inside_corner", "j_channel"):
        assert by[k]["lf"] is None
    assert j["lf"] is None


# ---------------------------------------------------------------------------
# ITEM 2 — THE FOUR WITH NO MARK TO READ STILL PRINT A ROW, AND NAME IT
# ---------------------------------------------------------------------------
def test_every_trim_howard_named_has_a_row_in_a_fixed_order():
    assert TRIM_ORDER == ("outside_corner", "inside_corner", "j_channel",
                          "starter", "soffit", "fascia", "gable_rake")
    rows, _, _ = _trim_rows([], [], IPP)
    assert [r["key"] for r in rows] == list(TRIM_ORDER)
    assert all(r["label"] == TRIM_LABELS[r["key"]] for r in rows)


def test_the_unsupported_lanes_name_the_missing_mark_and_print_no_zero():
    rows, _, _ = _trim_rows([], [], IPP)
    by = {r["key"]: r for r in rows}
    assert "no wall BASE is marked" in by["starter"]["refusal"]
    assert "may not be read off the plate line or the eave" in by["starter"]["refusal"]
    for k in ("outside_corner", "inside_corner"):
        assert "no corner is marked" in by[k]["refusal"]
        assert "no wall here carries a confirmed height" in by[k]["refusal"]
        assert "No height is copied from another wall" in by[k]["refusal"]
    assert "no EAVE is marked" in by["soffit"]["refusal"]
    assert "not invented" in by["fascia"]["refusal"]
    for k in ("outside_corner", "inside_corner", "starter", "soffit", "fascia"):
        assert by[k]["lf"] is None                        # em dash, never 0
        for bad in ("typical", "average", "assume", "mirror", "0 LF"):
            assert bad not in by[k]["refusal"].lower()


def test_the_starter_lane_still_prints_no_lf_when_a_wall_base_is_tapped():
    """SEND-147 — the starter RUN is not built, but the row must not LIE: with
    a WALL BASE line on the photo it stops saying none is marked and says what
    the line actually is. Still an em dash, still no LF."""
    from routes.photo_takeoff import _trim_rows as tr
    wb = {"kind": "wall_base", "status": "provisional",
          "points": [{"x": 10, "y": 300}, {"x": 900, "y": 302}]}
    row = {r["key"]: r for r in tr([wb], [], IPP)[0]}["starter"]
    assert row["lf"] is None
    assert "a WALL BASE line IS marked on this photo" in row["refusal"]
    assert "ANCHOR ONLY" in row["refusal"] and "NO LF" in row["refusal"]
    assert "no wall BASE is marked" not in row["refusal"]
    for bad in ("typical", "average", "assume", "mirror", "0 LF"):
        assert bad not in row["refusal"].lower()


def test_no_new_mark_type_was_smuggled_in():
    """The trims with no mark are refused BECAUSE the mark does not exist —
    a starter/corner/soffit MARK is still rejected at the door.

    SEND-147 PIN UPDATE, BY NAME: Howard authorised ONE new kind, `wall_base`,
    and it is an ANCHOR, not a trim run — the starter/corner/soffit/fascia
    RUNS are still rejected at the door and the starter LANE still prints an
    em dash."""
    from routes.photo_takeoff import PHASE1_KINDS, PHASE2_KINDS
    assert PHASE1_KINDS == {"siding_zone", "non_siding_zone", "opening",
                            "gable", "dormer", "wall_base"}
    for k in ("outside_corner", "inside_corner", "starter", "soffit",
              "fascia", "j_channel"):
        assert k in PHASE2_KINDS and k not in PHASE1_KINDS
    assert set(TRIM_REFUSALS) == {"outside_corner", "inside_corner", "starter",
                                  "soffit", "fascia"}


# ---------------------------------------------------------------------------
# ITEM 2 — THE LANES RIDE THE QUANTITY PAYLOAD, AND THE WRITE IS QUANTITY ONLY
# ---------------------------------------------------------------------------
def test_the_payload_carries_the_rows_even_with_no_scale_at_all():
    q = _quantities([_mark("opening", BOX), _mark("gable", TRI)], None)
    assert q["j_channel_lf"] is None and q["gable_rake_lf"] is None
    assert [r["key"] for r in q["trim_rows"]] == list(TRIM_ORDER)
    assert "the tape governs" in q["trim_basis_note"]


def test_the_payload_measures_both_lanes_when_the_tape_is_set():
    q = _quantities([_mark("opening", BOX), _mark("gable", TRI)], SCALE)
    assert q["scale_basis"] == "tape"
    assert q["j_channel_lf"] == 18.0
    assert q["gable_rake_lf"] == round(2 * math.hypot(15.0, 10.0), 2)
    # phase 1 did not move: ½ × w × rise still governs the gable ft²
    assert q["gable_sqft"] == 150.0


def test_apply_writes_the_two_lf_keys_and_no_money():
    assert '"photo_j_channel_lf": round(tot_j, 2) if live_j else None' in ROUTE
    assert '"photo_gable_rake_lf": round(tot_rake, 2) if live_rake else None' in ROUTE
    assert '"photo_j_channel_lf": block["photo_j_channel_lf"]' in ROUTE
    # the WRITE carries quantity only — the money tokens are absent from the
    # whole module (the SEND-131A structural rule, re-checked here).
    for banned in ("total_sell", "unit_price", "margin", "sell_price",
               "$ ", "USD", "cost"):
        assert banned not in ROUTE, f"money reached the photo lane: {banned}"
    # "price" survives in the module ONLY inside the sentences that refuse
    # money; no line of CODE reads or writes one.
    for ln in ROUTE.splitlines():
        if "price" in ln.lower() and not ln.strip().startswith(("#", "·", '"')):
            assert ("no price" in ln.lower() or "priced line" in ln.lower()
                    or "no money" in ln.lower()), ln


def test_a_lane_never_defaults_to_zero_in_the_route():
    for bad in ('"j_channel_lf": 0', '"gable_rake_lf": 0',
                '"photo_j_channel_lf": 0', '"photo_gable_rake_lf": 0',
                'j_channel_lf") or 0', 'gable_rake_lf") or 0',
                'tot_j += qty.get("j_channel_lf") or 0'):
        assert bad not in ROUTE, bad
    # and the totals only move behind an explicit `is not None`
    assert 'if qty.get("j_channel_lf") is not None:' in ROUTE
    assert 'if qty.get("gable_rake_lf") is not None:' in ROUTE


# ---------------------------------------------------------------------------
# ITEM 2 — THE ROWS RENDER, WITH THEIR BASIS, AND THE REFUSALS SHOW
# ---------------------------------------------------------------------------
def test_the_trim_panel_prints_every_row_its_basis_and_its_refusal():
    for tid in ("photo-takeoff-trim-panel", "photo-takeoff-trim-row-",
                "photo-takeoff-trim-lf-", "photo-takeoff-trim-basis-",
                "photo-takeoff-trim-refusal-", "photo-takeoff-trim-item-",
                "photo-takeoff-trim-basis-note"):
        assert tid in TRIM_JSX, tid
    # the em dash is the ONLY thing a missing figure may print
    assert 'const lf = (v) => (v == null ? "—" : `${v} LF`);' in TRIM_JSX
    for bad in ("0 LF", "toFixed", "|| 0"):
        assert bad not in TRIM_JSX, bad
    editor = pathlib.Path(
        "/app/frontend/src/components/estimate/PhotoTakeoffEditor.jsx").read_text()
    assert "<TrimPanel qty={qty} />" in editor
    # the rows are never hidden behind a silent null return in the
    # panel itself — the parent mounts it, the panel prints every row
    assert "return null" not in TRIM_JSX


def test_the_panel_decides_nothing_the_server_wrote_the_line():
    """Not one refusal sentence exists in the JSX — the reason cannot be
    re-decided or drift on the client (the SEND-140 rule)."""
    for sentence in TRIM_REFUSALS.values():
        assert sentence[:40] not in TRIM_JSX
    assert "perimeter of the box drawn on this photo" not in TRIM_JSX


# ---------------------------------------------------------------------------
# ITEM 0 — THE SEND-142 REGRESSION: A PHOTO IN OBJECT STORAGE IS READABLE
# ---------------------------------------------------------------------------
def test_the_readers_ask_object_storage_before_giving_up():
    store = (BACKEND / "upload_store.py").read_text()
    assert "from object_storage import get_object, upload_path" in store
    aim = (BACKEND / "routes" / "ai_measure.py").read_text()
    assert aim.count("from upload_store import rehydrate_to_disk") >= 2
    assert "from upload_store import rehydrate_to_disk" in ROUTE
    assert "nothing is placed on a guessed size" in ROUTE


def test_live_a_photo_only_in_object_storage_comes_back():
    """No Mongo blob is written for this name — the bytes can ONLY come
    from object storage, which is where an upload lives since SEND-142."""
    import asyncio

    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
    from config import UPLOAD_DIR
    import object_storage as store
    from upload_store import rehydrate_to_disk

    name = f"pin143_{uuid.uuid4().hex}.png"
    payload = b"\x89PNG\r\n\x1a\n" + b"only-in-object-storage"
    store.put_object(store.upload_path(name), payload, "image/png")
    target = UPLOAD_DIR / name
    assert not target.exists()
    got = asyncio.run(rehydrate_to_disk(name, UPLOAD_DIR))
    try:
        assert got and got.exists()
        assert got.read_bytes() == payload
    finally:
        target.unlink(missing_ok=True)
