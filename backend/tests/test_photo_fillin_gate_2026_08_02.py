"""PHOTO FILL-IN QUOTE GATE + PROVENANCE PRINT (Howard ruled 2026-08-02).
GATE: an UNSET fill-in box on a photo estimate is SCOPE NOT SET — it BLOCKS
the quote like an open intake flag, never a $0 and never a click-past nudge.
An explicit 0 is a decision and clears; a measured value makes the box inert.
PRINT: the material list marks TYPED (contractor fill-in) vs MEASURED — the
document must not hide how a number got there. Non-fill-in notes stay
byte-identical (261 Haugh + 3 Degree are Hover-door: any movement there is a
regression)."""
from gates import GATE_TIERS, QUOTE_BLOCKING, quote_gate_blockers
from measure_staging import fold_photo_fillins, photo_fillins_unset
from routes.hover import _build_lines


PHOTO_BLOB = {"_source": "photo", "siding_sqft": 1400.0,
              "eaves_lf": 120.0, "rakes_lf": 60.0}


def _photo_est(**fields):
    return {"kind": "siding", "lines": [
        {"tab": "vinyl", "section": "Vinyl Siding", "name": "x",
         "unit": "SQ", "qty": 20}],
        "hover_measurements": dict(PHOTO_BLOB), **fields}


def test_registry_photo_fillin_unset_is_quote_blocking():
    assert GATE_TIERS["photo_fillin_unset"] == "quote"
    assert "photo_fillin_unset" in QUOTE_BLOCKING


def test_unset_boxes_block_the_quote():
    items = quote_gate_blockers(_photo_est())
    hit = next(i for i in items if i["code"] == "photo_fillin_unset")
    assert hit["blocking"] is True and hit["tier"] == "quote"
    assert "SCOPE NOT SET" in hit["label"] and "never $0" in hit["label"]
    for name in ("soffit ft²", "drip edge LF", "total trim ft²", "frieze yes/no"):
        assert name in hit["label"]


def test_explicit_zero_and_answered_frieze_clear():
    """0 is a DECISION — the house has none; frieze clears on yes OR no."""
    est = _photo_est(photo_soffit_sqft=0, photo_drip_edge_lf=0,
                     photo_total_trim_sqft=0, photo_frieze_present=False)
    assert not [i for i in quote_gate_blockers(est)
                if i["code"] == "photo_fillin_unset"]
    est2 = _photo_est(photo_soffit_sqft=250, photo_drip_edge_lf=180,
                      photo_total_trim_sqft=90, photo_frieze_present=True)
    assert not [i for i in quote_gate_blockers(est2)
                if i["code"] == "photo_fillin_unset"]


def test_measured_value_makes_the_box_inert():
    """Source provides it → engine consumes it: a blob carrying the value
    never asks for it (per-box)."""
    est = _photo_est(photo_frieze_present=True)
    est["hover_measurements"].update({"soffit_sqft": 300.0, "drip_edge_lf": 150.0,
                                      "total_trim_sqft": 80.0})
    assert not [i for i in quote_gate_blockers(est)
                if i["code"] == "photo_fillin_unset"]
    # measured frieze clears the toggle question too
    est2 = _photo_est(photo_soffit_sqft=1, photo_drip_edge_lf=1,
                      photo_total_trim_sqft=1)
    est2["hover_measurements"]["level_frieze_lf"] = 88.0
    assert not [i for i in quote_gate_blockers(est2)
                if i["code"] == "photo_fillin_unset"]


def test_gate_is_photo_door_only():
    """Hover and blueprint estimates NEVER see this blocker."""
    hover_est = _photo_est()
    hover_est["hover_measurements"] = {"siding_sqft": 1400.0, "eaves_lf": 120.0}
    assert not [i for i in quote_gate_blockers(hover_est)
                if i["code"] == "photo_fillin_unset"]
    bp_est = _photo_est()
    bp_est["hover_measurements"]["_source"] = "blueprint"
    assert not [i for i in quote_gate_blockers(bp_est)
                if i["code"] == "photo_fillin_unset"]
    assert photo_fillins_unset({}, {}) == []


def test_partial_fill_names_only_the_open_boxes():
    est = _photo_est(photo_soffit_sqft=250, photo_frieze_present=False)
    hit = next(i for i in quote_gate_blockers(est)
               if i["code"] == "photo_fillin_unset")
    assert "2 box(es)" in hit["label"]
    assert "open: drip edge LF, total trim ft²." in hit["label"]  # exact list — soffit + frieze cleared


# ── PROVENANCE PRINT — TYPED vs MEASURED on the printed notes ────────────

def _note(lines, tab, prefix):
    return next(str(l.get("note") or "") for l in lines
                if l.get("tab") == tab
                and str(l.get("name") or "").lower().startswith(prefix))


def test_typed_soffit_prints_typed_not_measured():
    est = {"photo_soffit_sqft": 250.0, "photo_frieze_present": True}
    m = fold_photo_fillins({**PHOTO_BLOB, "overhang_in": 12.0}, est)
    lines = _build_lines(m)
    vinyl = _note(lines, "vinyl", "soffit & fascia")
    assert "TYPED soffit total 250" in vinyl and "CONTRACTOR" in vinyl
    assert "MEASURED" not in vinyl
    vented = _note(lines, "lp_smart", "38 series soffit 16 x 16 vented")
    closed = _note(lines, "lp_smart", "38 series soffit 16 x 16 closed")
    assert "TYPED soffit total governs" in vented and "FILL-IN" in vented
    assert "TYPED soffit total governs" in closed and "FILL-IN" in closed
    trim540 = _note(lines, "lp_smart", "540 series")
    assert "TYPED toggle" in trim540 and "measured eave/rake runs" in trim540


def test_measured_soffit_note_byte_identical_to_before_the_ruling():
    """The Hover-door wording did NOT move — 261 Haugh / 3 Degree class.
    Exact strings pinned."""
    m = {"soffit_sqft": 250.0, "eaves_lf": 120.0, "rakes_lf": 60.0,
         "overhang_in": 12.0, "level_frieze_lf": 88.0}
    lines = _build_lines(m)
    vinyl = _note(lines, "vinyl", "soffit & fascia")
    assert vinyl == ("MEASURED soffit total 250 sqft ÷ 10 sqft/pc "
                     "(Q14a ruled 2026-07-27 — measured total governs); "
                     "Standard color default")
    vented = _note(lines, "lp_smart", "38 series soffit 16 x 16 vented")
    assert vented == ("Vented — measured soffit total governs: eave share "
                      "166.7 of 250 sqft ÷ 21.3 × 1.10 — verify venting split")
    trim540 = _note(lines, "lp_smart", "540 series")
    assert "TYPED" not in trim540 and "frieze 88+0 LF per-segment" in trim540
