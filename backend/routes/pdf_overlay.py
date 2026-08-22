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
    # SEND-96: a chimney chase is its own bindable surface — it exists
    # even where no chase ink was found (refused faces must leave
    # Howard somewhere to draw; the SEND-48 lesson, third instance
    # prevented).
    if face_id.startswith("chase:") and face_id[len("chase:"):] in _FIXED_FACES:
        return True
    return face_id.startswith("dormer:") and len(face_id) > len("dormer:")


def _surface_of(face_id: str):
    """(wall_label, surface) for a bindable face_id; None for dormers."""
    if face_id in _FIXED_FACES:
        return face_id, "body"
    if face_id.startswith("gable:"):
        return face_id[len("gable:"):], "gable"
    if face_id.startswith("chase:"):
        return face_id[len("chase:"):], "chase"
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
    if kind == "chase":
        # SEND-96: the walk derives body and gable only — a chase never
        # has a derived figure to supersede. 0.0 + the named reason
        # keeps every chase surface fully bindable, ink or no ink.
        return 0.0, ("no chase is ever derived by the walk — chase "
                     "area enters only by a drawn zone")
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
    # SEND-66: set ONLY by the UI's explicit face pick after the API
    # returned FACE_AMBIGUOUS — the human's answer, recorded as such.
    face_confirmed: bool = False


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


def _overlay_note(line: dict, total: float, gable_zone: bool = False) -> str:
    base = (line.get("note") or "").split(" · PDF-OVERLAY")[0]
    note = (base + f" · PDF-OVERLAY zone ({total:.1f} ft²)").strip(" ·")
    if gable_zone:
        # SEND-74 — the money line says the gable basis: a bound gable
        # zone is drawn evidence at its true area, never factored.
        note += (" · gable zone bound at its drawn area — no field "
                 "factor")
    return note


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
    chase_zones: list[dict] = []
    for p in polygons or []:
        # SEND-48: PROPOSED zones are provisional — they never feed a
        # quantity. Only human zones enter the takeoff math.
        if (p.get("provenance") or "human") == "proposed":
            continue
        # SEND-71 (one-off cleanup, registered — NOT a class): a zone
        # FLAGGED face-ambiguous by ruling stops binding until Howard
        # redraws it. The FACE_AMBIGUOUS write gate (SEND-66) catches
        # straddles at write time now, so this flag exists for the
        # single pre-gate zone. Do not build a splitting feature.
        if p.get("binding_suspended"):
            continue
        # SEND-96 item 2: a chase zone is its OWN quote row, basis
        # labelled — it never merges into the body line's class math.
        if str(p.get("face_id") or "").startswith("chase:"):
            chase_zones.append(p)
            continue
        by_class.setdefault(p.get("material_class") or "", []).append(p)

    out: list[dict] = []
    for line in (lines or []):
        if line.get("overlay_chase_line"):
            continue    # SEND-96: rebuilt fresh from the zones each pass
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
        new["note"] = _overlay_note(
            line, total_sqft,
            gable_zone=any(str(p.get("face_id") or "").startswith("gable:")
                           for p in convertible))
        out.append(new)
    # ── SEND-96 item 2 — CHIMNEY CHASE rows on the quote, basis
    # labelled (customer-facing is where a laundered basis does the
    # most damage). A chase on a CONTESTED-scale face REFUSES and
    # blocks the quote gate (Ruling L: the total is INCOMPLETE).
    _face_disp = {"back": "rear", "front": "front",
                  "left": "left", "right": "right"}
    for p in chase_zones:
        face = str(p.get("face_id") or "").split(":", 1)[-1]
        basis = str(p.get("basis")
                    or "zone drawn by hand — human trace")
        host = next((ln for ln in (lines or [])
                     if _line_matches(ln, p.get("material_class") or "")),
                    None)
        row = {"id": f"chase-{p.get('id')}",
               "name": f"Chimney Chase — {_face_disp.get(face, face)}",
               "unit": "SQ", "mat": 0, "lab": 0,
               "tab": (host or {}).get("tab") or "vinyl",
               "section": (host or {}).get("section") or "Vinyl Siding",
               "overlay_chase_line": True,
               "qty_src": "human",
               # SEND-96 order item 2 — the four chase corner verticals,
               # a visible UNPRICED note; no corner-count change
               # (Ruling G: corners over unverified heights are not
               # derivable).
               "chase_corner_note": (
                   "carries 4 corner verticals running the chase "
                   "height — UNPRICED, corner count unchanged")}
        contested = (p.get("tier") == "contested_pick_larger"
                     or "CONTESTED" in basis)
        if contested:
            row.update({
                "qty": None, "raw_qty": None,
                "not_derivable": True,
                "not_derivable_reason": (
                    "chase sits on a CONTESTED-scale face — an "
                    "unverifiable quantity must not quietly price; "
                    "the total is INCOMPLETE until the contest "
                    "resolves (Ruling L). Basis: " + basis),
                "note": "REFUSED — contested scale. Basis: " + basis})
        else:
            sqft = p.get("sqft")
            qty = (_sqft_to_line_qty(float(sqft), "SQ")
                   if sqft is not None else None)
            if qty is None:
                row.update({
                    "qty": None, "raw_qty": None,
                    "not_derivable": True,
                    "not_derivable_reason": (
                        "chase zone carries no usable scale — the "
                        "area is REFUSED, never $0. Basis: " + basis),
                    "note": "REFUSED — no usable scale. Basis: "
                            + basis})
            else:
                row.update({"qty": qty, "raw_qty": qty,
                            "overlay_sqft": round(float(sqft), 2),
                            "note": "Basis: " + basis})
        out.append(row)
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


_BAND_FACE_TO_ID = {"front": "front", "rear": "back",
                    "left": "left", "right": "right"}


