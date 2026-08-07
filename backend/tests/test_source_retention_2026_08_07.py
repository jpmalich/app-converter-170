"""SOURCE-RETENTION RULING (Howard, 2026-08-07).

"THE ORIGINAL UPLOAD IS RETAINED. Always, every door, every file type.
A derived artifact never replaces its source."

Named defect: the blueprint door was rasterizing every PDF at the door and
THROWING AWAY THE SOURCE — every job ever run was reduced to
vision-on-images regardless of what the file actually held.

Pins:
1. PDF upload → original bytes retained byte-identical (disk + blob),
   `source_files` stamped on the run doc, native-text probe recorded.
2. Image-sheet upload → ORIGINAL bytes retained (not the compressed copy).
3. Rerun carries `source_files` / `source_probe` forward.
4. Probe classification: native export (text layer) vs scan (pictures-only).
   Printed dim strings survive into the text ground truth verbatim.
5. temperature=0 pinned on extraction runs (ruled 2026-08-07) — and it
   NEVER satisfies the determinism gate: agreement is not correctness.
   The card's source line says vision-read when vision is all there is.
6. Chunked blob store: originals above Mongo's 16 MB doc cap round-trip.
"""
from __future__ import annotations
from creds_for_tests import TEST_PASSWORD

import inspect
import io
import os
import sys
import unittest
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api_base import BASE_URL

ADMIN_EMAIL = "hhunt6677@yahoo.com"
ADMIN_PASSWORD = TEST_PASSWORD


# --------------------------------------------------------------------------
# Unit pins — probe + temperature + readback source line
# --------------------------------------------------------------------------

def _native_pdf_bytes() -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 700, "FRONT ELEVATION  WINDOW 3-0x5-0 SH")
    c.drawString(100, 680, "EAVE OVERHANG 16 IN  FASCIA 1x6")
    c.showPage()
    c.drawString(100, 700, "FLOOR PLAN 42'-6\" x 28'-0\"")
    c.showPage()
    c.save()
    return buf.getvalue()


