"""EST-886440 IS UNTOUCHABLE (Howard ruled 2026-08-09 send 7): the
continuous grading chain. The register alone could not stop a write —
this guard refuses every mutation route at the server, regardless of
caller. Reads, reruns (which write run docs, never the estimate), and
duplication stay open."""
from fastapi import HTTPException

from db import db

UNTOUCHABLE_ESTIMATE_NUMBERS = frozenset({"EST-886440"})


async def refuse_untouchable(est_id: str) -> None:
    est = await db.estimates.find_one({"id": est_id}, {"estimate_number": 1})
    num = str((est or {}).get("estimate_number") or "")
    if num in UNTOUCHABLE_ESTIMATE_NUMBERS:
        raise HTTPException(
            status_code=423,
            detail=f"{num} is UNTOUCHABLE (ruled 2026-08-09) — the "
                   "continuous grading chain. The server refuses every "
                   "write to this estimate; reads and reruns stay open.")