def resolve_face_from_bands(bands: dict, vertices_pct: list,
                            face_id: str) -> dict:
    """SEND-66 (Howard's ruling, P0 money bug): a human zone's face
    resolves from its CENTROID'S ELEVATION BAND on that page — never the
    page tag. If the zone straddles two bands or the centroid sits in no
    band, the write is NOT GUESSED: AMBIGUOUS comes back and the UI asks
    for the face explicitly. Pure — the same band carving the height
    read already uses.

    bands: {face_name: (y0, y1)} percent-of-page from `face_bands`.
    vertices_pct: [[x, y], ...] page-normalised [0, 1].
    face_id: the submitted tag ("front", "gable:front", "dormer:x")."""
    if face_id.startswith("dormer:"):
        return {"status": "NO_BANDS",
                "reason": "a dormer zone carries no elevation face"}
    if not bands or not vertices_pct:
        return {"status": "NO_BANDS",
                "reason": ("no face bands carved on this page — the tag "
                           "stands")}

    def _band_of(y_pct):
        # 1e-3 pct boundary tolerance: a vertex constructed ON the band
        # edge (a gable top at the band's own y0) must not flip bands on
        # float round-trip noise.
        for f, (b0, b1) in bands.items():
            if b0 - 1e-3 <= y_pct < b1 - 1e-3:
                return f
        return None

    cy = sum(v[1] for v in vertices_pct) / len(vertices_pct) * 100.0
    c_face = _band_of(cy)
    is_gable = face_id.startswith("gable:")
    if c_face is None:
        cands = sorted(_BAND_FACE_TO_ID[f] for f in bands)
        return {"status": "AMBIGUOUS",
                "reason": ("this zone's centroid sits in no elevation "
                           "drawing's band on this sheet — which face is "
                           "it? A zone outside every drawing may have "
                           "been drawn in the title block or margin by "
                           "accident."),
                "candidates": [("gable:" + c) if is_gable else c
                               for c in cands]}
    touched = {c_face} | {f for f in (_band_of(v[1] * 100.0)
                                      for v in vertices_pct) if f}
    if len(touched) > 1:
        names = " and ".join(sorted(f.upper() for f in touched))
        return {"status": "AMBIGUOUS",
                "reason": (f"this zone sits across the {names} drawings "
                           "on this sheet — which face is it? A zone "
                           "drawn across two elevations is usually an "
                           "accident: fixing the shape may be the real "
                           "answer."),
                "candidates": [("gable:" + _BAND_FACE_TO_ID[f]) if is_gable
                               else _BAND_FACE_TO_ID[f]
                               for f in sorted(touched)]}
    base = _BAND_FACE_TO_ID[c_face]
    resolved = ("gable:" + base) if is_gable else base
    sub = face_id[len("gable:"):] if is_gable else face_id
    return {"status": "RESOLVED", "resolved_face_id": resolved,
            "band_face": c_face, "disagrees": sub != base}


async def _latest_ocr(est_id: str):
    """The latest done blueprint run's persisted OCR pages + the run doc
    (run_id, source_files). Inline pages or the spillover ref."""
    run = await db.ai_blueprint_runs.find_one(
        {"estimate_id": est_id, "status": "done"},
        {"_id": 0, "result.raw_ai._ocr_text_by_page": 1,
         "result.raw_ai._ocr_text_ref": 1, "run_id": 1,
         "result.raw_ai.sheets_identified": 1,
         "result.raw_ai.appendages": 1,
         "source_files": 1},
        sort=[("created_at", -1)])
    raw_ai = ((run or {}).get("result") or {}).get("raw_ai") or {}
    ot = raw_ai.get("_ocr_text_by_page")
    if not ot and raw_ai.get("_ocr_text_ref"):
        ref = await db.ai_blueprint_ocr.find_one(
            {"run_id": raw_ai["_ocr_text_ref"]}, {"_id": 0, "pages": 1})
        ot = (ref or {}).get("pages")
    return (ot if isinstance(ot, dict) and ot else None), run


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
    verts = [[float(x), float(y)] for x, y in payload.vertices_pct]

    # SEND-66 INVARIANT: a zone whose tag and centroid band disagree
    # never binds silently, on any path. The face resolves from the
    # centroid's band; straddle / no band → 409, the UI asks.
    from height_read import elevation_page_faces
    ot, _run = await _latest_ocr(est_id)
    bands = ((elevation_page_faces(ot) if ot else {})
             .get(str(payload.page))) or {}
    face_res = resolve_face_from_bands(bands, verts, payload.face_id)
    face_id = payload.face_id
    if face_res["status"] == "AMBIGUOUS":
        if payload.face_confirmed:
            face_resolution = {"method": "human_choice_on_ambiguity",
                               "reason": face_res["reason"],
                               "chosen_face_id": payload.face_id}
        else:
            raise HTTPException(status_code=409, detail={
                "code": "FACE_AMBIGUOUS",
                "reason": face_res["reason"],
                "candidates": face_res["candidates"],
                "message": ("pick the face explicitly — the write is "
                            "not guessed")})
    elif face_res["status"] == "RESOLVED":
        face_id = face_res["resolved_face_id"]
        face_resolution = {"method": "centroid_band",
                           "band_face": face_res["band_face"],
                           "submitted_face_id": payload.face_id,
                           "resolved_face_id": face_id,
                           "disagreed_with_tag": face_res["disagrees"]}
    else:
        face_resolution = {"method": "tag_stands_no_bands",
                           "reason": face_res["reason"]}

    scale_ref = payload.scale_ref.dict() if payload.scale_ref else None
    sqft = polygon_sqft_from_scale(
        verts, scale_ref, payload.page_w_px, payload.page_h_px,
    )
    baseline = await _current_baseline_for_class(
        est, est_id, payload.material_class, pid)
    surface_sqft, surface_refusal = surface_derived_snapshot(
        est, face_id)
    doc = {
        "id": pid,
        "estimate_id": est_id,
        "page": int(payload.page),
        "face_id": face_id,
        "face_resolution": face_resolution,
        "material_class": payload.material_class,
        "vertices_pct": verts,
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
                "geometry_tier": existing.get("geometry_tier"),
                "derived_gable_sqft": existing.get("derived_gable_sqft"),
                "divergence_notice": existing.get("divergence_notice"),
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
    # SEND-84 — DELETION LEDGER on EVERY estimate: a deleted zone
    # leaves a full recoverable snapshot. EST-713272's nine human
    # zones died traceless; that class of loss ends here.
    await db.zone_deletion_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "estimate_id": est_id,
        "kind": "human_delete",
        "actor_email": user.get("email", ""),
        "at": datetime.now(timezone.utc),
        "polygon": dict(victim),
    })
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
         # override alive. SEND-71: neither does a suspended zone.
         "provenance": {"$ne": "proposed"},
         "binding_suspended": {"$exists": False}})
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
              "datum_rectangle": 2, "band_rectangle": 3,
              "gable_outline": 4, "gable_rectangle": 5}


def _best_ladder_spec(face_result: dict):
    cands = face_result.get("candidates") or [face_result]
    specs = [s for s in (_ladder_geometry(c) for c in cands) if s]
    if not specs:
        return None
    return min(specs, key=lambda s: _TIER_RANK[s["tier"]])


# SEND-90 (Howard, 2026-08-14) — RULING XX WIDTH CROSS-CHECK, register:
# THIS WOULD HAVE CAUGHT THE MISSING CHIMNEY WITHOUT ANYONE CHECKING
# PRINTS. Left read 32.60 and right read 29.65, three feet apart, on a
# house XX already knew had equal depths. Nobody noticed until Howard
# looked at the drawings.
XX_CROSS_CHECK_REGISTER = (
    "RULING XX width cross-check (SEND-90): left and right elevation "
    "widths that disagree are FLAGGED ON THE PAYLOAD, NEVER "
    "AUTO-RESOLVED. It compares WALL-ONLY figures (a depth is a "
    "plan-derived wall figure; a silhouette includes projections — "
    "pairing them mixes two rulers). It reports the DIFFERENCE "
    "MAGNITUDE, never a boolean flag — any 'agree within X' is a "
    "chosen threshold, and a boolean either needs a number nobody can "
    "justify or fires on every face. Silent-because-INDETERMINATE is "
    "distinguishable from silent-because-agreeing. This would have "
    "caught the missing chimney: left 32.60 vs right 29.65, three feet "
    "apart, on a house XX already knew had equal depths.")


