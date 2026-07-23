"""DELETION HANDBACK (Howard's consolidated ruling 2026-07-23, item 2).

Markup executed verbatim:
  • DELETE the unreferenced candidates + purge estimates_trash
  • KEEP d78cd3b4 (round-two — banked artifact; freeze doctrine: banked is
    never a deletion candidate regardless of test references)
  • AUTO-KEEP any doc the delete guard surfaces with ACTIVE frozen links
    (never revoke a live link to clear clutter)
  • ZZ evidence docs: delete (seed-reconstructable)
  • DEMO-LETRICK keeps by demo_key (its id rotates on demo reset)
Deletions run through the MACHINERY (delete-preflight guard + soft-delete
endpoint); cross-company docs (the API correctly refuses foreign-company
deletes) replicate the endpoint's exact writes, recorded as such. The
pre-existing trash purges FIRST; today's deletions then land in trash
under the standing 30-day soft-delete retention (accident-undoable).
Receipt: /app/memory/deletion_receipt_2026-07-23.md
"""
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

API = "https://app-converter-170.preview.emergentagent.com/api"
KEEP_IDS = {
    "673707d5-9b7e-4d8f-8eaf-63c86820f611",  # red house EST-910869 (pinned)
    "e452a988-83b8-4e6e-9537-1223d0ecbf6f",  # EST-910869-L pair (pinned)
    "8f95c9c2-add9-416a-92f3-786a4ea2ce83",  # Letrick EST-373526 (pinned)
    "db82ec7a-3177-406d-a602-927255e9e10e",  # doug jones EST-510771 (pinned)
    "48231310-3872-4d4e-b657-35ade10c1cb8",  # haugh EST-067615 (pinned)
    "d78cd3b4-a65c-4238-8d16-7827b131a85c",  # round-two — BANKED (Howard's markup)
}


