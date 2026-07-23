"""Elevation Sheet data binder — EL-1..EL-4 (front/left/back/right).

READ-ONLY ROUTE (pinned): performs ZERO writes — a new output route on
existing data. September protection: demo surfaces are imported as
CONSTANTS only (sealed key module, LETRICK_TAPE_WALLS), never modified.

Data-binding rules (Howard's build directives 2026-07-18):
  • geometry-source rule governs — the tape-validated sealed key is the
    default wall basis where it exists; extraction-run fallback labeled.
  • stepped walls: EACH tape segment keeps its own basis line (courses ×
    exposure formula) — no silent interpolation; step location is untaped.
  • openings come from the run's schedule with their AI-READ tags and
    ratify states; every value traces to its named source — NO hand-typed
    constants.
  • opening categories are a CLOSED five-key contract (ruled 2026-07-20,
    Spec v2 C-6/C-7 — amends the 2026-07-18 three-key ruling):
    {windows, doors, patio_doors, vents, garage_doors}. Every category
    gets full provenance, ratify verbs, collision-guard registration,
    and basis treatment. Any future type needs a pin amendment ruling
    BEFORE code emits it.
  • chimney chase (back): AI accent read, footprint untaped — the sheet
    annotates, never scale-renders silently.
"""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user

router = APIRouter()

_FRAC = {0.0: "", 0.125: "⅛", 0.25: "¼", 0.375: "⅜", 0.5: "½",
         0.625: "⅝", 0.75: "¾", 0.875: "⅞"}

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

_SHEET_CODES = {"front": "EL-1", "left": "EL-2", "back": "EL-3", "right": "EL-4"}


def fmt_ftin(ft: float) -> str:
    """Architectural format X'-Y[⅛..⅞]\" — nearest eighth inch (eighths
    ruled in with the taped chase height 234-5/8\")."""
    sign = "-" if ft < 0 else ""
    total_e = round(abs(ft) * 12 * 8)
    feet, rem = divmod(total_e, 12 * 8)
    inches, e = divmod(rem, 8)
    return f"{sign}{feet}'-{inches}{_FRAC[e / 8.0]}\""


def fmt_inches(inches: float) -> str:
    sign = "-" if inches < 0 else ""
    total_e = round(abs(inches) * 8)
    whole, e = divmod(total_e, 8)
    return f"{sign}{whole}{_FRAC[e / 8.0]}\""


def detect_collisions(elements, tol_in=0.1):
    """GLOBAL COLLISION GUARD — FLAG-ALWAYS, SUPPRESS-NEVER (rule AMENDED
    by Howard's ruling 2026-07-21; original suppression rule 2026-07-19
    predates C-4 chases as scale-rendered first-class elements). ALL
    collisions — opening × opening AND opening × chase — draw BOTH
    elements at their best-known positions, flag both, and emit a
    deviation-style callout naming both elements and their bases, plus
    the fix direction (Field Verify location review). Collisions between
    tagged AI positions are uncertainty, not impossibility: a missing
    chimney misleads a crew worse than a flagged overlap.

    2D AMENDMENT (Howard's ruling 2026-07-23): a collision requires
    overlap in BOTH axes — the along-wall horizontal span AND the
    vertical extent (sill/base → head). Elements clear in either axis
    never flag (founding false positive: red house front W1, sill
    11'-5⅛", × G2, grade → 73" head — 17⅝" horizontal overlap but 64"
    of vertical clearance). Vertical bounds are OPTIONAL: an element
    with no sill read (v_lo_ft/v_hi_ft absent/None) cannot PROVE
    clearance, so horizontal overlap alone still flags — uncertainty
    flags, it never silently clears.
    elements: [{name, base, lo_ft, hi_ft, v_lo_ft?, v_hi_ft?,
                kind: opening|appendage}]."""
    out = []
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            a, b = elements[i], elements[j]
            # PLANE RULE (P5, ruled 2026-07-23): elements on different
            # planes (wall vs dormer roof-plane) are separated by
            # construction — the dormer sits above the eave, wall
            # elements end at it. Never compared, never flagged.
            if a.get("plane", "wall") != b.get("plane", "wall"):
                continue
            overlap_ft = min(a["hi_ft"], b["hi_ft"]) - max(a["lo_ft"], b["lo_ft"])
            if overlap_ft * 12.0 <= tol_in:
                continue
            v_overlap_in = None
            if all(e.get("v_lo_ft") is not None and e.get("v_hi_ft") is not None
                   for e in (a, b)):
                v_overlap_in = (min(a["v_hi_ft"], b["v_hi_ft"])
                                - max(a["v_lo_ft"], b["v_lo_ft"])) * 12.0
                if v_overlap_in <= tol_in:
                    continue  # vertically clear — both-axes rule: no collision
            out.append({
                "elements": [a["name"], b["name"]],
                "bases": [a["base"], b["base"]],
                "overlap_in": round(overlap_ft * 12.0, 1),
                "overlap_label": fmt_inches(overlap_ft * 12.0),
                "v_overlap_in": round(v_overlap_in, 1) if v_overlap_in is not None else None,
                "v_overlap_label": (fmt_inches(v_overlap_in)
                                    if v_overlap_in is not None else "unknown (no sill read)"),
                "suppressed": None,
                "resolution": ("both elements flagged — positions unverified"
                               " · resolve via Field Verify location review"),
            })
    return out


def _door_relative_chase_center(est, raw, chase_w_in):
    """Ratified chase position (ruled 2026-07-19, supersedes the AI
    corner-read binding): human photo ground truth — the chase sits LEFT
    of D1 with a siding strip between (relationship CONFIRMED — human,
    photo). The right-edge offset from D1's trim edge enters via the
    appendage ratify machinery: ESTIMATED (photo-scaled, untaped) until a
    tape upgrades it by the normal amendment path. D1 stays where the
    run put it."""
    off = ((est.get("lp_appendage_dims") or {}).get("appendage:back") or {}).get("door_offset_ft") or {}
    if not off.get("value") or not chase_w_in:
        return None
    door = next((o for o in (raw.get("openings") or [])
                 if str(o.get("wall", "")).lower() == "back"
                 and "door" in str(o.get("type", ""))
                 and o.get("along_wall_ft") is not None and o.get("width_in")), None)
    if not door:
        return None
    d1_left = float(door["along_wall_ft"]) - float(door["width_in"]) / 24.0
    right_edge = d1_left - float(off["value"])
    return {
        "center_ft": right_edge - float(chase_w_in) / 24.0,
        "right_edge_ft": right_edge,
        "d1_left_ft": d1_left,
        "offset_ft": float(off["value"]),
        "offset_taped": off.get("status") in ("user_measured", "user_confirmed_from_blueprint"),
    }


