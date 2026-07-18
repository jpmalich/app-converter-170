"""Run archival for persistent artifacts (ruled 2026-07-14).

PIN: no persistent artifact may reference a reapable run. Any event that
embeds a run's data in a persistent artifact archives that run into
`fixture_runs` (no TTL):
  • quote-send            (routes/email.py::email_quote)
  • /m/ freeze-minting    (routes/lp_package_routes.py::lp_material_list_freeze)
  • /r/ freeze-minting    (routes/estimates.py::_freeze_accuracy_snapshot)
  • material-order send   (endpoint does not exist yet — MUST call
                           archive_run_for_artifact when it ships)
Unreferenced runs keep their substrate TTL (correct hygiene).
Read side: lp_package_routes._load_run falls back to fixture_runs so a
November callback still gets its Material List panel + 3D.

TTL pin, SECOND instance (ruled 2026-07-18): archival covers ALL reapable
run substrates — ai_measure_runs (30d), ai_blueprint_runs (24h) AND
hover_import_runs (24h). The Haugh hover pin substrate (4ffc35f4…) reaped
under the 24h TTL because hover runs were outside the archival bounds.
New trigger: routes/hover.py::hover_lp_run archives BOTH the materialized
LP run and its SOURCE hover run the moment an estimate stamp is minted.
Incident log: /app/memory/incident_2026-07-18_ttl_expiry_second_instance.md
"""
import re

from db import db, logger

# Every run substrate carrying a Mongo TTL index (inventoried live from
# index_information(), not from memory — see the incident log's table).
_RUN_SUBSTRATE_COLLS = ("ai_measure_runs", "ai_blueprint_runs", "hover_import_runs")


async def archive_run_for_artifact(estimate_id=None, run_id=None, reason=""):
    """Upsert the referenced done run into fixture_runs. Explicit run_id
    wins; otherwise the estimate's latest done non-probe run. Idempotent
    and never raises — artifact creation must not fail on archival."""
    try:
        run = None
        if run_id:
            # ALL TTL'd run substrates are archival sources (2nd-instance
            # pin, 2026-07-18) — never enumerate a subset from memory.
            for coll_name in _RUN_SUBSTRATE_COLLS:
                run = await db[coll_name].find_one({"run_id": run_id}, {"_id": 0})
                if run is not None:
                    run["substrate"] = coll_name
                    break
            if run is None and await db.fixture_runs.find_one({"run_id": run_id}, {"_id": 1}):
                if reason:
                    await db.fixture_runs.update_one(
                        {"run_id": run_id}, {"$addToSet": {"artifact_reasons": reason}})
                return run_id
        if run is None and estimate_id:
            run = await db.ai_measure_runs.find_one(
                {"estimate_id": estimate_id, "status": "done", "usage_probe": {"$ne": True}},
                {"_id": 0}, sort=[("created_at", -1)])
            if run is not None:
                run["substrate"] = "ai_measure_runs"
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


async def find_archived_run(query):
    """Read side of the artifact pin — serve archived runs after the live
    ai_measure_runs doc reaps. fixture_runs access is owned by THIS module
    (fork-boundary: LP routers must not touch untagged collections)."""
    return await db.fixture_runs.find_one(query, {"_id": 0}, sort=[("created_at", -1)])


async def list_archived_runs(query, projection):
    """Bulk read side (extraction-spend telemetry, 2026-07-15) — same
    fork-boundary ownership rule as find_archived_run."""
    return await db.fixture_runs.find(query, projection).to_list(length=None)


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
        # 2nd-instance pin (2026-07-18): an estimate's lp_source_run_id
        # stamp is a persistent artifact — sweep every stamp, and for
        # hover-materialized stamps also archive the SOURCE hover run
        # (24h TTL — the reapable class that broke the Haugh pins).
        async for est in db.estimates.find(
            {"lp_source_run_id": {"$exists": True, "$nin": [None, ""]}},
            {"_id": 0, "id": 1, "lp_source_run_id": 1},
        ):
            stamp = str(est.get("lp_source_run_id") or "").strip()
            if not stamp:
                continue
            rid = await archive_run_for_artifact(run_id=stamp, reason="backfill:lp-stamp")
            if rid:
                archived.add(rid)
            m = re.match(r"^hover-([0-9a-f]{8,12})-", stamp)
            if m:
                src = await db.hover_import_runs.find_one(
                    {"run_id": {"$regex": f"^{m.group(1)}"}}, {"_id": 0, "run_id": 1})
                if src:
                    rid = await archive_run_for_artifact(
                        run_id=src["run_id"], reason="backfill:hover-source")
                    if rid:
                        archived.add(rid)
                elif not await db.fixture_runs.find_one(
                        {"run_id": {"$regex": f"^{m.group(1)}"}}, {"_id": 1}):
                    logger.warning(
                        "run-archive backfill: hover source for stamp %s already reaped "
                        "(unrecoverable — re-upload the Hover PDF)", stamp)
        if archived:
            logger.info("run-archive backfill: %d artifact-referenced run(s) ensured in fixture_runs", len(archived))
    except Exception:
        logger.exception("run-archive backfill failed")
    return archived
