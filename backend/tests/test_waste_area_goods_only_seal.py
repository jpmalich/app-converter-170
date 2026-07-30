"""WASTE MULTIPLIES AREA GOODS ONLY — SEALED (Howard, ruled 2026-07-29).

THE SEAL: any row whose count method is whole-stick-per-run,
whole-stick-per-corner or whole-stick-per-segment (LENGTH-CUT GOODS) is
waste-included BY CONSTRUCTION — the whole-stick count already contains
the scrap; a percentage on top buys sticks nobody cuts. The contractor's
waste field multiplies AREA GOODS only (panels, lap, soffit, wrap),
every family, BOTH doors. Battens carry 0% waste, NO breakage allowance
(ruling b — battens do not break).

THE DETECTOR: fails on any length-cut row missing `_waste_included` —
the check that would have caught the default-lap double-bake (item 4 of
the waste-model report) without Howard asking for it.
"""
import inspect
import math
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FRONTEND_SRC = Path("/app/frontend/src")

# Length-cut name classes — whole-stick counted rows, every family.
_LENGTH_CUT_PAT = re.compile(
    r"outside corner|inside corner|\bosc\b|j-channel|j - channel|"
    r"finish trim|starter|440 series|540 series|190 series",
    re.I)


def _is_length_cut(line: dict) -> bool:
    return (str(line.get("unit") or "").upper() == "PCS"
            and bool(_LENGTH_CUT_PAT.search(str(line.get("name") or ""))))


def _rich_measurements(**over):
    m = {
        "siding_sqft": 2000.0, "siding_with_openings_sqft": 2000.0,
        "outside_corner_lf": 142.0, "outside_corner_count": 15,
        "inside_corner_count": 4, "inside_corner_lf": 36.0,
        "eaves_lf": 120.0, "rakes_lf": 80.0, "starter_lf": 160.0,
        "window_count": 10, "entry_door_count": 2, "garage_door_count": 1,
        "patio_door_count": 1, "_hover_source": True,
    }
    m.update(over)
    return m


# ── THE DETECTOR — every length-cut row carries the flag, both doors ─────
def test_detector_every_length_cut_row_flagged():
    from routes.hover import _build_lines
    shapes = [
        _rich_measurements(),                                     # Hover, no breakdown
        _rich_measurements(_per_profile_sqft={"board_batten": 2000.0},
                           _waste_pct=0.30, _default_family="board_batten"),
        _rich_measurements(_per_profile_sqft={"lap": 1500.0, "shake": 500.0},
                           _waste_pct=0.10),                      # multi-profile
        _rich_measurements(_per_profile_sqft={"lap": 1200.0, "board_batten": 800.0},
                           _per_profile_base_lf={"lap": 90.0, "board_batten": 50.0},
                           _waste_pct=0.10),                      # region split rows
    ]
    naked = []
    for m in shapes:
        for l in _build_lines(dict(m)):
            if _is_length_cut(l) and not l.get("_waste_included"):
                naked.append(f"{l.get('tab')}/{l.get('name')}")
    assert not naked, (
        "LENGTH-CUT row(s) missing _waste_included (waste multiplies AREA "
        f"GOODS ONLY — sealed 2026-07-29): {sorted(set(naked))}")


# ── the bake itself refuses length-cut rows even when the flag is lost ───
def test_bake_never_touches_length_cut_rows_even_unflagged():
    from routes.hover import _bake_tab_waste
    rows = [
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": "Outside corners Standard color", "unit": "PCS", "qty": 15.0},
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": "Starter", "unit": "PCS", "qty": 13.0},
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": "Finish Trim Standard color", "unit": "PCS", "qty": 21.0},
        {"tab": "vinyl", "section": "Siding Accessories",
         "name": '3/4" J-Channel Standard color',
         "unit": "PCS", "qty": 30.0},
        {"tab": "vinyl", "section": "Vinyl Soffit with Siding",
         "name": '3/4" Soffit J-Channel (Charter Oak) Standard color',
         "unit": "PCS", "qty": 23.0},
        {"tab": "lp_smart", "section": "LP SmartSide Trim",
         "name": '540 Series Trim 5/4" x 4" x 16\'', "unit": "PCS", "qty": 62.0},
        {"tab": "lp_smart", "section": "LP Siding Accessories",
         "name": "540 Series OSC 5/4\" x 6\" x 16'", "unit": "PCS", "qty": 15.0},
    ]
    for r in rows:
        out = _bake_tab_waste([dict(r)], 30)[0]
        assert out["qty"] == r["qty"], (
            f"{r['name']}: whole-stick count moved {r['qty']} → {out['qty']} "
            "under the waste field — length-cut goods take NO percentage")
        assert "raw_qty" not in out


