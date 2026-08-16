"""SEND-27 RULING REGISTER (Howard sealed 2026-08-14). Accuracy only.

FINDING (ledger query on the fresh EST-713272 read, run
c54633996e7a49e48432cf66a61efaf7): the three hypotheses separate cleanly.
  (a) EE inert?        NO — footprint_closure fired: closes=False,
                       refused_faces={right: "footprint does not close: ..."}.
  (b) EE backend-only? YES, for RIGHT — the backend refusal reason is
                       correct; the RENDERER (PdfOverlayEditor.jsx:716) emitted
                       a HARDCODED "width not read, NEEDS TAPE", ignoring the
                       reason. THAT is the defect. Two sources of refusal text:
                       the backend _faces_not_derivable[].reason was updated by
                       EE; its frontend sibling was not.
  (c) EE never got the chance? Applies to LEFT ONLY — LEFT has no width read
                       at all, so "wall width not read" is the CORRECT message
                       for LEFT (it is not an EE refusal). RIGHT had segment
                       depths 30+9=39 to close against and left unread, so EE
                       correctly refused it.

RULING (Item 2): the refusal reason must reach the rendered surface. A
correct backend field nobody sees delivers nothing. Fix: the surface reads
the backend reason (refused_reason on the per-wall row, else the matching
_faces_not_derivable reason) — never a hardcoded string.

RULING (Item 3): a claim that cannot be checked by the person who has to
trust it is the accuracy problem. A read-only diagnostic surfaces GG (runs
per page, where stored, truncation, int-key fires), the FF inputs (garage
label, LEFT/RIGHT elevation title blocks, depth string nearest the garage —
raw string + page + percent box, or ABSENT), and EE per-face reasons.

RULING C / Item 4 (STANDING DISCIPLINE, registered here): A HANDBACK CLAIM
ABOUT WHAT THE SURFACE SAYS MUST BE VERIFIED AGAINST THE RENDERED SURFACE,
NEVER AGAINST MODEL OUTPUT. "The field is populated" and "the user sees it"
came apart on the record (send-25 claimed the RIGHT string; the surface
showed the hardcoded one). From here, any handback sentence describing what
a user sees is either backed by the rendered surface or written as "the
field is set; not verified in the UI."
"""
import sys

sys.path.insert(0, "/app/backend")

from blueprint_diagnostics import build_blueprint_diagnostics  # noqa: E402


def _boni_result():
    """Synthetic Boni-shaped stored result — RIGHT refused by footprint
    closure, LEFT genuinely width-not-read, plus a small OCR substrate
    carrying the FF-input strings."""
    return {
        "measurements": {
            "_footprint_closure": {
                "closes": False,
                "failing_relations": [
                    "right depth 39 present but opposing left depth not read "
                    "— right cannot be closed"],
                "unverified_faces": ["right"],
                "refused_faces": {
                    "right": "footprint does not close: right depth 39 present "
                             "but opposing left depth not read — right cannot "
                             "be closed"},
            },
            "_faces_not_derivable": [
                {"elevation": "left", "surface": "body",
                 "reason": "wall width not read — area not derivable"},
                {"elevation": "right", "surface": "footprint_closure",
                 "reason": "footprint does not close: right depth 39 present "
                           "but opposing left depth not read — right cannot "
                           "be closed"},
            ],
        },
        "raw_ai": {
            "_ocr_text_ref": {"where": "run_doc"},
            "_ocr_text_by_page": {
                "6": {"page_w": 1000, "page_h": 800, "runs": [
                    {"norm": "3cargarage", "raw": "3 CAR GARAGE",
                     "loc": {"x_pct": 66.0, "y_pct": 44.0, "w_pct": 4.3, "h_pct": 1.1}},
                    {"norm": "3311", "raw": "33-11",
                     "loc": {"x_pct": 45.9, "y_pct": 20.0, "w_pct": 1.9, "h_pct": 0.9}},
                ]},
                "2": {"page_w": 1000, "page_h": 800, "runs": [
                    {"norm": "leftelevation", "raw": "LEFTELEVATION",
                     "loc": {"x_pct": 15.0, "y_pct": 47.0, "w_pct": 11.5, "h_pct": 1.8}},
                    {"norm": "rightelevation", "raw": "RIGHTELEVATION",
                     "loc": {"x_pct": 45.0, "y_pct": 87.8, "w_pct": 12.6, "h_pct": 1.8}},
                ]},
            },
        },
    }


# ── Item 1 / (b): EE fired; the reason IS the backend truth ──

def test_ee_backend_reason_is_footprint_closure_not_width_not_read():
    diag = build_blueprint_diagnostics(_boni_result())
    ee = {e["face"]: e for e in diag["ee"]}
    assert "right" in ee
    assert ee["right"]["refusal_reason"].startswith("footprint does not close:")
    assert "wall width not read" not in ee["right"]["refusal_reason"]
    assert ee["right"]["produced_by"] == "footprint_closure (Ruling EE)"


def test_left_genuinely_width_not_read_is_the_correct_message():
    # (c) for LEFT — width-not-read is CORRECT here, NOT an EE refusal.
    diag = build_blueprint_diagnostics(_boni_result())
    ee = {e["face"]: e for e in diag["ee"]}
    assert ee["left"]["refusal_reason"] == "wall width not read — area not derivable"
    assert ee["left"]["produced_by"] == "derive-or-disclose (width/height not read)"


# ── Item 3: the diagnostic surfaces GG + FF inputs ──

def test_diagnostic_gg_section_counts_runs_and_names_where_stored():
    diag = build_blueprint_diagnostics(_boni_result())
    gg = diag["gg"]
    assert gg["where"] == "run_doc"
    assert gg["total_runs"] == 4 and gg["pages"] == {"6": 2, "2": 2}
    assert gg["truncated"] is None and gg["int_key_coercions"] is None


def test_diagnostic_ff_probes_find_garage_and_titles():
    diag = build_blueprint_diagnostics(_boni_result())
    ff = diag["ff_inputs"]
    assert ff["garage_label"] != "ABSENT"
    assert any("3 CAR GARAGE" in h["raw"] for h in ff["garage_label"])
    assert ff["left_elevation_title"] != "ABSENT"
    assert ff["right_elevation_title"] != "ABSENT"
    # depth-near-garage selects by DISTANCE (a raw string surfaced), never
    # by value — it must be a real OCR string, not a fabricated depth.
    assert ff["depth_near_garage"] != "ABSENT"
    assert any("33-11" in h["raw"] for h in ff["depth_near_garage"])


def test_diagnostic_ff_absent_when_ocr_empty():
    res = _boni_result()
    res["raw_ai"]["_ocr_text_by_page"] = {}
    diag = build_blueprint_diagnostics(res)
    ff = diag["ff_inputs"]
    assert ff["garage_label"] == "ABSENT"
    assert ff["left_elevation_title"] == "ABSENT"
    assert ff["depth_near_garage"] == "ABSENT"


# ── Item 4 / Ruling C: surface-truth discipline, operationalised ──

def test_surface_reason_equals_backend_reason_no_hardcoded_string():
    # The rendered surface source-of-truth is the backend reason. A
    # footprint-closure face's diagnostic reason must EQUAL its refused_faces
    # reason verbatim — if a hardcoded string ever diverges, this fails.
    res = _boni_result()
    diag = build_blueprint_diagnostics(res)
    ee = {e["face"]: e for e in diag["ee"]}
    refused = res["measurements"]["_footprint_closure"]["refused_faces"]
    assert ee["right"]["refusal_reason"] == refused["right"]
