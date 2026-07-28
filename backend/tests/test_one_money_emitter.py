"""ONE EMITTER PER MONEY FORMULA — doctrine SEALED 2026-07-28 (convergence
audit rulings). Any number that reaches a dollar has exactly ONE
implementation; every other surface COMPOSES through it. A comment is not
a pin. These pins FAIL WHEN A SECOND IMPLEMENTATION APPEARS — they scan
the source for money-formula signatures and refuse any location outside
the named emitter (not merely asserting today's agreement).

Named emitters:
  TOTALS (waste/tax/margin) ... backend services.calc_totals · frontend lib/calc.js
  TIER SELL .................. backend lp_costs.sell_price
  VERO/MEZZO OPENING $ ....... inside the two totals emitters only
Named display-only exceptions (render a preview, feed no dollar):
  SettingsRow.jsx (margin multiplier preview) · VeroPanel/VeroJobSnapshot
  (per-opening entry surfaces write fields; totals compose elsewhere).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND = Path("/app/backend")
FRONTEND_SRC = Path("/app/frontend/src")


def _py_files():
    for p in BACKEND.rglob("*.py"):
        s = str(p)
        if "__pycache__" in s or "/tests/" in s or "/.pytest_cache/" in s:
            continue
        yield p


def _js_files():
    for pat in ("*.js", "*.jsx"):
        for p in FRONTEND_SRC.rglob(pat):
            if "node_modules" in str(p) or p.name.endswith(".test.mjs"):
                continue
            yield p


# ── RULING #1: totals waste — the add-on formula is DEAD everywhere ──────
def test_backend_totals_waste_addon_retired():
    services = (BACKEND / "services.py").read_text()
    assert "wasted = sub_mat\n" in services or "wasted = sub_mat " in services
    assert "waste_add" not in services, "the retired waste add-on is back"
    assert "WASTE_ASCEND" not in services


def test_no_second_waste_addon_implementation_backend():
    # signature: multiplying a waste base by waste_pct inside a totals path
    sig = re.compile(r"waste_base\s*\*|\*\s*\(\s*\(?est\.get\(.waste_pct")
    for p in _py_files():
        assert not sig.search(p.read_text()), f"waste add-on signature in {p}"


def test_frontend_wasted_is_submat_pin_still_holds():
    calc = (FRONTEND_SRC / "lib/calc.js").read_text()
    assert "const wasted = subMat;" in calc
    assert "subMat + wasteAdd" not in calc


# ── RULING #2: Vero opening $ — adders model, identical both emitters ────
def test_vero_openings_price_identically_backend_vs_frontend():
    from services import calc_totals
    est = {
        "tax_enabled": False, "margin_pct": 0, "pricing_mode": "markup",
        "lines": [], "misc_labor": [], "misc_material": [],
        "vero_openings": [
            {"qty": 2, "base_mat": 300.0,
             "adders": [{"qty": 1, "mat": 45.0}, {"qty": 2, "mat": 10.0}]},
            {"qty": 1, "base_mat": 400.0, "glass_mat": 50.0,
             "tempered_mat": 25.0, "premium_mat": 10.0},
        ],
    }
    t = calc_totals(est)
    # mirror of lib/calc.js: qty×base + Σ(adder.qty×mat) + qty×legacy
    expected = (2 * 300.0 + (45.0 + 20.0)) + (1 * 400.0 + 85.0)
    assert t["sub_mat"] == expected
    assert t["sell"] == expected  # no waste add-on, no tax, no margin


def test_vero_backend_reads_adders():
    services = (BACKEND / "services.py").read_text()
    i = services.index("_vero_opening_mat")
    block = services[i:i + 1200]
    assert "adders" in block, "Vero backend lost the adders term again"


# ── RULING #1 pin: accept page == editor (waste_pct cannot move a dollar) ─
def test_accept_vs_editor_fixture_pin():
    from services import calc_totals
    est = {
        "tax_enabled": True, "tax_rate": 7.0, "margin_pct": 30.0,
        "pricing_mode": "margin", "waste_pct": 15.0,
        "misc_labor": [], "misc_material": [],
        "lines": [
            # baked vinyl siding line (qty carries the waste; raw_qty stored)
            {"tab": "vinyl", "section": "Vinyl Siding",
             "name": 'Charter Oak Standard color Dutch Lap 4.5" .046',
             "qty": 23.0, "raw_qty": 20.0, "mat": 136.22, "lab": 0},
            {"tab": "vinyl", "section": "Siding Accessories",
             "name": "Caulking (per color)", "qty": 3, "mat": 14.03, "lab": 0},
        ],
    }
    with_waste = calc_totals(est)
    zero_waste = calc_totals({**est, "waste_pct": 0})
    assert with_waste["sell"] == zero_waste["sell"], (
        "waste_pct moved the Accept-page dollar — the retired add-on is back")
    sub = 23.0 * 136.22 + 3 * 14.03
    assert round(with_waste["sell"], 2) == round((sub * 1.07) / 0.70, 2)


# ── RULING #3: no client-side writer of a sealed waste default ───────────
def test_no_client_side_waste_default_writer():
    for p in _js_files():
        s = p.read_text()
        assert "defaultWastePct" not in s, f"localStorage waste writer in {p}"
        assert "saveWasteDefault" not in s, f"waste-default writer in {p}"
    assert not (FRONTEND_SRC / "lib/wasteDefaults.js").exists()


# ── RULING #4 (pre-Sept slice): OSC/ISC hover-basis equivalence pin ──────
def _assemble_osc_qty(m):
    from lp_package import assemble_lp_package, OSC_ITEM
    pkg = assemble_lp_package(dict(m))
    line = next((l for l in pkg["lines"] if l["name"] == OSC_ITEM), None)
    return int(line["qty"]) if line else 0


def test_osc_hover_basis_tab_equals_package():
    from routes.hover import _osc_lp_pcs
    for m in (
        {"_hover_source": True, "siding_sqft": 2064,
         "outside_corner_count": 14, "outside_corner_lf": 140.3},
        {"_hover_source": True, "siding_sqft": 4504,
         "outside_corner_count": 26, "outside_corner_lf": 175.42},
        # pooled fallback (count unavailable — Q16 flag path)
        {"_hover_source": True, "siding_sqft": 1500,
         "outside_corner_lf": 175.42},
    ):
        assert _assemble_osc_qty(m) == _osc_lp_pcs(m), (
            f"OSC tab-line vs package diverge on {m}")


def test_isc_hover_basis_tab_equals_package_formula():
    # ISC merges onto the 540-4" wrap row in the package; compare the
    # spec's per-corner formula against assemble's corner-walk block math.
    import math
    from routes.hover import _isc_540_pcs
    for ic, ilf in ((24, 173.08), (6, 57.0), (3, 0.0)):
        m = {"inside_corner_count": ic, "inside_corner_lf": ilf}
        per_h = (ilf / ic) if ilf > 0 else 9.5
        package_math = ic * max(1, math.ceil(per_h / 16.0 - 1e-9))
        assert _isc_540_pcs(m) == package_math


# ── DOCTRINE detector: margin division exists ONLY in named emitters ─────
_MARGIN_SIG = re.compile(r"/\s*\(\s*1(\.0)?\s*-\s*|/\s*denom|\(1\s*-\s*min\(pct|1\s*-\s*pct\s*/\s*100")
# NAMED exceptions (reported to Howard 2026-07-28 — hand ruling pending):
#   vero_catalog.py — seed-time cost→sell catalog generator (its OUTPUT is
#     pinned by test_pricing_parity); second FORMULA instance nonetheless.
#   ISSEstimateEditor.jsx — ISS workspace computes sell locally instead of
#     lib/calc.js; unification queued post-Sept.
_ALLOWED_MARGIN_PY = {"services.py", "lp_costs.py", "vero_catalog.py"}
_ALLOWED_MARGIN_JS = {"calc.js", "SettingsRow.jsx", "ISSEstimateEditor.jsx"}


def _code_lines_py(path):
    """Source lines with comments + strings/docstrings stripped, so prose
    describing a formula never trips the detector — only code does."""
    import io
    import tokenize
    src = path.read_text()
    out = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            if tok.type == tokenize.NAME or tok.type == tokenize.OP or tok.type == tokenize.NUMBER:
                out.setdefault(tok.start[0], []).append(tok.string)
    except tokenize.TokenizeError:
        return [(i + 1, l) for i, l in enumerate(src.splitlines())]
    lines = src.splitlines()
    return [(n, lines[n - 1]) for n in sorted(out) if n <= len(lines)]


def test_margin_math_single_emitter_backend():
    for p in _py_files():
        if "margin" not in p.read_text():
            continue
        for n, line in _code_lines_py(p):
            if "margin" in line.lower() and _MARGIN_SIG.search(line):
                assert p.name in _ALLOWED_MARGIN_PY, (
                    f"second margin implementation in {p}:{n}: {line.strip()}")


def test_margin_math_single_emitter_frontend():
    sig = re.compile(r"1\s*-\s*Math\.min\(pct|/\s*denom|/\s*\(1\s*-\s*pct")
    for p in _js_files():
        s = p.read_text()
        for line in s.splitlines():
            if sig.search(line) and not line.strip().startswith(("//", "*", "/*")):
                assert p.name in _ALLOWED_MARGIN_JS, (
                    f"second margin implementation in {p}: {line.strip()}")
