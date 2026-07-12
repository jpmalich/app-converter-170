"""Iter 79j.95 — color architecture pins (Howard ruling: per-component,
line-level color; consolidation splits on color; apply-to-all is the
shortcut not the model; availability flagged never silently substituted)."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv(Path("/app/backend/.env"))

from lp_colors import (  # noqa: E402
    ALL_COLORS, AVAILABILITY_FLAG, COMPONENT_GROUPS, EXPERTFINISH_CORE_16,
    NATURALS_COLLECTION, apply_colors, consolidate_lines, group_for_line,
    resolve_group_colors,
)
from lp_conventions import FASCIA_RAKE_ITEM, ISC_TRIM_ITEM, WRAP_TRIM_ITEM  # noqa: E402
from lp_package import OSC_ITEM, assemble_lp_package  # noqa: E402
from tests.test_lp_package_iter93 import LETRICK_HEIGHTS, MEAS, _letrick_locations  # noqa: E402


def test_published_palette_pinned():
    assert len(EXPERTFINISH_CORE_16) == 16
    assert "Sand Dunes" in EXPERTFINISH_CORE_16      # 2026 Color of the Year
    assert len(NATURALS_COLLECTION) == 6
    assert len(ALL_COLORS) == 23                     # 16 + 6 + primed
    assert set(COMPONENT_GROUPS) == {"siding", "soffit_fascia", "opening_trim", "osc", "isc"}


def test_group_mapping():
    assert group_for_line({"name": OSC_ITEM}) == "osc"
    assert group_for_line({"name": ISC_TRIM_ITEM}) == "isc"
    assert group_for_line({"name": WRAP_TRIM_ITEM}) == "opening_trim"
    assert group_for_line({"name": FASCIA_RAKE_ITEM}) == "soffit_fascia"
    assert group_for_line({"name": "38 Series Soffit 16 x 16 Vented"}) == "soffit_fascia"
    assert group_for_line({"name": "38 Series Lap 3/8\" x 8\" x 16'",
                           "section": "LP Smart Siding"}) == "siding"
    assert group_for_line({"name": "Touch up kits", "section": "LP Siding Accessories"}) is None


def test_apply_to_all_is_shortcut_and_group_overrides_win():
    resolved, errors = resolve_group_colors({"all": "Quarry Gray", "osc": "Snowscape White"})
    assert errors == []
    assert resolved["siding"] == "Quarry Gray"
    assert resolved["osc"] == "Snowscape White"  # corners recolor while siding holds


def test_unknown_color_and_group_refused_never_invented():
    resolved, errors = resolve_group_colors({"all": "Hot Pink", "chimney": "Abyss Black"})
    assert any("not in the published ExpertFinish palette" in e for e in errors)
    assert any("unknown component group" in e for e in errors)
    assert all(v is None for v in resolved.values())


def test_every_line_carries_color_field_and_availability_flag():
    pkg = assemble_lp_package(MEAS, _letrick_locations(), LETRICK_HEIGHTS,
                              colors={"all": "Terra Brown", "osc": "Abyss Black"})
    assert pkg["summary"]["color_errors"] == []
    for l in pkg["lines"]:
        assert "color" in l and "component_group" in l
    osc_line = next(l for l in pkg["lines"] if l["name"] == OSC_ITEM)
    lap = next(l for l in pkg["lines"] if "38 Series Lap" in l["name"])
    assert osc_line["color"] == "Abyss Black" and lap["color"] == "Terra Brown"
    assert AVAILABILITY_FLAG in osc_line["color_flags"]  # matrix unverified → flagged


def test_consolidation_splits_on_color():
    a = {"name": "X", "color": "Terra Brown", "qty": 3}
    b = {"name": "X", "color": "Abyss Black", "qty": 2}
    c = {"name": "X", "color": "Terra Brown", "qty": 4}
    out = consolidate_lines([a, b, c])
    assert len(out) == 2  # same profile + different color = different SKU
    assert next(l for l in out if l["color"] == "Terra Brown")["qty"] == 7


def test_no_colors_means_none_not_default():
    lines = [{"name": OSC_ITEM}]
    apply_colors(lines, None)
    assert lines[0]["color"] is None  # never a silent default color
