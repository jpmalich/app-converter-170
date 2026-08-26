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
PHASE 2 (next pass, NOT built): outside/inside corners, J-channel,
starter, soffit, fascia, finish trim.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from untouchable import is_untouchable

router = APIRouter(tags=["photo-takeoff"])

# PHASE 1 kinds only. A kind outside this set is refused, not guessed —
# phase 2 adds the linear runs.
AREA_KINDS = {"siding_zone", "non_siding_zone"}
OPENING_KINDS = {"opening"}
PHASE1_KINDS = AREA_KINDS | OPENING_KINDS
PHASE2_KINDS = {"outside_corner", "inside_corner", "j_channel", "starter",
                "soffit", "fascia", "finish_trim"}
NON_SIDING_CATEGORIES = {"brick", "stone", "stucco", "garage_door", "other"}
STATUSES = {"provisional", "confirmed", "refused"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


class MarkPatch(BaseModel):
    points: Optional[List[Point]] = None
    category: Optional[str] = None
    label: Optional[str] = None
    status: Optional[str] = None            # confirmed | refused | provisional
    refused_reason: Optional[str] = None


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


def _quantities(marks: List[dict], scale: Optional[dict]) -> dict:
    """Quantity from CONFIRMED marks only, and only with a scale. Every
    refusal is named; a refusal is never reported as 0."""
    ipp, basis = _in_per_px(scale)
    confirmed = [m for m in marks if m.get("status") == "confirmed"]
    provisional = [m for m in marks if m.get("status") == "provisional"]
    out: Dict[str, Any] = {
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
    }
    if not ipp:
        return out
    sq_ft_per_px = (ipp * ipp) / 144.0
    siding = 0.0
    non_siding = 0.0
    by_cat: Dict[str, float] = {}
    op_n = 0
    op_sqft = 0.0
    op_no_extent = 0
    for m in confirmed:
        pts = m.get("points") or []
        area = _poly_area_px(pts) * sq_ft_per_px
        if m["kind"] == "siding_zone":
            siding += area
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
    for key in {m["photo_key"] for m in marks} | set(scales):
        per_photo[key] = {
            "scale": scales.get(key),
            "quantities": _quantities(
                [m for m in marks if m["photo_key"] == key], scales.get(key)),
        }
    return {"ok": True, "phase": 1,
            "kinds": sorted(PHASE1_KINDS),
            "phase2_kinds_not_built": sorted(PHASE2_KINDS),
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
    await _est_or_404(est_id, user)
    if body.kind in PHASE2_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"{body.kind} is a phase-2 linear run — not built yet; "
                   f"phase 1 is {sorted(PHASE1_KINDS)}")
    if body.kind not in PHASE1_KINDS:
        raise HTTPException(status_code=400,
                            detail=f"unknown mark kind {body.kind!r}")
    need = 1 if body.shape == "point" else 3
    pts = [p.model_dump() for p in body.points]
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
    doc = {
        "id": str(uuid4()), "estimate_id": est_id,
        "company_id": user["company_id"], "photo_key": body.photo_key,
        "kind": body.kind, "shape": body.shape, "points": pts,
        "category": body.category, "label": body.label,
        "source": body.source, "status": "provisional",
        "confirmed_at": None, "confirmed_by": None, "refused_reason": None,
        "created_at": _now(), "created_by": user.get("email"),
        "updated_at": _now(),
    }
    await db.photo_takeoff_marks.insert_one(dict(doc))
    return {"ok": True, "mark": _mark_public(doc)}


@router.patch("/estimates/{est_id}/photo-takeoff/marks/{mark_id}")
async def patch_mark(est_id: str, mark_id: str, body: MarkPatch,
                     user: dict = Depends(get_current_user)):
    """Adjust, CONFIRM or REFUSE. Adjusting a confirmed mark returns it to
    PROVISIONAL — the confirmation was of the old geometry, and a
    confirmation cannot outlive the figure it was given for."""
    await _est_or_404(est_id, user)
    key = {"id": mark_id, "estimate_id": est_id,
           "company_id": user["company_id"]}
    cur = await db.photo_takeoff_marks.find_one(key)
    if not cur:
        raise HTTPException(status_code=404, detail="mark not found")
    upd: Dict[str, Any] = {"updated_at": _now()}
    if body.points is not None:
        pts = [p.model_dump() for p in body.points]
        need = 1 if cur.get("shape") == "point" else 3
        if len(pts) < need:
            raise HTTPException(status_code=400,
                               detail=f"a mark needs {need} point(s)")
        upd["points"] = pts
        if cur.get("status") == "confirmed":
            upd.update({"status": "provisional", "confirmed_at": None,
                        "confirmed_by": None,
                        "refused_reason": "geometry changed after "
                                          "confirmation — re-confirm the "
                                          "new figure"})
    if body.category is not None:
        upd["category"] = body.category
    if body.label is not None:
        upd["label"] = body.label
    if body.status is not None:
        if body.status not in STATUSES:
            raise HTTPException(status_code=400,
                               detail=f"status must be one of {sorted(STATUSES)}")
        upd["status"] = body.status
        if body.status == "confirmed":
            upd.update({"confirmed_at": _now(),
                        "confirmed_by": user.get("email"),
                        "refused_reason": None})
        elif body.status == "refused":
            upd.update({"confirmed_at": None, "confirmed_by": None,
                        "refused_reason": (body.refused_reason
                                           or "refused by the contractor")})
        else:
            upd.update({"confirmed_at": None, "confirmed_by": None})
    await db.photo_takeoff_marks.update_one(key, {"$set": upd})
    doc = await db.photo_takeoff_marks.find_one(key)
    return {"ok": True, "mark": _mark_public(doc)}


@router.delete("/estimates/{est_id}/photo-takeoff/marks/{mark_id}")
async def delete_mark(est_id: str, mark_id: str,
                      user: dict = Depends(get_current_user)):
    await _est_or_404(est_id, user)
    res = await db.photo_takeoff_marks.delete_one(
        {"id": mark_id, "estimate_id": est_id,
         "company_id": user["company_id"]})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="mark not found")
    return {"ok": True, "deleted": mark_id}


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
            "status": "provisional", "confirmed_at": None,
            "confirmed_by": None, "refused_reason": None,
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
            "source": "imported_annotation", "status": "provisional",
            "confirmed_at": None, "confirmed_by": None,
            "refused_reason": None, "created_at": _now(),
            "created_by": user.get("email"), "updated_at": _now()})
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
    tot_open_n = 0
    live = False
    for key in {m["photo_key"] for m in marks}:
        qty = _quantities([m for m in marks if m["photo_key"] == key],
                          scales.get(key))
        per_photo[key] = qty
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
                  "updated_at": _now()}})
    return {"ok": True, "photo_takeoff": block}
