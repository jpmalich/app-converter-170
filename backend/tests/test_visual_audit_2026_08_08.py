"""VISUAL AUDIT — SAME BUILD AS EVIDENCE-OR-NULL (Howard ruled 2026-08-08):

"IT IS NOT A SECOND FEATURE. Evidence-or-null already requires every
dimension to carry its page and source location. VISUAL AUDIT IS THE
DISPLAY OF THAT FIELD. One schema, one renderer. Built separately, the
first build discards the coordinates the second one needs and we pay
for the read twice."

Three design requirements, ruled before build:
1. The highlight is APPROXIMATE on a scan (vision-returned pixels,
   labelled so — never a tight box implying precision we do not have);
   EXACT only when located in a native PDF's text layer.
2. Derived numbers carry MANY highlights plus the arithmetic (srcs[] +
   calc) — one-to-one gets torn up immediately.
3. A number with NO SOURCE displays as such — a first-class state,
   rendered as clearly as a highlight.
"""
from __future__ import annotations

import io
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routes.ai_blueprint import (  # noqa: E402
    SYSTEM_PROMPT, _enforce_evidence_or_null, _exact_locate_evidence,
    _norm_loc, _pdf_rect_to_pct, _probe_pdf_source,
    build_blueprint_readback,
)

DICT_TEXT = (Path(__file__).resolve().parents[2]
             / "frontend/src/lib/dictionaries.js").read_text(encoding="utf-8")


def _dim(v, page=3, frm="printed", loc=None):
    d = {"v": v, "page": page, "from": frm}
    if loc is not None:
        d["loc"] = loc
    return d


# ---- schema: loc rides, junk dies, a box never rescues a missing quote ----

def test_a_valid_loc_rides_through_with_the_evidence():
    loc = {"x_pct": 12.5, "y_pct": 40, "w_pct": 6, "h_pct": 2}
    out = _enforce_evidence_or_null(
        {"walls": [{"label": "front", "width_ft": _dim(58, 2, "58'-0\"", loc)}]})
    assert out["_dim_evidence"]["walls.front.width_ft"]["loc"] == {
        "x_pct": 12.5, "y_pct": 40.0, "w_pct": 6.0, "h_pct": 2.0}


def test_junk_locs_are_nulled_not_ridden():
    assert _norm_loc({"x_pct": 12, "y_pct": 40, "w_pct": 6}) is None
    assert _norm_loc({"x_pct": 120, "y_pct": 40, "w_pct": 6, "h_pct": 2}) is None
    assert _norm_loc({"x_pct": 12, "y_pct": 40, "w_pct": 0, "h_pct": 2}) is None
    assert _norm_loc({"x_pct": "a", "y_pct": 40, "w_pct": 6, "h_pct": 2}) is None
    assert _norm_loc(None) is None


def test_a_box_never_rescues_a_missing_quote():
    out = _enforce_evidence_or_null(
        {"eave_overhang_in": {"v": 12, "page": 4, "from": "",
                              "loc": {"x_pct": 1, "y_pct": 1, "w_pct": 1, "h_pct": 1}}})
    assert out["eave_overhang_in"] is None
    assert out["_nulled_no_evidence"] == ["eave_overhang_in"]


# ---- design req 2: derived values — many highlights plus the arithmetic ----

def test_derived_value_carries_srcs_and_calc():
    """Howard's 20'-0 1/4" corner stacks from three plate dimensions —
    the schema supports many highlights plus the arithmetic."""
    raw = {"outside_corner_heights_ft": [{
        "v": 20.02,
        "calc": "9'-11 1/8\" + 1'-0\" + 8'-1 1/8\" + 11 1/2\"",
        "srcs": [
            {"page": 3, "from": "9'-11 1/8\"",
             "loc": {"x_pct": 10, "y_pct": 20, "w_pct": 5, "h_pct": 1.5}},
            {"page": 3, "from": "1'-0\""},
            {"page": 4, "from": "8'-1 1/8\""},
        ]}]}
    out = _enforce_evidence_or_null(raw)
    assert out["outside_corner_heights_ft"] == [20.02]
    ev = out["_dim_evidence"]["corner_heights.0"]
    assert len(ev["srcs"]) == 3
    assert ev["calc"].startswith("9'-11 1/8\"")
    assert ev["srcs"][0]["loc"]["x_pct"] == 10.0
    assert ev["srcs"][1]["loc"] is None


def test_derived_value_with_no_quoted_srcs_is_as_dead_as_a_bare_number():
    out = _enforce_evidence_or_null(
        {"eave_overhang_in": {"v": 12, "srcs": [{"page": 3, "from": ""}]}})
    assert out["eave_overhang_in"] is None
    assert out["_nulled_no_evidence"] == ["eave_overhang_in"]


# ---- design req 3: no source is a first-class state ----

def test_unread_dims_are_named_not_omitted():
    out = _enforce_evidence_or_null(
        {"eave_overhang_in": None,
         "walls": [{"label": "back",
                    "width_ft": _dim(58, 2, "58'-0\""),
                    "height_ft": None}]})
    assert set(out["_dim_unread"]) == {"eave_overhang_in",
                                       "walls.back.height_ft"}
    assert "_nulled_no_evidence" not in out


