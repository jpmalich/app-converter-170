"""Mezzo (3000 Series) replacement-window catalog.

Distinct from the Vero catalog in `catalog_seed.py` because Mezzo pricing
is a per-tier × per-size-bucket × per-adder matrix (Vero adders are flat
per-product-type). Lives in its own module so it can grow to cover
Fusion / Preservation / Sovereign without crowding the siding catalog.

Phase 1 (Iter 37): Mezzo Double Hung only. Howard will fill in the
per-tier prices via the Pricing Admin once he likes the W×H entry UX.

Size buckets are taken straight from the Mezzo wholesale Excel — each
bucket lists the min/max UI (United Inches = width + height). Tempered
Full is the only sqft-based adder: cost = $9.18 × (W × H / 144). All
other adders are flat per-window at the bucket's listed price.
"""
from typing import Optional

MEZZO_TIER_NAMES = ["whole-sale", "Contractor", "Builder-Dealer", "one-opp"]

# Size buckets ordered by min UI. Same buckets for every Mezzo product
# type at Phase 1; future product types may override this list.
MEZZO_DH_BUCKETS = [
    {"label": "32-73 UI",   "min_ui": 32,  "max_ui": 73},
    {"label": "74-83 UI",   "min_ui": 74,  "max_ui": 83},
    {"label": "84-93 UI",   "min_ui": 84,  "max_ui": 93},
    {"label": "94-101 UI",  "min_ui": 94,  "max_ui": 101},
    {"label": "102-103 UI", "min_ui": 102, "max_ui": 103},
    {"label": "104-105 UI", "min_ui": 104, "max_ui": 105},
    {"label": "106-107 UI", "min_ui": 106, "max_ui": 107},
    {"label": "108-109 UI", "min_ui": 108, "max_ui": 109},
    {"label": "110-111 UI", "min_ui": 110, "max_ui": 111},
    {"label": "112-120 UI", "min_ui": 112, "max_ui": 120},
    {"label": "121-126 UI", "min_ui": 121, "max_ui": 126},
    {"label": "127-132 UI", "min_ui": 127, "max_ui": 132},
    {"label": "133-148 UI", "min_ui": 133, "max_ui": 148},
]

# Per-tier base window mat prices keyed by bucket label. All $0 at
# Phase 1 — supplier admin fills in via the Pricing Admin once the
# layout is approved.
def _zero_priced_by_bucket(buckets):
    return {b["label"]: 0.0 for b in buckets}


MEZZO_DH_TIER_PRICES = {
    tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES
}

# Adders. `kind` is "flat" (per-window cost from prices_by_bucket) or
# "sqft" (rate × sqft of the opening, independent of bucket). For sqft
# adders the rate is the same across all tiers per Howard's Mezzo sheet.
MEZZO_DH_ADDERS = [
    {
        "name": "Extruded Beige or Clay",
        "kind": "flat",
        "tier_prices": {tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES},
    },
    {
        "name": "ClimaTech Plus - 9E",
        "kind": "flat",
        "tier_prices": {tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES},
    },
    {
        "name": "ClimaTech TG2 Plus",
        "kind": "flat",
        "tier_prices": {tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES},
    },
    {
        "name": "Obscure Full",
        "kind": "flat",
        "tier_prices": {tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES},
    },
    {
        # Tempered Full is sqft-based per Howard: $9.18 × (W × H / 144).
        # No flat per-window charge — the rate IS the entire cost.
        "name": "Tempered Full",
        "kind": "sqft",
        "rate": 9.18,
    },
    {
        "name": 'NAILFIN 1 3/8" W/ J',
        "kind": "flat",
        "tier_prices": {tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES},
    },
    {
        "name": "Black Exterior Paint",
        "kind": "flat",
        "tier_prices": {tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES},
    },
    {
        "name": "Cherry Laminate",
        "kind": "flat",
        "tier_prices": {tier: _zero_priced_by_bucket(MEZZO_DH_BUCKETS) for tier in MEZZO_TIER_NAMES},
    },
]

# Product types live in this dict; Phase 1 has only Double Hung. Future
# product types (2-Lite, 3-Lite, Picture) plug in here with their own
# bucket lists + adder matrices.
MEZZO_PRODUCT_TYPES = {
    "Mezzo Double Hung": {
        "buckets": MEZZO_DH_BUCKETS,
        "tier_prices": MEZZO_DH_TIER_PRICES,
        "adders": MEZZO_DH_ADDERS,
    },
}


def find_bucket(product_type: str, ui: float) -> Optional[dict]:
    """Return the bucket whose min_ui <= ui <= max_ui, or None."""
    pt = MEZZO_PRODUCT_TYPES.get(product_type)
    if not pt:
        return None
    for b in pt["buckets"]:
        if b["min_ui"] <= ui <= b["max_ui"]:
            return b
    return None


def base_price(product_type: str, tier: str, ui: float) -> float:
    """Look up the base mat price for an opening at this UI on the
    given tier. Returns 0 if out of bucket range."""
    bucket = find_bucket(product_type, ui)
    if not bucket:
        return 0.0
    pt = MEZZO_PRODUCT_TYPES[product_type]
    return float(pt["tier_prices"].get(tier, {}).get(bucket["label"], 0.0))


def adder_price(product_type: str, adder_name: str, tier: str, width: float, height: float) -> float:
    """Look up adder price for an opening. For 'sqft' adders, returns
    rate × (W × H / 144). For 'flat' adders, returns the bucket price."""
    pt = MEZZO_PRODUCT_TYPES.get(product_type)
    if not pt:
        return 0.0
    ad = next((a for a in pt["adders"] if a["name"] == adder_name), None)
    if not ad:
        return 0.0
    if ad["kind"] == "sqft":
        sqft = (float(width) * float(height)) / 144.0
        return float(ad.get("rate", 0)) * sqft
    ui = float(width) + float(height)
    bucket = find_bucket(product_type, ui)
    if not bucket:
        return 0.0
    return float(ad["tier_prices"].get(tier, {}).get(bucket["label"], 0.0))


def catalog_for_tier(tier: str) -> dict:
    """Return a frontend-friendly catalog snapshot for a single tier.
    Shape:
      { "product_types": [
          { "name": "Mezzo Double Hung",
            "buckets": [...],
            "base_prices": {bucket_label: mat},
            "adders": [{name, kind, prices_by_bucket | rate}, ...] }
        ]
      }
    """
    out = []
    for name, pt in MEZZO_PRODUCT_TYPES.items():
        adders_out = []
        for a in pt["adders"]:
            if a["kind"] == "sqft":
                adders_out.append({"name": a["name"], "kind": "sqft", "rate": float(a["rate"])})
            else:
                adders_out.append({
                    "name": a["name"],
                    "kind": "flat",
                    "prices_by_bucket": {
                        b["label"]: float(a["tier_prices"].get(tier, {}).get(b["label"], 0))
                        for b in pt["buckets"]
                    },
                })
        out.append({
            "name": name,
            "buckets": pt["buckets"],
            "base_prices": {
                b["label"]: float(pt["tier_prices"].get(tier, {}).get(b["label"], 0))
                for b in pt["buckets"]
            },
            "adders": adders_out,
        })
    return {"product_types": out}
