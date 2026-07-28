"""WASTE — SEALED, ALL FAMILIES, ONE RULE, BOTH SURFACES (Howard, ruled
2026-07-28).

THE RULE: the CONTRACTOR sets the waste — vinyl, Ascend and LP SmartSide
alike; no family gets its own convention. ONE visible contractor-editable
field, family-defaulted (lap/soffit 10 · shake 15 · B&B 30 · nickel gap
12), fully editable including to zero. Whatever the field says is ALWAYS
applied into the quantity, every family, at the same layer. The
waste-inclusive quantity on the tab lines and on the printed material
list is THE SAME NUMBER — a quantity differing between surfaces is the
same defect class as a dollar differing between editor and Accept page.
THE FIELD MUST NOT LIE: display and math are the same fact. NOTHING GOES
DOWN under this ruling (a drop = LP moved to raw instead of vinyl moved
to wasted — shorts a job).

ONE EMITTER: waste application detectors below scan the source for
waste-factor signatures and refuse any location outside the RATIFIED
whitelist (memory/ratified_money_emitters.txt, scopes backend-waste /
frontend-waste) — same machinery as the money emitters.

Named emitters:
  QTY BAKE ......... backend routes/hover.py::_bake_tab_waste ·
                     frontend lib/wasteLogic.js::applyWasteQty (mirror, pinned)
  LP DERIVATION .... lp_smartside_formulas / lp_conventions / lp_package —
                     sealed formulas composing the SAME field value
                     (plumbed only by _apply_contractor_waste)
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND = Path("/app/backend")
FRONTEND_SRC = Path("/app/frontend/src")
RATIFIED = Path("/app/memory/ratified_money_emitters.txt")

# waste-factor signatures: `(1 + w…)` / `(1.0 + waste…)` paren form,
# `factor = 1 + max(…)` assignment form, `(wastePct / 100)` add-on form —
# counted only when "waste" appears within a ±3-line window.
_P_PAREN = re.compile(r"\(\s*1(?:\.0)?\s+\+\s+")
_P_FACTOR = re.compile(r"=\s*1\s*\+\s*max")
_P_ADDON = re.compile(r"\(\s*wastePct\s*/\s*100")


def _ratified(scope: str) -> set[str]:
    out = set()
    for raw in RATIFIED.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 3)
        assert len(parts) >= 3, f"malformed ratification line: {raw}"
        s, fname, ruled_date = parts[0], parts[1], parts[2]
        assert re.match(r"\d{4}-\d{2}-\d{2}$", ruled_date), (
            f"ratification line missing ruled-date: {raw}")
        if s == scope:
            out.add(fname)
    return out


def _scan(root: Path, exts, pats, skip=()):
    hits = {}
    for p in sorted(root.rglob("*")):
        if p.suffix not in exts or any(s in str(p) for s in skip):
            continue
        try:
            lines = p.read_text().splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines):
            if ln.strip().startswith(("#", "//", "*")):
                continue
            if not any(pt.search(ln) for pt in pats):
                continue
            window = " ".join(lines[max(0, i - 3):i + 4]).lower()
            if "waste" in window:
                hits.setdefault(p.name, []).append(f"{p}:{i + 1}")
    return hits


# ── DETECTORS — fail on any SECOND implementation ────────────────────────
def test_backend_waste_math_only_in_ratified_emitters():
    allowed = _ratified("backend-waste")
    assert allowed, "no ratified backend-waste entries — governance missing"
    hits = _scan(BACKEND, {".py"}, [_P_PAREN, _P_FACTOR],
                 skip=("/tests",))
    rogue = {f: locs for f, locs in hits.items() if f not in allowed}
    assert not rogue, (
        "UNRATIFIED backend waste-factor implementation (one-emitter rule, "
        f"sealed 2026-07-28) — ratify or compose through the named emitter: {rogue}")


def test_frontend_waste_math_only_in_ratified_emitters():
    allowed = _ratified("frontend-waste")
    assert allowed, "no ratified frontend-waste entries — governance missing"
    hits = _scan(FRONTEND_SRC, {".js", ".jsx"}, [_P_PAREN, _P_FACTOR, _P_ADDON],
                 skip=("node_modules", ".test."))
    rogue = {f: locs for f, locs in hits.items() if f not in allowed}
    assert not rogue, (
        "UNRATIFIED frontend waste-factor implementation (one-emitter rule, "
        f"sealed 2026-07-28): {rogue}")


def test_backend_frontend_bake_mirror_identical_math():
    """The two qty-bake emitters (one per language) carry the SAME sealed
    formula: qty = ceil(raw × (1 + w/100) − 1e-9) — WHOLE UNITS at the
    order layer (0.5 RETIRED, Howard sealed 2026-07-28), never down."""
    from routes.hover import _bake_tab_waste
    js = (FRONTEND_SRC / "lib" / "wasteLogic.js").read_text()
    assert "Math.ceil(x - 1e-9)" in js           # roundUpWhole
    assert "Math.ceil(x * 2) / 2" not in js      # the 0.5 convention is DEAD
    assert "(1 + pct / 100)" in js               # inside applyWasteQty
    assert "export function applyWasteQty" in js
    vinyl = {"tab": "vinyl", "section": "Vinyl Siding",
             "name": 'Charter Oak Standard color Dutch Lap 4.5" .046',
             "unit": "SQ", "qty": 42.4}
    out10 = _bake_tab_waste([dict(vinyl)], 10)[0]
    assert out10["qty"] == 47.0 and out10["raw_qty"] == 42.4   # ceil(93.28)/2
    out20 = _bake_tab_waste([dict(vinyl, qty=18.0)], 20)[0]
    assert out20["qty"] == 22.0                  # 18 × 1.2 → 21.6, IEEE754 21.5999… → ceil-half 22.0 (identical in JS)


# ── THE FIELD MUST NOT LIE ───────────────────────────────────────────────
def test_field_never_lies_including_zero():
    from routes.hover import _bake_tab_waste
    vinyl = {"tab": "vinyl", "section": "Vinyl Siding",
             "name": "x", "unit": "SQ", "qty": 42.0}
    at0 = _bake_tab_waste([dict(vinyl)], 0)[0]
    assert at0["qty"] == 42.0                    # editable to zero → raw
    at10 = _bake_tab_waste([dict(vinyl)], 10)[0]
    assert at10["qty"] == 47.0 and at10["raw_qty"] == 42.0   # whole units
    # raw preserved → a later field edit recomputes losslessly


# ── NOTHING GOES DOWN — Howard's named quantities on the 3 Degree import ─
def test_nothing_goes_down_3degree_all_families():
    from routes.hover import _bake_tab_waste
    from lp_smartside_formulas import lap_pieces_book, board_batten_panel_pieces
    # vinyl / ascend MOVE UP: 42.4 SQ raw → 47.0 SQ at the 10% default
    for section in ("Vinyl Siding", "Ascend Cladding"):
        l = _bake_tab_waste([{"tab": "vinyl", "section": section,
                              "name": "Ascend Composite Lap Siding 7\""
                              if "Ascend" in section else "Charter Oak lap",
                              "unit": "SQ", "qty": 42.4}], 10)[0]
        assert l["qty"] >= 42.4, "a family DROPPED — vinyl moved to raw, STOP"
        assert l["qty"] == 47.0
    # LP stays: already correct — 138 panels B&B · 513 lap pcs
    assert board_batten_panel_pieces(4239, waste=0.30) == 138
    assert lap_pieces_book(4239, waste=0.10) == 513


# ── ONE RULE ALL FAMILIES — the Iter 79c vinyl zero-waste branch is DEAD ─
def test_hover_door_no_family_waste_exception():
    src = (FRONTEND_SRC / "components" / "estimate" / "HoverImportButton.jsx").read_text()
    assert '"lp_smart" ? lpWasteFieldPrefill : 0' not in src
    assert "Waste % reset to 0" not in src, "Iter 79c vinyl zero-waste convention resurfaced"
    assert "const wastePct = wasteFieldPrefill" in src
    assert "waste_pct: wastePct" in src          # field written for ALL kinds


# ── BOTH SURFACES, SAME NUMBER — printed list == tab lines, % printed ────
def test_printed_material_list_equals_tab_lines_and_prints_pct():
    ml = (FRONTEND_SRC / "lib" / "materialList.js").read_text()
    assert "re-applying waste" in ml             # renders baked qty verbatim
    assert "${wastePct}% waste" in ml            # the % used is PRINTED
    assert "lap/soffit 10" in ml                 # family defaults named on the doc
    assert re.search(r"\(\s*1\s*\+\s*wastePct", ml) is None, (
        "materialList re-applies waste — tab and print would diverge")
    # LP printed panel states the APPLIED value from the engine itself
    lp = (FRONTEND_SRC / "components" / "estimate" / "LpMaterialListPanel.jsx").read_text()
    assert "lp-waste-applied-chip" in lp and "waste_pct_applied" in lp


def test_recon_card_composes_through_the_emitter():
    tc = (FRONTEND_SRC / "components" / "estimate" / "TakeoffReconCard.jsx").read_text()
    assert "applyWasteQty" in tc
    assert "roundUpHalf(qty * (1 + pct" not in tc


# ── WHOLE UNITS AT THE ORDER LAYER (Howard sealed 2026-07-28) ────────────
def test_whole_units_at_order_layer_every_line():
    """Nobody orders half a stick: 540 trim raw 100 × 1.1 was IEEE754
    110.000…01 and round-up-half kept 110.5 on estimate f3e7d728. Whole
    units, every family, every line, applied AFTER waste."""
    from routes.hover import _bake_tab_waste
    trim = {"tab": "lp_smart", "section": "LP SmartSide Trim",
            "name": '540 Series Trim 5/4" x 4" x 16\'', "unit": "PCS", "qty": 100.0}
    out = _bake_tab_waste([dict(trim)], 10)[0]
    assert out["qty"] == 110.0                   # float noise stripped, NOT 110.5, NOT 111
    # fractional qty on a non-cut-prone ordered row rounds up at the same layer
    coil = {"tab": "vinyl", "section": "Vinyl Accessories",
            "name": ".019 Coil", "unit": "ROLL", "qty": 5.28}
    assert _bake_tab_waste([dict(coil)], 10)[0]["qty"] == 6.0
    # sealed derivation rows (_waste_included) are the formulas' own —
    # already order-ready, never re-touched here
    lap = {"tab": "lp_smart", "section": "LP Smart Siding",
           "name": '38 Series Lap 3/8" x 8" x 16\'', "unit": "PCS",
           "qty": 513.0, "_waste_included": True}
    assert _bake_tab_waste([dict(lap)], 10)[0]["qty"] == 513.0


# ── NOTHING STALE LEFT BEHIND (Howard sealed 2026-07-28 — f3e7d728) ──────
def test_profile_pick_rederive_is_the_last_write():
    """The B&B pick re-derived correctly server-side and the editor's
    debounced autosave replayed the pre-pick lap merge over it (lap 514
    standing, panels 0). The apply flow now adopts the rebuilt tab_lines
    into client state and persists them as the LAST write."""
    src = (FRONTEND_SRC / "components" / "estimate" / "HoverImportButton.jsx").read_text()
    assert "const { data: freshEst }" in src      # server truth re-fetched
    assert "lines: freshEst.lines" in src         # rebuilt lines adopted
    assert "waste_pct: freshEst.waste_pct" in src # family waste adopted (B&B 30)
    # the stale wrap-0 facade scope builder is dead: untouched picker
    # sends NO scope on the lp-run door too
    assert '"wrap_only"' not in src and '"all_included"' not in src
    assert "facadeMaterials.length && Object.keys(facadeInclude).length" in src


# ── family defaults sealed values ────────────────────────────────────────
def test_family_waste_defaults_sealed_values():
    from lp_conventions import FAMILY_WASTE_DEFAULTS, family_waste_default_pct
    assert FAMILY_WASTE_DEFAULTS == {"lap": 10.0, "board_batten": 30.0,
                                     "shake": 15.0, "nickel_gap": 12.0}
    assert family_waste_default_pct(None) == 10.0   # vinyl/ascend lap family
