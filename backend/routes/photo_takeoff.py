"""PHOTO TAKEOFF — marks on the photo itself (Howard ruled 2026-08-26,
pro-quote SEND-131A).

The contractor works on the PHOTOS, not on generated elevation renders.
The discipline is the blueprint discipline, carried over verbatim:

  · EVIDENCE ON THE PHOTO. A mark is geometry drawn on that photo, stored
    in that photo's NATURAL PIXELS. Nothing is inferred from another
    photo, another face or another estimate.
  · PROVISIONAL UNTIL CONFIRMED. Every mark lands `provisional`. A
    provisional mark NEVER contributes a quantity — it is listed, named
    and waiting. NO SILENT QUANTITY FROM AN UNCONFIRMED MARK.
  · SCALE IS LOCAL TO THE PHOTO. Either the two-tap known-span ANCHOR or
    a typed TAPE figure on that photo. WHERE A TAPE IS PRESENT, THE TAPE
    WINS. No anchor and no tape → no quantity on that photo, and the
    refusal is named (never a zero).
  · CONFIRMED MARKS WRITE QUANTITY, NOT MONEY. ft², LF and counts land on
    the estimate under the photo lane's own keys; no priced line, no
    price key, no money is touched here. Money depends on the product and
    stays outside this path.
  · 423 ON PROTECTED ESTIMATES for the derived write (apply), exactly as
    the blueprint lane does.

PHASE 1 (the ft² spine): siding zones, non-siding zones, openings.
PHASE 2 (SEND-143, 2026-08-28 — LINEAR RUNS FROM MARKS ALREADY DRAWN):
J-channel measures the perimeter of the box drawn round each opening, and
the GABLE RAKE measures the two sloped lines drawn with each gable
triangle. Outside/inside corners, starter, soffit and horizontal fascia
have NOTHING to read yet (there is no corner tick, no wall-base mark and
no eave mark) — their rows still appear and NAME the missing mark. No mark
type is invented, and no linear run is derived from a figure the
contractor did not draw.
"""
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from photo_zone_proposals import (propose_zones_for_photo,
                                  rebase_zones_for_photo)
from untouchable import is_untouchable

router = APIRouter(tags=["photo-takeoff"])

# PHASE 1 kinds only. A kind outside this set is refused, not guessed —
# phase 2 adds the linear runs.
AREA_KINDS = {"siding_zone", "non_siding_zone"}
OPENING_KINDS = {"opening"}
# SEND-139 (Howard ruled 2026-08-27) — THE GABLE AND DORMER TOOLS MOVE
# HERE FROM THE ANNOTATOR. Ported, not reinvented: the same drawing
# gesture (gable = LEFT EAVE → PEAK → RIGHT EAVE, dormer = the four
# corners of the vertical face), the same typed fields (symmetric, pitch,
# dormer depth), the same masking rule. The NUMBER obeys the SEND-137
# gable ruling: ½ × width × rise where both exist, and a NAMED REFUSAL
# where either does not. No 0.70 comes across (the annotator's drawn
# gable never used it — see the send-139 report).
GABLE_KINDS = {"gable", "dormer"}
# SEND-147 (Howard ruled 2026-08-28) — THE WALL-BASE MARK. HUMAN TWO-TAP,
# NO DETECTOR. The same gesture as the two-tap scale, on THAT photo only:
# tap 1 = the LEFT end of the starter / wall base, tap 2 = the RIGHT end.
# It stores `a`, `b` and its `y` in this photo's own natural pixels and it
# writes NO LF and no price — THIS IS AN ANCHOR, NOT A TRIM TAKEOFF. The
# phase-2 `starter` RUN stays unbuilt and still refuses by name.
# SEND-149 (Howard ruled 2026-08-29) — THE EAVE MARK. The same two-tap, the
# same discipline, for the OTHER end of the wall: tap 1 = the LEFT end of the
# eave / frieze, tap 2 = the RIGHT end. It sets the BODY TOP and it carries no
# LF either. Soffit, fascia, corner ticks and J-channel are NOT in this send.
ANCHOR_KINDS = {"wall_base", "eave"}
PHASE1_KINDS = AREA_KINDS | OPENING_KINDS | GABLE_KINDS | ANCHOR_KINDS
# Exact point counts — a gable is a triangle, a dormer face is a quad and a
# wall base is the two ends of one line. A wrong count is refused by name,
# never padded or truncated.
KIND_POINTS = {"gable": 3, "dormer": 4, "wall_base": 2, "eave": 2}
# The annotator's own pitch presets, carried over verbatim.
GABLE_PITCH_PRESETS = (4, 5, 6, 7, 8, 9, 10, 12)
GABLE_PITCH_MIN = 3
GABLE_PITCH_MAX = 18
PHASE2_KINDS = {"outside_corner", "inside_corner", "j_channel", "starter",
                "soffit", "fascia", "finish_trim"}
NON_SIDING_CATEGORIES = {"brick", "stone", "stucco", "garage_door", "other"}
STATUSES = {"provisional", "confirmed", "refused"}

# SEND-132 — ONE EDITOR, TWO STAGES. Provenance never launders:
#   contractor_stage1     drawn before any AI read on this photo — GUIDANCE
#   imported_annotation   pulled in from the pre-AI annotator — GUIDANCE
#   ai_proposal           minted from a completed read on THIS photo
#   contractor_stage2     drawn by hand after the read (what the AI missed)
ORIGINS = {"contractor_stage1", "imported_annotation", "ai_proposal",
           "contractor_stage2", "ai_zone_proposal"}
GUIDANCE_ORIGINS = {"contractor_stage1", "imported_annotation"}
# The body-siding sections a zone's product may come from. Accessories,
# soffit and trim are NOT body products and are never offered.
BODY_SECTION_EXCLUDE = ("accessor", "soffit", "fascia", "trim", "labor",
                        "install", "misc")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _wall_base_record(pts: List[dict]) -> dict:
    """SEND-147 — THE START LINE GETS ITS OWN STORED y. `a` and `b` are the
    two taps exactly as they landed, in this photo's natural pixels; `y` is
    the mean of their two y's, and it is the ONE number the body bottom
    reads. Nothing here is a length: no LF is written and no price exists."""
    a, b = ({"x": float(pts[0]["x"]), "y": float(pts[0]["y"])},
            {"x": float(pts[1]["x"]), "y": float(pts[1]["y"])})
    if b["x"] < a["x"]:                       # a is the LEFT end, always
        a, b = b, a
    return {"a": a, "b": b, "y": round((a["y"] + b["y"]) / 2.0, 3),
            "units": "natural pixels of this photo",
            "tilt_px": round(abs(b["y"] - a["y"]), 3)}


EAVE_BASIS = (
    "EAVE — the frieze line you tapped on THIS photo. It stores its two ends "
    "and its own y in this photo's natural pixels, and it is an ANCHOR, NOT A "
    "TRIM RUN: no LF is written for it, it is never priced, and it is never "
    "copied to another photo or another face. While it exists, the AI body "
    "zone's TOP on this photo comes from this line. It is not a soffit and it "
    "is not a fascia — neither of those is built.")


WALL_BASE_BASIS = (
    "WALL BASE — the start line you tapped on THIS photo. It stores its two "
    "ends and its own y in this photo's natural pixels, and it is an ANCHOR, "
    "NOT A TRIM RUN: no LF is written for it, it is never priced, and it is "
    "never copied to another photo or another face. While it exists, the AI "
    "body zone's BOTTOM on this photo comes from this line.")


class Point(BaseModel):
    x: float
    y: float


class MarkIn(BaseModel):
    photo_key: str
    kind: str
    shape: str = "poly"                     # poly | rect | point
    points: List[Point] = Field(default_factory=list)
    category: Optional[str] = None          # non-siding: brick/stone/...
    label: Optional[str] = None
    source: str = "human"                   # human | imported_annotation
    # STAGE 1 GUIDANCE CLAIMS (openings): what the contractor knows and
    # the AI should read. They are NOT quantity inputs — ft² comes from
    # the drawn geometry and this photo's own scale, never from these.
    style: Optional[str] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    # body-siding product for a zone — only a product already on the job
    product: Optional[str] = None
    # SEND-139 — GABLE fields, ported from the annotator. `symmetric`
    # mirrors the peak to the base midpoint; `pitch_set` records the
    # preset the contractor picked (the rise it implies is in the
    # geometry, never a second stored number).
    symmetric: Optional[bool] = None
    pitch_set: Optional[float] = None
    # DORMER DEPTH — TYPED, NEVER PHOTO-DERIVED. Untyped → the cheeks
    # REFUSE (no default depth is invented here).
    depth_ft: Optional[float] = None


class MarkPatch(BaseModel):
    points: Optional[List[Point]] = None
    category: Optional[str] = None
    label: Optional[str] = None
    status: Optional[str] = None            # confirmed | refused | provisional
    refused_reason: Optional[str] = None
    style: Optional[str] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    # A PRODUCT CHANGE ALTERS THE OUTPUT, NOT THE GEOMETRY — it is
    # recorded and it does NOT drop a confirmed mark to provisional.
    product: Optional[str] = None
    symmetric: Optional[bool] = None
    pitch_set: Optional[float] = None
    depth_ft: Optional[float] = None


class ScaleIn(BaseModel):
    photo_key: str
    # the two-tap known span, in this photo's natural pixels
    anchor: Optional[Dict[str, Any]] = None      # {p1:{x,y}, p2:{x,y}, inches}
    # a typed tape figure for the same span — THE TAPE WINS
    tape_inches: Optional[float] = None
    clear: bool = False


async def _est_or_404(est_id: str, user: dict) -> dict:
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0})
    if not est:
        raise HTTPException(status_code=404, detail="Not found")
    return est


def _poly_area_px(points: List[dict]) -> float:
    if len(points) < 3:
        return 0.0
    a = 0.0
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        a += float(p["x"]) * float(q["y"]) - float(q["x"]) * float(p["y"])
    return abs(a) / 2.0


def _centroid(points: List[dict]) -> dict:
    n = len(points)
    return {"x": sum(float(p["x"]) for p in points) / n,
            "y": sum(float(p["y"]) for p in points) / n}


