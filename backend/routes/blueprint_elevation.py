"""BLUEPRINT ELEVATION SHEET — PHASE 1 (Howard ordered 2026-08-10; scope
filed memory/takeoff_elevations_scope_2026_08_09.md, ruling: approach (A)).

A SYNTHETIC elevation rendered from the blueprint model — never the
architectural sheet painted over. Same sheet contract as the photo
door's elevation_sheets endpoint, so the frontend SheetSvg renders it
UNCHANGED. Honesty carries onto the drawing:
- printed (quoted) dims tag PRINTED ✓; unquoted values tag AI-READ ⚠;
- a wall with no readable height hatches NEEDS YOUR TAPE (the Boni back
  garage wing is the acceptance case);
- opening positions are SCHEMATIC (even spacing, schedule-attributed)
  and say so — never claimed as placed;
- mark-merge-suspected openings carry the suspicion onto the sheet.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user
from routes.elevation_sheets import (
    _SHEET_CODES, _VIEW_DATUM, WINDOW_HEAD_ANCHOR_IN, _bind_roofline,
    fmt_ftin,
)

router = APIRouter()


def _ev_tag(ev: dict, key: str, val) -> tuple[str, str]:
    """(tag, source) for a dim — quoted printed dim, unquoted read, or
    unread. Evidence keys follow the worker's 'walls.front.width_ft'
    convention."""
    if val is None:
        return "UNREAD", "no printed dimension survived evidence-or-null"
    e = ev.get(key) or {}
    q = str(e.get("from") or "").strip()
    if q:
        loc = f" p.{e['page']}" if e.get("page") else ""
        return "AI-READ ✓", f"printed dim \u201c{q}\u201d{loc} (quoted, located)"
    return "AI-READ ⚠", "read without a surviving quote"


def build_blueprint_sheet(est: dict, run: dict, which: str) -> dict:
    raw = (run.get("result") or {}).get("raw_ai") or {}
    ev = raw.get("_dim_evidence") or {}
    wall = next((w for w in (raw.get("walls") or [])
                 if str(w.get("label", "")).lower() == which), None)
    run_short = str(run.get("run_id", ""))[:8]

    width_ft = height_ft = None
    gable_ft = 0
    hatch = None
    if wall:
        width_ft = wall.get("width_ft")
        height_ft = wall.get("height_ft")
        gable_ft = wall.get("gable_triangle_height_ft") or 0
    width_tag, width_src = _ev_tag(ev, f"walls.{which}.width_ft", width_ft)
    height_tag, height_src = _ev_tag(ev, f"walls.{which}.height_ft", height_ft)
    if height_ft is None and raw.get("avg_wall_height_ft"):
        height_ft = float(raw["avg_wall_height_ft"])
        height_tag = "ESTIMATED"
        height_src = ("avg_wall_height_ft fallback — DERIVED, "
                      "NEEDS YOUR TAPE")
        hatch = "height unread on this wall — drawn at the average wall height, NEEDS YOUR TAPE"
    if wall is None:
        hatch = f"the blueprint read carries no {which} wall — NEEDS YOUR TAPE"
    elif width_ft is None:
        hatch = "width unread on this wall — not drawable, NEEDS YOUR TAPE"
    elif height_ft is None:
        hatch = "height unread on this wall — not drawable, NEEDS YOUR TAPE"

    # ── openings: schedule-attributed to this elevation; positions
    # SCHEMATIC even spacing — labeled, never claimed as placed.
    merge_marks = {str(m) for e2 in (raw.get("_mark_merge_suspected") or [])
                   for m in (e2.get("marks") or [])}
    rows = []
    for d in (raw.get("doors") or []):
        if str(d.get("elevation", "")).lower() == which:
            rows.append(("door", d))
    for w2 in (raw.get("windows") or []):
        if str(w2.get("elevation", "")).lower() == which:
            rows.append(("window", w2))
    expanded = []
    for kind, o in rows:
        try:
            q = max(int(o.get("qty") or 1), 1)
        except (TypeError, ValueError):
            q = 1
        expanded.extend((kind, o) for _ in range(min(q, 12)))
    openings = []
    wn = dn = pn = gn = 0
    n = len(expanded)
    for i, (kind, o) in enumerate(expanded):
        hint = f"{o.get('type_hint') or ''} {o.get('product_code') or ''}".lower()
        if kind == "door" and "garage" in hint:
            gn += 1
            tag, typ = f"G{gn}", "Garage door"
        elif kind == "door" and ("patio" in hint or "slid" in hint or "sgd" in hint):
            pn += 1
            tag, typ = f"P{pn}", "Patio door"
        elif kind == "door":
            dn += 1
            tag, typ = f"D{dn}", "Entry door"
        else:
            wn += 1
            tag, typ = f"W{wn}", "Window"
        center = (round(float(width_ft) * (i + 1) / (n + 1), 2)
                  if width_ft else None)
        h_in = o.get("height_in")
        if kind == "door":
            sill_in = 0.0
            sill_tag = "SCHEMATIC (doors at grade — convention)"
        elif h_in:
            sill_in = round(WINDOW_HEAD_ANCHOR_IN - float(h_in), 1)
            sill_tag = "SCHEMATIC (6'-8\" header convention)"
        else:
            sill_in, sill_tag = None, "—"
        suspect = str(o.get("id") or "") in merge_marks
        openings.append({
            "on_dormer": False, "dormer_face": None,
            "tag": tag,
            "opening_id": o.get("id"),
            "type": typ,
            "style": o.get("type_hint") or "",
            "width_in": o.get("width_in"),
            "height_in": h_in,
            "center_ft": center,
            "center_label": fmt_ftin(center) if center is not None else "—",
            "position_tag": ("SCHEMATIC — schedule-attributed, NOT placed"
                             + (" · MERGE-SUSPECT ⚠" if suspect else "")),
            "sill_in": sill_in,
            "sill_label": (fmt_ftin(sill_in / 12.0)
                           if sill_in is not None else "—"),
            "sill_tag": sill_tag,
            "confirmed": not suspect,
            "collision": False,
        })
    windows = [o for o in openings if o["type"] == "Window"]
    doors = [o for o in openings if o["type"] == "Entry door"]
    patio_doors = [o for o in openings if o["type"] == "Patio door"]
    garage_doors = [o for o in openings if o["type"] == "Garage door"]

    roofline = (_bind_roofline(raw, which, height_ft, height_tag)
                if height_ft is not None else None)
    segs = (wall or {}).get("height_segments") or []
    step_note = None
    if len(segs) > 1:
        parts = []
        for s in segs:
            nm = str(s.get("name") or "segment")
            hv = s.get("height_ft")
            parts.append(f"{nm} {fmt_ftin(hv) if hv is not None else 'UNREAD'}")
        step_note = ("STEPPED WALL — drawn as one rectangle at the eave "
                     "height; printed segments: " + " · ".join(parts)
                     + " (step location not read)")

    area = (round(float(width_ft) * float(height_ft), 1)
            if width_ft and height_ft and len(segs) <= 1 else None)
    schedule_note = ("Sizes: schedule-printed (COUNT COLUMN GOVERNS). "
                     "Positions SCHEMATIC — even spacing within the "
                     "attributed wall, never claimed as placed. Sills: "
                     "doors at grade, windows head-anchored 6'-8\" — "
                     "conventions, not reads.")
    if not openings:
        schedule_note = "No schedule openings attributed to this elevation."
    if merge_marks & {o["opening_id"] for o in openings if o["opening_id"]}:
        schedule_note += (" MARK-MERGE SUSPECTED on this sheet — suspect "
                          "openings flagged; verify against the schedule.")

    return {
        "sheet": which,
        "sheet_code": _SHEET_CODES[which],
        "source_door": "blueprint",
        "synthetic_note": ("SYNTHETIC ELEVATION — rendered from the "
                           "blueprint model (approach A, ruled "
                           "2026-08-09); never the architectural sheet"),
        "hatch_needs_tape": hatch,
        "customer_name": est.get("customer_name"),
        "address": est.get("address"),
        "estimate_number": est.get("estimate_number"),
        "generated_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "wall": {
            "width_ft": width_ft,
            "width_label": fmt_ftin(width_ft) if width_ft is not None else "—",
            "height_ft": height_ft,
            "height_label": fmt_ftin(height_ft) if height_ft is not None else "—",
            "width_tag": width_tag,
            "width_source": f"blueprint run {run_short} — {width_src}",
            "height_tag": height_tag,
            "height_formula": f"blueprint run {run_short} — {height_src}",
            "exposure_in": None, "courses": None, "courses_label": None,
            "ai_count_note": None, "exposure_basis": None,
            "segments": None,
            "step_note": step_note,
            "area_sqft": area,
            "area_note": ("not derivable — wall not fully read"
                          if area is None and len(segs) <= 1 else
                          ("stepped wall — area needs segment layout"
                           if len(segs) > 1 else None)),
            "gable_triangle_ft": gable_ft,
            "gable_tag": "AI-READ ⚠",
            "siding_pct": (wall or {}).get("siding_pct_this_wall"),
            "profile_callout": (wall or {}).get("wall_body_profile_callout") or "",
            "profile_key_item": "",
            "stories": raw.get("story_count"),
            "overhang_in": raw.get("overhang_in") or 12.0,
            "ai_confidence": None,
            "ai_reasoning": "",
            "source_photos": [],
        },
        "chase": None, "chase_profile": None, "chase_cap": None,
        "roofline": roofline,
        "dormer": None, "dormer_profiles": [],
        "view": {
            "convention": "viewed from exterior — SYNTHETIC (blueprint model)",
            "datum": "positions SCHEMATIC — schedule-attributed, not placed",
            "orientation_note": (
                f"viewed from outside — drawing-left = "
                f"{_VIEW_DATUM[which]['drawing_left']} · drawing-right = "
                f"{_VIEW_DATUM[which]['drawing_right']} (VIEW-ORIENTATION PIN)"),
            "grade_note": None,
            "mirrored_segments": False,
        },
        "deviation": None,
        "collisions": [],
        "openings": openings,
        "opening_counts": {"windows": len(windows), "doors": len(doors),
                           "patio_doors": len(patio_doors), "vents": 0,
                           "garage_doors": len(garage_doors)},
        "schedule_note": schedule_note,
        "geometry_basis": {
            "walls": (f"blueprint run {run_short} — printed dims, "
                      "evidence-or-null (unquoted values tagged)"),
            "openings": (f"openings: blueprint schedule, run {run_short} "
                         "(count column governs) — positions schematic"),
        },
        "contractor_gables": [],
        "contractor_gable_bands": [],
        "contractor_dormers": [],
        "run": {"run_id": run.get("run_id"),
                "model_name": run.get("model_name") or "",
                "completed_at": str(run.get("completed_at"))[:10]
                if run.get("completed_at") else ""},
    }


@router.get("/estimates/{est_id}/blueprint-elevation/{which}")
async def blueprint_elevation(est_id: str, which: str,
                              user: dict = Depends(get_current_user)):
    if which not in _SHEET_CODES:
        raise HTTPException(status_code=404, detail="Unknown elevation")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "id": 1, "estimate_number": 1, "customer_name": 1,
         "address": 1})
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    run = await db.ai_blueprint_runs.find_one(
        {"estimate_id": est_id, "status": "done"},
        {"_id": 0}, sort=[("created_at", -1)])
    if not run:
        raise HTTPException(
            status_code=404,
            detail="No completed blueprint run for this estimate")
    return build_blueprint_sheet(est, run, which)
