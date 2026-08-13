"""SEND-11 CORRECTIONS TO SEND-10 (Howard ruled 2026-08-13 send-11):

Verbatim item 1: "Update _one_source_one_path_guard to DEMOTE ALL
consumers when a quote is shared. If one must survive, mark it
UNVERIFIED, never AI-READ ✓. Crowning the alphabetically-first is a
coin flip; the box model wins on either coin face."

Verbatim item 2: "Add a MISREAD tier between FABRICATED and
UNVERIFIED. A quote within one edit (character) of a real located
string is a misread (e.g., 32'-5 1/2\" instead of 33'-5 1/2\"). Name
it, show the real string, kill the value for money, but diagnose it
as a typo rather than an invention."

Verbatim item 3 (report-only): "Weigh OCR coverage on the page before
branding a quote FABRICATED. High character count + no hit = strong
fabrication evidence. Poor coverage + no hit = weak evidence — the
miss may be OCR's fault, not the model's."

The Boni cases each ruling targets:
  Item 1: walls.left.width_ft AND walls.right.width_ft both fed
          from the SAME 39'-0" quote. Under send-10, `left` kept the
          quote as evidence. That was arbitrary; send-11 nulls both.
  Item 2: The 32'-5 1/2" claim on Boni was a MISREAD of a real
          33'-5 1/2" printed on the plans. Same class as the
          SH340-vs-SH3040 glyph drop, one digit over.
  Item 3: A stacked-fraction elevation cell OCR can barely read is
          NOT strong evidence for fabrication when the quote is
          absent from that page's runs. Coverage decides the badge.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    _null_unverified_quotes,
    _one_source_one_path_guard,
    build_blueprint_readback,
)


# ---------- (A) DEMOTE-ALL on shared-source quotes ------------------

def _mirror_raw():
    return {
        "walls": [
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


def test_demote_all_nulls_every_consumer():
    """Both consumers null on raw. Neither may claim AI-READ ✓."""
    raw = _mirror_raw()
    _one_source_one_path_guard(raw)
    walls = {w["label"]: w for w in raw["walls"]}
    assert walls["left"]["width_ft"] is None
    assert walls["right"]["width_ft"] is None


def test_demote_all_records_kept_as_none():
    """The shared-source ledger MUST carry `kept=None`. A consumer
    surviving as 'the kept one' would recreate the coin-flip send-11
    ruled out."""
    raw = _mirror_raw()
    _one_source_one_path_guard(raw)
    shared = raw.get("_dim_shared_source") or []
    assert len(shared) == 1
    r = shared[0]
    assert r["kept"] is None
    assert set(r["demoted"]) == {"walls.left.width_ft",
                                 "walls.right.width_ft"}
    assert set(r["consumers"]) == {"walls.left.width_ft",
                                   "walls.right.width_ft"}


def test_demote_all_both_land_on_unverified_ledger():
    raw = _mirror_raw()
    _one_source_one_path_guard(raw)
    unv = raw.get("_dim_unverified") or []
    paths = {r["path"] for r in unv}
    assert paths == {"walls.left.width_ft", "walls.right.width_ft"}
    for r in unv:
        assert r["value"] == 39.0
        assert "shared" in r["reason"]
        assert "send-11" in r["reason"]


def test_demote_all_three_way_share_demotes_all_three():
    """A quote consumed by three paths demotes all three (there is
    no 'first two demote, third keep' compromise)."""
    raw = {
        "walls": [
            {"label": "back", "width_ft": 39.0},
            {"label": "left", "width_ft": 39.0},
            {"label": "right", "width_ft": 39.0},
        ],
        "_dim_evidence": {
            f"walls.{lbl}.width_ft": {
                "v": 39.0, "page": 6, "from": "39'-0\""}
            for lbl in ("back", "left", "right")
        },
    }
    _one_source_one_path_guard(raw)
    for w in raw["walls"]:
        assert w["width_ft"] is None
    shared = raw["_dim_shared_source"][0]
    assert shared["kept"] is None
    assert len(shared["demoted"]) == 3


def test_singleton_quote_still_untouched():
    """A quote consumed by exactly one path is fine; the guard must
    not fire on the common case (regression pin)."""
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


# ---------- (B) MISREAD tier ----------------------------------------

def _misread_raw():
    """A single wall claim whose quote 32'-5 1/2" does NOT appear on
    the page, but a real 33'-5 1/2" run DOES (one substitution away).
    The pre-locator step recorded `misread_of` on the miss."""
    return {
        "walls": [{"label": "front", "width_ft": 32.458}],
        "_dim_evidence": {
            "walls.front.width_ft": {
                "v": 32.458, "page": 4, "from": "32'-5 1/2\""},
        },
        "_ocr_quote_misses": [{
            "path": "walls.front.width_ft",
            "page": 4,
            "from": "32'-5 1/2\"",
            "rotations_checked": True,
            "reason": "quote norm not present in OCR on page",
            "misread_of": "3350112",  # normalised 33'-5 1/2"
            "page_ocr_chars": 4200,
        }],
    }


def test_misread_lands_on_dim_misread_not_fabricated():
    """SEND-11 item 2: presence of `misread_of` routes the miss to
    the MISREAD tier, NOT the FABRICATED tier."""
    raw = _misread_raw()
    _null_unverified_quotes(raw)
    misread = raw.get("_dim_misread") or []
    assert len(misread) == 1
    m = misread[0]
    assert m["path"] == "walls.front.width_ft"
    assert m["value"] == 32.458
    assert m["misread_of"] == "3350112"
    # NOT on the fabricated list — diagnostic tier matters.
    assert not raw.get("_dim_fabricated")


def test_misread_kills_the_value_for_money():
    """The value nulls on raw even though we call it a typo — a
    misread cannot feed money any more than a fabrication can."""
    raw = _misread_raw()
    _null_unverified_quotes(raw)
    assert raw["walls"][0]["width_ft"] is None


def test_misread_records_page_coverage():
    """Coverage rides on the misread record too so the card can
    weigh diagnosis with the same instrument as fabrication."""
    raw = _misread_raw()
    _null_unverified_quotes(raw)
    m = raw["_dim_misread"][0]
    assert m["page_ocr_chars"] == 4200
    assert m["evidence_strength"] == "strong"


def test_misread_seam_accounts_the_removal():
    raw = _misread_raw()
    _null_unverified_quotes(raw)
    led = raw.get("_seam_ledger") or {}
    assert "dims_misread" in led
    assert led["dims_misread"]["removed"] == 1


def test_misread_rides_readback_and_rail_loud():
    raw = _misread_raw()
    _null_unverified_quotes(raw)
    rb = build_blueprint_readback(raw)
    assert rb.get("dim_misread")
    codes = {r["code"]: r for r in rb["rail"]}
    assert "dims_misread" in codes
    assert codes["dims_misread"]["level"] == "loud"
    # The rail text names the REAL string OCR found.
    assert "3350112" in codes["dims_misread"]["text"]


# ---------- (C) OCR-coverage weighting on FABRICATED ----------------

def _fabricated_page(coverage_chars: int):
    """A fabricated miss (no misread_of) with an explicit page
    coverage character count for the weighting."""
    return {
        "walls": [{"label": "back", "width_ft": 9.5}],
        "_dim_evidence": {
            "walls.back.width_ft": {
                "v": 9.5, "page": 2, "from": "9'-6\""},
        },
        "_ocr_quote_misses": [{
            "path": "walls.back.width_ft",
            "page": 2,
            "from": "9'-6\"",
            "rotations_checked": True,
            "reason": "quote norm not present in OCR on page",
            "page_ocr_chars": coverage_chars,
        }],
    }


def test_fabricated_high_coverage_is_strong_evidence():
    """A page OCR read densely (thousands of char-normalised tokens)
    with NO hit is strong evidence of fabrication."""
    raw = _fabricated_page(4200)
    _null_unverified_quotes(raw)
    fab = raw.get("_dim_fabricated") or []
    assert len(fab) == 1
    r = fab[0]
    assert r["evidence_strength"] == "strong"
    assert r["page_ocr_chars"] == 4200


def test_fabricated_low_coverage_is_weak_evidence():
    """A page OCR could barely read (<=300 char-normalised tokens —
    stacked fractions, low contrast) with NO hit is WEAK evidence:
    the miss may be OCR's fault, not the model's. Same instrument,
    different confidence."""
    raw = _fabricated_page(90)
    _null_unverified_quotes(raw)
    fab = raw.get("_dim_fabricated") or []
    assert fab[0]["evidence_strength"] == "weak"
    assert fab[0]["page_ocr_chars"] == 90


def test_fabricated_rail_badges_strength_per_path():
    raw = _fabricated_page(4200)
    _null_unverified_quotes(raw)
    rb = build_blueprint_readback(raw)
    codes = {r["code"]: r for r in rb["rail"]}
    assert "dims_fabricated" in codes
    # Rail text carries the [strong]/[weak] badge next to the path.
    assert "[strong]" in codes["dims_fabricated"]["text"]


def test_unverified_untouched_by_coverage_and_misread_tiers():
    """A path whose miss reason is 'no anchor' / 'not near feature'
    stays UNVERIFIED — coverage weighting and misread scanning are
    for the FABRICATED family only."""
    raw = {
        "walls": [{"label": "front", "width_ft": 58.0}],
        "_dim_evidence": {
            "walls.front.width_ft": {
                "v": 58.0, "page": 3, "from": "58'-0\""},
        },
        "_ocr_quote_misses": [{
            "path": "walls.front.width_ft",
            "page": 3,
            "from": "58'-0\"",
            "rotations_checked": True,
            "reason": "quote matched but no candidate within 900px of "
                      "feature anchor ['FRONT']",
            "page_ocr_chars": 4200,
        }],
    }
    _null_unverified_quotes(raw)
    unv = raw.get("_dim_unverified") or []
    assert len(unv) == 1
    assert unv[0]["path"] == "walls.front.width_ft"
    # No coverage badge on the unverified record — coverage weighs
    # fabrication, not proximity refusal.
    assert "evidence_strength" not in unv[0]
    assert not raw.get("_dim_fabricated")
    assert not raw.get("_dim_misread")
