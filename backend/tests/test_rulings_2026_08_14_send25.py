"""SEND-25 RULING REGISTER (Howard sealed 2026-08-14). Ruling WORDS verbatim
in the docstrings; every ruling pinned the moment it was made (Ruling C
register discipline). Order was mandated: EE → GG → FF (report only).

RULING EE — WIRE DD INTO THE LIVE DERIVATION.
  "A face that fails closure is NOT DERIVABLE and blocks the gate.
  Report-loud-but-still-derives is rejected — it means RIGHT keeps pricing
  against a check that says it cannot be closed, which is the exact silent
  number Ruling EE exists to stop. But DO NOT NULL THE WIDTH AT SOURCE:
  (1) it conflates 'wall width not read' with 'read, footprint does not
  close' — nulling makes the second wear the first one's label; (2) it
  erases its own evidence — DD's failing relation names the 39, null the
  width and the next run names a different relation; (3) it trips a sealed
  rule — an instrument that kills good data is a defect of equal urgency to
  one that passes bad data. Build it through the Ruling J Quantity path: the
  face's quantity carries status NOT_DERIVABLE with reason 'footprint does
  not close: <failing relation>', naming the relation verbatim; the read
  value is retained on the record as the failing input, not discarded.
  gates.quote_gate_blockers reads DD. Acceptance on EST-713272: RIGHT
  refuses and the surface says 'footprint does not close — right depth 39
  present but opposing left depth not read.' It must NOT say 'wall width not
  read.'"

RULING GG — PERSIST OCR TEXT WITH PAGE + PER-STRING POSITION.
  "Persist ALL runs. No per-page N cap. Positions as percent-of-page
  (resolution-independent — absolute pixels die on a re-raster at a
  different DPI). Store the page's own dims alongside so a highlight renders
  back. Store both norm and raw — the tuple is (norm, raw, bbox) and all
  three persist. raw is what a contractor sees printed and is the only
  version worth quoting; norm is only what matching uses. Do not solve the
  size problem by truncating: if the run doc approaches the limit, move OCR
  to its own collection keyed by run id. If truncation ever does happen it
  is loud and specific — names which pages and how many runs were dropped —
  and any evidence lookup that could have hit a dropped run returns
  UNVERIFIED, not NOT LOCATED."

INT-KEY WRITE GUARD.
  "Recursive key coercion at the single Mongo write boundary, not
  field-by-field. GG makes it mandatory — OCR persistence is page-keyed, the
  same shape that nulled run 2. RECORD WHEN THE COERCION FIRES so an
  int-keyed dict cannot enter the result forever without anyone knowing."
"""
import asyncio
import sys

import bson
import pytest

sys.path.insert(0, "/app/backend")

from footprint_checks import footprint_closure  # noqa: E402
import measure_staging as staging  # noqa: E402
from profile_callouts import breakdown_walls_by_profile  # noqa: E402
import gates  # noqa: E402
import routes.ai_blueprint as bp  # noqa: E402


# ── Boni-like footprint: right depth 30+9=39 (segments), left depth unread ──
def _boni_footprint():
    return {"walls": [
        {"label": "front", "width_ft": 58.0, "height_ft": 20.0,
         "height_segments": [
             {"label": "main", "width_ft": 34.0, "height_ft": 20.0},
             {"label": "garage", "width_ft": 24.0, "height_ft": 10.0}]},
        {"label": "back", "width_ft": 58.0, "height_ft": 20.0},
        {"label": "left", "height_ft": 20.0},              # depth not read
        {"label": "right", "width_ft": None, "height_ft": 20.0,
         "gable_triangle_height_ft": 8.0,
         "height_segments": [
             {"label": "main body 2-story", "width_ft": 30.0, "height_ft": 20.0},
             {"label": "bonus room section", "width_ft": 9.0, "height_ft": 10.0}]},
    ]}


# ── RULING EE ──

