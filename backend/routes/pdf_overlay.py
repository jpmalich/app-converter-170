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
import re
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
    # SEND-48 zone binding: per-surface faces — a gable is its own
    # bindable surface ("gable:front"), distinct from the face body.
    if face_id.startswith("gable:") and face_id[len("gable:"):] in _FIXED_FACES:
        return True
    return face_id.startswith("dormer:") and len(face_id) > len("dormer:")


def _surface_of(face_id: str):
    """(wall_label, surface) for a bindable face_id; None for dormers."""
    if face_id in _FIXED_FACES:
        return face_id, "body"
    if face_id.startswith("gable:"):
        return face_id[len("gable:"):], "gable"
    return None


def surface_derived_snapshot(est: dict, face_id: str):
    """SEND-48: the ONE surface a zone supersedes — its derived value or
    its named refusal, read from the persisted walk detail. Returns
    (sqft, refusal) — (None, None) when no walk detail exists (legacy
    whole-class replacement stays in force for that group). A REFUSING
    face returns (0.0, <named reason>) so it is fully bindable — the
    primary purpose of the feature."""
    surf = _surface_of(face_id)
    if not surf:
        return None, None
    label, kind = surf
    detail = (est.get("hover_measurements") or {}).get("_wall_walk_detail")
    if not isinstance(detail, list):
        return None, None
    row = next((d for d in detail
                if str(d.get("label") or "").lower() == label), None)
    if row is None:
        return 0.0, f"face {label!r} not present in the derivation"
    if row.get("refused"):
        return 0.0, row.get("reason") or "face refused"
    if kind == "body":
        ref = row.get("body_refusal")
        return (0.0 if ref else float(row.get("body_sqft") or 0.0)), ref
    ref = row.get("gable_refusal")
    if ref:
        return 0.0, ref
    g = row.get("gable_sqft")
    return float(g or 0.0), None


