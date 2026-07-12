"""Iter 79j.96 — CONFIDENTIAL DEALER COST LAYER. BlueLinx Pittsburgh
PIT00003 "LP ExpertFinish Dealer Price Pages — Quick Reference 2.26.2026".
HOWARD'S DEALER COST — NEVER render on any contractor-facing surface
(Material List tab, quote PDF, Accept page, shareable links). External
surfaces render SELL only; until margins are set, external price fields
show "pricing pending" — never cost.

PRICING BASIS RULING: cost is keyed off PRODUCT + FINISH, never product
alone. A prefinished (ExpertFinish) color selection changes the line's
cost basis to the ExpertFinish price. A missing finish price = cost
pending — NEVER fall back to mill finish for a prefinished selection.

SKU doctrine: the sheet prints NO item codes — sku stays "pending"
everywhere, never extrapolated. Descriptions ingested verbatim.
Piece prices ingested (UOM: Piece unless noted)."""

QUOTE_REF = "BlueLinx PIT00003 — 2.26.2026"

PREFINISHED_FINISHES = ("expertfinish", "expertfinish_brushed")

# finish keys: mill, third_party_painted, brushed_mill,
#              brushed_third_party, expertfinish, expertfinish_brushed
BLUELINX_COSTS = {
    "38 Series Lap 3/8\" x 8\" x 16'": {"mill": 21.69, "third_party_painted": 23.34, "brushed_mill": 23.21, "brushed_third_party": 24.19, "expertfinish": 32.54, "expertfinish_brushed": 34.82},
    "38 Series Lap 3/8\" x 6\" x 16'": {"mill": 17.19, "third_party_painted": 18.83, "brushed_mill": 18.38, "brushed_third_party": 19.54},
    "NICKEL GAP": {"mill": 50.64, "brushed_mill": 54.18, "expertfinish": 75.96, "expertfinish_brushed": 81.28},
    "Shake": {"mill": 16.62, "third_party_painted": 16.66},
    "190 Series Trim 19/32\" x 3\" x 16'": {"mill": 13.76, "third_party_painted": 20.80, "brushed_mill": 14.72, "expertfinish": 20.64, "expertfinish_brushed": 22.09},
    "440 Series Trim 4/4\" x 4\" x 16'": {"mill": 19.74, "third_party_painted": 23.16, "brushed_mill": 21.13, "brushed_third_party": 24.13, "expertfinish": 29.62, "expertfinish_brushed": 31.69},
    "440 Series Trim 4/4\" x 6\" x 16'": {"mill": 29.62, "third_party_painted": 31.09, "brushed_mill": 31.69, "brushed_third_party": 32.54, "expertfinish": 44.44, "expertfinish_brushed": 47.54},
    "440 Series Trim 4/4\" x 8\" x 16'": {"mill": 39.50, "third_party_painted": 41.86, "brushed_mill": 42.26, "brushed_third_party": 43.80},
    "440 Series Trim 4/4\" x 10\" x 16'": {"mill": 51.47, "third_party_painted": 53.39, "brushed_mill": 55.09, "brushed_third_party": 55.85},
    "440 Series Trim 4/4\" x 12\" x 16'": {"mill": 61.74, "third_party_painted": 62.79, "brushed_mill": 66.08, "brushed_third_party": 65.75},
    "540 Series Trim 5/4\" x 4\" x 16'": {"mill": 24.01, "third_party_painted": 27.54, "brushed_mill": 25.69, "brushed_third_party": 28.79, "expertfinish": 36.01, "expertfinish_brushed": 38.54},
    "540 Series Trim 5/4\" x 6\" x 16'": {"mill": 36.01, "third_party_painted": 37.43, "brushed_mill": 38.54, "brushed_third_party": 39.31, "expertfinish": 54.03, "expertfinish_brushed": 57.81},
    "540 Series Trim 5/4\" x 8\" x 16'": {"mill": 48.01, "third_party_painted": 50.66, "brushed_mill": 51.37, "brushed_third_party": 53.21, "expertfinish": 72.03, "expertfinish_brushed": 77.08},
    "540 Series Trim 5/4\" x 10\" x 16'": {"mill": 62.87, "third_party_painted": 64.06, "brushed_mill": 67.27, "brushed_third_party": 67.26},
    "540 Series Trim 5/4\" x 12\" x 16'": {"mill": 75.41, "third_party_painted": 75.09, "brushed_mill": 80.68, "brushed_third_party": 78.90, "expertfinish": 113.10, "expertfinish_brushed": 121.03},
    "38 Series Soffit 12 x 16 Vented": {"mill": 45.05, "third_party_painted": 53.05, "brushed_mill": 48.21},
    "38 Series Soffit 12 x 16 Closed": {"mill": 41.87, "third_party_painted": 51.33, "brushed_mill": 44.79, "brushed_third_party": 53.46},
    "38 Series Soffit 16 x 16 Vented": {"mill": 60.08, "third_party_painted": 69.66, "brushed_mill": 64.27},
    "38 Series Soffit 16 x 16 Closed": {"mill": 51.45, "third_party_painted": 67.54, "brushed_mill": 55.05, "brushed_third_party": 70.36, "expertfinish": 77.18, "expertfinish_brushed": 82.60},
    "24 inch CTW soffit": {"mill": 87.46, "third_party_painted": 102.05, "brushed_mill": 93.58, "brushed_third_party": 106.29},
    "24 inch VSSFT": {"mill": 93.95, "third_party_painted": 104.53, "brushed_mill": 100.51},
    "38 Series Vertical Panel": {"mill": 51.45, "third_party_painted": 56.21, "brushed_mill": 55.05, "brushed_third_party": 58.48, "expertfinish": 77.18, "expertfinish_brushed": 82.60},
    "38 Series 4' x 8' Panel": {"mill": 72.13, "third_party_painted": 84.76, "brushed_mill": 75.32},
    "38 Series 4' x 10' Panel": {"mill": 96.56, "third_party_painted": 111.35, "brushed_mill": 103.33},
    "540 Series OSC 5/4\" x 4\" x 16'": {"mill": 126.78, "third_party_painted": 263.24, "brushed_mill": 135.65},
    # sheet prints length as 192' — 192" = 16', consistent with the stick-length ruling
    "540 Series OSC 5/4\" x 6\" x 16'": {"mill": 190.18, "third_party_painted": 327.68, "brushed_mill": 203.49},
    "Touch up kits": {"mill": 42.67},
    "OSI Quad Max Caulking": {"mill": 9.82},
    "J blocks": {"mill": 40.00},
    "Mini Splits": {"mill": 56.00},
}