def _xx_seat_verdict(ot: dict, run: dict) -> dict:
    """SEND-90 — the XX verdict's SEAT: the run's FLOOR-PLAN sheets
    (XX's claim is about plan-derived depths, never a silhouette page —
    elevation pages establish envelopes of their own and would seat the
    verdict on the wrong instrument). Plan sheets that disagree are
    FLAGGED INDETERMINATE naming each page — never resolved."""
    from ocr_geometry import attribution_verdict
    sheets = (((run or {}).get("result") or {}).get("raw_ai")
              or {}).get("sheets_identified") or []
    plan_pages = [str(s.get("page")) for s in sheets
                  if isinstance(s, dict)
                  and s.get("useful_for") == "floor_plan"]
    out = {"seat_pages": plan_pages, "seat_source": "sheets_identified",
           "status": "INDETERMINATE", "why": None, "depth": None,
           "per_page": []}
    if not plan_pages:
        out["why"] = ("no floor-plan sheet identified on the run — the "
                      "verdict has no seat")
        return out
    for pg in plan_pages:
        page = (ot or {}).get(pg) or {}
        try:
            v = attribution_verdict(page.get("runs") or [])
        except Exception as e:
            v = {"status": "INDETERMINATE",
                 "why": f"verdict failed on p{pg}: {e}", "depth": None}
        out["per_page"].append({"page": pg, "status": v.get("status"),
                                "why": v.get("why"),
                                "depth": v.get("depth")})
    statuses = {p["status"] for p in out["per_page"]}
    if statuses == {"IMMATERIAL"}:
        depths = {(p["depth"] or {}).get("feet") is not None
                  and ((p["depth"] or {}).get("feet"),
                       (p["depth"] or {}).get("inches"))
                  for p in out["per_page"]}
        if len(depths) == 1:
            out["status"] = "IMMATERIAL"
            out["depth"] = out["per_page"][0]["depth"]
            out["why"] = ("equal side depths on every floor-plan sheet "
                          f"(pages {', '.join(plan_pages)})")
            return out
        out["why"] = ("floor-plan sheets all read IMMATERIAL but at "
                      "different depths: " + "; ".join(
                          f"p{p['page']} {p['depth']}"
                          for p in out["per_page"]))
        return out
    if statuses == {"MATERIAL"}:
        out["status"] = "MATERIAL"
        out["why"] = ("unequal side depths on every floor-plan sheet "
                      f"(pages {', '.join(plan_pages)})")
        return out
    out["why"] = ("floor-plan sheets disagree — flagged, never "
                  "resolved: " + "; ".join(
                      f"p{p['page']} {p['status']} ({p['why']})"
                      for p in out["per_page"]))
    return out


def _chase_partition(face_ft_h: int, chase_ft_h: int, ratio_l: float):
    """SEND-94 item 2 — the sum holds BY CONSTRUCTION, never by
    tolerance: the chase is the (possibly human-set) value, the wall
    sections are the remainder split at the chase's drawn position.
    Integer hundredths of a foot — the three parts always sum to the
    face exactly, at either contested scale."""
    rem = face_ft_h - chase_ft_h
    wall_l = int(round(rem * ratio_l))
    return wall_l, chase_ft_h, face_ft_h - chase_ft_h - wall_l