class ScaleRefIn(BaseModel):
    """Evidence-grounded scale for the VIEW a polygon sits in. TWO honest
    modes, NO baked constant (Law C):

    - mode="printed_scale": the printed fraction (e.g. 3/16"=1'-0") read
      off the sheet → `in_per_ft` (paper inches per foot) + `dpi` (the
      page's RECORDED render DPI). feet-per-pixel = 1/(in_per_ft × dpi).
      This is the PRIMARY path — deterministic, no vision pixel coords.
    - mode="trace": a human calibration line (`p1`,`p2` page-normalised)
      over a printed dimension of `real_ft`. feet-per-pixel from the
      traced span. The human places the endpoints, so it is precise.

    Absence of a usable scale → the area is REFUSED (sqft None)."""
    mode: str = "trace"                     # "printed_scale" | "trace"
    # printed_scale fields:
    in_per_ft: Optional[float] = None       # paper inches per foot
    dpi: Optional[float] = None             # recorded page render DPI
    # trace fields:
    p1: Optional[list[float]] = None
    p2: Optional[list[float]] = None
    real_ft: Optional[float] = None
    # provenance (names the path that ACTUALLY ran — Howard ruled):
    source: str = ""                        # "READ" | "TRACE" text
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
    # SEND-48: "proposed" zones are PROVISIONAL (AI-suggested, human-
    # confirmable) and NEVER feed a quantity; "human" zones are the
    # contractor's hand. Confirming/bumping a proposal makes it human.
    provenance: str = "human"


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
    """ft² of a page-normalised polygon under an evidence-grounded scale,
    or None (REFUSED) when the scale cannot be resolved.

    Two modes (see ScaleRefIn). Both resolve a feet-per-pixel in the
    page's NATURAL raster px space; the polygon is shoelaced in that same
    px space (square pixels ⇒ isotropic) and multiplied by
    (ft/px)². Winding-order insensitive."""
    if not vertices_pct or len(vertices_pct) < 3:
        return None
    if not scale_ref or not page_w_px or not page_h_px:
        return None

    mode = scale_ref.get("mode")
    if not mode:
        mode = "printed_scale" if scale_ref.get("in_per_ft") else "trace"

    ft_per_px: Optional[float] = None
    if mode == "printed_scale":
        try:
            in_per_ft = float(scale_ref.get("in_per_ft"))
            dpi = float(scale_ref.get("dpi"))
        except (TypeError, ValueError):
            return None
        if in_per_ft <= 0 or dpi <= 0:
            return None
        # feet per paper inch = 1/in_per_ft ; pixels per paper inch = dpi
        ft_per_px = 1.0 / (in_per_ft * dpi)
    else:  # trace
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

    if not ft_per_px or ft_per_px <= 0:
        return None
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
        # SEND-48: PROPOSED zones are provisional — they never feed a
        # quantity. Only human zones enter the takeoff math.
        if (p.get("provenance") or "human") == "proposed":
            continue
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
        # SEND-48 PER-SURFACE BINDING: when every zone in the class
        # carries its surface snapshot, a zone replaces the ONE surface
        # it covers (body or gable of one face) — never the whole house.
        # line qty = baseline − Σ(replaced surface derived) + Σ(zone ft²).
        # A refusing surface snapshots 0.0 + its named refusal, so a
        # refused face is fully bindable. Zones missing the snapshot
        # (pre-SEND-48) keep the legacy whole-class replacement — both
        # modes are named on the line.
        per_surface = all(p.get("surface_derived_sqft") is not None
                          for p in convertible)
        if per_surface:
            surf: dict[str, dict] = {}
            for p in convertible:
                surf.setdefault(p.get("face_id") or "", {
                    "face_id": p.get("face_id") or "",
                    "superseded_sqft": float(p["surface_derived_sqft"]),
                    "refusal": p.get("surface_refusal")})
            replaced_sqft = round(sum(s["superseded_sqft"]
                                      for s in surf.values()), 2)
            delta_qty = _sqft_to_line_qty(total_sqft - replaced_sqft,
                                          new.get("unit") or "")
            base_for_math = (_group_baseline(polys, new) or 0.0)
            if delta_qty is None:
                _retire_override(new)
                new["overlay_scale_unreadable"] = True
                new["overlay_polygon_count"] = len(convertible)
                out.append(new)
                continue
            line_qty = round(base_for_math + delta_qty, 2)
        else:
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
        if per_surface:
            new["overlay_per_surface"] = True
            new["overlay_replaced_surfaces"] = sorted(
                surf.values(), key=lambda s: s["face_id"])
        else:
            new.pop("overlay_per_surface", None)
            new.pop("overlay_replaced_surfaces", None)
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
            detail=(f"face_id must be one of {sorted(_FIXED_FACES)}, "
                    "'gable:<face>' or 'dormer:<label>'"),
        )
    if p.provenance not in {"human", "proposed"}:
        raise HTTPException(
            status_code=400,
            detail="provenance must be 'human' or 'proposed'",
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
    surface_sqft, surface_refusal = surface_derived_snapshot(
        est, payload.face_id)
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
        # SEND-48 per-surface snapshot: the ONE surface this zone
        # supersedes (0.0 + named refusal when the face refuses — a
        # refusing face is fully bindable, the feature's primary purpose)
        "surface_derived_sqft": surface_sqft,
        "surface_refusal": surface_refusal,
        "provenance": payload.provenance,
        "qty_src": payload.provenance,
        "author_id": user.get("id") or "",
        "author_email": user.get("email") or "",
        "updated_at": now,
    }
    existing = await db.pdf_overlay_polygons.find_one({"id": pid})
    if existing:
        doc["created_at"] = existing.get("created_at") or now
        # SEND-55 item 2 — CONFIRMATION MUST NOT LAUNDER THE BASIS.
        # Confirmation upgrades AUTHORITY, not EVIDENCE: the record keeps
        # what was confirmed (tier + basis + the proposal's own shape).
        if (existing.get("provenance") == "proposed"
                and doc["provenance"] == "human"):
            doc["confirmed_from"] = {
                "tier": existing.get("tier"),
                "basis": existing.get("basis"),
                "band_note": existing.get("band_note"),
                "proposed_vertices_pct": existing.get("vertices_pct"),
                "proposed_from": existing.get("proposed_from"),
            }
        elif existing.get("confirmed_from"):
            doc["confirmed_from"] = existing["confirmed_from"]
        # Preserve the group's original baseline across edits of an
        # existing polygon (never re-capture from a now-overridden line).
        if existing.get("derived_baseline_qty") is not None:
            doc["derived_baseline_qty"] = existing["derived_baseline_qty"]
        # ... and the surface snapshot (never re-capture post-override).
        if existing.get("surface_derived_sqft") is not None:
            doc["surface_derived_sqft"] = existing["surface_derived_sqft"]
            doc["surface_refusal"] = existing.get("surface_refusal")
        await db.pdf_overlay_polygons.replace_one({"id": pid}, doc)
    else:
        doc["created_at"] = now
        await db.pdf_overlay_polygons.insert_one(doc)

    await _recompute_and_store(est_id, user, est.get("lines") or [])

    # SEND-55 item 4 — the correction metric (eval only, never an input).
    if doc.get("confirmed_from") and doc["provenance"] == "human":
        metrics = zone_event_metrics(
            doc["confirmed_from"].get("proposed_vertices_pct") or [],
            doc["vertices_pct"], doc.get("scale_ref"),
            doc.get("page_w_px"), doc.get("page_h_px"))
        await _record_zone_event("CORRECTED", est_id, doc, user, metrics)
    elif not existing and doc["provenance"] == "human":
        n_props = await db.pdf_overlay_polygons.count_documents(
            {"estimate_id": est_id, "face_id": doc["face_id"],
             "material_class": doc["material_class"],
             "provenance": "proposed"})
        await _record_zone_event(
            "ADDED_FROM_SCRATCH", est_id, doc, user,
            extra={"proposal_existed_on_face": n_props > 0,
                   "area_confirmed_sqft": sqft})

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

    # SEND-55 item 4 — a deleted PROPOSAL scores ZERO, never "no data":
    # a face whose proposal was thrown away is a total failure of the
    # proposal and must appear as one.
    if victim.get("provenance") == "proposed":
        await _record_zone_event(
            "DELETED", est_id, victim, user,
            extra={"area_delta_ratio": None, "score": 0.0})

    remaining = await db.pdf_overlay_polygons.count_documents(
        {"estimate_id": est_id,
         "material_class": victim.get("material_class"),
         # SEND-48: proposed zones are provisional — they never hold an
         # override alive.
         "provenance": {"$ne": "proposed"}})
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


