"""GABLE ATTRIBUTION — Howard's 4-vs-2 fix (2026-08-11 send-3 item c).

The mechanism report (memory/elevation_mechanisms_2026-08-11.md §2)
named the class narrowly: the front-facing gable is READ AT THE PLANE
LEVEL but LOST AT WALL ATTRIBUTION.
    Main plane        gable_ends = 2 → walls left + right carry primary
    Garage/bonus      gable_ends = 2 → UNATTRIBUTED to any wall
    Porch             gable_ends = 0
    Σ plane_gables = 4        wall_gables = 2        census fires 4-vs-2

Howard's ruling: fix the attribution step, not the read. The wing's ends
face the walls PERPENDICULAR to the walls carrying the primary gables.
When primary is L+R, the wing's ends face F+B; when primary is F+B, the
wing's ends face L+R.

This module owns the attribution as a PURE FUNCTION over (walls, planes):
- Never mutates the raw. The attribution is DERIVED, evidenced by which
  planes carry it, and computed at readback + sheet-render time.
- Never guesses. If the extras cannot be safely distributed to the
  perpendicular axis (odd count, no primary gables, no non-main plane),
  the attribution stays empty and the census flag continues to fire —
  loud, not silenced.
- Never sets gable_triangle_height_ft on the wall. The primary read is
  the primary read; secondary attribution rides in its own key so the
  gable-honest area math (Phase 2) can distinguish.

The renderer (blueprint_elevation.py) reads these attributions to draw
the wing gables in Phase 2. The readback (build_blueprint_readback)
reads them so the census reconciles when attribution is complete.

PURITY (Howard, permanent): evidence for rulings, never constants or
targets. Nothing in this module tunes toward 4 or 2 or any known number.
"""
from __future__ import annotations

from typing import Any


_PRIMARY = ("front", "back", "left", "right")
_PERPENDICULAR = {
    ("front", "back"): ("left", "right"),
    ("left", "right"): ("front", "back"),
}


def _f(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def attribute_secondary_gables(walls: list[dict],
                               planes: list[dict]) -> dict:
    """Attribute plane-read gable ends that no wall carries as a primary
    gable to the wall pair PERPENDICULAR to the primary gable axis.

    Returns
    -------
    {
      "plane_gables_total": int,
      "wall_gables_primary": int,
      "unattributed_before": int,
      "attributions": [
          {"wall": "front", "plane": "garage/bonus", "kind": "secondary",
           "count": 1},
          ...
      ],
      "wall_gables_attributed": int,
      "census_reconciled": bool,
      "reason": str | None,   # populated when attribution refuses
    }
    """
    plane_gables_total = sum(int(p.get("gable_ends") or 0)
                             for p in (planes or []))
    primary_walls = [
        str(w.get("label") or "").lower()
        for w in (walls or [])
        if _f(w.get("gable_triangle_height_ft")) > 0
    ]
    wall_gables_primary = sum(
        1 for lbl in primary_walls if lbl in _PRIMARY)

    unattributed = plane_gables_total - wall_gables_primary
    result = {
        "plane_gables_total": plane_gables_total,
        "wall_gables_primary": wall_gables_primary,
        "unattributed_before": max(unattributed, 0),
        "attributions": [],
        "wall_gables_attributed": wall_gables_primary,
        "census_reconciled": plane_gables_total == wall_gables_primary,
        "reason": None,
    }
    if unattributed <= 0:
        return result

    # Find the primary axis (pair of opposing walls carrying gables).
    primary_axis: tuple[str, str] | None = None
    for pair in _PERPENDICULAR:
        if all(w in primary_walls for w in pair) and wall_gables_primary == 2:
            primary_axis = pair
            break
    if primary_axis is None:
        result["reason"] = (
            f"unattributed={unattributed} but primary gable axis not "
            "identifiable from wall reads — attribution refuses to guess"
        )
        return result

    perpendicular = _PERPENDICULAR[primary_axis]
    # Non-main, non-porch planes carrying gable ends — the candidates
    # whose ridges cross the primary axis.
    candidates = []
    for p in (planes or []):
        if p.get("is_porch"):
            continue
        ends = int(p.get("gable_ends") or 0)
        if ends <= 0:
            continue
        lbl = str(p.get("label") or "").lower()
        if lbl == "main":
            continue
        candidates.append((lbl, ends))

    if not candidates:
        result["reason"] = (
            f"unattributed={unattributed} but no non-main gabled plane "
            "carries the extras — refusing to attribute"
        )
        return result

    # Distribute: for each candidate plane, split its ends across the
    # perpendicular pair. Typical wing (1 gable end each face) → 1 to
    # each of the pair. If a plane carries an odd count, attribute one
    # end each until the count runs out — never over-attribute.
    attributions: list[dict] = []
    remaining = unattributed
    # Walk perpendicular walls in a stable order (front then back / left
    # then right — matches the plane's "ends face F/B" or "ends face L/R"
    # ordering the mechanism report describes).
    for plane_lbl, ends in candidates:
        # Split ends across the pair — one each for the typical 2, or
        # cascade if the plane carries more.
        idx = 0
        while ends > 0 and remaining > 0:
            wall_lbl = perpendicular[idx % 2]
            attributions.append({
                "wall": wall_lbl,
                "plane": plane_lbl,
                "kind": "secondary",
                "count": 1,
            })
            ends -= 1
            remaining -= 1
            idx += 1
        if remaining <= 0:
            break

    attributed_count = sum(a["count"] for a in attributions)
    result["attributions"] = attributions
    result["wall_gables_attributed"] = wall_gables_primary + attributed_count
    result["census_reconciled"] = (
        result["wall_gables_attributed"] == plane_gables_total)
    if not result["census_reconciled"]:
        result["reason"] = (
            "attribution partial: "
            f"{result['wall_gables_attributed']} of "
            f"{plane_gables_total} plane gables land on walls"
        )
    return result


def secondary_gables_for_wall(attribution: dict,
                              wall_label: str) -> list[dict]:
    """Return the list of secondary-gable attributions on this wall.
    Empty when the wall carries none. Purpose: the elevation-sheet
    renderer walks this to know whether a wing gable belongs on the
    sheet (Phase 2 draws it; Phase 1 just carries the annotation)."""
    wall_lbl = str(wall_label or "").lower()
    return [
        a for a in (attribution or {}).get("attributions", [])
        if str(a.get("wall") or "").lower() == wall_lbl
    ]
