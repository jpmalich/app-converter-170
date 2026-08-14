"""EVIDENCE OR NULL — STRUCTURAL (Howard ruled 2026-08-08, TOP ITEM,
above the determinism gate).

"The model wrote 10.0' where the drawing holds no number. That is not
getting it wrong. THAT IS HAVING NO WAY TO SAY 'I DO NOT KNOW.' …
Abstention must not be something the model chooses. It must be
something the schema enforces. Same shape as the source-retention
ruling: do not ask the model to behave, make the wrong behaviour
unrepresentable."

Pins:
1. An evidenced dim ({"v", "page", "from"}) passes through as a plain
   number and its evidence is stamped on the read.
2. A BARE NUMBER is nulled by construction and recorded.
3. An object WITHOUT its "from" quote is nulled the same way.
4. null stays null (abstention is a first-class answer).
5. The nulling cascades: an unevidenced garage-section height nulls →
   wall_segment_undimensioned fires → the math holds the rectangle.
6. The card NAMES every dropped path (rail: dims_nulled_no_evidence,
   loud, EN+ES).
7. The prompt makes the contract explicit and the enforcement sits at
   the pipeline seam, before anything downstream sees a number.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from measure_staging import wall_body_gross_sqft  # noqa: E402
from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _enforce_evidence_or_null, build_blueprint_readback,
    check_read_consistency,
)


def _dim(v, page=3, frm="printed"):
    return {"v": v, "page": page, "from": frm}


def test_evidenced_dims_pass_through_with_their_provenance():
    raw = {"walls": [{"label": "front",
                      "width_ft": _dim(58, 2, "58'-0\""),
                      "height_ft": _dim(20.5, 3, "9'-11 1/8\" + 1'-0\" + 8'-1 1/8\" + 11 1/2\" plate stack")}],
           "eave_overhang_in": _dim(12, 4, "1'-0\""),
           "outside_corner_heights_ft": [_dim(20.5, 3, "20'-6\""), None]}
    out = _enforce_evidence_or_null(raw)
    w = out["walls"][0]
    assert w["width_ft"] == 58.0 and w["height_ft"] == 20.5
    assert out["eave_overhang_in"] == 12.0
    assert out["outside_corner_heights_ft"] == [20.5, None]
    ev = out["_dim_evidence"]
    assert ev["walls.front.width_ft"] == {"v": 58.0, "page": 2,
                                          "from": "58'-0\"", "loc": None}
    assert "corner_heights.0" in ev
    assert "_nulled_no_evidence" not in out


def test_a_bare_number_is_nulled_by_construction():
    raw = {"walls": [{"label": "back", "width_ft": 58,
                      "height_ft": _dim(20.5, 3, "plate stack")}],
           "fascia_width_in": 6}
    out = _enforce_evidence_or_null(raw)
    assert out["walls"][0]["width_ft"] is None, \
        "a number with no evidence must be UNREPRESENTABLE"
    assert out["fascia_width_in"] is None
    assert set(out["_nulled_no_evidence"]) == {"walls.back.width_ft",
                                               "fascia_width_in"}


def test_an_object_without_its_quote_is_nulled_too():
    raw = {"eave_overhang_in": {"v": 12, "page": 4, "from": ""}}
    out = _enforce_evidence_or_null(raw)
    assert out["eave_overhang_in"] is None
    assert out["_nulled_no_evidence"] == ["eave_overhang_in"]


def test_null_stays_null_without_accusation():
    out = _enforce_evidence_or_null({"eave_overhang_in": None,
                                     "walls": [{"label": "left",
                                                "width_ft": None,
                                                "height_ft": None}]})
    assert "_nulled_no_evidence" not in out, \
        "abstention is a first-class answer, not a violation"


def test_the_back_garage_case_cascades_to_the_flag():
    """The exact failure Howard graded: an undimensioned back garage
    section. Under evidence-or-null a guessed 14.4 (bare) NULLS, the
    section flag fires, and the math holds the rectangle."""
    raw = {"walls": [{"label": "back",
                      "width_ft": _dim(58, 2, "58'-0\""),
                      "height_ft": _dim(20.5, 3, "plate stack"),
                      "height_segments": [
                          {"label": "main body",
                           "width_ft": _dim(34, 3, "34'-0\""),
                           "height_ft": _dim(20.5, 3, "plate stack")},
                          {"label": "garage wing",
                           "width_ft": _dim(24, 3, "24'-0\""),
                           "height_ft": 14.4},  # bare — no printed string
                      ]}],
           "roof_planes": [], "outside_corner_heights_ft": [],
           "footprint_area_sqft": 1800, "gutter_runs": [], "windows": []}
    out = _enforce_evidence_or_null(raw)
    seg = out["walls"][0]["height_segments"][1]
    assert seg["height_ft"] is None
    assert "walls.back.segments.garage wing.height_ft" in out["_nulled_no_evidence"]
    flags = check_read_consistency(out)
    f = next(x for x in flags if x["code"] == "wall_segment_undimensioned")
    assert f["vars"]["section"] == "garage wing"
    gross, segs, deriv = wall_body_gross_sqft(out["walls"][0])
    # SEND-13: the math reports the DERIVABLE segment (main body) and
    # names the garage wing not-derivable — it never inflates to the
    # full 58×20.5 rectangle to cover the missing height.
    assert gross == 34 * 20.5 and segs == [(34.0, 20.5)], \
        "the math reports the subset, never guesses"
    assert deriv["subset"] is True
    assert deriv["not_derivable"][0]["label"] == "garage wing"


def test_the_card_names_every_dropped_path():
    raw = {"walls": [{"label": "front", "width_ft": 58, "height_ft": 19}],
           "roof_planes": [], "outside_corner_heights_ft": [],
           "gutter_runs": [], "windows": []}
    out = _enforce_evidence_or_null(raw)
    rb = build_blueprint_readback(out)
    f = next(x for x in rb["rail"] if x["code"] == "dims_nulled_no_evidence")
    assert f["level"] == "loud"
    assert "walls.front.width_ft" in f["text"]
    assert "walls.front.height_ft" in f["text"]


def test_prompt_makes_abstention_first_class():
    for must in ('{"v": number, "page": <1-based sheet number>, "from":',
                 "DROPPED BY THE",
                 "first-class answer",
                 "unrepresentable"):
        assert must in SYSTEM_PROMPT, f"prompt lost the contract: {must!r}"


def test_enforcement_sits_at_the_pipeline_seam():
    src = Path(__file__).resolve().parents[1].joinpath(
        "routes/ai_blueprint.py").read_text()
    seam = src.index("raw = _enforce_evidence_or_null(raw)")
    agg = src.index("measurements = _aggregate_to_hover_shape(raw, annotations=annotations)")
    assert seam < agg, "enforcement must run before anything downstream sees a number"


def test_flag_strings_exist_in_both_languages():
    text = (Path(__file__).resolve().parents[2]
            / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")
    assert text.count('"bp.rb.rail.dims_nulled_no_evidence"') == 2
