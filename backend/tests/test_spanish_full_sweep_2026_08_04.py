"""SPANISH FULL SWEEP — DETECTOR EXTENSION (Howard ruled 2026-08-04).
"FULLY FUNCTIONAL IN SPANISH — SWEEP EVERYTHING... The SKU-leak detector
and the tItem-verbatim pin must COVER every surface this sweep touches —
the contractor panels, the QR pages, the accept page. Not just the
surfaces already pinned."
Chrome and labels translate; SKU names, color names, tier terms and every
dollar figure stay verbatim.
"""
import re

FE = "/app/frontend/src"
SWEPT = [
    f"{FE}/components/estimate/SettingsRow.jsx",
    f"{FE}/components/estimate/FieldVerifyCard.jsx",
    f"{FE}/components/estimate/LpMaterialListPanel.jsx",
    f"{FE}/pages/MaterialListShare.jsx",
    f"{FE}/pages/AccuracyReportShare.jsx",
]


def _src(p):
    return open(p).read()


def _stripped(p):
    src = re.sub(r"/\*.*?\*/", "", _src(p), flags=re.S)
    src = re.sub(r"\{/\*.*?\*/\}", "", src, flags=re.S)
    return re.sub(r"^\s*//.*$", "", src, flags=re.M)


def test_qr_pages_have_no_hardcoded_english_between_tags():
    """Same shape as the accept-page pin — a literal English string between
    tags on a crew-facing QR page is a string the crew cannot read."""
    for p in (f"{FE}/pages/MaterialListShare.jsx", f"{FE}/pages/AccuracyReportShare.jsx"):
        literals = [w for w in re.findall(r">([A-Za-z][A-Za-z ,'&/-]{3,60})<", _stripped(p))
                    if w.strip() and w.strip() not in ("Accuracy report",)]
        assert not literals, f"hardcoded QR-page strings in {p}: {literals}"


def test_qr_material_list_renders_sku_and_color_verbatim():
    """The crew orders by the NAME — {l.name} and {l.color} render raw,
    never through a translation call."""
    src = _src(f"{FE}/pages/MaterialListShare.jsx")
    assert "{l.name}</div>" in src, "SKU name must render verbatim"
    assert re.search(r"\{l\.color \|\| .—.\}", src), "color name must render verbatim"
    assert "tItem(" not in src, "item names never route through a translation fn"


def test_qr_pages_honor_lang_param_and_carry_toggle():
    for p in (f"{FE}/pages/MaterialListShare.jsx", f"{FE}/pages/AccuracyReportShare.jsx"):
        src = _src(p)
        assert 'searchParams.get("lang")' in src, f"{p} must honor ?lang"
        assert "PublicLangToggle" in src, f"{p} must carry the EN/ES toggle"


def test_swept_surfaces_route_chrome_through_t():
    """Every swept contractor surface uses the dictionary — and the strings
    Howard named are keyed in BOTH languages (the EN/ES parity detector in
    test_spanish_parity guards every new key globally)."""
    js = open(f"{FE}/lib/dictionaries.js").read()
    en_block = js[js.index("en: {"):js.index("es: {")]
    es_block = js[js.index("es: {"):]
    for key in ("sr.recomputeWaste", "sr.wasteBaked", "sr.soffitType",
                "sr.sellMargin", "sr.sellMarkup", "sr.wallHeights.title",
                "fv.title", "fv.perWall", "fv.tapedDims.title",
                "fv.assumedDepth", "fv.printedOnPlans",
                "lpp.derivedNote", "lpp.pendingCount", "lpp.compare",
                "jip.pending.title", "intake.importHover",
                "intake.readBlueprints", "intake.aiMeasure",
                "mls.title", "mls.readOnly", "mls.unpricedNote",
                "ars.title", "ars.frozen", "ars.frozenBodyNote"):
        assert f'"{key}":' in en_block, f"{key} missing from en"
        assert f'"{key}":' in es_block, f"{key} missing from es"
    for p in SWEPT:
        assert re.search(r"useT\(\)", _src(p)), f"{p} does not use the dictionary"


def test_no_sku_leaks_into_the_new_keys():
    """A full catalog SKU name appearing as a dictionary VALUE would put a
    product name into the translation layer — the exact leak Howard named."""
    import catalog_seed
    js = open(f"{FE}/lib/dictionaries.js").read()
    es_block = js[js.index("es: {"):]
    for name in catalog_seed.ITEM_META:
        if len(name) < 15:
            continue
        assert f'"{name}"' not in es_block, f"SKU leaked into es dictionary: {name}"


def test_hover_modal_chrome_routes_through_t():
    """CLICK-SWEEP FINDING (2026-08-04, iteration 52): the Hover modal's
    RESTORE / PRINT / CANCEL / I-AGREE buttons and the quantity-verify
    modal were hard-coded English while the CTA next to them was Spanish.
    Chrome translates; the keys exist in BOTH dictionaries."""
    src = _src(f"{FE}/components/estimate/HoverImportButton.jsx")
    for key in ("hov.restore", "hov.print", "hov.cancel", "hov.agree",
                "hov.qtyVerifyTitle", "hov.qtyVerifyBody",
                "hov.openingsTitle", "hov.openingsTap", "hov.openingsExpanded",
                "hov.needsReview", "hov.sanity", "hov.tapToReview"):
        assert f'"{key}"' in src, f"HoverImportButton no longer routes '{key}' through t()"
    for literal in (">Print<", ">Cancel<", ">I Agree<", "Restore HOVER Lines<"):
        assert literal not in src, f"hard-coded English button label back in the Hover modal: {literal}"
    dicts = _src(f"{FE}/lib/dictionaries.js")
    for key in ("hov.restore", "hov.print", "hov.cancel", "hov.agree",
                "hov.qtyVerifyTitle", "hov.qtyVerifyBody", "hov.openingsTap",
                "hov.needsReview", "hov.sanity"):
        assert dicts.count(f'"{key}"') >= 2, f"'{key}' missing from one of the two dictionaries"


def test_frozen_accuracy_body_stays_sealed():
    """The frozen report body renders verbatim (srcDoc={data.html}) — the
    ES page names the sealed-document framing instead of re-rendering a
    frozen artifact."""
    src = _src(f"{FE}/pages/AccuracyReportShare.jsx")
    assert "srcDoc={data.html}" in src
    assert "ars.frozenBodyNote" in src
