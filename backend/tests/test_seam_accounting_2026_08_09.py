"""SEAM ACCOUNTING (Howard's build order 2026-08-09, item 3).

"Build a detector/registry that fails the build if data drops silently.
Identify layers doing filtering, splitting, projecting, or whitelisting
(the 'es: {' dictionary truncation, the qty-0 filter dropping rows) and
ensure they account for what they removed."

Two teeth:
1. REGISTRY — every removing layer records into the seam ledger via
   seam_accounting.account(); an unregistered seam RAISES.
2. DETECTOR — an AST scan of ai_blueprint.py finds every filtering list
   comprehension over the data-bearing collections. A new filter that is
   neither accounted nor reviewed-inert FAILS this suite by name.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import seam_accounting  # noqa: E402

BP = Path(__file__).resolve().parents[1] / "routes" / "ai_blueprint.py"

# Every filtering comprehension over a data-bearing collection, reviewed.
# ACCOUNTED = the complement is recorded in the seam ledger.
# INERT = a selection/projection that feeds a comparison, never a store.
# A new entry appearing here unreviewed is the failure this test exists for.
ALLOWLIST = {
    # INERT — selects the garage plane to pick roof-pass sheets.
    '[p for p in planes if "garage" in str(p.get("label") or "").lower()]',
    # INERT — wall heights feeding the tallest-wall comparison.
    '[_f(w.get("height_ft")) for w in walls if _f(w.get("height_ft")) > 0]',
    # ACCOUNTED (interior_doors_dropped) — the selection…
    '[d for d in doors if isinstance(d, dict) and '
    'str(d.get("exterior_evidence") or "").lower() == "none"]',
    # …and the removal it feeds.
    '[d for d in doors if d not in _interior]',
    # ACCOUNTED (lp_smart_lines_cut) — THE CUT.
    '[l for l in _built if (l.get("tab") or "vinyl") != "lp_smart"]',
    # ACCOUNTED (marks_dropped_not_located + interior_signal_dropped) —
    # fabricated rows and machine-read interior rows leave.
    '[r for r in arr if not (isinstance(r, dict) and '
    '(r.get("_drop_not_located") or r.get("_drop_interior_signal")))]',
    # INERT — the accounting arm of THE CUT: projects the removed rows'
    # names INTO the ledger, removes nothing itself.
    '[str(l.get("name") or "?") for l in _built '
    'if (l.get("tab") or "vinyl") == "lp_smart"]',
}

WATCHED = {"doors", "windows", "walls", "planes", "lines", "_built",
           "rows", "arr"}


def _filtering_comps():
    src = BP.read_text()
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ListComp):
            continue
        for g in node.generators:
            if g.ifs and isinstance(g.iter, ast.Name) and g.iter.id in WATCHED:
                seg = " ".join(ast.get_source_segment(src, node).split())
                found.append((node.lineno, seg))
    return found


class TestDetector:
    def test_every_filtering_seam_is_reviewed(self):
        unreviewed = [(ln, seg) for ln, seg in _filtering_comps()
                      if seg not in ALLOWLIST]
        assert not unreviewed, (
            "UNACCOUNTED SEAM(S) — a layer filters a data collection "
            "without accounting for what it removes. Route the removal "
            "through seam_accounting.account() (or review it as inert) "
            "and add it to the ALLOWLIST:\n" + "\n".join(
                f"  line {ln}: {seg}" for ln, seg in unreviewed))

    def test_allowlist_carries_no_dead_entries(self):
        live = {seg for _, seg in _filtering_comps()}
        dead = ALLOWLIST - live
        assert not dead, (
            "ALLOWLIST entries no longer in the source — remove them so "
            "the list stays a true register:\n" + "\n".join(sorted(dead)))


class TestRegistry:
    def test_unregistered_seam_raises(self):
        with pytest.raises(KeyError, match="unregistered seam"):
            seam_accounting.account({}, "brand_new_filter", ["x"])

    def test_account_records_removed_and_kept(self):
        c = {}
        seam_accounting.account(c, "interior_doors_dropped",
                                ["E4", "E5"], kept=4)
        e = c["_seam_ledger"]["interior_doors_dropped"]
        assert e["removed"] == 2 and e["items"] == ["E4", "E5"]
        assert e["kept"] == 4
        seam_accounting.account(c, "interior_doors_dropped", ["E6"])
        assert c["_seam_ledger"]["interior_doors_dropped"]["removed"] == 3

    def test_every_registered_seam_names_its_layer(self):
        for name, desc in seam_accounting.SEAM_REGISTRY.items():
            assert isinstance(desc, str) and len(desc) > 20, name


class TestLiveSeamsAccount:
    def test_interior_door_drop_accounts(self):
        from routes.ai_blueprint import _aggregate_to_hover_shape
        raw = {"doors": [
            {"id": "E2", "qty": 1, "width_in": 36, "height_in": 80,
             "type_hint": "entry", "exterior_evidence": "elevation"},
            {"id": "D7", "qty": 1, "width_in": 30, "height_in": 80,
             "type_hint": "entry", "exterior_evidence": "none"}],
            "walls": [{"label": "front", "width_ft": 40, "height_ft": 9,
                       "gable_triangle_height_ft": 0}]}
        _aggregate_to_hover_shape(raw)
        assert raw["_seam_ledger"]["interior_doors_dropped"]["items"] == ["D7"]

    def test_evidence_nulls_account(self):
        from routes.ai_blueprint import _enforce_evidence_or_null
        raw = {"eave_overhang_in": 12}  # bare number, no quote — nulled
        _enforce_evidence_or_null(raw)
        assert "eave_overhang_in" in raw["_seam_ledger"][
            "dims_nulled_no_evidence"]["items"]

    def test_ledger_rides_the_readback(self):
        from routes.ai_blueprint import build_blueprint_readback
        raw = {"_seam_ledger": {"interior_doors_dropped":
                                {"removed": 1, "items": ["D7"]}}}
        rb = build_blueprint_readback(raw)
        assert rb["seams"]["interior_doors_dropped"]["removed"] == 1

    def test_dictionary_strings_carry_no_es_brace_landmine(self):
        # The 'es: {' truncation class (ruled 2026-08-08) — no EN rail
        # string added for these seams may contain the splitter landmine.
        dicts = (Path(__file__).resolve().parents[2] / "frontend" / "src"
                 / "lib" / "dictionaries.js").read_text()
        for line in dicts.splitlines():
            if "bp.rb.rail.count_" in line or "bp.rb.rail.mark_" in line:
                assert "es: {" not in line.split(":", 1)[1], line
