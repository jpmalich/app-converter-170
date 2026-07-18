"""Elevation Sheet data binder — Phase 1: the Letrick FRONT sheet (EL-1).

READ-ONLY ROUTE (pinned): performs ZERO writes — a new output route on
existing data. September protection: demo surfaces are imported as
CONSTANTS only (sealed key module, LETRICK_TAPE_WALLS), never modified.

Data-binding rules (Howard's build directive 2026-07-18):
  • geometry-source rule governs — the tape-validated sealed key is the
    default wall basis where it exists; extraction-run fallback labeled.
  • openings come from the run's schedule with their AI-READ tags and
    ratify states; every value traces to its named source — NO hand-typed
    constants (the mock's numbers were hand-built; these are bound).
"""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user

router = APIRouter()

_FRAC = {0.0: "", 0.25: "¼", 0.5: "½", 0.75: "¾"}

# Tag taxonomy (spec §3): AI field-source → chip.
_AI_TAGS = {
    "direct_ref": "AI-READ ✓",
    "direct_consensus": "AI-READ ✓",
    "direct_single_reading": "AI-READ ✓",
    "direct_disagreement": "AI-READ ⚠",
    "cross_plane": "AI-READ ⚠",
    "below_typical_range": "AI-READ ⚠",
    "estimated_no_direct_view": "ESTIMATED",
    "defaulted": "ESTIMATED",
}


def fmt_ftin(ft: float) -> str:
    """Architectural format X'-Y[¼½¾]\" — nearest quarter inch."""
    sign = "-" if ft < 0 else ""
    total_q = round(abs(ft) * 12 * 4)
    feet, rem = divmod(total_q, 12 * 4)
    inches, q = divmod(rem, 4)
    return f"{sign}{feet}'-{inches}{_FRAC[q / 4.0]}\""


def fmt_inches(inches: float) -> str:
    sign = "-" if inches < 0 else ""
    total_q = round(abs(inches) * 4)
    whole, q = divmod(total_q, 4)
    return f"{sign}{whole}{_FRAC[q / 4.0]}\""


def _sealed_tape_basis(est: dict, wall_label: str) -> dict | None:
    """Sealed hand-takeoff key binding (Letrick). Values BIND from the key
    artifact + the Class-1-corrected structured tape walls — never retyped.
    Sides carry NO taped width (key eaves formula covers front/back only):
    width falls back to the extraction run, labeled."""
    if est.get("estimate_number") != "EST-373526":
        return None
    from letrick_hand_takeoff_key import LETRICK_HAND_TAKEOFF_KEY as KEY
    from routes.demo import LETRICK_TAPE_WALLS  # constant import only
    tw = LETRICK_TAPE_WALLS.get(wall_label)
    if not tw:
        return None
    exposure_in = float(KEY["inputs"]["exposure_in"])   # TAPED
    segments = []
    for seg in tw["segments"]:
        courses = int(seg["courses"])
        height_ft = round(courses * exposure_in / 12.0, 3)
        segments.append({
            "courses": courses,
            "height_ft": height_ft,
            "height_label": fmt_ftin(height_ft),
            "height_tag": "TAPED-DERIVED",
            "height_formula": f"{courses} × {exposure_in:g}\" ÷ 12 = {height_ft:g}'",
        })
    width_ft = None
    if wall_label in ("front", "back"):
        width_ft = float(KEY["inputs"]["eaves_lf"]) / 2.0  # eaves 2×54; 54 TAPED
    # soffit overhang from the key's own soffit line (e.g. '12" overhang')
    overhang_in = 12.0
    for ln in KEY.get("lines", []):
        m = re.search(r'(\d+)"\s*overhang', str(ln.get("derivation", "")))
        if m:
            overhang_in = float(m.group(1))
            break
    return {
        "key_number": KEY["estimate_number"],
        "key_corrected": KEY.get("corrected"),
        "segments": segments,
        "exposure_in": exposure_in,
        "width_ft": width_ft,
        "width_label": fmt_ftin(width_ft) if width_ft is not None else None,
        "width_tag": "TAPED" if width_ft is not None else None,
        "width_source": (f"sealed key {KEY['estimate_number']} · {width_ft:g} print-confirmed"
                         if width_ft is not None else None),
        "profile_key_item": str((KEY.get("lines") or [{}])[0].get("item", "")),
        "overhang_in": overhang_in,
    }


