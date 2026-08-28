"""S1 + S2 — Hover drawn-elevation geometry read (authorized 2026-07-29).

S1: every Hover import persists the PDF (uploads/hover_pdfs/{run_id}.pdf,
path on the run doc) so the drawn pages outlive the 1h page-cache TTL.
S2: the geometry reader extracts per-facade WIDTH + HEIGHT callouts,
opening IDs drawn on their facades, and dimensioned corner heights —
tagged HOVER-DIM (HOVER-READ ✓/⚠), REPORT ONLY.

NO S3 BY RULING: nothing from the read feeds a flag, a count, or a
line — Howard reviews the 261 Haugh + 3 Degree acceptance runs first.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routes.hover_elevation_read import aggregate_geometry

BACKEND = Path(__file__).resolve().parent.parent


def _haugh_like_pages():
    return [
        {"view": "FRONT", "confidence": "high",
         "facades": [{"label": "WR-20", "width_ft": 29.25, "width_text": "29'3\"",
                      "height_min_ft": 9.25, "height_max_ft": 9.58}],
         "openings_placed": [{"id": "W-206", "on_facade": "WR-2"},
                             {"id": "W-207", "on_facade": "WR-2"}],
         "corner_heights_ft": []},
        {"view": "RIGHT-BACK", "confidence": "high",
         "facades": [{"label": "WR-17", "width_ft": 18.42, "width_text": "18'5\""}],
         "openings_placed": [{"id": "W-211", "on_facade": "WR-7"},
                             {"id": "D-2", "on_facade": "BLOCK"}],
         "corner_heights_ft": [{"near_facade": "WR-17", "height_ft": 18.42,
                                "text": "18'5\""}]},
    ]


def test_aggregate_reads_widths_heights_placements_and_corners():
    out = aggregate_geometry(_haugh_like_pages(),
                             schedule_text="W-206 W-207 W-211 D-2 WR-20 WR-17 WR-2 WR-7")
    labels = {f["label"]: f for f in out["facades"]}
    assert labels["WR-20"]["width_ft"] == 29.25          # the batten input
    assert labels["WR-20"]["height_min_ft"] == 9.25
    assert {(p["id"], p["on_facade"]) for p in out["openings_placed"]} == {
        ("W-206", "WR-2"), ("W-207", "WR-2"), ("W-211", "WR-7"), ("D-2", "BLOCK")}
    assert out["corner_heights_ft"][0]["height_ft"] == 18.42   # the 18'5" corner
    assert out["warnings"] == []                                # clean read → zero ⚠
    assert "HOVER-DIM" in out["provenance"] and "never TAPED" in out["provenance"]


def test_every_warning_is_named_not_summarized():
    pages = _haugh_like_pages()
    # unknown ID + cross-view width disagreement + double placement
    pages[1]["openings_placed"].append({"id": "W-999", "on_facade": "WR-7"})
    pages[1]["facades"].append({"label": "WR-20", "width_ft": 31.0})
    pages[1]["openings_placed"].append({"id": "W-206", "on_facade": "WR-7"})
    out = aggregate_geometry(pages, schedule_text="W-206 W-207 W-211 D-2 WR-20 WR-17 WR-2 WR-7")
    joined = "\n".join(out["warnings"])
    assert "W-999" in joined and "not in the report's schedule" in joined
    assert "WR-20" in joined and "width disagrees" in joined
    assert "W-206" in joined and "2 different walls" in joined
    assert all(w.startswith("⚠") for w in out["warnings"])


def test_no_s3_wiring_by_construction():
    """The reader's output feeds NOTHING: no import into the derivation
    or flag modules, and the report never touches estimate lines."""
    reader = (BACKEND / "routes" / "hover_elevation_read.py").read_text()
    for banned in ("_build_lines", "lp_package", "flag_checklist",
                   "estimates.update_one", "hover_mapping_flags"):
        assert banned not in reader, f"S3 wiring appeared without a ruling: {banned}"
    for mod in ("lp_package.py", "routes/lp_package_routes.py"):
        assert "hover_elevation_read" not in (BACKEND / mod).read_text()


def test_s1_import_persists_pdf():
    src = (BACKEND / "routes" / "hover.py").read_text()
    # SEND-142 NAMED PIN UPDATE (Howard authorised 2026-08-28): S1's
    # substrate persistence is UNCHANGED as a rule — the PDF is still kept
    # past the page-cache TTL, keyed by run_id — but it is kept in Emergent
    # OBJECT STORAGE instead of the pod's own disk, which a pod
    # replacement used to wipe. The pin follows the substrate.
    assert "hover_pdf_path(run_id)" in src
    assert '"pdf_object": pdf_object' in src
    assert 'uploads", "hover_pdfs"' not in src.replace("'", '"')
    # a run from BEFORE the move still reads off its legacy disk path
    assert 'doc.get("pdf_path")' in src
    # the read endpoint refuses politely when the substrate predates S1
    assert "re-upload the Hover" in src


def test_view_page_locator_exactly_one_token_rule():
    """The drawn-view pages carry ONE bare compass token; the footprint/
    compass page carries several at once and must be excluded."""
    import fitz
    from routes.hover_elevation_read import _find_view_pages
    doc = fitz.open()
    p = doc.new_page()   # compass page — all four tokens → excluded
    p.insert_text((72, 72), "FRONT\nRIGHT\nBACK\nLEFT")
    p = doc.new_page()   # true view page
    p.insert_text((72, 72), "Complete Measurements\nFRONT-RIGHT\nN")
    p = doc.new_page()   # unrelated table page
    p.insert_text((72, 72), "OPENINGS\nWindows")
    pages = _find_view_pages(doc.tobytes())
    assert [(pg["page_num"], pg["label"]) for pg in pages] == [(2, "FRONT-RIGHT")]


def test_straight_on_only_oblique_pages_dropped():
    """Howard's ruling 2026-07-29: the four oblique compass pages are
    DROPPED from the extraction — every invented ID on the Haugh
    acceptance run came off an oblique view."""
    from routes.hover_elevation_read import CARDINAL_VIEWS
    assert set(CARDINAL_VIEWS) == {"FRONT", "BACK", "LEFT", "RIGHT"}
    src = (BACKEND / "routes" / "hover_elevation_read.py").read_text()
    assert 'p["label"] in CARDINAL_VIEWS' in src


def test_id_constraint_rides_every_read():
    """Howard's standing rule from the STC-1 probe (2026-07-29): every
    vision read carries the deterministic ID universe as a constraint —
    an honest omission beats a guessed tag."""
    src = (BACKEND / "routes" / "hover_elevation_read.py").read_text()
    assert "NEVER invent an ID" in src
    assert "known_ids_line" in src
