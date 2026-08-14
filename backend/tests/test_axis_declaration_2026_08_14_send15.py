"""RULING E — INVERT THE AXIS CATALOG (send-15, 2026-08-14).

'Every dimension leaf DECLARES its axis: VERTICAL, HORIZONTAL, or UNKNOWN.
Undeclared is UNKNOWN. Not horizontal. Never inferred from the field name.
A share involving an UNKNOWN-axis leaf fires the CONFLICT rail, naming the
undeclared leaf.' The pin adds a leaf with a novel vertical name, asserts
it lands UNKNOWN, and that a share involving it fires the conflict rail —
the pin that stops the catalog rotting again.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes.ai_blueprint as ab  # noqa: E402
from routes.ai_blueprint import build_blueprint_readback  # noqa: E402


def test_declared_leaves_class_correctly():
    assert ab._leaf_axis("width_ft") == "H"
    assert ab._leaf_axis("height_ft") == "V"
    assert ab._leaf_axis("eave_lf") == "H"
    assert ab._leaf_axis("knee_wall_height_ft") == "V"


def test_novel_vertical_leaf_lands_UNKNOWN_not_horizontal():
    """A future `parapet_ft` reads as a height on a real plan, but the
    catalog has never heard of it — it must be UNKNOWN, never silently
    horizontal (the rot Ruling E kills)."""
    assert ab._leaf_axis("parapet_ft") == "U"
    assert ab._leaf_axis("story_ft") == "U"


def test_share_touching_an_unknown_leaf_fires_the_conflict_rail():
    """A share involving an undeclared-axis leaf CANNOT be proven possible
    → conflict, naming the undeclared leaf on the rail."""
    paths = ["walls.front.width_ft", "walls.front.parapet_ft"]
    assert ab._shared_attribution_conflict(paths) is True
    assert "parapet_ft" in ab._unknown_axis_leaves(paths)
    raw = {
        "walls": [{"label": "front", "width_ft": 20.0, "parapet_ft": 20.0}],
        "_dim_evidence": {
            "walls.front.width_ft": {"v": 20.0, "page": 6, "from": "20'-0\""},
            "walls.front.parapet_ft": {"v": 20.0, "page": 6, "from": "20'-0\""},
        },
    }
    ab._one_source_one_path_guard(raw)
    assert raw["_dim_shared_source"][0]["conflicting"] is True
    rb = build_blueprint_readback(raw)
    conf = next(r for r in rb["rail"]
                if r["code"] == "dims_shared_source_conflict")
    assert "undeclared-axis leaf: parapet_ft" in conf["text"]


def test_two_declared_horizontals_stay_plain():
    """Opposing-facade widths + a same-span gutter LF are all declared
    HORIZONTAL — no unknown, no vertical: PLAIN."""
    assert ab._shared_attribution_conflict(
        ["walls.front.width_ft", "walls.back.width_ft",
         "gutter_runs.front.lf"]) is False
