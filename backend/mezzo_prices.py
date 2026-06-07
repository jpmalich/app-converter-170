"""Mezzo price store backed by MongoDB (`db.mezzo_prices`).

Each Mongo document is one (tier, product_type) entry holding:
  { tier, product_type, base_prices: {bucket: $}, adder_prices: {adder: {bucket: $}} }

Boot-time seeding (`seed_mezzo_prices`) is idempotent — it only writes if
the doc doesn't exist. Prices for missing (adder, bucket) combos default
to $0 so the admin matrix UI is safe to render without nulls.
"""
import json
from pathlib import Path

from db import db, logger
from mezzo_catalog import (
    MEZZO_ADDER_NAMES,
    MEZZO_BUCKETS,
    MEZZO_PRODUCT_TYPES,
    MEZZO_TIER_NAMES,
)

SEED_PATH = Path(__file__).parent / "mezzo_seed_prices.json"


def _empty_matrix(product_type: str) -> dict:
    """Return a zeroed base_prices + adder_prices matrix for a product."""
    buckets = MEZZO_BUCKETS[product_type]
    return {
        "base_prices": {b["label"]: 0.0 for b in buckets},
        "adder_prices": {
            a: {b["label"]: 0.0 for b in buckets}
            for a in MEZZO_ADDER_NAMES[product_type]
        },
    }


def _load_seed() -> dict:
    if not SEED_PATH.exists():
        return {}
    try:
        with open(SEED_PATH, "r") as f:
            return json.load(f)
    except Exception:
        logger.warning("Failed to read mezzo_seed_prices.json — defaulting to zeros.")
        return {}


def _merge_seed_into_matrix(matrix: dict, seed: dict) -> dict:
    """Apply the (partial) JSON seed onto a zero matrix without erasing
    bucket/adder keys the seed didn't include."""
    if not seed:
        return matrix
    for k, v in (seed.get("base_prices") or {}).items():
        if k in matrix["base_prices"]:
            matrix["base_prices"][k] = float(v or 0)
    seed_adders = seed.get("adder_prices") or {}
    for ad_name, bucket_map in seed_adders.items():
        # Tolerate "Cherry Laminate" vs "CHERRY LAMINATE" casing drift.
        canonical = next(
            (a for a in matrix["adder_prices"] if a.lower() == ad_name.lower()),
            None,
        )
        if not canonical:
            continue
        for bk, v in (bucket_map or {}).items():
            if bk in matrix["adder_prices"][canonical]:
                matrix["adder_prices"][canonical][bk] = float(v or 0)
    return matrix


async def seed_mezzo_prices() -> None:
    """Insert one doc per (tier, product_type) on first boot. Idempotent:
    finds existing docs and skips them. Subsequent admin edits live in
    Mongo only — they aren't overwritten by the JSON seed."""
    seed = _load_seed()
    for tier in MEZZO_TIER_NAMES:
        for product_type in MEZZO_PRODUCT_TYPES.keys():
            existing = await db.mezzo_prices.find_one(
                {"tier": tier, "product_type": product_type},
                {"_id": 1},
            )
            if existing:
                continue
            matrix = _empty_matrix(product_type)
            tier_seed = (seed.get(tier) or {}).get(product_type) or {}
            matrix = _merge_seed_into_matrix(matrix, tier_seed)
            await db.mezzo_prices.insert_one({
                "tier": tier,
                "product_type": product_type,
                **matrix,
            })
            logger.info(f"Seeded mezzo prices: {tier} / {product_type}")


async def get_prices(tier: str, product_type: str) -> dict:
    """Return the matrix for a single (tier, product_type)."""
    doc = await db.mezzo_prices.find_one(
        {"tier": tier, "product_type": product_type},
        {"_id": 0},
    )
    if not doc:
        matrix = _empty_matrix(product_type)
        return {"tier": tier, "product_type": product_type, **matrix}
    return doc


async def list_all_prices() -> list:
    """Return every (tier, product_type) doc for the admin UI."""
    docs = await db.mezzo_prices.find({}, {"_id": 0}).to_list(length=64)
    return docs


async def save_prices(tier: str, product_type: str, base_prices: dict, adder_prices: dict) -> dict:
    """Upsert the full matrix for one (tier, product_type). Only known
    bucket/adder keys are saved — unknown keys are silently dropped so
    the admin UI can't introduce typos that break the matrix schema."""
    canon = _empty_matrix(product_type)
    # Sanitise: only keep entries whose key matches a canonical bucket/adder
    clean_base = {
        bk: float(v or 0)
        for bk, v in (base_prices or {}).items()
        if bk in canon["base_prices"]
    }
    clean_adder = {}
    for ad_name, bucket_map in (adder_prices or {}).items():
        if ad_name not in canon["adder_prices"]:
            continue
        clean_adder[ad_name] = {
            bk: float(v or 0)
            for bk, v in (bucket_map or {}).items()
            if bk in canon["base_prices"]
        }
    # Fill missing keys with 0 so the matrix is always complete.
    canon["base_prices"].update(clean_base)
    for ad_name, bmap in canon["adder_prices"].items():
        bmap.update(clean_adder.get(ad_name, {}))
    await db.mezzo_prices.update_one(
        {"tier": tier, "product_type": product_type},
        {"$set": {
            "tier": tier,
            "product_type": product_type,
            **canon,
        }},
        upsert=True,
    )
    return {"tier": tier, "product_type": product_type, **canon}
