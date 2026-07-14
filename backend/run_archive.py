"""Run archival for persistent artifacts (ruled 2026-07-14).

PIN: no persistent artifact may reference a reapable run. Any event that
embeds a run's data in a persistent artifact archives that run into
`fixture_runs` (no TTL):
  • quote-send            (routes/email.py::email_quote)
  • /m/ freeze-minting    (routes/lp_package_routes.py::lp_material_list_freeze)
  • /r/ freeze-minting    (routes/estimates.py::_freeze_accuracy_snapshot)
  • material-order send   (endpoint does not exist yet — MUST call
                           archive_run_for_artifact when it ships)
Unreferenced runs keep the 30-day ai_measure_runs TTL (correct hygiene).
Read side: lp_package_routes._load_run falls back to fixture_runs so a
November callback still gets its Material List panel + 3D.
"""
from db import db, logger


async def archive_run_for_artifact(estimate_id=None, run_id=None, reason=""):
    """Upsert the referenced done run into fixture_runs. Explicit run_id
    wins; otherwise the estimate's latest done non-probe run. Idempotent
    and never raises — artifact creation must not fail on archival."""
    try:
        run = None
        if run_id:
            run = await db.ai_measure_runs.find_one({"run_id": run_id}, {"_id": 0})
            if run is None and await db.fixture_runs.find_one({"run_id": run_id}, {"_id": 1}):
                if reason:
                    await db.fixture_runs.update_one(
                        {"run_id": run_id}, {"$addToSet": {"artifact_reasons": reason}})
                return run_id
        if run is None and estimate_id:
            run = await db.ai_measure_runs.find_one(
                {"estimate_id": estimate_id, "status": "done", "usage_probe": {"$ne": True}},
                {"_id": 0}, sort=[("created_at", -1)])
        if not run or not run.get("run_id"):
            return None
        # docs cloned FROM fixture_runs (demo flows) may carry
        # artifact_reasons — strip to avoid a $set/$addToSet path conflict
        run.pop("artifact_reasons", None)
        update = {"$set": run}
        if reason:
            update["$addToSet"] = {"artifact_reasons": reason}
        await db.fixture_runs.update_one({"run_id": run["run_id"]}, update, upsert=True)
        return run["run_id"]
    except Exception:
        logger.exception("run archive failed (reason=%s)", reason)
        return None


async def backfill_artifact_referenced_runs():
    """Ruled backfill: archive runs already referenced by sent quotes or
    live QR freezes — November callbacks must not depend on when this
    shipped. Idempotent (upserts); runs every boot."""
    archived = set()
    try:
        async for est in db.estimates.find(
            {"$or": [{"status_label": "sent"}, {"last_sent_at": {"$exists": True}}]},
            {"_id": 0, "id": 1},
        ):
            rid = await archive_run_for_artifact(
                estimate_id=est["id"], reason="backfill:quote-send")
            if rid:
                archived.add(rid)
        async for s in db.lp_material_list_snapshots.find(
            {"revoked": {"$ne": True}},
            {"_id": 0, "estimate_id": 1, "snapshot.run_id": 1},
        ):
            rid = await archive_run_for_artifact(
                estimate_id=s.get("estimate_id"),
                run_id=(s.get("snapshot") or {}).get("run_id"),
                reason="backfill:m-freeze")
            if rid:
                archived.add(rid)
        async for s in db.accuracy_report_snapshots.find(
            {"revoked": {"$ne": True}}, {"_id": 0, "estimate_id": 1},
        ):
            rid = await archive_run_for_artifact(
                estimate_id=s.get("estimate_id"), reason="backfill:r-freeze")
            if rid:
                archived.add(rid)
        if archived:
            logger.info("run-archive backfill: %d artifact-referenced run(s) ensured in fixture_runs", len(archived))
    except Exception:
        logger.exception("run-archive backfill failed")
    return archived
