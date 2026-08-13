"""SEND-10 ONE-SOURCE-ONE-PATH + OPENINGS-vs-WALL-WIDTH
(Howard ruled 2026-08-12 send-10 items 1 and 2).

Verbatim (item 1): "A single evidence source may not silently populate
two distinct paths. If one quote is consumed by more than one path,
it FLAGS, names both paths, and the second consumer is treated as
UNVERIFIED. Same family as the seam ledger: a value that appears in
two places must account for how it got there."

Verbatim (item 2): "The sum of opening widths on a wall may not exceed
that wall's width. Flag loud when it does. That is a pure arithmetic
consistency check on numbers you already hold, it needs no read, and
it would have caught this on the first card."

The Boni cases that forced both rulings:
  Item 1: walls.left.width_ft AND walls.right.width_ft both fed from
          the SAME 39'-0" quote — one dim applied to two opposing
          walls; the right side was never read independently. The
          box model still alive under every fix.
  Item 2: G1 16'-0" plus G2 9'-0" = 25 ft of garage door placed on
          the FRONT wall's 23'-8 1/2" garage segment. Cannot fit.
          Belongs on the 33'-0" side wall. Simple arithmetic.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _one_source_one_path_guard,
    build_blueprint_readback,
    check_read_consistency,
)


# ---------- (A) ONE-SOURCE-ONE-PATH GUARD ----------

def _mirror_raw():
    """The Boni mirror: both side walls fed from ONE 39'-0" quote."""
    return {
        "walls": [
            {"label": "front", "width_ft": 58.0},
            {"label": "back", "width_ft": 58.0},
            {"label": "left", "width_ft": 39.0},
            {"label": "right", "width_ft": 39.0},
        ],
        "_dim_evidence": {
            "walls.left.width_ft": {
                "v": 39.0, "page": 6, "from": "39'-0\""},
            "walls.right.width_ft": {
                "v": 39.0, "page": 6, "from": "39'-0\""},
        },
    }


def test_shared_quote_demotes_second_consumer_to_unverified():
    raw = _mirror_raw()
    _one_source_one_path_guard(raw)
    # Alphabetical order: "walls.left..." precedes "walls.right...".
    # Left keeps evidence; RIGHT is demoted (nulled + unverified).
    walls = {w["label"]: w for w in raw["walls"]}
    assert walls["left"]["width_ft"] == 39.0
    assert walls["right"]["width_ft"] is None
    unv = raw.get("_dim_unverified") or []
    demoted = next(r for r in unv
                   if r["path"] == "walls.right.width_ft")
    assert demoted["value"] == 39.0
    assert "walls.left.width_ft" in demoted["reason"]
    assert "already consumed" in demoted["reason"]


def test_shared_source_ledger_names_all_consumers():
    raw = _mirror_raw()
    _one_source_one_path_guard(raw)
    shared = raw.get("_dim_shared_source") or []
    r = next(s for s in shared if s["quote"] == "39'-0\"")
    assert set(r["consumers"]) == {"walls.left.width_ft",
                                   "walls.right.width_ft"}
    assert r["kept"] == "walls.left.width_ft"
    assert r["demoted"] == ["walls.right.width_ft"]


def test_singleton_quote_leaves_evidence_alone():
    raw = {
        "walls": [{"label": "front", "width_ft": 58.0}],
        "_dim_evidence": {
            "walls.front.width_ft": {
                "v": 58.0, "page": 6, "from": "58'-0\""},
        },
    }
    _one_source_one_path_guard(raw)
    assert raw["walls"][0]["width_ft"] == 58.0
    assert not raw.get("_dim_unverified")
    assert not raw.get("_dim_shared_source")


def test_different_quotes_do_not_share_source():
    """A number that legitimately prints on multiple pages with
    different `from` strings does NOT trigger the guard — the
    key is (page, from), not just the number."""
    raw = {
        "walls": [
            {"label": "left", "width_ft": 39.0},
            {"label": "right", "width_ft": 39.0},
        ],
        "_dim_evidence": {
            "walls.left.width_ft": {
                "v": 39.0, "page": 6, "from": "39'-0\""},
            "walls.right.width_ft": {
                "v": 39.0, "page": 6, "from": "39'-0 1/2\""},
        },
    }
    _one_source_one_path_guard(raw)
    assert raw["walls"][0]["width_ft"] == 39.0
    assert raw["walls"][1]["width_ft"] == 39.0
    assert not raw.get("_dim_unverified")