def _removed_and_corrected(run, review_state):
    """Verb machinery (ruled 2026-07-15): lp_openings_review rows are
    run-scoped `open:{rid8}:{index}` over _ai_openings_schedule. Removed
    rows must not render; corrected types render as corrected."""
    sched = ((run.get("result") or {}).get("measurements") or {}).get("_ai_openings_schedule") or []
    rid = str(run.get("run_id") or "")[:8]
    removed, corrected = [], []
    for i, s in enumerate(sched):
        st = (review_state or {}).get(f"open:{rid}:{i}") or {}
        dims = re.findall(r"\d+", str(s.get("size_label") or ""))[:2]
        matcher = {
            "wall": str(s.get("elevation") or "").lower(),
            "type": s.get("type"), "style": s.get("style") or "",
            "dims": dims,
        }
        if st.get("status") == "user_removed":
            removed.append(matcher)
        elif st.get("corrected_type"):
            corrected.append({**matcher, "corrected_type": st["corrected_type"]})
    return removed, corrected


def _matches(o, m):
    if str(o.get("wall", "")).lower() != m["wall"]:
        return False
    if o.get("type") != m["type"] or (o.get("style") or "") != m["style"]:
        return False
    if not m["dims"]:
        return True
    # schedule rows carry the GROUP's representative size — raw members
    # vary by an inch or two (photo reads), so match within 2.5"
    try:
        dw = abs(float(o.get("width_in") or 0) - float(m["dims"][0]))
        dh = abs(float(o.get("height_in") or 0) - float(m["dims"][1]))
    except (ValueError, IndexError):
        return True
    return dw <= 2.5 and dh <= 2.5


def _bind_openings(raw, wall_label, removed, corrected):
    """Openings for this wall, position-ordered, tagged, door-anchored
    sills from photo bbox (doors sit at grade — spec §2). Removed
    openings don't render; corrected types render corrected."""
    ops = [o for o in (raw.get("openings") or [])
           if str(o.get("wall", "")).lower() == wall_label
           and not o.get("on_dormer")]
    ops = [o for o in ops if not any(_matches(o, m) for m in removed)]
    ops.sort(key=lambda o: (o.get("along_wall_ft") if o.get("along_wall_ft") is not None else 1e9))
    # door anchor: grade fraction + inches-per-bbox-fraction scale
    anchor = None
    for o in ops:
        if "door" in str(o.get("type", "")) and (o.get("bbox") or {}).get("h") and o.get("height_in"):
            bb = o["bbox"]
            anchor = {"grade_frac": bb["y"] + bb["h"],
                      "in_per_frac": float(o["height_in"]) / float(bb["h"])}
            break
    out, wn, dn = [], 0, 0
    for o in ops:
        eff_type = str(o.get("type", ""))
        for m in corrected:
            if _matches(o, m):
                eff_type = str(m["corrected_type"])
                break
        is_door = "door" in eff_type
        if is_door:
            dn += 1
            tag = f"D{dn}"
        elif "vent" in eff_type:
            tag = f"V{sum(1 for x in out if x['tag'].startswith('V')) + 1}"
        else:
            wn += 1
            tag = f"W{wn}"
        center = o.get("along_wall_ft")
        pos_tag = "AI-READ ✓" if center is not None else "ESTIMATED"
        if center is None and (o.get("bbox") or {}).get("x") is not None:
            center = None  # bbox X-fraction fallback handled client-side only when present
        sill_in, sill_tag = None, "ESTIMATED"
        if is_door:
            sill_in, sill_tag = 0.0, "AI-READ ✓"  # doors sit at grade (anchor by construction)
        elif anchor and (o.get("bbox") or {}).get("h") is not None:
            bottom_frac = o["bbox"]["y"] + o["bbox"]["h"]
            sill_in = round((anchor["grade_frac"] - bottom_frac) * anchor["in_per_frac"], 1)
        out.append({
            "tag": tag,
            "opening_id": o.get("opening_id"),
            "type": "Entry door" if is_door else "Window",
            "style": o.get("style") or "",
            "width_in": o.get("width_in"),
            "height_in": o.get("height_in"),
            "center_ft": center,
            "center_label": fmt_ftin(center) if center is not None else "—",
            "position_tag": pos_tag,
            "sill_in": sill_in,
            "sill_label": fmt_ftin(sill_in / 12.0) if sill_in is not None else "—",
            "sill_tag": sill_tag,
            "confirmed": True,   # verb machinery: no removal/ratify verbs on this estimate
            "collision": False,  # set below
        })
    # collision check (horizontal interval overlap on the same wall band)
    spans = []
    for o in out:
        if o["center_ft"] is None or not o["width_in"]:
            continue
        half = float(o["width_in"]) / 24.0
        spans.append((o, o["center_ft"] - half, o["center_ft"] + half))
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            a, b = spans[i], spans[j]
            if a[1] < b[2] and b[1] < a[2]:
                a[0]["collision"] = True
                b[0]["collision"] = True
    return out


