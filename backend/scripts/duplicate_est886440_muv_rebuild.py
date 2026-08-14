"""One-shot: duplicate EST-886440 into an UNPROTECTED draft for the MUV
rebuild-survival walk (Howard ruled 2026-08-14).

Four checks (Howard's ruling):
  1. The duplicate CARRIES a completed blueprint read + its source pages
     (the latest done run is copied, re-pointed to the new estimate id).
  2. It does NOT inherit the protected_estimate_ledger (that chain
     belongs to the original; the ledger collection is est_id-scoped so
     the fresh id simply has none — verified).
  3. The duplication is LOGGED on the ORIGINAL's ledger (one line).
  4. It gets a DISTINCT name ("Boni — MUV rebuild test"), not a twin.

Inserts only (new estimate + new run + one ledger row). No existing doc
is modified — EST-886440 is untouched (nothing applies to it). A read
snapshot is still written to memory/backups for traceability.
"""
import os, sys, uuid, json, time
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

ORIG_NO = "EST-886440"
DUP_NAME = "Boni — MUV rebuild test"

c = MongoClient(os.environ["MONGO_URL"])
db = c[os.environ["DB_NAME"]]

orig = db.estimates.find_one({"estimate_number": ORIG_NO})
if not orig:
    sys.exit(f"original {ORIG_NO} not found")
orig_id = orig["id"]

# latest completed blueprint run for the original
run = db.ai_blueprint_runs.find_one(
    {"estimate_id": orig_id, "status": "done"}, sort=[("created_at", -1)])
if not run:
    sys.exit("no completed blueprint run on the original — nothing to carry")

now = datetime.now(timezone.utc)
ts = now.strftime("%Y%m%d_%H%M%S")

# --- pre-heal / traceability snapshot (read-only; we only insert) ---
bdir = "/app/memory/backups"
os.makedirs(bdir, exist_ok=True)
snap = {"_id": str(orig.get("_id"))}
snap.update({k: v for k, v in orig.items() if k != "_id"})
with open(f"{bdir}/{ts}_est886440_pre_duplicate_snapshot.json", "w") as f:
    json.dump(snap, f, default=str, indent=1)

# --- build the duplicate (a fresh draft) ---
dup = {k: v for k, v in orig.items()
       if k not in ("_id", "id",
                    "protected", "protected_at", "protected_reason",
                    "protected_estimate_ledger",
                    "accept_token", "accepted_at", "accepted_ip", "accepted_note",
                    "last_sent_at", "recipient_email")}
new_id = str(uuid.uuid4())
new_no = f"EST-{int(time.time()) % 1_000_000:06d}"
dup.update({
    "id": new_id,
    "estimate_number": new_no,
    "customer_name": DUP_NAME,               # DISTINCT name (check 4)
    "created_at": now.isoformat(),
    "updated_at": now.isoformat(),
    "estimate_date": now.isoformat()[:10],
    "status_label": "draft",
})
db.estimates.insert_one(dict(dup))

# --- carry the completed read + source pages (check 1) ---
new_run = {k: v for k, v in run.items() if k != "_id"}
new_run_id = uuid.uuid4().hex
new_run.update({
    "run_id": new_run_id,
    "estimate_id": new_id,
    "created_at": now,
    "updated_at": now,
    "rerun_of": run.get("run_id"),
})
db.ai_blueprint_runs.insert_one(dict(new_run))

# --- log the duplication on the ORIGINAL's ledger (check 3) ---
db.protected_estimate_ledger.insert_one({
    "estimate_id": orig_id,
    "kind": "duplicated",
    "actor_email": "hhunt6677@yahoo.com",
    "meta": {"to_estimate_number": new_no, "to_id": new_id,
             "reason": "MUV rebuild-survival walk (unprotected copy)",
             "run_copied": run.get("run_id"), "new_run": new_run_id},
    "at": now,
})

# --- VERIFY the four checks ---
d = db.estimates.find_one({"id": new_id}, {"_id": 0})
print("=== DUPLICATE CREATED ===")
print("new estimate_number:", new_no)
print("new id:", new_id)
print("name:", d.get("customer_name"))
print("lines carried:", len(d.get("lines") or []))
print("CHECK 1 completed read carried:",
      db.ai_blueprint_runs.count_documents({"estimate_id": new_id, "status": "done"}) >= 1,
      "| page_paths present:", bool(new_run.get("page_paths")))
print("CHECK 2 no inherited ledger:",
      db.protected_estimate_ledger.count_documents({"estimate_id": new_id}) == 0)
print("   duplicate protected fields:",
      {k: d.get(k) for k in ("protected", "protected_at", "protected_reason")})
print("CHECK 3 logged on original ledger:",
      db.protected_estimate_ledger.count_documents(
          {"estimate_id": orig_id, "kind": "duplicated", "meta.to_id": new_id}) == 1)
print("CHECK 4 distinct name:", d.get("customer_name") == DUP_NAME
      and d.get("customer_name") != orig.get("customer_name"))
print("original still protected (untouched):",
      db.estimates.find_one({"id": orig_id}, {"protected": 1}).get("protected"))
