"""Vero Series catalog metadata — buckets, sister colors, adders.

After Iter 44 the Vero pricing model mirrors Mezzo 1:1:
  - One `base_prices` matrix per (tier, product_type, bucket)
  - One `adder_prices` matrix per (tier, product_type, adder_name, bucket)
  - All adders are flat (no sqft-based rate on Vero)
  - Patio Door stays fixed-model (just base prices on 3 panel sizes)

Iter 78y (2026-02-13): collapsed to match Howard's master pricing file:
  - 3 tiers only (one-opp removed); fall back to Builder-Dealer for
    new estimates created by one-opp companies.
  - 3 product types only: Double Hung, 2-Lite Slider, Patio Door.
    3-Lite Slider + Picture dropped per Howard's directive (master file
    doesn't carry them anymore).
  - DH + Slider use a single UI bucket "0-101" (was 14 buckets).
  - 8 cost-basis adders replace the previous 12.
  - All prices computed from cost via gross-margin formula:
    sell = cost / (1 - margin%) with margins 35% / 30% / 25%.

This file is the structural source of truth. Prices live in Mongo
(seeded from `vero_seed_prices.json` on first boot; force-refreshed
on every boot via the Iter 78y migration in services.py).
"""
from __future__ import annotations
from typing import Optional

# Iter 78y — one-opp removed from Vero. Companies on the one-opp tier
# fall back to Builder-Dealer pricing for any new Vero estimates
# (see vero_prices.get_prices fallback). Saved snapshots keep their
# original prices.
VERO_TIER_NAMES = ["whole-sale", "Contractor", "Builder-Dealer"]


# ──────────────────── Bucket helpers ────────────────────

def parse_bucket_label(label: str) -> tuple[int, int]:
    """'Min-73' → (0, 73). '74-83' → (74, 83). '161-170' → (161, 170)."""
    s = label.strip()
    if "-" not in s:
        return (0, 0)
    left, right = s.split("-", 1)
    try:
        lo = 0 if left.strip().lower().startswith("min") else int(left.strip())
        hi = int(right.strip())
        return (lo, hi)
    except ValueError:
        return (0, 0)


def buckets_to_objects(labels: list[str]) -> list[dict]:
    return [
        {"label": L, "min_ui": parse_bucket_label(L)[0], "max_ui": parse_bucket_label(L)[1]}
        for L in labels
    ]


# ──────────────────── Adder names per product ────────────────────

# Iter 78y — Vero adders replaced per Howard's master pricing file.
# DH + 2-Lite Slider share the same 8-adder list. Patio Door has none.
# Display order is the order in the master Excel (left → right) which
# Howard wants preserved in the UI.
VERO_ADDER_NAMES = {
    "Vero Double Hung": [
        "Quattro .25 U Factor 2 coats LoE",
        "Elite TG2 .24 U Factor 1 coat",
        "TG2 Triple Pane/Argon .19 U Factor",
        "Head Expander 0-101",
        "Grids",
        "Sentry System - Tilt Lock upgrade",
        "Integral Nail Fin 0-101",
        "Heavy Duty 1/2 Screen White ONLY",
    ],
    "Vero 2-Lite Slider": [
        "Quattro .25 U Factor 2 coats LoE",
        "Elite TG2 .24 U Factor 1 coat",
        "TG2 Triple Pane/Argon .19 U Factor",
        "Head Expander 0-101",
        "Grids",
        "Sentry System - Tilt Lock upgrade",
        "Integral Nail Fin 0-101",
        "Heavy Duty 1/2 Screen White ONLY",
    ],
    "Vero Patio Door": [],  # fixed-model; adders not applicable
}


# ──────────────────── Product type registry ────────────────────

# Iter 78y — 3-Lite Slider and Picture removed. Each remaining product
# carries the canonical UI bucket list ("0-101" single bucket for the
# two sashed products; fixed models for Patio Door).
VERO_PRODUCT_TYPES: dict[str, dict] = {
    "Vero Double Hung":   {"sizing": "ui_bucket"},
    "Vero 2-Lite Slider": {"sizing": "ui_bucket"},
    "Vero Patio Door":    {"sizing": "fixed_model"},
}


# ──────────────────── Cost basis + margin model ────────────────────
# Iter 78y — single source of truth for Vero pricing. Tier prices are
# computed via the gross-margin formula `sell = cost / (1 − margin%)`.
# Update only this section when Howard ships a new master pricing file.

VERO_MARGIN_PCT = {
    "whole-sale":     35,
    "Contractor":     30,
    "Builder-Dealer": 25,
}
_VERO_MARGIN_DIVISOR = {tier: round(1 - pct / 100, 2) for tier, pct in VERO_MARGIN_PCT.items()}

# Cost basis per UI-bucket product (single bucket "0-101" each).
VERO_BASE_COSTS = {
    "Vero Double Hung":   {"0-101": 186.92},
    "Vero 2-Lite Slider": {"0-101": 186.92},
}

