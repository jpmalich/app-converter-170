"""AI PHOTO FINDINGS → STARTING ZONES ON THE PHOTO (Howard ruled 2026-08-28,
pro-quote SEND-144).

  8 photos + his annotations → the AI read that ALREADY FINISHED → starting
  zones on those photos → he adjusts and adds what the AI missed →
  CONFIRMED shapes only count.

WHAT THIS MODULE IS:
  · a READER of a finished run. There is NO second finder here: no OCR, no
    photo pass, no height/gable/dormer engine. Every figure it places came
    out of `ai_measure_runs.result` as it stands.
  · a placer of PROVISIONAL shapes. A proposal is not a quantity. Nothing
    here writes an estimate figure, a price or a material line.

THE LAW IT HOLDS:
  · A FACE THE RUN REFUSED GETS NO ZONE — the row says so in the run's own
    words. A width the run marked `assumed_symmetric` is NOT a measured
    width: it was mirrored off the opposite wall, and this send does not
    place a rectangle on it.
  · A CORNER SHOT IS NOT A FIFTH WALL. Zones land only on a photo the run
    itself called a head-on elevation.
  · THE RECTANGLE'S SHAPE comes from that face's own width × height. WHERE
    IT SITS is a starting position and is NOT a measurement — the ft² comes
    from the shape the contractor confirms after he moves it.
  · A CONTESTED HEIGHT IS NOT AVERAGED. Both readings go in the basis and
    the starting rectangle uses the LARGER so it can be pulled down.
  · A GABLE ONLY WHERE THE RUN REPORTS A RISE, using that rise. Pitch never
    creates a triangle here.
  · A DORMER ONLY WHERE THE RUN REPORTS ONE, and when the run flagged the
    width UNANCHORED the basis SAYS UNANCHORED, in the run's own words.
  · A RE-PULL NEVER OVERWRITES A ZONE A HUMAN TOUCHED: proposals are keyed
    (run_id, face:<label>:<part>) and an existing key is left alone.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

HEAD_ON_FACES = ("front", "back", "left", "right")
# SEND-145 (Howard ruled 2026-08-28, after the field run on EST-176308):
# "80% of photo width, near the BOTTOM OF THE PHOTO" was a PHOTO rule, not a
# wall rule — a yard or a patio put the box on the grass and parked the
# dormer on the first floor. THE SHAPE WAS FINE; THE ANCHOR WAS WRONG.
#
# The anchor order, as ruled. (1) BECAME REAL IN SEND-147; (2) is still the
# door it will be the day the read writes pixels for that bar, and (4) SAYS SO
# OUT LOUD:
#   1. THE WALL-BASE MARK on that photo — REAL AS OF SEND-147: a HUMAN
#      TWO-TAP (`kind: wall_base`) that stores its two ends and its own y.
#      It BEATS the door sill and it BEATS the window-indeterminate answer.
#      (The SEND-144 candidate EDGE is still derived FROM the body zone, so
#      reading THAT back would be circular — this rung reads the tapped
#      mark, never the drawn candidate.)
#   2. the WALL REF bar                                       — the read
#      names it in prose only; it writes no pixel geometry for it.
#   3. THE READ'S OWN FIRST-FLOOR OPENING BOXES — real pixels on the wall,
#      each with its own measured width. The BIGGEST sets the plane scale.
#      The bottom is CLASSIFIED first (SEND-146): the lowest DOOR TO GRADE
#      sets it; a WINDOW sill is MID-WALL and sets nothing. A gable-peak
#      window and a dormer opening set NEITHER.
#   4. else the photo bottom at 80% width, and the basis says it is a PHOTO
#      EDGE, NOT A WALL LINE — indeterminate, never a silent fallback that
#      looks measured.
BODY_WIDTH_FRAC = 0.80
MAX_SET_HEIGHT_FRAC = 0.80
BODY_BOTTOM_FRAC = 0.92
ZONE_ORIGIN = "ai_zone_proposal"

# SEND-146 (Howard ruled 2026-08-28, after the field run on SEND-145's boxes):
# SEND-145 took the LOWEST first-floor opening's sill as the wall bottom. That
# is true only when the opening is a DOOR TO GRADE. On EST-176308's LEFT the
# lowest opening is a Double Hung window, and **A WINDOW SILL IS MID-WALL**:
# the box started at the sills and left the starter-to-sill strip of siding
# outside it. So the bottom is classified BEFORE it is placed:
#   DOOR-TO-GRADE → its sill MAY set the body bottom, and the basis NAMES it.
#   WINDOW        → its sill must NOT set the body bottom: the bottom is
#                   INDETERMINATE, the box keeps its top and its width, and
#                   NO drop from the sill and NO typical sill height is used.
#   NONE          → the photo-bottom answer of SEND-145, unchanged.
# The classification is a read of the row's OWN `type`, which the run already
# carries. There is NO new detector, and `style` never promotes a window: a
# "2-Lite Slider" WINDOW is a window; only a `type` in this tuple is a door.
DOOR_TO_GRADE_TYPES = ("garage_door", "entry_door", "patio_door",
                       "sliding_glass_door", "slider_door", "french_door")

WINDOW_SILL_SENTENCE = (
    "BOTTOM IS INDETERMINATE: no door-to-grade opening on this photo — bottom "
    "is not a wall line")

PHOTO_BOTTOM_SENTENCE = (
    "no first-floor opening on this photo carries a typed size, so there is "
    "NO SCALE FROM OPENINGS here and none is guessed: the box is 80% of the "
    "photo's width sitting at the PHOTO BOTTOM, which is a photo edge and "
    "NOT a wall line — INDETERMINATE, move it onto the wall you see")

PLACEMENT_SENTENCE = (
    "the rectangle's SHAPE comes from those figures; WHERE IT SITS on this "
    "photo is a starting position and NOT a measurement — the ft² comes from "
    "the shape you confirm after you move it")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_photo_names(run: dict) -> List[str]:
    return [n for n in str(run.get("photo_paths") or "").split(",") if n]


def _raw(run: dict) -> dict:
    return ((run.get("result") or {}).get("raw_ai") or {})


def _measurements(run: dict) -> dict:
    return ((run.get("result") or {}).get("measurements") or {})


def _wall(run: dict, face: str) -> Optional[dict]:
    for w in (_raw(run).get("walls") or []):
        if isinstance(w, dict) and str(w.get("label") or "").lower() == face:
            return w
    return None


def _refusal_for_face(run: dict, face: str) -> Optional[str]:
    """The RUN'S OWN words when it refused this face. Nothing is rephrased
    into something softer, and nothing is invented when it did not refuse."""
    m = _measurements(run)
    for r in (m.get("_faces_refused") or []):
        if str(r.get("label") or "").lower() == face:
            return str(r.get("refusal") or f"{face.upper()} — refused by the read")
    measured = [str(x).lower() for x in (m.get("_faces_measured") or [])]
    if measured and face not in measured:
        return (f"{face.upper()} — this read did not measure this face, so "
                "there is no width to shape a zone from. Not measured. Not "
                "copied from another face")
    w = _wall(run, face)
    if not w:
        return (f"{face.upper()} — this read carries no wall entry for this "
                "face: no measured width, no zone")
    if not float(w.get("width_ft") or 0) > 0:
        return (f"{face.upper()} — no measured width on this face. Not "
                "measured. Not copied from another face")
    src = str(w.get("width_ft_source") or "")
    if src and src != "direct_ref" and "direct" not in src:
        return (f"{face.upper()} — no measured width on this face: the read's "
                f"{w.get('width_ft')} ft is `{src}`, not a measurement. Not "
                "copied from another face")
    return None


def face_for_photo(run: dict, photo_key: str) -> dict:
    """Which face's zone set belongs on THIS photo — or the named reason no
    zone does."""
    names = _run_photo_names(run)
    if photo_key not in names:
        return {"face": None, "refusal": (
            "this photo is not in that read — a read on another photo "
            "unlocks nothing here")}
    idx = names.index(photo_key)
    entry = None
    for p in (_raw(run).get("photos") or []):
        if isinstance(p, dict) and p.get("index") == idx:
            entry = p
            break
    elev = str((entry or {}).get("elevation") or "").strip().lower()
    if not elev:
        return {"face": None, "photo_index": idx, "refusal": (
            "the read did not name an elevation for this photo, so no face "
            "owns it — no zone is placed on a plane the read never called")}
    if elev not in HEAD_ON_FACES:
        return {"face": None, "photo_index": idx, "refusal": (
            f"the read calls this photo a {elev.upper()} shot — a corner shot "
            "is NOT a fifth wall: it shows two faces foreshortened and the "
            "read measured neither plane here. Zones land on a face's own "
            "head-on photo")}
    refusal = _refusal_for_face(run, elev)
    if refusal:
        return {"face": elev, "photo_index": idx,
                "refusal": refusal + " — no body zone, no gable zone, no "
                                     "dormer zone"}
    return {"face": elev, "photo_index": idx, "refusal": None,
            "wall": _wall(run, elev)}


def _height_for(wall: dict) -> tuple[float, Optional[str]]:
    """A CONTESTED HEIGHT IS NOT AVERAGED (Howard, SEND-144). Both readings
    are named and the starting rectangle takes the LARGER so it can be
    pulled down."""
    h = float(wall.get("height_ft") or 0)
    readings = []
    for r in (wall.get("_per_photo_readings") or []):
        if isinstance(r, dict) and r.get("eave_ft"):
            readings.append(round(float(r["eave_ft"]), 2))
    src = str(wall.get("height_ft_source") or "")
    if src == "direct_disagreement" and len(set(readings)) > 1:
        pair = " vs ".join(f"{v} ft" for v in sorted(set(readings), reverse=True))
        return max(readings), (
            f"the read's height readings DISAGREE: {pair} — NOT averaged. The "
            f"starting rectangle uses the larger ({max(readings)} ft) so you "
            "can pull it down; it is not a measurement until you confirm the "
            "shape")
    return h, None


def _dormer_for(run: dict, face: str) -> tuple[Optional[dict], Optional[str]]:
    """The run's own dormer for this face, plus its UNANCHORED message when
    the run flagged the width as having no reference marker in frame."""
    d = None
    for entry in (_raw(run).get("dormers") or []):
        if isinstance(entry, dict) and str(entry.get("face") or "").lower() == face:
            d = entry
            break
    if not d:
        return None, None
    unanchored = None
    for hint in (_measurements(run).get("_ai_pin_gap_hints") or []):
        if (str(hint.get("kind") or "") == "unanchored_dormer_width"
                and str(hint.get("elevation") or "").lower() == face):
            unanchored = str(hint.get("message") or "")
            break
    return d, unanchored


def _two_tap_line_mark(marks_on_photo, kind: str) -> Optional[dict]:
    """The tapped two-tap ANCHOR of one `kind` on THIS photo — `wall_base`
    (SEND-147, the body BOTTOM) or `eave` (SEND-149, the body TOP).

    A REFUSED line is not an anchor. A CONFIRMED one wins over a provisional
    one, and among equals the LATEST tap governs — the contractor's most
    recent word about his own line. Nothing is copied from another photo: the
    caller only ever passes THIS photo's marks."""
    best = None
    for m in (marks_on_photo or []):
        if m.get("kind") != kind or m.get("status") == "refused":
            continue
        rec = m.get(kind) or {}
        try:
            y = float(rec["y"])
        except (KeyError, TypeError, ValueError):
            continue
        rank = (1 if m.get("status") == "confirmed" else 0,
                str(m.get("updated_at") or m.get("created_at") or ""))
        if best is None or rank > best[0]:
            best = (rank, {"y": y, "a": rec.get("a"), "b": rec.get("b"),
                           "tilt_px": rec.get("tilt_px"), "kind": kind,
                           "status": m.get("status"), "mark_id": m.get("id")})
    return best[1] if best else None