def test_readback_evidence_block_holds_all_three_states():
    raw = _enforce_evidence_or_null(
        {"walls": [{"label": "front",
                    "width_ft": _dim(58, 2, "58'-0\""),
                    "height_ft": 19}],       # bare — dropped
         "eave_overhang_in": None,           # abstained — unread
         "roof_planes": [], "outside_corner_heights_ft": [],
         "gutter_runs": [], "windows": []})
    rb = build_blueprint_readback(raw)
    ev = rb["evidence"]
    assert [i["path"] for i in ev["items"]] == ["walls.front.width_ft"]
    assert ev["items"][0]["from"] == "58'-0\""
    assert ev["dropped"] == ["walls.front.height_ft"]
    assert "eave_overhang_in" in ev["unread"]


# ---- design req 1: precision labelling ----

def test_pdf_rect_to_pct_converts_bottom_left_origin_to_top_left():
    # 612x792 letter page, rect at l=61.2, b=712.8, r=122.4, t=752.4
    loc = _pdf_rect_to_pct((61.2, 712.8, 122.4, 752.4), 612, 792)
    assert loc == {"x_pct": 10.0, "y_pct": 5.0, "w_pct": 10.0, "h_pct": 5.0}
    assert _pdf_rect_to_pct((0, 0, 10, 10), 0, 792) is None


def test_scan_boxes_stay_approximate_and_quote_only_stays_unlocated():
    ev = {"walls.front.width_ft": {
              "v": 58, "page": 1, "from": "58'-0\"",
              "loc": {"x_pct": 10, "y_pct": 20, "w_pct": 5, "h_pct": 2}},
          "eave_overhang_in": {"v": 12, "page": 2, "from": "1'-0\"",
                               "loc": None}}
    _exact_locate_evidence(ev, [{"name": "nope.jpg", "kind": "image"}],
                           {"kind": "image_scans"})
    assert ev["walls.front.width_ft"]["precision"] == "approximate"
    assert ev["eave_overhang_in"]["precision"] is None


def test_native_pdf_text_layer_yields_an_exact_box():
    from reportlab.pdfgen import canvas
    from config import UPLOAD_DIR
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(612, 792))
    c.drawString(100, 750, "ELEVATION SHEET A-3 — SCALE 1/4 IN = 1 FT")
    c.drawString(100, 700, "58'-0")
    c.save()
    pdf_bytes = buf.getvalue()
    probe, _texts = _probe_pdf_source(pdf_bytes)
    assert probe["kind"] == "native_text"
    name = f"bpsrc_test_{uuid.uuid4().hex}.pdf"
    target = UPLOAD_DIR / name
    target.write_bytes(pdf_bytes)
    try:
        ev = {"walls.front.width_ft": {"v": 58, "page": 1, "from": "58'-0",
                                       "loc": None}}
        _exact_locate_evidence(ev, [{"name": name, "kind": "pdf"}], probe)
        e = ev["walls.front.width_ft"]
        assert e["precision"] == "exact", "text-layer hit must label EXACT"
        assert e["loc"] is not None
        assert 10 < e["loc"]["x_pct"] < 25       # x=100/612 ≈ 16.3%
        assert 5 < e["loc"]["y_pct"] < 20        # y=700 near the top
        # a string the page does not hold never invents a box
        ev2 = {"eave_overhang_in": {"v": 12, "page": 1,
                                    "from": "NOT ON THIS PAGE", "loc": None}}
        _exact_locate_evidence(ev2, [{"name": name, "kind": "pdf"}], probe)
        assert ev2["eave_overhang_in"]["precision"] is None
        assert ev2["eave_overhang_in"]["loc"] is None
    finally:
        target.unlink(missing_ok=True)


def test_a_missing_source_file_never_sinks_anything():
    ev = {"walls.front.width_ft": {"v": 58, "page": 1, "from": "58'-0",
                                   "loc": None}}
    _exact_locate_evidence(ev, [{"name": "bpsrc_gone.pdf", "kind": "pdf"}],
                           {"kind": "native_text"})
    assert ev["walls.front.width_ft"]["precision"] is None


# ---- contract pins ----

def test_prompt_carries_the_visual_audit_contract():
    for must in ('"loc": {"x_pct"', "DERIVED VALUES", '"srcs":',
                 "quote to justify a box"):
        assert must in SYSTEM_PROMPT, f"prompt lost the contract: {must!r}"


def test_audit_strings_exist_in_both_languages():
    for key in ("bp.va.title", "bp.va.approx", "bp.va.exact", "bp.va.noloc",
                "bp.va.calc", "bp.va.page", "bp.va.dropped", "bp.va.unread",
                "bp.va.none"):
        assert DICT_TEXT.count(f'"{key}"') == 2, f"{key} must exist EN+ES"
    assert "APPROXIMATE LOCATION" in DICT_TEXT
    assert "UBICACIÓN APROXIMADA" in DICT_TEXT
