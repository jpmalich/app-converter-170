"""Iter 79j.93/.94 — September LP-native package assembly.
Deterministic engine per Howard's rulings (2026-07-11):
  - 540 OSC 5/4"×6"×16' DEFAULT (Howard's convention) — whole sticks per
    outside-corner location; 440 4/4"×4" per ISC location; 440 4/4"×8"
    fascia+rake (slope LF, never plan-view); 540 5/4"×4" window/door wrap.
  - COMPOSITION GUARD: J-channel / finish trim / coil = composition bugs.
  - LP STARTER: non-SKU informational line, ALWAYS present — LF derived
    from start-course length, 0 pieces by default (field-ripped from
    siding stock); thin-waste-margin annotation per near-boundary doctrine.
  - MATERIAL-LIST SUBSTITUTION: per-line, opt-in, limited to the known LP
    product table, triggers FULL RE-DERIVATION from stored geometry
    (never a reprice of a stale count), carries substituted_from
    provenance. Defaults remain Howard's conventions — nothing is
    silently remembered as a new global default."""
import math
import re

from lp_conventions import (
    FASCIA_RAKE_ITEM, ISC_TRIM_ITEM, PENDING_CONFIRMATIONS, TRIM_STICK_LEN_FT,
    WRAP_TRIM_ITEM, fascia_rake_takeoff, line_math, lp_composition_bugs,
)
from lp_smartside_formulas import lap_coverage_sqft_per_pc, override_flag

OSC_ITEM = "540 Series OSC 5/4\" x 6\" x 16'"   # Howard's default width
LAP8_ITEM = "38 Series Lap 3/8\" x 8\" x 16'"
STARTER_LINE_NAME = "LP Starter — field-ripped from siding stock"
SIDING_BOARD_LEN_FT = 16.0

_STICK_LEN_RE = re.compile(r"x\s*(\d+)'")


def _stick_len_ft(item_name: str) -> float:
    m = _STICK_LEN_RE.search(item_name or "")
    return float(m.group(1)) if m else 16.0


def _lp_product_table() -> dict:
    """Known LP product table from the catalog seed — substitution
    options never include free-text SKUs inventing products."""
    import catalog_seed as cs
    out = {"osc": [], "trim": []}
    for sec in cs.SECTION_LAYOUT:
        name, _, items = sec[0], sec[1], sec[2]
        if name == "LP Siding Accessories":
            out["osc"] = [i for i in items if "OSC" in i]
        elif name == "LP SmartSide Trim":
            out["trim"] = [i for i in items if "Series Trim" in i]
    return out


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