def _point_in_triangle(pt: dict, tri: List[dict]) -> bool:
    def sign(p1, p2, p3):
        return ((float(p1["x"]) - float(p3["x"])) * (float(p2["y"]) - float(p3["y"]))
                - (float(p2["x"]) - float(p3["x"])) * (float(p1["y"]) - float(p3["y"])))
    a, b, c = tri
    d1, d2, d3 = sign(pt, a, b), sign(pt, b, c), sign(pt, c, a)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def _point_in_polygon(pt: dict, pts: List[dict]) -> bool:
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = float(pts[i]["x"]), float(pts[i]["y"])
        xj, yj = float(pts[j]["x"]), float(pts[j]["y"])
        if ((yi > pt["y"]) != (yj > pt["y"])
                and pt["x"] < (xj - xi) * (pt["y"] - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _masked_sqft(container: List[dict], masks: List[dict], ipp: float,
                 inside) -> float:
    """The annotator's own masking rule, ported: a NO-SIDING mask whose
    CENTROID sits inside the shape subtracts its own area. Only CONFIRMED
    masks subtract — a provisional mark carries no quantity anywhere in
    this editor, and it may not silently reduce one either."""
    px = 0.0
    for m in masks:
        pts = m.get("points") or []
        if len(pts) < 3:
            continue
        if inside(_centroid(pts), container):
            px += _poly_area_px(pts)
    return px * ((ipp * ipp) / 144.0)


def _gable_figure(mark: dict, masks: List[dict],
                  ipp: Optional[float]) -> dict:
    """THE GABLE, PORTED FROM THE ANNOTATOR (SEND-139) AND RULED BY
    SEND-137: pts = [LEFT EAVE, PEAK, RIGHT EAVE] in this photo's own
    pixels. Base = the eave-point span. Rise = the PERPENDICULAR distance
    from the peak to the eave line (the eave line may tilt a touch; the
    perpendicular keeps it honest). Pitch is scale-free.

        AREA = ½ × width × rise

    and NOTHING ELSE. Where width or rise is missing the gable REFUSES BY
    NAME — never a 0, and never the retired 0.70 factor on an unmeasured
    triangle."""
    pts = mark.get("points") or []
    # SEND-140 — THE REFUSAL RECEIPT. Every refusal already names its
    # reason; `receipt` adds ONE contractor sentence naming THE ACTUAL
    # MISSING FIELD and what to tape for it. It never invents a number,
    # never mentions a factor, and never points at another photo or
    # another face. A measured gable carries NO receipt.
    out: Dict[str, Any] = {"base_ft": None, "rise_ft": None, "pitch": None,
                           "gross_sqft": None, "masked_sqft": None,
                           "sqft": None, "refusal": None, "receipt": None,
                           "pitch_warning": None}
    if len(pts) != 3:
        out["refusal"] = ("a gable is a triangle: LEFT EAVE, PEAK, RIGHT "
                          "EAVE — this mark carries "
                          f"{len(pts)} point(s), so it has no width and no "
                          "rise. REFUSED, never a 0")
        out["receipt"] = ("Trace left eave, peak, and right eave — this mark "
                          f"is not a triangle yet ({len(pts)} of 3 points).")
        return out
    L, P, R = pts
    base_px = ((float(R["x"]) - float(L["x"])) ** 2
               + (float(R["y"]) - float(L["y"])) ** 2) ** 0.5
    if base_px <= 0:
        out["refusal"] = ("the two eave points sit on top of each other — "
                          "this gable has NO WIDTH. ½ × width × rise cannot "
                          "be formed: REFUSED, never a 0")
        out["receipt"] = ("Re-tap the left and right eave points apart on "
                          "this photo — rise is known, width is not.")
        return out
    rise_px = abs((float(R["x"]) - float(L["x"])) * (float(L["y"]) - float(P["y"]))
                  - (float(L["x"]) - float(P["x"])) * (float(R["y"]) - float(L["y"]))
                  ) / base_px
    out["pitch"] = round((rise_px / (base_px / 2)) * 12, 1) if base_px else None
    if rise_px <= 0:
        out["refusal"] = ("the peak sits on the eave line — this gable has "
                          "NO RISE. An untraced gable has no area: REFUSED, "
                          "never a 0 and never a factor on an unmeasured "
                          "triangle")
        out["receipt"] = ("Measure the rise at the peak on this photo — "
                          "width is known, rise is not.")
        return out
    if out["pitch"] is not None and not (
            GABLE_PITCH_MIN <= out["pitch"] <= GABLE_PITCH_MAX):
        out["pitch_warning"] = (
            f"pitch {out['pitch']}/12 is outside the usual "
            f"{GABLE_PITCH_MIN}/12–{GABLE_PITCH_MAX}/12 range — check the "
            "tapped points. This is a warning, never a block")
    if not ipp:
        out["refusal"] = ("this gable is drawn but this photo carries no "
                          "scale — width and rise have no feet, so there is "
                          "no area. REFUSED, never a 0")
        out["receipt"] = ("Set the scale on this photo — tap both ends of a "
                          "span you measured and type its feet; the triangle "
                          "is already drawn.")
        return out
    base_ft = (base_px * ipp) / 12.0
    rise_ft = (rise_px * ipp) / 12.0
    gross = 0.5 * base_ft * rise_ft
    masked = _masked_sqft(pts, masks, ipp, _point_in_triangle)
    out.update({"base_ft": round(base_ft, 2), "rise_ft": round(rise_ft, 2),
                "gross_sqft": round(gross, 2),
                "masked_sqft": round(masked, 2) if masked > 0 else None,
                "sqft": round(max(0.0, gross - masked), 2)})
    return out


def _dormer_figure(mark: dict, masks: List[dict],
                   ipp: Optional[float]) -> dict:
    """THE DORMER FACE, PORTED FROM THE ANNOTATOR (SEND-139): pts =
    [BOTTOM-LEFT, BOTTOM-RIGHT, TOP-RIGHT, TOP-LEFT] of the VERTICAL
    face. Width and height AVERAGE the opposing edges, exactly as the
    annotator does. Face area = width × height, less masks inside.

    CHEEKS need a TYPED depth (2 × height × depth). The annotator
    substituted a 1.5 ft DEFAULT when the contractor typed nothing; that
    default does NOT come across — an untyped depth REFUSES the cheeks by
    name, the same way a missing rise refuses a gable."""
    pts = mark.get("points") or []
    out: Dict[str, Any] = {"width_ft": None, "height_ft": None,
                           "gross_sqft": None, "masked_sqft": None,
                           "sqft": None, "cheek_sqft": None,
                           "cheek_refusal": None, "cheek_receipt": None,
                           "refusal": None, "receipt": None}
    if len(pts) != 4:
        out["refusal"] = ("a dormer face is a quad: bottom-left, "
                          "bottom-right, top-right, top-left — this mark "
                          f"carries {len(pts)} point(s). REFUSED, never a 0")
        out["receipt"] = ("Trace all four corners of the dormer face — this "
                          f"mark is not a face yet ({len(pts)} of 4 points).")
        return out
    bl, br, tr, tl = pts
    w_px = (((float(br["x"]) - float(bl["x"])) ** 2 + (float(br["y"]) - float(bl["y"])) ** 2) ** 0.5
            + ((float(tr["x"]) - float(tl["x"])) ** 2 + (float(tr["y"]) - float(tl["y"])) ** 2) ** 0.5) / 2
    h_px = (((float(tl["x"]) - float(bl["x"])) ** 2 + (float(tl["y"]) - float(bl["y"])) ** 2) ** 0.5
            + ((float(tr["x"]) - float(br["x"])) ** 2 + (float(tr["y"]) - float(br["y"])) ** 2) ** 0.5) / 2
    if w_px <= 0 or h_px <= 0:
        out["refusal"] = ("this dormer face has no width or no height — "
                          "REFUSED, never a 0")
        out["receipt"] = ("Re-tap the dormer corners apart on this photo — "
                          "two of them landed on the same spot.")
        return out
    if not ipp:
        out["refusal"] = ("this dormer is drawn but this photo carries no "
                          "scale — no feet, no area. REFUSED, never a 0")
        out["receipt"] = ("Set the scale on this photo — tap both ends of a "
                          "span you measured and type its feet; the face is "
                          "already drawn.")
        return out
    w_ft = (w_px * ipp) / 12.0
    h_ft = (h_px * ipp) / 12.0
    gross = w_ft * h_ft
    masked = _masked_sqft(pts, masks, ipp, _point_in_polygon)
    depth = mark.get("depth_ft")
    try:
        depth = float(depth) if depth not in (None, "") else None
    except (TypeError, ValueError):
        depth = None
    if depth and depth > 0:
        out["cheek_sqft"] = round(2 * h_ft * depth, 2)
    else:
        out["cheek_refusal"] = ("dormer depth is not typed — the cheeks "
                                "REFUSE. Depth is measured on the roof, "
                                "never read off the photo, and no default "
                                "depth is invented here")
        out["cheek_receipt"] = ("Type the dormer depth in feet — the face is "
                                "drawn, cheeks cannot be counted without it.")
    out.update({"width_ft": round(w_ft, 2), "height_ft": round(h_ft, 2),
                "gross_sqft": round(gross, 2),
                "masked_sqft": round(masked, 2) if masked > 0 else None,
                "sqft": round(max(0.0, gross - masked), 2)})
    return out


def _in_per_px(scale: Optional[dict]) -> tuple[Optional[float], str]:
    """THE TAPE WINS. Returns (inches per pixel, source|refusal)."""
    if not scale:
        return None, ("no scale on this photo — set the two-tap anchor or "
                      "type the tape figure; no scale, no quantity")
    span_px = float(scale.get("span_px") or 0)
    if span_px <= 0:
        return None, ("the scale span has no pixel length on this photo — "
                      "re-tap the two ends")
    tape = scale.get("tape_inches")
    if tape:
        return float(tape) / span_px, "tape"
    inches = (scale.get("anchor") or {}).get("inches")
    if inches:
        return float(inches) / span_px, "anchor"
    return None, ("the scale span is drawn but carries no length — type the "
                  "tape figure or the anchor's real span")


def _mark_public(m: dict) -> dict:
    return {k: v for k, v in m.items() if k not in ("_id", "company_id")}


def _run_photo_names(run: dict) -> List[str]:
    return [n for n in str(run.get("photo_paths") or "").split(",") if n]


async def _photo_read(est_id: str, photo_key: str) -> Optional[dict]:
    """THE STAGE IS PER PHOTO (Howard ruled 2026-08-26, SEND-132): a
    completed read on ANOTHER photo unlocks nothing here. Returns the
    latest done run that actually carried THIS photo, or None."""
    async for run in db.ai_measure_runs.find(
            {"estimate_id": est_id, "status": "done"},
            sort=[("created_at", -1)]).limit(25):
        if photo_key in _run_photo_names(run):
            return run
    return None


def _stage_block(run: Optional[dict], photo_key: str) -> dict:
    if not run:
        return {
            "stage": 1,
            "ai_read": None,
            "stage_note": ("STAGE 1 — BEFORE AI. Marks here are GUIDANCE: "
                           "the AI reads them, they do not price anything. "
                           "Confirming one still writes quantity, and the "
                           "record says it was confirmed with no AI read on "
                           "this photo."),
            "proposals_refusal": ("no completed AI read carries this photo — "
                                  "Stage 2 is not unlocked here; a read on "
                                  "another photo unlocks nothing on this one"),
        }
    return {
        "stage": 2,
        "ai_read": {
            "run_id": run.get("run_id"),
            "completed_at": (run.get("completed_at").isoformat()
                             if hasattr(run.get("completed_at"), "isoformat")
                             else run.get("completed_at")),
            "photo_index": _run_photo_names(run).index(photo_key),
        },
        "stage_note": ("STAGE 2 — AFTER AI. Pull the read's proposals, then "
                       "confirm, adjust, refuse or delete each one and add "
                       "what it missed. A confirm here is EVIDENCE."),
        "proposals_refusal": None,
    }


def _job_body_products(est: dict) -> List[dict]:
    """ONLY BODY-SIDING PRODUCTS ALREADY ON THIS JOB (ruled). Accessories,
    soffit, fascia, trim, labour and misc are not body products and are
    never offered. No catalog, no invention — an empty list says so."""
    out: List[dict] = []
    seen = set()
    for ln in (est.get("lines") or []):
        section = str(ln.get("section") or "")
        name = str(ln.get("name") or "").strip()
        low = section.lower()
        if "siding" not in low or not name:
            continue
        if any(tok in low for tok in BODY_SECTION_EXCLUDE):
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "tab": ln.get("tab"), "section": section,
                    "unit": ln.get("unit")})
    return out