def _base_mark_line(marks_on_photo) -> Optional[dict]:
    """ANCHOR 1 — THE WALL-BASE MARK (SEND-147, Howard's option 2). A human
    two-tap on THAT photo, stored as kind `wall_base` with its own `a`, `b`
    and `y`. When one exists it BEATS the door sill and it BEATS the
    window-indeterminate answer."""
    return _two_tap_line_mark(marks_on_photo, "wall_base")


def _eave_mark_line(marks_on_photo) -> Optional[dict]:
    """SEND-149 — THE EAVE MARK. The same gesture at the OTHER end of the
    wall: when one exists on that photo it sets the BODY TOP, and the box's
    height stops being the read's claim and becomes the span between two
    lines the contractor tapped. No eave mark → the top stays exactly as it
    is."""
    return _two_tap_line_mark(marks_on_photo, "eave")

def _wall_ref_bar(run: dict, photo_idx: int) -> None:
    """ANCHOR 2 — the WALL REF bar. The read NAMES it in prose
    (`eave_reasoning`, `notes`) but writes no pixel geometry for it, so there
    is nothing to anchor to. Prose is not a position."""
    return None


def _is_door_to_grade(o: dict) -> bool:
    """A read of the opening row's OWN `type`. `style` is never consulted —
    a 2-Lite Slider WINDOW is a window; an unrecognised type is NOT a door to
    grade, so it falls to INDETERMINATE rather than to a guess."""
    return str(o.get("type") or "").strip().lower() in DOOR_TO_GRADE_TYPES