def _xx_width_cross_check(verdict: dict, sides: dict) -> dict:
    """SEND-90 — the cross-check payload. Compares WALL-ONLY widths,
    reports the DIFFERENCE MAGNITUDE (never a boolean, no threshold),
    and keeps silent-because-INDETERMINATE distinguishable from
    silent-because-agreeing. Flags, never resolves."""
    out = {"register": XX_CROSS_CHECK_REGISTER, "verdict": verdict,
           "sides": sides, "state": None, "statement": None,
           "difference_ft": None, "silhouette_difference_ft": None}
    st = (verdict or {}).get("status")
    if st == "MATERIAL":
        out["state"] = "NOT_COMPARED"
        out["statement"] = ("XX says the side depths are UNEQUAL — "
                            "equality is not claimed on this house; no "
                            "width comparison applies")
        return out
    if st != "IMMATERIAL":
        out["state"] = "SILENT_INDETERMINATE"
        out["statement"] = (
            f"XX verdict is {st or 'INDETERMINATE'} — the check is "
            "silent because attribution is unresolved "
            f"({(verdict or {}).get('why')}), NOT because the sides "
            "agree")
        return out
    L = (sides or {}).get("left") or {}
    R = (sides or {}).get("right") or {}
    lw_, rw_ = L.get("wall_only_ft"), R.get("wall_only_ft")
    if lw_ is None or rw_ is None:
        missing = [s for s in ("left", "right")
                   if ((sides or {}).get(s) or {}).get("wall_only_ft")
                   is None]
        out["state"] = "SILENT_NO_FIGURE"
        out["statement"] = (
            "XX says the side depths are EQUAL but no wall-only width "
            "stands on: " + "; ".join(
                f"{s} ({((sides or {}).get(s) or {}).get('note') or 'no wall-only figure'})"
                for s in missing))
        return out
    d = round(abs(lw_ - rw_), 2)
    out["state"] = "REPORTED"
    out["difference_ft"] = d
    out["statement"] = (
        f"XX says the side depths are EQUAL — wall-only widths: left "
        f"{lw_} ft, right {rw_} ft — differ by {d} ft")
    ls, rs = L.get("silhouette_ft"), R.get("silhouette_ft")
    if ls is not None and rs is not None:
        sd = round(abs(ls - rs), 2)
        out["silhouette_difference_ft"] = sd
        out["statement"] += (
            f" (silhouettes: left {ls} ft, right {rs} ft — differ by "
            f"{sd} ft; silhouettes include projections and are NOT the "
            "compared figures)")
    return out


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
    ot, run = await _latest_ocr(est_id)
    if not ot:
        raise HTTPException(
            status_code=409,
            detail="no persisted OCR text on this estimate's blueprint "
                   "run — nothing to propose from")

    # SEND-69: the line-work read consumes the run's retained VECTOR
    # source (single PDF). Absent → NOT_ATTEMPTED, disclosed per zone.
    from linework_read import (page_segments, wall_outline_from_segments,
                               gable_triangle_from_segments)
    from measure_staging import (GABLE_BASIS_TRACED,
                                 GABLE_BASIS_FIELD_FACTOR,
                                 gable_basis_label)
    src_pdf = None
    pdf_name = next((f.get("name")
                     for f in ((run or {}).get("source_files") or [])
                     if isinstance(f, dict) and f.get("kind") == "pdf"),
                    None)
    if pdf_name:
        from config import UPLOAD_DIR
        cand_path = UPLOAD_DIR / pdf_name
        if cand_path.exists():
            src_pdf = str(cand_path)
    seg_cache: dict = {}

    from height_read import derive_face_heights
    faces = derive_face_heights(ot)
    # SEND-84 — the rebuild wipe of derived proposals is ledgered too:
    # a rule change overwrites old geometry; the ledger keeps what the
    # superseded rules had drawn.
    wiped = await db.pdf_overlay_polygons.find(
        {"estimate_id": est_id, "provenance": "proposed"},
        {"_id": 0}).to_list(200)
    if wiped:
        await db.zone_deletion_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "estimate_id": est_id,
            "kind": "propose_rebuild_wipe",
            "actor_email": user.get("email", ""),
            "at": datetime.now(timezone.utc),
            "polygons": wiped,
        })
    await db.pdf_overlay_polygons.delete_many(
        {"estimate_id": est_id, "provenance": "proposed"})
    now = datetime.now(timezone.utc)
    created = []
    skipped = []
    face_to_id = {"front": "front", "rear": "back",
                  "left": "left", "right": "right"}
    # SEND-90 — RULING XX width cross-check: verdict seated on the
    # run's floor-plan sheets; side widths collected per face below.
    xx_verdict = _xx_seat_verdict(ot, run)
    xx_sides = {}
    # SEND-94 item 1 — HUMAN-SUPPLIED chase widths (e.g. Howard reading
    # the print). Stored as data with provenance, never in code; a
    # human dimension is NEVER presented as derived.
    _hd_rows = await db.human_dimensions.find(
        {"estimate_id": est_id, "kind": "chase_width_ft"},
        {"_id": 0}).to_list(20)
    chase_width_by_face = {d.get("face_id"): d for d in _hd_rows}
    partitions = {}
    # SEND-84 (authorized) — FENCE MARGIN data: every drawing's own
    # datum extent, per page, for the neighbouring-drawing warning.
    face_fences = {}
    for f2, r2 in faces.items():
        for c2 in (r2.get("candidates") or [r2]):
            g2 = c2.get("datum_geometry") or {}
            fx = []
            for dk in ("top_of_plate", "first_floor", "top_of_foundation"):
                for mk in (g2.get(dk) or {}).get("markers") or []:
                    fx.extend(mk)
            if c2.get("page") and c2.get("band") and len(fx) >= 2:
                face_fences.setdefault(str(c2["page"]), []).append(
                    (f2, c2["band"], (min(fx), max(fx))))
    for face, r in faces.items():
        # SEND-55 item 2 — RULING BBB ladder: EVERY evaluated face
        # proposes. Coverage is a FACT, not a success metric — the
        # metric is correction distance (item 4).
        spec = _best_ladder_spec(r)
        if not spec:
            if face in ("left", "right"):
                xx_sides[face] = {
                    "wall_only_ft": None, "silhouette_ft": None,
                    "note": "no evaluated elevation drawing for this "
                            "face"}
            skipped.append({
                "face_id": face_to_id[face],
                "reason": ("no evaluated elevation drawing for this face "
                           "— nothing to propose from")})
            continue
        # SEND-69 — the LINE-WORK read (wall outline only). When it
        # resolves, the drawn outline REPLACES the datum-span geometry
        # and the basis says so; when it cannot, the datum span stands
        # under ITS OWN geometry tier — a fallback never wears a read's
        # clothes.
        cand = next((c for c in (r.get("candidates") or [r])
                     if c.get("page") == spec["page"]), r)
        geo = cand.get("datum_geometry") or {}
        band = cand.get("band") or [0.0, 100.0]
        top_d, bot_d = geo.get("top_of_plate"), geo.get("first_floor")
        bot_box = bot_d
        if spec.get("differs_from_derived_band"):
            tof = geo.get("top_of_foundation") or {}
            if tof.get("b0") is not None:
                bot_box = tof
        lw = {"status": "NOT_ATTEMPTED",
              "reason": "datum pair not located on this drawing"}
        lw_ctx = None
        if not src_pdf:
            lw = {"status": "NOT_ATTEMPTED",
                  "reason": "no single-PDF vector source retained on "
                            "the run"}
        elif (top_d and bot_box and top_d.get("b0") is not None
                and bot_box.get("b0") is not None):
            try:
                idx = int(spec["page"]) - 1
                if idx not in seg_cache:
                    seg_cache[idx] = page_segments(src_pdf, idx)
                mask = [(u["loc"]["x_pct"], u["loc"]["y_pct"],
                         u["loc"]["x_pct"] + u["loc"]["w_pct"],
                         u["loc"]["y_pct"] + u["loc"]["h_pct"])
                        for u in (ot.get(spec["page"]) or {}).get("runs")
                        or []]
                # SEND-77 (authorized) — X-SCOPING: the face's own
                # datum-line extent fences the strokes, so a second
                # drawing sharing the band's y-range is excluded by the
                # face's own evidence. Union of the governing datum
                # labels' marker boxes, applied VERBATIM (never shrunk).
                fence_xs = []
                for dkey in ("top_of_plate", "first_floor",
                             "top_of_foundation"):
                    for mk in (geo.get(dkey) or {}).get("markers") or []:
                        fence_xs.extend(mk)
                x_fence = ((min(fence_xs), max(fence_xs))
                           if len(fence_xs) >= 2 else None)
                lw = wall_outline_from_segments(
                    seg_cache[idx], (band[0], band[1]),
                    (top_d["b0"], top_d["b1"]),
                    (bot_box["b0"], bot_box["b1"]), mask,
                    x_fence=x_fence)
                if x_fence is not None:
                    lw["x_fence"] = [round(x_fence[0], 2),
                                     round(x_fence[1], 2)]
                    # SEND-84 (authorized) — FENCE MARGIN WARNING: when
                    # a neighbouring drawing's own datum extent reaches
                    # inside this face's fence, say so plainly. The
                    # fence stays applied VERBATIM — never shrunk.
                    for f2, b2, fn2 in face_fences.get(
                            str(spec["page"]), []):
                        if f2 == face:
                            continue
                        if not (b2[0] < band[1] and b2[1] > band[0]):
                            continue      # bands do not share y-range
                        if fn2[0] < x_fence[1] and fn2[1] > x_fence[0]:
                            lw["fence_margin_warning"] = (
                                f"the {f2} drawing's datum extent "
                                f"[{fn2[0]:.2f}, {fn2[1]:.2f}]% shares "
                                "this band and reaches inside this "
                                f"face's fence [{x_fence[0]:.2f}, "
                                f"{x_fence[1]:.2f}]% — its strokes may "
                                "sit inside the fence; the fence is "
                                "applied verbatim, never shrunk")
                            break
                lw_ctx = (idx, mask)
            except Exception as e:
                lw = {"status": "INDETERMINATE",
                      "reason": f"line-work read failed: {e}"}
        # SEND-90 — side widths for the XX cross-check: WALL-ONLY (the
        # plate-terminated wall corners) is the compared figure; the
        # SILHOUETTE (x_span, includes projections) rides alongside and
        # is never compared — pairing them mixes two rulers.
        if face in ("left", "right"):
            entry = {"wall_only_ft": None, "silhouette_ft": None,
                     "note": None}
            pgd = ot.get(spec["page"]) or {}
            if (lw.get("status") == "RESOLVED" and spec.get("ft")
                    and spec.get("scale_y") and pgd.get("page_w")
                    and pgd.get("page_h")):
                sy = spec["scale_y"]
                fppx = (spec["ft"] / (abs(sy[1] - sy[0])
                                      * pgd["page_h"])
                        * pgd["page_w"] / 100.0)
                entry["silhouette_ft"] = round(
                    (lw["x_span"][1] - lw["x_span"][0]) * fppx, 2)
                wc = lw.get("wall_corners")
                if wc:
                    entry["wall_only_ft"] = round(
                        (wc[1] - wc[0]) * fppx, 2)
                else:
                    entry["note"] = ("no plate-terminated wall corners "
                                     "on this drawing — a wall-only "
                                     "width does not stand")
            elif lw.get("status") != "RESOLVED":
                entry["note"] = (f"line-work {lw.get('status')}: "
                                 f"{lw.get('reason')}")
            else:
                entry["note"] = ("no evidence scale on this face — "
                                 "feet not derivable")
            xx_sides[face] = entry
        geometry_tier = "datum_span"
        if lw.get("status") == "RESOLVED":
            geometry_tier = "wall_outline"
            spec["datum_span_x_pct"] = [round(spec["x"][0] * 100, 2),
                                        round(spec["x"][1] * 100, 2)]
            body_span = lw.get("body_x_span") or lw["x_span"]
            if lw.get("chases"):
                # SEND-94 — THE PARTITION: the chase is its own surface;
                # the body reverts to WALL-ONLY (edge) or splits into
                # wall sections (interrupting). The bump never
                # disappears — chase zones are created below.
                spec["outline_vertices"] = None
                spec["x"] = [body_span[0] / 100.0, body_span[1] / 100.0]
                spec["basis"] += (
                    "; PARTITION (SEND-89/94 interrupted-wall ruling): "
                    "the chimney chase is its own surface — this body "
                    "is wall-only; the silhouette span is kept in "
                    "proposed_from")
            else:
                spec["outline_vertices"] = lw["vertices_pct"]
                spec["x"] = [lw["x_span"][0] / 100.0,
                             lw["x_span"][1] / 100.0]
            spec["y"] = [lw["y_top"] / 100.0, lw["y_bot"] / 100.0]
            spec["basis"] += (
                "; GEOMETRY FROM WALL OUTLINE (line-work read): lateral "
                "bounds are drawn boundaries spanning the datum "
                "interval, top/bottom the drawn datum-level lines; the "
                "datum-span figures are kept in proposed_from for "
                "comparison")
            # RULING CCC (SEND-84) — a refused projection SAYS SO on
            # the face itself, not only in the disclosure.
            for pr in lw.get("projection_refusals") or []:
                spec["basis"] += "; PROJECTION REFUSED — " + pr["reason"]
        elif lw.get("status") == "INDETERMINATE":
            geometry_tier = "datum_span_after_linework_refused"
            spec["basis"] += (
                "; line-work could not resolve the outline on this "
                "drawing — this is the datum-marker span, which carries "
                f"the leader offset ({lw.get('reason')})")
        if lw.get("fence_margin_warning"):
            spec["basis"] += ("; FENCE MARGIN WARNING — "
                              + lw["fence_margin_warning"])
        (x0, x1), (y_top, y_bot) = spec["x"], spec["y"]
        page = ot.get(spec["page"]) or {}
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
        # SEND-94 — per-face x/y scales for the partition figures
        fpp_x = fpp_y = None
        if (spec.get("ft") and spec.get("scale_y")
                and page.get("page_w") and page.get("page_h")):
            _sy = spec["scale_y"]
            fpp_x = (spec["ft"] / (abs(_sy[1] - _sy[0])
                                   * page["page_h"])
                     * page["page_w"] / 100.0)
            fpp_y = spec["ft"] / (abs(_sy[1] - _sy[0]) * 100.0)
        doc = {
            "id": str(uuid.uuid4()),
            "estimate_id": est_id,
            "page": int(spec["page"]),
            "face_id": face_to_id[face],
            "material_class": "siding",
            "vertices_pct": (spec.get("outline_vertices")
                             or [[x0, y_top], [x1, y_top],
                                 [x1, y_bot], [x0, y_bot]]),
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
            "geometry_tier": geometry_tier,
            "proposed_from": {"run_id": (run or {}).get("run_id"),
                              "height_ft": spec.get("ft"),
                              # SEND-90: the XX verdict rides every
                              # proposal (seat + status, never a value).
                              "attribution": {
                                  "status": xx_verdict.get("status"),
                                  "why": xx_verdict.get("why"),
                                  "seat_pages":
                                      xx_verdict.get("seat_pages")},
                              "span": r.get("span"),
                              "band": band,
                              "tier": spec["tier"],
                              "bottom_datum": ("TOP_OF_FOUNDATION"
                                               if spec.get("differs_from_derived_band")
                                               else "FIRST_FLOOR"),
                              "span_x_pct": [round(x0 * 100, 2),
                                             round(x1 * 100, 2)],
                              "datum_span_x_pct": spec.get("datum_span_x_pct"),
                              "geometry_tier": geometry_tier,
                              "linework": {
                                  "status": lw.get("status"),
                                  "reason": lw.get("reason"),
                                  "n_spanning": lw.get("n_spanning"),
                                  "n_vertices": lw.get("n_vertices"),
                                  # SEND-94: silhouette kept beside the
                                  # wall-only body; chases disclosed.
                                  "silhouette_x_span": lw.get("x_span"),
                                  "body_x_span": lw.get("body_x_span"),
                                  "chases": lw.get("chases"),
                                  # SEND-77: the x-scoping fence (the
                                  # face's own datum-line extent) that
                                  # scoped the stroke set, disclosed.
                                  "x_fence": lw.get("x_fence"),
                                  # SEND-84 RULING CCC: projections the
                                  # drawing refused, by x, disclosed.
                                  "projection_refusals":
                                      lw.get("projection_refusals"),
                                  # SEND-84: neighbouring-drawing fence
                                  # margin warning (fence never shrunk).
                                  "fence_margin_warning":
                                      lw.get("fence_margin_warning")}},
            "author_id": "height_build",
            "author_email": "",
            "created_at": now,
            "updated_at": now,
        }
        # ── SEND-94 — THE PARTITION, wired. INTERRUPTING chases split
        # the body into wall sections at the chase's drawn inner
        # strokes; every chase becomes its own proposal surface; the
        # partition payload sums to the face BY CONSTRUCTION.
        chase_list = ((lw.get("chases") or [])
                      if lw.get("status") == "RESOLVED" else [])
        inter_chs = sorted((c2 for c2 in chase_list
                            if c2["kind"] == "interrupting"),
                           key=lambda c2: c2["x_inner"][0])
        sib_docs = []
        if inter_chs:
            lo2 = x0
            sections = []
            for c2 in inter_chs:
                sections.append((lo2, c2["x_inner"][0] / 100.0))
                lo2 = c2["x_inner"][1] / 100.0
            sections.append((lo2, x1))
            a2, b2 = sections[0]
            doc["vertices_pct"] = [[a2, y_top], [b2, y_top],
                                   [b2, y_bot], [a2, y_bot]]
            doc["basis"] += (f"; WALL SECTION 1 of {len(sections)} "
                             "(face interrupted by the chase)")
            doc["proposed_from"] = {**doc["proposed_from"],
                                    "wall_section": 1}
            for i2, (a2, b2) in enumerate(sections[1:], start=2):
                sib_docs.append({
                    **doc, "id": str(uuid.uuid4()),
                    "vertices_pct": [[a2, y_top], [b2, y_top],
                                     [b2, y_bot], [a2, y_bot]],
                    "basis": (doc["basis"].rsplit("; WALL SECTION", 1)[0]
                              + f"; WALL SECTION {i2} of {len(sections)}"),
                    "proposed_from": {**doc["proposed_from"],
                                      "wall_section": i2}})
        await db.pdf_overlay_polygons.insert_one(doc)
        created.append({k: v for k, v in doc.items() if k != "_id"})
        for sib in sib_docs:
            await db.pdf_overlay_polygons.insert_one(sib)
            created.append({k: v for k, v in sib.items() if k != "_id"})
        # chase surfaces — the bump moves to its own surface, it does
        # not disappear; the above-plate chase stops being dropped.
        recovered_sqft = []
        for c2 in chase_list:
            if c2["kind"] == "edge":
                cx0, cx1 = sorted((c2["x_proj"], c2["x_wall"]))
                hd = None
            else:
                cx0, cx1 = c2["x_inner"]
                hd = chase_width_by_face.get(face_to_id[face])
            top_pct = (c2["top_ink_y"] if c2.get("top_ink_y") is not None
                       else lw["y_top"])
            drawn_w = (round((cx1 - cx0) * fpp_x, 2) if fpp_x else None)
            width_ft = (round(float(hd["value_ft"]), 2) if hd
                        else drawn_w)
            rise_ft = (round((lw["y_top"] - top_pct) * fpp_y, 2)
                       if (fpp_y and top_pct < lw["y_top"]) else None)
            if width_ft is not None and rise_ft:
                recovered_sqft.append(round(width_ft * rise_ft, 2))
            if hd:
                cbasis = (
                    f"{hd.get('basis')} — HUMAN DIMENSION, never "
                    "presented as derived; drawn strokes read "
                    f"{round((c2['x_inner'][1] - c2['x_inner'][0]) * fpp_x, 2) if fpp_x else None} ft (inner) / "
                    f"{round((c2['x_outer'][1] - c2['x_outer'][0]) * fpp_x, 2) if fpp_x else None} ft (outer) "
                    "at the carried scale")
            else:
                cbasis = (
                    "chimney chase — its own bindable surface "
                    "(interrupted-wall ruling SEND-89/94): drawn "
                    + ("depth" if c2["kind"] == "edge" else "width")
                    + (f" {drawn_w} ft" if drawn_w is not None
                       else " (no evidence scale — shape only)"))
            if rise_ft:
                cbasis += (f"; drawn ink rises {rise_ft} ft above the "
                           "plate closure — above-plate area carried "
                           "(previously dropped)")
            if spec["tier"] == "contested_pick_larger":
                cbasis += ("; this face's scale stays CONTESTED ("
                           + " vs ".join(spec.get("contested_rails")
                                         or []) +
                           ") — wall sections shift with the "
                           "contestant, the chase width is fixed "
                           "either way")
            cdoc = {
                **{k: v for k, v in doc.items() if k != "_id"},
                "id": str(uuid.uuid4()),
                "face_id": f"chase:{face_to_id[face]}",
                "vertices_pct": [[cx0 / 100.0, top_pct / 100.0],
                                 [cx1 / 100.0, top_pct / 100.0],
                                 [cx1 / 100.0, y_bot],
                                 [cx0 / 100.0, y_bot]],
                "basis": cbasis,
                "band_note": None,
                "geometry_tier": "chase_outline",
                "proposed_from": {
                    **doc["proposed_from"], "wall_section": None,
                    "geometry_tier": "chase_outline",
                    "chase": {**c2,
                              "width_ft": width_ft,
                              "width_source": ("human" if hd
                                               else "drawn"),
                              "rise_above_plate_ft": rise_ft,
                              "human_dimension": ({
                                  "value_ft": hd.get("value_ft"),
                                  "basis": hd.get("basis"),
                                  "supplied_by": hd.get("supplied_by")}
                                  if hd else None)}}}
            await db.pdf_overlay_polygons.insert_one(cdoc)
            created.append({k: v for k, v in cdoc.items()
                            if k != "_id"})
        # partition payload — sums to the face BY CONSTRUCTION
        if chase_list:
            part = {"face_id": face_to_id[face],
                    "kind": ("interrupting" if inter_chs else "edge"),
                    # SEND-96 order item 2 — visible UNPRICED note; no
                    # corner-count change (Ruling G).
                    "corner_note": (
                        "each chase carries 4 corner verticals running "
                        "its height — UNPRICED note, corner count "
                        "unchanged"),
                    "contested": spec["tier"] == "contested_pick_larger",
                    "contested_rails": spec.get("contested_rails"),
                    "parts": [], "sums_exact": None,
                    "above_plate_recovered_sqft":
                        (round(sum(recovered_sqft), 2)
                         if recovered_sqft else None),
                    "notes": []}
            bs = lw.get("body_x_span") or lw["x_span"]
            if not inter_chs:
                sil_h = round((lw["x_span"][1] - lw["x_span"][0]) * 100)
                wall_h = round((bs[1] - bs[0]) * 100)
                ch_hs = [round(abs(c2["x_wall"] - c2["x_proj"]) * 100)
                         for c2 in chase_list if c2["kind"] == "edge"]
                part["parts"] = [
                    {"surface": "wall (body)", "pct": wall_h / 100.0,
                     "ft": (round(wall_h / 100.0 * fpp_x, 2)
                            if fpp_x else None)}] + [
                    {"surface": "chase", "pct": ch / 100.0,
                     "ft": (round(ch / 100.0 * fpp_x, 2)
                            if fpp_x else None),
                     "width_source": "drawn"} for ch in ch_hs]
                part["face_pct"] = sil_h / 100.0
                part["sums_exact"] = (wall_h + sum(ch_hs) == sil_h)
            elif len(inter_chs) == 1 and fpp_x:
                c2 = inter_chs[0]
                face_h = round((lw["x_span"][1] - lw["x_span"][0])
                               * fpp_x * 100)
                hd = chase_width_by_face.get(face_to_id[face])
                chase_h = (round(float(hd["value_ft"]) * 100) if hd
                           else round((c2["x_inner"][1]
                                       - c2["x_inner"][0])
                                      * fpp_x * 100))
                drawn_rem = ((lw["x_span"][1] - lw["x_span"][0])
                             - (c2["x_inner"][1] - c2["x_inner"][0]))
                ratio_l = (((c2["x_inner"][0] - lw["x_span"][0])
                            / drawn_rem) if drawn_rem else 0.5)
                wl, cc, wr = _chase_partition(face_h, chase_h, ratio_l)
                part["parts"] = [
                    {"surface": "wall", "ft": wl / 100.0},
                    {"surface": "chase", "ft": cc / 100.0,
                     "width_source": "human" if hd else "drawn",
                     "drawn_inner_ft": round((c2["x_inner"][1]
                                              - c2["x_inner"][0])
                                             * fpp_x, 2),
                     "drawn_outer_ft": round((c2["x_outer"][1]
                                              - c2["x_outer"][0])
                                             * fpp_x, 2)},
                    {"surface": "wall", "ft": wr / 100.0}]
                part["face_ft"] = face_h / 100.0
                part["sums_exact"] = (wl + cc + wr == face_h)
                if hd:
                    part["chase_width_basis"] = hd.get("basis")
            else:
                part["notes"].append(
                    "no evidence scale (or multiple chases) — parts "
                    "reported in pct on the zones themselves")
            partitions[face_to_id[face]] = part
        # SEND-68 — GABLE STARTING SHAPES. Only faces the roof read says
        # carry a gable end (the walk detail row derived a gable or
        # named its refusal). A band_rectangle-style STARTING SHAPE that
        # states plainly the triangle could not be read — NO triangle
        # computed from pitch and width (a computed triangle would be a
        # derived shape wearing a measured shape's clothes; the 0.70
        # convention lives on the derived side and stays there).
        walk = ((est.get("hover_measurements") or {})
                .get("_wall_walk_detail") or [])
        wrow = next((d for d in walk if isinstance(d, dict)
                     and str(d.get("label") or "").lower()
                     == face_to_id[face]), None)
        carries_gable = bool(wrow and (
            float(wrow.get("gable_sqft") or 0) > 0
            or wrow.get("gable_refusal")))
        if carries_gable:
            plate = geo.get("top_of_plate")
            if not plate:
                skipped.append({
                    "face_id": f"gable:{face_to_id[face]}",
                    "reason": ("gable starting shape needs the TOP OF "
                               "PLATE datum on this drawing — not "
                               "located")})
            else:
                g_derived = (round(float(wrow["gable_sqft"]), 2)
                             if float(wrow.get("gable_sqft") or 0) > 0
                             else None)
                # SEND-71 item 5 — GABLE LINE-WORK: trace the drawn
                # triangle where the wall outline resolved (the read
                # earned the extension). Refusal keeps the SEND-68
                # starting rectangle and says why.
                g_read = None
                if (lw.get("status") == "RESOLVED"
                        and lw.get("wall_corners") and lw_ctx):
                    try:
                        g_read = gable_triangle_from_segments(
                            seg_cache[lw_ctx[0]], (band[0], band[1]),
                            (top_d["b0"], top_d["b1"]),
                            lw["wall_corners"], lw["y_top"], lw_ctx[1])
                    except Exception as e:
                        g_read = {"status": "INDETERMINATE",
                                  "reason": f"gable read failed: {e}"}
                if g_read and g_read.get("status") == "RESOLVED":
                    g_verts = [[round(v[0], 4), round(v[1], 4)]
                               for v in g_read["vertices_pct"]]
                    g_tier = "gable_outline"
                    traced = (polygon_sqft_from_scale(
                        g_verts, scale_ref, page.get("page_w"),
                        page.get("page_h")) if scale_ref else None)
                    g_basis = (
                        "GABLE TRACED FROM LINE-WORK — base: the drawn "
                        "wall corners at the plate-level closure; sides: "
                        "the drawn rakes (each passes within a joint of "
                        "its wall corner); apex: their drawn "
                        f"intersection at x={g_read['apex'][0]}%, "
                        f"y={g_read['apex'][1]}%. No triangle computed "
                        "from pitch and width")
                    # SEND-74 — TRACED basis, mandated sentence first.
                    g_basis_kind = GABLE_BASIS_TRACED
                    g_basis_lab = gable_basis_label(GABLE_BASIS_TRACED,
                                                    traced)
                    if traced is not None and g_derived is not None:
                        notice = (g_basis_lab
                                  + f"; this face's gable derives at "
                                  f"{g_derived} ft² (the 0.70 field "
                                  "factor carries the safety margin — "
                                  "the traced figure is the drawn "
                                  "triangle)")
                    elif g_derived is not None:
                        notice = (g_basis_lab
                                  + f"; this face's gable derives at "
                                  f"{g_derived} ft²")
                    else:
                        notice = (g_basis_lab
                                  + "; no derived gable figure exists ("
                                  + str(wrow.get("gable_refusal")) + ")")
                else:
                    g_top = round(band[0] / 100.0, 4)
                    g_bot = round(plate["y"] / 100.0, 4)
                    g_verts = [[x0, g_top], [x1, g_top],
                               [x1, g_bot], [x0, g_bot]]
                    g_tier = "gable_rectangle"
                    # SEND-74 — a starting rectangle is a shape, not a
                    # quantity; the QUANTITY alongside is the derived
                    # gable, which always carries the FIELD FACTOR basis
                    # (the derived path never traces).
                    g_basis_kind = (GABLE_BASIS_FIELD_FACTOR
                                    if g_derived is not None else None)
                    g_basis_lab = (
                        gable_basis_label(GABLE_BASIS_FIELD_FACTOR)
                        if g_derived is not None else None)
                    g_basis = (
                        "GABLE STARTING SHAPE — the roof read puts "
                        "a gable end on this face; the triangle "
                        "could not be read from the drawing, and "
                        "no triangle is computed from pitch and "
                        "width. bottom: TOP OF PLATE datum, this "
                        "elevation (the body zone's top); top: top "
                        "of this face's drawing band — the ridge "
                        "could not be read from the drawing; "
                        "sides: the body zone's span, same basis")
                    if g_read:
                        g_basis += ("; gable line-work refused: "
                                    + str(g_read.get("reason")))
                    if g_derived is not None:
                        notice = (f"this face's gable already derives at "
                                  f"{g_derived} ft². This starting "
                                  "rectangle is larger than the gable "
                                  "and will OVERSTATE it if confirmed — "
                                  "pull it in to the roof line first.")
                    else:
                        notice = ("this face's gable area is not "
                                  "derivable ("
                                  + str(wrow.get("gable_refusal"))
                                  + ") — this rectangle is still larger "
                                  "than the gable triangle and will "
                                  "OVERSTATE it if confirmed as-is; pull "
                                  "it in to the roof line first.")
                gdoc = {
                    "id": str(uuid.uuid4()),
                    "estimate_id": est_id,
                    "page": int(spec["page"]),
                    "face_id": f"gable:{face_to_id[face]}",
                    "material_class": "siding",
                    "vertices_pct": g_verts,
                    "scale_ref": scale_ref,
                    "page_w_px": page.get("page_w"),
                    "page_h_px": page.get("page_h"),
                    "sqft": None,
                    "derived_baseline_qty": None,
                    "surface_derived_sqft": None,
                    "surface_refusal": None,
                    "provenance": "proposed",
                    "qty_src": "proposed",
                    "tier": g_tier,
                    "geometry_tier": g_tier if g_tier == "gable_outline"
                                     else "datum_span",
                    "derived_gable_sqft": g_derived,
                    # SEND-74 — the gable basis is a strict binary and
                    # rides the proposal to the editor surface.
                    "gable_basis": g_basis_kind,
                    "gable_basis_label": g_basis_lab,
                    "divergence_notice": notice,
                    "basis": g_basis,
                    "band_note": None,
                    "proposed_from": {
                        "run_id": (run or {}).get("run_id"),
                        "tier": g_tier,
                        "band": band,
                        "derived_gable_sqft": g_derived,
                        "gable_refusal": wrow.get("gable_refusal"),
                        "gable_linework": (
                            {"status": g_read.get("status"),
                             "reason": g_read.get("reason"),
                             "apex": g_read.get("apex"),
                             "n_diagonals": g_read.get("n_diagonals")}
                            if g_read else
                            {"status": "NOT_ATTEMPTED",
                             "reason": ("wall outline not resolved on "
                                        "this drawing — the gable read "
                                        "only extends a trusted wall "
                                        "read")}),
                        "span_x_pct": [round(x0 * 100, 2),
                                       round(x1 * 100, 2)]},
                    "author_id": "height_build",
                    "author_email": "",
                    "created_at": now,
                    "updated_at": now,
                }
                await db.pdf_overlay_polygons.insert_one(gdoc)
                created.append({k: v for k, v in gdoc.items()
                                if k != "_id"})
    for c in created:
        c["created_at"] = str(c["created_at"])
        c["updated_at"] = str(c["updated_at"])
    # ── SEND-96 item 1 — a model-claimed chase with no locatable ink
    # REFUSES into a surface that still exists and stays bindable
    # (the SEND-48 lesson: refused surfaces must leave Howard
    # somewhere to draw).
    _claimed = (((run or {}).get("result") or {}).get("raw_ai")
                or {}).get("appendages") or []
    _chase_created = {str(c.get("face_id")) for c in created
                      if str(c.get("face_id") or "").startswith("chase:")}
    _wall_map = {"front": "front", "rear": "back", "back": "back",
                 "left": "left", "right": "right"}
    for ap in _claimed:
        if not isinstance(ap, dict):
            continue
        try:
            _fs = float(ap.get("faces_sqft") or 0)
        except (TypeError, ValueError):
            _fs = 0.0
        if _fs <= 0:
            continue
        _w = str(ap.get("wall") or "?").lower()
        _fid = "chase:" + _wall_map.get(_w, _w)
        if _fid in _chase_created:
            continue
        skipped.append({
            "face_id": _fid,
            "reason": (
                f"REFUSED — the run claims a "
                f"{str(ap.get('kind') or 'chase').replace('_', ' ')} of "
                f"{_fs:.0f} ft² on this wall; no chase ink locatable on "
                "any evaluable face — the claim is hypothesis only and "
                "feeds nothing; the chase surface still exists and "
                "stays bindable — draw a zone to bind it")})
    _rec_total = round(sum((p.get("above_plate_recovered_sqft") or 0)
                           for p in partitions.values()), 2)
    return {"ok": True, "proposed": created, "skipped": skipped,
            # SEND-90 — RULING XX width cross-check: flagged on the
            # payload, never auto-resolved; magnitude, never a boolean.
            "width_cross_check": _xx_width_cross_check(xx_verdict,
                                                       xx_sides),
            # SEND-94 — the partition per face: sums to the face by
            # construction; chase provenance stated, never laundered.
            "partitions": partitions,
            # SEND-96 item 3 — warn, never move silently: the recovery
            # enters a quantity ONLY through a human-confirmed chase
            # zone; this names the jump before anyone confirms one.
            "recovery_warning": (
                (f"the chase partition newly carries {_rec_total} ft² "
                 "of above-plate chase area on this estimate — nothing "
                 "moves until a human confirms a chase zone (proposals "
                 "feed no quantity); confirming them will raise the "
                 "siding takeoff by about that much")
                if _rec_total else None),
            "note": ("proposed zones are PROVISIONAL — they feed no "
                     "quantity until a human confirms or bumps them")}


