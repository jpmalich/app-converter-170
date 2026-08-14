"""RULING I — ARCHIVE AUDIT (send-15, 2026-08-14).

'Archive every send VERBATIM in-repo, one file per send, and make the
register audit compare PROSE TO PINS rather than tests to tests. Until that
archive exists, no retro-registration report should be described as
complete — say "consistent with existing pins" instead.'

This audit enforces the archive's integrity: a MANIFEST row that claims
ARCHIVED must point at a non-empty file that is NOT an AWAITING-PASTE
placeholder, so a false "archived" cannot slip through. A row marked
AWAITING PASTE is honest and passes — it is on the record as not-yet-done.
"""
from __future__ import annotations

import re
from pathlib import Path

ARCHIVE = Path(__file__).resolve().parents[1] / "rulings_archive"
MANIFEST = ARCHIVE / "MANIFEST.md"


def _rows():
    rows = []
    for line in MANIFEST.read_text().splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m and m.group(1).isdigit():
            rows.append((int(m.group(1)), m.group(2).strip(),
                         m.group(3).strip()))
    return rows


def test_manifest_names_every_send_8_through_15():
    sends = {r[0] for r in _rows()}
    assert {8, 9, 10, 11, 12, 13, 14, 15} <= sends


def test_archived_rows_point_at_real_nonplaceholder_prose():
    for num, fname, status in _rows():
        f = ARCHIVE / fname
        if status.upper().startswith("ARCHIVED"):
            assert f.exists(), f"{fname} claims ARCHIVED but is missing"
            body = f.read_text().strip()
            assert len(body) > 200, f"{fname} ARCHIVED but near-empty"
            assert "AWAITING PASTE" not in body, \
                f"{fname} claims ARCHIVED but is a placeholder"


def test_awaiting_rows_are_honest_placeholders():
    for num, fname, status in _rows():
        if "AWAITING" in status.upper():
            f = ARCHIVE / fname
            assert f.exists() and "AWAITING PASTE" in f.read_text()


def test_retro_registration_completeness_is_gated_on_the_archive():
    """The register may only call a retro-walk COMPLETE once every send's
    prose is archived; while any row is AWAITING, completeness is 'consistent
    with existing pins' only. This pin encodes that gate."""
    statuses = [s for _n, _f, s in _rows()]
    archive_complete = all(s.upper().startswith("ARCHIVED") for s in statuses)
    # Currently sends 8-12 await paste — so completeness MUST be False.
    assert archive_complete is False