def _photo_natural_size(photo_key: str) -> Optional[tuple[float, float]]:
    """The read's boxes are NORMALISED; they land in this photo's own
    natural pixels or they do not land at all. No assumed size."""
    try:
        from PIL import Image
        from config import UPLOAD_DIR
        path = UPLOAD_DIR / photo_key
        if not path.exists():
            return None
        with Image.open(path) as im:
            w, h = im.size
        return (float(w), float(h)) if w and h else None
    except Exception:
        return None


def _origin_basis(origin: str, stage: int) -> str:
    if origin == "ai_zone_proposal":
        # SEND-144 — a STARTING ZONE read off a finished run. Its own basis
        # names the face's figures; this is the provenance line.
        return ("AI STARTING ZONE — shaped from the completed read's own "
                "figures for this face; provisional until the contractor "
                "moves it and rules on it")
    if origin == "ai_proposal":
        return ("AI PROPOSAL — minted from the completed read on this photo; "
                "provisional until the contractor rules on it")
    if origin == "contractor_stage2":
        return ("STAGE 2 — drawn by the contractor after the AI read on this "
                "photo (what the read missed)")
    if origin == "imported_annotation":
        return ("GUIDANCE — pulled in from the pre-AI annotator on this "
                "photo; the AI reads it, it prices nothing")
    return ("GUIDANCE — drawn before any AI read on this photo; the AI "
            "reads it, it prices nothing")


async def _validated_product(est: dict, name: str) -> str:
    """A zone may only carry a body-siding product ALREADY ON THIS JOB."""
    allowed = {p["name"] for p in _job_body_products(est)}
    if name not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(f"{name!r} is not a body-siding product on this job — "
                    f"the picker offers only {sorted(allowed)}; no catalog "
                    "product and no invented product may ride a zone"))
    return name


def _plane_basis(marks: List[dict], ipp: Optional[float]) -> dict:
    """BLOCK B ITEM 1+2 (Howard ruled 2026-08-27, SEND-136) — NAME THE
    PLANE. The ft² math is scaled-orthographic: one inches-per-pixel
    over the whole frame, `ipp²/144 × shoelace(px)`. That is only true of
    a wall square-on to the camera; on an oblique photo it measures the
    wall's PROJECTION. Until this send that assumption was SILENT. It is
    now stated on every figure, as one of exactly three values:

        SQUARE-ON   measured, with what earned it
        OBLIQUE     with the angle ONLY if the evidence gives one
        UNKNOWN     nothing on this photo supports a verdict

    THE CLASSIFIER USES ONLY MARKS ALREADY ON THE PHOTO:
      * a boxed opening's pixel aspect vs its typed aspect;
      * two boxed openings' inches-per-pixel disagreeing across depth;
      * converging verticals — NOT AVAILABLE: nothing in phase 1 traces
        a vertical line, so this test cannot run and says so.

    THERE IS NO DEFAULT THAT READS AS SQUARE-ON, and no correction
    factor is derived from any of this. A verdict is a label, never a
    multiplier.
    """
    ev: List[str] = []
    oblique: List[str] = []
    square: List[str] = []
    angle_deg = None
    boxed = [m for m in marks
             if m.get("kind") == "opening" and len(m.get("points") or []) >= 3]
    # (1) pixel aspect vs typed aspect
    for m in boxed:
        w_in = float(m.get("width_in") or 0)
        h_in = float(m.get("height_in") or 0)
        if w_in <= 0 or h_in <= 0:
            continue
        xs = [p["x"] for p in m["points"]]
        ys = [p["y"] for p in m["points"]]
        w_px = max(xs) - min(xs)
        h_px = max(ys) - min(ys)
        if w_px <= 0 or h_px <= 0:
            continue
        ratio = (w_px / h_px) / (w_in / h_in)
        tag = m.get("style") or m.get("label") or "opening"
        if abs(ratio - 1.0) <= 0.08:
            square.append(f"{tag}: drawn box matches its typed "
                          f"{w_in:g}×{h_in:g} in aspect within "
                          f"{abs(ratio - 1) * 100:.0f}%")
        elif ratio < 0.92:
            import math
            a = math.degrees(math.acos(max(0.0, min(1.0, ratio))))
            angle_deg = round(a, 1) if angle_deg is None else angle_deg
            oblique.append(f"{tag}: drawn box is horizontally compressed "
                           f"{(1 - ratio) * 100:.0f}% against its typed "
                           f"{w_in:g}×{h_in:g} in — a wall turned "
                           f"≈{a:.0f}° from the camera reads like this")
        else:
            oblique.append(f"{tag}: drawn box is {(ratio - 1) * 100:.0f}% "
                           f"wider than its typed {w_in:g}×{h_in:g} in "
                           "aspect — a turned wall or a tilted camera; the "
                           "angle is NOT stated because the two cannot be "
                           "told apart from this alone")
    # (2) two openings' inches-per-pixel across depth
    ipps = []
    for m in boxed:
        w_in = float(m.get("width_in") or 0)
        if w_in <= 0:
            continue
        xs = [p["x"] for p in m["points"]]
        w_px = max(xs) - min(xs)
        if w_px > 0:
            ipps.append((w_in / w_px, m.get("style") or m.get("label") or "opening"))
    if len(ipps) >= 2:
        lo = min(ipps)[0]
        hi = max(ipps)[0]
        spread = (hi / lo) if lo else 0
        if spread > 1.15:
            oblique.append(
                f"two boxed openings disagree on scale by {(spread - 1) * 100:.0f}%"
                f" ({lo:.3f} vs {hi:.3f} in/px) — the scale falls off across "
                "this frame, which one ruler cannot describe")
        elif spread <= 1.08:
            square.append(
                f"two boxed openings agree on scale within "
                f"{(spread - 1) * 100:.0f}% ({lo:.3f} vs {hi:.3f} in/px)")
    ev.append("converging verticals: NOT TESTED — phase 1 traces no "
              "vertical lines on the photo, so this test cannot run")
    if oblique:
        basis = "OBLIQUE"
        reason = ("OBLIQUE — this photo's own marks say the wall is turned "
                  "from the camera, so an area from it measures the wall's "
                  "PROJECTION, not the wall: " + "; ".join(oblique)
                  + (f". Angle indicated ≈{angle_deg}° (from the box "
                     "compression only)" if angle_deg is not None else
                     ". No angle is stated — the evidence does not give one")
                  + ". NO correction is applied: a perspective correction "
                    "from an unmeasured angle is a fabricated ruler.")
    elif square:
        basis = "SQUARE-ON"
        reason = ("SQUARE-ON — earned by this photo's own marks: "
                  + "; ".join(square)
                  + ". The area math (one inches-per-pixel over the frame) "
                    "holds on a wall square-on to the camera.")
    else:
        basis = "UNKNOWN"
        reason = ("UNKNOWN — nothing on this photo supports a verdict. No "
                  "boxed opening carries BOTH a typed width and height, and "
                  "no two boxed openings carry typed widths, so neither "
                  "aspect nor scale-falloff can be tested. The ft² here "
                  "assumes the wall is square-on to the camera; that "
                  "assumption is UNVERIFIED, and an oblique photo reads "
                  "LOW (≈13% at 30°, ≈29% at 45°). Box one window and type "
                  "its width and height to settle it.")
    return {"plane_basis": basis, "plane_basis_reason": reason,
            "plane_basis_evidence": (oblique + square + ev) or ev,
            "plane_basis_angle_deg": angle_deg}


def _seg_ft(a: dict, b: dict, ipp: float) -> float:
    """Length of a DRAWN segment in feet. Nothing here is derived from a
    typed figure — the contractor's own line is measured."""
    px = math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))
    return px * ipp / 12.0


def _perimeter_ft(pts: List[dict], ipp: float) -> float:
    n = len(pts)
    return sum(_seg_ft(pts[i], pts[(i + 1) % n], ipp) for i in range(n))


# PHASE 2 TRIM (Howard ruled 2026-08-28, SEND-143) — LINEAR RUNS FROM
# MARKS ALREADY DRAWN. Two lanes measure; the other four have NOTHING to
# read and say so on screen. The refusal names the missing MARK and what
# to draw — it is never a 0 and it is never hidden.
TRIM_REFUSALS = {
    "outside_corner": (
        "no corner is marked on this photo, and no wall here carries a "
        "confirmed height — mark the corner and measure that wall's height "
        "on this photo. No height is copied from another wall, another "
        "photo or another estimate"),
    "inside_corner": (
        "no corner is marked on this photo, and no wall here carries a "
        "confirmed height — mark the corner and measure that wall's height "
        "on this photo. No height is copied from another wall, another "
        "photo or another estimate"),
    "starter": (
        "no wall BASE is marked on this photo — a zone outline does not say "
        "which of its edges is the base, and the base may not be read off "
        "the plate line or the eave. Mark the base to measure starter"),
    "soffit": (
        "no EAVE is marked on this photo — the roof edge is not invented. "
        "Mark the eave to measure soffit"),
    "fascia": (
        "no EAVE is marked on this photo — the horizontal fascia run is not "
        "invented. Mark the eave to measure it. The GABLE RAKE is measured "
        "separately, from the rake lines already drawn"),
}
TRIM_ORDER = ("outside_corner", "inside_corner", "j_channel", "starter",
              "soffit", "fascia", "gable_rake")
TRIM_LABELS = {"outside_corner": "Outside corners",
               "inside_corner": "Inside corners",
               "j_channel": "J-channel",
               "starter": "Starter",
               "soffit": "Soffit",
               "fascia": "Fascia",
               "gable_rake": "Gable rake"}
TRIM_ZONES = {"gable_rake": "gable"}          # everything else is body


def _j_channel(marks: List[dict], ipp: Optional[float]) -> dict:
    """J-CHANNEL = THE PERIMETER OF THE BOX DRAWN ROUND THE OPENING, on
    this photo, in this photo's own scale. A tap carries a COUNT and no
    extent — its J-channel is REFUSED BY NAME until the opening is boxed.
    No size is ever invented, and a typed width/height is a guidance claim,
    never a quantity input (SEND-131A)."""
    opens = [m for m in marks if m.get("kind") in OPENING_KINDS
             and m.get("status") == "confirmed"]
    rows, refusals = [], []
    total = 0.0
    live = False
    for m in opens:
        pts = m.get("points") or []
        label = m.get("label") or "opening"
        if len(pts) < 3:
            reason = ("count only — this opening is a tap with no drawn "
                      "extent; box it on this photo to measure its J-channel")
            rows.append({"id": m.get("id"), "label": label, "lf": None,
                         "basis": None, "refusal": reason})
            refusals.append(f"{label}: {reason}")
            continue
        if not ipp:
            reason = ("no scale on this photo — the box is drawn, its "
                      "length is not known")
            rows.append({"id": m.get("id"), "label": label, "lf": None,
                         "basis": None, "refusal": reason})
            refusals.append(f"{label}: {reason}")
            continue
        per = _perimeter_ft(pts, ipp)
        w_ft = h_ft = None
        if len(pts) == 4:
            w_ft = round((_seg_ft(pts[0], pts[1], ipp)
                          + _seg_ft(pts[2], pts[3], ipp)) / 2.0, 2)
            h_ft = round((_seg_ft(pts[1], pts[2], ipp)
                          + _seg_ft(pts[3], pts[0], ipp)) / 2.0, 2)
        if not per > 0 or not _poly_area_px(pts) > 0:
            reason = ("the box drawn round this opening encloses nothing — "
                      "re-draw it")
            rows.append({"id": m.get("id"), "label": label, "lf": None,
                         "basis": None, "refusal": reason})
            refusals.append(f"{label}: {reason}")
            continue
        basis = ("perimeter of the box drawn on this photo"
                 + (f" · {w_ft} ft × {h_ft} ft" if w_ft and h_ft else "")
                 + f" · {round(per, 2)} LF")
        rows.append({"id": m.get("id"), "label": label,
                     "lf": round(per, 2), "width_ft": w_ft, "height_ft": h_ft,
                     "basis": basis, "refusal": None})
        total += per
        live = True
    return {"lf": round(total, 2) if live else None,
            "rows": rows or None, "refusals": refusals or None,
            "count": len(opens) or None}