def _bind_roofline(raw, which, height_ft, height_tag):
    """P3 (ruled 2026-07-21): the roofline draws on EVERY elevation, gable
    first. Eave views: ridge = this view's eave + gable rise (worst-case
    read when the side reads disagree — flagged, never averaged). Gable
    ends: true rakes + apex ridge. Hip: NAMED limitation, never a guess.
    Ridge tag ESTIMATED (derived) per C-3; basis strings composed from
    the reads — nothing hardcoded."""
    if height_ft is None:
        return None
    roof_type = str(raw.get("roof_type") or "")
    walls = raw.get("walls") or []
    me = next((w for w in walls if str(w.get("label", "")).lower() == which), None)
    own_rise = (me or {}).get("gable_triangle_height_ft") or 0
    if roof_type == "hip":
        return {"kind": "hip_unreconciled",
                "note": "HIP ROOFLINE — PITCH NOT YET RECONCILED — NOT DRAWN"}
    if own_rise > 0:
        tag = _AI_TAGS.get(str((me or {}).get("height_ft_source")), "ESTIMATED")
        ridge = height_ft + float(own_rise)
        return {"kind": "gable_end", "rise_ft": float(own_rise),
                "ridge_ft": round(ridge, 3), "ridge_label": fmt_ftin(ridge),
                "tag": "ESTIMATED",
                "basis": (f"ridge = eave {height_tag} + own gable rise "
                          f"{fmt_ftin(own_rise)} ({tag}) — DERIVED")}
    reads = [(str(w.get("label", "")).lower(), float(w.get("gable_triangle_height_ft")),
              _AI_TAGS.get(str(w.get("height_ft_source")), "ESTIMATED"))
             for w in walls
             if w.get("gable_triangle_height_ft")
             and str(w.get("label", "")).lower() != which]
    if not reads:
        return {"kind": "none_readable",
                "note": "RIDGE NOT DRAWN — NO GABLE RISE READ ON RECORD"}
    vals = [r[1] for r in reads]
    rise = max(vals)
    ridge = height_ft + rise
    out = {"kind": "eave_ridge", "rise_ft": rise,
           "ridge_ft": round(ridge, 3), "ridge_label": fmt_ftin(ridge),
           "tag": "ESTIMATED",
           "basis": (f"ridge = eave {height_tag} + gable rise {fmt_ftin(rise)} "
                     f"({' · '.join(sorted(set(r[2] for r in reads)))}) — DERIVED")}
    if max(vals) - min(vals) > 0.05:
        out["note"] = ("gable rises "
                       + " / ".join(f"{l} {fmt_ftin(v)}" for l, v, _ in reads)
                       + f" disagree — drawn at {fmt_ftin(rise)} (worst case)"
                       " — flagged, not averaged")
    return out


def _norm_face(f):
    f = str(f or "").lower()
    return {"rear": "back"}.get(f, f)


# drawing side of a perpendicular dormer profile, per the exterior-view
# convention (left elevation mirrors; back flips left/right)
_PROFILE_SIDE = {("front", "left"): "left", ("front", "right"): "right",
                 ("back", "left"): "right", ("back", "right"): "left",
                 ("left", "front"): "right", ("left", "back"): "left",
                 ("right", "front"): "left", ("right", "back"): "right"}


WINDOW_HEAD_ANCHOR_IN = 80.0
# CONTRACTOR-SPEC (RATIFIED by Howard 2026-07-22, re-ratification to
# change): standard residential window/door header height 6'-8" above
# grade. Sole anchor closing photo-scaled head-line chains (same-photo
# bbox offsets are fully evidence-bound; the wall-window head height has
# no direct read on doorless walls). A convention, not a promise —
# residual error at this rung is expected and tape-closable.


def _dormer_photo_chain(raw, wall_label):
    """Same-photo bbox chain (ruled 2026-07-22, P5 defect #2 — evidence
    before hypothesis): wall-plane vertical scale = height_in / bbox.h
    averaged over this wall's NON-dormer windows that share the dormer
    bbox photo; head line = highest wall-window bbox top. Returns
    (scale_in_per_frac, head_frac, dormer_openings) or None when no
    same-photo chain exists."""
    ops = [o for o in (raw.get("openings") or [])
           if str(o.get("wall", "")).lower() == wall_label]
    dorm = [o for o in ops if o.get("on_dormer") and (o.get("bbox") or {}).get("h")]
    if not dorm:
        return None
    photos = {o.get("bbox_photo_idx", o.get("photo_idx")) for o in dorm}
    wall_wins = [o for o in ops
                 if not o.get("on_dormer") and "window" in str(o.get("type", ""))
                 and (o.get("bbox") or {}).get("h") and o.get("height_in")
                 and o.get("bbox_photo_idx", o.get("photo_idx")) in photos]
    if not wall_wins:
        return None
    scale = sum(float(o["height_in"]) / float(o["bbox"]["h"]) for o in wall_wins) / len(wall_wins)
    head_frac = min(float(o["bbox"]["y"]) for o in wall_wins)
    return scale, head_frac, dorm


def _dormer_vpos(raw, wall_label, knee_ft):
    """Bound dormer v-pos band: dormer window band center (bbox, wall-plane
    scale) above the wall-window head line, anchored at the PROPOSED
    ASSUMED 6'-8" standard header; face band = center ± knee/2 (windows
    centered in the face — construction norm, inverse of the draw rule)."""
    chain = _dormer_photo_chain(raw, wall_label)
    if not chain or not knee_ft:
        return None
    scale, head_frac, dorm = chain
    band_top = min(float(o["bbox"]["y"]) for o in dorm)
    band_bot = max(float(o["bbox"]["y"]) + float(o["bbox"]["h"]) for o in dorm)
    center_above_head = (head_frac - (band_top + band_bot) / 2.0) * scale
    center_in = WINDOW_HEAD_ANCHOR_IN + center_above_head
    return {
        "base_ft": round((center_in - float(knee_ft) * 6.0) / 12.0, 2),
        "top_ft": round((center_in + float(knee_ft) * 6.0) / 12.0, 2),
        "tag": "ESTIMATED (photo-scaled · head-anchor CONTRACTOR-SPEC 6'-8\")",
        "basis": (f"same-photo bbox chain — wall-plane scale {scale:.0f} in/frac, "
                  f"dormer window-band center {fmt_inches(center_above_head)} above the "
                  f"wall-window head line, anchored at the CONTRACTOR-SPEC 6'-8\" "
                  f"header (RATIFIED 2026-07-22)"),
    }


_OPPOSITE = {"left": "right", "right": "left", "front": "back", "back": "front"}
PAIRED_DORMER_TOL_FT = 0.5


def _paired_dormer(raw, d):
    """PAIRED-FEATURE RECONCILIATION (ruled 2026-07-22, red house is the
    founding example): matching features on OPPOSITE faces — width AND
    knee within 6" — bind ONE reconciled band, drawn LEVEL on both.
    Independent per-wall scales never produce asymmetric twins."""
    face = _norm_face(d.get("face"))
    for other in raw.get("dormers") or []:
        if other is d or _norm_face(other.get("face")) != _OPPOSITE.get(face):
            continue
        if (d.get("width_ft") and other.get("width_ft")
                and abs(float(d["width_ft"]) - float(other["width_ft"])) <= PAIRED_DORMER_TOL_FT
                and d.get("knee_wall_height_ft") and other.get("knee_wall_height_ft")
                and abs(float(d["knee_wall_height_ft"]) - float(other["knee_wall_height_ft"])) <= PAIRED_DORMER_TOL_FT):
            return other
    return None


def _dormer_tape(est, face):
    """AUTHORIZED tape ladder (Howard, 2026-07-22): lp_appendage_dims
    dormer:{face} — user_measured knee_ft/base_ft outrank every rung;
    'assumed' status never overrides (standing appendage-dims rule)."""
    d = ((est.get("lp_appendage_dims") or {}).get(f"dormer:{face}") or {})
    out = {}
    for k in ("knee_ft", "base_ft"):
        e = d.get(k) or {}
        if e.get("value") and e.get("status") == "user_measured":
            out[k] = float(e["value"])
    return out


