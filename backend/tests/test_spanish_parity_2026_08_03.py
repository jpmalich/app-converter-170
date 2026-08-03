"""SPANISH BUILDOUT — PARITY PINS + ENGLISH-ONLY ROT DETECTOR
(Howard ruled 2026-08-03). The rule that cannot break: SKU and product
names VERBATIM in both languages — labels, sections, units, colors
translate; the product name never does. A Spanish line that unprices
means the name leaked into translation. The detector below is the color
rot detector's shape pointed at translation: a NEW dictionary string that
ships English-only FAILS the suite."""
import re

import catalog_seed

DICT_PATH = "/app/frontend/src/lib/dictionaries.js"
CAT_TR_PATH = "/app/frontend/src/lib/catalogTranslations.js"


def _blocks():
    js = open(DICT_PATH).read()
    en_start = js.index("en: {")
    es_start = js.index("es: {")
    return js[en_start:es_start], js[es_start:]


def _keys(block):
    return set(re.findall(r'^\s{4}"([^"]+)":', block, re.M))


def test_detector_no_english_only_dictionary_string():
    """EVERY key in `en` exists in `es` and vice versa. This is what
    stops the app going half-English one string at a time."""
    en_block, es_block = _blocks()
    en, es = _keys(en_block), _keys(es_block)
    assert en, "failed to parse dictionaries.js"
    missing_es = en - es
    missing_en = es - en
    assert not missing_es, f"English-only strings shipped (add es): {sorted(missing_es)}"
    assert not missing_en, f"Spanish-only strings (add en): {sorted(missing_en)}"


def test_new_surfaces_are_translated():
    """The strings Howard named MUST-TRANSLATE: fill-in boxes, gate
    chips/banner, tier chips — present in BOTH languages."""
    en_block, es_block = _blocks()
    for key in ("pf.title", "pf.notSet", "pf.friezeQ", "gate.pf.title",
                "gate.pf.body", "gate.pf.hint", "tier.architectural",
                "tier.standard"):
        assert f'"{key}":' in en_block, f"{key} missing from en"
        assert f'"{key}":' in es_block, f"{key} missing from es"


def test_sku_names_never_translate():
    """tItem returns the canonical string unchanged (ruled 2026-07-31) —
    pinned by ruling text + no item-name translation map exists."""
    src = open(CAT_TR_PATH).read()
    assert "SKU NAMES NEVER TRANSLATE" in src
    assert "ITEMS_ES RETIRED" in src, "the retirement record must stay on file"
    live = "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))
    assert "ITEMS_ES" not in live, "an item-name translation map reappeared"
    assert re.search(r"export function tItem\(name, lang\) \{[^}]*return ITEM_NAME_ALIASES\[name\] \|\| name;", src, re.S), \
        "tItem no longer returns the canonical name verbatim"


def test_no_catalog_sku_leaks_into_any_translation():
    """No full SKU name appears as a translation source anywhere — not in
    the es dictionary, not in the note-fragment map. The leak that would
    unprice a Spanish line."""
    _, es_block = _blocks()
    cat_src = open(CAT_TR_PATH).read()
    frag_block = cat_src[cat_src.index("NOTE_FRAGMENTS_ES"):]
    for name in catalog_seed.ITEM_META:
        if len(name) < 15:
            continue  # one-word generics ("Shake") double as family labels
        assert f'"{name}"' not in es_block, f"SKU leaked into es dictionary: {name}"
        assert f'["{name}"' not in frag_block, f"SKU leaked into note fragments: {name}"


def test_note_fragments_cover_the_provenance_strings():
    """The crew-facing provenance wording translates: TYPED/CONTRACTOR
    FILL-IN, the frieze toggle note, MEASURED, and the derived tier note."""
    src = open(CAT_TR_PATH).read()
    for frag in ("TYPED soffit total", "CONTRACTOR FILL-IN, photo door",
                 "MEASURED soffit total",
                 "TYPED toggle — frieze LF from measured eave/rake runs",
                 "Architectural color tier (derived from"):
        assert frag in src, f"provenance fragment untranslated: {frag}"


def test_gate_item_carries_structured_unset_list():
    """The banner composes its Spanish text from the gate's structured
    `unset` list — the server (one set/unset copy) names the open boxes."""
    from gates import quote_gate_blockers
    est = {"kind": "siding",
           "lines": [{"tab": "vinyl", "section": "Vinyl Siding",
                      "name": "x", "unit": "SQ", "qty": 20}],
           "hover_measurements": {"_source": "photo", "siding_sqft": 1400.0,
                                  "eaves_lf": 120.0, "rakes_lf": 60.0}}
    hit = next(i for i in quote_gate_blockers(est)
               if i["code"] == "photo_fillin_unset")
    assert hit["unset"] == ["soffit ft²", "drip edge LF", "total trim ft²",
                            "frieze yes/no"]


def test_pricing_is_language_blind():
    """PENNY PARITY, structural half: derivation and pricing run entirely
    server-side on canonical names — no language token exists anywhere in
    the pricing path. (The live EN/ES side-by-side is the demonstrated
    half.)"""
    import routes.hover as hover_mod
    import vinyl_color_tiers as tiers_mod
    for mod in (hover_mod, tiers_mod, catalog_seed):
        src = open(mod.__file__.replace(".pyc", ".py")).read()
        assert "lang" not in re.sub(r"#.*", "", src).replace("angle", "").replace(
            "triangle", "").replace("rectangle", "").replace("flang", ""), \
            f"a language token reached the pricing path: {mod.__name__}"