def test_shared_source_lands_on_readback_and_rail():
    """The readback carries `dim_shared_source` for the card; the
    rail fires `dims_shared_source` LOUD."""
    raw = _mirror_raw()
    _one_source_one_path_guard(raw)
    rb = build_blueprint_readback(raw)
    assert rb.get("dim_shared_source")
    codes = {r["code"]: r for r in rb["rail"]}
    assert "dims_shared_source" in codes
    assert codes["dims_shared_source"]["level"] == "loud"


# ---------- (B) OPENINGS SUM vs WALL WIDTH ----------

def _boni_garage_case():
    """The Boni case that forced item 2: two garage doors 16'+9' = 25
    ft placed on the FRONT wall (58 ft overall, but the garage
    segment is 23'-8 1/2"; the arithmetic already refuses at the
    wall-total level too — 25 ft > 23.71 ft)."""
    return {
        "walls": [
            {"label": "front", "width_ft": 23.71},   # garage-segment width
            {"label": "back", "width_ft": 58.0},
            {"label": "left", "width_ft": 30.17},
            {"label": "right", "width_ft": 33.0},    # the real garage-door wall
        ],
        "doors": [
            {"mark": "G1", "elevation": "front", "width_in": 192,
             "height_in": 96, "qty": 1, "type_hint": "garage"},
            {"mark": "G2", "elevation": "front", "width_in": 108,
             "height_in": 96, "qty": 1, "type_hint": "garage"},
        ],
        "windows": [],
        "roof_planes": [], "outside_corner_count": 4,
    }


def test_openings_exceed_wall_width_fires_on_boni_garage():
    flags = check_read_consistency(_boni_garage_case())
    codes = [f["code"] for f in flags]
    assert "openings_exceed_wall_width" in codes
    f = next(x for x in flags if x["code"] == "openings_exceed_wall_width")
    assert f["level"] == "loud"
    v = f["vars"]
    assert v["wall"] == "front"
    assert abs(v["openings_sum_ft"] - 25.0) < 0.01
    assert abs(v["excess_ft"] - (25.0 - 23.71)) < 0.01
    assert "G1" in v["openings"] or "192" in v["openings"]


def test_openings_fits_when_placed_on_the_right_wall():
    """When the same two garage doors are correctly attributed to the
    33'-0" side wall, the sum fits and the flag stays silent."""
    raw = _boni_garage_case()
    for d in raw["doors"]:
        d["elevation"] = "right"
    flags = check_read_consistency(raw)
    codes = [f["code"] for f in flags]
    assert "openings_exceed_wall_width" not in codes


def test_openings_check_ignores_walls_without_width():
    """A wall whose width_ft is unread (send-9 unverified — set to
    None on raw) can't be checked. The pin must not trip on a
    missing width."""
    raw = {
        "walls": [{"label": "front", "width_ft": None}],
        "doors": [{"mark": "G1", "elevation": "front", "width_in": 192,
                   "qty": 1}],
        "windows": [],
        "roof_planes": [], "outside_corner_count": 0,
    }
    flags = check_read_consistency(raw)
    codes = [f["code"] for f in flags]
    assert "openings_exceed_wall_width" not in codes


def test_openings_check_multiplies_by_qty():
    """A window mark that prints 5 times on one wall consumes 5×
    its width. A single row `qty:5` must reach the flag correctly."""
    raw = {
        "walls": [{"label": "back", "width_ft": 10.0}],
        "doors": [],
        "windows": [{"mark": "A", "elevation": "back", "width_in": 48,
                     "height_in": 60, "qty": 3}],  # 3 × 4 ft = 12 > 10
        "roof_planes": [], "outside_corner_count": 0,
    }
    flags = check_read_consistency(raw)
    f = next(x for x in flags if x["code"] == "openings_exceed_wall_width")
    assert abs(f["vars"]["openings_sum_ft"] - 12.0) < 0.01
    assert abs(f["vars"]["wall_width_ft"] - 10.0) < 0.01
