"""Iter 79j.93/.94 — September LP-native package assembly.
Deterministic: runs the shared `_build_lines` mapping with the LP PDF
formulas forced ON, keeps LP lines only, whole-piece rounding at the SKU
level everywhere, and applies the RULED LP trim system (2026-07-11):
  - 540 Series OSC per outside-corner location, WHOLE STICKS PER LOCATION
    (stick length 16' pending confirmation, flagged; splice rule on >16'
    corners pending, flagged)
  - 440 Series Trim 4/4"×4"×16' per INSIDE-corner location (C3-driven)
  - 440 Series Trim 4/4"×8"×16' fascia + rake boards (rake = slope
    length, never plan-view; splice + presence pendings flagged)
  - 540 Series Trim 5/4"×4"×16' window/door wrap (door 3/4-side pending)
  - COMPOSITION GUARD: J-channel / finish trim / coil lines on an
    LP-native takeoff are composition bugs — stripped and reported.
Amber corner locations included per presence guarantee, flagged —
honesty carries into the takeoff."""
import math

from lp_conventions import (
    FASCIA_RAKE_ITEM, ISC_TRIM_ITEM, PENDING_CONFIRMATIONS, TRIM_STICK_LEN_FT,
    WRAP_TRIM_ITEM, fascia_rake_takeoff, line_math, lp_composition_bugs,
)
from lp_smartside_formulas import lap_coverage_sqft_per_pc, override_flag

OSC_ITEM = "540 Series OSC 5/4\" x 4\" x 16'"
LAP8_ITEM = "38 Series Lap 3/8\" x 8\" x 16'"
OSC_PIECE_LEN_FT = 16.0


def _corner_height_ft(loc: dict, wall_heights: dict, avg_h) -> float:
    hs = []
    for w in loc.get("walls") or []:
        try:
            h = float(wall_heights.get(w) or 0)
        except (TypeError, ValueError):
            h = 0
        if h > 0:
            hs.append(h)
    if hs:
        return min(hs)
    try:
        return float(avg_h or 0)
    except (TypeError, ValueError):
        return 0.0


def _corner_sticks(locs, wall_heights: dict, avg_height_ft, stick_len: float):
    """RULED: whole sticks PER LOCATION (never pooled LF). Returns
    (sticks, total_lf, amber, elevated, any_over_stick)."""
    sticks = 0
    total_lf = 0.0
    amber = elevated = 0
    over = False
    for l in locs:
        h = _corner_height_ft(l, wall_heights, avg_height_ft)
        total_lf += h
        sticks += max(1, int(math.ceil(h / stick_len - 1e-9))) if h > 0 else 1
        if h > stick_len:
            over = True
        if l.get("tier") != "confirmed":
            amber += 1
        if l.get("elevated"):
            elevated += 1
    return sticks, round(total_lf, 1), amber, elevated, over


def osc_from_corner_locations(corner_locations, wall_heights: dict, avg_height_ft):
    """540 OSC takeoff: whole sticks per outside-corner location (Howard
    ruling). Elevated posts priced at full wall height (conservative)."""
    oscs = [l for l in corner_locations or [] if str(l.get("type")) == "outside"]
    if not oscs:
        return None
    sticks, total_lf, amber, elevated, over = _corner_sticks(
        oscs, wall_heights, avg_height_ft, OSC_PIECE_LEN_FT)
    note_bits = [
        f"C3: {len(oscs)} OSC locations, whole sticks per location = {sticks} "
        f"({total_lf} LF; 16' stick length pending confirmation)"
    ]
    flags = [PENDING_CONFIRMATIONS["osc_stick_length"]]
    if over:
        note_bits.append("corner run(s) over 16' — splice rule pending, ceil-per-location held")
        flags.append(PENDING_CONFIRMATIONS["corner_splice_rule"])
    if amber:
        note_bits.append(f"includes {amber} unconfirmed (amber) location(s) — field verify")
    if elevated:
        note_bits.append(
            f"{elevated} elevated post(s) priced at full wall height — trim to post height in field"
        )
    return {
        "qty": sticks,
        "note": "; ".join(note_bits),
        "osc_count": len(oscs),
        "amber": amber,
        "elevated": elevated,
        "total_lf": total_lf,
        "flags": flags,
    }


def isc_from_corner_locations(corner_locations, wall_heights: dict, avg_height_ft):
    """440 4/4"×4"×16' per inside-corner location (ruled)."""
    iscs = [l for l in corner_locations or [] if str(l.get("type")) == "inside"]
    if not iscs:
        return None
    sticks, total_lf, amber, _, over = _corner_sticks(
        iscs, wall_heights, avg_height_ft, TRIM_STICK_LEN_FT)
    note_bits = [f"C3: {len(iscs)} ISC locations, whole sticks per location = {sticks} ({total_lf} LF)"]
    flags = []
    if over:
        note_bits.append("run(s) over 16' — splice rule pending")
        flags.append(PENDING_CONFIRMATIONS["corner_splice_rule"])
    if amber:
        note_bits.append(f"includes {amber} unconfirmed (amber) location(s) — field verify")
    return {"qty": sticks, "note": "; ".join(note_bits), "isc_count": len(iscs),
            "amber": amber, "total_lf": total_lf, "flags": flags}


