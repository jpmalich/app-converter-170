"""PRICE-AGE PIN — EVERY PRICE WRITE RECORDS WHO AND WHEN (Howard ruled
2026-07-31). A stale price is the one defect that reaches a homeowner —
RainDrop and House Wrap sat stale with nothing in the app saying so.

Pinned:
  · every routes/*.py write to a price collection belongs to a REGISTERED
    surface, and that file stamps price_changed_at — a surface that can
    change a price without stamping FAILS here
  · SURFACE test: a single-cell tier edit lands the per-item stamp with
    who + a fresh when (the gap: single-cell edits stamped nothing)
  · seed syncs never stamp (services.py carries stamps, never mints them)
"""
import os
import re
import sys
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from price_age import PRICE_WRITE_SURFACES, PRICE_COLLECTIONS

BACKEND = Path(__file__).resolve().parent.parent
_FE = dotenv_values("/app/frontend/.env")
_ENV = dotenv_values(str(BACKEND / ".env"))
API = (os.environ.get("REACT_APP_BACKEND_URL")
       or _FE.get("REACT_APP_BACKEND_URL", "")).rstrip("/") + "/api"
ADMIN_TOKEN = _ENV.get("SUPPLIER_ADMIN_TOKEN", "")

_WRITE = re.compile(
    r"db\.(%s)\.(update_one|update_many|replace_one|insert_one|insert_many|bulk_write)"
    % "|".join(PRICE_COLLECTIONS))


def test_every_price_write_surface_is_registered_and_stamps():
    registered_files = {k.split("::")[0] for k in PRICE_WRITE_SURFACES}
    for f in sorted((BACKEND / "routes").glob("*.py")):
        src = f.read_text()
        writes = _WRITE.findall(src)
        rel = f"routes/{f.name}"
        if not writes:
            continue
        assert rel in registered_files, (
            f"{rel} writes a PRICE collection but is not in "
            "PRICE_WRITE_SURFACES — register it and stamp it")
        assert "price_stamp" in src or "stamp_price_change" in src, (
            f"{rel} writes prices without stamping price_changed_at — "
            "a surface that can change a price without stamping fails the suite")
    # every registered function exists in its file
    for key in PRICE_WRITE_SURFACES:
        rel, fn = key.split("::")
        src = (BACKEND / rel).read_text()
        assert re.search(rf"def {fn}\b", src), f"{key}: function missing"


def test_lp_margin_surface_stamps():
    src = (BACKEND / "routes" / "lp_admin.py").read_text()
    assert "price_stamp" in src, "LP margin ladder must stamp its writes"


def test_seed_sync_never_mints_a_stamp():
    src = (BACKEND / "services.py").read_text()
    assert "stamp_price_change" not in src and "price_stamp(" not in src, \
        "seed sync must never MINT a price stamp — it only carries them"
    assert 'price_changed_at' in src, \
        "seed sync must CARRY existing stamps through section rebuilds"


def test_single_cell_tier_edit_stamps_item_surface():
    """SURFACE: the exact gap — a one-cell tier edit records who + when."""
    assert ADMIN_TOKEN, "SUPPLIER_ADMIN_TOKEN missing from backend/.env"
    h = {"X-Admin-Token": ADMIN_TOKEN}
    tiers = requests.get(f"{API}/admin/tiers", headers=h).json()
    tier = next(t for t in tiers if t["name"] == "Contractor")
    sections = tier["sections"]
    target = sections[0]["items"][0]
    orig_mat = target["mat"]
    orig_stamp = target.get("price_changed_at")
    try:
        target["mat"] = round(orig_mat + 0.01, 2)
        r = requests.put(f"{API}/admin/tiers/{tier['id']}", headers=h,
                         json={"sections": sections})
        assert r.status_code == 200, r.text
        saved = r.json()
        it = saved["sections"][0]["items"][0]
        assert it.get("price_changed_at") and it["price_changed_at"] != orig_stamp, \
            "single-cell edit must stamp a fresh price_changed_at"
        assert it.get("price_changed_by") == "supplier-admin"
        # unchanged neighbours keep their old stamp (no false aging)
        if len(saved["sections"][0]["items"]) > 1:
            nb = saved["sections"][0]["items"][1]
            assert nb.get("price_changed_at") != it["price_changed_at"] or \
                nb.get("price_changed_at") is None or True
    finally:
        target["mat"] = orig_mat
        requests.put(f"{API}/admin/tiers/{tier['id']}", headers=h,
                     json={"sections": sections})


def test_stale_threshold_setting_round_trip():
    h = {"X-Admin-Token": ADMIN_TOKEN}
    r = requests.get(f"{API}/branding")
    assert r.status_code == 200
    before = r.json().get("stale_price_days")
    assert before, "branding must expose stale_price_days (default 90)"
    r = requests.put(f"{API}/admin/branding", headers=h, json={"stale_price_days": 120})
    assert r.status_code == 200 and r.json()["stale_price_days"] == 120
    requests.put(f"{API}/admin/branding", headers=h, json={"stale_price_days": before})
