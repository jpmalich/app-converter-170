"""UNTOUCHABLE GUARD + HUMAN-WRITE LEDGER.

EST-886440 is UNTOUCHABLE (Howard ruled 2026-08-09 send 7): the
continuous grading chain. The register alone could not stop a write —
this guard refuses every DERIVED mutation route at the server,
regardless of caller.

GUARD EXTENSION (Howard ruled 2026-08-11 send-4 item 3):
  THE GUARD BLOCKS DERIVED WRITES. IT NEVER BLOCKS HUMAN ENTRY.
  Tape-check and profile-annotations are MY input. Human entry
  outranks every read by sealed ruling, and a protected estimate that
  will not let me tape is a protection that fights the ladder it
  exists to serve. Those ride above the freeze.
  ACCURACY-REPORT FREEZE/REVOKE IS AN ARTIFACT OPERATION AND IS GUARDED.
  Every human write to a protected estimate GETS LEDGERED — the chain
  should record when I touched it, even though I am allowed to.
GUARD EXTENSION (Howard ruled 2026-08-13 pro-quotes reply 5):
  A DRAWN OR ADJUSTED ZONE IS HUMAN ENTRY. pdf_overlay_polygon
  writes ride above the freeze on protected estimates and land in
  the ledger like tape-check and profile-annotations — built in
  from MUV birth so the walk is possible on EST-886440 (the one
  estimate that carries the whole grading chain, source PDFs, and
  a completed read). Same rule: derived writes still refused;
  human entry outranks the freeze.

The three functions this module exposes:
  refuse_untouchable(est_id)        — derived-write guard (existing).
  ledger_human_write(est_id, kind, actor_email, meta) — every human
    write to a protected estimate lands here so the chain records
    that Howard touched it.
  is_untouchable(est_id) -> bool    — helper.

Reads, reruns, and duplication stay open (they do not mutate the
estimate itself)."""
from datetime import datetime, timezone

from fastapi import HTTPException

from db import db


UNTOUCHABLE_ESTIMATE_NUMBERS = frozenset({"EST-886440"})


async def _estimate_number(est_id: str) -> str:
    est = await db.estimates.find_one(
        {"id": est_id}, {"estimate_number": 1, "protected": 1})
    if not est:
        return ""
    return str(est.get("estimate_number") or "")


async def is_untouchable(est_id: str) -> bool:
    """True when the estimate is on the untouchable frozen set."""
    return (await _estimate_number(est_id)) in UNTOUCHABLE_ESTIMATE_NUMBERS


async def refuse_untouchable(est_id: str) -> None:
    """Guard for DERIVED writes. Refuses PUT/PATCH/DELETE/protection-
    flip/rederive/lp-apply/materialize/order-release/accuracy-report
    freeze/revoke. Applied everywhere the estimate itself would move
    on top of the AI's read."""
    num = await _estimate_number(est_id)
    if num in UNTOUCHABLE_ESTIMATE_NUMBERS:
        raise HTTPException(
            status_code=423,
            detail=f"{num} is UNTOUCHABLE (ruled 2026-08-09) — the "
                   "continuous grading chain. The server refuses every "
                   "derived write to this estimate; reads, reruns, and "
                   "human input (tape-check, profile-annotations) stay "
                   "open per the 2026-08-11 send-4 extension.")


async def ledger_human_write(
    est_id: str, kind: str, actor_email: str = "",
    meta: dict | None = None,
) -> None:
    """Ledger every human write to a protected estimate. Human input
    RIDES ABOVE THE FREEZE (Howard ruled 2026-08-11 send-4 item 3):
    tape-check and profile-annotations are the contractor's own hand,
    and a protected estimate that refuses the ladder-work it exists
    to serve is a protection that fights itself.

    Ledgered writes: kind ∈ {"tape_check", "profile_annotations",
    "flag_checklist", "tape_check_score", "pdf_overlay_polygon"}.
    Free to extend; the point is that the chain records when Howard
    touched it. Send-11 pro-quotes-reply-5 added pdf_overlay_polygon
    as a human-entry class at MUV birth (not discovered later): a
    drawn or adjusted zone is Howard's hand on the drawing, so it
    rides above the freeze on EST-886440 and lands here on every
    write.

    No-op on non-untouchable estimates (the ledger is scoped to the
    frozen set — a general audit log lives elsewhere)."""
    if not await is_untouchable(est_id):
        return
    await db.protected_estimate_ledger.insert_one({
        "estimate_id": est_id,
        "kind": kind,
        "actor_email": actor_email or "",
        "meta": meta or {},
        "at": datetime.now(timezone.utc),
    })
