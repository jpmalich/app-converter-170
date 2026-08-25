"""SEND-129 (Howard ruled 2026-08-25) — CORROBORATION AS THE LIFT.

The attribution gate is correct as the default. A located-but-unattributed
WIDTH may feed a quantity only when a SECOND INDEPENDENT READ corroborates
it. Otherwise it refuses, as built.

DECISION 1 — AGREEMENT RULE (derived, never chosen):
  the structural conditions
    · line-work RESOLVED on that face's own drawing,
    · a WALL-ONLY figure (plate-terminated corners), not a silhouette,
    · no fence-margin warning on that read,
    · a clean scale quote (not contested, not itself unattributed),
  PLUS Δ inside the ALREADY-REGISTERED 3.8% ELEVATION NOISE FLOOR
  (SEND-111, ocr_geometry.RULINGS_REGISTER findings): two elevations of
  the same house draw the same real dimension up to 3.8% apart, so no
  read can beat that spread. The floor is the drawing's own noise, not a
  number anybody picked. Δ IS PRINTED EITHER WAY.

DECISION 2 — WHICH FIGURE FEEDS: the PRINTED figure. Line-work's job is
  confirmation, not measurement; it carries a known residual we declined
  to chase.

STANDING LIMIT: corroboration is a WIDTH INSTRUMENT ONLY. It can never
corroborate a HEIGHT — the height is its ruler, so a height lift would be
circular by construction.
"""

NOISE_FLOOR_PCT = 3.8      # SEND-111, registered. Derived, not chosen.
WIDTH_INSTRUMENT_ONLY = (
    "corroboration is a width instrument only — the line-work read takes "
    "its ruler from the face's own datum chain, so corroborating a HEIGHT "
    "with it is circular by construction (SEND-129)")


def evaluate(printed_ft, read: dict | None) -> dict:
    """Does a second read corroborate this printed width?

    read: {status, wall_only_ft, silhouette_ft, fence_margin_warning,
           scale_quote, scale_contested, scale_quote_unattributed, reason}
    Returns {lifted, delta_ft, delta_pct, floor_pct, figure_that_feeds,
             statement} — Δ always reported, lifted or not.
    """
    out = {"lifted": False, "delta_ft": None, "delta_pct": None,
           "floor_pct": NOISE_FLOOR_PCT, "figure_that_feeds": None,
           "statement": None}
    try:
        printed = float(printed_ft)
    except (TypeError, ValueError):
        printed = 0.0
    if printed <= 0:
        out["statement"] = "no printed width to corroborate"
        return out
    read = read or {}
    if str(read.get("status")) != "RESOLVED":
        out["statement"] = (f"line-work {read.get('status') or 'ABSENT'}: "
                            f"{read.get('reason') or 'no second read'}")
        return out
    wall_only = read.get("wall_only_ft")
    if wall_only in (None, 0):
        out["statement"] = (
            "line-work RESOLVED but NO WALL-ONLY figure (no plate-"
            "terminated corners) — a silhouette includes projections and "
            "is never the compared figure")
        return out
    if read.get("fence_margin_warning"):
        out["statement"] = ("fence-margin warning on this read — a "
                            "neighbouring drawing's datum extent reaches "
                            "inside this face's fence, so the second read "
                            "may not be this face's: not corroboration")
        return out
    if read.get("scale_contested"):
        out["statement"] = (
            "the only scale on this face is CONTESTED — the corroborating "
            "read would be measured with a ruler whose own value is in "
            "dispute: circular, refused")
        return out
    if read.get("scale_quote_unattributed"):
        out["statement"] = (
            f"the scale quote {read.get('scale_quote') or '?'} is itself "
            "UNATTRIBUTED — a second read that inherits the ambiguity it "
            "is being used to resolve is not corroboration")
        return out
    delta = round(abs(printed - float(wall_only)), 2)
    pct = round(delta / printed * 100.0, 2)
    out["delta_ft"] = delta
    out["delta_pct"] = pct
    if pct > NOISE_FLOOR_PCT:
        out["statement"] = (
            f"printed {printed:g} ft vs drawn {float(wall_only):g} ft — "
            f"differ by {delta:g} ft ({pct:g}%), OUTSIDE the registered "
            f"{NOISE_FLOOR_PCT:g}% elevation noise floor: not corroborated")
        return out
    out["lifted"] = True
    out["figure_that_feeds"] = printed
    out["statement"] = (
        f"CORROBORATED — printed {printed:g} ft vs drawn "
        f"{float(wall_only):g} ft, differ by {delta:g} ft ({pct:g}%), "
        f"inside the registered {NOISE_FLOOR_PCT:g}% elevation noise "
        f"floor. The PRINTED figure feeds the quantity; the drawn read "
        f"confirms and never measures")
    return out
