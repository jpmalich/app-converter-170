"""SEND-117 pins (Howard authorized 2026-08-23) —
ITEM 1: rotation detect + normalize (the cut from the observed gap;
indeterminate is never normalized on a guess; Boni/Letrick must not move).
ITEM 2: aggregation-born refusals get rails (grouped, never noise).
ITEM 3: the marks-as-1 floors' unreachability PINNED — a property of
current callers outlives its reasoning only if a pin fails when the
collapse case becomes reachable."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import page_rotation  # noqa: E402
from routes.ai_blueprint import check_read_consistency  # noqa: E402


# ---------------------------------------------------------------- ITEM 1
def test_bands_come_from_the_observed_gap_not_round_numbers():
    """Rotated pages observed 6.0–24.6% upright; upright pages 33.9–52.3%.
    The cut sits inside the 24.6→33.9 gap."""
    assert 24.6 < page_rotation.ROTATED_MAX_SHARE < 33.9
    assert 24.6 < page_rotation.UPRIGHT_MIN_SHARE <= 33.9
    assert page_rotation.ROTATED_MAX_SHARE < page_rotation.UPRIGHT_MIN_SHARE


def test_verdicts_reproduce_all_32_observed_pages():
    # dart p5/p6 (rotated), dart p8 (in the gap), Boni p8 / Letrick p3
    # (the tightest upright pages) — the exact stored counts.
    v = page_rotation.rotation_verdict({"upright": 11, "rot90": 32, "rot270": 72})
    assert v["verdict"] == "ROTATED" and v["rotation_ccw"] == 270
    v = page_rotation.rotation_verdict({"upright": 8, "rot90": 38, "rot270": 87})
    assert v["verdict"] == "ROTATED" and v["rotation_ccw"] == 270
    v = page_rotation.rotation_verdict({"upright": 10, "rot90": 9, "rot270": 11})
    assert v["verdict"] == "INDETERMINATE", "dart p8 (33.3%) sits IN the gap"
    assert v["rotation_ccw"] is None, "never normalized on a guess"
    v = page_rotation.rotation_verdict({"upright": 115, "rot90": 114, "rot270": 110})
    assert v["verdict"] == "UPRIGHT", "Boni p8 at 33.9% stays upright"
    v = page_rotation.rotation_verdict({"upright": 140, "rot90": 144, "rot270": 129})
    assert v["verdict"] == "UPRIGHT", "Letrick p3 (rot90 ahead by noise) stays"


def test_180_is_not_independently_detectable_and_never_guessed():
    """No rot180 pass exists. An upside-down sheet reads garbage in ALL
    passes — it lands INDETERMINATE via the signal floor or the gap,
    never a guessed correction. And the math holds: share ≤ 25% forces
    the winning rot pass ≥ 1.5× upright, so no low-share page with
    signal escapes undetected."""
    v = page_rotation.rotation_verdict({"upright": 3, "rot90": 4, "rot270": 4})
    assert v["verdict"] == "INDETERMINATE" and v["rotation_ccw"] is None
    v = page_rotation.rotation_verdict({"upright": 5, "rot90": 6, "rot270": 6})
    assert v["verdict"] == "INDETERMINATE" and v["rotation_ccw"] is None
    for up, r90, r270 in ((4, 6, 6), (10, 15, 16), (1, 20, 2)):
        share = 100 * up / (up + r90 + r270)
        if share <= page_rotation.ROTATED_MAX_SHARE:
            assert max(r90, r270) >= page_rotation.ROT_DOMINANCE * up


def test_low_signal_page_is_indeterminate():
    v = page_rotation.rotation_verdict({"upright": 2, "rot90": 3, "rot270": 4})
    assert v["verdict"] == "INDETERMINATE"


def test_box_remap_round_trips_and_relabels():
    loc = {"x_pct": 85.0, "y_pct": 58.7, "w_pct": 1.1, "h_pct": 11.9}
    r = page_rotation.remap_loc_ccw(loc, 270)
    # CCW270: new_x = 100 − y − h, new_y = x, dims swap
    assert r == {"x_pct": 29.4, "y_pct": 85.0, "w_pct": 11.9, "h_pct": 1.1}
    back = page_rotation.remap_loc_ccw(r, 90)
    assert back == loc, "90 undoes 270"
    runs = [{"src": "rot270", "loc": loc, "raw": "T"},
            {"src": "upright", "loc": loc, "raw": "U"}]
    nr = page_rotation.normalize_runs(runs, 270)
    assert nr[0]["src"] == "upright", "the winning pass becomes upright"
    assert nr[1]["src"] == "rot90"
    assert runs[0]["src"] == "rot270", "the store itself is never mutated"


# ---------------------------------------------------------------- ITEM 2
DART_SHAPE = {
    "walls": [
        {"label": "front", "width_ft": 62, "height_ft": None},
        {"label": "back", "width_ft": 62, "height_ft": None},
        {"label": "left", "width_ft": None, "height_ft": None},
        {"label": "right", "width_ft": None, "height_ft": None},
    ],
    "windows": [{"id": m, "qty": 1} for m in "ABCDEFGHJ"],
    "doors": [{"id": "1", "qty": 1, "exterior_evidence": "schedule_row"},
              {"id": "2", "qty": 1, "exterior_evidence": "schedule_row"},
              {"id": "GARAGE", "qty": 1,
               "exterior_evidence": "schedule_row"}],
}


def _by_code(flags):
    return {f["code"]: f for f in flags}


def test_fully_refused_house_rails_grouped_not_noise():
    flags = _by_code(check_read_consistency(dict(DART_SHAPE)))
    f = flags["faces_refused"]
    assert f["vars"]["count"] == 4
    assert f["vars"]["faces"] == "back, front, left, right"
    s = flags["opening_sizes_refused"]
    assert s["vars"]["count"] == 12, "9 windows + 3 doors, ONE row"
    d = flags["deduction_refused"]
    assert d["vars"]["rows"] == 12 and "back" in d["vars"]["faces"]
    n_refusal_rows = sum(1 for c in flags if c in (
        "faces_refused", "opening_sizes_refused", "deduction_refused"))
    assert n_refusal_rows == 3, "grouped — never one rail per refusal"


def test_clean_house_adds_no_refusal_rails():
    flags = _by_code(check_read_consistency({
        "walls": [{"label": "front", "width_ft": 40, "height_ft": 10},
                  {"label": "back", "width_ft": 40, "height_ft": 10}],
        "windows": [{"id": "A", "qty": 1, "width_in": 36, "height_in": 60}]}))
    for code in ("faces_refused", "opening_sizes_refused",
                 "deduction_refused", "page_rotation_normalized",
                 "page_rotation_indeterminate"):
        assert code not in flags


def test_rotation_rails_fire_from_the_page_rotation_record():
    flags = _by_code(check_read_consistency({
        "walls": [{"label": "front", "width_ft": 40, "height_ft": 10}],
        "_page_rotation": [
            {"page": 1, "verdict": "ROTATED", "rotation_ccw": 270},
            {"page": 2, "verdict": "UPRIGHT"},
            {"page": 3, "verdict": "INDETERMINATE"}]}))
    assert flags["page_rotation_normalized"]["vars"]["pages"] == "1"
    assert flags["page_rotation_indeterminate"]["vars"]["pages"] == "3"


def test_rail_copy_exists_en_and_es():
    src = (Path(__file__).resolve().parents[2]
           / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")
    for key in ("faces_refused", "opening_sizes_refused", "deduction_refused",
                "page_rotation_normalized", "page_rotation_indeterminate"):
        hits = re.findall(rf'"bp\.rb\.consistency\.{key}":', src)
        assert len(hits) == 2, f"{key}: EN + ES"


# ---------------------------------------------------------------- ITEM 3
def test_marks_as_1_collapse_case_stays_unreachable():
    """THE UNREACHABILITY PIN. The three max(1, qty or 1) floors are safe
    ONLY while no governed row can reach them with a falsy qty. The
    parser's guarantee: under a COUNT column's jurisdiction, every
    governed row ends with qty ≥ 1 OR _count_unread (qty 0, skipped
    upstream of the floor). If this pin fails, the collapse case became
    reachable and the floors are live marks-as-1 again."""
    from tests.test_schedule_row_parser_2026_08_23_send114 import (
        _u, _window_table)
    from schedule_read import read_schedule_counts
    raw = {"windows": [
        {"id": "A", "qty": 9, "count_by_page": None},
        {"id": "B", "qty": 9, "count_by_page": None},
    ], "_ocr_text_by_page": _window_table([_u("2", 26, 53)])}
    read_schedule_counts(raw)
    for w in raw["windows"]:
        q = w.get("qty")
        assert (isinstance(q, int) and q >= 1) or w.get("_count_unread"), \
            f"mark {w['id']}: a governed row left qty={q!r} without " \
            f"_count_unread — the marks-as-1 floor is reachable"
    b = next(w for w in raw["windows"] if w["id"] == "B")
    assert b.get("_count_unread") and b.get("qty") == 0
