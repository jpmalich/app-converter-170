"""MATERIAL ZONE LAYER — MUV SESSION 2 (Howard ruled 2026-08-13
pro-quotes replies 5, 6, 7).

The user draws polygons over the ORIGINAL elevation PDF pages; each
polygon carries a material class + face_id + page-normalised vertices
+ an EVIDENCE-GROUNDED scale for the VIEW it sits in. This module owns
the persistence + area math + guard for those polygons.

Contract (verbatim from Howard — the SEVEN-point walk-bar for MUV):
  1. Open a real elevation page.
  2. Draw or drag a polygon over a wall.
  3. The square footage changes.
  4. The material line changes with it.
  5. It is marked as MY entry, not the app's.
  6. It is still there after a rebuild.
  7. When I DELETE it, the app's own number comes back.

RULED (pro-quotes replies 6/7) — three laws this module enforces:

  A. REPLACE, NEVER ADD + the superseded derived value STAYS VISIBLE
     and MARKED SUPERSEDED. A human zone SUPERSEDES the derived value
     for its (material_class, face_id); it does not stack on it. The
     app's original number is kept on `superseded_qty` +
     `overlay_superseded=True` so the reader sees what the app thought
     and what the human replaced it with, side by side.

  B. A HUMAN VALUE IS A FUNCTION OF ITS POLYGONS. Delete one of several
     → the sum RECOMPUTES from what remains. Delete the LAST polygon on
     a (face_id, material_class) → the override RETIRES, the derived
     value RETURNS, and the retirement is LEDGERED. There is NEVER a
     human value with zero polygons behind it.

  C. THE SCALE IS READ FROM THE SHEET, NEVER DEFAULTED. The hardcoded
     3/16" = 1'-0" constant is GONE (purity rider). Every conversion
     needs an explicit, evidence-grounded scale for the VIEW the polygon
     sits in (an OCR read of the printed dimension, or a human
     calibration line traced over one). Where the scale cannot be read,
     we REFUSE: the polygon holds its pixel geometry, `sqft` is None,
     the line is flagged `overlay_scale_unreadable`, and the derived
     value is untouched — a wrong-scale area LOOKS RIGHT and is invisible.

DURABILITY NOTE (why the DERIVED BASELINE lives on the polygon, not the
line): the estimate editor's load/save merge rebuilds line objects and
STRIPS unknown fields (the sealed "silent-strip class"). If the app's
original number lived only on the line, an autosave would erase it and
the retirement in Law B would have nothing to restore. So each polygon
carries `derived_baseline_qty` — captured ONCE from the pristine line
when the first polygon of a (face_id, material_class) is drawn — and
the pdf_overlay_polygons collection is never touched by the editor.

PROTECTED-ESTIMATE HUMAN-ENTRY (Howard ruled 2026-08-13 pro-quotes
reply 5): a drawn / adjusted / deleted zone is Howard's hand on the
drawing, so it RIDES ABOVE the untouchable freeze on EST-886440 and
lands in `protected_estimate_ledger` via `ledger_human_write`.

SEAM (registered in `seam_accounting.SEAM_REGISTRY`):
  pdf_overlay_polygon_write — every write/delete/retirement is a
  boundary crossing (drawing → structured takeoff → protected ledger).
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import hypot
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from untouchable import is_untouchable, ledger_human_write

router = APIRouter(tags=["pdf-overlay"])


# ---------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------

MATERIAL_CLASSES = {"siding", "soffit", "accent", "trim"}

# KNOWN LIMIT (Howard ruled 2026-08-13 pro-quotes reply 7, named on the
# editor surface): these cardinals have NO face for the front-facing
# ENTRY GABLE (it is not a dormer), and "front"/"back" COLLAPSE stepped
# / multi-height segments (main body + garage wing) into ONE number.
# Segment-level (`front:main`) and gable-level (`gable:entry`) faces are
# a scoped-but-unbuilt increment; the editor names the limit and the
# takeoff flags `overlay_merged` when >1 polygon feeds one number.
_FIXED_FACES = {"front", "back", "left", "right"}

# Takeoff line units a polygon area can bind to (Law-C conversion below).
_AREA_UNITS = {"sq", "square", "squares", "sf", "sqft", "ft2", "ft²"}


def _face_ok(face_id: str) -> bool:
    if not face_id:
        return False
    if face_id in _FIXED_FACES:
        return True
    return face_id.startswith("dormer:") and len(face_id) > len("dormer:")


class ScaleRefIn(BaseModel):
    """Evidence-grounded calibration for the VIEW a polygon sits in: two
    page-normalised endpoints tracing a printed dimension + its real-world
    length in feet + the source of the reading. NO default — absence
    means the scale could not be read and the area is REFUSED (Law C)."""
    p1: list[float]
    p2: list[float]
    real_ft: float
    source: str = "calibration"     # "ocr" | "calibration"
    from_quote: str = ""


class PolygonWriteIn(BaseModel):
    id: Optional[str] = None
    page: int
    face_id: str
    material_class: str
    vertices_pct: list[list[float]] = Field(
        ..., description="[[x_pct, y_pct], ...] page-normalised [0,1]",
    )
    scale_ref: Optional[ScaleRefIn] = None
    page_w_px: Optional[float] = None
    page_h_px: Optional[float] = None


# ---------------------------------------------------------------------
# MATH — polygon area (shoelace) in ft² from an EVIDENCE-GROUNDED scale.
# No baked constant. Returns None when the scale is absent/degenerate —
# a REFUSAL, never a defaulted number (Law C).
# ---------------------------------------------------------------------

def polygon_sqft_from_scale(
    vertices_pct: list[list[float]],
    scale_ref: Optional[dict],
    page_w_px: Optional[float],
    page_h_px: Optional[float],
) -> Optional[float]:
    if not vertices_pct or len(vertices_pct) < 3:
        return None
    if not scale_ref or not page_w_px or not page_h_px:
        return None
    p1 = scale_ref.get("p1")
    p2 = scale_ref.get("p2")
    real_ft = scale_ref.get("real_ft")
    if not (isinstance(p1, (list, tuple)) and len(p1) == 2
            and isinstance(p2, (list, tuple)) and len(p2) == 2):
        return None
    try:
        real_ft = float(real_ft)
    except (TypeError, ValueError):
        return None
    if real_ft <= 0:
        return None
    calib_px = hypot((float(p2[0]) - float(p1[0])) * page_w_px,
                     (float(p2[1]) - float(p1[1])) * page_h_px)
    if calib_px <= 0:
        return None
    ft_per_px = real_ft / calib_px
    n = len(vertices_pct)
    area_px = 0.0
    for i in range(n):
        x1 = float(vertices_pct[i][0]) * page_w_px
        y1 = float(vertices_pct[i][1]) * page_h_px
        x2 = float(vertices_pct[(i + 1) % n][0]) * page_w_px
        y2 = float(vertices_pct[(i + 1) % n][1]) * page_h_px
        area_px += x1 * y2 - x2 * y1
    area_px = abs(area_px) / 2.0
    return round(area_px * ft_per_px * ft_per_px, 2)


# ---------------------------------------------------------------------
# LINE APPLICATION — polygon → takeoff row (REPLACE / SUPERSEDE / RETIRE)
# ---------------------------------------------------------------------

def _line_matches(line: dict, material_class: str) -> bool:
    """Match a takeoff line to a polygon's material_class.

    REALITY (discovered on EST-886440, 2026-08-13): the takeoff has NO
    per-face lines — siding is ONE aggregate body line in SQUARES, not
    ft² per wall. So a polygon binds to the AGGREGATE line for its class
    (area-unit, on the vinyl tab, excluding the accessories section);
    `face_id` is carried as metadata for the future per-face increment.
    This is exactly the KNOWN LIMIT Howard named (front/back collapse
    every segment into one number) — the aggregate line flags
    `overlay_merged` + the zone count so the surface never hides it."""
    tab = (line.get("tab") or "vinyl")
    if tab != "vinyl":
        return False
    section = (line.get("section") or "").lower()
    unit = (line.get("unit") or "").strip().lower()
    if unit not in _AREA_UNITS:
        return False
    if material_class == "siding":
        return "siding" in section and "accessor" not in section
    if material_class == "soffit":
        return "soffit" in section
    if material_class == "accent":
        return bool(line.get("is_accent")) or "accent" in section
    if material_class == "trim":
        return "trim" in section and "accessor" not in section
    return False


def _sqft_to_line_qty(total_sqft: float, unit: str) -> Optional[float]:
    """Convert a polygon area (always ft²) into the takeoff line's unit.
    SQUARES ÷100; area units pass through; anything else can't hold an
    area → None (the caller refuses the bind)."""
    u = (unit or "").strip().lower()
    if u in {"sq", "square", "squares"}:
        return round(total_sqft / 100.0, 2)
    if u in {"sf", "sqft", "ft2", "ft²"}:
        return round(total_sqft, 2)
    return None


def _overlay_note(line: dict, total: float) -> str:
    base = (line.get("note") or "").split(" · PDF-OVERLAY")[0]
    return (base + f" · PDF-OVERLAY zone ({total:.1f} ft²)").strip(" ·")


def _retire_override(line: dict) -> bool:
    """Retire an overlay override IN PLACE: restore the superseded derived
    value and strip every overlay marker. Returns True when a retirement
    actually happened. A retirement that does not restore the derived
    value is a bug the suite refuses to ship (Law B)."""
    if not line.get("overlay_superseded"):
        line.pop("overlay_scale_unreadable", None)
        line.pop("overlay_polygon_count", None)
        line.pop("overlay_merged", None)
        line.pop("overlay_sqft", None)
        return False
    if "superseded_qty" in line:
        line["qty"] = line.pop("superseded_qty")
    line["raw_qty"] = line.pop("superseded_raw_qty", line.get("qty"))
    line["qty_src"] = line.pop("superseded_qty_src", "derived")
    line.pop("overlay_superseded", None)
    line.pop("overlay_polygon_count", None)
    line.pop("overlay_merged", None)
    line.pop("overlay_sqft", None)
    line.pop("overlay_scale_unreadable", None)
    if line.get("note"):
        cleaned = line["note"].split("PDF-OVERLAY")[0].strip(" ·")
        if cleaned:
            line["note"] = cleaned
        else:
            line.pop("note", None)
    return True


def _group_baseline(polys: list[dict], line: dict) -> float:
    """The pristine derived value (in the LINE's unit) for a material
    class. Prefer the baseline captured on the polygons (durable — the
    editor never touches that collection); fall back to the line's
    superseded snapshot, then the line's current qty."""
    for p in polys:
        b = p.get("derived_baseline_qty")
        if b is not None:
            return b
    if line.get("superseded_qty") is not None:
        return line["superseded_qty"]
    return line.get("qty")


def apply_overlay_to_takeoff(
    lines: list[dict],
    polygons: list[dict],
) -> list[dict]:
    """Return a NEW list of takeoff lines with the overlay applied per
    Howard's three laws. Polygons bind by MATERIAL CLASS to the aggregate
    takeoff line (the takeoff has no per-face lines — see `_line_matches`);
    each polygon carries a pre-computed `sqft` (None ⇒ scale refused) and a
    `derived_baseline_qty` (the app's original number in the line's unit)."""
    by_class: dict[str, list[dict]] = {}
    for p in polygons or []:
        by_class.setdefault(p.get("material_class") or "", []).append(p)

    out: list[dict] = []
    for line in (lines or []):
        new = dict(line)
        matched = next(
            (c for c in by_class if _line_matches(new, c)),
            None,
        )
        if matched is None:
            _retire_override(new)
            out.append(new)
            continue

        polys = by_class[matched]
        baseline = _group_baseline(polys, new)
        convertible = [p for p in polys if p.get("sqft") is not None]
        if not convertible:
            _retire_override(new)
            if baseline is not None:
                new["qty"] = baseline
                new["raw_qty"] = baseline
                new["qty_src"] = "derived"
            new["overlay_scale_unreadable"] = True
            new["overlay_polygon_count"] = len(polys)
            out.append(new)
            continue

        total_sqft = round(sum(float(p["sqft"]) for p in convertible), 2)
        line_qty = _sqft_to_line_qty(total_sqft, new.get("unit") or "")
        if line_qty is None:
            # An area cannot bind to this line's unit (e.g. LF) — refuse.
            _retire_override(new)
            new["overlay_scale_unreadable"] = True
            new["overlay_polygon_count"] = len(convertible)
            out.append(new)
            continue

        new["superseded_qty"] = baseline
        new["superseded_raw_qty"] = baseline
        new["superseded_qty_src"] = "derived"
        new["overlay_superseded"] = True
        new["qty"] = line_qty
        new["raw_qty"] = line_qty
        new["qty_src"] = "human"
        new["overlay_sqft"] = total_sqft
        new["overlay_polygon_count"] = len(convertible)
        new["overlay_merged"] = len(convertible) > 1
        new.pop("overlay_scale_unreadable", None)
        new["note"] = _overlay_note(line, total_sqft)
        out.append(new)
    return out


# ---------------------------------------------------------------------
# ROUTES — GET / PUT / DELETE  /api/estimates/{eid}/pdf-overlay
# ---------------------------------------------------------------------

async def _est_or_404(est_id: str, user: dict) -> dict:
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0},
    )
    if not est:
        raise HTTPException(status_code=404, detail="Not found")
    return est


