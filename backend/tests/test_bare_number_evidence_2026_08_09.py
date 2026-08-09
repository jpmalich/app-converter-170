"""BARE-NUMBER EVIDENCE — ROOF PLANES + GUTTER RUNS (Howard's build order
2026-08-09 send 3, item 4).

"22 OF 22 EVIDENCED PATHS AGREED, while the unevidenced numbers have
swung all week… THE INSTABILITY THAT REMAINS LIVES EXACTLY IN THE
UNGUARDED FAMILY. Evidence is what stops a number moving."

Plane eave/rake figures and gutter-run LF join the evidence discipline:
DIM objects in both prompts, quotes flattened + recorded by the
enforcement pass, bare numbers NULLED by construction and accounted.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    ROOF_PASS_PROMPT, SYSTEM_PROMPT, _dim_v, _enforce_evidence_or_null,
    _merge_roof_pass, _roof_pass_needed,
)


class TestPromptsCarryTheDiscipline:
    def test_main_prompt_planes_and_runs_are_dims(self):
        i = SYSTEM_PROMPT.index('"roof_planes"')
        seg = SYSTEM_PROMPT[i:i + 2200]
        assert '"eave_lf": DIM | null' in seg
        assert '"rake_lf": DIM | null' in seg
        gi = SYSTEM_PROMPT.index('"gutter_runs"')
        assert '"lf": DIM | null' in SYSTEM_PROMPT[gi:gi + 900]

    def test_roof_pass_prompt_matches(self):
        assert ROOF_PASS_PROMPT.count('"from": "<printed dim VERBATIM>"') >= 3


class TestEnforcement:
    def test_evidenced_figures_flatten_and_record(self):
        raw = {"roof_planes": [
            {"label": "main", "is_porch": False,
             "eave_lf": {"v": 128, "page": 3, "from": "34'-0\" + 30'-0\""},
             "rake_lf": {"v": 42.5, "calc": "2 gables × rake formula",
                         "srcs": [{"page": 4, "from": "34'-0\""},
                                  {"page": 4, "from": "7/12"}]}}],
            "gutter_runs": [
                {"label": "front", "lf": {"v": 58, "page": 3,
                                          "from": "58'-0\""}}]}
        _enforce_evidence_or_null(raw)
        p = raw["roof_planes"][0]
        assert p["eave_lf"] == 128 and p["rake_lf"] == 42.5
        assert raw["gutter_runs"][0]["lf"] == 58
        ev = raw["_dim_evidence"]
        assert "roof_planes.main.eave_lf" in ev
        assert "roof_planes.main.rake_lf" in ev
        assert "gutter_runs.front.lf" in ev

    def test_bare_numbers_are_nulled_and_accounted(self):
        raw = {"roof_planes": [{"label": "garage", "is_porch": False,
                                "eave_lf": 24, "rake_lf": 18}],
               "gutter_runs": [{"label": "back", "lf": 58}]}
        _enforce_evidence_or_null(raw)
        p = raw["roof_planes"][0]
        assert p["eave_lf"] is None and p["rake_lf"] is None
        assert raw["gutter_runs"][0]["lf"] is None
        nul = raw["_nulled_no_evidence"]
        assert {"roof_planes.garage.eave_lf", "roof_planes.garage.rake_lf",
                "gutter_runs.back.lf"} <= set(nul)
        assert set(nul) <= set(
            raw["_seam_ledger"]["dims_nulled_no_evidence"]["items"])

    def test_null_is_unread_not_nulled(self):
        raw = {"roof_planes": [{"label": "main", "is_porch": False,
                                "eave_lf": None, "rake_lf": None}]}
        _enforce_evidence_or_null(raw)
        assert "_nulled_no_evidence" not in raw
        assert "roof_planes.main.eave_lf" in raw["_dim_unread"]


class TestRoofPassMergeKeepsEvidence:
    def test_dim_v_reads_dims_and_numbers(self):
        assert _dim_v({"v": 42.5, "page": 4, "from": "x"}) == 42.5
        assert _dim_v(18) == 18.0
        assert _dim_v(None) == 0.0

    def test_gable_blind_detection_sees_through_dims(self):
        raw = {"roof_planes": [{"label": "garage",
                                "rake_lf": {"v": 0, "page": 4, "from": "-"},
                                "gable_ends": 0}],
               "doors": [{"type_hint": "garage"}], "walls": []}
        assert _roof_pass_needed(raw) is True
        raw["roof_planes"][0]["rake_lf"] = {"v": 21, "page": 4,
                                            "from": "16'-0\" @ 7/12"}
        raw["roof_planes"][0]["gable_ends"] = 1
        assert _roof_pass_needed(raw) is False

    def test_surgical_rake_merge_carries_the_dim_whole(self):
        raw = {"roof_planes": [{"label": "garage", "rake_lf": None,
                                "gable_ends": 0}]}
        rp = {"roof_planes": [
            {"label": "garage", "gable_ends": 1,
             "rake_lf": {"v": 21.4, "calc": "gable rake formula",
                         "srcs": [{"page": 4, "from": "16'-0\""}]}}]}
        _merge_roof_pass(raw, rp)
        g = raw["roof_planes"][0]
        assert isinstance(g["rake_lf"], dict) and g["rake_lf"]["v"] == 21.4
        assert raw["_roof_pass"]["accepted"]["garage_rakes"][
            "rake_lf"] == 21.4