# Cost basis for the 8 adders shared by DH + 2-Lite Slider.
VERO_ADDER_COSTS = {
    "Quattro .25 U Factor 2 coats LoE":    37.26,
    "Elite TG2 .24 U Factor 1 coat":       55.58,
    "TG2 Triple Pane/Argon .19 U Factor":  66.76,
    "Head Expander 0-101":                  3.73,
    "Grids":                               30.12,
    "Sentry System - Tilt Lock upgrade":   26.70,
    "Integral Nail Fin 0-101":             13.66,
    "Heavy Duty 1/2 Screen White ONLY":    18.01,
}

# Cost basis for Patio Door fixed models (3 panel sizes).
# Master-catalog VERO tab confirmed (Howard's ruling 2026-07-18, option a):
# these are per-SIZE wholesale COSTS from the tab's standard cost column —
# tier ladder derives via ÷0.65/÷0.70/÷0.75 (9 prices; one-opp stays
# absent). Howard's earlier "sell tiers" reading was RETRACTED (it had
# confirmed a mis-framed question; the sheet's structure governs).
VERO_PATIO_COSTS = {
    "4792PD 2 Panel 5068 (58 3/4\" x 79 1/2\")":  718.19,
    "4792PD 2 Panel 6068 (70 3/4\" x 79 1/2\")":  780.29,
    "4792PD 2 Panel 8068 (94 3/4\" x 79 1/2\")":  877.16,
}

VERO_SINGLE_SISTER_COLOR = "White Interior/White Exterior"
VERO_SINGLE_BUCKET = "0-101"


def compute_tier_price(cost: float, tier: str) -> float:
    """Apply the Vero gross-margin formula. Falls back to wholesale
    (highest price) for any tier not in the divisor table — keeps
    one-opp companies in a sane safe state until they're re-tiered."""
    divisor = _VERO_MARGIN_DIVISOR.get(tier) or _VERO_MARGIN_DIVISOR.get("Builder-Dealer")
    return round(float(cost) / float(divisor), 2)


# ──────────────────── Catalog assembly ────────────────────

async def catalog_for_tier_async(tier_name: str, prices_module) -> dict:
    """Build the contractor-facing catalog payload for one tier."""
    product_types: list[dict] = []
    for pt_name, meta in VERO_PRODUCT_TYPES.items():
        prices = await prices_module.get_prices(tier_name, pt_name)
        prod = _assemble_product(pt_name, meta, prices)
        # Ruled 2026-07-18: absent (tier, product) doc = not offered at
        # tier — render unavailable, never auto-compute a price.
        prod["available"] = not prices.get("_absent", False)
        product_types.append(prod)
    return {"tier": tier_name, "product_types": product_types}


def _assemble_product(pt_name: str, meta: dict, prices: dict) -> dict:
    sizing = meta["sizing"]
    sister_colors: list[str] = prices.get("_sister_colors") or []
    adder_prices = prices.get("adder_prices") or {}

    if sizing == "ui_bucket":
        bucket_labels: list[str] = prices.get("_buckets") or list((prices.get("base_prices") or {}).keys())
        # Pull (almost-flat) sister-color price out of the {bucket: {color: $}} shape
        flat_base = {}
        for b, payload in (prices.get("base_prices") or {}).items():
            if isinstance(payload, dict):
                flat_base[b] = float(payload.get(sister_colors[0], 0.0)) if sister_colors else 0.0
            else:
                flat_base[b] = float(payload or 0.0)
        # Build adder list in canonical display order; fall back to any
        # extra adders the doc has but the canonical list doesn't.
        canonical = VERO_ADDER_NAMES.get(pt_name, [])
        seen = set()
        adders_out: list[dict] = []
        for ad_name in canonical + [a for a in adder_prices.keys() if a not in canonical]:
            if ad_name in seen:
                continue
            seen.add(ad_name)
            prices_by_bucket = adder_prices.get(ad_name) or {}
            adders_out.append({
                "name": ad_name,
                "kind": "flat",
                "prices_by_bucket": {
                    b: float(prices_by_bucket.get(b, 0.0))
                    for b in bucket_labels
                },
            })
        return {
            "name": pt_name,
            "sizing": "ui_bucket",
            "buckets": buckets_to_objects(bucket_labels),
            "sister_colors": sister_colors,
            "base_prices": flat_base,
            "adders": adders_out,
        }

    # Fixed-model (Patio Door)
    models: list[str] = prices.get("_models") or list((prices.get("patio_prices") or {}).keys())
    flat_patio: dict[str, float] = {}
    for m, payload in (prices.get("patio_prices") or {}).items():
        if isinstance(payload, dict):
            flat_patio[m] = float(payload.get(sister_colors[0], 0.0)) if sister_colors else 0.0
        else:
            flat_patio[m] = float(payload or 0.0)
    return {
        "name": pt_name,
        "sizing": "fixed_model",
        "models": models,
        "sister_colors": sister_colors,
        "patio_prices": flat_patio,
        "adders": [],
    }


def get_empty_shell(product_type: str) -> dict:
    return {
        "_sister_colors": [],
        "_buckets": [],
        "_models": [],
        "base_prices": {},
        "patio_prices": {},
        "adder_prices": {},
    }


def validate_product_type(name: str) -> Optional[str]:
    if name not in VERO_PRODUCT_TYPES:
        return f"Unknown Vero product_type: {name}"
    return None


def validate_tier(name: str) -> Optional[str]:
    if name not in VERO_TIER_NAMES:
        return f"Unknown Vero tier: {name}"
    return None
