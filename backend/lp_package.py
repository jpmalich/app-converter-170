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
    """RULED: whole sticks PER LOCATION; stick-length changes recompute
    piece counts (10.44' corner: 1×16' vs 2×10'), never a stale reprice."""
    sticks = 0
    for h in heights:
        sticks += max(1, int(math.ceil(float(h) / stick_len_ft - 1e-9))) if h and h > 0 else 1
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
        f"({t['total_lf']} LF; 16' stick length pending confirmation)"
    ]
    flags = [PENDING_CONFIRMATIONS["osc_stick_length"]]
    if t["over_stick"]:
        note_bits.append("corner run(s) over stick length — splice rule pending, ceil-per-location held")
        flags.append(PENDING_CONFIRMATIONS["corner_splice_rule"])
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
        note_bits.append("run(s) over stick length — splice rule pending")
        flags.append(PENDING_CONFIRMATIONS["corner_splice_rule"])
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

    # ── 540 wrap: door side-count pending — flag, do not change derivation
    for l in lines:
        if l["name"] == WRAP_TRIM_ITEM:
            l["note"] = f"{l.get('note') or ''} — door trim 3-side vs 4-side pending (4-side derivation held)".strip(" —")

    # ── LP STARTER (ruled): non-SKU informational line, ALWAYS present
    try:
        starter_lf = float(measurements.get("starter_lf") or 0)
    except (TypeError, ValueError):
        starter_lf = 0.0
    if starter_lf > 0:
        note = (f"start-course {starter_lf:g} LF — material: field-ripped from siding stock "
                "(top-run offcuts / cut pieces); pieces added: 0 (rip-from-waste)")
        thin_margin = bool(lap_math and (lap_math["ordered_pcs"] - lap_math["waste_qty"]) < 0.5)
        if thin_margin:
            note += (f" — THIN WASTE MARGIN on siding (cushion "
                     f"{round(lap_math['ordered_pcs'] - lap_math['waste_qty'], 2)} pc): "
                     "starter rips may consume the cushion")
            flags.append("thin siding waste margin — starter rips may consume the cushion")
        lines.append({"tab": "lp_smart", "section": "LP Siding Accessories",
                      "name": STARTER_LINE_NAME, "unit": "LF",
                      "qty": int(math.ceil(starter_lf)), "pieces_added": 0,
                      "non_sku": True, "note": note,
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

    pending = [PENDING_CONFIRMATIONS["osc_stick_length"],
               PENDING_CONFIRMATIONS["door_trim_sides"]]
    if osc and any("splice" in f.lower() for f in osc.get("flags") or []):
        pending.append(PENDING_CONFIRMATIONS["corner_splice_rule"])

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