def _gable_rake(marks: List[dict], masks: List[dict],
                ipp: Optional[float]) -> dict:
    """GABLE RAKE = THE TWO SLOPED LINES THE CONTRACTOR ALREADY DREW
    (left eave → peak → right eave), measured as drawn. It is a GABLE-ZONE
    figure: it is not a wall starter, not a wall corner, not J-channel, and
    it never joins any of them (Howard, SEND-143). A gable whose triangle
    is refused has NO rake — em dash, never a 0."""
    g = [m for m in marks if m.get("kind") == "gable"
         and m.get("status") == "confirmed"]
    rows, refusals = [], []
    total = 0.0
    live = False
    for m in g:
        label = m.get("label") or "gable"
        f = _gable_figure(m, masks, ipp)
        pts = m.get("points") or []
        if f["refusal"] or len(pts) != KIND_POINTS["gable"] or not ipp:
            reason = f["refusal"] or (
                "no scale on this photo — the rake lines are drawn, their "
                "length is not known")
            rows.append({"id": m.get("id"), "label": label, "lf": None,
                         "basis": None, "refusal": reason})
            refusals.append(f"{label}: {reason}")
            continue
        left, peak, right = pts[0], pts[1], pts[2]
        rake = _seg_ft(left, peak, ipp) + _seg_ft(peak, right, ipp)
        basis = (f"the two rake lines drawn on this photo · span "
                 f"{f['base_ft']} ft · rise {f['rise_ft']} ft · "
                 f"{round(rake, 2)} LF")
        rows.append({"id": m.get("id"), "label": label, "lf": round(rake, 2),
                     "span_ft": f["base_ft"], "rise_ft": f["rise_ft"],
                     "basis": basis, "refusal": None})
        total += rake
        live = True
    return {"lf": round(total, 2) if live else None,
            "rows": rows or None, "refusals": refusals or None,
            "count": len(g) or None}


def _trim_rows(marks: List[dict], masks: List[dict],
               ipp: Optional[float]) -> tuple[List[dict], dict, dict]:
    """The six trims Howard named plus the gable rake, IN ONE LIST, every
    row present whether or not it can be measured. A lane with no mark to
    read prints the em dash and NAMES the missing mark."""
    j = _j_channel(marks, ipp)
    r = _gable_rake(marks, masks, ipp)
    rows = []
    for key in TRIM_ORDER:
        if key == "j_channel":
            rows.append({"key": key, "label": TRIM_LABELS[key],
                         "zone": TRIM_ZONES.get(key, "body"),
                         "lf": j["lf"], "rows": j["rows"],
                         "refusal": None if j["lf"] is not None else (
                             "no boxed opening is confirmed on this photo — "
                             "box an opening to measure its J-channel"),
                         "basis": ("perimeter of every box drawn round an "
                                   "opening on this photo")})
        elif key == "gable_rake":
            rows.append({"key": key, "label": TRIM_LABELS[key],
                         "zone": TRIM_ZONES.get(key, "body"),
                         "lf": r["lf"], "rows": r["rows"],
                         "refusal": None if r["lf"] is not None else (
                             "no measured gable triangle on this photo — "
                             "the rake is the two lines you draw with it"),
                         "basis": ("the rake lines drawn with each gable "
                                   "triangle on this photo — GABLE ZONE, "
                                   "never a wall run")})
        else:
            # SEND-147 — THE STARTER LANE MUST NOT LIE. Once a WALL BASE line
            # is tapped on this photo it is FALSE to say none is marked: the
            # line exists, it is an ANCHOR for the AI body bottom, and this
            # send writes NO LF for it. The starter RUN stays unbuilt and the
            # row still prints the em dash.
            refusal = TRIM_REFUSALS[key]
            if key in ("soffit", "fascia") and any(m.get("kind") == "eave"
                                                   for m in marks):
                refusal = (
                    "an EAVE line IS marked on this photo, and it is an "
                    "ANCHOR ONLY — SEND-149 built it to set the AI body top "
                    "and writes NO LF for it. A frieze line is not a soffit "
                    "and it is not a fascia: neither run is built in this "
                    "send, so this row stays an em dash rather than a number "
                    "nobody ruled on")
            if key == "starter" and any(m.get("kind") == "wall_base"
                                        for m in marks):
                refusal = (
                    "a WALL BASE line IS marked on this photo, and it is an "
                    "ANCHOR ONLY — SEND-147 built it to set the AI body "
                    "bottom and writes NO LF for it. The starter RUN is not "
                    "built in this send, so this row stays an em dash rather "
                    "than a number nobody ruled on")
            rows.append({"key": key, "label": TRIM_LABELS[key],
                         "zone": TRIM_ZONES.get(key, "body"),
                         "lf": None, "rows": None,
                         "refusal": refusal, "basis": None})
    return rows, j, r


def _quantities(marks: List[dict], scale: Optional[dict]) -> dict:
    """Quantity from CONFIRMED marks only, and only with a scale. Every
    refusal is named; a refusal is never reported as 0."""
    ipp, basis = _in_per_px(scale)
    confirmed = [m for m in marks if m.get("status") == "confirmed"]
    provisional = [m for m in marks if m.get("status") == "provisional"]
    # NAME THE PLANE ON EVERY FIGURE — computed from ALL marks on the
    # photo (a provisional boxed window is still evidence about the
    # photo's geometry), and stated even when there is no scale at all.
    plane = _plane_basis(marks, ipp)
    out: Dict[str, Any] = {
        **plane,
        "scale_basis": basis if ipp else None,
        "scale_refusal": None if ipp else basis,
        "confirmed_marks": len(confirmed),
        "provisional_marks": len(provisional),
        "provisional_note": (
            f"{len(provisional)} mark(s) drawn but NOT CONFIRMED — they "
            "contribute nothing; confirm each one to let it carry a "
            "quantity") if provisional else None,
        "siding_sqft": None,
        "non_siding_sqft": None,
        "non_siding_by_category": None,
        "opening_count": None,
        "opening_sqft": None,
        "openings_without_extent": None,
        "openings_without_extent_note": None,
        "openings_deducted": False,
        "openings_note": None,
        "siding_by_product": None,
        "siding_no_product_sqft": None,
        "product_basis_notes": None,
        "guidance_confirmed": None,
        "guidance_confirmed_note": None,
        # SEND-139 — the gable and dormer lanes. None, never 0.
        "gable_sqft": None,
        "gable_count": None,
        "gable_refusals": None,
        "gable_pitch_warnings": None,
        "gable_rows": None,
        "dormer_face_sqft": None,
        "dormer_cheek_sqft": None,
        "dormer_count": None,
        "dormer_refusals": None,
        "dormer_rows": None,
        # SEND-140 — one contractor sentence per refused gable / cheek,
        # naming the actual missing field. A measured figure has none.
        "gable_receipts": None,
        "dormer_receipts": None,
        "gable_basis_note": None,
        # SEND-143 — PHASE 2 TRIM. Every row is present; a lane with no
        # mark to read carries None and names the missing mark.
        "trim_rows": None,
        "j_channel_lf": None,
        "j_channel_rows": None,
        "j_channel_refusals": None,
        "gable_rake_lf": None,
        "gable_rake_rows": None,
        "gable_rake_refusals": None,
        "trim_basis_note": None,
    }
    # ── SEND-139: THE GABLE AND DORMER LANES ────────────────────────────
    # Stated BEFORE the no-scale return, so a drawn gable with no scale
    # still NAMES its refusal instead of vanishing.
    masks = [m for m in confirmed if m.get("kind") == "non_siding_zone"]
    # SEND-143 — THE TRIM ROWS ARE STATED BEFORE THE NO-SCALE RETURN, so a
    # drawn box or a drawn rake still NAMES its refusal instead of
    # vanishing off the rail. CONFIRMED marks only, and a non-siding mask
    # never shortens a linear run (nothing is deducted here).
    trim_rows, j_lane, rake_lane = _trim_rows(confirmed, masks, ipp)
    out["trim_rows"] = trim_rows
    out["j_channel_lf"] = j_lane["lf"]
    out["j_channel_rows"] = j_lane["rows"]
    out["j_channel_refusals"] = j_lane["refusals"]
    out["gable_rake_lf"] = rake_lane["lf"]
    out["gable_rake_rows"] = rake_lane["rows"]
    out["gable_rake_refusals"] = rake_lane["refusals"]
    out["trim_basis_note"] = (
        "linear runs come from marks ALREADY DRAWN on this photo and from "
        "this photo's own scale (the tape governs): J-channel is the "
        "perimeter of the box drawn round an opening, the gable rake is the "
        "two sloped lines drawn with the gable triangle. Corners, starter, "
        "soffit and horizontal fascia have no mark to read on this photo — "
        "each row says which mark is missing. Nothing is deducted from a "
        "linear run, no height is copied, and the gable rake never joins a "
        "wall lane")
    g_marks = [m for m in confirmed if m.get("kind") == "gable"]
    d_marks = [m for m in confirmed if m.get("kind") == "dormer"]
    if g_marks:
        rows = []
        g_total = 0.0
        g_any = False
        refusals, warns, receipts = [], [], []
        for m in g_marks:
            f = _gable_figure(m, masks, ipp)
            rows.append({"id": m.get("id"), "label": m.get("label"), **f})
            if f["refusal"]:
                refusals.append(f"{m.get('label') or 'gable'}: {f['refusal']}")
            if f["receipt"]:
                receipts.append({"id": m.get("id"),
                                 "label": m.get("label"),
                                 "receipt": f["receipt"]})
            if f["pitch_warning"]:
                warns.append(f"{m.get('label') or 'gable'}: {f['pitch_warning']}")
            if f["sqft"] is not None:
                g_total += f["sqft"]
                g_any = True
        out["gable_rows"] = rows
        out["gable_count"] = len(g_marks)
        out["gable_sqft"] = round(g_total, 2) if g_any else None
        out["gable_refusals"] = refusals or None
        out["gable_receipts"] = receipts or None
        out["gable_pitch_warnings"] = warns or None
        out["gable_basis_note"] = (
            "gable measured — ½ × width × rise from the triangle drawn on "
            "THIS photo, no field factor (SEND-137). A face with no photo "
            "gets no gable: nothing here is copied from another face")
    if d_marks:
        rows = []
        f_total = c_total = 0.0
        f_any = c_any = False
        refusals, receipts = [], []
        for m in d_marks:
            f = _dormer_figure(m, masks, ipp)
            rows.append({"id": m.get("id"), "label": m.get("label"),
                         "depth_ft": m.get("depth_ft"), **f})
            for r in (f["refusal"], f["cheek_refusal"]):
                if r:
                    refusals.append(f"{m.get('label') or 'dormer'}: {r}")
            for r in (f["receipt"], f["cheek_receipt"]):
                if r:
                    receipts.append({"id": m.get("id"),
                                     "label": m.get("label"), "receipt": r})
            if f["sqft"] is not None:
                f_total += f["sqft"]
                f_any = True
            if f["cheek_sqft"] is not None:
                c_total += f["cheek_sqft"]
                c_any = True
        out["dormer_rows"] = rows
        out["dormer_count"] = len(d_marks)
        out["dormer_face_sqft"] = round(f_total, 2) if f_any else None
        out["dormer_cheek_sqft"] = round(c_total, 2) if c_any else None
        out["dormer_refusals"] = refusals or None
        out["dormer_receipts"] = receipts or None
    if not ipp:
        return out
    sq_ft_per_px = (ipp * ipp) / 144.0
    siding = 0.0
    non_siding = 0.0
    by_cat: Dict[str, float] = {}
    by_prod: Dict[str, float] = {}
    no_prod = 0.0
    prod_notes: List[str] = []
    op_n = 0
    op_sqft = 0.0
    op_no_extent = 0
    for m in confirmed:
        pts = m.get("points") or []
        area = _poly_area_px(pts) * sq_ft_per_px
        if m["kind"] == "siding_zone":
            siding += area
            # THE BASIS NAMES THE PRODUCT THE QUANTITY WAS CONFIRMED
            # UNDER. A later swap alters the OUTPUT, not the geometry —
            # both names stay in the record and the note says so.
            prod = m.get("product")
            under = m.get("confirmed_under_product")
            if prod:
                by_prod[prod] = round(by_prod.get(prod, 0.0) + area, 2)
            else:
                no_prod += area
            if under and prod and under != prod:
                prod_notes.append(
                    f"{round(area, 2)} ft² was confirmed under "
                    f"{under!r}, now assigned {prod!r} — the geometry did "
                    "not change; the output did")
            elif under and not prod:
                prod_notes.append(
                    f"{round(area, 2)} ft² was confirmed under {under!r} "
                    "and now carries no product")
        elif m["kind"] == "non_siding_zone":
            non_siding += area
            cat = m.get("category") or "other"
            by_cat[cat] = round(by_cat.get(cat, 0.0) + area, 2)
        elif m["kind"] == "opening":
            op_n += 1
            # AN OPENING TAP CARRIES A COUNT, NOT AN AREA. A point mark
            # has no drawn extent on the photo — its ft² is REFUSED and
            # named, never a silent 0. Draw the opening as a box to give
            # it an area.
            if len(pts) >= 3:
                op_sqft += area
            else:
                op_no_extent += 1
    # A LANE WITH NO CONFIRMED MARK OF ITS OWN KIND REPORTS None, NEVER 0
    # — a zero would read as "measured and empty" when nothing was
    # measured at all.
    any_siding = any(m["kind"] == "siding_zone" for m in confirmed)
    any_non = any(m["kind"] == "non_siding_zone" for m in confirmed)
    any_open = any(m["kind"] in OPENING_KINDS for m in confirmed)
    out["siding_sqft"] = round(siding, 2) if any_siding else None
    out["non_siding_sqft"] = round(non_siding, 2) if any_non else None
    out["non_siding_by_category"] = by_cat or None
    out["opening_count"] = op_n if any_open else None
    out["opening_sqft"] = (round(op_sqft, 2)
                           if (any_open and op_n > op_no_extent) else None)
    out["openings_without_extent"] = op_no_extent or None
    out["openings_without_extent_note"] = (
        f"{op_no_extent} confirmed opening(s) are taps with no drawn "
        "extent — they carry a COUNT and no ft²; box each one to give it "
        "an area") if op_no_extent else None
    # PHASE 1: OPENINGS REPORT SEPARATELY. No deduction from the
    # confirmed siding ft² on this photo — the blueprint lane's
    # deduction ruling does not carry here (Howard, 2026-08-26).
    out["openings_deducted"] = False
    out["openings_note"] = (
        "openings report separately — nothing is deducted from the "
        "confirmed siding ft² on this photo (phase 1)") if any_open else None
    out["siding_by_product"] = by_prod or None
    out["siding_no_product_sqft"] = (round(no_prod, 2)
                                     if no_prod > 0 else None)
    out["product_basis_notes"] = prod_notes or None
    # GUIDANCE AND EVIDENCE STAY DISTINCT. A confirmed mark whose origin
    # is guidance is NOT evidence that the AI was checked — the count is
    # reported so no reader can mistake one for the other.
    g = [m for m in confirmed
         if m.get("origin") in GUIDANCE_ORIGINS
         and not m.get("confirmed_after_ai_read")]
    out["guidance_confirmed"] = len(g) or None
    out["guidance_confirmed_note"] = (
        f"{len(g)} confirmed mark(s) are GUIDANCE-CONFIRMED — the "
        "contractor's own pre-AI marks, confirmed with no AI read on this "
        "photo. They carry quantity; they are NOT evidence that an AI "
        "read was checked") if g else None
    return out


