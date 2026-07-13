"""Iter 79j.95 — COLOR ARCHITECTURE (Howard ruling, lands before Phase 2
selector design). Color is a PER-COMPONENT, LINE-LEVEL attribute, not a
job-level setting:
  (1) every material line carries its own color field; same profile +
      different color = different SKU — consolidation splits on color;
  (2) selector assigns color per component group (siding / soffit+fascia /
      opening trim / OSC / ISC) with an "apply to all" convenience —
      job-level single color is the shortcut, not the model;
  (3) 3D flat-color repaint targets component mesh groups independently;
  (4) color availability per product line is PENDING verification against
      LP's published ExpertFinish matrix — never assume every color exists
      in every profile; FLAG unavailable combinations, never silently
      substitute.
Palette source: LP's published ExpertFinish page (verified 2026-06)."""
from lp_conventions import FASCIA_RAKE_ITEM, ISC_TRIM_ITEM, WRAP_TRIM_ITEM

EXPERTFINISH_CORE_16 = [
    "Sand Dunes",          # 2026 Color of the Year
    "Snowscape White", "Desert Stone", "Quarry Gray", "Prairie Clay",
    "Garden Sage", "Harvest Honey", "Terra Brown", "Timberland Suede",
    "Tundra Gray", "Cavern Steel", "Summit Blue", "Rapids Blue",
    "Midnight Shadow", "Abyss Black", "Redwood Red",
]
NATURALS_COLLECTION = [
    "Bonsai Black", "Weathered Walnut", "Aged Amber",
    "Saffron Cedar", "Smoky Slate", "Washed White",
]
PRIMED = "Primed (paint any color)"
ALL_COLORS = EXPERTFINISH_CORE_16 + NATURALS_COLLECTION + [PRIMED]

COMPONENT_GROUPS = ("siding", "soffit_fascia", "opening_trim", "osc", "isc")

# Availability now ingested from LP's PUBLISHED matrix (2026-07-13) —
# see lp_expertfinish_matrix.py. Dealer/BlueLinx verification pending;
# combos flag per status: unsupported (published-absent) / gap (published
# ambiguity). Never silently substituted.
AVAILABILITY_VERIFIED = "published-ingested"
AVAILABILITY_FLAG = ("color availability per published ExpertFinish matrix — "
                     "dealer verification pending; flagged, never silently substituted")


def group_for_line(line: dict):
    name = str(line.get("name") or "")
    section = str(line.get("section") or "")
    if name == FASCIA_RAKE_ITEM or "Soffit" in name:
        return "soffit_fascia"
    if "OSC" in name:
        return "osc"
    if name == ISC_TRIM_ITEM:
        return "isc"
    if name == WRAP_TRIM_ITEM:
        return "opening_trim"
    if section == "LP Smart Siding":
        return "siding"
    return None


def resolve_group_colors(colors: dict | None):
    """{"all": X} is the shortcut; per-group keys override it. Unknown
    colors and unknown groups are refused (never invented)."""
    errors = []
    resolved = {g: None for g in COMPONENT_GROUPS}
    if not colors:
        return resolved, errors
    base = colors.get("all")
    if base is not None:
        if base in ALL_COLORS:
            resolved = {g: base for g in COMPONENT_GROUPS}
        else:
            errors.append(f"'{base}': not in the published ExpertFinish palette — refused")
    for k, v in colors.items():
        if k == "all":
            continue
        if k not in COMPONENT_GROUPS:
            errors.append(f"'{k}': unknown component group — refused")
            continue
        if v not in ALL_COLORS:
            errors.append(f"{k} → '{v}': not in the published ExpertFinish palette — refused")
            continue
        resolved[k] = v
    return resolved, errors


def apply_colors(lines: list, colors: dict | None):
    """Every material line carries its own color field (None when no
    group color assigned). Returns (resolved_group_colors, errors)."""
    resolved, errors = resolve_group_colors(colors)
    from lp_expertfinish_matrix import check_combo
    for l in lines:
        g = group_for_line(l)
        l["component_group"] = g
        c = resolved.get(g) if g else None
        l["color"] = c
        if c:
            res = check_combo(l.get("name") or "", c)
            l["color_status"] = res["status"]
            if res["status"] == "unsupported":
                l["color_flags"] = [f"UNSUPPORTED COMBINATION: {res['note']}"]
            elif res["status"] == "gap":
                l["color_flags"] = [f"AVAILABILITY GAP: {res['note']}"]
            else:
                l.pop("color_flags", None)
    return resolved, errors


def consolidate_lines(lines: list) -> list:
    """Line identity = (name, color): same profile + different color =
    different SKU — NEVER merges across colors."""
    out = []
    index = {}
    for l in lines:
        key = (l.get("name"), l.get("color"))
        if key in index and isinstance(l.get("qty"), (int, float)):
            index[key]["qty"] = (index[key].get("qty") or 0) + (l.get("qty") or 0)
        else:
            index[key] = l
            out.append(l)
    return out