def first_floor_anchor(run: dict, photo_idx: int, nat_w: float, nat_h: float,
                       height_ft: float) -> Optional[dict]:
    """ANCHOR 3 — THE READ'S OWN FIRST-FLOOR OPENING BOXES.

    The BIGGEST first-floor box sets the plane SCALE, because its own width is
    measured in inches and its box is measured in pixels — the read's own
    evidence, named on the row, never averaged. A window is an honest RULER.

    The BOTTOM is classified first (SEND-146): the lowest **DOOR TO GRADE**
    sets it and is NAMED; if the lowest opening is a WINDOW its sill is
    MID-WALL and sets nothing — the bottom is INDETERMINATE and the box keeps
    its top and its width.

    A DORMER opening (`on_dormer`) and a GABLE-PEAK window set neither: the
    gable window is dropped because it sits ABOVE the wall band that the
    lowest box plus the run's own wall height describes.
    """
    cands = []
    for o in (_raw(run).get("openings") or []):
        if not isinstance(o, dict) or o.get("bbox_photo_idx") != photo_idx:
            continue
        bb = o.get("bbox") or {}
        try:
            w_ft = float(o.get("width_in") or 0) / 12.0
            box = (float(bb["x"]), float(bb["y"]), float(bb["w"]), float(bb["h"]))
        except (KeyError, TypeError, ValueError):
            continue
        if o.get("on_dormer") or not w_ft > 0 or not box[2] > 0:
            continue
        cands.append((o, box, w_ft))
    if not cands:
        return None
    low, low_box, low_ft = max(cands, key=lambda c: c[1][1] + c[1][3])
    seed_bottom_n = low_box[1] + low_box[3]
    seed_ppf = (low_box[2] * nat_w) / low_ft
    band_top_n = seed_bottom_n - (height_ft * seed_ppf / nat_h if nat_h else 0)
    first, dropped = [], []
    for c in cands:
        if (c[1][1] + c[1][3]) >= band_top_n:
            first.append(c)
        else:
            dropped.append(c[0].get("opening_id"))
    if not first:
        return None
    doors = [c for c in first if _is_door_to_grade(c[0])]
    if doors:
        low_o, low_obox, _ = max(doors, key=lambda c: c[1][1] + c[1][3])
        bottom_n = low_obox[1] + low_obox[3]
        bottom_kind = "door_to_grade"
        bottom_from = low_o.get("opening_id")
        bottom_sill_of = None
        below = [c[0].get("opening_id") for c in first
                 if not _is_door_to_grade(c[0])
                 and (c[1][1] + c[1][3]) > bottom_n] or None
    else:
        low_o, low_obox, _ = max(first, key=lambda c: c[1][1] + c[1][3])
        bottom_n = low_obox[1] + low_obox[3]
        bottom_kind = "window_sill_indeterminate"
        bottom_from = None
        bottom_sill_of = low_o.get("opening_id")
        below = None
    big, big_box, big_ft = max(first, key=lambda c: c[1][2])
    ppf = (big_box[2] * nat_w) / big_ft
    x_lo = min(c[1][0] for c in first) * nat_w
    x_hi = max(c[1][0] + c[1][2] for c in first) * nat_w
    return {
        "ppf": ppf,
        "bottom_px": bottom_n * nat_h,
        "center_px": (x_lo + x_hi) / 2.0,
        "bottom_kind": bottom_kind,
        "bottom_from": bottom_from,
        "bottom_sill_of": bottom_sill_of,
        "bottom_type": str(low_o.get("type") or "") or None,
        "bottom_style": str(low_o.get("style") or "") or None,
        "windows_below_the_door": below,
        "scale_from": big.get("opening_id"),
        "scale_from_ft": round(big_ft, 2),
        "scale_from_px": round(big_box[2] * nat_w),
        "dropped_above_the_wall_band": dropped or None,
        "first_floor_boxes": len(first),
        "doors_to_grade": [c[0].get("opening_id") for c in doors] or None,
    }


def _scale_note(anchor: dict) -> str:
    return (
        "SCALE from '" + str(anchor["scale_from"]) + "' ("
        f"{anchor['scale_from_ft']} ft wide, {anchor['scale_from_px']} px "
        "on this photo), the biggest first-floor box the read measured; "
        "no scale is averaged and no course height is guessed"
        + (f". Dropped above the wall band (not first floor): "
           f"{', '.join(anchor['dropped_above_the_wall_band'])}"
           if anchor["dropped_above_the_wall_band"] else ""))


