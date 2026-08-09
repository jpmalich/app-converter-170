"""MARK-MERGE DETECTION · PROXIMITY RULE · CALLOUT CENSUS (Howard's build
order 2026-08-09 send 4, items 2/3/4).

MECHANISM (evidenced from the Boni pixels): sibling schedule rows share a
long code prefix (SH 3-0_5-0 / SH 3-0_4-0 / SH 3-0_5-6) and the model
collapses a row into its prefix-sibling, copying the survivor's trailing
cells — C wore A's code, A's size, and once A's count; B and D before it.
Three symptoms, ONE defect: row identity not preserved cell-by-cell.

THE FIX AT THE SEAM: two marks NEVER share a product code on a real
schedule — sharers flag LOUD (mark_merge_suspected), the likely unread
sibling named from the omission register, and suspicion REVOKES the
region-relaxed matching leniency (a merged row's quote is its sibling's
print — leniency would resurrect the wrong dims).

PROXIMITY RULE — class over instance: a schedule row's locating match
must sit inside that schedule's table region (upright-only, NAMED blind
spot); no region (<2 anchors) = page-wide fallback. Inside the region the
containment cap relaxes — the region is the constraint.

CALLOUT CENSUS: profile keywords printed on the ELEVATION sheets with no
counterpart family in the read flag LOUD — a real detector behind "one
profile, but this house has gables".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _ocr_verify_marks, build_blueprint_readback,
)

PAYLOADS = [b"p1", b"p2"]


def _page(norms=None, boxed=None):
    return {"norms": norms or [], "boxed": boxed or []}


def _fake(pages):
    return lambda page: pages.get(page)


def _win(mk, code, size, pages=None):
    return {"id": mk, "product_code": code, "printed_size": size,
            "qty": 1, "width_in": 35.5, "height_in": 59.5,
            "schedule_pages": pages or [1]}


class TestMarkMergeDetection:
    def _sheet(self):
        # Anchors: SH3050 + mark A. SH3056 prints in-region, unread.
        # A's size skeleton exists ONLY inside a long joined row run.
        return _page(
            norms=["A", "SH3050", "SH3056",
                   "SH3050211X411PELLAENCOMPASS"],
            boxed=[("A", (80, 100, 92, 112)),
                   ("SH3050", (100, 100, 160, 112)),
                   ("SH3056", (100, 130, 160, 142)),
                   ("SH3050211X411PELLAENCOMPASS", (100, 100, 400, 112))])

    def test_shared_code_flags_loud_with_likely_sibling(self):
        raw = {"windows": [
            _win("A", "SH 3-0_5-0", "2'-11 1/2\" x 4'-11 1/2\""),
            _win("C", "SH 3-0_5-0", "2'-11 1/2\" x 4'-11 1/2\"")]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: self._sheet()}))
        sus = raw["_mark_merge_suspected"][0]
        assert set(sus["marks"]) == {"A", "C"}
        assert sus["code"] == "SH3050"
        assert sus["likely_unread"] == ["SH3056"]  # one glyph away
        rb = build_blueprint_readback(raw)
        f = next(x for x in rb["rail"] if x["code"] == "mark_merge_suspected")
        assert f["level"] == "loud"
        assert "SH3056" in f["text"]

    def test_suspicion_revokes_the_leniency(self):
        # Same quote, same sheet: A (unsuspected in this read) locates
        # via the relaxed in-region containment; C (a merge suspect)
        # verifies under the strict cap and its copied quote DIES.
        raw = {"windows": [
            _win("A", "SH 3-0_5-0", "2'-11 1/2\" x 4'-11 1/2\""),
            _win("C", "SH 3-0_5-0", "2'-11 1/2\" x 4'-11 1/2\"")]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: self._sheet()}))
        a = next(w for w in raw["windows"] if w["id"] == "A")
        c = next(w for w in raw["windows"] if w["id"] == "C")
        assert c["width_in"] is None and c["height_in"] is None
        assert a["width_in"] is None  # A is a suspect too — both strict
        # ONE defect, one family: distinct codes = no suspicion, and the
        # relaxed in-region match lets the true print live.
        raw2 = {"windows": [_win("A", "SH 3-0_5-0",
                                 "2'-11 1/2\" x 4'-11 1/2\"")]}
        _ocr_verify_marks(raw2, PAYLOADS, runs_for_page=_fake(
            {1: self._sheet()}))
        assert raw2["windows"][0]["width_in"] == 35.5

    def test_distinct_codes_never_flag(self):
        raw = {"windows": [_win("A", "SH 3-0_5-0", ""),
                           _win("B", "SH 3-0_4-0", "")]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["A", "B", "SH3050", "SH3040"])}))
        assert "_mark_merge_suspected" not in raw


class TestProximityRule:
    def test_out_of_region_match_no_longer_saves(self):
        # The E1 CLASS: the row's only locatable quote matches print far
        # outside the table region — with a region present it carries no
        # weight and the row drops.
        raw = {"doors": [{"id": "E1", "printed_size": "6'-0\" x 6'-8\"",
                          "product_code": "", "qty": 1, "width_in": 72,
                          "height_in": 80, "type_hint": "entry",
                          "exterior_evidence": "elevation",
                          "schedule_pages": [1]},
                         {"id": "E3", "printed_size": "", "product_code": "",
                          "qty": 1, "width_in": 36, "height_in": 80,
                          "type_hint": "entry",
                          "exterior_evidence": "elevation",
                          "schedule_pages": [1]},
                         {"id": "G1", "printed_size": "", "product_code": "",
                          "qty": 1, "width_in": 192, "height_in": 96,
                          "type_hint": "garage",
                          "exterior_evidence": "elevation",
                          "schedule_pages": [1]}]}
        boxed = [("E3", (100, 100, 120, 112)),
                 ("G1", (100, 130, 120, 142)),
                 # E1's size prints as a wall dim on the far plan side:
                 ("60X68", (2000, 2000, 2060, 2012))]
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=[b[0] for b in boxed], boxed=boxed)}))
        assert [d["id"] for d in raw["doors"]] == ["E3", "G1"]

    def test_no_region_falls_back_page_wide(self):
        # <2 anchors = undecidable region — the named fallback keeps the
        # page-wide behaviour rather than inventing a region.
        raw = {"doors": [{"id": "G1", "printed_size": "16'-0\" x 8'-0\"",
                          "product_code": "", "qty": 1, "width_in": 192,
                          "height_in": 96, "type_hint": "garage",
                          "exterior_evidence": "elevation",
                          "schedule_pages": [1]}]}
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {1: _page(norms=["160X80"],
                      boxed=[("160X80", (10, 10, 60, 22))])}))
        assert len(raw["doors"]) == 1


class TestCalloutCensus:
    def _raw(self, gable_callout=None):
        return {
            "sheets_identified": [{"page": 2, "useful_for": "elevation"}],
            "walls": [{"label": "front", "width_ft": 40, "height_ft": 9,
                       "wall_body_profile_callout": "LAP 4\"",
                       "gable_profile_callout": gable_callout,
                       "accents": []}],
            "windows": [{"id": "A", "printed_size": "", "qty": 1,
                         "schedule_pages": [2]}]}

    def test_printed_shake_with_no_shake_in_read_flags_loud(self):
        raw = self._raw()
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {2: _page(norms=["A", "SHAKEGABLE", "7SHAKESIDING"])}))
        cal = raw["_callout_omissions"]
        assert cal == [{"family": "shake", "page": 2,
                        "run": "SHAKEGABLE"}]
        rb = build_blueprint_readback(raw)
        f = next(x for x in rb["rail"] if x["code"] == "callout_omitted")
        assert f["level"] == "loud" and "shake" in f["text"]

    def test_family_carried_by_the_read_never_flags(self):
        raw = self._raw(gable_callout="SHAKE")
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {2: _page(norms=["A", "SHAKEGABLE"])}))
        assert "_callout_omissions" not in raw

    def test_no_elevation_sheets_means_no_census(self):
        raw = self._raw()
        raw["sheets_identified"] = []
        _ocr_verify_marks(raw, PAYLOADS, runs_for_page=_fake(
            {2: _page(norms=["SHAKEGABLE"])}))
        assert "_callout_omissions" not in raw


class TestPromptCarriesRowIdentity:
    def test_row_identity_rule_printed(self):
        assert "ROW IDENTITY (ruled 2026-08-09)" in SYSTEM_PROMPT
        assert "NEVER copy a sibling row's cells" in SYSTEM_PROMPT
