"""LP ExpertFinish color-by-product-line AVAILABILITY MATRIX.

INGESTED 2026-07-13 from LP's PUBLISHED sources (lpcorp.com ExpertFinish
color pages, contractor checklist, product-line pages).
DEALER-VERIFIED — Howard's dealer-reality verification COMPLETE, all six
open items resolved (incl. BlueLinx cross-check): matrix is dealer-true;
"available" = orderable through the dealer.

Resolved rulings (verbatim intent):
  1. Garden Sage: REAL, current ExpertFinish color — panels available.
  2. Naturals: run in EXACTLY the NATURALS_PROFILES list below; combos
     outside it flag unsupported.
  3. Shakes + vertical/B&B: all ExpertFinish colors, all regions —
     regional-ambiguity flags cleared.
  4. Trim: ALL ExpertFinish colors run in all quoted trim profiles —
     the corner-color-doesn't-exist failure mode is off the table.
  5. BlueLinx cross-check: all ExpertFinish colors orderable — no
     published-but-not-stocked entries at this time.
  6. Stocked-vs-published policy: SAME flag treatment — one amber
     vocabulary for all availability caveats, no special-order badge.

Doctrine (standing ruling): unsupported combinations FLAG — never
silently substitute. Ambiguity is a GAP, not an assumption.
"""
from lp_colors import EXPERTFINISH_CORE_16, NATURALS_COLLECTION, PRIMED

MATRIX_STATUS = ("dealer-verified (Howard, incl. BlueLinx cross-check) — "
                 "matrix is dealer-true; 'available' = orderable")

_CORE = frozenset(EXPERTFINISH_CORE_16)
_NATURALS = frozenset(NATURALS_COLLECTION)

# Per product family: colors available (dealer-verified), colors with
# unresolved ambiguity (none remain for core), and a note.
FAMILIES = {
    "lap": {
        "available": _CORE,
        "ambiguous": frozenset(),
        "note": "all 16 core colors for lap (cedar + brushed smooth; 16' lengths) — dealer-verified",
    },
    "trim": {
        "available": _CORE,
        "ambiguous": frozenset(),
        "note": "all 16 core colors run in all quoted trim profiles (540 5/4x6 OSC, 540 5/4x4, 440 4/4x8) — dealer-verified",
    },
    "vertical": {
        "available": _CORE,
        "ambiguous": frozenset(),
        "note": "all 16 core colors, all regions — dealer-verified (regional ambiguity cleared)",
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
        "available": frozenset({"Snowscape White", "Abyss Black", "Garden Sage"}),
        "ambiguous": frozenset(),
        "note": "panels in Snowscape White + Abyss Black + Garden Sage — dealer-verified (Garden Sage ambiguity resolved)",
    },
    "shakes": {
        "available": _CORE,
        "ambiguous": frozenset(),
        "note": "all 16 core colors, all regions — dealer-verified (regional ambiguity cleared)",
    },
}

# Naturals Collection: dealer-verified AUTHORITATIVE profile list —
# Naturals finishes run in EXACTLY these products; anything outside
# flags unsupported.
NATURALS_PROFILES = frozenset({
    '38 Series Lap 3/8" x 8" x 16\'',
    "Nickel Gap",
    '190 Series Trim 19/32" x 3" x 16\'',
    '440 Series Trim 4/4" x 4" x 16\'',
    '440 Series Trim 4/4" x 6" x 16\'',
    '540 Series Trim 5/4" x 4" x 16\'',
    '540 Series Trim 5/4" x 6" x 16\'',
    '540 Series Trim 5/4" x 8" x 16\'',
    '540 Series Trim 5/4" x 12" x 16\'',
    "38 Series Soffit 16 x 16 Closed",
    "38 Series Vertical Panel",
})

# Catalog cross-check (ruled: Naturals-scoped profiles must be quotable
# or flagged `catalog: pending`, never silently missing). 16x16 Closed
# soffit runs Naturals per the dealer but was dropped from the catalog
# in Iter 78x (Feb 2026 supplier sheet no longer ships it) — pending.
NATURALS_CATALOG_PENDING = frozenset({"38 Series Soffit 16 x 16 Closed"})

# Starter is field-ripped from lap siding stock — its color availability
# follows the lap profile it is ripped from.
_STARTER_LAP_PROFILE = '38 Series Lap 3/8" x 8" x 16\''


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
    n = str(item_name or "")
    if color in _NATURALS:
        profile = _STARTER_LAP_PROFILE if "starter" in n.lower() else n
        if profile in NATURALS_PROFILES:
            if profile in NATURALS_CATALOG_PENDING:
                return {"status": "gap",
                        "note": (f"'{profile}' runs Naturals (dealer-verified) but is "
                                 "catalog: pending — not on the current supplier sheet; "
                                 "never silently missing")}
            return {"status": "available",
                    "note": "Naturals Collection — dealer-verified profile list"}
        return {"status": "unsupported",
                "note": (f"'{color}' (Naturals) not offered on '{n}' — outside the "
                         "dealer-verified Naturals profile list; flagged per ruling, "
                         "never silently substituted")}
    fam = family_for_item(n)
    if fam is None:
        return {"status": "gap",
                "note": f"'{n}': product family not in the matrix — verify with dealer"}
    f = FAMILIES[fam]
    if color in f["available"]:
        return {"status": "available", "note": f["note"]}
    if color in f["ambiguous"]:
        return {"status": "gap",
                "note": f"'{color}' on {fam}: unresolved ambiguity — {f['note']}"}
    return {"status": "unsupported",
            "note": (f"'{color}' NOT available for {fam} ({f['note']}) — "
                     "flagged per ruling, never silently substituted")}
