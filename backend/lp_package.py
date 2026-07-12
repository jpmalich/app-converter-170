"""Iter 79j.93 — September LP-native package assembly (Phase 1, Howard-approved scope).
Deterministic: runs the shared `_build_lines` mapping with the LP PDF
formulas forced ON, keeps LP lines only, applies whole-piece rounding at
the SKU level everywhere, and overrides the 540 Series OSC line with the
C3 corner-location takeoff (amber corners included per presence
guarantee, flagged — honesty carries into the takeoff). Install-system
auto-adds (coil / touch-up / OSI Quad Max / J-blocks / Mini Splits) ride
the existing mapping spec unchanged. Dealer lines carry BlueLinx names
only for September (Howard ruling)."""
import math

from lp_smartside_formulas import override_flag

OSC_ITEM = "540 Series OSC 5/4\" x 4\" x 16'"
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


def osc_from_corner_locations(corner_locations, wall_heights: dict, avg_height_ft):
    """540 OSC takeoff from C3 corner locations: sum of per-corner wall
    heights ÷ 16' pieces, ceil (Howard ruling). Two-wall corners use the
    shorter adjacent wall; elevated posts are priced at full wall height
    (conservative — trim to post height in field) and flagged."""
    oscs = [l for l in corner_locations or [] if str(l.get("type")) == "outside"]
    if not oscs:
        return None
    total_lf = 0.0
    amber = elevated = 0
    for l in oscs:
        total_lf += _corner_height_ft(l, wall_heights, avg_height_ft)
        if l.get("tier") != "confirmed":
            amber += 1
        if l.get("elevated"):
            elevated += 1
    qty = max(1, math.ceil(total_lf / OSC_PIECE_LEN_FT - 1e-9))
    note_bits = [
        f"C3 corner locations: {len(oscs)} OSC, {round(total_lf, 1)} LF ÷ 16' pieces, whole-piece"
    ]
    if amber:
        note_bits.append(f"includes {amber} unconfirmed (amber) location(s) — field verify")
    if elevated:
        note_bits.append(
            f"{elevated} elevated post(s) priced at full wall height — trim to post height in field"
        )
    return {
        "qty": qty,
        "note": "; ".join(note_bits),
        "osc_count": len(oscs),
        "amber": amber,
        "elevated": elevated,
        "total_lf": round(total_lf, 1),
    }


def assemble_lp_package(measurements: dict, corner_locations=None, wall_heights=None) -> dict:
    from routes.hover import _build_lines  # local import to dodge cycle

    with override_flag(True):
        lines = [l for l in _build_lines(dict(measurements)) if l.get("tab") == "lp_smart"]

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
    avg_h = measurements.get("_ai_avg_wall_height_ft")
    osc = osc_from_corner_locations(corner_locations, wall_heights or {}, avg_h)
    if osc:
        replaced = False
        for l in lines:
            if l["name"] == OSC_ITEM:
                l["qty"] = osc["qty"]
                l["note"] = osc["note"]
                replaced = True
        if not replaced:
            lines.append({
                "tab": "lp_smart",
                "section": "LP Siding Accessories",
                "name": OSC_ITEM,
                "unit": "PCS",
                "qty": osc["qty"],
                "note": osc["note"],
            })
        if osc["amber"]:
            flags.append(
                f"{osc['amber']} amber corner location(s) included per presence guarantee — field verify before ordering"
            )
        if osc["elevated"]:
            flags.append(f"{osc['elevated']} elevated post(s) priced at full wall height")
    else:
        # fallback path still honors whole-piece: the legacy spec uses
        # round(), which can under-order (37.6 LF → 2 pcs); ceil it.
        try:
            lf = float(measurements.get("outside_corner_lf") or 0)
        except (TypeError, ValueError):
            lf = 0.0
        if lf > 0:
            for l in lines:
                if l["name"] == OSC_ITEM:
                    q = max(1, math.ceil(lf / OSC_PIECE_LEN_FT - 1e-9))
                    if q != l["qty"]:
                        l["qty"] = q
                        l["note"] = f"LP 16' outside-corner pieces — whole-piece: {lf:g} LF ÷ 16' = {q}"

    return {
        "lines": lines,
        "summary": {
            "line_count": len(lines),
            "total_pieces": sum(l["qty"] for l in lines if l.get("unit") == "PCS"),
            "osc_source": "c3_corner_locations" if osc else "outside_corner_lf",
            **({"osc_detail": osc} if osc else {}),
            "flags": flags,
        },
    }
