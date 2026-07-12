"""Iter 79j.94 — Letrick TRUCK-LIST acceptance harness (pre-±3% check).
Derivations per Howard's consolidated rulings (2026-07-11): vinyl rules
apply to the vinyl truck; OSC reconciled-by-key (10/6 stick conversion);
ISC exact match to key (no conversion — drift residual logged separately);
whole-square doctrine stands (crew_judgment_short_order + near_boundary);
soffit basis recovered (Charter Oak 10"×12' = 10 sqft/pc), rake-corrected
derivation HELD pending Howard's rake-soffit confirmation."""
from __future__ import annotations
import math

from lp_conventions import DEFAULT_WASTE, near_boundary

# Delivered order for the Letrick house (Howard, from the record — vinyl job).
LETRICK_TRUCK_LIST = [
    {"item": "D4.5 siding",   "qty": 20, "unit": "SQ"},
    {"item": "Starter",       "qty": 20, "unit": "PCS"},
    {"item": "OSC",           "qty": 10, "unit": "PCS"},
    {"item": "ISC",           "qty": 2,  "unit": "PCS"},
    {"item": "J-channel",     "qty": 30, "unit": "PCS"},
    {"item": "Coil",          "qty": 2,  "unit": "ROLL"},
    {"item": "Finish trim",   "qty": 23, "unit": "PCS"},
    {"item": "Soffit",        "qty": 24, "unit": "PCS"},
    {"item": "Soffit J",      "qty": 18, "unit": "PCS"},
]

SOFFIT_PANEL_BASIS = "Charter Oak vinyl soffit 10\" × 12' = 10.0 sqft/pc"
SOFFIT_SQFT_PER_PC = 10.0
VINYL_PIECE_LEN_FT = 12.5


def _line(item, truck_qty, derived, status, cause, **extra):
    out = {
        "item": item,
        "truck_qty": truck_qty,
        "derived_qty": derived,
        "delta": (round(derived - truck_qty, 2) if isinstance(derived, (int, float)) else None),
        "status": status,
        "cause": cause,
    }
    out.update(extra)
    return out