def _bind_dormers(est, raw, which, width_ft, height_ft, roofline_obj):
    """P5 DORMERS (C-5 ruling; v-pos + profile orientation AMENDED by
    Howard's field-compare FAIL ruling 2026-07-22). Face-on: the dormer
    band draws at its BOUND v-pos (TAPED > ESTIMATED photo-scaled bbox
    chain > mid-slope UNRESOLVED flag — base-at-eave RETIRED as an
    unratified assumption). Profiles (perpendicular gable views): the
    dormer renders as its ROOF EDGE — a LEVEL line projecting off the
    main slope — with the vertical face edge below it (height = knee by
    construction) and the cheek closing back to the roof plane. Wide and
    low, per the site-photo ground truth."""
    face_on, profiles = None, []
    for d in (raw.get("dormers") or []):
        if not d:
            continue
        face = _norm_face(d.get("face"))
        w, knee = d.get("width_ft"), d.get("knee_wall_height_ft")
        tag = _AI_TAGS.get(str(d.get("width_source")), "ESTIMATED")
        if not knee:
            continue
        tape = _dormer_tape(est, face)
        knee = tape.get("knee_ft", float(knee))
        knee_tag = "TAPED (user-measured)" if "knee_ft" in tape else tag
        # PAIRED-FEATURE RECONCILIATION (ruled 2026-07-22): opposite-face
        # twins bind ONE band, drawn LEVEL — tape on either face closes both
        pair = _paired_dormer(raw, d)
        pair_tape = _dormer_tape(est, _norm_face(pair.get("face"))) if pair else {}
        vpos = _dormer_vpos(raw, face, knee)
        if "base_ft" in tape:
            base_ft, top_ft = tape["base_ft"], round(tape["base_ft"] + knee, 2)
            v_tag, v_basis = "TAPED (user-measured)", "base taped via appendage dims"
        elif pair and "base_ft" in pair_tape:
            base_ft = pair_tape["base_ft"]
            top_ft = round(base_ft + knee, 2)
            v_tag = "TAPED (user-measured · paired)"
            v_basis = (f"base taped on the {_norm_face(pair.get('face'))} twin — "
                       f"paired-feature reconciliation binds both LEVEL")
        elif vpos:
            v_pair = (_dormer_vpos(raw, _norm_face(pair.get("face")),
                                   float(pair.get("knee_wall_height_ft")))
                      if pair else None)
            if v_pair:
                base_ft = round((vpos["base_ft"] + v_pair["base_ft"]) / 2.0, 2)
                top_ft = round((vpos["top_ft"] + v_pair["top_ft"]) / 2.0, 2)
                v_tag = ("ESTIMATED (photo-scaled · PAIRED-RECONCILED · "
                         "head-anchor CONTRACTOR-SPEC 6'-8\")")
                v_basis = (f"paired-feature reconciliation ({face} "
                           f"{fmt_ftin(vpos['base_ft'])}–{fmt_ftin(vpos['top_ft'])} / "
                           f"{_norm_face(pair.get('face'))} {fmt_ftin(v_pair['base_ft'])}–"
                           f"{fmt_ftin(v_pair['top_ft'])} → one LEVEL band) · {vpos['basis']}")
            else:
                base_ft, top_ft = vpos["base_ft"], vpos["top_ft"]
                v_tag, v_basis = vpos["tag"], vpos["basis"]
        else:
            base_ft, top_ft = None, None
            v_tag = "UNRESOLVED"
            v_basis = ("no same-photo window chain — v-pos not derivable; "
                       "drawn mid-slope INDICATIVE · default PENDING RATIFICATION")
        # HORIZONTAL CENTER LADDER (offset-evidence ruling 2026-07-22):
        # on-dormer window positions (structured bboxes, windows-centered
        # norm — same norm ratified for v-pos) outrank the reconciler's
        # rounded offset_x_ft claim
        d_wins = [o for o in (raw.get("openings") or [])
                  if str(o.get("wall", "")).lower() == face and o.get("on_dormer")
                  and o.get("along_wall_ft") is not None]
        off = float(d.get("offset_x_ft") or 0.0)
        if d_wins:
            center_val = sum(float(o["along_wall_ft"]) for o in d_wins) / len(d_wins)
            center_tag = "ESTIMATED (windows-centered norm)"
            center_basis = (f"midpoint of {len(d_wins)} on-dormer window position(s) "
                            f"(bbox-consistent) — outranks the run's rounded "
                            f"offset_x_ft {off:g}' claim")
        else:
            center_val = None
            center_tag = _AI_TAGS.get(str(d.get("width_source")), "ESTIMATED")
            center_basis = f"run offset_x_ft {off:g}' from wall center"
        if face == which and w and width_ft and height_ft is not None:
            ridge_ft = (roofline_obj or {}).get("ridge_ft")
            if base_ft is None:
                # mid-slope fallback — flagged, never silent
                span_top = float(ridge_ft) if ridge_ft else float(height_ft) + knee
                base_ft = round(float(height_ft) + max((span_top - float(height_ft) - knee) / 2.0, 0), 2)
                top_ft = round(base_ft + knee, 2)
            off = float(d.get("offset_x_ft") or 0.0)
            center = center_val if center_val is not None else width_ft / 2.0 + off
            top_note = None
            if ridge_ft and top_ft > float(ridge_ft) + 0.05:
                top_note = "dormer top exceeds the drawn ridge — reads disagree — flagged"
            face_on = {
                "face": face,
                "width_ft": float(w), "width_label": fmt_ftin(w), "width_tag": tag,
                "knee_ft": knee, "knee_label": fmt_ftin(knee), "knee_tag": knee_tag,
                "center_ft": round(center, 2), "center_label": fmt_ftin(center),
                "center_tag": center_tag,
                "offset_x_ft": off,
                "base_ft": base_ft, "base_label": fmt_ftin(base_ft),
                "top_ft": top_ft, "top_label": fmt_ftin(top_ft),
                "vpos_tag": v_tag,
                "base_note": f"base {fmt_ftin(base_ft)} · v-pos {v_tag} — {v_basis}",
                "top_note": top_note,
                "basis": (f"width {fmt_ftin(w)} · knee {fmt_ftin(knee)} — AI run "
                          f"dormer read ({tag}) · center {fmt_ftin(center)} — {center_basis}"),
                "source_photos": d.get("_source_photo_indices") or [],
            }
        elif face in ("front", "back", "left", "right") and face != which:
            side = _PROFILE_SIDE.get((which, face))
            if side:
                profiles.append({
                    "face": face, "drawing_side": side,
                    "knee_ft": knee, "knee_label": fmt_ftin(knee), "tag": knee_tag,
                    "width_ft": float(w) if w else None,
                    "width_label": fmt_ftin(w) if w else None,
                    "base_ft": base_ft, "top_ft": top_ft,
                    "vpos_tag": v_tag,
                    "note": ("roof edge drawn LEVEL — dormer roof pitch NOT READ · "
                             f"v-pos {v_tag}"),
                    "basis": (f"knee {fmt_ftin(knee)} — AI run dormer read ({tag}) · "
                              f"{face} slope · {v_basis}"),
                })
    return face_on, profiles


STANDARD_CHASE_DEPTH_IN = 30.0
# CONTRACTOR-SPEC (Howard, ratified 2026-07-21): ASSUMED standard chase
# depth = 30" — the bottom rung of TAPED > ESTIMATED > ASSUMED (spec C).
# Upgradeable by tape (appendage dims user_measured) or a photo-derived read.

CHASE_CODE_MIN_ABOVE_RIDGE_FT = 2.0
# CONTRACTOR-SPEC (Howard, ratified 2026-07-21): no-height-read fallback =
# grade to 2'-0" ABOVE THE DRAWN RIDGE at the chase position — ridge-relative,
# never a fixed-feet guess. Tagged ASSUMED, upgradeable like every rung.

STANDARD_CHASE_WIDTH_IN = 48.0
# CONTRACTOR-SPEC (Howard, ratified 2026-07-22): ASSUMED standard chase
# width = 48" — used ONLY when confirmation-weighted geometry leaves a
# single confirmed edge (mixed-tier reads). Upgradeable by tape
# (appendage width_ft user_measured) or a confirmed photo read.