def _validate_polygon(p: PolygonWriteIn) -> None:
    if p.material_class not in MATERIAL_CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"material_class must be one of {sorted(MATERIAL_CLASSES)}",
        )
    if not _face_ok(p.face_id):
        raise HTTPException(
            status_code=400,
            detail=(f"face_id must be one of {sorted(_FIXED_FACES)} "
                    "or 'dormer:<label>'"),
        )
    if not p.vertices_pct or len(p.vertices_pct) < 3:
        raise HTTPException(
            status_code=400,
            detail="a polygon needs at least 3 vertices",
        )
    for v in p.vertices_pct:
        if (not isinstance(v, list) or len(v) != 2
                or not (0.0 <= float(v[0]) <= 1.0)
                or not (0.0 <= float(v[1]) <= 1.0)):
            raise HTTPException(
                status_code=400,
                detail="vertices must be [[x_pct,y_pct],...] in [0,1]",
            )
    if not isinstance(p.page, int) or p.page < 1:
        raise HTTPException(
            status_code=400, detail="page must be a 1-based int",
        )


@router.get("/estimates/{est_id}/pdf-overlay")
async def get_pdf_overlay(
    est_id: str, user: dict = Depends(get_current_user),
):
    """List all polygons on this estimate (open read)."""
    await _est_or_404(est_id, user)
    polys: list[dict] = []
    async for row in db.pdf_overlay_polygons.find(
        {"estimate_id": est_id}, {"_id": 0}
    ).sort("created_at", 1):
        polys.append(row)
    return {"polygons": polys, "total": len(polys)}