def build_zone_marks(run: dict, face: str, wall: dict, photo_key: str,
                     nat_w: float, nat_h: float, est_id: str,
                     company_id: str, created_by: Optional[str],
                     base_mark: Optional[dict] = None,
                     eave_mark: Optional[dict] = None) -> List[dict]:
    """The starting shapes for ONE face, in that photo's own pixels. Every
    figure comes from `run`; the placement is stated as a placement.

    SEND-147 — a WALL_BASE mark on this photo (`base_mark`) sets the body
    bottom and BEATS both opening answers. The plane SCALE still comes from
    the read's own biggest first-floor box: a start line says WHERE the wall
    ends, never HOW BIG a foot is.

    SEND-149 — an EAVE mark (`eave_mark`) sets the body TOP the same way, and
    then the box's HEIGHT is the span between two lines HE tapped instead of
    the read's claim. Both figures are printed and neither is averaged."""
    width_ft = float(wall.get("width_ft") or 0)
    if not width_ft > 0 or not (nat_w > 0 and nat_h > 0):
        return []
    height_ft, disagreement = _height_for(wall)
    if not height_ft > 0:
        return []
    rise_ft = float(wall.get("gable_triangle_height_ft") or 0)
    dormer, unanchored = _dormer_for(run, face)
    dormer_w = float((dormer or {}).get("width_ft") or 0)
    dormer_h = float((dormer or {}).get("knee_wall_height_ft") or 0)
    has_dormer = bool(dormer and dormer_w > 0 and dormer_h > 0
                      and float(wall.get("dormer_face_sqft") or 0) > 0)
    idx = None
    names = _run_photo_names(run)
    if photo_key in names:
        idx = names.index(photo_key)
    anchor = (first_floor_anchor(run, idx, nat_w, nat_h, height_ft)
              if idx is not None else None)
    base_y = None
    if base_mark:
        try:
            base_y = float(base_mark["y"])
        except (KeyError, TypeError, ValueError):
            base_y = None
    if base_y is not None:
        # SEND-147 — THE START LINE GOVERNS. Its y is the body bottom; the
        # scale still comes from the read's own biggest first-floor box where
        # one exists, and the 80%-of-frame fallback ONLY where it does not.
        if anchor:
            ppf = anchor["ppf"]
            scale_note = _scale_note(anchor)
        else:
            above_ft = max(rise_ft, dormer_h if has_dormer else 0.0)
            ppf = min(BODY_WIDTH_FRAC * nat_w / width_ft,
                      MAX_SET_HEIGHT_FRAC * nat_h / (height_ft + above_ft))
            scale_note = (
                "no first-floor opening on this photo carries a typed size, so "
                "the WIDTH of the box is 80% of the frame and INDETERMINATE — "
                "only the BOTTOM is evidence here")
        body_w = width_ft * ppf
        body_h = height_ft * ppf
        y1 = base_y
        y0 = y1 - body_h
        x0 = ((anchor["center_px"] if anchor else nat_w / 2.0) - body_w / 2.0)
        anchor_note = (
            "bottom from wall_base mark on this photo — the start line YOU "
            f"tapped ({base_mark.get('status')}, y={round(base_y, 1)} px"
            + (f", tilt {base_mark.get('tilt_px')} px across its two ends"
               if base_mark.get("tilt_px") else "")
            + "), which beats every opening: an opening sill is not the wall "
              "base. "
            + scale_note)
    elif anchor:
        ppf = anchor["ppf"]
        body_w = width_ft * ppf
        body_h = height_ft * ppf
        y1 = anchor["bottom_px"]
        y0 = y1 - body_h
        x0 = anchor["center_px"] - body_w / 2.0
        scale_note = _scale_note(anchor)
        if anchor["bottom_kind"] == "door_to_grade":
            anchor_note = (
                f"BOTTOM anchored to the sill line of '{anchor['bottom_from']}'"
                f" — a DOOR TO GRADE ({anchor['bottom_type']}) THE READ boxed "
                "on this photo — because the wall BASE is not marked here: "
                "pull it down to the start line. "
                + scale_note
                + (". A window sill is MID-WALL and set nothing here: "
                   f"{', '.join(anchor['windows_below_the_door'])}"
                   if anchor["windows_below_the_door"] else ""))
        else:
            anchor_note = (
                WINDOW_SILL_SENTENCE
                + f". The lowest first-floor opening the read boxed is "
                f"'{anchor['bottom_sill_of']}' ({anchor['bottom_type']}"
                + (f", {anchor['bottom_style']}" if anchor["bottom_style"] else "")
                + "), and A WINDOW SILL IS MID-WALL — it does not set the wall "
                  "bottom. No drop from a sill is invented and no typical sill "
                  "height is used: the box keeps its TOP and its WIDTH and the "
                  "bottom edge is only drawn where that sill happens to be — "
                  "pull it down to the start line. "
                + scale_note)
    else:
        above_ft = max(rise_ft, dormer_h if has_dormer else 0.0)
        ppf = min(BODY_WIDTH_FRAC * nat_w / width_ft,
                  MAX_SET_HEIGHT_FRAC * nat_h / (height_ft + above_ft))
        body_w = width_ft * ppf
        body_h = height_ft * ppf
        x0 = (nat_w - body_w) / 2.0
        y1 = BODY_BOTTOM_FRAC * nat_h
        y0 = y1 - body_h
        anchor_note = PHOTO_BOTTOM_SENTENCE
    # SEND-149 — THE TOP COMES FROM THE EAVE MARK WHEN ONE IS TAPPED. The
    # bottom does not move, not one x changes, and the height the two lines
    # imply is NAMED beside the read's own claim — never averaged with it.
    eave_y = None
    if eave_mark:
        try:
            eave_y = float(eave_mark["y"])
        except (KeyError, TypeError, ValueError):
            eave_y = None
    if eave_y is not None:
        if eave_y < y1 - 1:
            marked_ft = round((y1 - eave_y) / ppf, 2)
            y0 = eave_y
            body_h = y1 - y0
            anchor_note += (
                ". top from eave mark on this photo — the frieze YOU tapped ("
                f"{eave_mark.get('status')}, y={round(eave_y, 1)} px"
                + (f", tilt {eave_mark.get('tilt_px')} px across its two ends"
                   if eave_mark.get("tilt_px") else "")
                + f"), so this box's HEIGHT is the span between two lines you "
                f"tapped: {marked_ft} ft at this photo's scale, NOT the read's "
                f"{height_ft} ft claim. Both figures are printed and neither is "
                "averaged")
        else:
            anchor_note += (
                f". The eave line you tapped (y={round(eave_y, 1)} px) sits at "
                "or BELOW this box's bottom, so it cannot be a top: the TOP was "
                "NOT moved and nothing was guessed — re-tap the frieze above "
                "the start line")
    clamped = []
    if x0 < 0 or x0 + body_w > nat_w:
        clamped.append("the sides run past the frame edge")
    if y0 < 0:
        clamped.append("the top runs past the frame edge")

    def cl(x, hi):
        return max(0.0, min(float(x), hi))

    if clamped:
        anchor_note += (
            f". The wall as read ({width_ft} ft × {height_ft} ft at this "
            f"photo's scale) does not fit the frame — {', and '.join(clamped)}"
            ", so the box is cut at the photo edge: move the sides onto what "
            "you can actually see")
    src_note = (f"width {wall.get('width_ft_source')}, height "
                f"{wall.get('height_ft_source')}, confidence "
                f"{wall.get('confidence')}")

    def base(part: str, kind: str, shape: str, pts: List[dict], label: str,
             basis: str, extra: Optional[dict] = None) -> dict:
        m = {
            "id": str(uuid4()), "estimate_id": est_id,
            "company_id": company_id, "photo_key": photo_key,
            "kind": kind, "shape": shape, "points": pts,
            "category": None, "label": label,
            "source": ZONE_ORIGIN, "style": None,
            "width_in": None, "height_in": None,
            "product": None, "product_history": [],
            "confirmed_under_product": None,
            "symmetric": None, "pitch_set": None, "depth_ft": None,
            "origin": ZONE_ORIGIN, "stage": 2, "basis": basis,
            "ai": {"run_id": run.get("run_id"),
                   "ref_id": f"face:{face}:{part}",
                   "face": face,
                   "claimed_width_ft": width_ft,
                   "claimed_height_ft": height_ft,
                   "width_source": wall.get("width_ft_source"),
                   "height_source": wall.get("height_ft_source"),
                   "confidence": wall.get("confidence"),
                   "placement": "starting position, not a measurement"},
            "status": "provisional", "confirmed_at": None,
            "confirmed_by": None, "confirmed_stage": None,
            "confirmed_basis": None, "confirmed_after_ai_read": None,
            "refused_reason": None, "created_at": _now(),
            "created_by": created_by, "updated_at": _now()}
        if extra:
            m["ai"].update(extra)
        return m

    out: List[dict] = []
    body_basis = (f"AI STARTING ZONE — the read measured this {face.upper()} "
                  f"face at {width_ft} ft × {height_ft} ft ({src_note}). "
                  + PLACEMENT_SENTENCE
                  + (f". {disagreement}" if disagreement else "")
                  + ". " + anchor_note)
    out.append(base("body", "siding_zone", "rect",
                    [{"x": cl(x0, nat_w), "y": cl(y0, nat_h)},
                     {"x": cl(x0 + body_w, nat_w), "y": cl(y0, nat_h)},
                     {"x": cl(x0 + body_w, nat_w), "y": cl(y1, nat_h)},
                     {"x": cl(x0, nat_w), "y": cl(y1, nat_h)}],
                    f"AI {face} body", body_basis,
                    {"height_readings_disagree": bool(disagreement),
                     "anchor": (
                         "wall_base_mark" if base_y is not None
                         else ("first_floor_door_to_grade"
                               if anchor["bottom_kind"] == "door_to_grade"
                               else "window_sill_indeterminate") if anchor
                         else "photo_bottom_indeterminate"),
                     "top_anchor": ("eave_mark" if eave_y is not None
                                    and eave_y < y1 - 1
                                    else "read_height_claim"),
                     "anchor_eave_mark": (eave_mark or {}).get("mark_id"),
                     "anchor_eave_y": (round(eave_y, 3)
                                       if eave_y is not None else None),
                     "anchor_wall_base_mark": (base_mark or {}).get("mark_id"),
                     "anchor_wall_base_y": (round(base_y, 3)
                                            if base_y is not None else None),
                     "anchor_bottom_from": (anchor or {}).get("bottom_from"),
                     "anchor_bottom_sill_of": (anchor or {}).get("bottom_sill_of"),
                     "anchor_scale_from": (anchor or {}).get("scale_from"),
                     "px_per_ft": round(ppf, 2)}))
    if rise_ft > 0:
        rise_px = rise_ft * ppf
        out.append(base(
            "gable", "gable", "poly",
            [{"x": cl(x0, nat_w), "y": cl(y0, nat_h)},
             {"x": cl(x0 + body_w / 2.0, nat_w), "y": cl(y0 - rise_px, nat_h)},
             {"x": cl(x0 + body_w, nat_w), "y": cl(y0, nat_h)}],
            f"AI {face} gable",
            (f"AI STARTING SHAPE — the read reports a gable RISE of "
             f"{rise_ft} ft on this face; that figure is its own, NOT derived "
             f"from a pitch. The triangle is a starting shape: ½ × width × "
             f"rise comes from the triangle you confirm, in this photo's own "
             f"scale. It stacks on the body top, in the body's own "
             f"px-per-foot"),
            {"claimed_gable_rise_ft": rise_ft}))
    if has_dormer:
        d_w = dormer_w * ppf
        d_h = dormer_h * ppf
        try:
            off = float(dormer.get("offset_x_ft") or 0) * ppf
        except (TypeError, ValueError):
            off = 0.0
        cx = x0 + body_w / 2.0 + off
        # SEND-145 — THE DORMER SITS ABOVE THE BODY TOP, on the upper-wall /
        # roof-face region of THIS photo. It never reuses the body's
        # photo-bottom: that rule is what parked it on the first floor.
        out.append(base(
            "dormer", "dormer", "poly",
            [{"x": cl(cx - d_w / 2.0, nat_w), "y": cl(y0, nat_h)},
             {"x": cl(cx + d_w / 2.0, nat_w), "y": cl(y0, nat_h)},
             {"x": cl(cx + d_w / 2.0, nat_w), "y": cl(y0 - d_h, nat_h)},
             {"x": cl(cx - d_w / 2.0, nat_w), "y": cl(y0 - d_h, nat_h)}],
            f"AI {face} dormer",
            (f"AI STARTING SHAPE — the read reports a dormer "
             f"{dormer_w} ft wide × {dormer_h} ft knee wall on this face "
             f"({dormer.get('width_source')}). "
             + (f"UNANCHORED: {unanchored}" if unanchored else
                "the read anchored this width to a reference in frame")
             + ". It is placed ABOVE THE BODY TOP, on the upper wall of this "
               "photo — never at the photo bottom. The depth is NOT typed, so "
               "the cheeks refuse until you type it"),
            {"claimed_dormer_width_ft": dormer_w,
             "claimed_dormer_knee_ft": dormer_h,
             "unanchored": bool(unanchored),
             "unanchored_message": unanchored}))
    return out