def _bind_chase_position(chase, reads, width_ft, est):
    """CONFIRMATION-WEIGHTED GEOMETRY (Howard's ruling 2026-07-22 —
    founding example: doug jones back chase, logged in the register).
    CONFIRMED reads anchor drawn geometry. UNCONFIRMED single-sighting
    reads NEVER define a drawn edge, position, or span — they render as
    flagged comparisons (ai_band pattern), awaiting sightings or human
    ratification. Mixed-tier: anchor the confirmed edge, extend toward
    the unconfirmed side by TAPED width (user_measured) > ASSUMED
    standard width 48". Zero confirmed reads: no drawn position — named
    state, annotation + comparison only."""
    conf = sorted({round(r["frac"], 4) for r in reads if r["tier"] == "confirmed"})
    unconf = sorted({round(r["frac"], 4) for r in reads if r["tier"] != "confirmed"})
    # EDGE-CLUSTER RULE: two confirmed reads are two DISTINCT edges only
    # when their span ≥ the ratified minimum credible chase width (48");
    # closer reads are one edge cluster (outside corner + inside return
    # read the SAME edge — doug's exact 0.40/0.42 pattern). The
    # discriminator derives from the ratified constant, not a magic number.
    two_edges = (len(conf) >= 2
                 and (max(conf) - min(conf)) * width_ft * 12.0 >= STANDARD_CHASE_WIDTH_IN)
    if two_edges:
        chase["center_ft"] = round((min(conf) + max(conf)) / 2 * width_ft, 1)
        chase["position_tag"] = "AI-READ ✓"
        chase["position"] = (f"bound from CONFIRMED chase-corner reads "
                             f"({min(conf):g}–{max(conf):g} frac of wall) — AI-READ ✓")
        chase["position_note"] = "position from confirmed run corner reads — untaped"
        chase["_lad_fr"] = conf
        return
    if len(conf) >= 1:
        # single confirmed edge (or one edge cluster): the OUTSIDE-corner
        # read is the chase's true outer edge; fall back to the cluster mean
        outside = [round(r["frac"], 4) for r in reads
                   if r["tier"] == "confirmed" and str(r.get("type", "")).lower() == "outside"]
        anchor = outside[0] if outside else round(sum(conf) / len(conf), 4)
        dims = (est.get("lp_appendage_dims") or {}).get("appendage:back") or {}
        w_entry = dims.get("width_ft") or {}
        if w_entry.get("status") == "user_measured" and w_entry.get("value"):
            w_in, w_tag = round(float(w_entry["value"]) * 12.0, 1), "TAPED (user-measured)"
        else:
            w_in = STANDARD_CHASE_WIDTH_IN
            w_tag = f"ASSUMED (standard width {fmt_inches(STANDARD_CHASE_WIDTH_IN)})"
        toward_lower = None
        if unconf:
            toward_lower = sum(unconf) / len(unconf) < anchor
        else:
            # locator handedness: a read naming the chase's RIGHT edge means
            # the chase extends LEFT of it (and vice versa) — data-derived
            loc = " ".join(str(r.get("locator", "")).lower() for r in reads
                           if r["tier"] == "confirmed")
            if "right" in loc and "left" not in loc:
                toward_lower = True
            elif "left" in loc and "right" not in loc:
                toward_lower = False
        if toward_lower is None:
            toward_lower = anchor > 0.5  # toward wall interior — last resort
        direction = -1 if toward_lower else 1
        chase["center_ft"] = round(anchor * width_ft + direction * (w_in / 12.0) / 2, 1)
        chase["_width_override"] = (w_in, w_tag)
        side = "left" if direction < 0 else "right"
        edge = "right" if direction < 0 else "left"
        chase["position_tag"] = "AI-READ ✓ (confirmed edge)"
        chase["position"] = (f"anchored on CONFIRMED {edge}-edge read ({anchor:g} frac →"
                             f" {fmt_ftin(anchor * width_ft)}) — extends {side} by {w_tag}")
        chase["position_note"] = "position anchored on confirmed corner read — untaped"
        if unconf:
            far = min(unconf, key=lambda f: -abs(f - anchor))
            sight = next((r.get("sightings") for r in reads
                          if round(r["frac"], 4) == far and r["tier"] != "confirmed"), None)
            implied = abs(anchor - far) * width_ft * 12.0
            chase["ai_band"] = {
                "frac_lo": min(unconf + [anchor]), "frac_hi": max(unconf + [anchor]),
                "note": (f"UNCONFIRMED {side}-edge read {far:g} frac"
                         f" ({sight or 1} sighting) implies {fmt_inches(implied)} width —"
                         " flagged comparison only, awaiting sightings or ratification"),
            }
        return
    # zero confirmed reads — nothing drawn, nothing guessed
    chase["position_tag"] = "UNCONFIRMED"
    chase["position"] = "position unconfirmed — not drawn (no confirmed corner read)"
    chase["position_note"] = "no confirmed corner read — glyph not drawn"
    if unconf:
        chase["ai_band"] = {
            "frac_lo": min(unconf), "frac_hi": max(unconf),
            "note": (f"unconfirmed reads at {' / '.join(f'{f:g}' for f in unconf)} frac —"
                     " comparison only, awaiting sightings or ratification"),
        }


def _chase_dims_ladder(est, fr, wall_width_ft, roofline_obj):
    """P4 (ruled 2026-07-21): dims ladder for chases WITHOUT sealed-tape
    dims — each dimension binds its best-known rung and carries that
    rung's tag (chases scale-render at best-known dims on every rung, C-4):
      width : ESTIMATED (photo-scaled) — corner-read span × wall best-known width
      depth : TAPED (user-measured appendage dims) > ASSUMED (standard depth)
      height: TAPED (user-measured appendage dims) > ASSUMED (ridge + 2'-0\")
    """
    out = {}
    dims = (est.get("lp_appendage_dims") or {}).get("appendage:back") or {}
    w_entry = dims.get("width_ft") or {}
    if w_entry.get("status") == "user_measured" and w_entry.get("value"):
        out["width_in"] = round(float(w_entry["value"]) * 12.0, 1)
        out["width_tag"] = "TAPED (user-measured)"
    elif fr and wall_width_ft and max(fr) > min(fr):
        out["width_in"] = round((max(fr) - min(fr)) * float(wall_width_ft) * 12.0, 1)
        out["width_tag"] = "ESTIMATED (photo-scaled)"
    d_entry = dims.get("depth_ft") or {}
    if d_entry.get("status") == "user_measured" and d_entry.get("value"):
        out["depth_in"] = round(float(d_entry["value"]) * 12.0, 1)
        out["depth_tag"] = "TAPED (user-measured)"
    else:
        out["depth_in"] = STANDARD_CHASE_DEPTH_IN
        out["depth_tag"] = f"ASSUMED (standard depth {fmt_inches(STANDARD_CHASE_DEPTH_IN)})"
    h_entry = dims.get("height_ft") or {}
    if h_entry.get("status") == "user_measured" and h_entry.get("value"):
        out["height_in"] = round(float(h_entry["value"]) * 12.0, 1)
        out["height_tag"] = "TAPED (user-measured)"
    elif roofline_obj and roofline_obj.get("ridge_ft"):
        out["height_in"] = round(
            (roofline_obj["ridge_ft"] + CHASE_CODE_MIN_ABOVE_RIDGE_FT) * 12.0, 1)
        out["height_tag"] = f"ASSUMED (ridge + {fmt_ftin(CHASE_CODE_MIN_ABOVE_RIDGE_FT)})"
    return out