# ── vinyl/ascend end-to-end: sticks stand, area goods move (Catch 1) ─────
def test_vinyl_whole_stick_counts_stand_area_goods_move():
    from routes.hover import _build_lines, _bake_tab_waste
    lines = _build_lines(_rich_measurements())
    baked = _bake_tab_waste([dict(l) for l in lines], 10)
    by = {(l["tab"], l["name"]): (pre["qty"], l["qty"])
          for pre, l in zip(lines, baked)}
    # 15 corners is 15 sticks — never 17 (Howard's day-job number)
    pre, post = by[("vinyl", "Outside corners Standard color")]
    assert pre == post == 12.0  # ceil(142/12.5)
    for name in ("Starter", "Finish Trim Standard color",
                 '3/4" J-Channel Standard color',
                 "Inside Corners (Siding) Standard color"):
        pre, post = by[("vinyl", name)]
        assert pre == post, f"{name} bought waste sticks: {pre} → {post}"
    # the AREA good still moves up under the same field
    pre, post = by[("vinyl", 'Charter Oak Standard color Dutch Lap 4.5" .046')]
    assert post == math.ceil(pre * 1.1 - 1e-9) and post > pre


# ── default-lap DOUBLE-BAKE fixed: single application on BOTH paths ──────
def test_default_lap_single_application_both_paths():
    from routes.hover import _build_lines, _bake_tab_waste
    from lp_smartside_formulas import lap_pieces_book
    LAP = '38 Series Lap 3/8" x 8" x 16\''
    # rebuild path: _waste_pct rides the measurements — waste INSIDE, flag ON
    m = _rich_measurements(_waste_pct=0.30)
    lines = _bake_tab_waste(_build_lines(dict(m)), 30)
    lap = next(l for l in lines if l["name"] == LAP)
    assert lap["_waste_included"] is True
    assert lap["qty"] == lap_pieces_book(2000.0, waste=0.30) == 286, (
        f"default lap = {lap['qty']} — the pre-pick path double-baked again "
        "(2,000 ft² at 30% is 286, was emitting 372)")
    # import-draft path: _waste_pct 0 — BASE qty, the ONE bake applies field
    m0 = _rich_measurements(_waste_pct=0.0)
    lines0 = _bake_tab_waste(_build_lines(dict(m0)), 30)
    lap0 = next(l for l in lines0 if l["name"] == LAP)
    assert lap0["qty"] == math.ceil(lap_pieces_book(2000.0, waste=0.0) * 1.3 - 1e-9) == 286
    assert lap0["raw_qty"] == lap_pieces_book(2000.0, waste=0.0) == 220


# ── ruling (b): battens at 0% waste, NO breakage allowance, pinned ───────
def test_battens_zero_waste_sealed():
    from routes.hover import _bake_tab_waste
    from lp_smartside_formulas import (bb_batten_pieces,
                                       bb_batten_pieces_hard,
                                       board_batten_batten_pieces)
    batten = {"tab": "lp_smart", "section": "LP SmartSide Trim",
              "name": '190 Series Trim 19/32" x 3" x 16\'',
              "unit": "PCS", "qty": 194.0}
    for pct in (0, 10, 30):
        assert _bake_tab_waste([dict(batten)], pct)[0]["qty"] == 194.0
    # neither emitter (live aggregate nor sealed hard formula) takes waste
    for fn in (bb_batten_pieces, bb_batten_pieces_hard,
               board_batten_batten_pieces):
        assert "waste" not in inspect.signature(fn).parameters, (
            f"{fn.__name__} grew a waste parameter — battens do not break "
            "(sealed 2026-07-29, ruling b)")


# ── frontend mirror in lockstep: classifier is AREA GOODS ONLY ───────────
def test_frontend_classifier_mirror_area_goods_only():
    js = (FRONTEND_SRC / "lib" / "wasteLogic.js").read_text()
    body = js.split("export function isCutProneItem", 1)[1].split("\n}", 1)[0]
    for gone in ('name.includes("outside corner")',
                 'name.includes("inside corner")',
                 'name.includes("finish trim")',
                 'name.includes("j-channel")',
                 '"lp smartside trim"',
                 'name === "starter"'):
        assert gone not in body, (
            f"frontend classifier still matches length-cut goods: {gone}")
    for kept in ('"vinyl siding"', '"lp smart siding"',
                 '"lp smartside soffit"', "charter oak soffit",
                 "house wrap", "fan fold"):
        assert kept in body, f"AREA good dropped from the classifier: {kept}"
    from routes.hover import _cut_prone_line
    for area in ({"section": "Vinyl Siding", "name": "x"},
                 {"section": "LP Smart Siding", "name": "x"},
                 {"section": "y", "name": "House Wrap"}):
        assert _cut_prone_line(area)
    for cut in ({"section": "LP SmartSide Trim", "name": "540 Series Trim"},
                {"section": "Siding Accessories", "name": "Outside corners Standard color"},
                {"section": "Siding Accessories", "name": "Starter"},
                {"section": "Siding Accessories", "name": "Finish Trim Standard color"},
                {"section": "Siding Accessories",
                 "name": '3/4" J-Channel Standard color'},
                {"section": "LP Siding Accessories",
                 "name": "540 Series OSC 5/4\" x 6\" x 16'"}):
        assert not _cut_prone_line(cut), f"{cut['name']} still classifies cut-prone"
    # waste-field edits snap legacy length-cut rows BACK to the count
    assert "if (!isCutProneItem(l)) return { ...l, qty: roundUpWhole(raw) };" in js