@router.get("/estimates/{est_id}/photo-takeoff")
async def get_photo_takeoff(est_id: str, photo_key: Optional[str] = None,
                            user: dict = Depends(get_current_user)):
    """Marks + the photo's own scale + the quantities the CONFIRMED marks
    carry. Unconfirmed marks are listed and named, never counted."""
    await _est_or_404(est_id, user)
    q: Dict[str, Any] = {"estimate_id": est_id,
                         "company_id": user["company_id"]}
    if photo_key:
        q["photo_key"] = photo_key
    marks = [_mark_public(m) async for m in db.photo_takeoff_marks.find(q)]
    scales = {}
    sq: Dict[str, Any] = {"estimate_id": est_id,
                          "company_id": user["company_id"]}
    if photo_key:
        sq["photo_key"] = photo_key
    async for s in db.photo_takeoff_scale.find(sq):
        scales[s["photo_key"]] = _mark_public(s)
    per_photo = {}
    est = await _est_or_404(est_id, user)
    products = _job_body_products(est)
    for key in {m["photo_key"] for m in marks} | set(scales) | (
            {photo_key} if photo_key else set()):
        run = await _photo_read(est_id, key)
        per_photo[key] = {
            "scale": scales.get(key),
            "quantities": _quantities(
                [m for m in marks if m["photo_key"] == key], scales.get(key)),
            **_stage_block(run, key),
        }
    return {"ok": True, "phase": 2,
            "kinds": sorted(PHASE1_KINDS),
            "phase2_kinds_not_built": sorted(PHASE2_KINDS),
            "phase2_linear_measured": ["j_channel", "gable_rake"],
            "phase2_linear_refused": ["outside_corner", "inside_corner",
                                      "starter", "soffit", "fascia"],
            "phase2_note": (
                "SEND-143: the linear runs come from marks ALREADY DRAWN — "
                "no new mark type exists, so a starter/corner/soffit/fascia "
                "MARK is still refused, and those rows print the em dash "
                "with the missing mark named"),
            "products": products,
            "products_note": (None if products else
                              "this job carries no body-siding product line "
                              "yet — the picker stays empty; no product is "
                              "invented to fill it"),
            "marks": marks, "per_photo": per_photo}


@router.put("/estimates/{est_id}/photo-takeoff/scale")
async def set_scale(est_id: str, body: ScaleIn,
                    user: dict = Depends(get_current_user)):
    """Scale is LOCAL TO THE PHOTO: the two-tap anchor or a typed tape on
    the same span. WHERE A TAPE IS PRESENT, THE TAPE WINS."""
    await _est_or_404(est_id, user)
    key = {"estimate_id": est_id, "company_id": user["company_id"],
           "photo_key": body.photo_key}
    if body.clear:
        await db.photo_takeoff_scale.delete_one(key)
        return {"ok": True, "scale": None}
    cur = await db.photo_takeoff_scale.find_one(key) or {}
    anchor = body.anchor or cur.get("anchor")
    if not anchor or not anchor.get("p1") or not anchor.get("p2"):
        raise HTTPException(
            status_code=400,
            detail="the scale needs a two-tap span on this photo — the "
                   "tape figure describes THAT span, it cannot stand alone")
    span_px = ((float(anchor["p2"]["x"]) - float(anchor["p1"]["x"])) ** 2
               + (float(anchor["p2"]["y"]) - float(anchor["p1"]["y"])) ** 2) ** 0.5
    doc = {**key, "anchor": anchor, "span_px": round(span_px, 3),
           "tape_inches": (body.tape_inches
                           if body.tape_inches is not None
                           else cur.get("tape_inches")),
           "updated_at": _now(), "updated_by": user.get("email")}
    await db.photo_takeoff_scale.update_one(key, {"$set": doc}, upsert=True)
    ipp, basis = _in_per_px(doc)
    return {"ok": True, "scale": _mark_public(doc),
            "basis": basis if ipp else None,
            "refusal": None if ipp else basis}


@router.post("/estimates/{est_id}/photo-takeoff/marks")
async def add_mark(est_id: str, body: MarkIn,
                   user: dict = Depends(get_current_user)):
    """A new mark lands PROVISIONAL. It carries no quantity until a human
    confirms it."""
    est = await _est_or_404(est_id, user)
    if body.kind in PHASE2_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"{body.kind} is a phase-2 linear run — not built yet; "
                   f"phase 1 is {sorted(PHASE1_KINDS)}")
    if body.kind not in PHASE1_KINDS:
        raise HTTPException(status_code=400,
                            detail=f"unknown mark kind {body.kind!r}")
    need = KIND_POINTS.get(body.kind, 1 if body.shape == "point" else 3)
    pts = [p.model_dump() for p in body.points]
    if body.kind in KIND_POINTS and len(pts) != need:
        raise HTTPException(
            status_code=400,
            detail=(f"a {body.kind} needs exactly {need} point(s) in this "
                    f"photo's natural pixels — "
                    + ("LEFT EAVE, PEAK, RIGHT EAVE"
                       if body.kind == "gable" else
                       "the LEFT end of the wall base, then the RIGHT end"
                       if body.kind == "wall_base" else
                       "the LEFT end of the eave / frieze, then the RIGHT end"
                       if body.kind == "eave" else
                       "bottom-left, bottom-right, top-right, top-left")
                    + "; nothing is padded or truncated to fit"))
    if len(pts) < need:
        raise HTTPException(
            status_code=400,
            detail=f"a {body.shape} mark needs at least {need} point(s) in "
                   "this photo's natural pixels")
    if (body.kind == "non_siding_zone"
            and (body.category or "other") not in NON_SIDING_CATEGORIES):
        raise HTTPException(
            status_code=400,
            detail=f"category must be one of {sorted(NON_SIDING_CATEGORIES)}")
    product = None
    if body.product:
        product = await _validated_product(est, body.product)
    run = await _photo_read(est_id, body.photo_key)
    stage = 2 if run else 1
    origin = ("imported_annotation" if body.source == "imported_annotation"
              else ("contractor_stage2" if run else "contractor_stage1"))
    doc = {
        "id": str(uuid4()), "estimate_id": est_id,
        "company_id": user["company_id"], "photo_key": body.photo_key,
        "kind": body.kind,
        "shape": "line" if body.kind in ANCHOR_KINDS else body.shape,
        "points": pts,
        "wall_base": (_wall_base_record(pts) if body.kind == "wall_base"
                      else None),
        "eave": _wall_base_record(pts) if body.kind == "eave" else None,
        "category": body.category, "label": body.label,
        "style": body.style, "width_in": body.width_in,
        "height_in": body.height_in,
        "product": product,
        "symmetric": body.symmetric,
        "pitch_set": body.pitch_set,
        "depth_ft": body.depth_ft,
        "product_history": [],
        "confirmed_under_product": None,
        "source": body.source, "status": "provisional",
        "origin": origin, "stage": stage,
        "basis": (WALL_BASE_BASIS if body.kind == "wall_base"
                  else EAVE_BASIS if body.kind == "eave"
                  else _origin_basis(origin, stage)),
        "ai": None,
        "confirmed_at": None, "confirmed_by": None, "confirmed_stage": None,
        "confirmed_basis": None, "confirmed_after_ai_read": None,
        "refused_reason": None,
        "created_at": _now(), "created_by": user.get("email"),
        "updated_at": _now(),
    }
    await db.photo_takeoff_marks.insert_one(dict(doc))
    # SEND-147 — THE TAP MOVES THE BOX. A start line is an ANCHOR, so the AI
    # zones already on this photo are re-placed against it at once. Nothing
    # new is placed, and a zone touched by hand stays where it was put.
    rebase = (await rebase_zones_for_photo(
        db, est_id, user["company_id"], body.photo_key, user.get("email"),
        scope="body" if body.kind == "eave" else "all")
        if body.kind in ANCHOR_KINDS else None)
    return {"ok": True, "mark": _mark_public(doc), "rebase": rebase}


