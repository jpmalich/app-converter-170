"""RULINGS CC + DD (Howard sealed 2026-08-14 send-24) — footprint sanity
instruments that need NO area table (dead per Howard), NO OCR positions and
NO anchor. They convert a silent coin-flip into a loud, named refusal while
the real face-disambiguation is built on an OCR-position substrate.

  CC  garage_side_verdict — the CONTRADICTION DETECTOR. Where the garage's
      side signals (door placement, garage naming, elevation labels)
      disagree, refuse BOTH sides and NAME the conflict. No majority vote,
      no winner. Absence is NOT agreement (Condition 1). Must FIRE on Boni
      today (Condition 2) — the app puts the garage doors on FRONT while the
      garage naming spans FRONT+BACK, and the truth is a RIGHT side-entry.
      Ruling BB: the door signal's face attribution is currently KNOWN-WRONG,
      so it is flagged unreliable; the garage LABEL is the independent one.

  DD  footprint_closure — a side's segments must SUM to that side's depth and
      the sides must be consistent with the front/back widths. Right at
      30+9=39 on a house with no 39' side violates closure and nothing
      checked it. A footprint that does not close is REPORTED as not
      closing, the failing relation NAMED, and the faces depending on it are
      listed so they can go NOT DERIVABLE rather than derive from parts that
      contradict each other.
"""
from __future__ import annotations

FACES = ("front", "back", "left", "right")
_OPPOSITE = {"front": "back", "back": "front", "left": "right", "right": "left"}


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _has_garage(text: str) -> bool:
    return "garage" in (text or "").lower()


def garage_side_signals(m: dict) -> dict:
    """The three independent garage-side signals, each a sorted list of the
    faces it implicates — or None when the signal is ABSENT (not read)."""
    walls = m.get("walls") or []
    doors = m.get("doors") or []
    planes = m.get("roof_planes") or []

    door_faces = sorted({str(d.get("elevation")) for d in doors
                         if (_has_garage(str(d.get("type_hint")))
                             or _has_garage(str(d.get("type"))))
                         and d.get("elevation")})

    name_faces = set()
    for w in walls:
        blob = str(w.get("label") or "") + " " + " ".join(
            str(s.get("label") or "") for s in (w.get("height_segments") or [])
            if isinstance(s, dict))
        if _has_garage(blob) and w.get("label"):
            name_faces.add(str(w.get("label")))
    for p in planes:
        if _has_garage(str(p.get("label"))):
            for fc in (p.get("gable_end_faces") or []):
                name_faces.add(str(fc))

    elev_faces = set()
    for e in (m.get("elevation_labels") or m.get("sheets_identified") or []):
        if isinstance(e, dict) and _has_garage(str(e.get("title") or e.get("label"))):
            fc = e.get("face") or e.get("elevation")
            if fc:
                elev_faces.add(str(fc))

    return {
        "garage_doors": door_faces or None,
        "garage_naming": sorted(name_faces) or None,
        "elevation_labels": sorted(elev_faces) or None,
    }


def garage_side_verdict(m: dict) -> dict:
    """RULING CC. Returns {status, side, signals, present, absent, conflict,
    door_signal_unreliable, note}. status ∈ VERIFIED / UNVERIFIED / CONFLICT.
    Never picks a winner; a conflict refuses both sides."""
    sig = garage_side_signals(m)
    present = {k: v for k, v in sig.items() if v}
    absent = [k for k, v in sig.items() if not v]

    if len(present) <= 1:
        only = next(iter(present), None)
        return {
            "status": "UNVERIFIED", "side": None, "signals": sig,
            "present": list(present), "absent": absent, "conflict": None,
            "door_signal_unreliable": True,
            "note": ("garage side UNVERIFIED — absence is not agreement "
                     "(Ruling CC C1): "
                     + (f"only signal present: {only}={present[only]}; "
                        if only else "no garage-side signal present; ")
                     + f"absent: {', '.join(absent) or 'none'}. A single "
                     "unopposed signal is not confirmation."),
        }

    face_sets = {k: tuple(v) for k, v in present.items()}
    if len(set(face_sets.values())) > 1:
        conflict = {k: list(v) for k, v in present.items()}
        pairs = "; ".join(f"{k} → {v}" for k, v in present.items())
        return {
            "status": "CONFLICT", "side": None, "signals": sig,
            "present": list(present), "absent": absent, "conflict": conflict,
            "door_signal_unreliable": True,
            "note": ("garage side REFUSED — signals disagree, no majority vote, "
                     f"no winner (Ruling CC): {pairs}. Door placement's face "
                     "attribution is currently known-wrong (Ruling BB) and is "
                     "not a trusted signal; the garage label is the independent "
                     "one. Both sides refused until face-disambiguation lands."),
        }

    side = list(next(iter(face_sets.values())))
    return {
        "status": "VERIFIED", "side": side, "signals": sig,
        "present": list(present), "absent": absent, "conflict": None,
        "door_signal_unreliable": True,
        "note": (f"garage-side signals agree on {side}; note this resolves "
                 "WHICH SIDE only, not which depth (Ruling CC)."),
    }