def test_ee_refused_faces_name_the_failing_relation_verbatim():
    fp = footprint_closure(_boni_footprint())
    refused = fp["refused_faces"]
    assert "right" in refused
    reason = refused["right"]
    # Names the relation verbatim, prefixed "footprint does not close:".
    assert reason.startswith("footprint does not close:")
    assert "right depth 39 present but opposing left depth not read" in reason
    # It must NOT wear the "width not read" label (Ruling EE point 1).
    assert "wall width not read" not in reason


def test_ee_walk_refuses_the_face_and_never_prices_it():
    fp = footprint_closure(_boni_footprint())
    walls = _boni_footprint()["walls"]
    refused = fp["refused_faces"]
    walk = staging.walk_walls(walls, refused_faces=refused)
    nd = walk["faces_not_derivable"]
    right = [f for f in nd if str(f.get("label")).lower() == "right"]
    assert right, "RIGHT must be named NOT DERIVABLE"
    assert right[0]["surface"] == "footprint_closure"
    assert "footprint does not close" in right[0]["reason"]
    assert "wall width not read" not in right[0]["reason"]
    # No RIGHT face detail carries priced area — the face refuses whole.
    right_detail = [d for d in walk["detail"]
                    if str(d.get("label")).lower() == "right"]
    assert right_detail and right_detail[0].get("refused") is True


def test_ee_read_width_is_retained_on_the_record_not_nulled():
    # DO NOT NULL THE WIDTH AT SOURCE — the wall dict keeps its read value.
    walls = _boni_footprint()["walls"]
    right_segs_before = [s.get("width_ft") for s in walls[3]["height_segments"]]
    fp = footprint_closure({"walls": walls})
    staging.walk_walls(walls, refused_faces=fp["refused_faces"])
    breakdown_walls_by_profile(walls, refused_faces=fp["refused_faces"])
    right_segs_after = [s.get("width_ft") for s in walls[3]["height_segments"]]
    assert right_segs_before == right_segs_after == [30.0, 9.0]


def test_ee_breakdown_excludes_refused_face_from_per_profile():
    walls = _boni_footprint()["walls"]
    fp = footprint_closure({"walls": walls})
    bd = breakdown_walls_by_profile(walls, refused_faces=fp["refused_faces"])
    refused_rows = [e for e in bd["per_elevation"]
                    if e.get("refused") and e["label"] == "right"]
    assert refused_rows and refused_rows[0]["wall_body_sqft"] is None
    named = [f for f in bd["faces_not_derivable"]
             if f.get("surface") == "footprint_closure" and f["elevation"] == "right"]
    assert named and "footprint does not close" in named[0]["reason"]


def test_ee_gate_blocks_when_footprint_does_not_close():
    fp = footprint_closure(_boni_footprint())
    est = {"lines": [], "kind": "siding"}
    blockers = gates.quote_gate_blockers(est, {"_footprint_closure": fp})
    fdc = [b for b in blockers if b["code"] == "footprint_does_not_close"]
    assert fdc and fdc[0]["blocking"] is True
    assert "right" in fdc[0]["refused_faces"]
    assert any("cannot be closed" in r for r in fdc[0]["failing_relations"])


def test_ee_clean_footprint_never_fires_the_mechanism():
    # Control: a closing rectangle refuses nothing and blocks nothing.
    clean = {"walls": [
        {"label": "front", "width_ft": 40.0, "height_ft": 9.0},
        {"label": "back", "width_ft": 40.0, "height_ft": 9.0},
        {"label": "left", "width_ft": 30.0, "height_ft": 9.0},
        {"label": "right", "width_ft": 30.0, "height_ft": 9.0}]}
    fp = footprint_closure(clean)
    assert fp["closes"] is True and fp["refused_faces"] == {}
    walk = staging.walk_walls(clean["walls"], refused_faces=fp["refused_faces"])
    assert not any(f.get("surface") == "footprint_closure"
                   for f in walk["faces_not_derivable"])
    blockers = gates.quote_gate_blockers({"lines": [], "kind": "siding"},
                                         {"_footprint_closure": fp})
    assert not any(b["code"] == "footprint_does_not_close" for b in blockers)