async def existing_refs(db, est_id: str, company_id: str, photo_key: str,
                        run_id: str) -> set:
    have = set()
    async for m in db.photo_takeoff_marks.find(
            {"estimate_id": est_id, "company_id": company_id,
             "photo_key": photo_key}):
        ai = m.get("ai") or {}
        if ai.get("run_id") and ai.get("ref_id"):
            have.add((ai["run_id"], ai["ref_id"]))
    return have


async def propose_zones_for_photo(db, run: dict, est_id: str, company_id: str,
                                  photo_key: str, created_by: Optional[str],
                                  natural_size, place_new: bool = True,
                                  scope: str = "all") -> dict:
    """Place (or decline to place) one face's zone set on one photo.
    Returns the report row — the refusal is as much of an answer as the
    zones are.

    SEND-147 — with `place_new=False` this is a REBASE and nothing new is
    placed: a wall-base tap may only MOVE zones that are already here and
    still fresh. Tapping a start line never conjures a zone set."""
    who = face_for_photo(run, photo_key)
    if who.get("refusal"):
        return {"photo_key": photo_key, "face": who.get("face"),
                "proposed": 0, "marks": [], "refusal": who["refusal"]}
    face, wall = who["face"], who["wall"]
    dims = await natural_size(photo_key)
    if not dims:
        return {"photo_key": photo_key, "face": face, "proposed": 0,
                "marks": [], "refusal": (
                    "this photo's file cannot be found, so a zone cannot be "
                    "placed in its own pixels — nothing is placed on a "
                    "guessed size")}
    nat_w, nat_h = dims
    marks_here = [m async for m in db.photo_takeoff_marks.find(
        {"estimate_id": est_id, "company_id": company_id,
         "photo_key": photo_key})]
    base_mark = _base_mark_line(marks_here)
    eave_mark = _eave_mark_line(marks_here)
    built = build_zone_marks(run, face, wall, photo_key, nat_w, nat_h,
                             est_id, company_id, created_by,
                             base_mark=base_mark, eave_mark=eave_mark)
    by_ref = {}
    for m in marks_here:
        ai = m.get("ai") or {}
        if ai.get("run_id") and ai.get("ref_id"):
            by_ref[(ai["run_id"], ai["ref_id"])] = m
    made, moved, notes = [], [], []
    for m in built:
        key = (m["ai"]["run_id"], m["ai"]["ref_id"])
        cur = by_ref.get(key)
        if cur is None:
            if place_new:
                made.append(m)
            continue
        # A PLAIN RE-PULL STILL OVERWRITES NOTHING (SEND-144). A zone only
        # moves when the ANCHOR changed: a tapped line exists, or one was
        # just removed and this is the REBASE that follows.
        if base_mark is None and eave_mark is None and place_new:
            continue
        # SEND-149 — AN EAVE TAP MAY ONLY MOVE THE BODY. "Do not reshape the
        # gable or the dormer in this send. They stay where they are."
        part = str((cur.get("ai") or {}).get("ref_id") or "").split(":")[-1]
        if scope == "body" and part != "body":
            notes.append(
                f"'{cur.get('label')}' was not moved: an eave line only sets "
                "the BODY top in this send — the gable and the dormer stay "
                "exactly where they are")
            continue
        # SEND-147 — A FRESH PROVISIONAL ZONE IS RE-PLACED WHOLE on the new
        # anchor: body, gable and dormer together, since the gable and the
        # dormer stack on the body top.
        #
        # SEND-148 (Howard ruled 2026-08-29) — A HAND NO LONGER BLOCKS A
        # START LINE HE JUST MARKED: "FRONT's tweaked body should FOLLOW the
        # wall_base tap. A start line he just marked outranks the old drag.
        # Do not clear the zone. Do not touch the gable." So on a
        # HUMAN-TOUCHED BODY only the BOTTOM EDGE is pulled to the line —
        # the zone is not cleared and not re-placed, his other edges are HIS
        # and stay — and a touched GABLE or DORMER is not touched at all.
        why = _zone_is_human_touched(cur)
        if why:
            follow = await _edge_follows_the_line(
                db, est_id, company_id, cur, base_mark, why, "bottom")
            top = await _edge_follows_the_line(
                db, est_id, company_id, cur, eave_mark, why, "top")
            follow = " ".join(x for x in (follow, top) if x) or None
            if follow:
                notes.append(follow)
                moved.append(dict(m, id=cur["id"]))
            else:
                notes.append(
                    f"'{cur.get('label')}' was not moved: {why} — your hand "
                    "outranks the anchor. Delete it if you want it "
                    "re-placed on the line you tapped")
            continue
        stamp = _now()
        await db.photo_takeoff_marks.update_one(
            {"id": cur["id"], "estimate_id": est_id, "company_id": company_id},
            {"$set": {"points": m["points"], "basis": m["basis"],
                      "ai": m["ai"], "updated_at": stamp,
                      "rebased_at": stamp}})
        moved.append(dict(m, id=cur["id"]))
    if made:
        await db.photo_takeoff_marks.insert_many([dict(m) for m in made])
    #  SEND-149 — IF THE NEW TOP CROSSES A DORMER, REPORT IT. No auto-fix.
    if eave_mark and moved:
        top_y = float(eave_mark["y"])
        for cur in by_ref.values():
            if str((cur.get("ai") or {}).get("ref_id") or "").endswith(":dormer"):
                low = max(float(p["y"]) for p in (cur.get("points") or [{"y": 0}]))
                if low > top_y + 1:
                    notes.append(
                        f"THE NEW BODY TOP CROSSES '{cur.get('label')}': the "
                        f"eave line you tapped sits at y={round(top_y, 1)} px "
                        f"and that dormer reaches down to y={round(low, 1)} px, "
                        "so the two overlap on this photo. NOTHING was "
                        "auto-fixed and the dormer was not moved — this is "
                        "reported for you to settle")
    if moved:
        notes.append(
            f"{len(moved)} provisional zone(s) MOVED to "
            + ((("the line(s) you tapped on this photo ("
                 + ", ".join(
                     ([f"wall_base y={round(float(base_mark['y']), 1)} px"]
                      if base_mark else [])
                     + ([f"eave y={round(float(eave_mark['y']), 1)} px"]
                        if eave_mark else []))
                 + ")")) if (base_mark or eave_mark) else
               "the read's own answer, because the wall_base line on this "
               "photo is gone")
            + ". A body you had moved by hand keeps its own sides — only the "
              "edge you anchored followed the line, never the other one; a "
              "gable or dormer you touched was not moved at all")
    for row in (_measurements(run).get("_per_elevation_breakdown") or []):
        if str(row.get("label") or "").lower() == face:
            stone = float(row.get("stone_sqft") or 0)
            if stone > 0:
                notes.append(
                    f"the read reports {stone} ft² of {row.get('stone_callout') or 'stone/brick'} "
                    "no-siding on this face and carries NO geometry for it — "
                    "masks are an INPUT to the read, never an output. Draw "
                    "the non-siding zone yourself; nothing is placed at a "
                    "guessed spot")
    return {"photo_key": photo_key, "face": face, "proposed": len(made),
            "marks": made, "refusal": None,
            "moved": len(moved) or None,
            "wall_base": ({"y": base_mark["y"], "status": base_mark["status"],
                           "mark_id": base_mark["mark_id"]}
                          if base_mark else None),
            "eave": ({"y": eave_mark["y"], "status": eave_mark["status"],
                      "mark_id": eave_mark["mark_id"]}
                     if eave_mark else None),
            "already_there": len(by_ref) or None, "notes": notes or None}


