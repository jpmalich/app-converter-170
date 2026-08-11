"""ONE-SHOT: mark EST-886440 protected = True.

Howard ordered 2026-08-11 send-3: "YES to marking EST-886440 protected
so every future run archives at birth."

The untouchable guard (backend/untouchable.py, ruled 2026-08-09) refuses
every write route to EST-886440 including the protection-flip route
itself. Marking it protected is a legitimate deliberate act that must
bypass the guard once (its whole purpose is to hard-freeze the estimate
in its current state — protection is a property OF that state, not
another mutation of it).

PERMANENT RULE (Iter 79j.63, permanent) — pre-heal backup satisfied:
  /app/memory/backups/20260811_est886440_protect_preheal.json
  (created 2026-08-11 by hand — full doc snapshot).

Effect after this script runs:
  - est.protected = True (a value the delete route refuses regardless
    of caller; auto-archive-on-birth kicks in for every future run
    against EST-886440 via routes/ai_blueprint.py's archive-on-view
    seam that already checks est.protected).

Idempotent: re-running is a no-op if protected is already True. The
script REFUSES to run against any estimate whose number is NOT in the
UNTOUCHABLE_ESTIMATE_NUMBERS set — you cannot use it to protect a
different estimate.
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import db  # noqa: E402
from untouchable import UNTOUCHABLE_ESTIMATE_NUMBERS  # noqa: E402


TARGET_NUMBER = "EST-886440"
PREHEAL = Path("/app/memory/backups/20260811_est886440_protect_preheal.json")


async def main() -> None:
    if TARGET_NUMBER not in UNTOUCHABLE_ESTIMATE_NUMBERS:
        raise SystemExit(
            f"REFUSED: {TARGET_NUMBER} is not in "
            "UNTOUCHABLE_ESTIMATE_NUMBERS — this script only protects "
            "the pre-declared estimate.")
    if not PREHEAL.exists():
        raise SystemExit(
            f"REFUSED: pre-heal backup {PREHEAL} does not exist. "
            "Create it before mutating (permanent rule Iter 79j.63).")
    doc = await db.estimates.find_one(
        {"estimate_number": TARGET_NUMBER}, {"id": 1, "protected": 1})
    if not doc:
        raise SystemExit(f"REFUSED: {TARGET_NUMBER} not found in DB.")
    if doc.get("protected") is True:
        print(f"NOOP: {TARGET_NUMBER} already protected. Nothing to do.")
        return
    res = await db.estimates.update_one(
        {"id": doc["id"]},
        {"$set": {"protected": True,
                  "updated_at": datetime.now(timezone.utc),
                  "protected_reason": (
                      "Howard ruled 2026-08-11 send-3: EST-886440 is the "
                      "continuous grading chain; every future run "
                      "archives at birth."),
                  "protected_at": datetime.now(timezone.utc)}},
    )
    print(f"HEAL: matched={res.matched_count} modified={res.modified_count}")
    print(f"pre-heal backup: {PREHEAL}")


if __name__ == "__main__":
    asyncio.run(main())
