"""EMERGENT OBJECT STORAGE — the durable home for UPLOADED FILES.

SEND-142 (Howard authorised 2026-08-28, MINIMUM SCOPE): the three upload
doors — job photos (`routes/uploads.py`), hover PDFs (`routes/hover.py`),
the supplier logo (`routes/branding.py`) — wrote the contractor's file to
the POD's OWN DISK. In preview that survives; on a deployed app the pod is
replaced and the file is gone. A photo on the pod disk is evidence that
can vanish, and every refusal and every measured gable on that photo
stands on it.

WHAT THIS MODULE IS AND IS NOT:
  · it stores and returns BYTES. No quantity, no price, no estimate write.
  · nothing here decides anything — a caller that cannot store a file
    RAISES, and the door above it refuses NAMED. There is no silent
    success and no placeholder file.
  · reads stay behind our own endpoints (the platform mints no presigned
    URLs), so the serve path, its magic-byte sniffing and its
    Content-Type discipline (SEC-003) are untouched.

Paths are prefixed `pro-quote/` so the app owns its own namespace.
"""
from __future__ import annotations

import asyncio
import logging
import os

import requests

logger = logging.getLogger(__name__)

APP_PREFIX = "pro-quote"
_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() \
    or "https://integrations.emergentagent.com"
STORAGE_URL = _BASE.rstrip("/") + "/objstore/api/v1/storage"

_storage_key: str | None = None


def init_storage(force: bool = False) -> str:
    """Mint (once) the session-scoped storage key."""
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY missing — object storage unavailable")
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": key}, timeout=30)
    r.raise_for_status()
    _storage_key = r.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    r = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": init_storage(), "Content-Type": content_type},
        data=data, timeout=120,
    )
    if r.status_code == 404:                      # dead session key — mint once, retry once
        r = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": init_storage(force=True),
                     "Content-Type": content_type},
            data=data, timeout=120,
        )
    r.raise_for_status()
    return r.json()


def get_object(path: str) -> tuple[bytes, str] | None:
    """Bytes + content-type, or None when the object is not there.

    Not-there is an ANSWER, not an error: a file uploaded before this
    send lives on the old disk path and the caller falls back to it.
    """
    r = requests.get(f"{STORAGE_URL}/objects/{path}",
                     headers={"X-Storage-Key": init_storage()}, timeout=60)
    if r.status_code == 404:
        r2 = requests.get(f"{STORAGE_URL}/objects/{path}",
                          headers={"X-Storage-Key": init_storage(force=True)},
                          timeout=60)
        if r2.status_code == 404:
            return None
        r = r2
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")


def upload_path(name: str) -> str:
    return f"{APP_PREFIX}/uploads/{name}"


def hover_pdf_path(run_id: str) -> str:
    return f"{APP_PREFIX}/hover_pdfs/{run_id}.pdf"


async def aput(path: str, data: bytes, content_type: str) -> dict:
    return await asyncio.to_thread(put_object, path, data, content_type)


async def aget(path: str) -> tuple[bytes, str] | None:
    try:
        return await asyncio.to_thread(get_object, path)
    except Exception as exc:                     # transport/proxy trouble
        logger.warning("object storage read failed for %s: %s", path, exc)
        return None