async def _edge_follows_the_line(db, est_id: str, company_id: str,
                                 cur: dict, line: Optional[dict], why: str,
                                 edge: str) -> Optional[str]:
    """SEND-148 — THE START LINE OUTRANKS THE OLD DRAG, FOR THE BODY ONLY, and
    SEND-149 — THE EAVE LINE DOES THE SAME AT THE TOP.

    The zone is NOT cleared and NOT re-placed: the two LOWEST vertices (for a
    `wall_base`) or the two HIGHEST (for an `eave`) of the box he already
    moved are pulled to the tapped line's y, and NOTHING ELSE is touched —
    not one x, and never the other edge. His sides are his own evidence and
    they stay. A GABLE or a DORMER he touched is left alone entirely.

    A CONFIRMED zone whose geometry changes goes back to PROVISIONAL: a
    confirmation cannot outlive the figure it was given for."""
    if line is None:
        return None
    if str((cur.get("ai") or {}).get("ref_id") or "").split(":")[-1] != "body":
        return None
    pts = [dict(p) for p in (cur.get("points") or [])]
    if len(pts) < 3:
        return None
    y = float(line["y"])
    order = sorted(range(len(pts)), key=lambda i: float(pts[i]["y"]))
    if edge == "bottom":
        pick, was = order[-2:], round(max(float(p["y"]) for p in pts), 1)
        other = round(min(float(p["y"]) for p in pts), 1)
        if y <= other + 1:
            return (f"the wall_base line you tapped (y={round(y, 1)} px) sits "
                    f"at or ABOVE this box's top (y={other} px), so it cannot "
                    "be a bottom: nothing moved and nothing was guessed")
    else:
        pick, was = order[:2], round(min(float(p["y"]) for p in pts), 1)
        other = round(max(float(p["y"]) for p in pts), 1)
        if y >= other - 1:
            return (f"the eave line you tapped (y={round(y, 1)} px) sits at or "
                    f"BELOW this box's bottom (y={other} px), so it cannot be "
                    "a top: nothing moved and nothing was guessed")
    if abs(was - y) < 0.5:
        return None
    for i in pick:
        pts[i]["y"] = y
    word = "wall_base" if edge == "bottom" else "eave"
    note = (
        f"SEND-{'148' if edge == 'bottom' else '149'} — YOUR "
        f"{'START' if edge == 'bottom' else 'EAVE'} LINE OUTRANKS THE OLD "
        f"DRAG: the {edge.upper()} EDGE of '{cur.get('label')}' moved from "
        f"y={was} px to the {word} line you tapped (y={round(y, 1)} px). "
        f"{why.capitalize()}, so nothing else was touched — your sides and "
        f"your {'top' if edge == 'bottom' else 'bottom'} are yours and they "
        "stayed, which means this box's HEIGHT is now YOURS and not the "
        "read's. The zone was not cleared and not re-placed, and the ft² "
        "still comes from the shape you confirm.")
    stamp = _now()
    ai = dict(cur.get("ai") or {})
    if edge == "bottom":
        ai.update(anchor="wall_base_mark",
                  anchor_wall_base_mark=line.get("mark_id"),
                  anchor_wall_base_y=round(y, 3),
                  bottom_followed_your_line=True)
    else:
        ai.update(top_anchor="eave_mark",
                  anchor_eave_mark=line.get("mark_id"),
                  anchor_eave_y=round(y, 3),
                  top_followed_your_line=True)
    upd = {"points": pts, "updated_at": stamp, "rebased_at": stamp,
           "basis": (cur.get("basis") or "") + " " + note, "ai": ai}
    if cur.get("status") == "confirmed":
        upd.update({"status": "provisional", "confirmed_at": None,
                    "confirmed_by": None, "confirmed_stage": None,
                    "confirmed_basis": None, "confirmed_after_ai_read": None,
                    "refused_reason": (f"the {edge} moved to the {word} line "
                                       "you tapped — re-confirm the new "
                                       "figure")})
        note += (" It was CONFIRMED, so it went back to PROVISIONAL: a "
                 "confirmation cannot outlive the figure it was given for.")
    await db.photo_takeoff_marks.update_one(
        {"id": cur["id"], "estimate_id": est_id, "company_id": company_id},
        {"$set": upd})
    return note


