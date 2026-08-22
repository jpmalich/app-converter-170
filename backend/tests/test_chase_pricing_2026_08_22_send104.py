"""SEND-104 (still-owed, authorized) — CHASE PRICING register: a clean
chase row prices at the HOST siding line's own rates, source named on
the row. A contested chase still refuses (Ruling L untouched). No host
line → the row stays unpriced with the reason printed; rates are never
invented."""
import sys

sys.path.insert(0, "/app/backend")
from routes.pdf_overlay import apply_overlay_to_takeoff


def _host(mat=151.31, lab=0.0):
    return {"name": "Charter Oak Standard color Dutch Lap 4.5\" .046",
            "unit": "SQ", "qty": 11.77, "raw_qty": 11.77,
            "mat": mat, "lab": lab, "tab": "vinyl",
            "section": "Vinyl Siding"}


def _chase(**kw):
    z = {"id": "z1", "face_id": "chase:back", "provenance": "human",
         "material_class": "siding", "sqft": 107.3,
         "basis": "chimney chase — its own bindable surface"}
    z.update(kw)
    return z


def test_clean_chase_prices_at_host_rates_source_named():
    out = apply_overlay_to_takeoff([_host(mat=151.31, lab=42.5)],
                                   [_chase()])
    row = next(ln for ln in out if ln.get("overlay_chase_line"))
    assert row["qty"] == 1.07
    assert row["mat"] == 151.31 and row["lab"] == 42.5
    assert "priced at the host siding line's rates" in row["note"]
    assert "Charter Oak" in row["note"]
    assert "sided in the face's own material" in row["note"]
    assert row["note"].startswith("Basis:")


def test_no_host_line_stays_unpriced_reason_printed():
    out = apply_overlay_to_takeoff([], [_chase()])
    row = next(ln for ln in out if ln.get("overlay_chase_line"))
    assert row["qty"] == 1.07
    assert row["mat"] == 0 and row["lab"] == 0
    assert "UNPRICED — no host siding line" in row["note"]
    assert "never invented" in row["note"]


def test_contested_chase_still_refuses_never_prices():
    out = apply_overlay_to_takeoff(
        [_host()],
        [_chase(tier="contested_pick_larger",
                basis="this face's scale stays CONTESTED")])
    row = next(ln for ln in out if ln.get("overlay_chase_line"))
    assert row["qty"] is None and row["not_derivable"]
    assert row["mat"] == 0 and row["lab"] == 0
    assert "Ruling L" in row["not_derivable_reason"]
    assert "priced at" not in (row.get("note") or "")


def test_unpriced_host_rates_carry_zero_not_invented():
    out = apply_overlay_to_takeoff([_host(mat=0, lab=0)], [_chase()])
    row = next(ln for ln in out if ln.get("overlay_chase_line"))
    assert row["mat"] == 0 and row["lab"] == 0
    assert "priced at the host siding line's rates" in row["note"]
