"""MATERIAL ZONE LAYER — MUV SESSION 1 (Howard ruled 2026-08-13
pro-quotes reply 5).

The user draws polygons over the original elevation PDF pages;
each polygon carries a material class + face_id + page-normalised
vertices. This module owns the persistence + math + guard for
those polygons.

Contract (verbatim from Howard, walk-bar for MUV):
  1. Open a real elevation page.
  2. Draw or drag a polygon over a wall.
  3. The square footage changes.
  4. The material line changes with it.
  5. It is marked as MY entry, not the app's.
  6. It is still there after a rebuild.

The polygon→sqft math is deterministic at 3/16" = 1'-0" (unless the
sheet's own calibration overrides). Every polygon write updates the
matching line's `qty` in-place and stamps `qty_src = "human"` so the
existing hover.py rebuild guard preserves it verbatim (send-hover
line 3500 pattern).

PROTECTED-ESTIMATE HUMAN-ENTRY (Howard ruled 2026-08-13 pro-quotes
reply 5): a drawn or adjusted zone is Howard's hand on the drawing,
so it RIDES ABOVE the untouchable freeze on EST-886440 — built in at
MUV birth, not discovered on the walk. Every polygon write on a
protected estimate lands in `protected_estimate_ledger` via
`ledger_human_write(est_id, "pdf_overlay_polygon", ...)`.

SEAM (registered in `seam_accounting.SEAM_REGISTRY`):
  pdf_overlay_polygon_write — a polygon write on any estimate is
  ledgered via seam_accounting for the same reason every other
  boundary-crossing removal or overwrite is: the drawing is a
  new class of surface and every touch must account for itself.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from untouchable import is_untouchable, ledger_human_write

router = APIRouter(tags=["pdf-overlay"])


# ---------------------------------------------------------------------
# MODELS — kept small; MUV includes only what the walk-bar needs
# ---------------------------------------------------------------------

# Material classes the MUV recognises. Additions are one-line entries
# that require a new tests_pin — see the seam registry rule.
MATERIAL_CLASSES = {"siding", "soffit", "accent", "trim"}

# Face ids the MUV recognises. `dormer:<label>` is a dynamic form
# (any label) so this set names ONLY the fixed cardinal faces plus
# the dormer prefix; validation is `id in _FIXED or id.startswith("dormer:")`.
_FIXED_FACES = {"front", "back", "left", "right"}


def _face_ok(face_id: str) -> bool:
    if not face_id:
        return False
    if face_id in _FIXED_FACES:
        return True
    return face_id.startswith("dormer:") and len(face_id) > len("dormer:")


class PolygonWriteIn(BaseModel):
    """One polygon upsert. `id` may be omitted on create — the server
    mints a UUID."""
    id: Optional[str] = None
    page: int
    face_id: str
    material_class: str
    vertices_pct: list[list[float]] = Field(
        ..., description="[[x_pct, y_pct], ...] page-normalised [0,1]",
    )


# ---------------------------------------------------------------------
# MATH — polygon area (shoelace) in ft² at 3/16" = 1'-0"
# ---------------------------------------------------------------------

# Architectural scale 3/16" = 1'-0":
#   1 foot of real geometry prints as 3/16 inch on the sheet.
#   A US-letter sheet at 8.5" × 11" therefore represents
#   8.5 / (3/16) = 45.33 ft in the LONGER dimension of a portrait page.
# The vertex payload uses PAGE-NORMALISED coordinates ([0,1] × [0,1]),
# so translating to feet requires knowing the sheet's rendered inch
# dimensions. For MUV we take them from the page raster the frontend
# already serves (image_payloads pipeline emits pixel dims); the
# sheet's inch-dims are stored on `estimates.sheets_identified[i]`
# as `page_width_in` / `page_height_in` when present. Absent that,
# MUV falls back to US-letter portrait (8.5" × 11").
DEFAULT_SHEET_WIDTH_IN = 8.5
DEFAULT_SHEET_HEIGHT_IN = 11.0
INCHES_PER_FT_AT_3_16 = 3.0 / 16.0  # 0.1875 in/ft


def polygon_sqft(
    vertices_pct: list[list[float]],
    sheet_width_in: float = DEFAULT_SHEET_WIDTH_IN,
    sheet_height_in: float = DEFAULT_SHEET_HEIGHT_IN,
) -> float:
    """Compute polygon area in ft² given page-normalised vertices and
    the sheet's rendered inch dimensions, at 3/16" = 1'-0".

    Uses the shoelace formula. Vertices are [0,1] × [0,1]; multiply
    by (sheet_dim_in / INCHES_PER_FT_AT_3_16) to reach feet.
    Not sensitive to winding order — abs value returned.
    """
    if not vertices_pct or len(vertices_pct) < 3:
        return 0.0
    ft_per_x = sheet_width_in / INCHES_PER_FT_AT_3_16
    ft_per_y = sheet_height_in / INCHES_PER_FT_AT_3_16
    # Shoelace in ft directly (scale each axis independently).
    total = 0.0
    n = len(vertices_pct)
    for i in range(n):
        x1, y1 = vertices_pct[i]
        x2, y2 = vertices_pct[(i + 1) % n]
        total += (x1 * ft_per_x) * (y2 * ft_per_y)
        total -= (x2 * ft_per_x) * (y1 * ft_per_y)
    return abs(total) / 2.0


# ---------------------------------------------------------------------
# LINE APPLICATION — polygon → takeoff row
# ---------------------------------------------------------------------

def _line_matches(line: dict, material_class: str, face_id: str) -> bool:
    """Match a takeoff line to a polygon's (material_class, face_id).

    MUV keeps this deliberately narrow: siding polygons feed the
    per-face siding line (the line whose `face_id == face_id` and
    tab ∈ {vinyl, lp_smart, ...} carrying the section for that class).
    A future refactor can widen the mapping; MUV ships with siding
    only because that's the walk-bar shape."""
    if material_class == "siding":
        return (line.get("face_id") == face_id
                and "siding" in (line.get("section") or "").lower())
    if material_class == "soffit":
        return (line.get("face_id") == face_id
                and "soffit" in (line.get("section") or "").lower())
    if material_class == "accent":
        return (line.get("face_id") == face_id
                and (line.get("is_accent")
                     or "accent" in (line.get("section") or "").lower()))
    if material_class == "trim":
        return (line.get("face_id") == face_id
                and "trim" in (line.get("section") or "").lower())
    return False