async def _bottom_follows_the_line(db, est_id: str, company_id: str,
                                   cur: dict, base_mark: Optional[dict],
                                   why: str) -> Optional[str]:
    """SEND-148's door, kept by name: the BOTTOM edge follows a wall_base."""
    return await _edge_follows_the_line(db, est_id, company_id, cur,
                                        base_mark, why, "bottom")


def _zone_is_human_touched(cur: dict) -> Optional[str]:
    """SEND-147 — A HUMAN-TOUCHED ZONE STAYS PUT, and this says WHY in words.

    Three ways a zone counts as touched:
      · the PATCH route stamped `human_touched` (every hand edit does);
      · it is CONFIRMED or REFUSED — a ruling is a hand;
      · it was UPDATED long after the machine last wrote it. Howard tweaked
        FRONT's edges BEFORE the stamp existed, so the clock is the only
        witness those drags left — and it is honoured. `rebased_at` records
        the machine's own last write so a re-base never mistakes itself for
        a hand.
    """
    if cur.get("human_touched"):
        return "you have already moved it by hand"
    if cur.get("status") != "provisional":
        return f"it is {cur.get('status')}, not provisional"
    machine = cur.get("rebased_at") or cur.get("created_at")
    seen = cur.get("updated_at")
    if machine and seen:
        try:
            gap = abs((datetime.fromisoformat(str(seen))
                       - datetime.fromisoformat(str(machine))).total_seconds())
        except (TypeError, ValueError):
            return None
        if gap > 5:
            return ("it was edited after it was placed (before this app "
                    "stamped hand edits), and an edit is a hand")
    return None


