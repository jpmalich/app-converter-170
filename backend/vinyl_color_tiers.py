"""COLOR TIER DERIVES FROM THE COLOR — PER ROW (Howard ruled 2026-08-02).
The standalone COLOR TIER dropdown is RETIRED: it was a second control for
a decision already made in Material Colors (the one-decision-two-controls
class). Tier is a PRICE TERM, so it derives instead of disappearing:
each row follows ITS OWN color picker —
  · siding row → siding color's tier (brand-gated by the row's own name)
  · outside corners → outside corner color's tier
  · inside corners + finish trim + J-channel → accessories color's tier
  · soffit & fascia + soffit J-channel → soffit/fascia color's tier
A Standard-color corner prices Standard even on an Architectural-siding
house — contractors run architectural siding with white trim on nearly
every two-tone job, and per-row is how the material is actually bought.
CONQUEST IS STANDARD ONLY (ruled): its single unlabeled palette is
correct; a Conquest color never derives Architectural.
The sets below mirror /app/frontend/src/lib/colorOptions.js (the dropdown
source) — a sync test pins the two files together so neither rots alone.
"""
import re

# Architectural collections per brand — VERBATIM from colorOptions.js.
# Conquest has NO entry: standard only (Howard ruled 2026-08-02).
ARCH_BY_BRAND = {
    "coventry": frozenset({
        "Canyon Drift", "Mountain Fern", "Harbor Blue", "Storm",
        "Sterling Gray", "Ageless Slate", "Charcoal Smoke"}),
    "odyssey": frozenset({
        "Fired Brick", "Canyon Drift", "Flagship Brown", "Mountain Fern",
        "Deep Moss", "Harbor Blue", "Midnight Blue", "Storm",
        "Sterling Gray", "Ageless Slate", "Charcoal Smoke"}),
    "charter": frozenset({
        "Fired Brick", "Harbor Blue", "Deep Espresso", "Riviera Dusk",
        "Canyon Drift", "Midnight Blue", "Rustic Timber", "Storm",
        "Mountain Fern", "Deep Moss", "Sterling Gray", "Ageless Slate",
        "Flagship Brown", "Laguna Blue", "Charcoal Smoke", "Cast Iron"}),
}

# Soffit & fascia has its own palette (SOFFIT_COLOR_GROUPS) — its
# Architectural collection is wider than any brand's.
SOFFIT_ARCH = frozenset({
    "Fired Brick", "Canyon Drift", "Flagship Brown", "Deep Espresso",
    "Musket Brown", "Rustic Timber", "Mountain Fern", "Deep Moss",
    "Harbor Blue", "Midnight Blue", "Laguna Blue", "Riviera Dusk",
    "Storm", "Sterling Gray", "Ageless Slate", "Charcoal Smoke",
    "Cast Iron", "Black"})

# Board & Batten profile rows have their own picker (board_batten_color)
# and their own Architectural collection (BOARD_BATTEN_COLOR_GROUPS) —
# found during the 2026-08-02 build: 'vertical board and batten Standard
# color 7"' has an Architectural twin and follows ITS OWN picker, same
# principle as the ruled four.
BOARD_BATTEN_ARCH = frozenset({
    "Fired Brick", "Canyon Drift", "Flagship Brown", "Deep Espresso",
    "Rustic Timber", "Mountain Fern", "Deep Moss", "Harbor Blue",
    "Midnight Blue", "Laguna Blue", "Riviera Dusk", "Storm",
    "Sterling Gray", "Ageless Slate", "Charcoal Smoke", "Cast Iron"})

# Same regexes as frontend brandKeyOf (colorOptions.js / subCategories.js).
_BRAND_RES = (("conquest", re.compile(r"^Conquest ")),
              ("coventry", re.compile(r"^Coventry ")),
              ("odyssey", re.compile(r"^Odyssey ")),
              ("charter", re.compile(r"^Charter Oak ")))

_TIER_SWAPS = (("Standard color", "Architectural color"),
               ("Standard Color", "Architectural color"))


def brand_key_of(item_name: str) -> str | None:
    for key, rx in _BRAND_RES:
        if rx.search(item_name or ""):
            return key
    return None


def _arch_for_brands(brands) -> frozenset:
    out = set()
    for b in brands:
        out |= ARCH_BY_BRAND.get(b, frozenset())  # conquest → nothing
    return frozenset(out)


def apply_row_color_tiers(lines: list, row_colors: dict) -> list:
    """Re-land Standard rows on their Architectural twins ROW BY ROW,
    each driven by its own picker's color. Runs BEFORE _stamp_item_ids so
    the renamed row binds the Architectural item id and its price.
    Empty/standard colors leave everything untouched (byte-identical
    class — tier is unreachable-by-accident, not settable-by-accident)."""
    if not row_colors or not any(row_colors.values()):
        return lines
    active = {b for b in (brand_key_of(l.get("name") or "") for l in lines
                          if float(l.get("qty") or 0) > 0) if b}
    accessory_arch = _arch_for_brands(active or {"charter"})
    for l in lines:
        if (l.get("tab") or "vinyl") not in ("vinyl", "ascend"):
            continue
        name = l.get("name") or ""
        if not any(old in name for old, _ in _TIER_SWAPS):
            continue
        low = name.lower()
        own_brand = brand_key_of(name)
        if own_brand:
            color, arch = row_colors.get("siding"), _arch_for_brands({own_brand})
        elif "board and batten" in low:
            color, arch = row_colors.get("board_batten"), BOARD_BATTEN_ARCH
        elif "soffit" in low:
            color, arch = row_colors.get("soffit_fascia"), SOFFIT_ARCH
        elif "outside corner" in low:
            color, arch = row_colors.get("outside_corner"), accessory_arch
        else:
            color, arch = row_colors.get("accessories"), accessory_arch
        if color and color in arch:
            for old, new in _TIER_SWAPS:
                if old in name:
                    l["name"] = name.replace(old, new)
                    l["note"] = (f"{l.get('note') or ''} — Architectural color "
                                 f"tier (derived from {color})").strip(" —")
                    break
    return lines