def _gap_y(s: str):
    m = re.search(r"@([\d.]+)", s or "")
    return float(m.group(1)) if m else None


def _contested_chain_value(r: dict, top_y: float, bot_y: float):
    """RULING BBB — the CONTESTED tier's value. Walk the gaps strictly
    between the datum pair. Every gap must be BOUND (its printed value)
    or CONTESTED (take the LARGER contestant — running short costs a
    trip, over-ordering costs dollars; never averaged, never list-order).
    Any UNDIMENSIONED gap → no chain value (None). Returns
    (total_inches, [contested rail raws]) or None."""
    total, named, any_contested = 0.0, [], False
    for g in r.get("gaps") or []:
        y0, y1 = _gap_y(g.get("from")), _gap_y(g.get("to"))
        if y0 is None or y1 is None:
            continue
        if min(y0, y1) < top_y - 0.05 or max(y0, y1) > bot_y + 0.05:
            continue  # outside the datum pair
        if g.get("status") == "BOUND" and g.get("value_in"):
            total += float(g["value_in"])
        elif g.get("status") == "CONTESTED" and g.get("rails"):
            vals = [(float(x["in"]), x.get("raw", "")) for x in g["rails"]
                    if x.get("in")]
            if not vals:
                return None
            vals.sort(reverse=True)
            total += vals[0][0]
            named.extend(v[1] for v in vals)
            any_contested = True
        else:
            return None
    if not any_contested or total <= 0:
        return None
    return total, named