@router.patch("/estimates/{est_id}/photo-takeoff/marks/{mark_id}")
async def patch_mark(est_id: str, mark_id: str, body: MarkPatch,
                     user: dict = Depends(get_current_user)):
    """Adjust, CONFIRM or REFUSE. Adjusting a confirmed mark returns it to
    PROVISIONAL — the confirmation was of the old geometry, and a
    confirmation cannot outlive the figure it was given for."""
    est = await _est_or_404(est_id, user)
    key = {"id": mark_id, "estimate_id": est_id,
           "company_id": user["company_id"]}
    cur = await db.photo_takeoff_marks.find_one(key)
    if not cur:
        raise HTTPException(status_code=404, detail="mark not found")
    scale = await db.photo_takeoff_scale.find_one(
        {"estimate_id": est_id, "company_id": user["company_id"],
         "photo_key": cur["photo_key"]})
    upd: Dict[str, Any] = {"updated_at": _now()}
    # SEND-147 — A HAND ON A MARK IS RECORDED. A body zone Howard has moved,
    # confirmed or refused is HUMAN-TOUCHED and a re-pull leaves it alone;
    # only a FRESH PROVISIONAL body may move to a new wall-base y.
    upd["human_touched"] = True
    upd["human_touched_at"] = _now()
    upd["human_touched_by"] = user.get("email")
    if body.points is not None:
        pts = [p.model_dump() for p in body.points]
        need = KIND_POINTS.get(cur.get("kind"),
                               1 if cur.get("shape") == "point" else 3)
        if (len(pts) != need if cur.get("kind") in KIND_POINTS
                else len(pts) < need):
            raise HTTPException(status_code=400,
                                detail=f"a mark needs {need} point(s)")
        upd["points"] = pts
        if cur.get("kind") in ANCHOR_KINDS:
            upd[cur["kind"]] = _wall_base_record(pts)
        if cur.get("status") == "confirmed":
            upd.update({"status": "provisional", "confirmed_at": None,
                        "confirmed_by": None, "confirmed_stage": None,
                        "confirmed_basis": None,
                        "confirmed_after_ai_read": None,
                        "refused_reason": "geometry changed after "
                                          "confirmation — re-confirm the "
                                          "new figure"})
    if body.category is not None:
        upd["category"] = body.category
    if body.label is not None:
        upd["label"] = body.label
    for field in ("style", "width_in", "height_in", "symmetric",
                  "pitch_set"):
        v = getattr(body, field)
        if v is not None:
            upd[field] = v
    if body.depth_ft is not None and body.depth_ft != cur.get("depth_ft"):
        # DORMER DEPTH IS A QUANTITY INPUT, not a guidance claim: the
        # cheeks are 2 × height × depth. A confirmation cannot outlive
        # the figure it was given for, so a depth change on a CONFIRMED
        # dormer returns it to PROVISIONAL — the same rule the geometry
        # already follows.
        upd["depth_ft"] = body.depth_ft
        if cur.get("status") == "confirmed":
            upd.update({"status": "provisional", "confirmed_at": None,
                        "confirmed_by": None, "confirmed_stage": None,
                        "confirmed_basis": None,
                        "confirmed_after_ai_read": None,
                        "refused_reason": "dormer depth changed after "
                                          "confirmation — re-confirm the "
                                          "new cheek figure"})
    if body.product is not None:
        # A PRODUCT CHANGE ALTERS THE OUTPUT, NOT THE GEOMETRY — the mark
        # keeps its confirmation, the swap is recorded, and the basis
        # keeps the product the quantity was confirmed under.
        new_prod = (await _validated_product(est, body.product)
                    if body.product else None)
        if new_prod != cur.get("product"):
            ipp, _ = _in_per_px(scale)
            sqft = (round(_poly_area_px(cur.get("points") or [])
                          * ((ipp * ipp) / 144.0), 2) if ipp else None)
            upd["product"] = new_prod
            upd["product_history"] = list(cur.get("product_history") or []) + [{
                "from": cur.get("product"), "to": new_prod,
                "at": _now(), "by": user.get("email") or None,
                "sqft_at_swap": sqft,
            }]
    if body.status is not None:
        if body.status not in STATUSES:
            raise HTTPException(status_code=400,
                               detail=f"status must be one of {sorted(STATUSES)}")
        upd["status"] = body.status
        if body.status == "confirmed":
            # A CONFIRM STILL NEEDS A SCALE ON THIS PHOTO. No tape and no
            # anchor → NAMED refusal, never a 0.
            ipp, sbasis = _in_per_px(scale)
            if not ipp:
                raise HTTPException(status_code=400, detail=sbasis)
            run = await _photo_read(est_id, cur["photo_key"])
            after = bool(run)
            origin = cur.get("origin") or "contractor_stage1"
            if origin == "ai_proposal":
                cbasis = ("EVIDENCE — an AI proposal on this photo, checked "
                          "and confirmed by the contractor")
            elif after:
                cbasis = ("EVIDENCE — confirmed with the AI read on this "
                          f"photo present (origin {origin})")
            else:
                cbasis = ("GUIDANCE-CONFIRMED — no AI read on this photo. "
                          "It carries quantity; it is NOT evidence that an "
                          "AI read was checked")
            upd.update({"confirmed_at": _now(),
                        "confirmed_by": user.get("email"),
                        "confirmed_stage": 2 if after else 1,
                        "confirmed_basis": cbasis,
                        "confirmed_after_ai_read": after,
                        "confirmed_under_product": (
                            upd.get("product", cur.get("product"))),
                        "refused_reason": None})
        elif body.status == "refused":
            upd.update({"confirmed_at": None, "confirmed_by": None,
                        "confirmed_stage": None, "confirmed_basis": None,
                        "confirmed_after_ai_read": None,
                        "refused_reason": (body.refused_reason
                                           or "refused by the contractor")})
        else:
            upd.update({"confirmed_at": None, "confirmed_by": None,
                        "confirmed_stage": None, "confirmed_basis": None,
                        "confirmed_after_ai_read": None})
    await db.photo_takeoff_marks.update_one(key, {"$set": upd})
    doc = await db.photo_takeoff_marks.find_one(key)
    rebase = (await rebase_zones_for_photo(
        db, est_id, user["company_id"], cur["photo_key"], user.get("email"),
        scope="body" if cur.get("kind") == "eave" else "all")
        if cur.get("kind") in ANCHOR_KINDS else None)
    return {"ok": True, "mark": _mark_public(doc), "rebase": rebase}


@router.delete("/estimates/{est_id}/photo-takeoff/marks/{mark_id}")
async def delete_mark(est_id: str, mark_id: str,
                      user: dict = Depends(get_current_user)):
    await _est_or_404(est_id, user)
    key = {"id": mark_id, "estimate_id": est_id,
           "company_id": user["company_id"]}
    cur = await db.photo_takeoff_marks.find_one(key)
    res = await db.photo_takeoff_marks.delete_one(key)
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="mark not found")
    # SEND-147 — with the start line gone the anchor is gone: a FRESH
    # provisional zone goes back to the read's own answer, and a zone
    # touched by hand stays exactly where the hand left it.
    rebase = (await rebase_zones_for_photo(
        db, est_id, user["company_id"], cur["photo_key"], user.get("email"),
        scope="body" if (cur or {}).get("kind") == "eave" else "all")
        if (cur or {}).get("kind") in ANCHOR_KINDS else None)
    return {"ok": True, "deleted": mark_id, "rebase": rebase}


