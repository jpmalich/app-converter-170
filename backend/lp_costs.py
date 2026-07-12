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


def cost_for(item_name: str, finish: str):
    """Strict (product, finish) lookup. Returns None when the selected
    finish has no sheet price — cost: pending. NEVER falls back to mill
    for a prefinished selection (pinned)."""
    prices = BLUELINX_COSTS.get(item_name)
    if not prices:
        return None
    return prices.get(finish)


def finish_basis_for_color(color) -> str:
    """A prefinished ExpertFinish color selection changes the cost basis
    to the ExpertFinish price; primed is its own basis question (pending,
    never assumed mill); no color = mill."""
    if not color:
        return "mill"
    if str(color).startswith("Primed"):
        return "pending"
    return "expertfinish"