def _ladder_geometry(r: dict):
    """SEND-55 item 2 — RULING BBB ladder: EVERY evaluated face proposes.
    Model heights are BARRED from proposals (Ruling BBB, strict AAA):
    every number below is read from that elevation drawing itself.

      DERIVED   → the face's own chain (tier: derived_chain)
      CONTESTED → the larger contestant, BOTH named (contested_pick_larger)
      otherwise → rectangle from the located datums (datum_rectangle)
                  or the title-carved band (band_rectangle)

    Returns a spec dict or None (face has no evaluated elevation)."""
    geo = r.get("datum_geometry") or {}
    band = r.get("band")
    if not r.get("page") or (not geo and not band):
        return None
    top, bot = geo.get("top_of_plate"), geo.get("first_floor")
    spans, span_names = [], []
    for name, d in (("TOP_OF_PLATE", top), ("FIRST_FLOOR", bot)):
        if d and d.get("span_x"):
            spans.append(d["span_x"])
            span_names.append(name)
    if spans:
        x = [min(s[0] for s in spans) / 100.0,
             max(s[1] for s in spans) / 100.0]
        x_basis = ("x: datum marker span (" + " + ".join(span_names)
                   + "), inner label edges (Ruling ZZ); leader offset "
                   "reported, never subtracted")
        x_measured = True
    else:
        x = [0.02, 0.98]
        x_basis = ("x: PAGE WIDTH — no two-corner datum markers on this "
                   "elevation; needs full horizontal adjustment")
        x_measured = False

    def _bottom(y_ff_frac):
        """SEND-63 item 2 (Howard's ruling): the PROPOSAL bottom drops to
        TOP OF FOUNDATION when that datum is located on the face's own
        drawing; else FIRST FLOOR, basis stated either way. DP-1's
        DERIVED band stays sealed at FIRST FLOOR — the proposal and the
        derivation now deliberately differ, and the zone says so."""
        tof = geo.get("top_of_foundation")
        if tof and tof["y"] / 100.0 > y_ff_frac:
            return (tof["y"] / 100.0,
                    "bottom: TOP OF FOUNDATION datum, this elevation",
                    True)
        return (y_ff_frac,
                "bottom: FIRST FLOOR datum — no foundation datum located "
                "on this drawing", False)

    if r.get("status") == "DERIVED" and r.get("span_y"):
        scale_y = [r["span_y"][0] / 100.0, r["span_y"][1] / 100.0]
        y_bot, bottom_basis, differs = _bottom(scale_y[1])
        return {"page": r["page"], "x": x, "y": [scale_y[0], y_bot],
                "scale_y": scale_y, "ft": r.get("ft"),
                "tier": "derived_chain" if x_measured else "datum_rectangle",
                "differs_from_derived_band": differs,
                "basis": (f"derived FIRST FLOOR → TOP OF PLATE chain, "
                          f"{r.get('ft')} ft; {bottom_basis}; {x_basis}")}
    if top and bot:
        scale_y = [top["y"] / 100.0, bot["y"] / 100.0]
        y_bot, bottom_basis, differs = _bottom(scale_y[1])
        y = [scale_y[0], y_bot]
        contested = _contested_chain_value(r, top["y"], bot["y"])
        if contested:
            inches, named = contested
            ft = round(inches / 12.0, 2)
            return {"page": r["page"], "x": x, "y": y, "scale_y": scale_y,
                    "ft": ft,
                    "tier": "contested_pick_larger",
                    "differs_from_derived_band": differs,
                    "basis": (f"CONTESTED height — rails "
                              f"{' vs '.join(named)}; proposed from the "
                              f"LARGER ({ft} ft): running short costs a "
                              f"trip, over-ordering costs dollars; never "
                              f"averaged; {bottom_basis}; {x_basis}"),
                    "contested_rails": named}
        return {"page": r["page"], "x": x, "y": y, "scale_y": scale_y,
                "ft": None,
                "tier": "datum_rectangle",
                "differs_from_derived_band": differs,
                "basis": ("rectangle from the located datums (FIRST "
                          "FLOOR → TOP OF PLATE y); height NOT "
                          f"established on this elevation; {bottom_basis}; "
                          f"{x_basis}")}
    if band:
        return {"page": r["page"],
                "x": x, "y": [band[0] / 100.0, band[1] / 100.0],
                "ft": None, "tier": "band_rectangle",
                "basis": ("STARTING SHAPE from the title-carved band — "
                          "no datum pair located on this elevation; "
                          f"needs full adjustment; {x_basis}")}
    return None


_TIER_RANK = {"derived_chain": 0, "contested_pick_larger": 1,
              "datum_rectangle": 2, "band_rectangle": 3}


def _best_ladder_spec(face_result: dict):
    cands = face_result.get("candidates") or [face_result]
    specs = [s for s in (_ladder_geometry(c) for c in cands) if s]
    if not specs:
        return None
    return min(specs, key=lambda s: _TIER_RANK[s["tier"]])


