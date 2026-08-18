"""SEND-47 pins — the HEIGHT BUILD wired into the live derivation.

Sealed DP-1 (FIRST FLOOR → plate/soffit from the face's own elevation),
Standing Prohibition structural (band containment), refusals name the
exact gap, model heights demoted to hypothesis (may be shown, may never
feed a quantity), no-OCR runs disclosed not silently model-fed, DP-5
overall-rail admission positional with strict closure, and the live
outcomes for Boni + Letrick pinned as observations of the accepted
SEND-46 census (never tuned toward).
"""
import os
import sys

import pytest

sys.path.insert(0, "/app/backend")

from height_read import apply_height_build, derive_face_heights
import measure_staging as staging


def _run(raw, w=1.0, h=1.5, x=10.0, y=10.0):
    return {"raw": raw, "norm": raw,
            "loc": {"x_pct": x, "y_pct": y, "w_pct": w, "h_pct": h}}


def _label(raw, y, x=8.0):
    return _run(raw, w=6.0, h=1.0, x=x, y=y)


def _rail(raw, y, x=6.0):
    # tall-thin box → VERTICAL axis
    return _run(raw, w=0.8, h=2.2, x=x, y=y)


def _page(runs):
    return {"runs": runs}


def _front_rear_page(front_runs, rear_runs=()):
    return _page([_label("FRONT ELEVATION", 46.0, x=30.0),
                  _label("REAR ELEVATION", 92.0, x=30.0),
                  *front_runs, *rear_runs])


class TestDP1Derivation:
    def test_single_bound_gap_derives(self):
        ot = {"1": _front_rear_page([
            _label("TOP OF PLATE", 20.0),
            _rail("9'-1\"", 25.0),
            _label("FIRST FLOOR", 30.0)])}
        r = derive_face_heights(ot)["front"]
        assert r["status"] == "DERIVED"
        assert r["ft"] == round(109 / 12.0, 2)
        assert "TOP_OF_PLATE" in r["span"] and "FIRST_FLOOR" in r["span"]

    def test_undimensioned_gap_refuses_named(self):
        ot = {"1": _front_rear_page([
            _label("TOP OF PLATE", 20.0),
            _label("FIRST FLOOR", 30.0)])}
        r = derive_face_heights(ot)["front"]
        assert r["status"] == "REFUSED"
        assert "UNDIMENSIONED" in r["refusal"]
        assert "TOP_OF_PLATE" in r["refusal"] and "FIRST_FLOOR" in r["refusal"]
        assert "area not derivable" in r["refusal"]

    def test_contested_gap_refuses_naming_both_rails(self):
        ot = {"1": _front_rear_page([
            _label("TOP OF PLATE", 20.0),
            _rail("9'-1\"", 25.0, x=6.0),
            _rail("9'-11\"", 25.0, x=60.0),
            _label("FIRST FLOOR", 30.0)])}
        r = derive_face_heights(ot)["front"]
        assert r["status"] == "REFUSED"
        assert "CONTESTED" in r["refusal"]
        assert "9'-1" in r["refusal"] and "9'-11" in r["refusal"]

    def test_missing_datum_refuses_named(self):
        ot = {"1": _front_rear_page([_label("TOP OF PLATE", 20.0)])}
        r = derive_face_heights(ot)["front"]
        assert "no FIRST FLOOR datum located" in r["refusal"]

    def test_rail_touching_datum_line_is_not_in_the_gap(self):
        # a glyph box overlapping the plate line is AT the datum
        ot = {"1": _front_rear_page([
            _label("TOP OF PLATE", 20.0),
            _rail("19'-11\"", 20.2),
            _rail("9'-1\"", 25.0),
            _label("FIRST FLOOR", 30.0)])}
        r = derive_face_heights(ot)["front"]
        assert r["status"] == "DERIVED" and r["ft"] == round(109 / 12.0, 2)


class TestStandingProhibition:
    def test_rear_never_borrows_the_front_rail(self):
        # identical datums on rear, rail ONLY in the front band
        ot = {"1": _front_rear_page(
            [_label("TOP OF PLATE", 20.0), _rail("9'-1\"", 25.0),
             _label("FIRST FLOOR", 30.0)],
            [_label("TOP OF PLATE", 60.0), _label("FIRST FLOOR", 75.0)])}
        faces = derive_face_heights(ot)
        assert faces["front"]["status"] == "DERIVED"
        assert faces["rear"]["status"] == "REFUSED"
        assert "UNDIMENSIONED" in faces["rear"]["refusal"]

    def test_face_with_no_drawing_refuses(self):
        ot = {"1": _front_rear_page([])}
        faces = derive_face_heights(ot)
        assert "no left elevation drawing located" in faces["left"]["refusal"]


class TestDP5OverallRail:
    def test_straddling_overall_rail_closes_undimensioned_strip(self):
        # plate --8'-1(97)-- SECOND FLOOR --(undimensioned)-- FIRST FLOOR
        # overall rail 18'-1(217) straddles the SECOND FLOOR line
        ot = {"1": _front_rear_page([
            _label("TOP OF PLATE", 16.0),
            _rail("8'-1\"", 20.0),
            _label("SECOND FLOOR", 24.0),
            _rail("18'-1\"", 23.5, x=60.0),
            _label("FIRST FLOOR", 34.0)])}
        r = derive_face_heights(ot)["front"]
        assert r["status"] == "DERIVED" and r["inches"] == 217
        assert "overall rail" in r["chain"][0]
        assert "residual 120" in r["chain"][0]

    def test_all_bound_span_demands_residual_zero(self):
        ot = {"1": _front_rear_page([
            _label("TOP OF PLATE", 16.0),
            _rail("8'-1\"", 20.0),
            _label("SECOND FLOOR", 24.0),
            _rail("9'-1\"", 28.0),
            _rail("18'-1\"", 23.5, x=60.0),   # 217 ≠ 97 + 109 = 206
            _label("FIRST FLOOR", 34.0)])}
        r = derive_face_heights(ot)["front"]
        assert r["status"] == "REFUSED"
        assert "does not close" in r["refusal"]
        assert "residual 11" in r["refusal"]