# ── RULING GG + INT-KEY WRITE GUARD ──

def test_int_key_guard_coerces_recursively_and_records_every_fire():
    fired = []
    src = {"a": {11: {"b": 3}}, "runs": [{7: "x"}], "ok": 1}
    out = bp._coerce_bson_keys(src, "result", fired)
    # Every key is a string now → bson-encodable (boundary has teeth).
    bson.BSON.encode(out)
    assert out["a"]["11"]["b"] == 3 and out["runs"][0]["7"] == "x"
    # Every fire is recorded with a path — the int source is NAMED.
    assert any("11" in f for f in fired) and any("7" in f for f in fired)


def test_int_key_guard_leaves_string_keys_untouched_no_false_fire():
    fired = []
    src = {"measurements": {"_run_id": "r1"}, "by_page": {"3": {"runs": []}}}
    out = bp._coerce_bson_keys(src, "result", fired)
    assert fired == [] and out == src


def test_gg_int_page_key_would_crash_without_the_guard():
    # BOUNDARY HAS TEETH (mirrors the send-11 int-key pin): a genuinely
    # int-keyed page dict raises the production error, and the guard clears it.
    int_keyed = {"by_page": {11: {"runs": []}}}
    with pytest.raises(Exception):
        bson.BSON.encode(int_keyed)
    fixed = bp._coerce_bson_keys(int_keyed, "result", [])
    bson.BSON.encode(fixed)  # no raise


class _FakeColl:
    def __init__(self):
        self.calls = []

    async def replace_one(self, flt, doc, upsert=False):
        self.calls.append((flt, doc, upsert))


class _FakeDB:
    def __init__(self):
        self.ai_blueprint_ocr = _FakeColl()


def _small_blob():
    return {"1": {"page_w": 1000, "page_h": 800,
                  "runs": [{"norm": "240", "raw": "24'-0\"",
                            "loc": {"x_pct": 10.0, "y_pct": 20.0,
                                    "w_pct": 5.0, "h_pct": 2.0}}]}}


def test_gg_small_ocr_blob_stays_on_the_run_doc():
    raw = {"_ocr_text_by_page": _small_blob()}
    asyncio.run(bp._persist_ocr_text("run-small", raw))
    # Stays on the run doc; the pointer names where it lives.
    assert raw.get("_ocr_text_by_page")
    assert raw["_ocr_text_ref"]["where"] == "run_doc"
    # Percent boxes + page dims + both norm & raw persist.
    run = raw["_ocr_text_by_page"]["1"]["runs"][0]
    assert run["raw"] == "24'-0\"" and run["norm"] == "240"
    assert set(run["loc"]) == {"x_pct", "y_pct", "w_pct", "h_pct"}


def test_gg_large_ocr_blob_moves_to_its_own_collection(monkeypatch):
    # Force the on-doc threshold tiny so the escape hatch fires; supply a
    # fake db so the separate-collection write is observable.
    fake = _FakeDB()
    monkeypatch.setattr(bp, "db", fake)
    monkeypatch.setattr(bp, "_OCR_ONDOC_MAX_BYTES", 10)
    raw = {"_ocr_text_by_page": _small_blob()}
    asyncio.run(bp._persist_ocr_text("run-big", raw))
    # Moved OFF the run doc, pointer names the separate collection.
    assert "_ocr_text_by_page" not in raw
    assert raw["_ocr_text_ref"]["where"] == "ai_blueprint_ocr"
    assert raw["_ocr_text_ref"]["run_id"] == "run-big"
    assert fake.ai_blueprint_ocr.calls, "OCR must be written to its own collection"
    flt, doc, upsert = fake.ai_blueprint_ocr.calls[0]
    assert flt == {"run_id": "run-big"} and upsert is True
    bson.BSON.encode(doc)  # the separate doc is BSON-clean
