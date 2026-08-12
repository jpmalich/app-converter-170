"""GABLE ATTRIBUTION — Howard's send-6 seam guard (2026-08-11).

CONTEXT (send-3 → send-6 evolution):

Send-3 (4-vs-2 fix): the mechanism report named a narrow class — a
front-facing wing gable READ AT THE PLANE LEVEL and LOST AT WALL
ATTRIBUTION. The first fix distributed the wing's ends across walls
PERPENDICULAR to the primary gable axis (L+R primary → F+B secondary).
It landed the Boni census; it also silently distributed EVERY non-main
plane's ends across the perpendicular pair — heuristic, not evidence.

Send-6 (Howard's ruling): "AN ORPHAN GABLE END IS NEVER DISTRIBUTED ONTO
AN UNRELATED [wall]. It FLAGS and stays unattributed, loud, on the card
and on the sheet." The perpendicular-axis heuristic is retired. Attribution
now needs EXPLICIT EVIDENCE: each plane with gable_ends > 0 lists
`gable_end_faces` (one entry per end naming the elevation face the
triangle points at). No faces → no attribution → the ends go into the
`orphans` list and the census flag names them loudly.

Twin rulings, both required:
  1. THE READ FIX (prompt-side) — extraction emits one plane per gable
     end it counts; every plane with gable_ends > 0 emits
     `gable_end_faces` of matching length.
  2. THE SEAM GUARD (this module) — an orphan gable end is never
     distributed onto an unrelated wall; unmatched ends flag.

PURITY (Howard, permanent): evidence for rulings, never constants or
targets. Nothing in this module tunes toward 4 or 2 or any known number.
"""
from __future__ import annotations

from typing import Any


_PRIMARY = ("front", "back", "left", "right")


def _f(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _face(x: Any) -> str:
    return str(x or "").strip().lower()


def attribute_secondary_gables(walls: list[dict],
                               planes: list[dict]) -> dict:
    """Attribute non-main plane gable ends to walls using the plane's
    own `gable_end_faces` evidence. No evidence → orphan → flag.

    Returns
    -------
    {
      "plane_gables_total": int,     # Σ gable_ends across planes
      "wall_gables_primary": int,    # walls carrying gable_triangle_height_ft > 0
      "unattributed_before": int,    # plane_gables_total − wall_gables_primary
      "attributions": [
          {"wall": "front", "plane": "entry", "kind": "secondary",
           "count": 1},
          ...
      ],
      "orphans": [
          {"plane": "garage/bonus", "count": 2,
           "reason": "no gable_end_faces on plane"},
          ...
      ],
      "wall_gables_attributed": int,  # primary + attributed count
      "census_reconciled": bool,
      "reason": str | None,           # populated when attribution refuses
    }
    """
    plane_gables_total = sum(int(p.get("gable_ends") or 0)
                             for p in (planes or []))
    primary_walls = [
        _face(w.get("label"))
        for w in (walls or [])
        if _f(w.get("gable_triangle_height_ft")) > 0
    ]
    wall_gables_primary = sum(
        1 for lbl in primary_walls if lbl in _PRIMARY)

    unattributed = plane_gables_total - wall_gables_primary
    result: dict = {
        "plane_gables_total": plane_gables_total,
        "wall_gables_primary": wall_gables_primary,
        "unattributed_before": max(unattributed, 0),
        "attributions": [],
        "orphans": [],
        "wall_gables_attributed": wall_gables_primary,
        "census_reconciled": plane_gables_total == wall_gables_primary,
        "reason": None,
    }
    if unattributed <= 0:
        return result

    reasons: list[str] = []
    # Walk non-main non-porch planes carrying gable ends. Only planes
    # with an explicit `gable_end_faces` list of matching length are
    # attributed. Everything else is an ORPHAN.
    for p in (planes or []):
        if p.get("is_porch"):
            continue
        ends = int(p.get("gable_ends") or 0)
        if ends <= 0:
            continue
        lbl_raw = str(p.get("label") or "").lower()
        if lbl_raw == "main":
            continue

        faces_raw = p.get("gable_end_faces")
        if not isinstance(faces_raw, list) or len(faces_raw) != ends:
            # No evidence, or evidence disagrees with the count →
            # every end on this plane is an orphan. NEVER distribute
            # onto an unrelated wall (Howard's seam guard).
            result["orphans"].append({
                "plane": p.get("label") or "?",
                "count": ends,
                "reason": (
                    "no gable_end_faces on plane"
                    if not isinstance(faces_raw, list)
                    else (
                        f"gable_end_faces length {len(faces_raw)} != "
                        f"gable_ends {ends}")
                ),
            })
            continue

        # Evidence provided — attribute one end per named face.
        placed = 0
        for face in faces_raw:
            f = _face(face)
            if f not in _PRIMARY:
                # A face named but not in the four-wall universe (a
                # verbatim plan label the app cannot bind to a wall) is
                # STILL an orphan — flag rather than silently swallow.
                result["orphans"].append({
                    "plane": p.get("label") or "?",
                    "count": 1,
                    "reason": f"gable_end_face {face!r} is not a "
                              "front/back/left/right wall",
                })
                continue
            result["attributions"].append({
                "wall": f,
                "plane": p.get("label") or "?",
                "kind": "secondary",
                "count": 1,
            })
            placed += 1
        if placed == 0 and ends > 0:
            reasons.append(
                f"plane {p.get('label')!r} carried {ends} end(s) with "
                "no attributable face — flagged as orphan")

    attributed_count = sum(a["count"] for a in result["attributions"])
    orphan_count = sum(o["count"] for o in result["orphans"])
    result["wall_gables_attributed"] = wall_gables_primary + attributed_count
    result["census_reconciled"] = (
        result["wall_gables_attributed"] == plane_gables_total
        and orphan_count == 0)
    if not result["census_reconciled"]:
        if orphan_count > 0:
            result["reason"] = (
                f"orphan gable end(s): {orphan_count} unattributed — "
                "no gable_end_faces evidence on the read")
        else:
            result["reason"] = (
                "attribution partial: "
                f"{result['wall_gables_attributed']} of "
                f"{plane_gables_total} plane gables land on walls")
    return result


def secondary_gables_for_wall(attribution: dict,
                              wall_label: str) -> list[dict]:
    """Return the list of secondary-gable attributions on this wall.
    Empty when the wall carries none."""
    wall_lbl = _face(wall_label)
    return [
        a for a in (attribution or {}).get("attributions", [])
        if _face(a.get("wall")) == wall_lbl
    ]


def orphan_gables(attribution: dict) -> list[dict]:
    """Return orphan gable entries (never on any wall). The sheet
    renderer surfaces these as a loud NEEDS YOUR TAPE band; the census
    flag names them on the readback card."""
    return list((attribution or {}).get("orphans") or [])
