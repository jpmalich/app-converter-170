"""CORNER + GUTTER RULINGS (Howard ruled 2026-08-06, Boni EST-886440
send — evidence only, no figure from that send appears here).

1. STOP AVERAGING CORNER HEIGHTS: when a door read per-corner
   dimensions, each corner takes ceil(its OWN trim height / stick),
   min 1. The corner takes the TALLER of its two walls (prompt-side).
   An undimensioned corner holds 1 stick and KEEPS ITS FLAG — never
   averaged, never silently defaulted. Off-path fallbacks unchanged.
2. GUTTER RUN INVENTORY: the gutter line consumes the door's run list
   when present and DISCLOSES it on the note; eaves LF stays the
   unchanged fallback and the soffit figure.
3. PURITY EXTENSION (rider #5): the new corner-height and gutter code
   is pure, idempotent, non-mutating, and carries no constants from
   the evidence send.
"""
import copy
import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

from routes.hover import (  # noqa: E402
    _build_lines, _gutter_lf, _gutter_note, _gutter_run_list,
    _osc_corner_heights, _osc_heights_note, _osc_lp_pcs,
    _osc_per_corner_pcs,
)

BASE = {"siding_with_openings_sqft": 2000, "eaves_lf": 120, "rakes_lf": 80,
        "window_count": 6, "door_count": 2}


def _row(lines, tab, frag):
    for l in lines:
        if (l.get("tab") or "vinyl") == tab and frag.lower() in str(
                l.get("item") or l.get("name") or "").lower():
            return l
    return None


# ═════════════ per-corner heights govern the corner line ════════════════
def test_per_corner_heights_govern_the_vinyl_corner_line():
    m = {**BASE, "outside_corner_count": 4, "outside_corner_lf": 52,
         "_osc_corner_heights_ft": [8, 14, 20, 10],
         "_osc_heights_source": "blueprint_dimensioned"}
    row = _row(_build_lines(m), "vinyl", "Outside corners")
    # ceil(8/12.5)=1, ceil(14/12.5)=2, ceil(20/12.5)=2, ceil(10/12.5)=1
    assert row["qty"] == 6, "each corner takes its OWN height, never a pool"
    assert "TALLER" in row["note"] and "12.5" in row["note"]
    assert "dimensioned elevations" in row["note"]
    # the pool would have said ceil(52/12.5)=5 — the average hides sticks
    assert row["qty"] != 5


def test_ascend_corner_line_takes_the_same_per_corner_math():
    m = {**BASE, "outside_corner_count": 4, "outside_corner_lf": 52,
         "_osc_corner_heights_ft": [8, 14, 20, 10],
         "_osc_heights_source": "blueprint_dimensioned"}
    row = _row(_build_lines(m), "ascend", "Outside Corner")
    assert row["qty"] == 6


def test_lp_corner_line_per_corner_heights_with_16ft_stick():
    m = {**BASE, "outside_corner_count": 4, "outside_corner_lf": 52,
         "_osc_corner_heights_ft": [8, 14, 20, 10]}
    assert _osc_lp_pcs(m) == 1 + 1 + 2 + 1  # only the 20' corner splits at 16'


def test_taped_tall_corners_still_win_over_door_read_heights():
    """Human overrides are absolute — taped heights keep governing LP."""
    m = {**BASE, "outside_corner_count": 2, "outside_corner_lf": 30,
         "_osc_corner_heights_ft": [9, 9],
         "_osc_tall_corners_ft": [20.0]}
    # taped path: 1 tall ceil(20/16)=2 + 1 rest ceil(10/16)=1 → 3
    assert _osc_lp_pcs(m) == 3


def test_undimensioned_corner_keeps_its_flag_never_defaulted():
    m = {**BASE, "outside_corner_count": 3, "outside_corner_lf": 40,
         "_osc_corner_heights_ft": [8, None, 14],
         "_osc_heights_source": "blueprint_dimensioned"}
    assert _osc_per_corner_pcs(m, 12.5) == 1 + 1 + 2
    note = _osc_heights_note(m, 12.5)
    assert "UNDIMENSIONED" in note and "flag stands" in note
    assert "never averaged" in note


def test_photo_door_heights_present_as_estimate_never_taped():
    m = {**BASE, "_osc_corner_heights_ft": [9, 9],
         "_osc_heights_source": "photo_ai"}
    note = _osc_heights_note(m, 12.5)
    assert "AI ESTIMATE" in note and "VERIFY" in note
    assert "taped" not in note.replace("never taped", "")


def test_no_heights_falls_back_byte_identical():
    m = {**BASE, "outside_corner_count": 4, "outside_corner_lf": 52}
    row = _row(_build_lines(m), "vinyl", "Outside corners")
    assert row["qty"] == 5  # ceil(52/12.5) — unchanged pooled fallback
    assert row["note"] == \
        "Vinyl 12.5' outside-corner pieces (HOVER LF ÷ 12.5, round up)"