def corner_sticks_for_length(heights: list, stick_len_ft: float) -> int:
    """RULED (six-ruling block): whole stick per location for runs ≤ stick
    length; runs OVER stick length SPLICE-AND-ROUND-UP TOTAL STICKS —
    full sticks per run + over-length tails POOLED into shared sticks
    (uniform with fascia/rake). Stick-length changes recompute counts."""
    sticks = 0
    tails = 0.0
    for h in heights:
        h = float(h or 0)
        if h <= 0:
            sticks += 1
            continue
        if h <= stick_len_ft + 1e-9:
            sticks += 1
        else:
            sticks += int(h // stick_len_ft)
            rem = h % stick_len_ft
            if rem > 1e-9:
                tails += rem
    if tails > 0:
        sticks += int(math.ceil(tails / stick_len_ft - 1e-9))
    return sticks


def _corner_takeoff(locs, wall_heights: dict, avg_height_ft, stick_len: float):
    heights = [_corner_height_ft(l, wall_heights, avg_height_ft) for l in locs]
    amber = sum(1 for l in locs if l.get("tier") != "confirmed")
    elevated = sum(1 for l in locs if l.get("elevated"))
    return {
        "heights": [round(h, 2) for h in heights],
        "sticks": corner_sticks_for_length(heights, stick_len),
        "total_lf": round(sum(heights), 1),
        "amber": amber,
        "elevated": elevated,
        "over_stick": any(h > stick_len for h in heights),
    }


def osc_from_corner_locations(corner_locations, wall_heights: dict, avg_height_ft,
                              stick_len: float = 16.0):
    oscs = [l for l in corner_locations or [] if str(l.get("type")) == "outside"]
    if not oscs:
        return None
    t = _corner_takeoff(oscs, wall_heights, avg_height_ft, stick_len)
    note_bits = [
        f"C3: {len(oscs)} OSC locations, whole sticks per location = {t['sticks']} "
        f"({t['total_lf']} LF; 16' (192\") stick length CONFIRMED)"
    ]
    flags = []
    if t["over_stick"]:
        note_bits.append("run(s) over stick length — splice-and-round-up, tails pooled (ruled)")
    if t["amber"]:
        note_bits.append(f"includes {t['amber']} unconfirmed (amber) location(s) — field verify")
    if t["elevated"]:
        note_bits.append(
            f"{t['elevated']} elevated post(s) priced at full wall height — trim to post height in field")
    return {"qty": t["sticks"], "note": "; ".join(note_bits), "osc_count": len(oscs),
            "amber": t["amber"], "elevated": t["elevated"], "total_lf": t["total_lf"],
            "heights": t["heights"], "flags": flags}


def isc_from_corner_locations(corner_locations, wall_heights: dict, avg_height_ft,
                              stick_len: float = TRIM_STICK_LEN_FT):
    iscs = [l for l in corner_locations or [] if str(l.get("type")) == "inside"]
    if not iscs:
        return None
    t = _corner_takeoff(iscs, wall_heights, avg_height_ft, stick_len)
    note_bits = [f"C3: {len(iscs)} ISC locations, whole sticks per location = {t['sticks']} ({t['total_lf']} LF)"]
    flags = []
    if t["over_stick"]:
        note_bits.append("run(s) over stick length — splice-and-round-up, tails pooled (ruled)")
    if t["amber"]:
        note_bits.append(f"includes {t['amber']} unconfirmed (amber) location(s) — field verify")
    return {"qty": t["sticks"], "note": "; ".join(note_bits), "isc_count": len(iscs),
            "amber": t["amber"], "total_lf": t["total_lf"], "heights": t["heights"], "flags": flags}


def assemble_lp_package(measurements: dict, corner_locations=None, wall_heights=None,
                        substitutions: dict | None = None,
                        colors: dict | None = None) -> dict:
    from routes.hover import _build_lines  # local import to dodge cycle

    with override_flag(True):
        lines = [l for l in _build_lines(dict(measurements)) if l.get("tab") == "lp_smart"]

    # COMPOSITION GUARD (ruled): strip J-channel / finish trim / coil
    removed = lp_composition_bugs(lines)
    if removed:
        lines = [l for l in lines if l.get("name") not in removed]

    # PER-SYSTEM TABLE (amendment): LP soffit panels EAVES ONLY — the
    # rake-driven Closed soffit row is a cross-system line on LP-native
    # (rakes carry 440 4/4"×8" rake boards instead)
    system_enforced = []
    rake_soffit = next((l for l in lines if l["name"] == "38 Series Soffit 16 x 16 Closed"), None)
    if rake_soffit is not None:
        lines.remove(rake_soffit)
        system_enforced.append(
            "38 Series Soffit 16 x 16 Closed removed — LP soffit panels eaves only "
            "(no rake soffit wrap); rakes carry 440 4/4\"×8\" rake boards")
    for l in lines:
        if l["name"] == "38 Series Soffit 16 x 16 Vented":
            l["note"] = f"{l.get('note') or ''} — LP soffit panels eaves only (per-system rule)".strip(" —")

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
    try:
        sqft = float(measurements.get("siding_sqft") or 0)
    except (TypeError, ValueError):
        sqft = 0.0
    lap_math = None
    if sqft > 0:
        for l in lines:
            if l["name"] == LAP8_ITEM:
                lap_math = line_math(sqft, lap_coverage_sqft_per_pc())
                l["math"] = lap_math

    def _set_line(name: str, section: str, qty: int, note: str, **extra):
        for l in lines:
            if l["name"] == name:
                l["qty"] = qty
                l["note"] = note
                l.update(extra)
                return l
        new = {"tab": "lp_smart", "section": section, "name": name,
               "unit": "PCS", "qty": qty, "note": note, **extra}
        lines.append(new)
        return new

    avg_h = measurements.get("_ai_avg_wall_height_ft")

    # ── OSC: Howard's default width 5/4"×6" — spec-emitted OSC rows superseded
    lines[:] = [l for l in lines if "540 Series OSC" not in l["name"]]
    osc = osc_from_corner_locations(corner_locations, wall_heights or {}, avg_h)
    if osc:
        _set_line(OSC_ITEM, "LP Siding Accessories", osc["qty"], osc["note"],
                  _derivation={"kind": "osc", "heights": osc["heights"]})
        if osc["amber"]:
            flags.append(f"{osc['amber']} amber corner location(s) included per presence guarantee — field verify before ordering")
        if osc["elevated"]:
            flags.append(f"{osc['elevated']} elevated post(s) priced at full wall height")
    else:
        try:
            lf = float(measurements.get("outside_corner_lf") or 0)
        except (TypeError, ValueError):
            lf = 0.0
        if lf > 0:
            q = max(1, math.ceil(lf / 16.0 - 1e-9))
            _set_line(OSC_ITEM, "LP Siding Accessories", q,
                      f"LP 16' outside-corner pieces — whole-piece: {lf:g} LF ÷ 16' = {q}",
                      _derivation={"kind": "osc_lf", "lf": lf})

    # ── 440 4/4"×4": ISC locations only (full profile spec, never bare)
    isc = isc_from_corner_locations(corner_locations, wall_heights or {}, avg_h)
    if isc:
        _set_line(ISC_TRIM_ITEM, "LP SmartSide Trim", isc["qty"], isc["note"],
                  _derivation={"kind": "isc", "heights": isc["heights"]})
        if isc["amber"]:
            flags.append(f"{isc['amber']} amber inside-corner location(s) included — field verify")

    # ── 440 4/4"×8": fascia + rake boards
    eaves_lf = float(measurements.get("eaves_lf") or 0)
    rakes_lf = float(measurements.get("rakes_lf") or 0)
    fr = fascia_rake_takeoff(eaves_lf, rakes_lf)
    if fr["ordered_pcs"] > 0:
        _set_line(
            FASCIA_RAKE_ITEM, "LP SmartSide Trim", fr["ordered_pcs"],
            f"Fascia (eaves {eaves_lf:g} LF) + rake slope ({rakes_lf:g} LF) = {fr['total_lf']} LF "
            f"× 1.10 ÷ 16' sticks = {fr['ordered_pcs']} — one product both run types; "
            "splice-and-round-up total sticks (ruled); always present on LP-native (ruled)",
            _derivation={"kind": "fascia_rake", "total_lf": fr["total_lf"]})

    # ── 540 wrap: DOOR TRIM 3-SIDE RULED (head + legs; windows 4-side).
    # Howard's Iter 57ee per-opening constants adjusted: entry 21−3' sill
    # = 18, patio 25−6' sill = 19; garage 32 HELD (16 + 2×8 is already
    # 3-side by inspection — flagged for confirmation, never silently cut)
    wc = int(measurements.get("window_count") or 0)
    ec = int(measurements.get("entry_door_count") or 0)
    pc = int(measurements.get("patio_door_count") or 0)
    gc = int(measurements.get("garage_door_count") or 0)
    if wc + ec + pc + gc > 0:
        from lp_smartside_formulas import shake_540_series_bump
        wrap_lf = wc * 14 + ec * 18 + pc * 19 + gc * 32
        bump = shake_540_series_bump(
            float((measurements.get("_per_profile_sqft") or {}).get("shake") or 0))
        wrap_qty = max(1, math.ceil(wrap_lf / 16.0)) + bump
        note = (f"windows 4-side ({wc}×14') + doors 3-SIDE head+legs (ruled): entry {ec}×18' "
                f"(21−3 sill), patio {pc}×19' (25−6 sill) = {wrap_lf} LF ÷ 16"
                + (f" + {bump} shake belly-band pcs" if bump else ""))
        if gc:
            note += f"; garage {gc}×32' held (16+2×8 already reads 3-side — confirm)"
        _set_line(WRAP_TRIM_ITEM, "LP SmartSide Trim", wrap_qty, note)

    # ── LP STARTER (rip yield RULED FINAL): 3 strips per 16' board =
    # 48 LF/board; pieces = ceil(starter LF ÷ 48), line-itemed as starter
    # stock (ripped) carrying the 38 Series 8" lap source SKU
    try:
        starter_lf = float(measurements.get("starter_lf") or 0)
    except (TypeError, ValueError):
        starter_lf = 0.0
    if starter_lf > 0:
        rip_pcs = int(math.ceil(starter_lf / 48.0 - 1e-9))
        lines.append({"tab": "lp_smart", "section": "LP Siding Accessories",
                      "name": STARTER_LINE_NAME, "unit": "LF",
                      "qty": int(math.ceil(starter_lf)), "pieces_added": rip_pcs,
                      "non_sku": True, "source_sku": LAP8_ITEM,
                      "note": (f"start-course {starter_lf:g} LF — starter stock ripped from "
                               f"38 Series 8\" lap (3 strips per 16' board = 48 LF/board): "
                               f"pieces = ceil({starter_lf:g} ÷ 48) = {rip_pcs}"),
                      "_derivation": {"kind": "starter", "starter_lf": starter_lf}})

    # ── MATERIAL-LIST SUBSTITUTION (ruled): re-derive, provenance, table-limited
    sub_errors = []
    if substitutions:
        table = _lp_product_table()
        for old_name, new_name in substitutions.items():
            target = next((l for l in lines if l["name"] == old_name), None)
            if target is None or not target.get("_derivation"):
                sub_errors.append(f"{old_name}: not a derived line — substitution refused")
                continue
            d = target["_derivation"]
            if d["kind"] in ("osc", "osc_lf"):
                allowed = table["osc"]
            elif d["kind"] in ("isc", "fascia_rake"):
                allowed = table["trim"]
            elif d["kind"] == "starter":
                allowed = ["dedicated-rip"]
            else:
                allowed = []
            if new_name not in allowed:
                sub_errors.append(
                    f"{old_name} → {new_name}: not in the known LP product table — refused (no free-text SKUs)")
                continue
            if d["kind"] == "starter":
                pcs = int(math.ceil(d["starter_lf"] / SIDING_BOARD_LEN_FT - 1e-9))
                target["pieces_added"] = pcs
                target["note"] = (f"SUBSTITUTED: dedicated-rip approach — re-derived pieces = "
                                  f"ceil({d['starter_lf']:g} LF ÷ {SIDING_BOARD_LEN_FT:g}') = {pcs}")
                target["substituted_from"] = "field-ripped from siding stock"
                continue
            stick = _stick_len_ft(new_name)
            if d["kind"] in ("osc", "isc"):
                qty = corner_sticks_for_length(d["heights"], stick)
                how = f"whole sticks per location at {stick:g}' = {qty}"
            elif d["kind"] == "osc_lf":
                qty = max(1, int(math.ceil(d["lf"] / stick - 1e-9)))
                how = f"{d['lf']:g} LF ÷ {stick:g}' = {qty}"
            else:  # fascia_rake
                qty = int(math.ceil(d["total_lf"] * 1.10 / stick - 1e-9))
                how = f"{d['total_lf']:g} LF × 1.10 ÷ {stick:g}' = {qty}"
            target["substituted_from"] = target["name"]
            target["name"] = new_name
            target["qty"] = qty
            target["note"] = f"SUBSTITUTED from {target['substituted_from']} — RE-DERIVED from stored geometry: {how}"

    pending = [PENDING_CONFIRMATIONS["expertfinish_availability_matrix"],
               PENDING_CONFIRMATIONS["bluelinx_sku_upload"]]

    # ── COLOR ARCHITECTURE (ruled): per-component line-level colors;
    # identity = (name, color); availability flagged while unverified
    from lp_colors import apply_colors, consolidate_lines
    group_colors, color_errors = apply_colors(lines, colors)
    lines = consolidate_lines(lines)

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
            "system_table_enforced": system_enforced,
            "substitution_errors": sub_errors,
            "group_colors": group_colors,
            "color_errors": color_errors,
            "flags": flags,
            "pending_confirmations": pending,
        },
    }
