"""LP ExpertFinish color-by-product-line AVAILABILITY MATRIX.

INGESTED 2026-07-13 from LP's PUBLISHED sources (ruled: publish-first,
flag gaps, never guess):
  - lpcorp.com ExpertFinish color pages + product catalog
  - LP SmartSide ExpertFinish contractor checklist
  - LP product-line pages (lap siding / trim / soffit)
Status: PUBLISHED-INGESTED — dealer-reality + BlueLinx sheet verification
by Howard pending; only gaps publishing doesn't cover get filled by him.

Doctrine (standing ruling): unsupported combinations FLAG — never
silently substitute. Ambiguity is a GAP, not an assumption.
"""
from lp_colors import EXPERTFINISH_CORE_16, NATURALS_COLLECTION, PRIMED

MATRIX_STATUS = ("published-ingested 2026-07-13 (lpcorp.com) — "
                 "dealer/BlueLinx verification pending")

_CORE = frozenset(EXPERTFINISH_CORE_16)
_NATURALS = frozenset(NATURALS_COLLECTION)

# Per product family: colors explicitly published as available, colors
# published with ambiguity (regional / "some" / "typically"), and a note.
FAMILIES = {
    "lap": {
        "available": _CORE,
        "ambiguous": frozenset(),
        "note": "all 16 core colors published for lap (cedar + brushed smooth; 16' lengths)",
    },
    "trim": {
        "available": _CORE,
        "ambiguous": frozenset(),
        "note": "all 16 core colors published for trim — STANDARD SIZES only (published qualifier)",
    },
    "vertical": {
        "available": frozenset(),
        "ambiguous": _CORE,
        "note": "published as 'all 16 in select regions/sizes' — regional ambiguity, verify with dealer",
    },
    "soffit_12_16": {
        "available": frozenset({"Snowscape White"}),
        "ambiguous": frozenset(),
        "note": "published: 12\" & 16\" soffit in Snowscape White ONLY",
    },
    "soffit_24": {
        "available": frozenset({"Snowscape White", "Abyss Black", "Sand Dunes", "Quarry Gray"}),
        "ambiguous": frozenset(),
        "note": "published: 24\" soffit in 4 colors",
    },
    "panel": {
        "available": frozenset({"Snowscape White", "Abyss Black"}),
        "ambiguous": frozenset({"Garden Sage"}),
        "note": "published: panels typically Snowscape White + Abyss Black; Garden Sage 'some' — verify",
    },
    "shakes": {
        "available": frozenset(),
        "ambiguous": frozenset({"Desert Stone", "Snowscape White", "Abyss Black"}),
        "note": "published: shake colors 'depending on region' — all regional, verify with dealer",
    },
}

# Naturals Collection: published as portfolio colors (cedar + brushed
# smooth) WITHOUT a per-product availability table → GAP on every family.
NATURALS_GAP_NOTE = ("Naturals Collection per-product availability not published "
                     "— gap, verify with dealer (never assumed)")


def family_for_item(name: str):
    n = str(name or "")
    low = n.lower()
    if "soffit" in low:
        return "soffit_24" if "24" in n else "soffit_12_16"
    if "vertical" in low:
        return "vertical"
    if "panel" in low:
        return "panel"
    if "shake" in low:
        return "shakes"
    if "lap" in low or "starter" in low:  # starter is field-ripped lap stock
        return "lap"
    if "440 series" in low or "540 series" in low or "osc" in low or "trim" in low:
        return "trim"
    return None


def check_combo(item_name: str, color: str) -> dict:
    """→ {status: available|unsupported|gap, note}. Flag, never substitute."""
    if not color or color == PRIMED:
        return {"status": "available",
                "note": "primed — paint any color (not an ExpertFinish combo)"}
    fam = family_for_item(item_name)
    if fam is None:
        return {"status": "gap",
                "note": f"'{item_name}': product family not in the published matrix — verify with dealer"}
    if color in _NATURALS:
        return {"status": "gap", "note": NATURALS_GAP_NOTE}
    f = FAMILIES[fam]
    if color in f["available"]:
        return {"status": "available", "note": f["note"]}
    if color in f["ambiguous"]:
        return {"status": "gap",
                "note": f"'{color}' on {fam}: published with ambiguity — {f['note']}"}
    return {"status": "unsupported",
            "note": (f"'{color}' NOT published for {fam} ({f['note']}) — "
                     "flagged per ruling, never silently substituted")}