@router.post("/estimates/{est_id}/photo-takeoff/import-annotations")
async def import_annotations(est_id: str, photo_key: str,
                             user: dict = Depends(get_current_user)):
    """Marks the contractor already drew in the pre-AI annotator flow in
    as PROVISIONAL — nothing already drawn is discarded, and nothing
    imported carries a quantity until it is confirmed here."""
    await _est_or_404(est_id, user)
    sess = await db.ai_measure_sessions.find_one(
        {"estimate_id": est_id, "company_id": user["company_id"]})
    ann = ((sess or {}).get("photo_annotations") or {}).get(photo_key) or {}
    made: List[dict] = []
    existing = {(m.get("source"), tuple(
        (round(p["x"], 1), round(p["y"], 1)) for p in (m.get("points") or [])))
        async for m in db.photo_takeoff_marks.find(
            {"estimate_id": est_id, "company_id": user["company_id"],
             "photo_key": photo_key})}
    for z in (ann.get("zones") or []):
        pts = [{"x": float(p["x"]), "y": float(p["y"])}
               for p in (z.get("points") or [])]
        if len(pts) < 3:
            continue
        sig = ("imported_annotation",
               tuple((round(p["x"], 1), round(p["y"], 1)) for p in pts))
        if sig in existing:
            continue
        existing.add(sig)
        cat = z.get("category") or "other"
        made.append({
            "id": str(uuid4()), "estimate_id": est_id,
            "company_id": user["company_id"], "photo_key": photo_key,
            "kind": "non_siding_zone",
            "shape": "poly" if z.get("kind") == "poly" else "rect",
            "points": pts,
            "category": cat if cat in NON_SIDING_CATEGORIES else "other",
            "label": f"imported {cat} zone", "source": "imported_annotation",
            "style": None, "width_in": None, "height_in": None,
            "product": None, "product_history": [],
            "confirmed_under_product": None,
            "origin": "imported_annotation", "stage": 1,
            "basis": _origin_basis("imported_annotation", 1), "ai": None,
            "status": "provisional", "confirmed_at": None,
            "confirmed_by": None, "confirmed_stage": None,
            "confirmed_basis": None, "confirmed_after_ai_read": None,
            "refused_reason": None,
            "created_at": _now(), "created_by": user.get("email"),
            "updated_at": _now()})
    for w in (ann.get("windows") or []):
        # A TAGGED WINDOW IS A TAP (x, y, style) — a point, not a box.
        # It comes in as a point opening: a COUNT with no ft² until the
        # contractor boxes it here. A window that already carries drawn
        # corners keeps them.
        pts = [{"x": float(p["x"]), "y": float(p["y"])}
               for p in (w.get("points") or [])]
        shape = "rect"
        if len(pts) < 3:
            if w.get("x") is None or w.get("y") is None:
                continue
            pts = [{"x": float(w["x"]), "y": float(w["y"])}]
            shape = "point"
        sig = ("imported_annotation",
               tuple((round(p["x"], 1), round(p["y"], 1)) for p in pts))
        if sig in existing:
            continue
        existing.add(sig)
        made.append({
            "id": str(uuid4()), "estimate_id": est_id,
            "company_id": user["company_id"], "photo_key": photo_key,
            "kind": "opening", "shape": shape, "points": pts,
            "category": None,
            "label": f"imported {w.get('style') or 'window'}",
            # THE ANNOTATOR'S OWN CLAIMS COME WITH IT — style and the
            # typed height are GUIDANCE, never a quantity input.
            "style": w.get("style") or None,
            "width_in": (float(w["width_in"])
                         if w.get("width_in") else None),
            "height_in": (float(w["height_in"])
                          if w.get("height_in") else None),
            "product": None, "product_history": [],
            "confirmed_under_product": None,
            "origin": "imported_annotation", "stage": 1,
            "basis": _origin_basis("imported_annotation", 1), "ai": None,
            "source": "imported_annotation", "status": "provisional",
            "confirmed_at": None, "confirmed_by": None,
            "confirmed_stage": None, "confirmed_basis": None,
            "confirmed_after_ai_read": None,
            "refused_reason": None, "created_at": _now(),
            "created_by": user.get("email"), "updated_at": _now()})
    # SEND-139 — THE ANNOTATOR IS AN IMPORT SOURCE, NOT A DRAWING DOOR.
    # Gables and dormers the contractor already drew there come across
    # with their own typed fields (symmetric, pitch, dormer depth), as
    # PROVISIONAL, exactly like every other imported mark.
    for g in (ann.get("gables") or []):
        pts = [{"x": float(p["x"]), "y": float(p["y"])}
               for p in (g.get("pts") or g.get("points") or [])]
        if len(pts) != KIND_POINTS["gable"]:
            continue
        sig = ("imported_annotation",
               tuple((round(p["x"], 1), round(p["y"], 1)) for p in pts))
        if sig in existing:
            continue
        existing.add(sig)
        made.append({
            "id": str(uuid4()), "estimate_id": est_id,
            "company_id": user["company_id"], "photo_key": photo_key,
            "kind": "gable", "shape": "poly", "points": pts,
            "category": None, "label": "imported gable",
            "source": "imported_annotation",
            "style": None, "width_in": None, "height_in": None,
            "product": None, "product_history": [],
            "confirmed_under_product": None,
            "symmetric": bool(g.get("symmetric")) or None,
            "pitch_set": (float(g["pitch_set"])
                          if g.get("pitch_set") else None),
            "depth_ft": None,
            "origin": "imported_annotation", "stage": 1,
            "basis": _origin_basis("imported_annotation", 1), "ai": None,
            "status": "provisional", "confirmed_at": None,
            "confirmed_by": None, "confirmed_stage": None,
            "confirmed_basis": None, "confirmed_after_ai_read": None,
            "refused_reason": None,
            "created_at": _now(), "created_by": user.get("email"),
            "updated_at": _now()})
    for d in (ann.get("dormers") or []):
        pts = [{"x": float(p["x"]), "y": float(p["y"])}
               for p in (d.get("pts") or d.get("points") or [])]
        if len(pts) != KIND_POINTS["dormer"]:
            continue
        sig = ("imported_annotation",
               tuple((round(p["x"], 1), round(p["y"], 1)) for p in pts))
        if sig in existing:
            continue
        existing.add(sig)
        depth = d.get("depth_ft")
        try:
            depth = float(depth) if depth not in (None, "") else None
        except (TypeError, ValueError):
            depth = None
        made.append({
            "id": str(uuid4()), "estimate_id": est_id,
            "company_id": user["company_id"], "photo_key": photo_key,
            "kind": "dormer", "shape": "poly", "points": pts,
            "category": None, "label": "imported dormer",
            "source": "imported_annotation",
            "style": None, "width_in": None, "height_in": None,
            "product": None, "product_history": [],
            "confirmed_under_product": None,
            "symmetric": None, "pitch_set": None,
            # A DEPTH THE CONTRACTOR NEVER TYPED DOES NOT ARRIVE AS 1.5:
            # it arrives as nothing, and the cheeks refuse until he types
            # it here.
            "depth_ft": depth,
            "origin": "imported_annotation", "stage": 1,
            "basis": _origin_basis("imported_annotation", 1), "ai": None,
            "status": "provisional", "confirmed_at": None,
            "confirmed_by": None, "confirmed_stage": None,
            "confirmed_basis": None, "confirmed_after_ai_read": None,
            "refused_reason": None,
            "created_at": _now(), "created_by": user.get("email"),
            "updated_at": _now()})

    if made:
        await db.photo_takeoff_marks.insert_many([dict(m) for m in made])
    ref = ann.get("reference") or {}
    scale_note = None
    if ref.get("p1") and ref.get("p2") and ref.get("inches"):
        key = {"estimate_id": est_id, "company_id": user["company_id"],
               "photo_key": photo_key}
        if not await db.photo_takeoff_scale.find_one(key):
            span = ((float(ref["p2"]["x"]) - float(ref["p1"]["x"])) ** 2
                    + (float(ref["p2"]["y"]) - float(ref["p1"]["y"])) ** 2) ** 0.5
            await db.photo_takeoff_scale.update_one(
                key, {"$set": {**key, "anchor": ref,
                               "span_px": round(span, 3),
                               "tape_inches": None, "updated_at": _now(),
                               "updated_by": user.get("email")}},
                upsert=True)
            scale_note = ("the photo's existing two-tap anchor came in as "
                          "the scale — type a tape figure to override it")
    return {"ok": True, "imported": len(made),
            "marks": [_mark_public(m) for m in made],
            "scale_note": scale_note,
            "note": ("imported marks are PROVISIONAL — confirm, adjust or "
                     "refuse each one; nothing imported carries a quantity")}


@router.post("/estimates/{est_id}/photo-takeoff/propose")
async def propose_from_read(est_id: str, photo_key: str,
                            user: dict = Depends(get_current_user)):
    """STAGE 2 — the AI's own marks on THIS photo, as PROVISIONAL
    proposals. The pull is not limited to any one kind: it takes every
    mark kind the read produced for this photo, and where the read
    produced none of a kind IT SAYS SO PLAINLY. Nothing is invented to
    fill a gap — a wall proposal that the read never made does not
    appear here.

    IDEMPOTENT per (run_id, mark id): a second pull adds nothing."""
    await _est_or_404(est_id, user)
    run = await _photo_read(est_id, photo_key)
    if not run:
        raise HTTPException(
            status_code=400,
            detail=("no completed AI read carries this photo — Stage 2 is "
                    "not unlocked here; a read on another photo unlocks "
                    "nothing on this one"))
    idx = _run_photo_names(run).index(photo_key)
    raw = ((run.get("result") or {}).get("raw_ai") or {})

    dims = _photo_natural_size(photo_key)
    if not dims:
        # SEND-143 — the photo's home is object storage since SEND-142; get
        # it back before refusing. The refusal below still stands when the
        # bytes cannot be found ANYWHERE — no size is ever guessed.
        from config import UPLOAD_DIR
        from upload_store import rehydrate_to_disk
        if await rehydrate_to_disk(photo_key, UPLOAD_DIR):
            dims = _photo_natural_size(photo_key)
    if not dims:
        raise HTTPException(
            status_code=400,
            detail=("this photo's file cannot be found, so the read's "
                    "normalised boxes cannot be placed in its own pixels — "
                    "nothing is placed on a guessed size"))
    nat_w, nat_h = dims

    have = set()
    async for m in db.photo_takeoff_marks.find(
            {"estimate_id": est_id, "company_id": user["company_id"],
             "photo_key": photo_key}):
        ai = m.get("ai") or {}
        if ai.get("run_id"):
            have.add((ai["run_id"], ai.get("ref_id")))

    made: List[dict] = []
    no_box = 0
    for op in (raw.get("openings") or []):
        if not isinstance(op, dict):
            continue
        on_this = (op.get("bbox_photo_idx") == idx
                   or (op.get("bbox_photo_idx") is None
                       and op.get("photo_idx") == idx))
        if not on_this:
            continue
        b = op.get("bbox")
        ref_id = str(op.get("opening_id") or "")
        if not (isinstance(b, dict) and float(b.get("w") or 0) > 0
                and float(b.get("h") or 0) > 0):
            no_box += 1
            continue
        if (run["run_id"], ref_id) in have:
            continue
        have.add((run["run_id"], ref_id))
        x, y = float(b["x"]) * nat_w, float(b["y"]) * nat_h
        w, h = float(b["w"]) * nat_w, float(b["h"]) * nat_h
        made.append({
            "id": str(uuid4()), "estimate_id": est_id,
            "company_id": user["company_id"], "photo_key": photo_key,
            "kind": "opening", "shape": "rect",
            "points": [{"x": x, "y": y}, {"x": x + w, "y": y},
                       {"x": x + w, "y": y + h}, {"x": x, "y": y + h}],
            "category": None,
            "label": f"AI {op.get('type') or 'opening'} {ref_id}".strip(),
            "style": op.get("style") or None,
            "width_in": (float(op["width_in"]) if op.get("width_in") else None),
            "height_in": (float(op["height_in"]) if op.get("height_in") else None),
            "product": None, "product_history": [],
            "confirmed_under_product": None,
            "origin": "ai_proposal", "stage": 2,
            "basis": _origin_basis("ai_proposal", 2),
            "ai": {"run_id": run["run_id"], "ref_id": ref_id,
                   "kind_claimed": op.get("type"),
                   "wall_claimed": op.get("wall"),
                   "bbox_source": op.get("_bbox_source")},
            "source": "ai_proposal", "status": "provisional",
            "confirmed_at": None, "confirmed_by": None,
            "confirmed_stage": None, "confirmed_basis": None,
            "confirmed_after_ai_read": None, "refused_reason": None,
            "created_at": _now(), "created_by": user.get("email"),
            "updated_at": _now()})
    if made:
        await db.photo_takeoff_marks.insert_many([dict(m) for m in made])

    # WHAT THE READ DOES NOT PRODUCE, SAID PLAINLY. The read returns no
    # zone geometry of any kind — masks are an INPUT to it, never an
    # output — so siding and non-siding zones have nothing to propose
    # and none is invented.
    kinds_absent = {
        "siding_zone": ("this read produces NO siding-zone geometry — it "
                        "returns wall dimensions, not drawn polygons; draw "
                        "the siding zones yourself, nothing is invented"),
        "non_siding_zone": ("this read produces NO non-siding-zone geometry "
                            "— the masks are an INPUT to the read, never an "
                            "output; draw them yourself"),
        # SEND-139 — the read returns a gable RISE and dormer counts as
        # NUMBERS, never as a triangle or a quad drawn on this photo.
        # There is nothing to propose, and nothing is placed at a guessed
        # spot to look helpful.
        "gable": ("this read returns a gable RISE figure, not a triangle "
                  "drawn on this photo — draw the gable yourself; ½ × width "
                  "× rise comes from what you draw here"),
        "dormer": ("this read returns dormer counts and sizes, not the four "
                   "corners of a face on this photo — draw the dormer face "
                   "yourself; nothing is placed at a guessed spot"),
    }
    return {
        "ok": True, "run_id": run["run_id"], "photo_index": idx,
        "proposed": len(made),
        "marks": [_mark_public(m) for m in made],
        "kinds_proposed": ["opening"] if made else [],
        "kinds_absent": kinds_absent,
        "openings_without_a_box": no_box or None,
        "openings_without_a_box_note": (
            f"{no_box} opening(s) this read placed on this photo carry NO "
            "box — they cannot be drawn and are NOT placed at a guessed "
            "spot; add them by hand where you see them") if no_box else None,
        "note": ("every proposal is PROVISIONAL — confirm, adjust, refuse "
                 "or delete each one, and add what the read missed. A "
                 "confirm here is EVIDENCE and writes quantity only"),
    }



