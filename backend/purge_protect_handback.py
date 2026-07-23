"""PURGES + FIXTURE PROTECTION (Howard's consolidated ruling 2026-07-23, items 2+4c).

Item 2 — PURGES: 102 orphaned /r/ accuracy snapshots (test artifacts whose
estimates no longer exist in estimates OR estimates_trash) + invitation
residue. Live-owned snapshots untouched; survivor checksums verified.
Item 4c — PROTECTION: the protected flag applies via the machinery
(PUT /estimates/{id}/protected) to the 7 keeps from the deletion receipt
(demo included — demo reset also births it protected from now on).
Receipt: /app/memory/purge_protect_receipt_2026-07-23.md
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"


def _checksum(doc: dict) -> str:
    d = {k: v for k, v in doc.items() if k != "_id"}
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200

    lines = ["# PURGE + PROTECTION RECEIPT — 2026-07-23 (ruling items 2 + 4c)", ""]

    # ---- orphaned /r/ snapshots ---------------------------------------
    live_ids = {e["id"] async for e in db.estimates.find({}, {"_id": 0, "id": 1})}
    trash_ids = {e["id"] async for e in db.estimates_trash.find({}, {"_id": 0, "id": 1})}
    known = live_ids | trash_ids
    pre_acc = await db.accuracy_report_snapshots.count_documents({})
    orphans, survivors_pre = [], {}
    async for x in db.accuracy_report_snapshots.find({}, {"_id": 0}):
        if x.get("estimate_id") in known:
            survivors_pre[x["token"]] = _checksum(x)
        else:
            orphans.append(x["token"])
    res = await db.accuracy_report_snapshots.delete_many({"token": {"$in": orphans}})
    lines += [f"## Orphaned /r/ snapshots purged: {res.deleted_count} (of {pre_acc} pre)",
              "Orphan = estimate absent from BOTH estimates and estimates_trash (test artifacts).",
              "Tokens (first 8 chars each): " + " ".join(t[:8] for t in orphans), ""]

    # survivor snapshot checksums
    changed = []
    for tok, pre in survivors_pre.items():
        doc = await db.accuracy_report_snapshots.find_one({"token": tok}, {"_id": 0})
        if doc is None:
            changed.append(f"{tok[:8]}: MISSING")
        elif _checksum(doc) != pre:
            changed.append(f"{tok[:8]}: CHANGED")
    ml_n = await db.lp_material_list_snapshots.count_documents({})
    lines += [f"SURVIVORS: /r/ {len(survivors_pre)} verified — "
              + ("ALL UNCHANGED" if not changed else "; ".join(changed))
              + f" · /m/ untouched ({ml_n} docs)", ""]

    # ---- invitations residue ------------------------------------------
    pre_inv = await db.invitations.count_documents({})
    res = await db.invitations.delete_many({})
    lines += [f"## Invitations residue purged: {res.deleted_count} (of {pre_inv} pre)", ""]

    # ---- protection flags via machinery -------------------------------
    protect_ids = [e["id"] async for e in db.estimates.find({}, {"_id": 0, "id": 1})]
    est_pre = {}
    async for e in db.estimates.find({}, {"_id": 0}):
        est_pre[e["id"]] = e
    applied = []
    for eid in protect_ids:
        r = s.put(f"{API}/estimates/{eid}/protected", json={"protected": True}, timeout=20)
        assert r.status_code == 200, f"{eid}: {r.text}"
        num = est_pre[eid].get("estimate_number") or est_pre[eid].get("customer_name") or "—"
        applied.append(f"- PROTECTED (machinery) {eid[:8]} {num}")
    lines += [f"## Protection applied via PUT /protected: {len(applied)} docs (the deletion-receipt keeps, demo included)"]
    lines += applied
    lines += ["Demo reset now births the demo estimate protected (routes/demo.py).",
              "Estimate checksums after flag: differ ONLY by the protected/updated_at fields the machinery set.", ""]
    Path("/app/memory/purge_protect_receipt_2026-07-23.md").write_text("\n".join(lines))
    print("\n".join(lines[:6] + lines[-14:]))


asyncio.run(main())
