"""BAR LINE (e) FLAG CENSUS + BAR LINE (g) GATE TRUTHFULNESS — structural
teeth (Howard's acceptance bar, closed 2026-08-10).

(e) Every flag the blueprint pipeline can raise must (1) carry EN and ES
card text — a code without dictionary text renders as a raw key in front
of a BDM — and (2) have a FIRING PIN somewhere in the suite — a flag no
test can fire is dead code wearing a safety label.

(g) Every gate blocker must be reachable (a gate that can never block is
a lying gate) and an empty blocker list must mean EMPTINESS — evaluated
truthfully from the estimate's own lines, never a skipped evaluation.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gates  # noqa: E402
from routes.ai_blueprint import build_blueprint_readback  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
BP_SRC = (BACKEND / "routes" / "ai_blueprint.py").read_text()
DICT_SRC = Path("/app/frontend/src/lib/dictionaries.js").read_text()


def _all_codes() -> set[str]:
    return set(re.findall(r'"code":\s*"([a-z_0-9]+)"', BP_SRC))


class TestFlagCensus:
    def test_every_code_carries_en_and_es_card_text(self):
        naked = []
        for c in sorted(_all_codes()):
            keys = [f'"bp.rb.rail.{c}"', f'"bp.rb.consistency.{c}"']
            hits = max(DICT_SRC.count(k) for k in keys)
            if hits < 2:  # one EN + one ES entry
                naked.append(f"{c} (dictionary entries found: {hits})")
        assert not naked, (
            "FLAG WITHOUT FULL CARD TEXT — a raw key in front of a BDM:\n"
            + "\n".join(naked))

    def test_every_code_has_a_firing_pin_in_the_suite(self):
        tests_src = "".join(p.read_text()
                            for p in (BACKEND / "tests").glob("*.py"))
        dead = [c for c in sorted(_all_codes()) if c not in tests_src]
        assert not dead, (
            "FLAG WITH NO FIRING PIN — dead code wearing a safety "
            "label. Fire it in a test:\n" + "\n".join(dead))

    def test_no_pitch_and_read_notes_fire(self):
        # The two codes the census found unpinned on its first run.
        raw = {"walls": [], "roof_planes": [], "notes": "porch assumed"}
        rail = build_blueprint_readback(raw)["rail"]
        codes = {r["code"] for r in rail}
        assert "no_pitch" in codes
        assert "read_notes" in codes
        raw2 = {"walls": [], "roof_planes": [], "roof_pitch": "7/12"}
        codes2 = {r["code"] for r in build_blueprint_readback(raw2)["rail"]}
        assert "no_pitch" not in codes2 and "read_notes" not in codes2


class TestGateTruthfulness:
    def test_every_blocker_code_is_reachable_in_the_suite(self):
        tests_src = "".join(p.read_text()
                            for p in (BACKEND / "tests").glob("*.py"))
        registry = (set(gates.QUOTE_BLOCKING) | set(gates.ORDER_BLOCKING)
                    | set(gates.GATE_TIERS) | set(gates.KIND_TIERS))
        dead = [c for c in sorted(registry) if c not in tests_src]
        assert not dead, (
            "GATE CODE WITH NO PIN — a gate that can never block (or "
            "never clear) is a lying gate:\n" + "\n".join(dead))

    def test_empty_blockers_mean_emptiness(self):
        # A priced, coherent single-family estimate → NO quote blockers.
        est = {"kind": "siding", "lines": [
            {"tab": "lp_smart", "name": "LP Series Lap 8in", "qty": 40,
             "section": "LP Smart Siding", "unit_price": 5.0,
             "lab_src": "human", "labor_price": 2.0},
        ]}
        assert gates.quote_gate_blockers(est, {}) == []

    def test_blockers_fire_from_the_lines_not_a_switch(self):
        # Two families carrying derived qty → the conflict blocker fires
        # from the LINES themselves.
        est = {"kind": "siding", "lines": [
            {"tab": "lp_smart", "name": "LP Series Lap 8in", "qty": 40,
             "section": "LP Smart Siding"},
            {"tab": "lp_smart", "name": "LP 4' x 10' Panel", "qty": 12,
             "section": "LP Smart Siding"},
        ]}
        codes = {i["code"] for i in gates.quote_gate_blockers(est, {})}
        assert "siding_family_conflict" in codes
        # human-entered qty is exempt (taped outranks derived) — the same
        # lines with qty_src human do NOT conflict.
        for l in est["lines"]:
            l["qty_src"] = "human"
        codes2 = {i["code"] for i in gates.quote_gate_blockers(est, {})}
        assert "siding_family_conflict" not in codes2

    def test_facade_scope_composed_is_pinned(self):
        # Census first run (2026-08-10) found this code unpinned: fired
        # at hover import when the scope excluded or force-sided a label.
        from lp_conventions import facade_scope_flag_label
        lbl = facade_scope_flag_label({
            "sided": {"siding": 900.0}, "wrap_sqft": 900.0,
            "excluded": {"masonry": 120.0},
            "excluded_reasons": {"masonry": "brick per elevations"},
            "unrecognized_sided": []})
        assert "FACADE SCOPE COMPOSED" in lbl
        assert "excluded 120" in lbl
        assert gates.tier_for("facade_scope_composed") == "quote"
        assert "facade_scope_composed" not in gates.QUOTE_BLOCKING

    def test_pending_price_is_pinned(self):
        # Census first run (2026-08-10) found this kind unpinned: a
        # package line with pricing_status pending escalates by NAME —
        # quote-tier, informational, never a silent $0.
        assert gates.tier_for(None, "pending_price") == "quote"
        assert gates.tier_for("some-line-name", "pending_price") == "quote"
        assert "pending_price" not in gates.QUOTE_BLOCKING
