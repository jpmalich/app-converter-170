"""PRICE AGE — EVERY PRICE WRITE RECORDS WHO AND WHEN (Howard ruled
2026-07-31). A stale price is the one defect that reaches a homeowner;
RainDrop and House Wrap sat stale with nothing in the app saying so.

RULES:
  · every HUMAN price write on every surface stamps price_changed_at +
    price_changed_by on the finest grain the surface has (per item on the
    tier editors and bulk panel; per doc on ISS/Vero/Mezzo/LP margins)
  · seed re-syncs NEVER stamp (they are not price decisions) and must
    preserve existing stamps
  · a surface that can change a price without stamping FAILS the suite —
    test_price_write_stamps_2026_07_31.py scans every route that writes a
    price collection against this register.
"""
from datetime import datetime, timezone

PRICE_STALE_DEFAULT_DAYS = 90

# Every surface that can change a price. Route-scan test enforces
# membership + stamping. Format: "file::function" → what it is.
PRICE_WRITE_SURFACES = {
    "routes/catalog.py::admin_update_tier":
        "four contractor tier editors (single-cell + row edits)",
    "routes/pricing_admin.py::_apply_changes":
        "bulk pricing panel — quick bump + CSV upload",
    "routes/iss_pricing_admin.py::_apply_changes":
        "ISS CSV flow",
    "routes/vero.py::admin_update_vero_prices":
        "Vero matrix editor",
    "routes/mezzo.py::admin_update_mezzo_prices":
        "Mezzo matrix editor",
    "routes/lp_admin.py::put_lp_margin_tiers":
        "LP margin ladder (35/30/25/20)",
}

# Collections that hold prices. Any routes/*.py write to these is a
# price-write surface and must be registered above.
PRICE_COLLECTIONS = ("price_tiers", "vero_prices", "mezzo_prices",
                     "iss_catalog")


def price_stamp(who: str = "supplier-admin") -> dict:
    return {
        "price_changed_at": datetime.now(timezone.utc).isoformat(),
        "price_changed_by": who,
    }


def stamp_price_change(obj: dict, who: str = "supplier-admin") -> None:
    obj.update(price_stamp(who))


# ═══ TRANSPOSITION GATE (Howard ruled 2026-07-31) ═══════════════════════
# His uploaded price page landed House Wrap and RainDrop CROSSED and
# nothing but his own sanity check caught it. THE RULE: a price write
# that moves past the threshold without an explicit confirm FAILS.
# A ×3 move is either a real market swing he confirms in one click, or a
# transposition he catches before it saves. Either way he SEES it.
MAGNITUDE_THRESHOLD = 3.0


def magnitude_flag(old, new) -> bool:
    """True when a price write moves past the ×3 threshold, up or down."""
    old = float(old or 0)
    new = float(new or 0)
    if old <= 0:
        return False  # first price on an unpriced row has no basis to gate
    if new <= 0:
        return True  # zeroing a live price is a −100% move — confirm it
    r = new / old
    return r >= MAGNITUDE_THRESHOLD or r <= 1.0 / MAGNITUDE_THRESHOLD


def magnitude_pct(old, new):
    old = float(old or 0)
    new = float(new or 0)
    if old <= 0:
        return None
    return round((new - old) / old * 100.0, 1)


def annotate_magnitude(changes: list) -> list:
    """Stamp pct + magnitude_flag on preview changes so the diff table
    can print 'House Wrap $11.55 → $336.13 (+2810%)' in red."""
    for c in changes:
        c["pct"] = magnitude_pct(c.get("old"), c.get("new"))
        c["magnitude_flag"] = magnitude_flag(c.get("old"), c.get("new"))
    return changes


def detect_transpositions(changes: list) -> list:
    """CROSSED-PAIR DETECTOR (Howard ruled 2026-07-31): the shape that got
    him — two rows landed with each other's dollars. Signature: among the
    magnitude-FLAGGED rows of one preview (same tier + field), a pair
    whose price ORDER inverted (A was cheaper than B, now A is dearer).
    His case: HW $11.55 < RD $30.73 old, but as-entered HW $336.13 >
    RD $119.11 — inverted. A uniform bump preserves order → no pair.
    Runs only on flagged rows, so clean uploads pay nothing."""
    from collections import defaultdict
    groups = defaultdict(list)
    for c in changes:
        if c.get("magnitude_flag") and float(c.get("old") or 0) > 0:
            groups[(c.get("tier_name"), c.get("field"))].append(c)
    pairs = []
    for (tier, field), rows in groups.items():
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                if (float(a["old"]) - float(b["old"])) * (float(a["new"]) - float(b["new"])) < 0:
                    pairs.append({
                        "tier_name": tier, "field": field,
                        "a": {"name": a["name"], "old": a["old"], "new": a["new"]},
                        "b": {"name": b["name"], "old": b["old"], "new": b["new"]},
                    })
    return pairs