async def _current_baseline_for_class(
    est: dict, est_id: str, material_class: str, exclude_id: str,
) -> Optional[float]:
    """The pristine derived value (line unit) for a material class. If any
    OTHER polygon of the class already captured it, reuse that (so the
    baseline never drifts to the human override). Otherwise read it from
    the current matching aggregate line — pristine, because this is the
    first polygon of the class."""
    async for row in db.pdf_overlay_polygons.find(
        {"estimate_id": est_id, "material_class": material_class,
         "id": {"$ne": exclude_id}},
        {"_id": 0, "derived_baseline_qty": 1},
    ):
        if row.get("derived_baseline_qty") is not None:
            return row["derived_baseline_qty"]
    for line in est.get("lines") or []:
        if _line_matches(line, material_class):
            return line.get("qty")
    return None


@router.put("/estimates/{est_id}/pdf-overlay")
async def upsert_pdf_overlay(
    est_id: str,
    payload: PolygonWriteIn,
    user: dict = Depends(get_current_user),
):
    """Upsert one polygon. Computes ft² from the evidence-grounded scale
    (or REFUSES). Recomputes the affected line: REPLACE + SUPERSEDE.

    HUMAN-ENTRY on protected estimates (ruled 2026-08-13 reply 5): NO
    derived-write guard — a drawn zone rides above the freeze on
    EST-886440 and lands in `protected_estimate_ledger`."""
    _validate_polygon(payload)
    est = await _est_or_404(est_id, user)
    pid = payload.id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    scale_ref = payload.scale_ref.dict() if payload.scale_ref else None
    sqft = polygon_sqft_from_scale(
        [[float(x), float(y)] for x, y in payload.vertices_pct],
        scale_ref, payload.page_w_px, payload.page_h_px,
    )
    baseline = await _current_baseline_for_class(
        est, est_id, payload.material_class, pid)
    doc = {
        "id": pid,
        "estimate_id": est_id,
        "page": int(payload.page),
        "face_id": payload.face_id,
        "material_class": payload.material_class,
        "vertices_pct": [[float(x), float(y)]
                         for x, y in payload.vertices_pct],
        "scale_ref": scale_ref,
        "page_w_px": payload.page_w_px,
        "page_h_px": payload.page_h_px,
        "sqft": sqft,                       # None ⇒ scale refused
        "derived_baseline_qty": baseline,   # the app's original number
        "qty_src": "human",
        "author_id": user.get("id") or "",
        "author_email": user.get("email") or "",
        "updated_at": now,
    }
    existing = await db.pdf_overlay_polygons.find_one({"id": pid})
    if existing:
        doc["created_at"] = existing.get("created_at") or now
        # Preserve the group's original baseline across edits of an
        # existing polygon (never re-capture from a now-overridden line).
        if existing.get("derived_baseline_qty") is not None:
            doc["derived_baseline_qty"] = existing["derived_baseline_qty"]
        await db.pdf_overlay_polygons.replace_one({"id": pid}, doc)
    else:
        doc["created_at"] = now
        await db.pdf_overlay_polygons.insert_one(doc)

    await _recompute_and_store(est_id, user, est.get("lines") or [])

    if await is_untouchable(est_id):
        await ledger_human_write(
            est_id, "pdf_overlay_polygon",
            actor_email=user.get("email", ""),
            meta={"polygon_id": pid, "page": doc["page"],
                  "face_id": doc["face_id"],
                  "material_class": doc["material_class"],
                  "sqft": sqft, "scale_read": sqft is not None},
        )
    safe = {k: v for k, v in doc.items() if k != "_id"}
    safe["created_at"] = str(safe.get("created_at") or "")
    safe["updated_at"] = str(safe.get("updated_at") or "")
    return {"ok": True, "polygon": safe, "scale_read": sqft is not None}


