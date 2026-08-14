"""RULING J/K/L PLUMBING — status is a property of the quantity
(Howard ruled 2026-08-14 send-16). Built ONCE so the five silent siblings
become impossible by construction rather than corrected by hand.

STANDING PRINCIPLE (send-16, sealed): Money is derived from the material
quantities. Measure → honest material list (every quantity carries its
real status) → populate line items → derive money from those quantities.
No special money-line logic, averages, or silent zeros. If a quantity is
NOT DERIVABLE, the money that depends on it must reflect that.

STRUCTURAL FINDING (the report Ruling J asked for BEFORE building): status
CANNOT ride the existing structures as-is — derived quantities are raw
floats living in JSON/Mongo-serialised dicts, and status today is a
side-channel (`faces_not_derivable`, line `note` strings). A lightweight
WRAPPER is required. The true 'only-obtainable' shape (a caller physically
cannot reach a raw float) is NOT reachable without breaking serialisation
and dozens of readers; the reachable shape is this `Quantity` value used at
the derivation boundary plus a `status` key carried on each line dict, with
propagation enforced here so no reader can combine inputs and drop status.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DERIVED = "DERIVED"
PARTIAL = "PARTIAL"
NOT_DERIVABLE = "NOT_DERIVABLE"

# Worst-wins order: any NOT_DERIVABLE input poisons the result; any PARTIAL
# input caps it at PARTIAL; only all-DERIVED stays DERIVED.
_RANK = {DERIVED: 0, PARTIAL: 1, NOT_DERIVABLE: 2}
_BY_RANK = {v: k for k, v in _RANK.items()}


@dataclass(frozen=True)
class Quantity:
    """A derived quantity that CANNOT exist without a status (Ruling J).
    Construct via derived()/partial()/not_derivable() — the bare
    constructor rejects an unknown status so a value can never be a
    'DERIVED by default' quantity."""
    value: float | None
    status: str
    reason: str = ""
    excluded: tuple = field(default_factory=tuple)

    def __post_init__(self):
        if self.status not in _RANK:
            raise ValueError(
                f"Quantity constructed without a valid status: {self.status!r} "
                "(Ruling J: a quantity cannot exist without a status).")
        if self.status == NOT_DERIVABLE and self.value is not None:
            # NOT DERIVABLE never carries a number — that is the silent zero
            # wearing a flag (Ruling K).
            object.__setattr__(self, "value", None)

    @property
    def derivable(self) -> bool:
        return self.status != NOT_DERIVABLE


def derived(value: float, reason: str = "") -> Quantity:
    return Quantity(float(value), DERIVED, reason)


def partial(value: float, excluded, reason: str = "") -> Quantity:
    ex = tuple(excluded) if not isinstance(excluded, str) else (excluded,)
    return Quantity(float(value), PARTIAL, reason or "disclosed subset", ex)


def not_derivable(reason: str, dead_input: str = "") -> Quantity:
    r = reason if not dead_input else f"{reason} — dead input: {dead_input}"
    return Quantity(None, NOT_DERIVABLE, r,
                    (dead_input,) if dead_input else ())


def propagate(inputs, value=None, reason: str = "") -> Quantity:
    """Combine input Quantities' STATUSES onto a computed value (Ruling J
    propagation). Worst status wins: any NOT_DERIVABLE input ⇒ the result
    is NOT_DERIVABLE (value dropped, dead inputs named); any PARTIAL input
    ⇒ at best PARTIAL. This is what makes the five siblings impossible
    rather than individually corrected."""
    inputs = [q for q in inputs if isinstance(q, Quantity)]
    worst = max((_RANK[q.status] for q in inputs), default=0)
    status = _BY_RANK[worst]
    if status == NOT_DERIVABLE:
        dead = [d for q in inputs if q.status == NOT_DERIVABLE
                for d in (q.excluded or (q.reason,))]
        return Quantity(None, NOT_DERIVABLE,
                        reason or "input not derivable", tuple(dead))
    if status == PARTIAL:
        ex = tuple(d for q in inputs if q.status == PARTIAL for d in q.excluded)
        return Quantity(value, PARTIAL, reason or "disclosed subset", ex)
    return Quantity(value, DERIVED, reason)


# ---- Ruling K: a NOT DERIVABLE line ----------------------------------

def render_line(qty: Quantity) -> dict:
    """How a line item renders from its quantity's status (Ruling K):
    NOT DERIVABLE ⇒ quantity column NAMES the dead input, price column is
    EMPTY (not $0), and the line BLOCKS the quote gate. PARTIAL renders the
    subset value and names what is out. DERIVED renders normally."""
    if qty.status == NOT_DERIVABLE:
        dead = ", ".join(str(x) for x in qty.excluded if x) or qty.reason
        return {"quantity_text": f"NOT DERIVABLE ({dead})",
                "value": None, "price": None,   # EMPTY, never 0
                "status": NOT_DERIVABLE, "blocks_gate": True}
    if qty.status == PARTIAL:
        out = ", ".join(str(x) for x in qty.excluded if x)
        return {"quantity_text": f"{qty.value} (PARTIAL — excludes {out})",
                "value": qty.value, "price": None, "status": PARTIAL,
                "blocks_gate": False}
    return {"quantity_text": str(qty.value), "value": qty.value,
            "price": None, "status": DERIVED, "blocks_gate": False}


# ---- Ruling L: an incomplete total is not a price --------------------

def rollup_total(line_qtys) -> dict:
    """A total that sums over a NOT DERIVABLE line is INCOMPLETE, states how
    many lines are refused, and is NEVER presented as a price (Ruling L).
    A PARTIAL input caps the total at PARTIAL."""
    qtys = [q for q in line_qtys if isinstance(q, Quantity)]
    refused = [q for q in qtys if q.status == NOT_DERIVABLE]
    partials = [q for q in qtys if q.status == PARTIAL]
    if refused:
        return {"status": NOT_DERIVABLE, "incomplete": True,
                "refused_count": len(refused), "is_price": False,
                "value": None,
                "label": f"INCOMPLETE — {len(refused)} line(s) refused"}
    total = sum(float(q.value or 0) for q in qtys)
    if partials:
        return {"status": PARTIAL, "incomplete": True, "refused_count": 0,
                "is_price": False, "value": total,
                "label": f"PARTIAL — {len(partials)} line(s) a subset"}
    return {"status": DERIVED, "incomplete": False, "refused_count": 0,
            "is_price": True, "value": total, "label": "TOTAL"}
