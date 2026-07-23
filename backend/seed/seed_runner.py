"""SEED RUNNER + PROVISIONING GATE (Howard's ruling 2026-07-23, items 3 + 5).

  python seed/seed_runner.py apply    # idempotent provisioning of ANY env
  python seed/seed_runner.py verify   # morning-of gate: every checksum
                                      # checked, GREEN/RED report, exit 1 on RED

APPLY rules:
  • pricing/settings: upsert by id (no human rungs — overwrite on drift)
  • accounts: demo company/users upsert (passwords hashed from env —
    FIXTURE_DEMO_PASSWORD, fallback ADMIN_PASSWORD; hashes never transport);
    test company + user created under fixed id (company slot "test")
  • estimates: INSERT-ONLY with an explicit import stamp (human rungs are
    transported, never synthesized, never overwritten — drift is REPORTED)
  • runs: upsert into fixture_runs (no-TTL archive = authoritative read
    fallback) + insert into the original live collection when absent
  • blobs: upsert upload_blobs + best-effort disk write (self-heal parity)
  • demo estimate: NOT seeded directly — run POST /demo/reset after apply
    (it rebuilds from the archived SOURCE run, which this seed provides)

VERIFY (the demo-script checklist line "verify seeds applied on prod"):
  pricing/blob/run checksums strict; estimates checked for presence +
  protected flag + human-rung fields (their content legitimately evolves —
  strict-checksum only until first post-seed edit); accounts + demo checked.
"""
import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv, dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

FIXTURES_DIR = BACKEND / "fixtures"
UPLOAD_DIR = BACKEND / "uploads"
TEST_CO_ID = "zzfix-test-co-0001"
TEST_USER_ID = "zzfix-test-user-0001"
_ENV = dotenv_values(BACKEND / ".env")
TEST_CO_EMAIL = _ENV.get("FIXTURE_TEST_EMAIL") or "fixtures@test.internal"


def checksum(doc: dict) -> str:
    # updated_at excluded: seed-on-boot re-stamps pricing docs every server
    # start; machinery touches it on estimates — volatile, not content
    d = {k: v for k, v in doc.items() if k not in ("_id", "fixture_import", "updated_at")}
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


def _load():
    m = json.loads((FIXTURES_DIR / "manifest.json").read_text())
    docs = {p.stem: json.loads((FIXTURES_DIR / "docs" / p.name).read_text())
            for p in (FIXTURES_DIR / "docs").glob("*.json")}
    return m, docs