import math
import re as _re

_NORM_RE = _re.compile(r"\s+")


def _norm(name) -> str:
    return _NORM_RE.sub(" ", str(name or "").strip().lower())


_COSTS_NORM = {_norm(k): v for k, v in BLUELINX_COSTS.items()}

# ── MARGIN ARCHITECTURE — FINAL (Howard ruling, 2026): named tiers in
# SUPPLIER ADMIN, all TRUE MARGIN: sell = cost ÷ (1 − tier%). NOT markup.
# Tier B = 25% is the global default. Percentages editable ONLY in admin;
# quotes carry a tier PICKER (no free-type margin field, ever).
# Resolution: line override > category override > quote's tier.
# Per-contractor pricing OUT of scope until post-September (PRD backlog).
MARGIN_TIER_SEED = {"A": 30.0, "B": 25.0, "C": 20.0}
DEFAULT_TIER = "B"

# Confidential keys — stripped from EVERY contractor/customer-facing
# payload by redact_external(). Cost, margins, tier identity, and the
# dealer-sheet provenance never render externally.
CONFIDENTIAL_KEYS = frozenset({
    "unit_cost", "line_cost", "total_cost", "cost_basis",
    "cost_pending_reason", "margin_pct", "tier", "tier_pct", "tiers",
    "default_tier", "category_overrides", "line_overrides",
    "quote_ref", "basis_doctrine",
})


def cost_for(item_name: str, finish: str):
    """Strict (product, finish) lookup. Returns None when the selected
    finish has no sheet price — cost: pending. NEVER falls back to mill
    for a prefinished selection (pinned). Name match is whitespace/case
    tolerant (catalog 'Nickel Gap' ↔ sheet 'NICKEL GAP'), never fuzzy."""
    prices = BLUELINX_COSTS.get(item_name) or _COSTS_NORM.get(_norm(item_name))
    if not prices:
        return None
    return prices.get(finish)


def sell_price(cost: float, margin_pct: float) -> float:
    """MARGIN RULING (pinned direction): TRUE MARGIN on sell —
    sell = cost ÷ (1 − m). A 25% markup (× 1.25) is WRONG and lands lower:
    cost 75 @ 25% margin = 100.00, not 93.75."""
    m = float(margin_pct) / 100.0
    if not (0.0 <= m < 1.0):
        raise ValueError(f"margin_pct out of range: {margin_pct}")
    return round(float(cost) / (1.0 - m), 2)


