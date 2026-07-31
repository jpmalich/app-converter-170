"""SKU NAMES NEVER TRANSLATE (Howard ruled 2026-07-31).

"The product name is the same string in English and Spanish. Labels,
headings and descriptors around it translate; the name itself never
does." This protects price binding from the second language — the same
reason a rename is dangerous (ID binding retires the class next).
ITEMS_ES (84 render-time catalog-name translations, incl. AMI-numbered
SKU rows) is RETIRED.
"""
import re
from pathlib import Path

FE = Path("/app/frontend/src")
CT = (FE / "lib/catalogTranslations.js").read_text()


def _fn_body(src, name):
    m = re.search(rf"export function {name}\([^)]*\) \{{(.*?)\n\}}", src, re.S)
    assert m, f"{name} not found"
    return m.group(1)


def test_items_es_is_retired():
    assert "const ITEMS_ES" not in CT, \
        "ITEMS_ES must stay retired — SKU names render verbatim in every language"
    assert "ITEMS_ES RETIRED" in CT, "the ruling note must stand where the dict was"


def test_titem_never_branches_on_language():
    body = _fn_body(CT, "tItem")
    code = "\n".join(l for l in body.splitlines() if not l.strip().startswith("//"))
    assert "ITEMS_ES" not in code and '"es"' not in code and "lang" not in code, \
        "tItem must return the canonical name VERBATIM regardless of language"
    assert "ITEM_NAME_ALIASES" in code, \
        "legacy-alias canonicalization stays — identity healing, not translation"


def test_labels_around_the_name_still_translate():
    # The ruling cuts NAMES only — sections, units, colors are descriptors.
    assert "const SECTIONS_ES" in CT
    assert "const UNITS_ES" in CT and '"ROLL": "ROLLO"' in CT
    assert "const COLORS_ES" in CT


def test_spanish_help_lives_in_descriptions_not_names():
    desc = (FE / "lib/itemDescriptions.js").read_text()
    assert "es:" in desc, \
        "ES item help stays in itemDescriptions (secondary text under the row)"


def test_no_other_surface_translates_item_names():
    # No frontend module may reintroduce a name-translation map.
    for p in FE.rglob("*.js*"):
        if "node_modules" in str(p) or p.name == "catalogTranslations.js":
            continue
        src = p.read_text()
        assert "ITEMS_ES" not in src, f"{p} reintroduces catalog-name translation"
