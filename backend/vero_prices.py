"""MongoDB CRUD for Vero pricing (per-tier × per-product). Mirrors the
shape of `mezzo_prices.py` but stores a richer document (the Vero
pricebook spans multiple optional grids — base, glass packages, tempered
upcharge, premium options).

Collection: `vero_prices`. Unique index on (tier, product_type).

Doc shape:
    {
        id: "<uuid>",
        tier: "whole-sale",
        product_type: "Vero Double Hung",
        sizing: "ui_bucket" | "fixed_model",
        # ui_bucket products store these:
        _sister_colors: [...],
        _buckets: [...],
        base_prices: { bucket: { sister: price } },
        glass_packages: { package: { bucket: price } },
        tempered: { package: { bucket: price } },
        premium_options: { variant: { bucket: price } },
        flat: { key: value, ... },
        # fixed_model (Patio Door) stores these instead:
        _models: [...],
        patio_prices: { model: { sister: price } },
        glass_packages_patio: { package: { model: price } },
        updated_at: ISO8601,
    }
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from db import db, logger
from vero_catalog import (
    VERO_PRODUCT_TYPES,
    VERO_TIER_NAMES,
    get_empty_shell,
    validate_product_type,
    validate_tier,
)

SEED_FILE = Path(__file__).parent / "vero_seed_prices.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_indexes():
    await db.vero_prices.create_index([("tier", 1), ("product_type", 1)], unique=True)


async def get_prices(tier: str, product_type: str) -> dict:
    """Return the price doc for one (tier, product). Falls back to a
    zero-shell if not seeded yet so the catalog endpoint stays schema-safe.
    """
    doc = await db.vero_prices.find_one(
        {"tier": tier, "product_type": product_type}, {"_id": 0}
    )
    if doc:
        return doc
    # Ruled 2026-07-18: an absent (tier, product) doc means NOT OFFERED
    # at that tier (e.g. Vero on one-opp). Never derive a price Howard
    # didn't set — surface `_absent` so the catalog can mark it
    # unavailable instead of rendering a $0 grid.
    shell = get_empty_shell(product_type)
    shell["_absent"] = True
    return shell


async def save_prices(
    tier: str,
    product_type: str,
    payload: dict,
) -> dict:
    """Upsert one (tier, product) doc. `payload` is taken verbatim except
    `tier` / `product_type` / `id` / `updated_at` are managed by us.

    Caller is expected to send a full grid — anything not in the payload
    is dropped. We don't try to deep-merge because the admin UI re-sends
    the whole product doc on every save.
    """
    err = validate_tier(tier) or validate_product_type(product_type)
    if err:
        raise ValueError(err)
    # Normalize: strip any keys the schema doesn't own.
    sizing = VERO_PRODUCT_TYPES[product_type]["sizing"]
    allowed_keys = {
        "ui_bucket": {
            "_sister_colors", "_buckets",
            "base_prices", "adder_prices",
        },
        "fixed_model": {
            "_sister_colors", "_models",
            "patio_prices", "adder_prices",
        },
    }[sizing]
    clean: dict = {k: payload[k] for k in allowed_keys if k in payload}
    clean["tier"] = tier
    clean["product_type"] = product_type
    clean["sizing"] = sizing
    clean["updated_at"] = _now_iso()

    await db.vero_prices.update_one(
        {"tier": tier, "product_type": product_type},
        {"$set": clean, "$setOnInsert": {"id": str(uuid.uuid4())}},
        upsert=True,
    )
    return clean


async def list_all_prices() -> list[dict]:
    return await db.vero_prices.find({}, {"_id": 0}).to_list(length=200)


async def seed_vero_prices(force: bool = False) -> int:
    """Seed `vero_prices` from `vero_seed_prices.json`. Idempotent: any
    (tier, product) doc that already exists is skipped unless force=True.
    Returns count of docs written."""
    if not SEED_FILE.exists():
        logger.warning("Vero seed file missing: %s", SEED_FILE)
        return 0
    with open(SEED_FILE, "r") as f:
        data = json.load(f)

    written = 0
    for tier, products in data.items():
        if tier not in VERO_TIER_NAMES:
            logger.warning("Skipping unknown Vero tier in seed: %s", tier)
            continue
        for pt_name, payload in products.items():
            if pt_name not in VERO_PRODUCT_TYPES:
                logger.warning("Skipping unknown Vero product in seed: %s", pt_name)
                continue
            if not force:
                existing = await db.vero_prices.find_one(
                    {"tier": tier, "product_type": pt_name}, {"_id": 1}
                )
                if existing:
                    continue
            await save_prices(tier, pt_name, payload)
            written += 1
    if written:
        logger.info("Seeded %d Vero price docs from %s", written, SEED_FILE.name)
    return written