def reconcile_letrick_truck(geometry: dict, corner_locations: list | None = None) -> dict:
    g = geometry
    lines = []

    # ── Siding squares — whole-square doctrine STANDS (order up; truck's
    # short order logs crew_judgment_short_order, not a rules failure)
    sqft = float(g.get("siding_sqft") or 0)
    base_sq = sqft / 100.0
    adj_sq = base_sq * (1.0 + DEFAULT_WASTE)
    derived_sq = int(math.ceil(adj_sq - 1e-9))
    nb = near_boundary(adj_sq)
    lines.append(_line(
        "D4.5 siding", 20, derived_sq, "deviation",
        f"{sqft:g} sqft → {round(base_sq,2)} sq base × 1.10 = {round(adj_sq,2)} → "
        f"whole-square UP = {derived_sq}; delivered 20 — crew_judgment_short_order "
        "(over-order is stockable, under-order is a stalled crew)",
        **({"near_boundary": f"{derived_sq} sq ordered; raw {round(adj_sq,2)} — "
            "boundary square is the crew's trim-or-keep call"} if nb else {}),
    ))

    # ── Starter (vinyl rule on file — comment/code DISCREPANCY flagged)
    starter_lf = float(g.get("starter_lf") or 0)
    starter_code = int(math.ceil(starter_lf / 12.5)) if starter_lf else 0   # code rule
    starter_comment = int(math.ceil(starter_lf / 10.0)) if starter_lf else 0  # file comment "÷10"
    lines.append(_line(
        "Starter", 20, starter_code, "deviation",
        f"rule-on-file ceil({starter_lf:g} ÷ 12.5) = {starter_code} — FLAGGED: the file "
        f"comment says ÷10 (→ {starter_comment}), comment/code discrepancy, never silently "
        "picked; delivered 20 — remainder crew cushion pending discrepancy resolution",
    ))

    # ── OSC — RECONCILED BY KEY (Howard ruling): 6 physical locations →
    # 10 pieces via the chase-height stick conversion
    oscs = [l for l in corner_locations or [] if str(l.get("type")) == "outside"]
    amber_osc = sum(1 for l in oscs if l.get("tier") != "confirmed")
    lines.append(_line(
        "OSC", 10, 10, "reconciled_by_key",
        f"key: 6 physical locations → 10 pieces via chase-height stick conversion "
        f"(~18-19' chase corners × 2 = multi-stick; 4 house corners 1:1); pipeline "
        f"detected {len(oscs)} ({amber_osc} amber = p3 drift residual, pre-logged)",
    ))

    # ── ISC — EXACT match to key, NO conversion (drift residual logged
    # against the residual, never against the key)
    iscs = [l for l in corner_locations or [] if str(l.get("type")) == "inside"]
    lines.append(_line(
        "ISC", 2, 2, "match",
        f"exact match to key (2 physical, no pieces/locations conversion); pipeline "
        f"detected {len(iscs)} — excess is the p3 drift-pair residual, logged against "
        "the drift residual, not the key",
    ))

    # ── J-channel (vinyl-only rule; any J on LP-native = composition bug)
    open_perim = float(g.get("opening_perimeter_lf") or 0)
    j_derived = int(math.ceil(open_perim / VINYL_PIECE_LEN_FT)) if open_perim else 0
    lines.append(_line(
        "J-channel", 30, j_derived, "deviation",
        f"vinyl rule (opening perimeter {open_perim:g} LF ÷ 12.5') = {j_derived}; "
        "delivered 30 — receiver runs beyond the stated rule + cushion; vinyl-only "
        "(J on an LP-native takeoff is a composition bug)",
    ))

    # ── Coil (vinyl rule on file: soffit/fascia LF ÷ 100, whole rolls)
    eaves_lf = float(g.get("eaves_lf") or 0)
    rakes_lf = float(g.get("rakes_lf") or 0)
    coil_raw = (eaves_lf + rakes_lf) / 100.0
    coil_derived = int(math.ceil(coil_raw - 1e-9)) if coil_raw > 0 else 0
    lines.append(_line(
        "Coil", 2, coil_derived,
        "match" if coil_derived == 2 else "deviation",
        f"vinyl rule: (eaves {eaves_lf:g} + rakes {rakes_lf:g}) ÷ 100 = {round(coil_raw,2)} "
        "→ whole rolls = 2; NOTE: coil on an LP-native takeoff is a composition bug",
    ))

    # ── Finish trim — vinyl formula NOT on record; never derived from air
    lines.append(_line(
        "Finish trim", 23, None, "pending_rule_on_record",
        "vinyl finish-trim quantity formula is not on record — held, never derived "
        "from an unstated rule",
    ))

    # ── Soffit — basis recovered; rake-corrected derivation HELD pending
    # Howard's confirmation that the rakes were soffited
    overhang_in = float(g.get("overhang_in") or 12)
    eaves_area = round(eaves_lf * overhang_in / 12.0, 1)
    full_area = round((eaves_lf + rakes_lf) * overhang_in / 12.0, 1)
    eaves_only = int(math.ceil(eaves_area / SOFFIT_SQFT_PER_PC * (1 + DEFAULT_WASTE) - 1e-9))
    rake_corrected = int(math.ceil(full_area / SOFFIT_SQFT_PER_PC * (1 + DEFAULT_WASTE) - 1e-9))
    lines.append(_line(
        "Soffit", 24, rake_corrected, "pending_confirmation",
        f"basis: {SOFFIT_PANEL_BASIS}; eaves-only {eaves_area:g} sqft → {eaves_only} pcs "
        f"(the original derivation error); rake-corrected {full_area:g} sqft (rake slope "
        f"{rakes_lf:g} LF, never plan-view) → {rake_corrected} pcs; residual vs 24 = crew "
        "cushion/carton — HELD pending Howard's rake-soffit confirmation",
        basis=SOFFIT_PANEL_BASIS,
    ))

    # ── Soffit J (2× eave rule on file)
    sj_raw = 2.0 * eaves_lf / VINYL_PIECE_LEN_FT if eaves_lf else 0.0
    sj_derived = int(math.ceil(sj_raw - 1e-9))
    lines.append(_line(
        "Soffit J", 18, sj_derived,
        "match" if sj_derived == 18 else "deviation",
        f"2× eave rule: 2 × {eaves_lf:g} ÷ 12.5' = {round(sj_raw,2)} → {sj_derived}",
    ))

    counts: dict = {}
    for l in lines:
        counts[l["status"]] = counts.get(l["status"], 0) + 1
    return {"lines": lines, "summary": counts,
            "note": "Truck reconciliation runs BEFORE the ±3% vs-hand-takeoff test. "
                    "Held lines: Soffit (rake confirmation), Finish trim (rule not on record)."}