class TestModelDemotion:
    def _walls(self):
        return [{"label": "front", "width_ft": 40.0, "height_ft": 20.0}]

    def test_model_height_becomes_hypothesis_and_derived_governs(self):
        raw = {"_ocr_text_by_page": {"1": _front_rear_page([
            _label("TOP OF PLATE", 20.0), _rail("9'-1\"", 25.0),
            _label("FIRST FLOOR", 30.0)])}}
        walls = self._walls()
        hb = apply_height_build(raw, walls)
        assert hb["status"] == "APPLIED" and hb["model_heights_demoted"]
        assert walls[0]["height_ft"] == round(109 / 12.0, 2)
        assert walls[0]["_model_height_hypothesis_ft"] == 20.0
        assert walls[0]["height_src"] == "height_build"

    def test_refused_face_never_falls_back_to_the_model_height(self):
        raw = {"_ocr_text_by_page": {"1": _front_rear_page([
            _label("TOP OF PLATE", 20.0), _label("FIRST FLOOR", 30.0)])}}
        walls = self._walls()
        apply_height_build(raw, walls)
        assert walls[0]["height_ft"] is None
        assert "UNDIMENSIONED" in walls[0]["height_refusal_reason"]
        walk = staging.walk_walls(walls)
        assert walk["siding_sqft"] == 0.0
        nd = walk["faces_not_derivable"]
        assert nd and "UNDIMENSIONED" in nd[0]["reason"]

    def test_model_segments_are_hypothesis_even_when_face_derives(self):
        raw = {"_ocr_text_by_page": {"1": _front_rear_page([
            _label("TOP OF PLATE", 20.0), _rail("9'-1\"", 25.0),
            _label("FIRST FLOOR", 30.0)])}}
        walls = [{"label": "front", "width_ft": 40.0, "height_ft": 20.0,
                  "height_segments": [
                      {"label": "garage wing", "width_ft": 20.0,
                       "height_ft": 10.0}]}]
        apply_height_build(raw, walls)
        assert walls[0]["height_ft"] is None
        assert "segment x-extents" in walls[0]["height_refusal_reason"]
        seg = walls[0]["height_segments"][0]
        assert seg["height_ft"] is None
        assert seg["_model_height_hypothesis_ft"] == 10.0

    def test_no_ocr_is_disclosed_not_silently_model_fed(self):
        raw = {}
        walls = self._walls()
        hb = apply_height_build(raw, walls)
        assert hb["status"] == "NOT_RUN"
        assert "UNVERIFIED" in hb["reason"]
        assert walls[0]["height_ft"] == 20.0  # untouched, and SAID so
        assert raw["_height_build"]["status"] == "NOT_RUN"


class TestLiveOutcomes:
    """Observation pins of the accepted SEND-46 census against the
    stored runs — never tuned toward. Skip when the datastore is absent."""

    @pytest.fixture(scope="class")
    def live(self):
        try:
            from pymongo import MongoClient
            from dotenv import load_dotenv
            load_dotenv("/app/backend/.env")
            db = MongoClient(os.environ["MONGO_URL"],
                             serverSelectionTimeoutMS=2000)[os.environ["DB_NAME"]]
            out = {}
            for house, eid in (
                    ("boni", "65bcb89d-8291-4b84-920c-7b503273f332"),
                    ("letrick", "264b6230-5d0f-49ea-b07d-8d33a537f293")):
                r = db.ai_blueprint_runs.find_one(
                    {"estimate_id": eid, "status": "done"},
                    sort=[("created_at", -1)])
                if not r:
                    pytest.skip(f"{house} run not in datastore")
                out[house] = r["result"]["raw_ai"]["_ocr_text_by_page"]
            return out
        except Exception as e:  # pragma: no cover
            pytest.skip(f"datastore unavailable: {e}")

    def test_letrick_three_faces_derive_from_their_own_drawings(self, live):
        faces = derive_face_heights(live["letrick"])
        for f in ("front", "left", "right"):
            assert faces[f]["status"] == "DERIVED", faces[f]
            assert faces[f]["ft"] == round(109 / 12.0, 2)
        assert faces["rear"]["status"] == "REFUSED"
        assert "CONTESTED" in faces["rear"]["refusal"]

    def test_boni_faces_refuse_with_named_reasons(self, live):
        faces = derive_face_heights(live["boni"])
        assert all(r["status"] == "REFUSED" for r in faces.values())
        # p3 (section sheet) prints a second FRONT ELEVATION title — a
        # SEND-47 finding awaiting Howard's ruling; the face refuses with
        # both pages named rather than picking one.
        assert "multiple front elevation drawings located" in faces["front"]["refusal"]
        assert "UNDIMENSIONED" in faces["rear"]["refusal"]
        assert "CONTESTED" in faces["left"]["refusal"]
        assert "no FIRST FLOOR datum located" in faces["right"]["refusal"]
