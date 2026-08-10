"""ROOF SECOND PASS — REGISTERED, LEDGERED, RULED (Howard ruled
2026-08-09 send 7, after the register audit found the merge an
unregistered seam that could replace evidenced corner heights with bare
numbers the evidence gate then nulled — evidence AND value destroyed).

THE NEVER-TOUCH RULE: the roof pass may NEVER replace an EVIDENCED
value with an unevidenced one. Every accepted overwrite is ledgered
old→new (roof_pass_overwrite); every refusal is NAMED on the rail.

Plus the same sitting's other teeth:
- PAGE TRUNCATION is a registered seam, flagged LOUD on the card.
- The callout census reads accent_profiles (the schema key), so an
  accent-borne family suppresses a false callout_omitted flag.
- EST-886440 is UNTOUCHABLE — the server refuses every write.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import seam_accounting  # noqa: E402
from routes.ai_blueprint import (  # noqa: E402
    ROOF_PASS_PROMPT, _merge_roof_pass, _ocr_verify_marks,
    build_blueprint_readback,
)

EV = {"v": 20.0, "page": 3, "from": "9'-0\""}


def _base_raw(**over):
    raw = {
        "roof_planes": [{"label": "main", "eave_lf": {"v": 60, "page": 2,
                                                      "from": "60'-0\""},
                         "rake_lf": None, "gable_ends": 2}],
        "outside_corner_count": 4, "inside_corner_count": 0,
        "outside_corner_lf": 38.0,
        "outside_corner_heights_ft": [EV, EV, EV, EV],
        "roof_pitch": "7/12",
        "walls": [],
    }
    raw.update(over)
    return raw


class TestNeverTouchRule:
    def test_evidenced_heights_never_replaced_by_bare_numbers(self):
        raw = _base_raw()
        rp = {"outside_corner_count": 6, "inside_corner_count": 2,
              "outside_corner_lf": 55.0,
              "outside_corner_heights_ft": [9, 9, 9, 20, 20, 9]}
        _merge_roof_pass(raw, rp)
        # counts may move (walk acceptance unchanged) — heights may NOT.
        assert raw["outside_corner_heights_ft"] == [EV, EV, EV, EV]
        rej = raw["_roof_pass"]["rejected"]
        assert "corner_heights" in rej
        assert "never" in rej["corner_heights"]

    def test_evidenced_replacement_is_accepted_and_ledgered(self):
        raw = _base_raw()
        new_hs = [dict(EV) for _ in range(6)]
        rp = {"outside_corner_count": 6, "inside_corner_count": 2,
              "outside_corner_lf": 55.0,
              "outside_corner_heights_ft": new_hs}
        _merge_roof_pass(raw, rp)
        assert raw["outside_corner_heights_ft"] == new_hs
        led = raw["_seam_ledger"]["roof_pass_overwrite"]["items"]
        assert any("corner_heights" in i for i in led)

    def test_bare_primary_heights_may_be_replaced(self):
        raw = _base_raw(outside_corner_heights_ft=[9, 9, 9, 9])
        rp = {"outside_corner_count": 6, "inside_corner_count": 2,
              "outside_corner_lf": 55.0,
              "outside_corner_heights_ft": [9, 9, 9, 20, 20, 9]}
        _merge_roof_pass(raw, rp)
        assert raw["outside_corner_heights_ft"] == [9, 9, 9, 20, 20, 9]
        assert "corner_heights" not in raw["_roof_pass"]["rejected"]

    def test_corner_and_pitch_overwrites_are_ledgered_old_to_new(self):
        raw = _base_raw(outside_corner_heights_ft=[])
        rp = {"outside_corner_count": 6, "inside_corner_count": 2,
              "outside_corner_lf": 55.0, "roof_pitch": "9/12"}
        _merge_roof_pass(raw, rp)
        items = raw["_seam_ledger"]["roof_pass_overwrite"]["items"]
        assert any("corners out 4→6" in i for i in items)
        assert any("roof_pitch 7/12→9/12" in i for i in items)

    def test_registry_carries_the_new_seams(self):
        assert "roof_pass_overwrite" in seam_accounting.SEAM_REGISTRY
        assert "pages_truncated" in seam_accounting.SEAM_REGISTRY

    def test_roof_pass_prompt_demands_evidenced_corner_heights(self):
        # The roof-pass schema carried bare-number heights while the main
        # schema carried DIMs — the exact asymmetry that fed the defect.
        assert '"outside_corner_heights_ft": [{"v": number' \
            in ROOF_PASS_PROMPT

    def test_rejection_and_truncation_ride_the_rail(self):
        raw = _base_raw(roof_planes=[{"label": "main", "eave_lf": 60,
                                      "rake_lf": 30, "gable_ends": 2}])
        raw["_roof_pass"] = {"accepted": {},
                             "rejected": {"corner_heights": "why text"},
                             "notes": ""}
        raw["_pages_truncated"] = {"total": 26, "read": 20}
        rb = build_blueprint_readback(raw)
        codes = {r["code"] for r in rb["rail"]}
        assert "roof_pass_rejected" in codes
        assert "pages_truncated" in codes
        pt = next(r for r in rb["rail"] if r["code"] == "pages_truncated")
        assert pt["level"] == "loud" and "26" in pt["text"]


class TestPageTruncationAccounting:
    def test_render_returns_total_page_count(self):
        import inspect
        from routes.ai_blueprint import _render_pdf_to_pngs
        sig = str(inspect.signature(_render_pdf_to_pngs))
        assert "tuple" in sig  # (pages, total) — caller accounts the gap

    def test_truncation_accounts_in_the_ledger(self):
        raw = {}
        pt = {"total": 26, "read": 20}
        raw["_pages_truncated"] = pt
        seam_accounting.account(
            raw, "pages_truncated",
            [f"pages {pt['read'] + 1}-{pt['total']} never rendered"],
            kept=pt["read"])
        e = raw["_seam_ledger"]["pages_truncated"]
        assert e["removed"] == 1 and e["kept"] == 20
        assert "21-26" in e["items"][0]


class TestCalloutCensusReadsTheSchemaKey:
    """The dead-key defect (register audit bucket ①): the census read
    w.get('accents') while the model returns accent_profiles — the accent
    leg never contributed, false-flagging callout_omitted on any house
    whose only SHAKE lives in an accent row."""

    def _run(self, walls):
        raw = {
            "sheets_identified": [
                {"page": 1, "sheet_title": "SCHEDULE", "useful_for": "schedule"},
                {"page": 2, "sheet_title": "FRONT", "useful_for": "elevation"}],
            "windows": [{"id": "A", "product_code": "SH3050",
                         "printed_size": "", "schedule_pages": [1],
                         "count_by_page": {"1": 2}, "qty": 2}],
            "doors": [],
            "walls": walls,
        }
        pages = {
            1: {"norms": ["A", "SH3050"], "boxed": []},
            2: {"norms": ["SHAKE"], "boxed": []},
        }
        _ocr_verify_marks(raw, [b"x", b"y"],
                          runs_for_page=lambda p: pages.get(p))
        return raw

    def test_accent_borne_family_suppresses_the_flag(self):
        raw = self._run([{"label": "front",
                          "accent_profiles": [
                              {"location": "porch face",
                               "profile_callout": "SHAKE",
                               "approx_sqft": 40}]}])
        fams = [c["family"] for c in (raw.get("_callout_omissions") or [])]
        assert "shake" not in fams, (
            "accent-borne shake must satisfy the census — the accents key "
            "regression is back")

    def test_missing_family_still_flags(self):
        raw = self._run([{"label": "front", "accent_profiles": []}])
        fams = [c["family"] for c in (raw.get("_callout_omissions") or [])]
        assert "shake" in fams


class TestUntouchableEstimate:
    def test_untouchable_write_refused_423(self, monkeypatch):
        import untouchable

        class _Coll:
            async def find_one(self, *a, **k):
                return {"estimate_number": "EST-886440"}

        class _DB:
            estimates = _Coll()

        monkeypatch.setattr(untouchable, "db", _DB())
        from fastapi import HTTPException
        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(HTTPException) as ei:
                loop.run_until_complete(
                    untouchable.refuse_untouchable("any-id"))
        finally:
            loop.close()
        assert ei.value.status_code == 423
        assert "UNTOUCHABLE" in ei.value.detail

    def test_other_estimates_pass(self, monkeypatch):
        import untouchable

        class _Coll:
            async def find_one(self, *a, **k):
                return {"estimate_number": "EST-000001"}

        class _DB:
            estimates = _Coll()

        monkeypatch.setattr(untouchable, "db", _DB())
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                untouchable.refuse_untouchable("any-id"))
        finally:
            loop.close()

    def test_every_mutation_route_carries_the_guard(self):
        """Completeness register — the guard covers every estimate
        mutation surface (the productive detector species)."""
        import ast as _ast
        base = Path(__file__).resolve().parents[1] / "routes"
        expected = {
            "estimates.py": {"update_estimate", "patch_estimate",
                             "delete_estimate", "set_estimate_protection",
                             "save_model3d_snapshot"},
            "hover.py": {"rederive_estimate", "hover_lp_run"},
            "lp_package_routes.py": {"lp_blueprint_applied",
                                     "lp_package_materialize",
                                     "order_release",
                                     "set_default_profile"},
        }
        for fname, fns in expected.items():
            src = (base / fname).read_text()
            tree = _ast.parse(src)
            guarded = set()
            for node in _ast.walk(tree):
                if isinstance(node, _ast.AsyncFunctionDef) and node.name in fns:
                    seg = _ast.get_source_segment(src, node) or ""
                    if "refuse_untouchable" in seg:
                        guarded.add(node.name)
            missing = fns - guarded
            assert not missing, f"{fname}: unguarded mutation routes {missing}"