def _scan_pdf_bytes() -> bytes:
    """Image-only PDF — exactly what a scanner/camera export produces.
    PIL writes the page as one embedded image, no text layer."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 300), (250, 250, 245))
    img.save(buf, format="PDF")
    return buf.getvalue()


def test_probe_native_pdf_reads_text_ground_truth():
    from routes.ai_blueprint import _probe_pdf_source
    probe, texts = _probe_pdf_source(_native_pdf_bytes())
    assert probe["kind"] == "native_text", probe
    assert probe["page_count"] == 2
    assert probe["text_pages"] == 2
    # Printed dim strings survive VERBATIM — never snapped, never lost.
    joined = "\n".join(texts)
    assert "3-0x5-0" in joined
    assert "SH" in joined
    assert "16 IN" in joined


def test_probe_scan_pdf_is_named_a_scan():
    from routes.ai_blueprint import _probe_pdf_source
    probe, texts = _probe_pdf_source(_scan_pdf_bytes())
    assert probe["kind"] == "scan", probe
    assert probe["text_pages"] == 0
    assert all(not t for t in texts)


def test_temperature_zero_pinned_on_extraction():
    """Ruled 2026-08-07: temp=0 on extraction runs. The pin also demands
    the docstring/comment names the limit — greedy sampling never
    satisfies the determinism gate and never claims correctness."""
    from routes.ai_blueprint import _claude_direct_blueprint
    src = inspect.getsource(_claude_direct_blueprint)
    assert "temperature=0.0" in src
    assert "determinism" in src.lower()


def test_readback_carries_source_line():
    """The card must distinguish 'two reads agreed' from 'matches the
    printed dimension' — the source block names what the numbers stand
    on. Scan/image sources say vision-read, in the dictionary strings."""
    from routes.ai_blueprint import _with_readback
    result = {"raw_ai": {"walls": [], "roof_planes": []}}
    enriched = _with_readback(result, source_probe={
        "kind": "scan", "text_pages": 0, "page_count": 3, "pages": []})
    rb = enriched.get("readback")
    assert rb is not None
    assert rb["source"] == {"kind": "scan", "text_pages": 0, "page_count": 3}
    # No probe → no source claim invented.
    bare = _with_readback({"raw_ai": {"walls": []}})
    assert "source" not in (bare.get("readback") or {})


def test_vision_only_sources_say_so_in_both_languages():
    dict_src = Path(__file__).resolve().parents[2] / "frontend/src/lib/dictionaries.js"
    text = dict_src.read_text(encoding="utf-8")
    for key in ("bp.rb.source.native", "bp.rb.source.mixed",
                "bp.rb.source.scan", "bp.rb.source.images"):
        assert text.count(f'"{key}"') == 2, f"{key} must exist in EN and ES"
    assert "vision read" in text
    assert "lectura de visión" in text


# --------------------------------------------------------------------------
# Chunked blob store — originals above the 16 MB Mongo doc cap survive
# --------------------------------------------------------------------------

class ChunkedBlobTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("MONGO_URL"):
            raise unittest.SkipTest("MONGO_URL not set")

    async def asyncSetUp(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        import upload_store
        self._client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        self._orig_db = upload_store.db
        upload_store.db = self._client[os.environ.get("DB_NAME") or "vinyl_estimator"]
        self.db = upload_store.db

    async def asyncTearDown(self):
        import upload_store
        await self.db["upload_blobs"].delete_many(
            {"name": {"$regex": "^TEST_chunk_"}})
        upload_store.db = self._orig_db
        self._client.close()

    async def test_20mb_original_round_trips(self):
        from upload_store import save_blob, load_blob, CHUNK_BYTES
        data = os.urandom(CHUNK_BYTES + 3_000_000)  # forces 2 chunks
        assert await save_blob("TEST_chunk_big.pdf", data, "application/pdf")
        got = await load_blob("TEST_chunk_big.pdf")
        assert got is not None
        blob, ctype = got
        assert blob == data, "chunked original must reassemble byte-identical"
        assert ctype == "application/pdf"
        parent = await self.db["upload_blobs"].find_one({"name": "TEST_chunk_big.pdf"})
        assert parent["chunks"] == 2 and parent["size"] == len(data)

    async def test_small_blob_path_unchanged(self):
        from upload_store import save_blob, load_blob
        data = b"tiny-original"
        assert await save_blob("TEST_chunk_small.bin", data, "application/x-t")
        got = await load_blob("TEST_chunk_small.bin")
        assert got == (data, "application/x-t")


# --------------------------------------------------------------------------
# HTTP pins — the door retains what walked in
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json().get("token") or r.json().get("access_token")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


@pytest.fixture(scope="module")
def estimate_id(session):
    r = session.post(f"{BASE_URL}/api/estimates",
                     json={"customer_name": "TEST_source_retention",
                           "address": "TEST_source_retention"},
                     timeout=15)
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    yield eid
    session.delete(f"{BASE_URL}/api/estimates/{eid}", timeout=15)
    from pymongo import MongoClient
    client = MongoClient(os.environ["MONGO_URL"])
    mdb = client[os.environ["DB_NAME"]]
    for run in mdb.ai_blueprint_runs.find({"estimate_id": eid}):
        for sf in run.get("source_files") or []:
            mdb.upload_blobs.delete_many({"name": {"$regex": f"^{sf['name']}"}})
    mdb.ai_blueprint_runs.delete_many({"estimate_id": eid})
    client.close()


def _run_doc(run_id):
    from pymongo import MongoClient
    client = MongoClient(os.environ["MONGO_URL"])
    doc = client[os.environ["DB_NAME"]].ai_blueprint_runs.find_one({"run_id": run_id})
    client.close()
    return doc


def test_pdf_original_retained_byte_identical(session, estimate_id):
    pdf = _native_pdf_bytes()
    r = session.post(
        f"{BASE_URL}/api/measure/ai-blueprint",
        files={"file": ("boni_test.pdf", pdf, "application/pdf")},
        data={"address": "TEST_source_retention", "max_pages": "2",
              "estimate_id": estimate_id},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    probe = body.get("source_probe")
    assert probe and probe["kind"] == "native_text", probe

    doc = _run_doc(body["run_id"])
    assert doc is not None
    sf = doc.get("source_files") or []
    assert len(sf) == 1 and sf[0]["kind"] == "pdf"
    assert sf[0]["bytes"] == len(pdf)
    assert sf[0]["uploaded_as"] == "boni_test.pdf"
    # Text ground truth stored on the run doc, dims verbatim.
    joined = "\n".join(doc.get("source_text_pages") or [])
    assert "3-0x5-0" in joined
    # Byte-identical serve of the ORIGINAL — not a render of it.
    served = session.get(f"{BASE_URL}/api/uploads/{sf[0]['name']}", timeout=15)
    assert served.status_code == 200
    assert served.content == pdf, "the retained source must be byte-identical"
    pytest._src_retention_run_id = body["run_id"]
    pytest._src_retention_files = sf


def test_rerun_carries_the_source_forward(session):
    run_id = getattr(pytest, "_src_retention_run_id", None)
    assert run_id, "PDF retention test didn't run"
    r = session.post(f"{BASE_URL}/api/measure/ai-blueprint/rerun/{run_id}",
                     json={}, timeout=60)
    assert r.status_code == 200, r.text
    new_doc = _run_doc(r.json()["run_id"])
    assert new_doc is not None
    assert new_doc.get("source_files") == pytest._src_retention_files
    assert (new_doc.get("source_probe") or {}).get("kind") == "native_text"


def test_image_sheets_retain_original_not_compressed(session, estimate_id):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (640, 480), (240, 235, 230)).save(buf, format="JPEG", quality=95)
    jpg = buf.getvalue()
    r = session.post(
        f"{BASE_URL}/api/measure/ai-blueprint",
        files=[("files", ("sheet1.jpg", jpg, "image/jpeg"))],
        data={"address": "TEST_source_retention", "estimate_id": estimate_id},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body.get("source_probe") or {}).get("kind") == "image_scans"
    doc = _run_doc(body["run_id"])
    sf = doc.get("source_files") or []
    assert len(sf) == 1 and sf[0]["kind"] == "image"
    served = session.get(f"{BASE_URL}/api/uploads/{sf[0]['name']}", timeout=15)
    assert served.status_code == 200
    assert served.content == jpg, (
        "the ORIGINAL sheet must be retained — the compressed Claude copy "
        "never replaces its source")


def test_status_endpoint_surfaces_the_probe(session):
    run_id = getattr(pytest, "_src_retention_run_id", None)
    assert run_id, "PDF retention test didn't run"
    r = session.get(f"{BASE_URL}/api/measure/ai-blueprint/status/{run_id}",
                    timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body.get("source_probe") or {}).get("kind") == "native_text"
    assert body.get("source_files"), "status must name the retained source"