def _wall_by_label(m, label):
    for w in (m.get("walls") or []):
        if str(w.get("label")) == label:
            return w
    return None


def footprint_closure(m: dict) -> dict:
    """RULING DD. Checks that need no area table / OCR / anchor:
      1. opposing WIDTHS agree  (front width == back width),
      2. SEGMENTS sum to their face width,
      3. opposing DEPTHS: a side whose opposite is unread cannot be closed →
         its depending face is UNVERIFIED (never confirmed from one end).
    Returns {closes, checks, failing_relations, unverified_faces}."""
    checks, failing, unverified = [], [], []

    def _width(face):
        w = _wall_by_label(m, face)
        return (_f(w.get("width_ft")) if w else 0.0), w

    # 1. opposing widths (front/back is the width pair; left/right is depth).
    fw, _ = _width("front")
    bw, _ = _width("back")
    if fw > 0 and bw > 0:
        ok = abs(fw - bw) < 0.5
        checks.append({"relation": "front.width == back.width",
                       "values": [fw, bw], "ok": ok})
        if not ok:
            failing.append(f"front width {fw:g} != back width {bw:g} — footprint does not close on width")

    # 2. segments sum to their face width.
    for w in (m.get("walls") or []):
        segs = [s for s in (w.get("height_segments") or []) if isinstance(s, dict)]
        sw = sum(_f(s.get("width_ft")) for s in segs)
        tw = _f(w.get("width_ft"))
        if segs and sw > 0 and tw > 0 and abs(sw - tw) >= 0.5:
            failing.append(
                f"{w.get('label')} segments sum to {sw:g} but the face width is "
                f"{tw:g} — segments do not close to the face")
            checks.append({"relation": f"{w.get('label')} Σsegments == width",
                           "values": [sw, tw], "ok": False})

    # 3. opposing depths — one end present, the other unread ⇒ cannot close.
    for a, b in (("left", "right"),):
        wa, wb = _wall_by_label(m, a), _wall_by_label(m, b)
        da = _f(wa.get("width_ft")) if wa else 0.0
        db = _f(wb.get("width_ft")) if wb else 0.0
        # rebuild depth from segments if the top-level is absent
        def _seg_depth(w):
            return sum(_f(s.get("width_ft")) for s in (w.get("height_segments") or [])
                       if isinstance(s, dict)) if w else 0.0
        da = da or _seg_depth(wa)
        db = db or _seg_depth(wb)
        if da > 0 and db <= 0:
            unverified.append(a)
            failing.append(f"{a} depth {da:g} present but opposing {b} depth not read — {a} cannot be closed")
        elif db > 0 and da <= 0:
            unverified.append(b)
            failing.append(f"{b} depth {db:g} present but opposing {a} depth not read — {b} cannot be closed")
        elif da > 0 and db > 0 and abs(da - db) >= 0.5:
            # allowed only if a named wing explains it; otherwise flag.
            failing.append(f"{a} depth {da:g} != {b} depth {db:g} — footprint sides do not close (unexplained)")

    return {
        "closes": not failing,
        "checks": checks,
        "failing_relations": failing,
        "unverified_faces": sorted(set(unverified)),
    }
