"""FIXTURE EXPORT TOOL (Howard's consolidated ruling 2026-07-23, item 5 / 3b).

Scope = FULL PARITY: every pinned fixture exports so the suite runs green on
production. Versioned JSON docs + raw photo blobs land in /app/backend/fixtures/
(in-repo — ships with every build). The seed runner upserts by the STABLE
EXISTING IDS so every pinned test keeps working verbatim.

COMPANY SLOTS (ruling condition): test-only fixtures carry slot "test" and
seed under a separate test company on prod; demo-facing fixtures carry slot
"demo" (the demo account's list shows only Letrick, red house, demo estimate,
and the red house's paired LP twin).

HUMAN RUNGS: tape_check / user_measured content transports INSIDE the estimate
docs exactly as the human entered it (original timestamps kept); the seed
runner adds an explicit import stamp on insert — transport, never synthesis.

NOT exported: the demo estimate (its id rotates — POST /demo/reset
reconstructs it from the archived SOURCE run, which IS exported), the sealed
key (code), frozen /m/ /r/ snapshots (environment-bound, re-minted on prod),
password hashes (secrets live only in env — the runner hashes env passwords).
"""
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

FIXTURES_DIR = BACKEND / "fixtures"
UPLOAD_DIR = BACKEND / "uploads"

# slot map — the ruling's split
SLOTS = {
    "673707d5-9b7e-4d8f-8eaf-63c86820f611": "demo",  # red house EST-910869
    "e452a988-83b8-4e6e-9537-1223d0ecbf6f": "demo",  # EST-910869-L (red house's LP twin)
    "8f95c9c2-add9-416a-92f3-786a4ea2ce83": "demo",  # Letrick EST-373526
    "db82ec7a-3177-406d-a602-927255e9e10e": "test",  # doug jones EST-510771
    "48231310-3872-4d4e-b657-35ade10c1cb8": "test",  # haugh EST-067615
    "d78cd3b4-a65c-4238-8d16-7827b131a85c": "test",  # round-two (banked)
}
PRICING_COLLECTIONS = ["vero_prices", "mezzo_prices", "iss_catalog",
                       "price_tiers", "lp_legacy_price_archive", "settings"]
# ai_blueprint_runs / hover_import_runs are EXCLUDED: 24h TTL = transient
# by design (test churn lands there mid-suite); anything durable from them
# already lives in fixture_runs via the archive machinery.
RUN_COLLECTIONS = ["ai_measure_runs", "fixture_runs"]

import re
FN_RE = re.compile(r"\b((?:ai_|bp_)?[0-9a-f]{32}(?:_p\d+)?\.(?:jpg|jpeg|png|webp|pdf))\b")


def checksum(doc: dict) -> str:
    # updated_at excluded: seed-on-boot re-stamps pricing docs every server
    # start; machinery touches it on estimates — volatile, not content
    d = {k: v for k, v in doc.items() if k not in ("_id", "fixture_import", "updated_at")}
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    docs_dir = FIXTURES_DIR / "docs"
    blobs_dir = FIXTURES_DIR / "blobs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    blobs_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"version": datetime.now(timezone.utc).isoformat(),
                "scope": "FULL_PARITY", "docs": {}, "blobs": {}, "counts": {}}

    # ---- estimates (human rungs ride inside, verbatim) ----------------
    estimates, blob_names = [], set()
    for eid, slot in SLOTS.items():
        e = await db.estimates.find_one({"id": eid}, {"_id": 0})
        assert e, f"fixture estimate missing: {eid}"
        assert e.get("protected") is True, f"fixture must be protected before export: {eid}"
        e["company_slot"] = slot
        estimates.append(e)
        blob_names |= set(FN_RE.findall(json.dumps(e, default=str)))
    (docs_dir / "estimates.json").write_text(json.dumps(estimates, indent=1, default=str))
    manifest["docs"]["estimates"] = {e["id"]: checksum(e) for e in estimates}

    # ---- runs (dedupe by run_id; archive target = fixture_runs) -------
    from routes.demo import SOURCE_RUN_ID
    runs, seen = [], set()
    for coll in RUN_COLLECTIONS:
        q = {"$or": [{"estimate_id": {"$in": list(SLOTS)}}, {"run_id": SOURCE_RUN_ID}]}
        async for r in db[coll].find(q, {"_id": 0}):
            rid = r.get("run_id") or r.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            r["_source_collection"] = coll
            runs.append(r)
            blob_names |= set(FN_RE.findall(json.dumps(r, default=str)))
    (docs_dir / "runs.json").write_text(json.dumps(runs, indent=1, default=str))
    manifest["docs"]["runs"] = {(r.get("run_id") or r.get("id")): checksum(r) for r in runs}

    # ---- sessions ------------------------------------------------------
    sessions = [s async for s in db.ai_measure_sessions.find(
        {"estimate_id": {"$in": list(SLOTS)}}, {"_id": 0})]
    for s in sessions:
        blob_names |= set(FN_RE.findall(json.dumps(s, default=str)))
    (docs_dir / "sessions.json").write_text(json.dumps(sessions, indent=1, default=str))
    manifest["docs"]["sessions"] = {s["estimate_id"]: checksum(s) for s in sessions}

    # ---- pricing + settings -------------------------------------------
    pricing = {}
    for coll in PRICING_COLLECTIONS:
        pricing[coll] = [x async for x in db[coll].find({}, {"_id": 0})]
    (docs_dir / "pricing.json").write_text(json.dumps(pricing, indent=1, default=str))
    manifest["docs"]["pricing"] = {
        coll: {str(x.get("id") or x.get("sku") or i): checksum(x) for i, x in enumerate(rows)}
        for coll, rows in pricing.items()}

    # ---- accounts (NO password hashes — runner hashes env passwords) --
    demo_cids = {e["company_id"] for e in estimates if e["company_slot"] == "demo"}
    accounts = {"demo_companies": [], "demo_users": [], "demo_catalogs": []}
    for cid in demo_cids:
        comp = await db.companies.find_one({"id": cid}, {"_id": 0})
        accounts["demo_companies"].append(comp)
        async for u in db.users.find({"company_id": cid}, {"_id": 0, "password_hash": 0}):
            accounts["demo_users"].append(u)
        async for cat in db.catalogs.find({"company_id": cid}, {"_id": 0}):
            accounts["demo_catalogs"].append(cat)
    (docs_dir / "accounts.json").write_text(json.dumps(accounts, indent=1, default=str))
    manifest["docs"]["accounts"] = {k: len(v) for k, v in accounts.items()}

    # ---- blobs (disk first, Mongo mirror fallback — self-heal parity) --
    missing = []
    for name in sorted(blob_names):
        data = None
        p = UPLOAD_DIR / name
        if p.exists():
            data = p.read_bytes()
        else:
            b = await db.upload_blobs.find_one({"name": name})
            if b and b.get("data"):
                data = bytes(b["data"])
        if data is None:
            missing.append(name)
            continue
        (blobs_dir / name).write_bytes(data)
        manifest["blobs"][name] = {"sha256": hashlib.sha256(data).hexdigest(),
                                   "size": len(data)}
    manifest["counts"] = {"estimates": len(estimates), "runs": len(runs),
                          "sessions": len(sessions),
                          "blobs": len(manifest["blobs"]),
                          "blob_bytes": sum(b["size"] for b in manifest["blobs"].values()),
                          "blobs_missing_at_export": missing}
    (FIXTURES_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest["counts"], indent=1))
    assert not missing, f"blobs missing from both stores: {missing}"


if __name__ == "__main__":
    asyncio.run(main())
