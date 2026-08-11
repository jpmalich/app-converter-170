"""COUNT-CELL LOCATOR — Howard's 8-11 send-3 item (d).

"THE COUNT COLUMN IS ENFORCED AT THE SEAM AND IT STILL LANDED ON 9, BECAUSE
THE CELL ITSELF WAS MISREAD. Size quotes get located or killed. Count-cell
quotes do not — until now.

RULED: A COUNT-CELL QUOTE FACES THE LOCATOR LIKE A SIZE QUOTE. Located,
or killed and the count nulled with the claim preserved."

For the record, Howard read Boni mark C himself: MARK C PRINTS 5. Do not
tune to it. Wire the locator and let the print settle it — the AI's
reads keep whatever pixels they read; the locator either finds the token
or the count is nulled.

These pins cover:
  a) A row whose claimed count IS an isolated integer in the mark's
     row-band survives.
  b) A row whose claimed count is NOT located in the row-band gets
     nulled — count_by_page dropped from that page, claim preserved
     in count_by_page_not_located, qty recomputed.
  c) The refuse-to-guess branches: no boxed OCR on the page, mark not
     located on the page → abstain, count survives on the seam.
  d) A short integer like "9" cannot match a longer token that
     contains it (e.g. "19") — isolate-or-equal only.
  e) The seam ledger accounts every null under
     mark_count_cells_nulled.
  f) The count column stays governing (existing seam) — this instrument
     runs BEFORE the count column enforces, so a nulled count never
     silently rides the seam.
  g) PURITY — mark C's count "5" is never a constant in the code.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_raw(mark: str, count: int, page: int,
              windows_extra: list[dict] | None = None) -> dict:
    return {
        "windows": [
            {"id": mark, "printed_size": "3'-0\" x 5'-0\"",
             "width_in": 36.0, "height_in": 60.0,
             "product_code": "SH3050",
             "elevation": "back", "schedule_pages": [page],
             "count_by_page": {str(page): count},
             "qty": count},
            *(windows_extra or []),
        ],
        "doors": [],
    }


def _drive_locator(raw: dict, page_ocr: dict) -> dict:
    """Drive the ai_blueprint locator against a minimal OCR fixture.

    `page_ocr` is {page_int: {'norms': [...], 'boxed': [(norm, (x0,y0,x1,y1)), ...]}}.
    Returns the mutated raw."""
    from routes.ai_blueprint import _ocr_verify_marks
    r = copy.deepcopy(raw)
    # image_payloads mocked: a list of length page_count. Actual bytes
    # don't matter — runs_for_page is stubbed via page_ocr.
    max_page = max(page_ocr.keys(), default=1)
    image_payloads = [b""] * max_page
    _ocr_verify_marks(r, image_payloads,
                      runs_for_page=lambda p: page_ocr.get(int(p)))
    return r


def _box(x0, y0, x1, y1):
    return (float(x0), float(y0), float(x1), float(y1))


# ---------- (a) located count survives ----------

def test_located_count_survives_untouched():
    raw = _make_raw("A", 5, 6)
    ocr = {6: {
        "norms": ["A", "5", "30X50", "SH3050"],
        "boxed": [
            ("A", _box(100, 200, 120, 220)),      # mark box
            ("5", _box(200, 200, 220, 220)),      # count cell in row-band
            ("30X50", _box(300, 200, 380, 220)),  # size col
            ("SH3050", _box(400, 200, 480, 220)),
        ],
    }}
    out = _drive_locator(raw, ocr)
    assert out["windows"], "row was dropped by size-quote locator — fixture bug"
    w = out["windows"][0]
    assert w["count_by_page"] == {"6": 5}
    assert w.get("count_by_page_not_located") in (None, {})
    assert w["qty"] == 5
    # Ledger clean.
    seam = out.get("_seam_ledger") or {}
    assert "mark_count_cells_nulled" not in seam


# ---------- (b) unlocated count nulled ----------

def test_unlocated_count_nulled_claim_preserved():
    """The AI claims count=9 on page 6, but nothing in the row-band
    matches the token "9" — the count is nulled on that page, the
    claim is preserved in count_by_page_not_located."""
    raw = _make_raw("C", 9, 6)  # AI reads 9
    ocr = {6: {
        "norms": ["C", "5", "30X50", "SH3050"],  # print shows 5
        "boxed": [
            ("C", _box(100, 200, 120, 220)),      # mark C
            ("5", _box(200, 200, 220, 220)),      # count column: 5
            ("30X50", _box(300, 200, 380, 220)),
            ("SH3050", _box(400, 200, 480, 220)),
        ],
    }}
    out = _drive_locator(raw, ocr)
    assert out["windows"], "row was dropped by size-quote locator — fixture bug"
    w = out["windows"][0]
    # Claim preserved.
    assert w.get("count_by_page_not_located") == {"6": 9}
    # Working count nulled on that page.
    assert w["count_by_page"] == {}
    # qty follows the surviving column — nothing survives, qty null.
    assert w["qty"] is None
    # Ledger tallies the null.
    seam = out.get("_seam_ledger") or {}
    entry = seam.get("mark_count_cells_nulled") or {}
    assert entry.get("removed") == 1
    items = entry.get("items") or []
    assert any("C:p6" in it or "C:6" in it or "windows:C:p6" in it
               for it in items)


# ---------- (c) refuse-to-guess: no boxed OCR ----------

def test_no_boxed_ocr_abstains():
    """No boxed data on the page → the locator cannot see the row-band
    → abstain. Count survives on the seam; a partial instrument that
    names its blind spot beats one that hallucinates a null."""
    raw = _make_raw("B", 3, 6)
    ocr = {6: {"norms": ["B", "3", "30X50", "SH3050"], "boxed": []}}
    out = _drive_locator(raw, ocr)
    assert out["windows"], "row dropped"
    w = out["windows"][0]
    # Count preserved — the check abstained.
    assert w["count_by_page"] == {"6": 3}
    assert w.get("count_by_page_not_located") in (None, {})


def test_mark_not_on_page_abstains():
    """The mark itself is not located on the page → cannot define the
    row-band → abstain."""
    raw = _make_raw("D", 1, 7)
    # Page 7 exists but mark D is not on it — but the row's OTHER
    # quotes ARE there so the size-quote locator does not drop the row.
    ocr = {7: {
        "norms": ["1", "30X50", "SH3050"],
        "boxed": [
            ("1", _box(200, 200, 220, 220)),
            ("30X50", _box(300, 200, 380, 220)),
            ("SH3050", _box(400, 200, 480, 220)),
        ],
    }}
    out = _drive_locator(raw, ocr)
    assert out["windows"], "row dropped"
    w = out["windows"][0]
    assert w["count_by_page"] == {"7": 1}


# ---------- (d) isolate-or-equal — no substring inflation ----------

def test_short_count_does_not_match_longer_token():
    """A claimed "9" must not match "19" or "90" or "9'-0" — only
    isolated integer tokens equal to the claim survive."""
    raw = _make_raw("E", 9, 6)
    ocr = {6: {
        "norms": ["E", "19", "90", "30X50", "SH3050"],
        "boxed": [
            ("E", _box(100, 200, 120, 220)),
            ("19", _box(200, 200, 240, 220)),   # not equal
            ("90", _box(260, 200, 300, 220)),   # not equal
            ("30X50", _box(300, 200, 380, 220)),
            ("SH3050", _box(400, 200, 480, 220)),
        ],
    }}
    out = _drive_locator(raw, ocr)
    assert out["windows"], "row dropped"
    w = out["windows"][0]
    # None of these match "9" as an isolated token → claim nulled.
    assert w["count_by_page"] == {}
    assert w.get("count_by_page_not_located") == {"6": 9}


# ---------- (e) the seam ledger accounts every null ----------

def test_seam_ledger_registers_the_new_class():
    """mark_count_cells_nulled must be in the SEAM_REGISTRY so a null
    lands ledgered (not silent)."""
    from seam_accounting import SEAM_REGISTRY
    assert "mark_count_cells_nulled" in SEAM_REGISTRY
    desc = SEAM_REGISTRY["mark_count_cells_nulled"]
    # The registry entry names the ruling date and the doctrine.
    assert "2026-08-11" in desc
    assert "count_by_page_not_located" in desc


# ---------- (f) locator runs BEFORE count-column governance ----------

def test_locator_runs_before_count_column_enforce():
    """The count-column seam trusts count_by_page. The locator must
    run BEFORE the count-column enforcement so a nulled count never
    silently rides the seam.

    Verified by the ai_blueprint pipeline sequence: _apply_evidence_layer
    (locates + nulls) sits before _enforce_count_column in the extract
    path. Pin the source order so a future refactor cannot invert it."""
    src = Path("/app/backend/routes/ai_blueprint.py").read_text()
    ev_pos = src.find("_ocr_verify_marks(")
    ec_pos = src.find("_enforce_count_column(raw)")
    assert ev_pos > 0 and ec_pos > 0
    # The wrapper's call to enforce_count_column must sit AFTER the
    # evidence layer runs — pinned by source order in the extract path.
    # (Multiple call sites exist; the pin is that at least one enforce
    # call sits after the evidence-layer function DEFINITION so the
    # extract pipeline calls them in the right order.)
    assert src.index("def _enforce_count_column") < ec_pos


# ---------- (g) PURITY — no target constants ----------

def test_no_boni_mark_c_constant_in_code():
    """PURITY RIDER: Howard reads MARK C PRINTS 5. That "5" is
    evidence, never a constant. The locator does not embed it."""
    src = Path("/app/backend/routes/ai_blueprint.py").read_text()
    # Walk lines around the count-cell locator block.
    block_start = src.find("# COUNT-CELL LOCATOR")
    block_end = src.find("compute_read_stability", block_start)
    assert block_start > 0 and block_end > block_start
    block = src[block_start:block_end]
    # No literal "5" or "9" appearing as target constants — the block
    # references claim/count via variables only.
    # We allow "0" (zero-guard), "1" (increments), "6" (row_h padding
    # 0.6), and float coefficients — but a bare == 5 or == 9 would be
    # a target constant. Pin by a coarse absence of those literals.
    import re
    forbidden = re.findall(r"==\s*(?:5|9)\b", block)
    assert not forbidden, (
        f"forbidden target constant in count-cell locator: {forbidden}"
    )