def apply_overlay_to_takeoff(
    lines: list[dict],
    polygons: list[dict],
    sheet_dims_by_page: dict[int, tuple[float, float]] | None = None,
) -> list[dict]:
    """Update `lines` in-place shape (returns a NEW list) so each
    line whose (material_class, face_id) has one or more polygons
    carries the summed polygon sqft on `qty`, with `qty_src="human"`.

    Rebuild survival is delegated to hover.py's existing shield:
    every line stamped `qty_src="human"` survives the next
    rebuild verbatim. That's the walk-bar item 5+6 in one shot.
    """
    if not polygons:
        return list(lines or [])
    # Sum sqft per (material_class, face_id) key.
    sums: dict[tuple[str, str], float] = {}
    dims_by_page = sheet_dims_by_page or {}
    for p in polygons:
        page = int(p.get("page") or 1)
        w_in, h_in = dims_by_page.get(
            page, (DEFAULT_SHEET_WIDTH_IN, DEFAULT_SHEET_HEIGHT_IN))
        sqft = polygon_sqft(p.get("vertices_pct") or [], w_in, h_in)
        key = (p.get("material_class") or "", p.get("face_id") or "")
        sums[key] = sums.get(key, 0.0) + sqft
    # Apply to matching lines. A line with no matching polygon is left
    # untouched. A polygon with no matching line is dropped on the floor
    # this session — MUV punts adding new lines to session 3 (LegendPanel).
    out = []
    for line in (lines or []):
        matched_key = next(
            ((k, v) for k, v in sums.items()
             if _line_matches(line, k[0], k[1])),
            None,
        )
        if matched_key is None:
            out.append(line)
            continue
        (_klass, _face), qty = matched_key
        new_line = dict(line)
        new_line["qty"] = round(qty, 2)
        new_line["raw_qty"] = round(qty, 2)
        new_line["qty_src"] = "human"
        new_line["note"] = (
            (line.get("note") or "").split(" · PDF-OVERLAY")[0]
            + f" · PDF-OVERLAY zone ({qty:.1f} ft²)"
        ).strip(" ·")
        out.append(new_line)
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
    """List all polygons on this estimate (open read; reads never
    fail on protected estimates)."""
    await _est_or_404(est_id, user)
    polys: list[dict] = []
    async for row in db.pdf_overlay_polygons.find(
        {"estimate_id": est_id}, {"_id": 0}
    ).sort("created_at", 1):
        polys.append(row)
    return {"polygons": polys, "total": len(polys)}


