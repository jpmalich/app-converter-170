"""BLUEPRINT SOURCE-SHEET VIEWER — Phase-1 render-contract pins (Howard,
ruled 2026-07-20). Build discipline pinned:

1. READ-ONLY: the page performs GETs only — no POST/PUT/PATCH/DELETE
   anywhere in the viewer source. Zero writes by construction.
2. DIRECT ROUTE ONLY: /estimate/:id/source-sheets is registered in
   App.js and referenced NOWHERE else in the frontend — no entry-point
   chip/button/link on any existing surface (demo-surface rule).
3. ZERO BACKEND CHANGES: the viewer consumes the pre-existing
   latest-for-estimate endpoint + /api/uploads store as-is.
4. PROVENANCE: every sheet renders which upload (filename), which page
   (Sheet i of n), and which extraction run (run id) — and the AI-read
   summary names the SAME run so the field-compare is same-basis.
5. NAMED BOUNDARY: the 24h ai_blueprint_runs TTL is stated on the empty
   state, never hidden.
"""
import re
import subprocess
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
JSX = (FRONTEND / "pages" / "SourceSheets.jsx").read_text()
APP = (FRONTEND / "App.js").read_text()


def test_pin1_read_only_no_write_calls():
    assert "api.get(" in JSX
    for verb in ("api.post", "api.put", "api.patch", "api.delete"):
        assert verb not in JSX, f"viewer must be read-only — found {verb}"
    assert 'data-testid="source-sheets-readonly-note"' in JSX
    assert "READ-ONLY" in JSX


def test_pin2_direct_route_only_no_entry_points():
    assert '<Route path="/estimate/:id/source-sheets"' in APP
    hits = subprocess.run(
        ["grep", "-rl", "source-sheets", str(FRONTEND)],
        capture_output=True, text=True,
    ).stdout.split()
    allowed = {str(FRONTEND / "App.js"), str(FRONTEND / "pages" / "SourceSheets.jsx")}
    assert set(hits) == allowed, (
        f"source-sheets referenced outside the direct route: {set(hits) - allowed}")


def test_pin3_consumes_existing_endpoints_only():
    assert "/measure/ai-blueprint/latest-for-estimate/" in JSX
    assert "/api/uploads/" in JSX  # durable store — disk + upload_blobs mirror


def test_pin4_per_sheet_provenance():
    assert 'data-testid="source-sheets-provenance"' in JSX
    assert "blueprint extraction run {rid8}" in JSX
    assert re.search(r"Sheet \{i \+ 1\} of \{pages\.length\} · \{name\} · run \{rid8\}", JSX), \
        "per-sheet caption must name page number, upload filename and run id"
    assert 'data-testid="source-sheets-estimate"' in JSX  # estimate identity in header


def test_pin4b_ai_summary_same_run_alongside():
    assert 'data-testid="source-sheets-ai-summary"' in JSX
    assert "AI-READ · blueprint extraction run {rid8}" in JSX
    idx_pages = JSX.index('data-testid="source-sheets-provenance"')
    idx_summary = JSX.index('data-testid="source-sheets-ai-summary"')
    assert idx_pages < idx_summary  # sheets render alongside/before the summary column


def test_pin5_ttl_boundary_named_on_empty_state():
    assert 'data-testid="source-sheets-no-run"' in JSX
    assert "24h" in JSX and "TTL" in JSX


def test_pin6_lightbox_zoom_contract():
    for tid in ("source-sheet-thumb-", "source-sheets-lightbox",
                "source-sheets-lightbox-img", "source-sheets-lightbox-close",
                "source-sheets-lightbox-prev", "source-sheets-lightbox-next"):
        assert tid in JSX, f"missing {tid}"