# ═════════════ gutter run inventory + disclosure ════════════════════════
def test_gutter_consumes_the_run_inventory_and_discloses_it():
    m = {**BASE, "_gutter_runs": [
        {"label": "front", "lf": 40}, {"label": "back", "lf": 40},
        {"label": "porch", "lf": 12}]}
    row = _row(_build_lines(m), "vinyl", "Gutter 6")
    assert row["qty"] == 92, "gutter = sum of runs, not the eave plane-sum"
    assert "Run inventory: front 40' + back 40' + porch 12'" in row["note"]
    assert "soffit figure" in row["note"]


def test_gutter_without_runs_is_byte_identical():
    row = _row(_build_lines(dict(BASE)), "vinyl", "Gutter 6")
    assert row["qty"] == 120
    assert row["note"] == "Eaves LF × 1 run (gutters run along eaves, not rakes)"


def test_soffit_keeps_the_eave_plane_sum_even_when_runs_exist():
    """Runs govern GUTTER only — soffit lives under every eave."""
    m = {**BASE, "_gutter_runs": [{"label": "front", "lf": 40}]}
    j = _row(_build_lines(m), "vinyl", "Soffit J-Channel")
    j_base = _row(_build_lines(dict(BASE)), "vinyl", "Soffit J-Channel")
    assert j["qty"] == j_base["qty"], "soffit consumers must not follow runs"


# ═════════════ prompt-side pins ═════════════════════════════════════════
def test_blueprint_prompts_ask_for_heights_and_runs():
    src = (Path(__file__).resolve().parents[1] / "routes"
           / "ai_blueprint.py").read_text()
    assert src.count("outside_corner_heights_ft") >= 4
    assert src.count("gutter_runs") >= 4
    assert "TALLER" in src, "corner takes the taller of its two walls"
    assert "run to the EAVE" in src, "gable corners run to the eave — " \
        "never an area÷width figure (the naive gable case)"
    assert "counted ONCE" in src, "a bump-out eave never re-lists the " \
        "run it already sits inside"


def test_roof_pass_merge_accepts_heights_and_runs_conservatively():
    from routes.ai_blueprint import _merge_roof_pass
    # AGREEMENT-OR-FLAG (ruled 2026-08-10): heights ride only when the
    # two walks AGREE (or the primary had none). Counts here agree (4/0).
    raw = {"roof_planes": [{"label": "main", "eave_lf": 50}],
           "outside_corner_count": 4}
    rp = {"outside_corner_count": 4, "inside_corner_count": 0,
          "outside_corner_lf": 60,
          "outside_corner_heights_ft": [8, 8, 12, 12],
          "gutter_runs": [{"label": "front", "lf": 40}]}
    out = _merge_roof_pass(dict(raw), dict(rp))
    assert out["outside_corner_heights_ft"] == [8, 8, 12, 12]
    assert out["gutter_runs"] == [{"label": "front", "lf": 40}]
    # heights refused when the list doesn't cover the counted corners
    rp_bad = {**rp, "outside_corner_heights_ft": [8, 8]}
    out2 = _merge_roof_pass(dict(raw), dict(rp_bad))
    assert "outside_corner_heights_ft" not in out2
    # a DISAGREEING walk keeps the primary and never carries its heights
    rp_conflict = {**rp, "outside_corner_count": 6,
                   "inside_corner_count": 2,
                   "outside_corner_heights_ft": [8, 8, 12, 12, 10, 10]}
    out3 = _merge_roof_pass(dict(raw), dict(rp_conflict))
    assert out3["outside_corner_count"] == 4
    assert "outside_corner_heights_ft" not in out3
    assert out3["_corner_walk_conflict"]["roof_pass"]["out"] == 6


# ═════════════ purity extension (rider #5) ══════════════════════════════
def test_corner_and_gutter_code_is_pure_and_carries_no_evidence_constants():
    srcs = "".join(inspect.getsource(f) for f in (
        _osc_corner_heights, _osc_per_corner_pcs, _osc_heights_note,
        _gutter_run_list, _gutter_lf, _gutter_note))
    assert "db." not in srcs and "await " not in srcs
    nums = {float(n) for n in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)", srcs)}
    barred = {58.0, 89.0, 167.0, 126.0, 198.0, 11.0,
              9.92, 5.67, 15.5, 18.0}
    hits = nums & barred
    assert not hits, f"evidence-send figure hardcoded into general code: {hits}"


def test_corner_and_gutter_helpers_idempotent_and_non_mutating():
    m = {"_osc_corner_heights_ft": [7.5, None, 14.0, 20.0],
         "_gutter_runs": [{"label": "front", "lf": 40},
                          {"label": "back", "lf": 40}],
         "eaves_lf": 95}
    snap = copy.deepcopy(m)
    assert _osc_per_corner_pcs(m, 12.5) == _osc_per_corner_pcs(m, 12.5) == 6
    assert _gutter_lf(m) == _gutter_lf(m) == 80.0
    assert _osc_heights_note(m, 12.5) == _osc_heights_note(m, 12.5)
    assert m == snap, "helpers must never mutate their input"
