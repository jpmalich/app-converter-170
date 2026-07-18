"""DEMO RESET (ruled 2026-06): stages the Letrick showcase estimate for
walkthroughs. Idempotent wipe-and-rebuild of ONE dedicated, flagged demo
estimate — never touches real contractor data, pipeline records of other
estimates, or tier assignments. Runs with LP-native mode ON."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user

router = APIRouter()

DEMO_KEY = "letrick_demo"
# fixed, self-identifying run id — [:8] renders as "demo-let" in UIs
DEMO_RUN_ID = "demo-letrick-4a009e93"
# the post-C4 Letrick validation run (frozen provenance) — cloned read-only
SOURCE_RUN_ID = "4a009e93eb5348c08cc26bfb935675ce"
DEMO_COLORS = {
    "siding": "Quarry Gray",
    "soffit_fascia": "Snowscape White",
    "opening_trim": "Snowscape White",
    "osc": "Quarry Gray",
    "isc": "Quarry Gray",
}
DEMO_TIER = "Contractor"

# Letrick taped ground truth — FROZEN into code (Iter 112) after the
# original EST-191890 source estimate was deleted from the dashboard;
# the demo depends only on the cloned run + these truths now.
LETRICK_TAPE_WALLS = {
    "front": {"segments": [{"height_ft": 8.96, "courses": 25}], "start_ref": "siding_start"},
    "back": {"segments": [{"height_ft": 9.92, "courses": 28}], "start_ref": "siding_start"},
    "left": {"segments": [{"height_ft": 8.96, "courses": 25},
                          {"height_ft": 9.92, "courses": 28}], "start_ref": "siding_start"},
    "right": {"segments": [{"height_ft": 8.96, "courses": 25},
                           {"height_ft": 9.92, "courses": 28}], "start_ref": "siding_start"},
}


@router.get("/demo/status")
async def demo_status(user: dict = Depends(get_current_user)):
    """Preflight for the reset confirmation — surfaces how many printed
    QR links a reset would revoke (the print-then-reset footgun)."""
    est = await db.estimates.find_one(
        {"company_id": user["company_id"], "demo_key": DEMO_KEY},
        {"_id": 0, "id": 1})
    if not est:
        return {"exists": False, "qr_tokens": 0}
    ml = await db.lp_material_list_snapshots.count_documents(
        {"estimate_id": est["id"], "revoked": {"$ne": True}})
    acc = await db.accuracy_report_snapshots.count_documents(
        {"estimate_id": est["id"], "revoked": {"$ne": True}})
    return {"exists": True, "estimate_id": est["id"], "qr_tokens": ml + acc}


@router.post("/demo/reset")
async def demo_reset(user: dict = Depends(get_current_user)):
    # The frozen source run must OUTLIVE the ai_measure_runs 30-day TTL
    # (demo day is past that horizon): archive it into fixture_runs
    # (no TTL) on first touch and prefer the archived copy thereafter.
    src_run = await db.fixture_runs.find_one({"run_id": SOURCE_RUN_ID}, {"_id": 0})
    if not src_run:
        src_run = await db.ai_measure_runs.find_one({"run_id": SOURCE_RUN_ID}, {"_id": 0})
        if src_run:
            await db.fixture_runs.update_one(
                {"run_id": SOURCE_RUN_ID}, {"$set": src_run}, upsert=True)
    if not src_run:
        raise HTTPException(status_code=404, detail="Letrick source run not found")
    # hard isolation: only the fixture-owner's company can stage the demo
    # (gated via the frozen run's owner — the original source estimate no
    # longer exists)
    run_owner = await db.users.find_one(
        {"id": src_run.get("user_id")}, {"_id": 0, "company_id": 1})
    if not run_owner or run_owner.get("company_id") != user["company_id"]:
        raise HTTPException(status_code=403,
                            detail="Demo reset is restricted to the fixture owner's company")

    # ── WIPE — scoped EXCLUSIVELY to the flagged demo estimate's documents
    old = await db.estimates.find_one(
        {"company_id": user["company_id"], "demo_key": DEMO_KEY}, {"_id": 0, "id": 1})
    if old:
        await db.ai_measure_runs.delete_many({"estimate_id": old["id"]})
        await db.lp_material_list_snapshots.delete_many({"estimate_id": old["id"]})
        await db.accuracy_report_snapshots.delete_many({"estimate_id": old["id"]})
        await db.estimates.delete_one({"id": old["id"], "demo_key": DEMO_KEY})

    # ── REBUILD (deterministic staged state)
    now = datetime.now(timezone.utc).isoformat()
    est_id = str(uuid.uuid4())
    await db.estimates.insert_one({
        "id": est_id, "company_id": user["company_id"], "demo_key": DEMO_KEY,
        "kind": "lp_smart",
        "estimate_number": "DEMO-LETRICK",
        "customer_name": "Letrick Blueprint House — DEMO",
        "address": "Letrick showcase fixture",
        "estimate_date": now[:10],
        "created_at": now, "updated_at": now,
        "created_by": user["id"], "created_by_name": user.get("name"),
        "status_label": "draft",
        "lines": [], "misc_labor": [], "misc_material": [],
        "lp_pricing_tier": DEMO_TIER,
        "lp_colors": dict(DEMO_COLORS),
        # frozen Letrick taped truths; the single history entry is
        # re-scored below (never copied)
        "tape_check": {"walls": LETRICK_TAPE_WALLS,
                       "dormers": [],
                       "held_out": False, "updated_at": now, "history": []},
    })

    run = dict(src_run)
    run.update({"run_id": DEMO_RUN_ID, "estimate_id": est_id, "user_id": user["id"],
                "created_at": now, "updated_at": now, "completed_at": now})
    await db.ai_measure_runs.insert_one(run)

    # seed stored lines from the run (same path pair-lp uses) at the
    # demo tier — tier coherence: one estimate, one tier, every surface
    from routes.catalog import _resolve_catalog_for_company
    from routes.hover import _build_lines
    measurements = ((src_run.get("result") or {}).get("measurements")) or {}
    company = await db.companies.find_one({"id": user["company_id"]}, {"_id": 0})
    catalog = await _resolve_catalog_for_company(company, lp_tier_override=DEMO_TIER)
    price_idx = {}
    for sec in catalog.get("sections", []):
        for it in sec.get("items", []):
            price_idx[(sec["title"], it["name"])] = it
    seeded = []
    for ln in _build_lines(measurements):
        if ln.get("tab") != "lp_smart":
            continue
        try:
            qty = float(ln.get("qty") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        cat_row = price_idx.get((ln.get("section"), ln.get("name")), {})
        doc = {"section": ln.get("section", ""), "name": ln.get("name", ""),
               "unit": ln.get("unit") or cat_row.get("unit", ""), "qty": qty,
               "mat": float(cat_row.get("mat") or 0),
               "lab": float(cat_row.get("lab") or 0),
               "ami_part": cat_row.get("ami_part"), "tab": "lp_smart", "adders": []}
        if not cat_row or cat_row.get("pricing_pending"):
            doc["pricing_pending"] = True
        if cat_row.get("pricing_source"):
            doc["pricing_source"] = cat_row["pricing_source"]
        seeded.append(doc)
    await db.estimates.update_one({"id": est_id}, {"$set": {"lines": seeded}})

    # one scored run in the accuracy history (dev-fixture framing applies)
    from routes.estimates import accuracy_report_freeze, score_tape_check
    scored = await score_tape_check(est_id, {"run_id": DEMO_RUN_ID}, user)

    # LP-native mode is a GLOBAL presentation filter — flipping it here
    # would strip non-LP catalogs for every contractor (isolation rule
    # forbids that). The demo estimate is BUILT to run with the mode ON
    # (kind lp_smart, LP-only lines); flip the switch itself from the LP
    # admin panel for demo day. We report the current state.
    from routes.lp_admin import load_lp_native_mode
    native_on = await load_lp_native_mode()

    # frozen QR links minted (material list + accuracy report)
    from routes.lp_package_routes import lp_material_list_freeze, lp_package_preview
    ml = await lp_material_list_freeze(
        est_id, {"run_id": DEMO_RUN_ID, "colors": dict(DEMO_COLORS)}, user)
    acc = await accuracy_report_freeze(est_id, user)

    # staged-state readout from the actual derivation surface
    pkg = await lp_package_preview(est_id, {"run_id": DEMO_RUN_ID}, user)
    ambers = pkg.get("amber_items") or []
    op = pkg.get("openings_review") or {}
    subs = [l["name"] for l in pkg.get("lines") or []
            if (l.get("substitutable_with") or [])]

    staged = {
        "estimate_id": est_id,
        "estimate_number": "DEMO-LETRICK",
        "run_id": DEMO_RUN_ID,
        "lp_native_mode": native_on,
        "pricing_tier": DEMO_TIER,
        "colors": dict(DEMO_COLORS),
        "tape_check_scored": {
            "accuracy_pct": (scored.get("entry") or {}).get("accuracy_pct"),
            "history_entries": 1,
        },
        "ambers_unratified": [
            {"kind": a.get("kind"), "locator": a.get("locator"),
             "status": a.get("status")} for a in ambers],
        "openings_review": {
            "items": len(op.get("items") or []),
            "unconfirmed": sum(
                1 for i in (op.get("items") or [])
                if i.get("status") in (None, "", "unconfirmed")),
        },
        "substitutable_lines": subs,
        "package_lines": len(pkg.get("lines") or []),
        "stored_lines_seeded": len(seeded),
        "share_links": {
            "material_list": ml.get("share_path"),
            "accuracy_report": acc.get("share_path"),
        },
    }
    await db.estimates.update_one(
        {"id": est_id}, {"$set": {"demo_staged": staged}})
    return staged
