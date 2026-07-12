"""Iter 79j.94 — Letrick TRUCK-LIST acceptance harness (Howard's spec:
"the cheaper, harder check", runs BEFORE the ±3% vs-hand-takeoff test).
The delivered truck list is a fixed fixture; the harness derives each
line's expected quantity from the conventions layer + validated Letrick
geometry, itemizing deviations per line WITH CAUSE. Lines that depend on
the PENDING LP trim/accessory conventions are marked pending_confirmation
— never derived from unconfirmed rules."""
from __future__ import annotations
import math

from lp_conventions import DEFAULT_WASTE, line_math

# Delivered LP-native order for the Letrick house (Howard, from the record).
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

# Answer-key note: 10 delivered OSC pieces ↔ 6 corner LOCATIONS.
OSC_PIECES_PER_LOCATION_KEY = (10, 6)


def _line(item, truck_qty, derived, status, cause, math_detail=None):
    out = {
        "item": item,
        "truck_qty": truck_qty,
        "derived_qty": derived,
        "delta": (round(derived - truck_qty, 2) if isinstance(derived, (int, float)) else None),
        "status": status,
        "cause": cause,
    }
    if math_detail:
        out["math"] = math_detail
    return out


def reconcile_letrick_truck(geometry: dict, corner_locations: list | None = None) -> dict:
    """geometry: validated Letrick measurements (siding_sqft, eaves_lf,
    starter_lf, opening_perimeter_lf, overhang_in, ...)."""
    g = geometry
    lines = []

    # ── Siding squares (confirmed rule: waste before whole-piece/whole-square up)
    sqft = float(g.get("siding_sqft") or 0)
    base_sq = sqft / 100.0
    adj_sq = base_sq * (1.0 + DEFAULT_WASTE)
    derived_sq = int(math.ceil(adj_sq - 1e-9))
    lines.append(_line(
        "D4.5 siding", 20, derived_sq,
        "match" if derived_sq == 20 else "deviation",
        f"validated {sqft:g} sqft → {round(base_sq,2)} sq base × 1.10 waste = "
        f"{round(adj_sq,2)} sq → whole-square up = {derived_sq}; delivered 20 "
        f"(≈{round((20/base_sq-1)*100,1)}% effective waste on the truck)",
        {"base_sq": round(base_sq, 2), "waste_sq": round(adj_sq, 2)},
    ))

    # ── OSC (confirmed rule: C3 corner locations; answer-key 10/6 conversion)
    oscs = [l for l in corner_locations or [] if str(l.get("type")) == "outside"]
    confirmed = [l for l in oscs if l.get("tier") == "confirmed"]
    derived_osc = len(oscs)  # one 12.5' vinyl piece per location (heights ≤ 12.5')
    lines.append(_line(
        "OSC", 10, derived_osc, "deviation",
        f"C3: {len(oscs)} OSC locations ({len(confirmed)} confirmed) × 1 piece each "
        f"(all corner heights ≤ 12.5' piece) = {derived_osc}; delivered 10 — answer-key "
        f"notes the {OSC_PIECES_PER_LOCATION_KEY[0]}-pieces/{OSC_PIECES_PER_LOCATION_KEY[1]}-locations "
        "conversion (delivered extras beyond one-piece-per-corner)",
    ))

    # ── ISC (confirmed rule: C3 — presence guarantee carries into the harness)
    iscs = [l for l in corner_locations or [] if str(l.get("type")) == "inside"]
    amber_isc = sum(1 for l in iscs if l.get("tier") != "confirmed")
    derived_isc = len(iscs)
    lines.append(_line(
        "ISC", 2, derived_isc,
        "match" if derived_isc == 2 else "deviation",
        f"C3: {derived_isc} ISC locations × 1 piece each (chase junctions ≤ 12.5')"
        + (f" — includes {amber_isc} amber (drift residual, flagged + provenance-limited); "
           "physical key = 2, field check resolves" if derived_isc != 2 else ""),
    ))

    # ── Soffit (confirmed LP method for comparison; truck unit basis is vinyl)
    eave_lf = float(g.get("eaves_lf") or 0)
    overhang = float(g.get("overhang_in") or 12)
    # vinyl-basis comparison: 12' panel along the fascia at 12" depth ≈ 12 LF/pc
    base_pcs = eave_lf / 12.0 if eave_lf else 0.0
    adj_pcs = base_pcs * (1.0 + DEFAULT_WASTE)
    derived_soffit = int(math.ceil(adj_pcs - 1e-9))
    lines.append(_line(
        "Soffit", 24, derived_soffit, "deviation",
        f"eave-length method on vinyl basis: {eave_lf:g} LF ÷ 12' pieces × 1.10 = "
        f"{round(adj_pcs,2)} → {derived_soffit}; delivered 24 — truck unit basis "
        f"unverifiable from record (may include porch ceilings / {overhang:g}\" depth pieces)",
    ))

    # ── PENDING lines (LP trim/accessory conventions unconfirmed — DO NOT derive)
    starter_lf = float(g.get("starter_lf") or 0)
    lines.append(_line(
        "Starter", 20, None, "pending_confirmation",
        f"starter-by-eave-length rule was logged in the Alside context — carry-over "
        f"unconfirmed (sanity only: {starter_lf:g} start-line LF ÷ 10' pieces = "
        f"{math.ceil(starter_lf/10) if starter_lf else '?'})",
    ))
    open_perim = float(g.get("opening_perimeter_lf") or 0)
    lines.append(_line(
        "J-channel", 30, None, "pending_confirmation",
        f"J by opening+perimeter sums was logged in the Alside context — carry-over "
        f"unconfirmed (openings perimeter on record: {open_perim:g} LF)",
    ))
    lines.append(_line(
        "Coil", 2, None, "pending_confirmation",
        "fascia coil by run length was logged in the Alside context — carry-over "
        "unconfirmed (LP install-system default is 1 roll; delivered 2)",
    ))
    lines.append(_line(
        "Finish trim", 23, None, "pending_confirmation",
        "finish-trim quantity rule was logged in the Alside context — carry-over unconfirmed",
    ))
    lines.append(_line(
        "Soffit J", 18, None, "pending_confirmation",
        "2× eave for soffit F/J-channel was logged in the Alside context — carry-over unconfirmed",
    ))

    counts = {
        "match": sum(1 for l in lines if l["status"] == "match"),
        "deviation": sum(1 for l in lines if l["status"] == "deviation"),
        "pending_confirmation": sum(1 for l in lines if l["status"] == "pending_confirmation"),
    }
    return {"lines": lines, "summary": counts,
            "note": "Truck reconciliation runs BEFORE the ±3% vs-hand-takeoff acceptance "
                    "test. Pending lines await Howard's LP trim/accessory confirmation."}