def _sealed_tape_basis(est: dict, wall_label: str) -> dict | None:
    """Sealed hand-takeoff key binding (Letrick). Values BIND from the key
    artifact + the Class-1-corrected structured tape walls — never retyped.
    Sides carry NO taped width (key eaves formula covers front/back only):
    width falls back to the extraction run, labeled. Stepped sides carry
    BOTH tape segments, each with its own courses × exposure basis."""
    if est.get("estimate_number") != "EST-373526":
        return None
    from letrick_hand_takeoff_key import LETRICK_HAND_TAKEOFF_KEY as KEY
    from routes.demo import LETRICK_TAPE_WALLS  # constant import only
    tw = LETRICK_TAPE_WALLS.get(wall_label)
    if not tw:
        return None
    exposure_in = float(KEY["inputs"]["exposure_in"])   # TAPED
    # tape segment order (key structure): [front-adjacent, back-adjacent]
    # — side counts mirror the front (25) / back (28) wall tape counts.
    seg_adjacent = ["front", "back"] if len(tw["segments"]) > 1 else [None]
    segments = []
    for seg, adj in zip(tw["segments"], seg_adjacent):
        courses = int(seg["courses"])                    # tape count
        height_ft = float(seg["height_ft"])              # reconciled constant (courses × exposure)
        segments.append({
            "adjacent": adj,
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
    # chase ratification amendment (TAPED 2026-07-19) — all three dims
    chase_dims = None
    if "chase_width_in" in KEY["inputs"]:
        note = str((KEY["bases"].get("chase_width_in") or {}).get("note", ""))
        m = re.search(r"\d{4}-\d{2}-\d{2}", note)
        chase_dims = {
            "width_in": float(KEY["inputs"]["chase_width_in"]),
            "depth_in": float(KEY["inputs"]["chase_depth_in"]),
            "height_in": float(KEY["inputs"]["chase_height_in"]),
            "taped": m.group(0) if m else KEY.get("amended", ""),
        }
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
        "chase_dims": chase_dims,
    }


def _schedule_matchers(run, review_state):
    """Verb machinery (ruled 2026-07-15): lp_openings_review rows are
    run-scoped `open:{rid8}:{index}` over _ai_openings_schedule. Removed
    rows must not render; corrected types render as corrected."""
    sched = ((run.get("result") or {}).get("measurements") or {}).get("_ai_openings_schedule") or []
    rid = str(run.get("run_id") or "")[:8]
    matchers = []
    for i, s in enumerate(sched):
        st = (review_state or {}).get(f"open:{rid}:{i}") or {}
        dims = re.findall(r"\d+", str(s.get("size_label") or ""))[:2]
        matchers.append({
            "wall": str(s.get("elevation") or "").lower(),
            "type": s.get("type"), "style": s.get("style") or "",
            "dims": [float(d) for d in dims],
            "removed": st.get("status") == "user_removed",
            "corrected_type": st.get("corrected_type"),
        })
    return matchers


def _nearest_matcher(o, matchers):
    """A raw opening belongs to its NEAREST schedule row (same wall/type/
    style, dims within 2.5\" — photo reads vary by an inch or two around
    the group's representative size). Nearest-row assignment keeps
    adjacent size groups (e.g. 36×54 vs 36×52) distinct: removing one
    group must never swallow its neighbor."""
    best, best_d = None, None
    for m in matchers:
        if str(o.get("wall", "")).lower() != m["wall"]:
            continue
        if o.get("type") != m["type"] or (o.get("style") or "") != m["style"]:
            continue
        if not m["dims"] or len(m["dims"]) < 2:
            d = 0.0
        else:
            try:
                dw = abs(float(o.get("width_in") or 0) - m["dims"][0])
                dh = abs(float(o.get("height_in") or 0) - m["dims"][1])
            except (TypeError, ValueError):
                dw = dh = 0.0
            if dw > 2.5 or dh > 2.5:
                continue
            d = dw + dh
        if best is None or d < best_d:
            best, best_d = m, d
    return best


def _bind_openings(raw, wall_label, matchers):
    """Openings for this wall, position-ordered, tagged (W/D/P/V/G per the
    closed FIVE-key contract, ruled 2026-07-20), door-anchored sills from
    photo bbox (all door categories sit at grade — spec §2). Walls without
    a door have no sill anchor: sills stay None ('—'), vertical position
    not derivable. Removed openings don't render; corrected types render
    corrected. DEFECT RETIRED by this amendment (audit 2026-07-20):
    garage_door/patio_door previously folded into 'Entry door' via the
    `"door" in type` check — dormant misclassification, caught by audit.
    P5 (C-5 ruling, 2026-07-23): on_dormer openings JOIN the sheet and
    schedule — tagged in along-wall order with the rest, flagged
    on_dormer; their sills sit on the dormer plane, never grade-anchored
    (sill stays None — the door anchor lives on the wall plane)."""
    ops = [o for o in (raw.get("openings") or [])
           if str(o.get("wall", "")).lower() == wall_label]
    kept = []
    for o in ops:
        m = _nearest_matcher(o, matchers)
        if m and m["removed"]:
            continue
        kept.append((o, m))
    kept.sort(key=lambda om: (om[0].get("along_wall_ft")
                              if om[0].get("along_wall_ft") is not None else 1e9))
    # door anchor: grade fraction + inches-per-bbox-fraction scale
    anchor = None
    # dormer-plane sill chain (v-pos amendment, ruled 2026-07-22)
    dormer_chain = (_dormer_photo_chain(raw, wall_label)
                    if any(o.get("on_dormer") for o, _ in kept) else None)
    for o, _ in kept:
        if "door" in str(o.get("type", "")) and (o.get("bbox") or {}).get("h") and o.get("height_in"):
            bb = o["bbox"]
            anchor = {"grade_frac": bb["y"] + bb["h"],
                      "in_per_frac": float(o["height_in"]) / float(bb["h"])}
            break
    # SILL-BINDING EXTENSION (AUTHORIZED 2026-07-22): doorless walls —
    # per-photo head-line chain over wall windows, anchored at the
    # CONTRACTOR-SPEC 6'-8" header (ratified). Door anchor outranks it.
    head_chains = {}
    if anchor is None:
        by_photo = {}
        for o, _ in kept:
            if o.get("on_dormer") or "window" not in str(o.get("type", "")):
                continue
            # face-on evidence only: position-less windows mark corner
            # shots — their bbox geometry cannot carry the head chain
            if o.get("along_wall_ft") is None:
                continue
            if not (o.get("bbox") or {}).get("h") or not o.get("height_in"):
                continue
            by_photo.setdefault(o.get("bbox_photo_idx", o.get("photo_idx")), []).append(o)
        for ph, grp in by_photo.items():
            sc = sum(float(g["height_in"]) / float(g["bbox"]["h"]) for g in grp) / len(grp)
            head_chains[ph] = (sc, min(float(g["bbox"]["y"]) for g in grp))
    out, wn, dn, pn, vn, gn = [], 0, 0, 0, 0, 0
    for o, m in kept:
        eff_type = str(o.get("type", ""))
        if m and m["corrected_type"]:
            eff_type = str(m["corrected_type"])
        is_garage = "garage" in eff_type
        is_patio = "patio" in eff_type
        is_door = "door" in eff_type and not is_garage and not is_patio
        is_vent = "vent" in eff_type
        if is_garage:
            gn += 1
            tag = f"G{gn}"
            typ = "Garage door"
        elif is_patio:
            pn += 1
            tag = f"P{pn}"
            typ = "Patio door"
        elif is_door:
            dn += 1
            tag = f"D{dn}"
            typ = "Entry door"
        elif is_vent:
            vn += 1
            tag = f"V{vn}"
            typ = "Vent"
        else:
            wn += 1
            tag = f"W{wn}"
            typ = "Window"
        center = o.get("along_wall_ft")
        pos_tag = "AI-READ ✓" if center is not None else "ESTIMATED"
        sill_in, sill_tag = None, "ESTIMATED"
        if is_door or is_patio or is_garage:
            sill_in, sill_tag = 0.0, "AI-READ ✓"  # all door categories sit at grade (anchor by construction)
        elif o.get("on_dormer") and dormer_chain and (o.get("bbox") or {}).get("h") is not None:
            # v-pos amendment (ruled 2026-07-22): same-photo bbox chain,
            # head-anchored (CONTRACTOR-SPEC 6'-8" — ratified)
            d_scale, d_head, _ = dormer_chain
            bottom_frac = o["bbox"]["y"] + o["bbox"]["h"]
            sill_in = round(WINDOW_HEAD_ANCHOR_IN + (d_head - bottom_frac) * d_scale, 1)
            sill_tag = "ESTIMATED"
        elif (anchor and not o.get("on_dormer")
              and (o.get("bbox") or {}).get("h") is not None):
            bottom_frac = o["bbox"]["y"] + o["bbox"]["h"]
            sill_in = round((anchor["grade_frac"] - bottom_frac) * anchor["in_per_frac"], 1)
        elif (not o.get("on_dormer") and not is_vent
              and (o.get("bbox") or {}).get("h") is not None
              and o.get("along_wall_ft") is not None
              and o.get("bbox_photo_idx", o.get("photo_idx")) in head_chains):
            # sill-binding extension: head-anchor chain (doorless wall)
            h_scale, h_head = head_chains[o.get("bbox_photo_idx", o.get("photo_idx"))]
            bottom_frac = o["bbox"]["y"] + o["bbox"]["h"]
            sill_in = round(WINDOW_HEAD_ANCHOR_IN - (bottom_frac - h_head) * h_scale, 1)
            sill_tag = "ESTIMATED"
        out.append({
            "on_dormer": bool(o.get("on_dormer")),
            "dormer_face": _norm_face(o.get("dormer_face")) if o.get("on_dormer") else None,
            "tag": tag,
            "opening_id": o.get("opening_id"),
            "type": typ,
            "style": o.get("style") or "",
            "width_in": o.get("width_in"),
            "height_in": o.get("height_in"),
            "center_ft": center,
            "center_label": fmt_ftin(center) if center is not None else "—",
            "position_tag": pos_tag,
            "sill_in": sill_in,
            "sill_label": fmt_ftin(sill_in / 12.0) if sill_in is not None else "—",
            "sill_tag": sill_tag,
            "confirmed": True,   # verb machinery: no removal/ratify verbs pending
            "collision": False,  # set by the global collision guard (route level)
        })
    return out


@router.get("/estimates/{est_id}/elevation-sheet/{which}")
async def elevation_sheet(est_id: str, which: str, user: dict = Depends(get_current_user)):
    if which not in _SHEET_CODES:
        raise HTTPException(status_code=404, detail="Unknown elevation")
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]},
        {"_id": 0, "id": 1, "estimate_number": 1, "customer_name": 1, "address": 1,
         "lp_openings_review": 1, "lp_appendage_dims": 1})
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
    stepped = False
    if tape:
        segments = tape["segments"]
        stepped = len(segments) > 1
        # VIEW CONVENTION (exterior): the run's along_wall_ft datum is the
        # LEFT corner as viewed from OUTSIDE (extraction prompt iter
        # 79j.40) — openings are already in exterior-view space. Segments
        # arrive in tape order [front-adjacent, back-adjacent]; in the
        # exterior view of the LEFT wall the FRONT corner sits at the
        # drawing's RIGHT, so the LEFT sheet draws them REVERSED. LEFT
        # and RIGHT step positions are mirror-consistent by construction.
        if which == "left" and stepped:
            segments = list(reversed(segments))
        # tallest segment drives the drawing frame; EACH keeps its basis line
        height_ft = max(s["height_ft"] for s in segments)
        if tape["width_ft"] is not None:
            width_ft = tape["width_ft"]
            width_tag, width_source = tape["width_tag"], tape["width_source"]
            walls_basis_line = (f"sealed key {tape['key_number']} "
                                f"(tape, corrected {tape['key_corrected']}) — walls")
        else:
            # sides: width untaped — extraction-run fallback, LABELED
            width_ft = ai_width
            width_tag = ai_width_tag
            width_source = f"AI run {run['run_id'][:8]} ({wall.get('width_ft_source')}) — width untaped"
            walls_basis_line = (f"sealed key {tape['key_number']} "
                                f"(tape, corrected {tape['key_corrected']}) — heights"
                                f" · width AI run {run['run_id'][:8]}")
        first = segments[0]
        basis = {
            "width_tag": width_tag, "width_source": width_source,
            "height_tag": first["height_tag"], "height_formula": first["height_formula"],
            "exposure_in": tape["exposure_in"], "courses": first["courses"],
        }
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
    # tape governs and the run disagrees on either axis. On stepped walls
    # the AI's single height must miss EVERY tape segment to count as off.
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
                "ai_width_ft": ai_width,
                "ai_width_label": fmt_ftin(ai_width) if ai_width is not None else "—",
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

    # chimney chase (back wall) — AI accent read; dims TAPED per the
    # 2026-07-19 ratification amendment; position bound from the run's
    # chase corner-location reads (see below).
    roofline_obj = _bind_roofline(raw, which, height_ft, basis["height_tag"])
    # P5 (C-5 ruling): dormers face-on + cheek profiles on perpendiculars
    dormer, dormer_profiles = _bind_dormers(est, raw, which, width_ft, height_ft, roofline_obj)
    chase = None
    for acc in (wall.get("accent_profiles") or []):
        loc = str(acc.get("location") or "")
        if "chase" in loc.lower():
            chase = {"note": loc,
                     "profile": acc.get("profile_callout") or acc.get("profile") or "",
                     "tag": "AI-READ ✓", "footprint": "untaped — NOT TO SCALE"}
            break

    matchers = _schedule_matchers(run, est.get("lp_openings_review"))
    openings = _bind_openings(raw, which, matchers)
    cd = (tape or {}).get("chase_dims")
    # chase position — RULED 2026-07-19 (supersedes the AI corner-read
    # binding): ratified door-relative — chase sits LEFT of D1, siding
    # strip between (relationship CONFIRMED — human, photo); offset via
    # the ratify machinery, ESTIMATED (photo-scaled, untaped). D1 stays
    # where the run put it; the AI corner-read band stays ON RECORD as
    # the flagged comparison. Fallback (no ratified offset): bind from
    # the run's chase corner-location reads (span heuristic RETIRED).
    def _chase_fracs(wall_label):
        return [c["position_frac"] for c in (raw.get("corner_locations") or [])
                if "chase" in str(c.get("locator", "")).lower()
                and c.get("walls") == [wall_label]
                and c.get("position_frac") is not None]

    def _chase_reads(wall_label):
        return [{"frac": c["position_frac"],
                 "tier": str(c.get("tier") or "unconfirmed").lower(),
                 "type": c.get("type"),
                 "locator": c.get("locator"),
                 "sightings": c.get("sightings")}
                for c in (raw.get("corner_locations") or [])
                if "chase" in str(c.get("locator", "")).lower()
                and c.get("walls") == [wall_label]
                and c.get("position_frac") is not None]
    # P4 (ruled 2026-07-21): chases also DETECT from run corner reads —
    # an accent read is not required. FACE-WALL GUARD: accents name the
    # chase's FACE wall; projection edges also read on ADJACENT walls
    # (Letrick right wall carries 3 chase reads) and must not spawn face
    # glyphs — the fallback fires only when NO wall carries a chase
    # accent, this wall has a read SPAN (≥2 reads), and no other wall
    # carries more chase reads than this one.
    if not chase:
        any_chase_accent = any(
            "chase" in str(a.get("location", "")).lower()
            for w2 in (raw.get("walls") or [])
            for a in (w2.get("accent_profiles") or []))
        fr_here = _chase_fracs(which)
        read_counts = [len(_chase_fracs(lbl)) for lbl in ("front", "back", "left", "right")]
        if (not any_chase_accent and len(fr_here) >= 2
                and len(fr_here) == max(read_counts)):
            chase = {"note": "chimney chase (detected from run corner reads)",
                     "tag": "AI-READ ✓", "profile": "",
                     "footprint": "untaped"}
    if chase:
        fr = _chase_fracs(which)
        dr = _door_relative_chase_center(est, raw, (cd or {}).get("width_in")) if which == "back" else None
        if dr:
            off_tag = "TAPED" if dr["offset_taped"] else "ESTIMATED (photo-scaled, untaped)"
            chase["center_ft"] = round(dr["center_ft"], 1)
            chase["position_tag"] = "CONFIRMED (human, photo)"
            chase["position"] = (f"left of D1, siding strip between — relationship CONFIRMED (human, photo)"
                                 f" · right edge {fmt_inches(dr['offset_ft'] * 12.0)} left of D1 trim edge"
                                 f" — offset {off_tag}")
            chase["position_note"] = ("immediately left of D1, siding strip between"
                                      " — ruled 2026-07-19 (ratify machinery)")
            if fr and width_ft:
                ai_center = round((min(fr) + max(fr)) / 2 * width_ft, 1)
                chase["ai_band"] = {
                    "frac_lo": min(fr), "frac_hi": max(fr),
                    "center_ft": ai_center,
                    "delta_ft": round(ai_center - chase["center_ft"], 1),
                    "note": (f"AI corner-read band {min(fr):g}–{max(fr):g} frac → center {ai_center:g}'"
                             " — FLAGGED COMPARISON (superseded by ratified door-relative position)"),
                }
        elif fr and width_ft:
            # CONFIRMATION-WEIGHTED GEOMETRY (ruled 2026-07-22): confirmed
            # reads anchor; unconfirmed reads render as flagged comparison.
            # PROVENANCE RULE (ruled 2026-07-20) still governs: the ratified
            # relationship note renders ONLY on the dr path above.
            _bind_chase_position(chase, _chase_reads(which), width_ft, est)
    # chase ratification (Howard, ruled 2026-07-19): human ground truth —
    # projects from the back wall, lap-clad; dims TAPED via sealed-key
    # amendment. Supersedes "footprint untaped".
    if chase and cd:
        chase.update({
            "width_in": cd["width_in"], "depth_in": cd["depth_in"],
            "height_in": cd["height_in"],
            "width_label": fmt_inches(cd["width_in"]),
            "depth_label": fmt_inches(cd["depth_in"]),
            "height_label": fmt_ftin(cd["height_in"] / 12.0),
            "dims_tag": "TAPED",
            "taped_stamp": cd["taped"],
            "footprint": (f"{fmt_inches(cd['width_in'])} × {fmt_inches(cd['depth_in'])}"
                          f" — TAPED ({cd['taped']})"),
            "ratified": ("human ground truth (projects from back wall, lap-clad)"
                         " — ruled 2026-07-19; sealed key amendment"),
        })
    elif chase:
        # P4 dims ladder (ruled 2026-07-21) — scale-render at best-known
        # dims on every rung (C-4); each dim carries its rung's tag
        lad = _chase_dims_ladder(est, chase.pop("_lad_fr", None), width_ft, roofline_obj)
        if chase.get("_width_override"):
            v, t = chase.pop("_width_override")
            lad["width_in"], lad["width_tag"] = v, t
        parts = []
        for dim, mark in (("width", "W"), ("depth", "D"), ("height", "H")):
            v = lad.get(f"{dim}_in")
            if v is None:
                continue
            label = fmt_ftin(v / 12.0) if dim == "height" else fmt_inches(v)
            chase[f"{dim}_in"] = v
            chase[f"{dim}_label"] = label
            chase[f"{dim}_tag"] = lad[f"{dim}_tag"]
            parts.append(f"{label} {mark} {lad[f'{dim}_tag']}")
        if parts:
            chase["dims_tag"] = "LADDER"
            chase["footprint"] = " × ".join(parts)
    # sides: chase in PROFILE — ALWAYS drawn where the chase projects
    # (spec C, ruled 2026-07-21) at the best-known depth rung, tagged
    # with that rung. Letrick TAPED path first; generic ladder otherwise.
    chase_profile = None
    if which in ("left", "right") and cd:
        chase_profile = {
            "depth_in": cd["depth_in"], "height_in": cd["height_in"],
            "depth_label": fmt_inches(cd["depth_in"]),
            "height_label": fmt_ftin(cd["height_in"] / 12.0),
            "dims_tag": "TAPED",
            "anchor": "abuts back wall — position anchored (back corner)",
            "corner": "back",
            "note": (f"chimney chase in profile — projects {fmt_inches(cd['depth_in'])}"
                     f" proud of the back wall (TAPED {cd['taped']})"),
        }
    elif which in ("left", "right"):
        fr_b = _chase_fracs("back")
        wall_b = next((w for w in (raw.get("walls") or [])
                       if str(w.get("label", "")).lower() == "back"), None)
        has_chase_b = bool(fr_b) or any(
            "chase" in str(a.get("location", "")).lower()
            for a in ((wall_b or {}).get("accent_profiles") or []))
        if has_chase_b:
            conf_b = sorted({r["frac"] for r in _chase_reads("back")
                             if r["tier"] == "confirmed"})
            bt = _sealed_tape_basis(est, "back")
            hb = (max(s["height_ft"] for s in bt["segments"]) if bt
                  else (wall_b or {}).get("height_ft"))
            rl_b = (_bind_roofline(raw, "back", hb,
                                   "TAPED-DERIVED" if bt else _AI_TAGS.get(
                                       str((wall_b or {}).get("height_ft_source")), "ESTIMATED"))
                    if hb else None)
            lad = _chase_dims_ladder(est, conf_b if len(conf_b) >= 2 else None,
                                     (wall_b or {}).get("width_ft"), rl_b)
            if lad.get("depth_in") and lad.get("height_in"):
                rungs = " · ".join(sorted({str(lad["depth_tag"]).split(" ")[0],
                                           str(lad["height_tag"]).split(" ")[0]}))
                chase_profile = {
                    "depth_in": lad["depth_in"], "height_in": lad["height_in"],
                    "depth_label": fmt_inches(lad["depth_in"]),
                    "height_label": fmt_ftin(lad["height_in"] / 12.0),
                    "dims_tag": rungs,
                    "depth_tag": lad["depth_tag"], "height_tag": lad["height_tag"],
                    "anchor": (f"projects from the back wall — depth {lad['depth_tag']}"
                               f" · height {lad['height_tag']}"),
                    "corner": "back",
                    "note": (f"chimney chase in profile — projects "
                             f"{fmt_inches(lad['depth_in'])} proud of the back wall"
                             f" ({lad['depth_tag']})"),
                }
    # front: cap-over-ridge visibility — taped cap vs AI ridge band
    chase_cap = None
    if which == "front" and cd:
        cap_ft = cd["height_in"] / 12.0
        side_basis = _sealed_tape_basis(est, "left")
        eaves = [s["height_ft"] for s in side_basis["segments"]] if side_basis else []
        rises = [w.get("gable_triangle_height_ft") for w in (raw.get("walls") or [])
                 if str(w.get("label", "")).lower() in ("left", "right")
                 and w.get("gable_triangle_height_ft")]
        cands = [e + r for e in eaves for r in rises]
        if cands:
            chase_cap = {
                "cap_ft": round(cap_ft, 3), "cap_label": fmt_ftin(cap_ft),
                "cap_tag": "TAPED",
                "width_in": cd["width_in"],
                "width_label": fmt_inches(cd["width_in"]),
                "ridge_min_ft": round(min(cands), 3),
                "ridge_max_ft": round(max(cands), 3),
                "ridge_min_label": fmt_ftin(min(cands)),
                "ridge_max_label": fmt_ftin(max(cands)),
                "ridge_basis": "eave segments TAPED-DERIVED + gable rise AI-READ ⚠ — ESTIMATED band",
                "visible": cap_ft > max(cands),
                "clearance_worst_label": fmt_inches((cap_ft - max(cands)) * 12.0),
            }
            # front-view position = mirror of the BACK chase center —
            # ratified door-relative when on record (ruled 2026-07-19),
            # else the bound corner reads (exterior views mirror)
            dr_b = _door_relative_chase_center(est, raw, cd["width_in"])
            fr_b = _chase_fracs("back")
            if dr_b and width_ft:
                cap_off_tag = "TAPED" if dr_b["offset_taped"] else "ESTIMATED (photo-scaled, untaped)"
                chase_cap["center_ft"] = round(width_ft - dr_b["center_ft"], 1)
                chase_cap["position"] = ("mirrored from ratified door-relative back position"
                                         " — relationship CONFIRMED (human, photo)"
                                         f" · offset {cap_off_tag}")
                chase_cap["position_tag"] = "CONFIRMED (human, photo)"
            elif fr_b and width_ft:
                back_center = (min(fr_b) + max(fr_b)) / 2 * width_ft
                chase_cap["center_ft"] = round(width_ft - back_center, 1)
                chase_cap["position"] = ("mirrored from back chase-corner reads — AI-READ ✓"
                                         " · position untaped")
                chase_cap["position_tag"] = "AI-READ ✓"
            else:
                chase_cap = None  # no bound position — nothing rendered
    windows = [o for o in openings if o["type"] == "Window"]
    doors = [o for o in openings if o["type"] == "Entry door"]
    patio_doors = [o for o in openings if o["type"] == "Patio door"]
    vents = [o for o in openings if o["type"] == "Vent"]
    garage_doors = [o for o in openings if o["type"] == "Garage door"]

    # GLOBAL COLLISION GUARD — every sheet, every rendered wall element:
    # openings + chase glyph. FLAG-ALWAYS, SUPPRESS-NEVER (amended
    # 2026-07-21): both elements draw, both flag, callout directs to
    # Field Verify location review — never silent.
    guard_elements = []
    for o in openings:
        if o["center_ft"] is None or not o["width_in"]:
            continue
        half = float(o["width_in"]) / 24.0
        v_lo = v_hi = None
        if o["sill_in"] is not None and o["height_in"]:
            v_lo = float(o["sill_in"]) / 12.0
            v_hi = (float(o["sill_in"]) + float(o["height_in"])) / 12.0
        guard_elements.append({
            "name": o["tag"], "kind": "opening",
            "plane": f"dormer:{o.get('dormer_face') or ''}" if o.get("on_dormer") else "wall",
            "base": f"position {o['position_tag']} · center {o['center_label']}",
            "lo_ft": o["center_ft"] - half, "hi_ft": o["center_ft"] + half,
            "v_lo_ft": v_lo, "v_hi_ft": v_hi})
    if chase and chase.get("center_ft") is not None and chase.get("width_in"):
        half = float(chase["width_in"]) / 24.0
        guard_elements.append({
            "name": "CHASE", "kind": "appendage",
            "base": f"position {chase.get('position_tag', '—')} · center {fmt_ftin(chase['center_ft'])}",
            "lo_ft": chase["center_ft"] - half, "hi_ft": chase["center_ft"] + half,
            # chase rises from grade to its ladder height (when known)
            "v_lo_ft": 0.0 if chase.get("height_in") else None,
            "v_hi_ft": float(chase["height_in"]) / 12.0 if chase.get("height_in") else None})
    collisions = detect_collisions(guard_elements)
    for c in collisions:
        for o in openings:
            if o["tag"] in c["elements"]:
                o["collision"] = True
        if chase and "CHASE" in c["elements"]:
            chase["collision"] = True

    completed = run.get("completed_at")
    completed_str = str(completed)[:10] if completed else ""
    model_name = run.get("model_name") or (run.get("result") or {}).get("model") or ""
    # area: honest only when the wall is a rectangle — a stepped wall's
    # area needs the step location, which is UNTAPED.
    area, area_note = None, None
    if stepped:
        area_note = "not derivable — step location untaped"
    elif width_ft and height_ft:
        area = round(width_ft * height_ft, 1)

    schedule_note = ("Sizes + positions: AI run (along_wall_ft). "
                     "Sills: photo bbox, door-anchored (doors at grade).")
    if not openings:
        schedule_note = "No openings read on this wall."
    elif not (doors or patio_doors or garage_doors):
        # SILL-BINDING EXTENSION (authorized 2026-07-22): doorless walls
        # head-anchor at the ratified CONTRACTOR-SPEC 6'-8" header
        if any(o["sill_in"] is not None and not o.get("on_dormer") for o in openings):
            schedule_note += (" No door on this wall — window sills head-anchored"
                              " at the CONTRACTOR-SPEC 6'-8\" header (ratified).")
        else:
            schedule_note += " No door on this wall — sills not derivable (—)."

    return {
        "sheet": which,
        "sheet_code": _SHEET_CODES[which],
        "customer_name": est.get("customer_name"),
        "address": est.get("address"),
        "estimate_number": est.get("estimate_number"),
        "generated_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "wall": {
            "width_ft": width_ft,
            "width_label": fmt_ftin(width_ft) if width_ft is not None else "—",
            "height_ft": height_ft,
            "height_label": fmt_ftin(height_ft),
            **basis,
            "segments": segments,
            "step_note": ("stepped wall — step location NOT TAPED (indicative only)"
                          if stepped else None),
            "area_sqft": area,
            "area_note": area_note,
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
        "chase_profile": chase_profile,
        "chase_cap": chase_cap,
        # P3 (ruled 2026-07-21): roofline on every elevation
        "roofline": roofline_obj,
        # P5 (C-5 ruling): face-on dormer + perpendicular cheek profiles
        "dormer": dormer,
        "dormer_profiles": dormer_profiles,
        "view": {
            "convention": "viewed from exterior",
            "datum": ("along-wall datum: left corner as viewed from outside "
                      "(extraction prompt iter 79j.40)"),
            "mirrored_segments": bool(which == "left" and stepped),
        },
        "deviation": deviation,
        "collisions": collisions,
        "openings": openings,
        # CLOSED five-key contract (ruled 2026-07-20) — see module docstring
        "opening_counts": {"windows": len(windows), "doors": len(doors),
                           "patio_doors": len(patio_doors), "vents": len(vents),
                           "garage_doors": len(garage_doors)},
        "schedule_note": schedule_note,
        "geometry_basis": {
            "walls": walls_basis_line,
            "openings": f"openings: AI run {run['run_id'][:8]}…{run['run_id'][-2:]} ({model_name}, {completed_str})",
        },
        "run": {"run_id": run["run_id"], "model_name": model_name, "completed_at": completed_str},
    }