def assemble_lp_package(measurements: dict, corner_locations=None, wall_heights=None) -> dict:
    from routes.hover import _build_lines  # local import to dodge cycle

    with override_flag(True):
        lines = [l for l in _build_lines(dict(measurements)) if l.get("tab") == "lp_smart"]

    # COMPOSITION GUARD (ruled): strip J-channel / finish trim / coil
    removed = lp_composition_bugs(lines)
    if removed:
        lines = [l for l in lines if l.get("name") not in removed]

    # whole-piece rounding at the SKU level, everywhere
    for l in lines:
        try:
            q = float(l.get("qty") or 0)
        except (TypeError, ValueError):
            q = 0.0
        rq = int(math.ceil(q - 1e-9))
        if rq != q:
            l["note"] = f"{l.get('note') or ''} — whole-piece: {q:g} → {rq}".strip(" —")
        l["qty"] = rq

    flags = []
    # transparency math on the formula-driven siding line
    try:
        sqft = float(measurements.get("siding_sqft") or 0)
    except (TypeError, ValueError):
        sqft = 0.0
    if sqft > 0:
        for l in lines:
            if l["name"] == LAP8_ITEM:
                l["math"] = line_math(sqft, lap_coverage_sqft_per_pc())

    def _set_line(name: str, section: str, qty: int, note: str):
        for l in lines:
            if l["name"] == name:
                l["qty"] = qty
                l["note"] = note
                return
        lines.append({"tab": "lp_smart", "section": section, "name": name,
                      "unit": "PCS", "qty": qty, "note": note})

    avg_h = measurements.get("_ai_avg_wall_height_ft")
    osc = osc_from_corner_locations(corner_locations, wall_heights or {}, avg_h)
    if osc:
        _set_line(OSC_ITEM, "LP Siding Accessories", osc["qty"], osc["note"])
        if osc["amber"]:
            flags.append(
                f"{osc['amber']} amber corner location(s) included per presence guarantee — field verify before ordering"
            )
        if osc["elevated"]:
            flags.append(f"{osc['elevated']} elevated post(s) priced at full wall height")
    else:
        # fallback path still honors whole-piece (legacy spec round() under-orders)
        try:
            lf = float(measurements.get("outside_corner_lf") or 0)
        except (TypeError, ValueError):
            lf = 0.0
        if lf > 0:
            q = max(1, math.ceil(lf / OSC_PIECE_LEN_FT - 1e-9))
            _set_line(OSC_ITEM, "LP Siding Accessories", q,
                      f"LP 16' outside-corner pieces — whole-piece: {lf:g} LF ÷ 16' = {q}")

    # 440 4/4"×4": ISC locations ONLY (horizontal runs superseded by the
    # 4/4"×8" fascia/rake item — full profile spec always, never bare)
    isc = isc_from_corner_locations(corner_locations, wall_heights or {}, avg_h)
    if isc:
        _set_line(ISC_TRIM_ITEM, "LP SmartSide Trim", isc["qty"], isc["note"])
        if isc["amber"]:
            flags.append(f"{isc['amber']} amber inside-corner location(s) included — field verify")

    # 440 4/4"×8": fascia + rake boards (rake = measured slope LF, never plan-view)
    fr = fascia_rake_takeoff(measurements.get("eaves_lf") or 0, measurements.get("rakes_lf") or 0)
    if fr["ordered_pcs"] > 0:
        _set_line(
            FASCIA_RAKE_ITEM, "LP SmartSide Trim", fr["ordered_pcs"],
            f"Fascia (eaves {measurements.get('eaves_lf') or 0:g} LF) + rake slope "
            f"({measurements.get('rakes_lf') or 0:g} LF) = {fr['total_lf']} LF × 1.10 "
            f"÷ 16' sticks = {fr['ordered_pcs']} — splice-and-round-up assumed (pending); "
            "presence toggle pending (remodels keeping existing fascia)",
        )

    # 540 wrap: door side-count pending — flag, do not change derivation
    for l in lines:
        if l["name"] == WRAP_TRIM_ITEM:
            l["note"] = f"{l.get('note') or ''} — door trim 3-side vs 4-side pending (4-side derivation held)".strip(" —")

    pending = [PENDING_CONFIRMATIONS["osc_stick_length"],
               PENDING_CONFIRMATIONS["door_trim_sides"]]
    if osc and any("splice" in f for f in osc.get("flags") or []):
        pending.append(PENDING_CONFIRMATIONS["corner_splice_rule"])
    if fr["ordered_pcs"] > 0:
        pending += [PENDING_CONFIRMATIONS["fascia_rake_splice"],
                    PENDING_CONFIRMATIONS["fascia_rake_presence"]]

    return {
        "lines": lines,
        "summary": {
            "line_count": len(lines),
            "total_pieces": sum(l["qty"] for l in lines if l.get("unit") == "PCS"),
            "osc_source": "c3_corner_locations" if osc else "outside_corner_lf",
            **({"osc_detail": osc} if osc else {}),
            **({"isc_detail": isc} if isc else {}),
            "fascia_rake": fr,
            "composition_guard_removed": removed,
            "flags": flags,
            "pending_confirmations": pending,
        },
    }
