from creds_for_tests import TEST_PASSWORD
"""Ruled 2026-07-14 — audience wording split for the 3D snapshot verify note.

Pins:
  1. API: PUT /model3d-snapshot persists `model3d_unverified` (true/false).
  2. Customer surfaces (quote email/PDF builder, dictionaries, QuoteModal 3D
     block) use HOMEOWNER language ("on-site verification") and NEVER
     internal flag vocabulary (amber / unconfirmed / field-verify).
  3. Contractor surface (HouseModel3D panel) KEEPS the precise internal
     language as-is.
"""
import os
import re
import uuid

import requests
from dotenv import dotenv_values

_ENV = dotenv_values("/app/backend/.env")
_FE_ENV = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _FE_ENV.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = _ENV.get("ADMIN_EMAIL", "hhunt6677@yahoo.com")
ADMIN_PASSWORD = _ENV.get("ADMIN_PASSWORD", TEST_PASSWORD)

FE = "/app/frontend/src"
INTERNAL_VOCAB = ("amber", "unconfirmed", "field-verify", "field verify", "unratified")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


def test_unverified_flag_persists_and_resets():
    s = _session()
    r = s.post(f"{API}/estimates", json={"customer_name": "Wording Split Test"}, timeout=15)
    assert r.status_code == 200, r.text
    est_id = r.json()["id"]
    try:
        url = f"/api/uploads/{uuid.uuid4().hex}.png"
        r1 = s.put(f"{API}/estimates/{est_id}/model3d-snapshot",
                   json={"url": url, "unverified": True}, timeout=15)
        assert r1.status_code == 200, r1.text
        assert r1.json()["model3d_unverified"] is True
        est = s.get(f"{API}/estimates/{est_id}", timeout=15).json()
        assert est["model3d_unverified"] is True
        # re-capture after ratification clears the flag (omitted → default False)
        r2 = s.put(f"{API}/estimates/{est_id}/model3d-snapshot",
                   json={"url": url}, timeout=15)
        assert r2.status_code == 200 and r2.json()["model3d_unverified"] is False
        est = s.get(f"{API}/estimates/{est_id}", timeout=15).json()
        assert est["model3d_unverified"] is False
    finally:
        s.delete(f"{API}/estimates/{est_id}", timeout=15)


def test_customer_email_builder_uses_homeowner_language_only():
    src = _read(f"{FE}/lib/emailQuote.js")
    # PIN AMENDED (quote visual NONE, ruled 2026-07-20): the 3D block is
    # gone from the quote builder — the wording-split rule now asserts
    # only that no internal vocabulary leaks anywhere in the builder.
    assert "model3d_png_url" not in src
    low = src.lower()
    for term in INTERNAL_VOCAB:
        assert term not in low, f"internal vocab {term!r} leaked into customer email builder"


def test_dictionaries_homeowner_wording_en_es():
    src = _read(f"{FE}/lib/dictionaries.js")
    assert "Some details are subject to on-site verification." in src
    assert "Algunos detalles están sujetos a verificación en el sitio." in src
    # every email.* customer string stays free of internal vocabulary
    for m in re.finditer(r'"email\.[^"]+":\s*"([^"]*)"', src):
        val = m.group(1).lower()
        for term in INTERNAL_VOCAB:
            assert term not in val, f"internal vocab {term!r} in customer dictionary string: {m.group(0)[:80]}"


def test_quote_modal_3d_block_homeowner_wording():
    """PIN AMENDED (quote visual NONE, ruled 2026-07-20): the QuoteModal 3D
    block was removed — the on-screen quote preview ships with no picture,
    mirroring the email. Absence pinned; wording rule is moot for a block
    that no longer exists."""
    src = _read(f"{FE}/components/QuoteModal.jsx")
    assert "quote-3d-model-block" not in src
    assert "model3d_png_url" not in src


def test_contractor_surface_keeps_internal_language():
    src = _read(f"{FE}/components/estimate/HouseModel3D.jsx")
    # the contractor panel keeps the precise internal terms — pinned so a
    # future "soften everything" pass can't erase contractor precision
    assert "Unconfirmed" in src
    assert "field-verify" in src
    assert "assumed, not measured" in src