@router.post("/estimates/{est_id}/photo-takeoff/propose-zones")
async def propose_zones(est_id: str, photo_key: str,
                        user: dict = Depends(get_current_user)):
    """SEND-144 — THE HANDOFF: the finished read's own findings become
    STARTING ZONES on the photo that belongs to that face. It does not
    rebuild measure: no second finder, no re-OCR, no height/gable/dormer
    engine. Body from that face's own width × height, a gable ONLY where
    the read reports a rise, a dormer ONLY where the read reports one
    (basis SAYS UNANCHORED when the read flagged it), and the openings
    through THE EXISTING PROPOSER — one proposer, not two.

    A refused face gets NO zone and answers in the read's own words. A
    corner shot gets none either: it is not a fifth wall."""
    est = await _est_or_404(est_id, user)
    if await is_untouchable(est_id):
        raise HTTPException(
            status_code=423,
            detail="protected estimate — a zone proposal is still a write")
    run = await _photo_read(est_id, photo_key)
    if not run:
        raise HTTPException(
            status_code=400,
            detail=("no completed AI read carries this photo — there are no "
                    "findings to hand off here"))

    async def natural_size(key):
        dims = _photo_natural_size(key)
        if dims:
            return dims
        from config import UPLOAD_DIR
        from upload_store import rehydrate_to_disk
        if await rehydrate_to_disk(key, UPLOAD_DIR):
            return _photo_natural_size(key)
        return None

    row = await propose_zones_for_photo(
        db, run, est_id, user["company_id"], photo_key,
        user.get("email"), natural_size)
    # THE OPENINGS COME THROUGH THE EXISTING PROPOSER — there is one
    # opening proposer in this app and this is a call to it, not a copy.
    openings = None
    if not row["refusal"]:
        try:
            openings = await propose_from_read(est_id, photo_key, user)
        except HTTPException as exc:
            openings = {"ok": False, "proposed": 0, "detail": exc.detail}
    _ = est
    return {
        "ok": True, "run_id": run.get("run_id"),
        "face": row.get("face"), "photo_key": photo_key,
        "zones_proposed": [m["ai"]["ref_id"].split(":")[-1]
                           for m in row.get("marks") or []] or [],
        "proposed": row.get("proposed", 0),
        # SEND-147 — a MOVE is reported as loudly as a placement: a fresh
        # provisional zone may follow a wall_base line the contractor
        # tapped, and a zone he has touched by hand never does.
        "moved": row.get("moved"),
        "wall_base": row.get("wall_base"),
        "already_there": row.get("already_there"),
        "marks": [_mark_public(m) for m in row.get("marks") or []],
        "refusal": row.get("refusal"),
        "notes": row.get("notes"),
        "openings": ({"proposed": openings.get("proposed"),
                      "without_a_box": openings.get("openings_without_a_box"),
                      "note": openings.get("openings_without_a_box_note")}
                     if openings else None),
        "note": ("every zone is PROVISIONAL and its shape is a STARTING "
                 "SHAPE: move it onto the wall you see, add what the read "
                 "missed, then confirm. A confirm is EVIDENCE and writes "
                 "quantity only — no price, no material line"),
    }


@router.post("/estimates/{est_id}/photo-takeoff/apply")
async def apply_photo_takeoff(est_id: str,
                              user: dict = Depends(get_current_user)):
    """CONFIRMED MARKS WRITE QUANTITY — ft², counts — under the photo
    lane's own keys. No priced line and no price key is touched: money
    depends on the product and stays outside this path. A derived write →
    423 on a protected estimate."""
    est = await _est_or_404(est_id, user)
    if await is_untouchable(est_id):
        raise HTTPException(
            status_code=423,
            detail="protected estimate — the photo takeoff write is a "
                   "derived write")
    marks = [_mark_public(m) async for m in db.photo_takeoff_marks.find(
        {"estimate_id": est_id, "company_id": user["company_id"]})]
    scales = {}
    async for s in db.photo_takeoff_scale.find(
            {"estimate_id": est_id, "company_id": user["company_id"]}):
        scales[s["photo_key"]] = _mark_public(s)
    per_photo = {}
    tot_siding = tot_non = tot_open_sqft = 0.0
    tot_gable = tot_dormer_face = tot_dormer_cheek = 0.0
    live_gable = live_dormer_face = live_dormer_cheek = False
    tot_j = tot_rake = 0.0
    live_j = live_rake = False
    tot_open_n = 0
    by_product: Dict[str, float] = {}
    guidance_confirmed = 0
    live = False
    for key in {m["photo_key"] for m in marks}:
        qty = _quantities([m for m in marks if m["photo_key"] == key],
                          scales.get(key))
        per_photo[key] = qty
        for prod, v in (qty.get("siding_by_product") or {}).items():
            by_product[prod] = round(by_product.get(prod, 0.0) + v, 2)
        guidance_confirmed += int(qty.get("guidance_confirmed") or 0)
        # SEND-139 — the gable and dormer lanes total the same way: a
        # lane with nothing measured stays None, never 0.
        if qty.get("gable_sqft") is not None:
            tot_gable += qty["gable_sqft"]
            live_gable = True
        if qty.get("dormer_face_sqft") is not None:
            tot_dormer_face += qty["dormer_face_sqft"]
            live_dormer_face = True
        if qty.get("dormer_cheek_sqft") is not None:
            tot_dormer_cheek += qty["dormer_cheek_sqft"]
            live_dormer_cheek = True
        # SEND-143 — the two PHASE 2 lanes that measure. A refused lane
        # carries None into the write, never a 0, and the four lanes with
        # no mark to read never reach this loop at all.
        if qty.get("j_channel_lf") is not None:
            tot_j += qty["j_channel_lf"]
            live_j = True
        if qty.get("gable_rake_lf") is not None:
            tot_rake += qty["gable_rake_lf"]
            live_rake = True
        for src, add in (("siding_sqft", "siding"), ("non_siding_sqft", "non"),
                         ("opening_sqft", "open_sqft"),
                         ("opening_count", "open_n")):
            v = qty.get(src)
            if v is None:
                continue
            live = True
            if add == "siding":
                tot_siding += v
            elif add == "non":
                tot_non += v
            elif add == "open_sqft":
                tot_open_sqft += v
            else:
                tot_open_n += int(v)
    block = {
        "generated_at": _now(), "generated_by": user.get("email"),
        "phase": 1, "per_photo": per_photo,
        "photo_siding_sqft": round(tot_siding, 2) if live else None,
        "photo_non_siding_sqft": round(tot_non, 2) if live else None,
        "photo_opening_sqft": round(tot_open_sqft, 2) if live else None,
        "photo_opening_count": tot_open_n if live else None,
        "photo_gable_sqft": round(tot_gable, 2) if live_gable else None,
        "photo_dormer_face_sqft": (round(tot_dormer_face, 2)
                                   if live_dormer_face else None),
        "photo_dormer_cheek_sqft": (round(tot_dormer_cheek, 2)
                                    if live_dormer_cheek else None),
        "photo_gable_basis": (
            "½ × width × rise — the triangle drawn on each photo, no field "
            "factor (SEND-137). A face with no photo has no gable here: "
            "nothing is mirrored, nothing is copied from another face"),
        # SEND-143 — PHASE 2 LINEAR RUNS, QUANTITY ONLY. No price, no
        # priced line, no material-list row: quote wiring stays off.
        "photo_j_channel_lf": round(tot_j, 2) if live_j else None,
        "photo_gable_rake_lf": round(tot_rake, 2) if live_rake else None,
        "photo_trim_basis": (
            "J-channel is the perimeter of the box drawn round each opening "
            "on its own photo; the gable rake is the two sloped lines drawn "
            "with each gable triangle, and it is a GABLE-ZONE run that "
            "never joins starter, wall corners or J-channel. Corners, "
            "starter, soffit and horizontal fascia are REFUSED — no corner "
            "tick, no wall base and no eave is marked on any photo, and "
            "none of them is invented"),
        "photo_siding_by_product": by_product or None,
        # NAME THE PLANE (SEND-136): the assumption behind every one of
        # these figures, per photo. UNKNOWN is the honest starting state
        # — it is never defaulted to SQUARE-ON.
        "plane_basis_by_photo": {k: v.get("plane_basis")
                                 for k, v in per_photo.items()},
        "plane_basis_note": (
            "each photo's ft² carries its own plane basis: SQUARE-ON "
            "(earned by that photo's marks), OBLIQUE (the area measures "
            "the wall's projection, and reads LOW), or UNKNOWN (nothing "
            "on the photo supports a verdict). No correction factor is "
            "applied to any of them."),
        "guidance_confirmed_marks": guidance_confirmed or None,
        "guidance_confirmed_note": (
            f"{guidance_confirmed} confirmed mark(s) are GUIDANCE-CONFIRMED "
            "— pre-AI marks confirmed with no AI read on their photo; they "
            "carry quantity and are NOT evidence an AI read was checked")
        if guidance_confirmed else None,
        "note": ("quantity only — confirmed photo marks carry ft² and "
                 "counts under the photo lane's own keys; no price, no "
                 "priced line, no money is written here; openings are "
                 "reported, never deducted (phase 1)"),
    }
    # A SEPARATE PHOTO LANE (Howard ruled 2026-08-26): the four figures
    # land at the estimate's top level under their own photo_* keys and
    # DO NOT mix into `hover_measurements` or any blueprint/derived total.
    # They are outside `EstimateIn`, so no client save can carry, alter,
    # or strip them — the silent-strip class cannot reach this lane.
    await db.estimates.update_one(
        {"id": est_id},
        {"$set": {"photo_takeoff": block,
                  "photo_siding_sqft": block["photo_siding_sqft"],
                  "photo_non_siding_sqft": block["photo_non_siding_sqft"],
                  "photo_opening_sqft": block["photo_opening_sqft"],
                  "photo_opening_count": block["photo_opening_count"],
                  "photo_gable_sqft": block["photo_gable_sqft"],
                  "photo_dormer_face_sqft": block["photo_dormer_face_sqft"],
                  "photo_dormer_cheek_sqft": block["photo_dormer_cheek_sqft"],
                  "photo_j_channel_lf": block["photo_j_channel_lf"],
                  "photo_gable_rake_lf": block["photo_gable_rake_lf"],
                  "updated_at": _now()}})
    return {"ok": True, "photo_takeoff": block}