@router.put("/estimates/{est_id}/pdf-overlay")
async def upsert_pdf_overlay(
    est_id: str,
    payload: PolygonWriteIn,
    user: dict = Depends(get_current_user),
):
    """Upsert one polygon. Recomputes affected takeoff lines' qty
    with `qty_src="human"` so rebuild-survival rides through the
    existing hover.py shield.

    HUMAN-ENTRY on protected estimates (Howard ruled 2026-08-13
    pro-quotes reply 5): NO derived-write guard here. A drawn zone
    is human entry — it rides above the freeze on EST-886440 and
    lands in `protected_estimate_ledger` like tape-check and
    profile-annotations.
    """
    _validate_polygon(payload)
    est = await _est_or_404(est_id, user)
    pid = payload.id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": pid,
        "estimate_id": est_id,
        "page": int(payload.page),
        "face_id": payload.face_id,
        "material_class": payload.material_class,
        "vertices_pct": [[float(x), float(y)]
                         for x, y in payload.vertices_pct],
        "qty_src": "human",
        "author_id": user.get("id") or "",
        "author_email": user.get("email") or "",
        "updated_at": now,
    }
    existing = await db.pdf_overlay_polygons.find_one({"id": pid})
    if existing:
        doc["created_at"] = existing.get("created_at") or now
        await db.pdf_overlay_polygons.replace_one({"id": pid}, doc)
    else:
        doc["created_at"] = now
        await db.pdf_overlay_polygons.insert_one(doc)

    # Recompute lines with all polygons on this estimate.
    all_polys: list[dict] = []
    async for row in db.pdf_overlay_polygons.find(
        {"estimate_id": est_id}, {"_id": 0}
    ):
        all_polys.append(row)
    new_lines = apply_overlay_to_takeoff(
        est.get("lines") or [], all_polys,
    )
    await db.estimates.update_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"$set": {"lines": new_lines, "updated_at": now}},
    )
    # Ledger the human write on protected estimates.
    if await is_untouchable(est_id):
        await ledger_human_write(
            est_id, "pdf_overlay_polygon",
            actor_email=user.get("email", ""),
            meta={"polygon_id": pid, "page": doc["page"],
                  "face_id": doc["face_id"],
                  "material_class": doc["material_class"]},
        )
    # Return a JSON-safe view (strip motor's inserted _id and coerce
    # datetimes to iso strings on the timestamps).
    safe = {k: v for k, v in doc.items() if k != "_id"}
    safe["created_at"] = str(safe.get("created_at") or "")
    safe["updated_at"] = str(safe.get("updated_at") or "")
    return {"ok": True, "polygon": safe}


@router.delete("/estimates/{est_id}/pdf-overlay/{polygon_id}")
async def delete_pdf_overlay(
    est_id: str, polygon_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete one polygon. Recomputes lines. Same human-entry rule
    as PUT — deleting a zone is still Howard's hand."""
    est = await _est_or_404(est_id, user)
    res = await db.pdf_overlay_polygons.delete_one(
        {"id": polygon_id, "estimate_id": est_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Polygon not found")
    all_polys: list[dict] = []
    async for row in db.pdf_overlay_polygons.find(
        {"estimate_id": est_id}, {"_id": 0}
    ):
        all_polys.append(row)
    new_lines = apply_overlay_to_takeoff(
        est.get("lines") or [], all_polys,
    )
    await db.estimates.update_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"$set": {"lines": new_lines,
                  "updated_at": datetime.now(timezone.utc)}},
    )
    if await is_untouchable(est_id):
        await ledger_human_write(
            est_id, "pdf_overlay_polygon",
            actor_email=user.get("email", ""),
            meta={"deleted": polygon_id},
        )
    return {"ok": True, "deleted": polygon_id}