async def rebase_zones_for_photo(db, est_id: str, company_id: str,
                                 photo_key: str,
                                 created_by: Optional[str] = None,
                                 scope: str = "all") -> dict:
    """SEND-147 — THE TAP MOVES THE BOX. When a wall_base line is tapped,
    moved or removed on a photo, the AI zones already on that photo are
    re-placed against the new anchor. NOTHING NEW IS PLACED: a start line is
    an anchor, not a proposal, so a photo with no zones stays empty. A zone
    Howard has dragged, confirmed or refused STAYS PUT and says why."""
    out = {"photo_key": photo_key, "moved": None, "notes": None}
    try:
        run = None
        async for r in db.ai_measure_runs.find(
                {"estimate_id": est_id, "status": "done"},
                sort=[("created_at", -1)]).limit(25):
            if photo_key in _run_photo_names(r):
                run = r
                break
        if not run:
            return out
        from routes.photo_takeoff import _photo_natural_size

        async def natural_size(key):
            dims = _photo_natural_size(key)
            if dims:
                return dims
            from config import UPLOAD_DIR
            from upload_store import rehydrate_to_disk
            if await rehydrate_to_disk(key, UPLOAD_DIR):
                return _photo_natural_size(key)
            return None

        row = await propose_zones_for_photo(db, run, est_id, company_id,
                                            photo_key, created_by,
                                            natural_size, place_new=False,
                                            scope=scope)
        return {"photo_key": photo_key, "moved": row.get("moved"),
                "wall_base": row.get("wall_base"), "eave": row.get("eave"),
                "notes": row.get("notes"), "refusal": row.get("refusal")}
    except Exception as exc:                     # a tap must never 500
        logger.warning("zone rebase failed on %s: %s", photo_key, exc)
        out["notes"] = [f"the zones on this photo were not re-based: {exc}"]
        return out


async def maybe_propose_zones(run_id: str) -> dict:
    """AUTO-PROPOSE ON COMPLETION (Howard ruled 2026-08-28): the moment a run
    finishes, every face that has a MEASURED WIDTH gets its starting zone
    set on its own head-on photo. A protected estimate is skipped — a
    proposal is still a write, and 423 governs. Never raises into the
    worker."""
    out = {"run_id": run_id, "faces": [], "skipped": None}
    try:
        from db import db
        from untouchable import is_untouchable
        run = await db.ai_measure_runs.find_one({"run_id": run_id})
        if not run or run.get("status") != "done":
            out["skipped"] = "run is not done"
            return out
        est_id = run.get("estimate_id")
        if not est_id:
            out["skipped"] = "this run carries no estimate"
            return out
        if await is_untouchable(est_id):
            out["skipped"] = ("protected estimate — no derived write, not "
                              "even a proposal")
            return out
        est = await db.estimates.find_one({"id": est_id},
                                          {"_id": 0, "company_id": 1})
        if not est:
            out["skipped"] = "estimate not found"
            return out
        user = await db.users.find_one({"id": run.get("user_id")},
                                       {"_id": 0, "email": 1}) or {}
        from routes.photo_takeoff import _photo_natural_size

        async def natural_size(key):
            dims = _photo_natural_size(key)
            if dims:
                return dims
            from config import UPLOAD_DIR
            from upload_store import rehydrate_to_disk
            if await rehydrate_to_disk(key, UPLOAD_DIR):
                return _photo_natural_size(key)
            return None

        for photo_key in _run_photo_names(run):
            row = await propose_zones_for_photo(
                db, run, est_id, est["company_id"], photo_key,
                user.get("email"), natural_size)
            row.pop("marks", None)
            out["faces"].append(row)
    except Exception as exc:                      # never break the worker
        logger.warning("zone auto-proposal failed for run %s: %s", run_id, exc)
        out["skipped"] = f"auto-proposal failed: {exc}"
    return out