@router.get("/estimates/{est_id}/pdf-overlay/height-cards")
async def height_cards(est_id: str,
                       user: dict = Depends(get_current_user)):
    """SEND-96 order item 3 — HEIGHT CARDS: every refusing face gets a
    plain, printable card saying what to tape. A card is a field
    instruction, never a quantity — the tape's figure comes back as a
    human dimension."""
    await _est_or_404(est_id, user)
    ot, run = await _latest_ocr(est_id)
    if not ot:
        return {"cards": [], "note": "no blueprint run on this estimate"}
    from height_read import derive_face_heights
    faces = derive_face_heights(ot)
    cards = []
    for face in ("front", "rear", "left", "right"):
        r = faces.get(face) or {}
        spec = _best_ladder_spec(r)
        if spec and spec.get("tier") == "derived_chain":
            continue                       # the face derives — no card
        refusal = str(r.get("refusal") or r.get("reason") or "")
        page = (spec or {}).get("page") or r.get("page")
        if spec and spec.get("tier") == "contested_pick_larger":
            rails = " vs ".join(spec.get("contested_rails") or [])
            kind = "contested"
            refusal = (f"the print carries two figures ({rails}) and "
                       "the app may not choose between them")
            tape = ("Tape ONE height on this wall: hook at the TOP OF "
                    "PLATE line, read at the FIRST FLOOR line. The "
                    f"tape decides between {rails}.")
        elif "Two different wall heights" in refusal:
            kind = "conflicting_heights"
            tape = ("The print shows two conflicting wall heights on "
                    "this elevation. Tape plate-to-floor ONCE at this "
                    "wall — the tape decides which figure is real.")
        elif "UNDIMENSIONED" in refusal:
            kind = "undimensioned_band"
            tape = ("One band of this wall is printed with NO "
                    "dimension. Tape the wall from TOP OF PLATE down "
                    "to FIRST FLOOR in one pull — the missing band is "
                    "inside that pull.")
        elif "no FIRST FLOOR datum" in refusal or "datum" in refusal:
            kind = "no_datum"
            tape = ("The drawing gives no usable floor line on this "
                    "face. Tape the full wall height — grade to top "
                    "of wall — and write the figure on this card.")
        else:
            kind = "refused"
            tape = ("Tape the wall from TOP OF PLATE to FIRST FLOOR "
                    "at this face and write the figure on this card.")
        cards.append({"face": face, "page": page, "kind": kind,
                      "refusal": refusal or "height not established",
                      "tape": tape})
    return {"cards": cards,
            "note": ("a card is a field instruction, never a quantity "
                     "— the taped figure enters as a human dimension")}


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


async def reapply_overlay_law(est_id: str, lines: list[dict]) -> list[dict]:
    """SEND-79 Item 1 (authorized) — THE LAW SURVIVES BY CONSTRUCTION.
    Every rebuild door re-RUNS the overlay law over the fresh lines
    instead of carrying markers across a merge: a copied marker is one
    refactor away from being dropped again; a re-run law cannot lose
    what it recomputes. Called by every path that rebuilds lines from a
    derivation before it writes them (pinned structurally in
    tests/test_overlay_rederive_2026_08_21_send79.py)."""
    all_polys: list[dict] = []
    async for row in db.pdf_overlay_polygons.find(
        {"estimate_id": est_id}, {"_id": 0}
    ):
        all_polys.append(row)
    if not all_polys:
        return lines
    return apply_overlay_to_takeoff(lines, all_polys)


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
