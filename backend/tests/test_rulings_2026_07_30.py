"""RULINGS 2026-07-30 — three new suite-level detector classes.

R4 class: AN EMITTER FEEDING A RETIRED CATALOG NAME ("worse than a ghost
guard — it puts a line a contractor cannot buy onto a real quote").
Every static emitter item name must resolve to a live catalog row.

#6 class: A REGISTRY NAME MUST RESOLVE TO A LIVE CATALOG ROW or the guard
watches nothing ('24" CTW' lesson).

R3 class: WHOLE UNITS ON EVERY ORDERED LINE, each line on its own — the
old pin tested the emitter FUNCTIONS while pre-seal fractional rows sat
on the stored surface; this one walks the composed build surface.
"""
import math

from catalog_seed import SECTION_LAYOUT
from iss_catalog import ISS_SECTIONS
from lp_conventions import CATALOG_ONLY_MANUAL_BY_DESIGN


def _catalog_names() -> set[str]:
    return {it for _s, _sh, items in SECTION_LAYOUT for it in items}


def _iss_names() -> set[str]:
    return {n for _sec, rows in ISS_SECTIONS for (n, *_rest) in rows}


def test_every_static_emitter_item_resolves_to_a_live_catalog_row():
    """R4 detector — the 'Inside Corners' (Ascend) class: supplier dropped
    the row Feb 2026, the emitter kept feeding it, four estimates carried
    it at $0.00."""
    import routes.hover as hv
    cat, iss = _catalog_names(), _iss_names()
    ghosts = []
    maps = [m for m in vars(hv).values()
            if isinstance(m, list) and m and isinstance(m[0], dict)
            and "item" in m[0]]
    for mp in maps:
        for row in mp:
            item = row.get("item")
            if not isinstance(item, str):
                continue
            tabs = row.get("tabs") or []
            pool = iss if tabs == ["iss"] else cat | iss
            if item not in pool:
                ghosts.append((tabs, item))
    assert not ghosts, (
        "EMITTER FEEDS A NAME THE CATALOG DOES NOT CARRY (R4 class, ruled "
        f"2026-07-30) — the line can never price: {ghosts}")


def test_registry_names_resolve_to_live_catalog_rows():
    """#6 detector — a guard on a name that doesn't exist protects nothing."""
    cat = _catalog_names()
    ghosts = sorted(set(CATALOG_ONLY_MANUAL_BY_DESIGN) - cat)
    assert not ghosts, (
        f"register #8 name(s) match no catalog SKU — vacuous guard: {ghosts}")


def test_no_door_prints_a_fractional_order_quantity():
    """R3 surface detector: build through the composed emitter with rich
    measurements; after the order layer no line may carry a fractional
    qty a contractor cannot buy — any unit, any tab. Cut-prone rows are
    ceiled by the waste bake (its formula pins live in
    test_one_waste_emitter); everything else must already be whole."""
    from routes.hover import _bake_tab_waste, _build_lines
    m = {"siding_sqft": 2437, "eaves_lf": 104.3, "rakes_lf": 141.7,
         "window_count": 7, "entry_door_count": 2, "patio_door_count": 1,
         "garage_door_count": 1, "soffit_sqft": 233.4, "openings_perimeter_lf": 0,
         "outside_corner_lf": 77.3, "inside_corner_lf": 24.2,
         "porch_ceiling_sqft": 61.8, "overhang_in": 16}
    lines = _bake_tab_waste(_build_lines(m), 10)
    bad = [(l.get("tab"), l.get("name"), l.get("qty")) for l in lines
           if isinstance(l.get("qty"), (int, float)) and l["qty"] > 0
           and float(l["qty"]) != int(l["qty"])]
    assert not bad, f"fractional order quantities printed: {bad}"


def test_spec_keys_are_read_by_the_exact_key_they_are_written_under():
    """F2 class detector (ruled 2026-07-30): every spec the plumbing writes
    (underscore-prefixed) must have at least one consumer reading that
    EXACT key, and no consumer may read the bare (unwritten) variant."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    src = "".join((root / f).read_text() for f in
                  ("routes/hover.py", "lp_package.py",
                   "routes/lp_package_routes.py", "lp_smartside_formulas.py"))
    for key in ("_shake_reveal_in", "_batten_spacing_in", "_fascia_width_in",
                "_panel_size", "_wrap_trim_width_in"):
        assert f'"{key}"' in src or f"'{key}'" in src, f"{key}: no consumer"
        bare = key[1:]
        for pat in (f'm.get("{bare}")', f"m.get('{bare}')"):
            assert pat not in src, (
                f"F2 recurrence: a consumer reads the bare key {bare!r} "
                f"while the spec plumbing writes {key!r}")


def test_wrap_and_panel_specs_bind_and_move_what_they_claim():
    """Delivery pins (ruled 2026-07-30): panel size changes COUNT and SKU;
    wrap width changes ONLY the name."""
    from lp_conventions import (WRAP_TRIM_WIDTHS_IN, WRAP_TRIM_ITEM,
                                wrap_item_for_width)
    cat = _catalog_names()
    for w in WRAP_TRIM_WIDTHS_IN:
        assert wrap_item_for_width(w) in cat, f'540 wrap width {w}" unbound'
    assert wrap_item_for_width(None) == WRAP_TRIM_ITEM
    assert "38 Series 4' x 8' Panel" in cat and "38 Series 4' x 10' Panel" in cat
