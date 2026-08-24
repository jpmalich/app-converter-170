"""SEND-124 pins (Howard ruled 2026-08-24) — the material-claim split,
the pct gate, and the printed-only lanes joining the DIM discipline.

ITEM 1 — THE SORT: a field that CHANGES QUANTITY gates
(siding_pct_this_wall — an unverified 85 silently removes ~15% of a
wall); fields that only ROUTE a category (profile callouts,
stone_callout's label) go to the human confirmation card, ungated.
ITEM 2 — the five printed-only lanes are DIM-schema'd while their
surface is empty: a bare number nulls as no-evidence (the accepted
risk); a quoted DIM gets located or nulls.
ITEM 3 — the fixture-figure registry coupling lives in
test_send123_prompt_purity (the set grows with the seals).
"""
import sys

sys.path.insert(0, "/app/backend")

from routes.ai_blueprint import (  # noqa: E402
    _gate_siding_pct,
    _enforce_evidence_or_null,
    _aggregate_to_hover_shape,
    check_read_consistency,
)


def _ocr(pages):
    return {str(i + 1): t for i, t in enumerate(pages)}


class TestSidingPctGate:
    def test_unverified_pct_reverts_to_100_named(self):
        raw = {"walls": [
            {"label": "back", "siding_pct_this_wall": 85,
             "stone_callout": "STONE WATERTABLE"},
            {"label": "front", "siding_pct_this_wall": 100}],
            "_ocr_text_by_page": _ocr(["NOTHING RELEVANT PRINTED"])}
        _gate_siding_pct(raw)
        assert raw["walls"][0]["siding_pct_this_wall"] == 100
        g = raw["_siding_pct_gated"][0]
        assert g["label"] == "back" and g["claimed_pct"] == 85
        assert "siding_pct_gated_no_evidence" in (raw.get("_seam_ledger") or {})

    def test_located_callout_lets_pct_stand(self):
        raw = {"walls": [
            {"label": "back", "siding_pct_this_wall": 85,
             "stone_callout": "STONE WATERTABLE"}],
            "_ocr_text_by_page": _ocr(["... STONE WATERTABLE TO 36 ..."])}
        _gate_siding_pct(raw)
        assert raw["walls"][0]["siding_pct_this_wall"] == 85
        assert "_siding_pct_gated" not in raw

    def test_fraction_form_gates_too(self):
        raw = {"walls": [{"label": "left", "siding_pct_this_wall": 0.85}],
               "_ocr_text_by_page": _ocr(["INK"])}
        _gate_siding_pct(raw)
        assert raw["walls"][0]["siding_pct_this_wall"] == 100
        assert raw["_siding_pct_gated"][0]["claimed_pct"] == 85

    def test_category_callouts_are_never_gated(self):
        # the sort: routing fields go to the card, not the gate — a
        # VINYL body claim survives the pass untouched.
        raw = {"walls": [{"label": "front", "siding_pct_this_wall": 100,
                          "wall_body_profile_callout": "VINYL"}],
               "_ocr_text_by_page": _ocr(["INK"])}
        _gate_siding_pct(raw)
        assert raw["walls"][0]["wall_body_profile_callout"] == "VINYL"


class TestMaterialConfirmationCard:
    def test_card_carries_claim_face_and_sqft(self):
        raw = {"walls": [
            {"label": "front", "width_ft": 30, "height_ft": 10,
             "wall_body_profile_callout": "VINYL",
             "siding_pct_this_wall": 100}],
            "openings": [], "avg_wall_height_ft": 10.0, "story_count": 1}
        m = _aggregate_to_hover_shape(raw)
        card = m["_material_claims"]
        assert any(c["face"] == "front" and c["claim"] == "VINYL"
                   and c["field"] == "wall_body_profile_callout"
                   for c in card)
        vinyl = [c for c in card if c["claim"] == "VINYL"][0]
        assert (vinyl["sqft_at_stake"] or 0) > 0

    def test_flag_groups_all_claims(self):
        raw = {"walls": [
            {"label": "back", "wall_body_profile_callout": "SYNTHETIC STONE AS SPECIFIED",
             "stone_callout": "STONE WATERTABLE"}],
            "_siding_pct_gated": [{"label": "back", "claimed_pct": 85.0}]}
        flags = {f["code"]: f for f in check_read_consistency(raw)}
        f = flags["material_claims_unconfirmed"]
        assert f["vars"]["count"] == 3
        assert "SYNTHETIC STONE" in f["vars"]["claims"]
        assert "85% \u2192 100" in f["vars"]["claims"]

    def test_no_claims_no_flag(self):
        raw = {"walls": [{"label": "front"}]}
        codes = [f["code"] for f in check_read_consistency(raw)]
        assert "material_claims_unconfirmed" not in codes


class TestPrintedOnlyLanesDim:
    def test_bare_number_nulls_as_no_evidence(self):
        raw = {"soffit_sqft": 240.0, "drip_edge_lf": 180.0}
        _enforce_evidence_or_null(raw)
        assert raw["soffit_sqft"] is None
        assert raw["drip_edge_lf"] is None
        nulled = raw.get("_nulled_no_evidence") or []
        assert "soffit_sqft" in nulled and "drip_edge_lf" in nulled

    def test_quoted_dim_survives_with_evidence(self):
        raw = {"total_trim_sqft": {"v": 62.0, "page": 3,
                                   "from": "TRIM: 62 SF"}}
        _enforce_evidence_or_null(raw)
        assert raw["total_trim_sqft"] == 62.0
        assert "total_trim_sqft" in (raw.get("_dim_evidence") or {})

    def test_absent_lane_stays_null_silently(self):
        raw = {"level_frieze_lf": None}
        _enforce_evidence_or_null(raw)
        assert raw["level_frieze_lf"] is None
        assert "level_frieze_lf" not in (raw.get("_nulled_no_evidence") or [])

    def test_rail_copy_exists_en_and_es(self):
        txt = open("/app/frontend/src/lib/dictionaries.js",
                   encoding="utf-8").read()
        assert txt.count('"bp.rb.consistency.material_claims_unconfirmed"') == 2