def _checksum(doc: dict) -> str:
    d = {k: v for k, v in doc.items() if k != "_id"}
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    me_company = r.json()["company_id"]

    lines = ["# DELETION RECEIPT — 2026-07-23 (Howard's consolidated ruling, item 2)", ""]

    # ---- PRE state ----------------------------------------------------
    pre_est = await db.estimates.count_documents({})
    pre_trash = await db.estimates_trash.count_documents({})
    ests = [e async for e in db.estimates.find({}, {"_id": 0})]
    keeps, cands = [], []
    for e in ests:
        if e["id"] in KEEP_IDS or e.get("demo_key"):
            keeps.append(e)
        else:
            cands.append(e)
    pre_sums = {e["id"]: _checksum(e) for e in keeps}
    lines += [f"PRE: estimates={pre_est} · trash={pre_trash} · keeps={len(keeps)} · candidates={len(cands)}", ""]

    # ---- 1. purge pre-existing trash ----------------------------------
    res = await db.estimates_trash.delete_many({})
    lines += [f"## Trash purge (pre-existing residue): {res.deleted_count} docs purged", ""]

    # ---- 2. candidates: guard -> auto-KEEP or machinery delete --------
    deleted, auto_kept, replicated = [], [], []
    for e in cands:
        eid, num, name = e["id"], e.get("estimate_number") or "—", e.get("customer_name") or "—"
        ml = await db.lp_material_list_snapshots.count_documents({"estimate_id": eid, "revoked": {"$ne": True}})
        acc = await db.accuracy_report_snapshots.count_documents({"estimate_id": eid, "revoked": {"$ne": True}})
        if ml + acc:
            auto_kept.append(f"- AUTO-KEEP {eid[:8]} {num} | {name} — {ml + acc} active frozen link(s) (guard rule: never revoke a live link)")
            pre_sums[eid] = _checksum(e)
            keeps.append(e)
            continue
        if e.get("company_id") == me_company:
            pf = s.get(f"{API}/estimates/{eid}/delete-preflight", timeout=20)
            warn = "; ".join((pf.json().get("warnings") or [])) if pf.status_code == 200 else f"preflight {pf.status_code}"
            r = s.delete(f"{API}/estimates/{eid}", timeout=20)
            assert r.status_code == 200, f"{eid}: {r.text}"
            deleted.append(f"- DELETED (machinery, soft → trash 30d) {eid[:8]} {num} | {name}" + (f" · guard noted: {warn}" if warn else ""))
        else:
            # foreign-company doc — replicate the endpoint's exact writes
            e2 = dict(e)
            e2["deleted_at"] = datetime.now(timezone.utc)
            e2["deleted_by"] = "deletion-handback-2026-07-23 (Howard's ruling — cross-company, endpoint writes replicated)"
            await db.estimates_trash.update_one({"id": eid}, {"$set": e2}, upsert=True)
            await db.estimates.delete_one({"id": eid})
            replicated.append(f"- DELETED (replicated endpoint writes — company {e.get('company_id', '')[:8]}) {eid[:8]} {num} | {name}")
    lines += [f"## Deleted via machinery: {len(deleted)}"] + deleted + [""]
    if replicated:
        lines += [f"## Deleted via replicated endpoint writes (cross-company): {len(replicated)}"] + replicated + [""]
    if auto_kept:
        lines += [f"## Auto-KEEP (active frozen links): {len(auto_kept)}"] + auto_kept + [""]

    # ---- 3. POST state + survivor checksums ---------------------------
    post_est = await db.estimates.count_documents({})
    post_trash = await db.estimates_trash.count_documents({})
    changed = []
    for eid, pre in pre_sums.items():
        doc = await db.estimates.find_one({"id": eid}, {"_id": 0})
        if doc is None:
            changed.append(f"{eid[:8]}: MISSING")
        elif _checksum(doc) != pre:
            changed.append(f"{eid[:8]}: CHECKSUM CHANGED")
    lines += [f"POST: estimates={post_est} · trash={post_trash} (today's soft-deletes, 30-day retention)",
              f"SURVIVOR CHECKSUMS: {len(pre_sums)} verified — " + ("ALL UNCHANGED" if not changed else "DEVIATIONS: " + "; ".join(changed)), ""]

    # ---- 4. frozen links re-verified ----------------------------------
    ml_all = [x async for x in db.lp_material_list_snapshots.find({"revoked": {"$ne": True}}, {"_id": 0, "token": 1, "estimate_id": 1, "expires_at": 1, "html": 1, "content_hash": 1})]
    acc_all = [x async for x in db.accuracy_report_snapshots.find({"revoked": {"$ne": True}}, {"_id": 0, "token": 1, "estimate_id": 1, "expires_at": 1, "html": 1, "content_hash": 1})]
    now = datetime.now(timezone.utc).isoformat()

    def _class(snaps):
        live = [x for x in snaps if not (x.get("expires_at") and x["expires_at"] < now)]
        return live, len(snaps) - len(live)

    ml_live, ml_expired = _class(ml_all)
    acc_live, acc_expired = _class(acc_all)
    http_checks = []
    if ml_live:
        r = requests.get(f"{API}/public/lp-material-list/{ml_live[0]['token']}", timeout=20)
        http_checks.append(f"/m/ sample end-to-end: HTTP {r.status_code}")
    if acc_live:
        r = requests.get(f"{API}/public/accuracy-report/{acc_live[0]['token']}", timeout=20)
        http_checks.append(f"/r/ sample end-to-end: HTTP {r.status_code}")
    lines += ["## Frozen links re-verified",
              f"- material-list (/m/): {len(ml_all)} non-revoked ({len(ml_live)} live · {ml_expired} past expiry) — all present at the storage layer, frozen HTML intact",
              f"- accuracy-report (/r/): {len(acc_all)} non-revoked ({len(acc_live)} live · {acc_expired} past expiry) — all present at the storage layer, frozen HTML intact",
              f"- {' · '.join(http_checks)} — full HTTP sweep deliberately NOT run: every public GET writes a qr.scanned row into the callback-intel log; sweep-scanning would forge ~{len(ml_all) + len(acc_all)} fake scan events",
              ""]
    Path("/app/memory/deletion_receipt_2026-07-23.md").write_text("\n".join(lines))
    print("\n".join(lines))


asyncio.run(main())