_SHEET_CODES = {"front": "EL-1", "left": "EL-2", "back": "EL-3", "right": "EL-4"}


@router.get("/estimates/{est_id}/elevation-sheet/{which}")
async def elevation_sheet(est_id: str, which: str, user: dict = Depends(get_current_user)):
    if which not in _SHEET_CODES:
        raise HTTPException(status_code=404, detail="Unknown elevation")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "id": 1, "estimate_number": 1, "customer_name": 1, "address": 1,
         "lp_openings_review": 1})
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    run = await db.ai_measure_runs.find_one(
        {"estimate_id": est_id, "status": "done", "usage_probe": {"$ne": True}},
        {"_id": 0}, sort=[("created_at", -1)])
    if run is None:
        from run_archive import find_archived_run
        run = await find_archived_run({"estimate_id": est_id, "status": "done"})
    if not run:
        raise HTTPException(status_code=404, detail="No completed AI measure run for this estimate")
    raw = (run.get("result") or {}).get("raw_ai") or {}
    wall = next((w for w in (raw.get("walls") or [])
                 if str(w.get("label", "")).lower() == which), None)
    if not wall:
        raise HTTPException(status_code=404, detail=f"Run has no {which} wall")

    tape = _sealed_tape_basis(est, which)
    ai_width = wall.get("width_ft")
    ai_height = wall.get("height_ft")
    ai_width_tag = _AI_TAGS.get(str(wall.get("width_ft_source")), "ESTIMATED")
    segments = None
    if tape:
        segments = tape["segments"]
        # tallest segment drives the drawing frame; each keeps its basis line
        height_ft = max(s["height_ft"] for s in segments)
        if tape["width_ft"] is not None:
            width_ft = tape["width_ft"]
            width_tag, width_source = tape["width_tag"], tape["width_source"]
        else:
            # sides: width untaped — extraction-run fallback, LABELED
            width_ft = ai_width
            width_tag = ai_width_tag
            width_source = f"AI run {run['run_id'][:8]} ({wall.get('width_ft_source')}) — width untaped"
        first = segments[0]
        basis = {
            "width_tag": width_tag, "width_source": width_source,
            "height_tag": first["height_tag"], "height_formula": first["height_formula"],
            "exposure_in": tape["exposure_in"], "courses": first["courses"],
        }
        walls_basis_line = (f"sealed key {tape['key_number']} "
                            f"(tape, corrected {tape['key_corrected']}) — heights"
                            + ("" if tape["width_ft"] is not None
                               else f" · width AI run {run['run_id'][:8]}"))
    else:
        width_ft, height_ft = ai_width, ai_height
        basis = {
            "width_tag": ai_width_tag,
            "width_source": f"AI run ({wall.get('width_ft_source')})",
            "height_tag": _AI_TAGS.get(str(wall.get("height_ft_source")), "ESTIMATED"),
            "height_formula": f"AI run ({wall.get('height_ft_source')})",
            "exposure_in": None, "courses": None,
        }
        walls_basis_line = f"AI run {run['run_id'][:8]}… — walls"

    # Tape/AI deviation (spec §2, standing sheet element): render whenever
    # tape governs and the run disagrees on either axis.
    deviation = None
    if tape and ai_height is not None:
        seg_heights = [s["height_ft"] for s in segments]
        height_off = all(abs(ai_height - h) > 0.05 for h in seg_heights)
        width_off = (tape["width_ft"] is not None and ai_width is not None
                     and abs(ai_width - tape["width_ft"]) > 0.05)
        if height_off or width_off:
            counts = sorted({int(m) for r in (wall.get("_per_photo_readings") or [])
                             for m in re.findall(r"(\d+)\s+courses counted", str(r.get("notes", "")))})
            deviation = {
                "ai_width_ft": ai_width, "ai_width_label": fmt_ftin(ai_width) if ai_width is not None else "—",
                "ai_height_ft": ai_height, "ai_height_label": fmt_ftin(ai_height),
                "ai_counts": counts,
                "ai_basis": str(wall.get("height_ft_source") or wall.get("width_ft_source") or ""),
                "tape_heights_label": " / ".join(s["height_label"] for s in segments),
                "delta_width_label": (fmt_ftin(ai_width - tape["width_ft"]) if width_off else None),
                "delta_height_label": fmt_inches((ai_height - seg_heights[0]) * 12.0),
                "width_disputed": bool(width_off),
                "governs": "tape",
                "run_short": run["run_id"][:8],
            }

    # chimney chase (back wall) — AI accent read; footprint is UNTAPED, so
    # the sheet must annotate, never scale-render silently.
    chase = None
    for acc in (wall.get("accent_profiles") or []):
        loc = str(acc.get("location") or "")
        if "chase" in loc.lower():
            chase = {"note": loc,
                     "profile": acc.get("profile_callout") or acc.get("profile") or "",
                     "tag": "AI-READ ✓", "footprint": "untaped — NOT TO SCALE"}
            break

    removed_rows, corrected_rows = _removed_and_corrected(run, est.get("lp_openings_review"))
    openings = _bind_openings(raw, which, removed_rows, corrected_rows)
    windows = [o for o in openings if o["type"] == "Window"]
    doors = [o for o in openings if "door" in o["type"].lower()]

    completed = run.get("completed_at")
    completed_str = str(completed)[:10] if completed else ""
    model_name = run.get("model_name") or (run.get("result") or {}).get("model") or ""
    area = round(width_ft * height_ft, 1) if (width_ft and height_ft) else None

    return {
        "sheet": which,
        "sheet_code": _SHEET_CODES[which],
        "customer_name": est.get("customer_name"),
        "address": est.get("address"),
        "estimate_number": est.get("estimate_number"),
        "generated_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "wall": {
            "width_ft": width_ft, "width_label": fmt_ftin(width_ft) if width_ft is not None else "—",
            "height_ft": height_ft, "height_label": fmt_ftin(height_ft),
            **basis,
            "segments": segments,
            "step_note": ("stepped wall — step location NOT TAPED (indicative only)"
                          if segments and len(segments) > 1 else None),
            "area_sqft": area,
            "gable_triangle_ft": wall.get("gable_triangle_height_ft") or 0,
            "gable_tag": _AI_TAGS.get(str(wall.get("height_ft_source")), "ESTIMATED"),
            "siding_pct": wall.get("siding_pct_this_wall"),
            "profile_callout": wall.get("wall_body_profile_callout") or "",
            "profile_key_item": (tape or {}).get("profile_key_item", ""),
            "stories": raw.get("story_count"),
            "overhang_in": (tape or {}).get("overhang_in", 12.0),
            "ai_confidence": wall.get("confidence"),
            "ai_reasoning": wall.get("confidence_reasoning") or "",
            "source_photos": wall.get("_source_photo_indices") or [],
        },
        "chase": chase,
        "deviation": deviation,
        "openings": openings,
        "opening_counts": {"windows": len(windows), "doors": len(doors),
                           "other": len(openings) - len(windows) - len(doors)},
        "schedule_note": "Sizes + positions: AI run (along_wall_ft). Sills: photo bbox, door-anchored (doors at grade)."
                         + ("" if doors else " No door on this wall — sills not derivable (—)."),
        "geometry_basis": {
            "walls": walls_basis_line,
            "openings": f"openings: AI run {run['run_id'][:8]}…{run['run_id'][-2:]} ({model_name}, {completed_str})",
        },
        "run": {"run_id": run["run_id"], "model_name": model_name, "completed_at": completed_str},
    }