@router.delete("/estimates/{est_id}/pdf-overlay/{polygon_id}")
async def delete_pdf_overlay(
    est_id: str, polygon_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete one polygon and recompute (Law B). Deleting the LAST
    polygon of a material_class RETIRES the override and RESTORES the
    derived value — the retirement is LEDGERED. (Binding is per-class,
    not per-face, because the takeoff has no per-face lines — the named
    known limit; see `_line_matches`.)"""
    est = await _est_or_404(est_id, user)
    victim = await db.pdf_overlay_polygons.find_one(
        {"id": polygon_id, "estimate_id": est_id}, {"_id": 0})
    if not victim:
        raise HTTPException(status_code=404, detail="Polygon not found")
    await db.pdf_overlay_polygons.delete_one(
        {"id": polygon_id, "estimate_id": est_id})

    remaining = await db.pdf_overlay_polygons.count_documents(
        {"estimate_id": est_id,
         "material_class": victim.get("material_class")})
    retired = remaining == 0

    # Law B: when the last polygon of a class is gone, apply() no longer
    # sees that class and leaves the (human-overridden) line as-is — so we
    # RESTORE it to the polygon-captured baseline BEFORE recompute. This
    # works even if the editor stripped the line's overlay markers.
    lines = list(est.get("lines") or [])
    if retired:
        baseline = victim.get("derived_baseline_qty")
        restored = []
        for line in lines:
            nl = dict(line)
            if _line_matches(nl, victim.get("material_class")):
                if baseline is not None:
                    nl["qty"] = baseline
                    nl["raw_qty"] = baseline
                nl["qty_src"] = "derived"
                _retire_override(nl)
            restored.append(nl)
        lines = restored

    await _recompute_and_store(est_id, user, lines)

    if await is_untouchable(est_id):
        meta = {"deleted": polygon_id,
                "face_id": victim.get("face_id"),
                "material_class": victim.get("material_class")}
        if retired:
            meta["retired_override"] = True
            meta["restored_derived"] = victim.get("derived_baseline_qty")
        await ledger_human_write(
            est_id, "pdf_overlay_polygon",
            actor_email=user.get("email", ""), meta=meta)
    return {"ok": True, "deleted": polygon_id, "retired_override": retired}


async def _recompute_and_store(
    est_id: str, user: dict, lines: list[dict],
) -> None:
    """Recompute the takeoff lines from ALL polygons on the estimate and
    persist. Single source of truth for PUT and DELETE so the
    REPLACE/SUPERSEDE/RETIRE laws never diverge between them."""
    all_polys: list[dict] = []
    async for row in db.pdf_overlay_polygons.find(
        {"estimate_id": est_id}, {"_id": 0}
    ):
        all_polys.append(row)
    new_lines = apply_overlay_to_takeoff(lines, all_polys)
    await db.estimates.update_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"$set": {"lines": new_lines,
                  "updated_at": datetime.now(timezone.utc)}},
    )