@router.post("/estimates/{est_id}/pdf-overlay/propose")
async def propose_zones(
    est_id: str, user: dict = Depends(get_current_user),
):
    """SEND-48: AI-PROPOSED zones. For every face whose height the HEIGHT
    BUILD established (DERIVED), propose a provisional band rectangle on
    that face's own elevation drawing, carrying an evidence-grounded
    trace scale read straight from the DP-1 chain. Proposed zones NEVER
    feed a quantity — the contractor bumps vertices / confirms, which
    makes them HUMAN. Re-proposing replaces earlier proposals and never
    touches a human zone. This is a DERIVED write → 423 on a protected
    estimate."""
    est = await _est_or_404(est_id, user)
    if await is_untouchable(est_id):
        raise HTTPException(
            status_code=423,
            detail="protected estimate — proposals are derived writes")
    run = await db.ai_blueprint_runs.find_one(
        {"estimate_id": est_id, "status": "done"},
        {"_id": 0, "result.raw_ai._ocr_text_by_page": 1,
         "result.raw_ai._ocr_text_ref": 1, "run_id": 1},
        sort=[("created_at", -1)])
    raw_ai = ((run or {}).get("result") or {}).get("raw_ai") or {}
    ot = raw_ai.get("_ocr_text_by_page")
    if not ot and raw_ai.get("_ocr_text_ref"):
        ref = await db.ai_blueprint_ocr.find_one(
            {"run_id": raw_ai["_ocr_text_ref"]}, {"_id": 0, "pages": 1})
        ot = (ref or {}).get("pages")
    if not isinstance(ot, dict) or not ot:
        raise HTTPException(
            status_code=409,
            detail="no persisted OCR text on this estimate's blueprint "
                   "run — nothing to propose from")

    from height_read import derive_face_heights
    faces = derive_face_heights(ot)
    await db.pdf_overlay_polygons.delete_many(
        {"estimate_id": est_id, "provenance": "proposed"})
    now = datetime.now(timezone.utc)
    created = []
    skipped = []
    face_to_id = {"front": "front", "rear": "back",
                  "left": "left", "right": "right"}
    for face, r in faces.items():
        # SEND-55 item 2 — RULING BBB ladder: EVERY evaluated face
        # proposes. Coverage is a FACT, not a success metric — the
        # metric is correction distance (item 4).
        spec = _best_ladder_spec(r)
        if not spec:
            skipped.append({
                "face_id": face_to_id[face],
                "reason": ("no evaluated elevation drawing for this face "
                           "— nothing to propose from")})
            continue
        (x0, x1), (y_top, y_bot) = spec["x"], spec["y"]
        page = ot.get(spec["page"]) or {}
        band = r.get("band") or [0.0, 100.0]
        scale_ref = None
        if spec.get("ft"):
            # the trace scale stays anchored to the DATUM PAIR (scale_y),
            # never the zone's TOF-extended bottom — the chain ft spans
            # FIRST FLOOR → TOP OF PLATE only.
            sy = spec.get("scale_y") or [y_top, y_bot]
            scale_ref = {"mode": "trace",
                         "p1": [0.5, sy[0]], "p2": [0.5, sy[1]],
                         "real_ft": spec["ft"], "source": "READ",
                         "from_quote": (r.get("chain") or [spec["tier"]])[0]}
        band_note = None
        if spec.get("differs_from_derived_band"):
            band_note = ("this proposal is taller than the derived wall "
                         "band (bottom at TOP OF FOUNDATION; DP-1's "
                         "derived band stays FIRST FLOOR) — confirming "
                         "it will change the quantity")
        doc = {
            "id": str(uuid.uuid4()),
            "estimate_id": est_id,
            "page": int(spec["page"]),
            "face_id": face_to_id[face],
            "material_class": "siding",
            "vertices_pct": [[x0, y_top], [x1, y_top],
                             [x1, y_bot], [x0, y_bot]],
            "scale_ref": scale_ref,
            "page_w_px": page.get("page_w"),
            "page_h_px": page.get("page_h"),
            "sqft": None,          # provisional — never feeds a quantity
            "derived_baseline_qty": None,
            "surface_derived_sqft": None,
            "surface_refusal": None,
            "provenance": "proposed",
            "qty_src": "proposed",
            "tier": spec["tier"],
            "basis": spec["basis"],
            "band_note": band_note,
            "proposed_from": {"run_id": (run or {}).get("run_id"),
                              "height_ft": spec.get("ft"),
                              "span": r.get("span"),
                              "band": band,
                              "tier": spec["tier"],
                              "bottom_datum": ("TOP_OF_FOUNDATION"
                                               if spec.get("differs_from_derived_band")
                                               else "FIRST_FLOOR"),
                              "span_x_pct": [round(x0 * 100, 2),
                                             round(x1 * 100, 2)]},
            "author_id": "height_build",
            "author_email": "",
            "created_at": now,
            "updated_at": now,
        }
        await db.pdf_overlay_polygons.insert_one(doc)
        created.append({k: v for k, v in doc.items() if k != "_id"})
    for c in created:
        c["created_at"] = str(c["created_at"])
        c["updated_at"] = str(c["updated_at"])
    return {"ok": True, "proposed": created, "skipped": skipped,
            "note": ("proposed zones are PROVISIONAL — they feed no "
                     "quantity until a human confirms or bumps them")}


