"""Reverse-pointer restoration on EST-910869-L (Howard's ruling 2026-07-22).

RULING: RESTORE — the report demonstrated a real consumer (dashboard
chain-link badge/navigation, routes/estimates.py L51-62 + Dashboard.jsx).
Discipline (same as the red-house doc restoration):
  • ONE write: a single $set of paired_estimate_id on e452a988… →
    673707d5… (EST-910869-L → EST-910869). Nothing else.
  • Per-doc checksum of EVERY estimate before/after — the diff must be
    exactly ONE doc changed, and on that doc exactly ONE field added.
  • Frozen /m/ links on e452a988… re-verified serving AS-FROZEN after
    the write (snapshot content hash unchanged).
"""
import asyncio
import hashlib
import json
import os
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

LP_ID = "e452a988-83b8-4e6e-9537-1223d0ecbf6f"    # EST-910869-L
SRC_ID = "673707d5-9b7e-4d8f-8eaf-63c86820f611"   # EST-910869 (red house)


def _checksum(doc):
    d = dict(doc)
    d.pop("_id", None)
    return hashlib.md5(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

    pre = {d["id"]: _checksum(d) async for d in db.estimates.find({})}
    lp = await db.estimates.find_one({"id": LP_ID})
    assert lp, "EST-910869-L missing — ABORT"
    assert lp.get("paired_lp_estimate_id") == SRC_ID, "forward context mismatch — ABORT"
    assert not lp.get("paired_estimate_id"), "pointer already set — ABORT (idempotency)"

    snaps_pre = [(s["token"], s.get("content_hash"), _checksum(s))
                 async for s in db.lp_material_list_snapshots.find({"estimate_id": LP_ID})]
    print(f"frozen snapshots on {LP_ID[:8]}…: {len(snaps_pre)}")

    res = await db.estimates.update_one(
        {"id": LP_ID}, {"$set": {"paired_estimate_id": SRC_ID}})
    assert res.modified_count == 1
    print(f"WRITE: paired_estimate_id = {SRC_ID[:8]}… set on {LP_ID[:8]}… (single $set)")

    post = {d["id"]: _checksum(d) async for d in db.estimates.find({})}
    assert set(pre) == set(post), "doc count changed — VIOLATION"
    changed = [k for k in pre if pre[k] != post[k]]
    assert changed == [LP_ID], f"unexpected docs changed: {changed}"
    lp2 = await db.estimates.find_one({"id": LP_ID})
    diff_fields = {k for k in set(lp2) | set(lp)
                   if lp2.get(k) != lp.get(k) and k != "_id"}
    assert diff_fields == {"paired_estimate_id"}, f"unexpected fields: {diff_fields}"
    print(f"CHECKSUMS: {len(pre)} estimate docs — exactly 1 changed ({LP_ID[:8]}…), "
          f"exactly 1 field added (paired_estimate_id)")

    snaps_post = [(s["token"], s.get("content_hash"), _checksum(s))
                  async for s in db.lp_material_list_snapshots.find({"estimate_id": LP_ID})]
    assert snaps_pre == snaps_post, "frozen snapshot mutated — VIOLATION"
    for tok, ch, _ in snaps_post:
        print(f"FROZEN LINK: token {tok[:8]}… content_hash {str(ch)[:12]}… — unchanged")
    print("DONE — reverse pointer restored, nothing else touched.")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