def resolve_margin_pct(cfg: dict, tier_name: str, line_name=None, category=None) -> float:
    """Resolution order (ruled): line > category > quote tier. Tiers are
    the primary mechanism; overrides are scaffold, empty until populated."""
    lo = cfg.get("line_overrides") or {}
    if line_name in lo:
        return float(lo[line_name])
    co = cfg.get("category_overrides") or {}
    if category in co:
        return float(co[category])
    tiers = cfg.get("tiers") or MARGIN_TIER_SEED
    return float(tiers[tier_name])


def _mark_pending(line: dict, reason: str):
    line["pricing_status"] = "pending"
    line["cost_pending_reason"] = reason
    line["unit_sell"] = None
    line["line_sell"] = None


def price_package(pkg: dict, cfg: dict, tier_name=None) -> dict:
    """Attach the confidential cost layer + sell prices to an assembled
    LP package IN PLACE. Caller MUST pass the result through
    redact_external() before returning it on any contractor-facing
    surface. Starter rip stock is priced from its source SKU at the
    SIDING group's color basis (the boards come from siding stock)."""
    tiers = cfg.get("tiers") or dict(MARGIN_TIER_SEED)
    tier = tier_name if tier_name in tiers else (cfg.get("default_tier") or DEFAULT_TIER)
    group_colors = (pkg.get("summary") or {}).get("group_colors") or {}
    total_cost = total_sell = 0.0
    priced = pending = 0
    for l in pkg.get("lines") or []:
        is_rip = bool(l.get("source_sku"))
        name = l["source_sku"] if is_rip else l.get("name")
        color = group_colors.get("siding") if is_rip else l.get("color")
        basis = finish_basis_for_color(color)
        margin_pct = resolve_margin_pct(cfg, tier, line_name=l.get("name"),
                                        category=l.get("section"))
        l["margin_pct"] = margin_pct
        if basis == "pending":
            _mark_pending(l, "primed cost basis pending — never assumed mill (ruled)")
            pending += 1
            continue
        l["cost_basis"] = basis
        unit_cost = cost_for(name, basis)
        if unit_cost is None:
            if basis in PREFINISHED_FINISHES:
                reason = (f"no dealer cost on {QUOTE_REF} for this product at ExpertFinish — "
                          "cost pending; NEVER falls back to mill for a prefinished selection (ruled)")
            else:
                reason = f"no dealer cost on {QUOTE_REF} for this product — cost pending"
            _mark_pending(l, reason)
            pending += 1
            continue
        try:
            q = float((l.get("pieces_added") if is_rip else l.get("qty")) or 0)
        except (TypeError, ValueError):
            q = 0.0
        l["unit_cost"] = unit_cost
        l["line_cost"] = round(unit_cost * q, 2)
        l["unit_sell"] = sell_price(unit_cost, margin_pct)
        l["line_sell"] = round(l["unit_sell"] * q, 2)
        l["pricing_status"] = "priced"
        if is_rip:
            l["priced_unit"] = "per ripped source board"
        total_cost += l["line_cost"]
        total_sell += l["line_sell"]
        priced += 1
    pkg.setdefault("summary", {})["pricing"] = {
        "tier": tier,
        "tier_pct": float(tiers.get(tier, MARGIN_TIER_SEED[DEFAULT_TIER])),
        "quote_ref": QUOTE_REF,
        "basis_doctrine": ("cost keyed by product + finish; sell = cost ÷ (1 − margin) — "
                           "true margin on sell, never markup; resolution line > category > tier"),
        "total_cost": round(total_cost, 2),
        "total_sell": round(total_sell, 2),
        "priced_lines": priced,
        "pending_lines": pending,
    }
    return pkg


def redact_external(obj):
    """Deep-strip every confidential key from a payload bound for any
    contractor/customer-facing surface. The external view keeps
    unit_sell / line_sell / pricing_status / total_sell only."""
    if isinstance(obj, dict):
        return {k: redact_external(v) for k, v in obj.items() if k not in CONFIDENTIAL_KEYS}
    if isinstance(obj, list):
        return [redact_external(v) for v in obj]
    return obj


def finish_basis_for_color(color) -> str:
    """A prefinished ExpertFinish color selection changes the cost basis
    to the ExpertFinish price; primed is its own basis question (pending,
    never assumed mill); no color = mill."""
    if not color:
        return "mill"
    if str(color).startswith("Primed"):
        return "pending"
    return "expertfinish"
