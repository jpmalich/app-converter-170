"""PROVISIONING GATE + SEED APPLY over HTTP (Howard's ruling 2026-07-23).

HARD CONDITION (ruled): supplier-admin AUTHENTICATION REQUIRED — the gate
reports environment internals and is never public/unauthed. Same
`X-Admin-Token` header check as every other /admin surface.

  GET  /api/admin/provisioning-gate  — the morning-of verifier: every
       seed checksum checked, GREEN/RED report (demo-script checklist line)
  POST /api/admin/seed-apply         — runs the seed runner's apply on THIS
       environment (prod has no shell — this is the ruled sequence's
       "seed_runner apply on prod" executed through the machinery);
       idempotent, insert-only for estimates, background task; poll the
       gate for the outcome
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from db import db
from deps import check_admin_token

router = APIRouter()

_last_apply = {"state": "never-run"}


@router.get("/admin/provisioning-gate")
async def provisioning_gate(_=Depends(check_admin_token)):
    from seed.seed_runner import verify
    result = await verify(db)
    return {"status": result["status"],
            "green": len(result["green"]), "red": len(result["red"]),
            "checks": result["green"] + result["red"],
            "last_apply": _last_apply}


async def _run_apply():
    from seed.seed_runner import apply
    try:
        report = await apply(db)
        _last_apply.update({"state": "done", "report": report,
                            "finished_at": datetime.now(timezone.utc).isoformat()})
    except Exception as e:  # surfaced via the gate, never swallowed silently
        _last_apply.update({"state": "failed", "error": str(e),
                            "finished_at": datetime.now(timezone.utc).isoformat()})


@router.post("/admin/seed-apply")
async def seed_apply(_=Depends(check_admin_token)):
    if _last_apply.get("state") == "running":
        return {"started": False, "state": "running"}
    _last_apply.clear()
    _last_apply.update({"state": "running",
                        "started_at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(_run_apply())
    return {"started": True, "state": "running"}
