"""HOVER PICKER → LP PRODUCT MAPPING defect (Jon Casile / 261 Haugh,
2026-07-23 — THE FOUNDING EXAMPLE, ruled).

DEFECT: the Hover-import profile picker did NOT drive the LP product
mapping — it only labeled. Root cause: `hoverRunId` state in
HoverImportButton.jsx was declared but NEVER SET after the async import
completed, so apply()'s materialize branch (`hover-lp-run`, the ONLY
profile-driven mapping) was unreachable. The estimate kept the
profile-blind default tab lines (38 Series Lap) regardless of the picker.

FIX PINNED here:
  • the run id reaches apply() in BOTH result branches (async poll +
    legacy sync shape)
  • honest failure: lp_smart + profile + missing run id raises an error
    toast — never a silent skip
  • the founding example itself: Jon Casile's estimate is materialized at
    board_batten via the machinery (hover-lp-run), geometry basis pinned
    to Hover report 8f6f9b5e — B&B set per the ruled book conventions:
    38 Series 4'×10' panel (40 ft²/pc), 190 Series Trim battens 16" o.c.
    (÷16' stock, no waste term), NO STARTER on B&B (base gets J — a
    starter line on B&B composition is a BUG, previously pinned in
    test_lp_smartside_formulas).
"""
import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api_base import API  # noqa: E402
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

CASILE_EST = "e2ce35b8-95ea-4dbc-89c9-f7a7a5c34170"  # EST-523061 — founding example
JSX = Path("/app/frontend/src/components/estimate/HoverImportButton.jsx")


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


def test_picker_run_id_wire_exists():
    """The dead wire: setHoverRunId must be CALLED (not just declared) in
    both import-result branches, or the picker is a label again."""
    jsx = JSX.read_text()
    assert jsx.count("setHoverRunId(runId") >= 2, "run id must be set in both result branches"
    assert "setHoverRunId(runId || null)" in jsx  # legacy sync shape included


def test_silent_skip_replaced_with_honest_failure():
    jsx = JSX.read_text()
    assert "profile && !hoverRunId" in jsx
    assert "could NOT be derived at the chosen profile" in jsx


def test_founding_example_materialized_at_bb(session):
    r = session.get(f"{API}/estimates/{CASILE_EST}", timeout=20)
    assert r.status_code == 200
    e = r.json()
    assert e["default_siding_profile"] == "board_batten"
    assert str(e["lp_source_run_id"]).startswith("hover-8f6f9b5e")


def test_founding_example_bb_product_set(session):
    """Book conventions govern: B&B = 4×10 panels + battens, NO starter,
    NO lap SKU anywhere in the composition."""
    r = session.post(f"{API}/estimates/{CASILE_EST}/lp-package/preview",
                     json={}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    items = [str(l.get("item") or l.get("name") or "") for l in d["lines"]]
    joined = " | ".join(items)
    assert any("38 Series 4' x 10' Panel" in i for i in items), joined
    assert any("190 Series Trim" in i for i in items), "battens missing"
    assert "38 Series Lap" not in joined, "LAP SKU on a B&B composition — the defect"
    assert "starter" not in joined.lower(), "starter on B&B is a pinned BUG"
    gb = d["geometry_basis"]
    assert gb["profile"] == "board_batten"
    assert "8f6f9b5e" in json.dumps(gb)


def test_founding_example_panel_math(session):
    """HOUSE-WRAP SCOPE GOVERNS (Casile item-1, ruled): the facade-scope
    picker composes 2064 ft² (stucco 312 + brick 234 excluded, never
    silently summed). AMENDED (family waste sealed 2026-07-24): B&B waste
    is 30% — 2064 × 1.30 ÷ 40 ft²/panel = 67.08 → 68 PCS. 85 PCS would
    mean the whole-house 2610 leaked back in — the defect."""
    r = session.post(f"{API}/estimates/{CASILE_EST}/lp-package/preview",
                     json={}, timeout=90)
    panel = next(l for l in r.json()["lines"]
                 if "4' x 10' Panel" in str(l.get("item") or l.get("name")))
    assert (panel.get("qty") or panel.get("quantity")) == 68


def test_founding_example_facade_scope_pinned(session):
    """The materialized run carries the explicit facade scope: 2064 ft²
    composes; stucco 312 + brick 234 are NAMED excluded; the flag is on
    the package so the contractor sees the scope in one glance."""
    r = session.post(f"{API}/estimates/{CASILE_EST}/lp-package/preview",
                     json={}, timeout=90)
    d = r.json()
    flags = " | ".join(str(f.get("label") or f) for f in d.get("hover_mapping_flags") or [])
    assert "2064" in flags, flags
    assert "stucco 312" in flags and "brick 234" in flags, flags
