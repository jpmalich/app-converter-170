"""RED-HOUSE FIXTURE RESTORATION (Howard's standing order, executed 2026-07-22).

Restores the missing estimate doc 673707d5-9b7e-4d8f-8eaf-63c86820f611
("red house", EST-910869) whose 16 live AI-measure runs + archived fixture
run 8ddb8932 + ai_measure_session survived while the estimate doc itself
disappeared. Receipts printed at every step; ABORTS if the doc exists.

Doctrine honored:
  • tape_check.history is NOT synthesized — human records enter only by
    tape or ratification (Howard, wave-1 close). The per-wall tape truths
    remain on the PRD/register record for re-entry via normal machinery.
  • Nothing else in the estimates collection is touched — verified by
    per-doc checksum before/after. The broken pair pointer to EST-910869-L
    is restored ONE-WAY on the new doc only (disclosed, reverse pointer
    left for a ruling).
"""
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

EID = "673707d5-9b7e-4d8f-8eaf-63c86820f611"
PAIR_ID = "e452a988-83b8-4e6e-9537-1223d0ecbf6f"  # EST-910869-L (lp pair)
TEMPLATE_ID = "db82ec7a-3177-406d-a602-927255e9e10e"  # schema-complete doc


def _checksum(doc):
    doc = {k: v for k, v in doc.items() if k != "_id"}
    return hashlib.md5(json.dumps(doc, sort_keys=True, default=str).encode()).hexdigest()


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    # ---- pre-state receipts -------------------------------------------------
    assert await db.estimates.find_one({"id": EID}) is None, "doc exists — ABORT"
    ses = await db.ai_measure_sessions.find_one({"estimate_id": EID}, {"company_id": 1})
    assert ses, "session missing — cannot bind company_id"
    runs = await db.ai_measure_runs.count_documents({"estimate_id": EID})
    fx = await db.fixture_runs.count_documents({"run_id": {"$regex": "^8ddb8932"}})
    pre_count = await db.estimates.count_documents({})
    pre_sums = {d["id"]: _checksum(d) async for d in db.estimates.find({})}
    print(f"PRE: estimates={pre_count} · live runs={runs} · fixture run 8ddb8932 present={bool(fx)}"
          f" · session company_id={ses['company_id']}")
    # ---- build the doc from a schema-complete template ----------------------
    template = await db.estimates.find_one({"id": TEMPLATE_ID}, {"_id": 0})
    doc = {k: ("" if isinstance(v, str) else None if not isinstance(v, (dict, list)) else type(v)())
           for k, v in template.items()}
    doc.update({
        "id": EID,
        "company_id": ses["company_id"],
        "estimate_number": "EST-910869",           # recovered: memory/prompts.md refine-loss log
        "customer_name": "red house",              # the fixture's name of record (PRD throughout)
        "address": "fixture — doc restored 2026-07-22 (see integrity register)",
        "kind": "siding",
        "estimator": "Howard Hunt",
        "estimate_date": "2026-07-07",             # first run date on record
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paired_estimate_id": PAIR_ID,             # one-way; reverse pointer awaits ruling
        # tape_check DELIBERATELY ABSENT — never synthesized
    })
    doc.pop("tape_check", None)
    await db.estimates.insert_one(doc)
    # ---- post-state receipts ------------------------------------------------
    post_count = await db.estimates.count_documents({})
    post_sums = {d["id"]: _checksum(d) async for d in db.estimates.find({})}
    changed = [i for i in pre_sums if post_sums.get(i) != pre_sums[i]]
    added = set(post_sums) - set(pre_sums)
    print(f"POST: estimates={post_count} (Δ{post_count - pre_count})"
          f" · added={sorted(added)} · pre-existing docs changed={changed or 'NONE'}")
    assert post_count == pre_count + 1 and added == {EID} and not changed
    print("RESTORED: red house estimate doc re-paired to its runs — receipts clean")

asyncio.run(main())