def _ft_per_px(scale_ref, W, H):
    """ft per rendered pixel from a trace scale, or None."""
    if not scale_ref or not W or not H:
        return None
    p1, p2 = scale_ref.get("p1"), scale_ref.get("p2")
    real_ft = scale_ref.get("real_ft")
    if not p1 or not p2 or not real_ft:
        return None
    d = hypot((p2[0] - p1[0]) * W, (p2[1] - p1[1]) * H)
    return (real_ft / d) if d > 0 else None


def zone_event_metrics(proposed_v, confirmed_v, scale_ref, W, H):
    """SEND-55 item 4 — how far the human moved the proposal.

    PER-VERTEX displacement in FEET (percent-of-page is not a number a
    contractor can act on) + WHICH EDGE moved (a consistently-short
    right edge is a diagnosis, an aggregate hides it) + AREA DELTA
    |proposed − confirmed| / confirmed — the headline: four vertices
    translating a foot barely changes area; one vertex can shift it 20%.
    This is an EVAL. Nothing may read it at derivation time."""
    out = {"ft_available": False, "per_vertex_ft": None, "edges_ft": None,
           "area_proposed_sqft": None, "area_confirmed_sqft": None,
           "area_delta_ratio": None}
    fpp = _ft_per_px(scale_ref, W, H)
    a_prop = polygon_sqft_from_scale(proposed_v, scale_ref, W, H)
    a_conf = polygon_sqft_from_scale(confirmed_v, scale_ref, W, H)
    out["area_proposed_sqft"] = a_prop
    out["area_confirmed_sqft"] = a_conf
    if a_prop is not None and a_conf and a_conf > 0:
        out["area_delta_ratio"] = round(abs(a_prop - a_conf) / a_conf, 4)
    if fpp:
        out["ft_available"] = True
        if len(proposed_v) == len(confirmed_v):
            pv = []
            for i, (p, c) in enumerate(zip(proposed_v, confirmed_v)):
                dx = (c[0] - p[0]) * W * fpp
                dy = (c[1] - p[1]) * H * fpp
                pv.append({"i": i, "dx_ft": round(dx, 2),
                           "dy_ft": round(dy, 2),
                           "dist_ft": round(hypot(dx, dy), 2)})
            out["per_vertex_ft"] = pv
        out["edges_ft"] = {
            "left": round((min(v[0] for v in confirmed_v)
                           - min(v[0] for v in proposed_v)) * W * fpp, 2),
            "right": round((max(v[0] for v in confirmed_v)
                            - max(v[0] for v in proposed_v)) * W * fpp, 2),
            "top": round((min(v[1] for v in confirmed_v)
                          - min(v[1] for v in proposed_v)) * H * fpp, 2),
            "bottom": round((max(v[1] for v in confirmed_v)
                             - max(v[1] for v in proposed_v)) * H * fpp, 2),
        }
    return out


async def _record_zone_event(event: str, est_id: str, doc: dict,
                             user: dict, metrics: dict | None = None,
                             extra: dict | None = None):
    """One row per (zone, event) in `zone_correction_events`. CORRECTED
    upserts on every human write so the FINAL confirmed shape scores —
    the first vertex bump must not freeze the measurement. DELETED
    scores zero, never 'no data'. ADDED_FROM_SCRATCH is area the system
    missed entirely. The denominator is FACES THAT NEEDED A ZONE, not
    proposals offered — a coverage-blind metric rewards not proposing."""
    row = {
        "id": f"{doc.get('id')}::{event}",
        "zone_id": doc.get("id"),
        "estimate_id": est_id,
        "event": event,
        "face_id": doc.get("face_id"),
        "material_class": doc.get("material_class"),
        "page": doc.get("page"),
        "tier": (doc.get("confirmed_from") or {}).get("tier") or doc.get("tier"),
        "basis": (doc.get("confirmed_from") or {}).get("basis") or doc.get("basis"),
        "author_email": (user or {}).get("email") or "",
        "at": datetime.now(timezone.utc),
    }
    if metrics:
        row.update(metrics)
    if extra:
        row.update(extra)
    await db.zone_correction_events.replace_one(
        {"id": row["id"]}, row, upsert=True)


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
