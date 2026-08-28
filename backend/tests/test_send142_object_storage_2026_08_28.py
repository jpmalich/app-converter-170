"""SEND-142 STORAGE PINS — AN UPLOADED FILE DOES NOT LIVE ON THE POD
(Howard authorised 2026-08-28, MINIMUM SCOPE).

  Move these three paths to Emergent object storage:
    routes/uploads.py     job photos
    routes/hover.py       hover PDFs
    routes/branding.py    supplier logo
  Same files come back on read. No quantity change. No price change.
  No hover/photo lane split. Own pins. Full green handback.

The rule these pins hold: **the contractor's own file is never written to
the pod's disk, and a store that fails REFUSES BY NAME** — it never hands
back a URL with nothing behind it. Reads are unchanged: the same
`/api/uploads/{name}` door, the same magic-byte sniffing, the same
Content-Type discipline (SEC-003), plus the legacy disk read so a file
uploaded before this send still opens.
"""
import pathlib
import uuid

BACKEND = pathlib.Path("/app/backend")
UPLOADS = (BACKEND / "routes" / "uploads.py").read_text()
HOVER = (BACKEND / "routes" / "hover.py").read_text()
BRANDING = (BACKEND / "routes" / "branding.py").read_text()
STORAGE = (BACKEND / "object_storage.py").read_text()


# ---------------------------------------------------------------------------
# 1. THE POD DISK IS NOT A HOME FOR AN UPLOAD
# ---------------------------------------------------------------------------
def test_no_upload_door_writes_the_file_to_the_pod_disk():
    for name, src in (("uploads.py", UPLOADS), ("hover.py", HOVER),
                      ("branding.py", BRANDING)):
        for bad in ('open(dest, "wb")', 'open(pdf_path, "wb")',
                    'uploads", "hover_pdfs"'):
            assert bad not in src, f"{name}: {bad} — the pod disk is back"


def test_every_door_stores_through_the_one_module():
    assert "await aput(upload_path(name), content, sniffed)" in UPLOADS
    assert "await aput(upload_path(name), content, ctype)" in BRANDING
    assert "await aput(pdf_object, raw" in HOVER
    assert "hover_pdf_path(run_id)" in HOVER


def test_the_paths_are_app_prefixed_and_carry_no_leading_slash():
    from object_storage import APP_PREFIX, hover_pdf_path, upload_path
    p1, p2 = upload_path("abc.png"), hover_pdf_path("deadbeef")
    for p in (p1, p2):
        assert p.startswith(f"{APP_PREFIX}/") and not p.startswith("/")
    assert p1 == "pro-quote/uploads/abc.png"
    assert p2 == "pro-quote/hover_pdfs/deadbeef.pdf"


# ---------------------------------------------------------------------------
# 2. A FAILED STORE IS A NAMED REFUSAL, NEVER A URL OVER NOTHING
# ---------------------------------------------------------------------------
def test_a_failed_store_refuses_and_says_the_file_was_not_saved():
    assert "the photo was NOT saved" in UPLOADS
    assert "branding was NOT changed" in BRANDING
    assert "the import was NOT" in HOVER
    for src in (UPLOADS, BRANDING, HOVER):
        assert "status_code=502" in src


def test_the_store_raises_rather_than_pretending():
    """No placeholder, no empty object, no 'best effort' success."""
    assert "raise RuntimeError" in STORAGE
    assert "r.raise_for_status()" in STORAGE
    for bad in ("except Exception:\n        return True", "pass  # ignore"):
        assert bad not in STORAGE


# ---------------------------------------------------------------------------
# 3. THE READ DID NOT CHANGE, AND YESTERDAY'S FILE STILL OPENS
# ---------------------------------------------------------------------------
def test_the_serve_door_reads_storage_and_keeps_the_legacy_disk_read():
    assert "await aget(upload_path(name))" in UPLOADS
    assert "if target.exists():" in UPLOADS          # legacy disk file
    assert "load_blob(name)" in UPLOADS              # mongo backing store
    # SEC-003 discipline untouched: the content type still comes from the
    # bytes, never from what was declared at upload time.
    assert "_safe_content_type_for_serve(data, name)" in UPLOADS
    assert 'headers["X-Content-Type-Options"] = "nosniff"' in UPLOADS


def test_the_original_upload_is_still_retained_in_mongo():
    """SOURCE-RETENTION ruling (2026-08-07) survives the move: the
    original is retained at every door."""
    assert "save_blob(name, content, sniffed)" in UPLOADS
    assert "save_blob(name, content, ctype)" in BRANDING


def test_a_hover_run_from_before_the_move_still_reads():
    assert 'doc.get("pdf_object")' in HOVER
    assert 'legacy = doc.get("pdf_path")' in HOVER
    assert "re-upload the Hover" in HOVER            # the same refusal


# ---------------------------------------------------------------------------
# 4. STORAGE DECIDES NOTHING — NO QUANTITY, NO MONEY
# ---------------------------------------------------------------------------
def test_the_storage_module_touches_no_quantity_and_no_money():
    for banned in ("sqft", "total_sell", "unit_price", "margin", "lines",
                   "estimates", "measurements", "qty"):
        assert banned not in STORAGE, f"storage module reaches {banned}"


# ---------------------------------------------------------------------------
# 5. LIVE — THE BYTES GO OUT AND COME BACK THE SAME
# ---------------------------------------------------------------------------
def test_live_round_trip_returns_the_same_bytes():
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
    import object_storage as store
    path = f"{store.APP_PREFIX}/_pins/{uuid.uuid4().hex}.png"
    payload = b"\x89PNG\r\n\x1a\n" + b"evidence-or-null"
    store.put_object(path, payload, "image/png")
    got = store.get_object(path)
    assert got is not None, "the object did not come back"
    assert got[0] == payload
    assert got[1].startswith("image/png")
