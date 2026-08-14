"""INT PAGE KEYS MUST NOT REACH THE PERSIST WRITE (regression 2026-08-14).

THE BUG (Boni fresh read on EST-713272): the run errored with
"AI blueprint read failed: documents must have only string keys, key was
11". Boni is an 11-page set. SEND-11 item 3 added a per-page OCR-coverage
breadcrumb, `page_ocr_chars`, keyed by page NUMBER (an int), and wrote it
onto `raw["_ocr_page_coverage_chars"]`. That raw is stored inside the run
`result`, so the run's persist write (`ai_blueprint_runs.update_one($set:
{result: ...})`) hands Mongo a document with an int key — which Mongo
refuses on ANY multi-page read, not just eleven.

WHY IT SHIPPED BROKEN — the gap Howard named: no test ran a full blueprint
read THROUGH the persistence boundary. The OCR-locate structures are only
produced when `_ocr_locate_evidence` runs over real page rasters, and the
persist is a real Mongo write; nothing fed a raw carrying the int-keyed
coverage dict to a real encode. So every change to that path shipped
unverified at exactly the point where this failed — the same shape as the
drag-vs-click gap (a test exercising something other than what happens).

THIS PIN closes it at the boundary: it runs the ACTUAL
`_ocr_locate_evidence` over synthetic page rasters (an 11-page set, so the
key `11` is really produced), then BSON-encodes the run result the way the
persist write does. RED before the fix (int key → encode raises), GREEN
after (keys stringified at the write edge).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import bson
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes.ai_blueprint as ab  # noqa: E402


def _blank_png(w=300, h=200):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def _locate_with_pages(n_pages: int, quote_page: int):
    """Run the real OCR-locate over n blank pages with one unfindable
    quote on quote_page — forces the coverage breadcrumb to be written."""
    imgs = [_blank_png() for _ in range(n_pages)]
    raw = {"sheets_identified": []}
    ev = {"walls.left.width_ft":
          {"v": 39.0, "page": quote_page, "from": "39'-0\"", "loc": None}}
    ab._ocr_locate_evidence(ev, imgs, raw)
    return raw


def test_coverage_breadcrumb_has_only_string_keys_after_a_real_locate():
    raw = _locate_with_pages(11, 11)          # Boni's 11-page set, page 11
    cov = raw.get("_ocr_page_coverage_chars")
    assert cov, "the SEND-11 coverage breadcrumb was expected to be written"
    assert all(isinstance(k, str) for k in cov), \
        f"page keys must be strings for Mongo, got {[type(k).__name__ for k in cov]}"


def test_run_result_carrying_coverage_survives_the_persist_write():
    """THE PIN THAT PERSISTS: encode the run result exactly as
    `ai_blueprint_runs.update_one($set={'result': result})` hands it to
    Mongo. An int page key makes this raise — which is the production
    failure — so a green encode is the whole point."""
    raw = _locate_with_pages(11, 11)
    result = {"raw_ai": raw, "measurements": {}, "lines": []}
    # bson.encode is exactly what pymongo runs on the write.
    bson.encode({"status": "done", "result": result})


def test_the_bug_is_not_eleven_specific_any_page_number_is_persisted_as_a_string():
    """Howard: an int key fails on EVERY write, not on eleven. A single
    early page must persist as a string too."""
    raw = _locate_with_pages(2, 2)
    cov = raw.get("_ocr_page_coverage_chars")
    assert cov and set(cov) == {"2"}, f"expected string key '2', got {cov}"
    bson.encode({"result": {"raw_ai": raw}})


def test_mongo_really_rejects_an_int_key_so_the_boundary_pin_has_teeth():
    """Document that the persist boundary is what enforces the rule — an
    int page key raises the exact production error — so the green pins
    above are meaningful, not vacuous."""
    with pytest.raises(Exception) as ei:
        bson.encode({"result": {"raw_ai": {"_ocr_page_coverage_chars": {11: 0}}}})
    assert "string keys" in str(ei.value)