async def apply(db):
    from deps import hash_password
    m, docs = _load()
    stamp = {"stamp": f"imported from preview export {m['version']} — transported, not synthesized",
             "imported_at": datetime.now(timezone.utc).isoformat()}
    report = {"applied": 0, "skipped": 0, "drift_reported": []}

    # accounts first (estimates reference company ids)
    acc = docs["accounts"]
    for comp in acc["demo_companies"]:
        await db.companies.update_one({"id": comp["id"]}, {"$set": comp}, upsert=True)
    for u in acc["demo_users"]:
        existing = await db.users.find_one({"id": u["id"]}, {"_id": 1})
        if not existing:
            pw = _ENV.get("FIXTURE_DEMO_PASSWORD") or _ENV.get("ADMIN_PASSWORD")
            assert pw, "FIXTURE_DEMO_PASSWORD / ADMIN_PASSWORD required to seed accounts"
            u = dict(u); u["password_hash"] = hash_password(pw)
            await db.users.insert_one(u)
    for cat in acc["demo_catalogs"]:
        await db.catalogs.update_one({"company_id": cat["company_id"]}, {"$set": cat}, upsert=True)
    # test company slot — fixed id, replicating create_company's writes
    if not await db.companies.find_one({"id": TEST_CO_ID}, {"_id": 1}):
        from deps import make_invite_code
        from services import get_default_tier_id
        await db.companies.insert_one({
            "id": TEST_CO_ID, "name": "ZZ Fixture Test Co",
            "owner_user_id": TEST_USER_ID, "invite_code": make_invite_code(),
            "logo_url": None, "quote_footer_enabled": True,
            "price_tier_id": await get_default_tier_id(),
            "created_at": datetime.now(timezone.utc).isoformat()})
        await db.catalogs.insert_one({
            "company_id": TEST_CO_ID, "overrides": {},
            "updated_at": datetime.now(timezone.utc).isoformat()})
    if not await db.users.find_one({"id": TEST_USER_ID}, {"_id": 1}):
        pw = _ENV.get("FIXTURE_TEST_PASSWORD") or _ENV.get("ADMIN_PASSWORD")
        assert pw, "FIXTURE_TEST_PASSWORD / ADMIN_PASSWORD required to seed test account"
        await db.users.insert_one({
            "id": TEST_USER_ID, "email": TEST_CO_EMAIL, "name": "Fixture Test",
            "password_hash": hash_password(pw), "role": "owner",
            "company_id": TEST_CO_ID,
            "created_at": datetime.now(timezone.utc).isoformat()})

    # pricing/settings — upsert on drift (natural keys per collection)
    def _key(coll, row):
        if coll in ("vero_prices", "mezzo_prices"):
            return {"tier": row["tier"], "product_type": row["product_type"]}
        if coll == "iss_catalog":
            return {"section": row["section"], "name": row["name"]}
        return {"id": row["id"]}

    for coll, rows in docs["pricing"].items():
        for row in rows:
            key = _key(coll, row)
            cur = await db[coll].find_one(key, {"_id": 0})
            if cur and checksum(cur) == checksum(row):
                report["skipped"] += 1
                continue
            await db[coll].update_one(key, {"$set": row}, upsert=True)
            report["applied"] += 1

    # estimates — INSERT-ONLY (human rungs never overwritten)
    for e in docs["estimates"]:
        e = dict(e)
        if e.pop("company_slot", None) == "test":
            e["company_id"] = TEST_CO_ID
        cur = await db.estimates.find_one({"id": e["id"]}, {"_id": 0})
        if cur:
            if checksum({k: v for k, v in cur.items() if k != "company_id"}) != \
               checksum({k: v for k, v in e.items() if k != "company_id"}):
                report["drift_reported"].append(e["id"][:8] + " (existing doc differs — NOT overwritten)")
            report["skipped"] += 1
            continue
        e["fixture_import"] = stamp
        await db.estimates.insert_one(e)
        report["applied"] += 1

    # runs — archive authoritative + live collection when absent
    for r in docs["runs"]:
        r = dict(r)
        src = r.pop("_source_collection", "ai_measure_runs")
        rid_key = "run_id" if r.get("run_id") else "id"
        await db.fixture_runs.update_one({rid_key: r[rid_key]}, {"$set": r}, upsert=True)
        if src != "fixture_runs" and not await db[src].find_one({rid_key: r[rid_key]}, {"_id": 1}):
            await db[src].insert_one(dict(r))
        report["applied"] += 1

    for s in docs["sessions"]:
        if not await db.ai_measure_sessions.find_one({"estimate_id": s["estimate_id"]}, {"_id": 1}):
            await db.ai_measure_sessions.insert_one(dict(s))
            report["applied"] += 1
        else:
            report["skipped"] += 1

    # blobs
    for name, meta in m["blobs"].items():
        data = (FIXTURES_DIR / "blobs" / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == meta["sha256"], f"pack corrupt: {name}"
        cur = await db.upload_blobs.find_one({"name": name}, {"size": 1})
        if not cur:
            await db.upload_blobs.update_one(
                {"name": name},
                {"$set": {"name": name, "data": data, "size": len(data),
                          "stored_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True)
            report["applied"] += 1
        else:
            report["skipped"] += 1
        try:
            p = UPLOAD_DIR / name
            if not p.exists():
                UPLOAD_DIR.mkdir(exist_ok=True)
                p.write_bytes(data)
        except OSError:
            pass
    print(json.dumps(report, indent=1))
    return report


async def verify(db):
    m, docs = _load()
    green, red = [], []

    def check(ok, label):
        (green if ok else red).append(("GREEN " if ok else "RED   ") + label)

    for e in docs["estimates"]:
        cur = await db.estimates.find_one({"id": e["id"]}, {"_id": 0})
        check(cur is not None, f"estimate {e['id'][:8]} {e.get('estimate_number')} present")
        if cur:
            check(cur.get("protected") is True, f"estimate {e['id'][:8]} protected flag")
            if e.get("tape_check"):
                check(bool(cur.get("tape_check")), f"estimate {e['id'][:8]} human rung (tape_check) present")
    for r in docs["runs"]:
        rid = r.get("run_id") or r.get("id")
        cur = await db.fixture_runs.find_one({("run_id" if r.get("run_id") else "id"): rid}, {"_id": 0})
        # archive docs legitimately carry extra archive metadata
        # (archived_at, reason) — verify over the exported doc's own fields
        exp = {k: v for k, v in r.items() if k != "_source_collection"}
        cur_sub = {k: cur[k] for k in exp if k in cur} if cur else None
        ok = cur is not None and checksum(cur_sub) == checksum(exp)
        check(ok, f"run {str(rid)[:8]} archived + checksum")
    for coll, rows in docs["pricing"].items():
        bad = 0
        for row in rows:
            key = ({"tier": row["tier"], "product_type": row["product_type"]}
                   if coll in ("vero_prices", "mezzo_prices")
                   else {"section": row["section"], "name": row["name"]}
                   if coll == "iss_catalog" else {"id": row["id"]})
            cur = await db[coll].find_one(key, {"_id": 0})
            if cur is None or checksum(cur) != checksum(row):
                bad += 1
        check(bad == 0, f"pricing {coll}: {len(rows) - bad}/{len(rows)} checksum-exact")
    bad = 0
    for name, meta in m["blobs"].items():
        b = await db.upload_blobs.find_one({"name": name})
        if not b or hashlib.sha256(bytes(b["data"])).hexdigest() != meta["sha256"]:
            bad += 1
    check(bad == 0, f"blobs: {len(m['blobs']) - bad}/{len(m['blobs'])} present + sha256-exact")
    for u in docs["accounts"]["demo_users"]:
        check(await db.users.find_one({"id": u["id"]}, {"_id": 1}) is not None,
              f"demo account {u['email']}")
    check(await db.users.find_one({"id": TEST_USER_ID}, {"_id": 1}) is not None,
          "test-company account (suite login for test-slot fixtures)")
    demo = await db.estimates.find_one({"demo_key": {"$ne": None}}, {"_id": 0, "protected": 1})
    check(demo is not None and demo.get("protected") is True,
          "demo estimate present + protected (run POST /demo/reset if RED)")

    print("\n".join(green + red))
    print(f"\nPROVISIONING GATE: {'GREEN — seeds verified' if not red else f'RED — {len(red)} failure(s)'}"
          f" ({len(green)} green / {len(red)} red)")
    return len(red)


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    if mode == "apply":
        await apply(db)
        sys.exit(await verify(db) and 1 or 0)
    sys.exit(await verify(db) and 1 or 0)


if __name__ == "__main__":
    asyncio.run(main())
