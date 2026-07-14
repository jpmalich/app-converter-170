"""Customer-journey event instrumentation (split ruling, 2026-07-14).

Events are captured NOW — events not captured are unrecoverable. The
contractor-facing timeline SURFACE is post-September backlog with an open
design ruling attached (counts vs. timestamps granularity ruled when the
surface is designed).

PIN: contractor-facing intel ONLY —
  • no customer surface may reveal the tracking's existence (public
    responses are never altered by logging)
  • logging never fails the serving request

Record: the existing append-only `tracking[]` array on the estimate doc —
the same record Resend webhook events (email.opened / email.clicked)
already join — capped at the last 500 events. Event types added here:
  quote.sent · quote.viewed (accept page) · quote.accepted ·
  qr.scanned (material_list / accuracy_report; expired scans logged with
  meta.expired=true — callback intel)
"""
from datetime import datetime, timezone

from db import db, logger

TRACKING_CAP = 500


async def log_estimate_event(estimate_id, event_type, meta=None):
    if not estimate_id:
        return
    try:
        rec = {"type": event_type, "at": datetime.now(timezone.utc).isoformat()}
        if meta:
            rec["meta"] = meta
        await db.estimates.update_one(
            {"id": estimate_id},
            {"$push": {"tracking": {"$each": [rec], "$slice": -TRACKING_CAP}}},
        )
    except Exception:
        logger.exception("estimate event log failed (%s)", event_type)
