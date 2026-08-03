"""ACCEPT PAGE SPANISH — PINS (Howard ruled 2026-08-03). The hosted
accept page is the LAST customer surface — where a homeowner clicks to
commit money. Same acceptance as every other surface: chrome translates,
money is language-independent, FINAL COST ONLY, and no SKU can leak
(the page renders no line items by construction).

Found while pinning: the 2026-07-20 "3D dark" commit referenced
RENDER_3D_ENABLED on this page without importing it — a ReferenceError
crash hiding on the exact surface where money gets accepted. The import
pin below keeps that class dead."""
import re

AP_PATH = "/app/frontend/src/pages/AcceptPage.jsx"
PUB_PATH = "/app/backend/routes/public.py"
DICT_PATH = "/app/frontend/src/lib/dictionaries.js"


def _src():
    return open(AP_PATH).read()


def test_accept_money_format_is_language_independent():
    """PENNY PARITY, structural half: one currency formatter, locked
    en-US — the homeowner sees the same figure in either language."""
    src = _src()
    assert 'Intl.NumberFormat("en-US", { style: "currency", currency: "USD" })' in src
    assert src.count("Intl.NumberFormat") == 1, \
        "a second money formatter appeared on the accept page — parity risk"


def test_accept_shows_final_cost_only():
    """RULED: FINAL COST ONLY. The only money field the page renders is
    d.total, and the server builds `total` from totals[sell] alone — no
    material/labor/tax split reaches the accept payload."""
    src = _src()
    money_fields = set(re.findall(r"fmt\(d\.(\w+)\)", src))
    assert money_fields == {"total"}, f"accept page renders a cost split: {money_fields}"
    pub = open(PUB_PATH).read()
    seg = pub[pub.index("def public_get_accept"):pub.index("def public_post_accept")]
    assert 'summary["total"] = round(totals["sell"], 2)' in seg
    for bad in ("sub_mat", "sub_labor", "labor", "tax", "margin"):
        assert f'summary["{bad}"' not in seg, f"cost split leaked to accept payload: {bad}"


def test_accept_has_no_sku_surface():
    """The accept page renders no line items — SKU-leak impossible by
    construction. If lines ever reach this surface they must route
    through tItem like every other surface (this pin flags the arrival)."""
    src = _src()
    for tok in (".lines", "tItem(", "l.name", "adders"):
        assert tok not in src, \
            f"line items reached the accept page ({tok}) — route names through tItem verbatim"


def test_accept_dictionary_keys_exist_both_languages():
    """Every t() key the accept page uses exists in BOTH en and es —
    same detector shape as the quote surfaces."""
    js = open(DICT_PATH).read()
    en, es = js[js.index("en: {"):js.index("  es: {")], js[js.index("  es: {"):]
    used = set(re.findall(r'\bt\("([^"]+)"', _src()))
    assert used, "no t() keys found in AcceptPage.jsx"
    for key in used:
        assert f'"{key}":' in en, f"accept key missing from en: {key}"
        assert f'"{key}":' in es, f"accept key missing from es: {key}"


def test_accept_has_no_hardcoded_english_between_tags():
    """All accept chrome routes through t() — a literal English string
    between tags is a string a Spanish homeowner cannot read."""
    src = re.sub(r"/\*.*?\*/", "", _src(), flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    literals = [w for w in re.findall(r">([A-Za-z][A-Za-z ,'&/-]{3,60})<", src)
                if w.strip()]
    assert not literals, f"hardcoded accept-page strings: {literals}"


def test_accept_page_imports_every_flag_it_references():
    """REGRESSION PIN: RENDER_3D_ENABLED was referenced without an import
    (crash since 2026-07-20). The reference and the import now travel
    together."""
    src = _src()
    if "RENDER_3D_ENABLED" in src:
        assert re.search(
            r'import \{[^}]*RENDER_3D_ENABLED[^}]*\} from "@/lib/featureFlags"', src
        ), "RENDER_3D_ENABLED referenced but not imported — ReferenceError on render"


def test_accept_language_follows_link_param():
    """?lang=es on the accept link flips the page — the customer's page
    matches the language of their email/PDF."""
    src = _src()
    assert 'params.get("lang")' in src
    assert 'wanted === "es"' in src
