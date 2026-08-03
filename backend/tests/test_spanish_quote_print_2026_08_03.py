"""SPANISH QUOTE PRINT — PINS (Howard ruled 2026-08-03). The customer
quote email/PDF (emailQuote.js) is the page a Spanish-speaking homeowner
reads: chrome and labels translate, SKU and tier terms stay verbatim,
money figures are language-independent. These pins make the quote surface
inherit the detectors built for the estimate page — a customer PDF is a
new surface, and new surfaces are where things hid."""
import re

EQ_PATH = "/app/frontend/src/lib/emailQuote.js"
QM_PATH = "/app/frontend/src/components/QuoteModal.jsx"


def _src():
    return open(EQ_PATH).read()


def _qm():
    return open(QM_PATH).read()


def test_quote_names_route_through_titem_verbatim():
    """Every item name in the quote HTML passes through tItem — the
    verbatim identity pinned on the estimate page covers the quote too."""
    src = _src()
    assert "tItem(l.name, lang)" in src
    assert "tItem(a.name, lang)" in src
    # no name may reach the HTML without tItem
    raw = re.findall(r"esc\((l|a)\.name\)", src)
    assert not raw, f"a name reached the quote HTML untranslated-guarded: {raw}"


def test_quote_has_no_hardcoded_english_between_tags():
    """All quote chrome routes through tFor — a literal English string
    between tags is a string a Spanish homeowner cannot read."""
    src = _src()
    literals = [w for w in re.findall(r">([A-Za-z][A-Za-z ,'&/-]{3,60})<", src)
                if w.strip()]
    assert not literals, f"hardcoded quote strings: {literals}"


def test_quote_money_format_is_language_independent():
    """PENNY PARITY, structural half: one currency formatter, locked —
    the homeowner sees the same figure in either language."""
    src = _src()
    assert 'Intl.NumberFormat("en-US", { style: "currency", currency: "USD" })' in src
    assert src.count("Intl.NumberFormat") == 1, \
        "a second money formatter appeared — parity risk"
    assert "lang" not in src[src.index("const $ ="):src.index("const esc =")], \
        "the money formatter grew a language dependency"


def test_quote_document_language_is_wired():
    src = _src()
    assert 'lang = "en"' in src            # explicit default
    assert "htmlLang" in src               # <html lang> follows sendLang
    assert 'lang === "es"' in src          # locale dates


def test_quote_dictionary_keys_exist_both_languages():
    """quote.* and email.* chrome keys ride the same EN/ES parity detector
    — spot-pin the customer-visible ones here."""
    js = open("/app/frontend/src/lib/dictionaries.js").read()
    en, es = js[js.index("en: {"):js.index("  es: {")], js[js.index("  es: {"):]
    used = set(re.findall(r'tFor\(lang,\s*"([^"]+)"', _src()))
    used |= set(re.findall(r'tFor\(sendLang,\s*"([^"]+)"', _qm()))
    assert used, "no tFor keys found in emailQuote.js / QuoteModal.jsx"
    for key in used:
        assert f'"{key}":' in en, f"quote key missing from en: {key}"
        assert f'"{key}":' in es, f"quote key missing from es: {key}"


# ---- QuoteModal.jsx — the on-screen print preview is the same surface ----

def test_modal_preview_names_route_through_titem_verbatim():
    """The preview the contractor prints mirrors the email: names via
    tItem (verbatim), sections via tSection, units via tUnit — all
    following sendLang, never uiLang."""
    src = _qm()
    assert "tItem(l.name, sendLang)" in src
    assert "tItem(a.name, sendLang)" in src
    assert "tSection(section, sendLang)" in src
    assert "tUnit(l.unit, sendLang)" in src


def test_modal_preview_chrome_follows_send_language():
    """No customer-facing chrome on the print preview may stay hardcoded
    English — each named string Howard ruled MUST-TRANSLATE routes
    through tFor(sendLang, ...)."""
    src = re.sub(r"/\*.*?\*/", "", _qm(), flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    assert 'tFor(sendLang, "' in src
    for literal in ("Prepared For", "Scope of Work", "Total Price",
                    "Customer Signature", "Job Photos",
                    "Per-Elevation Siding Breakdown", "Total Siding Area",
                    "Materials supplied by", "Valid for 30 days"):
        assert literal not in src, \
            f"hardcoded chrome on the print preview: {literal}"


def test_quote_shows_final_cost_only():
    """RULED: the customer quote shows FINAL COST ONLY — no material/
    labor/tax split may reach either quote surface. The only totals
    property either file may render is `sell`."""
    for path in (EQ_PATH, QM_PATH):
        src = open(path).read()
        used = set(re.findall(r"totals\.(\w+)", src))
        assert used == {"sell"}, f"{path} renders a cost split: {used}"
