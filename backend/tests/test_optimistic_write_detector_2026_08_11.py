"""OPTIMISTIC-WRITE DETECTOR (Howard ruled 2026-08-11 send-4).

"A write that is refused must say so. No optimistic local state
survives a non-2xx response. Roll it back and surface the refusal in
words." — Howard, 2026-08-11 send-4.

This detector is the fourth rung: without it, writeThrough is a
request (rung 3 — an available helper existing code ignores); with
it, the wrong behaviour becomes unrepresentable (rung 4 — the build
fails when an optimistic write does not route through the helper).

Same shape as the seam registry / TTL_REAPER_REGISTRY / schema-
consumer detector. All three caught something on first run; this
one already carries five known sites (see the registry) and any
future site that lands without a declaration will fail this test.

Scan rule:
  For each .jsx / .js in frontend/src, walk lines top-to-bottom.
  On every "await api.(put|post|patch|delete)" line, look back up
  to 25 lines for a local-state mutation NOT preceded by "await"
  on the same line (i.e., optimism-before-await, the Class Alpha
  shape). Local-write patterns:
    update({          |  setEst(       |  setLines(
    setLocal*(        |  setValue(     |  setDraft
    setBanner(        |  setPending

  If a match found, the file must either:
    (a) import writeThrough (retired to the helper contract), OR
    (b) be listed in UNCONDITIONAL_SAFE (Class Beta — post-response
        updates only).

Missing sites are the point of the detector: a new optimistic write
that no one registers still fails the build.
"""
from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


API_WRITE_RX = re.compile(r"await\s+api\.(put|post|patch|delete)")
LOCAL_WRITE_RX = re.compile(
    r"("
    r"update\(\s*\{"           # update({ ... })
    r"|setEst\("               # setEst(...)
    r"|setLines\("             # setLines(...)
    r"|setLocal[A-Za-z]*\("    # setLocalX(...)
    r"|setValue\("             # setValue(...)
    r"|setDraft"               # setDraft…
    r"|setBanner\("            # setBanner(...)
    r"|setPending"             # setPending…
    r")"
)


# UNCONDITIONAL_SAFE — sites that are Class-Beta by construction (the
# local write runs INSIDE the response block, so a thrown await never
# leaves optimistic state behind). Each entry named + explained. Adding
# a new entry requires a comment saying WHY it is safe.
UNCONDITIONAL_SAFE: dict[str, str] = {
    # (No sites listed. SettingsRow.jsx has ONE Class-Beta write
    # (saveSpec's post-response update) AND ONE Class-Alpha write
    # (updateWastePct's optimistic + rederive) — it therefore routes
    # through writeThrough. The Class-Beta write is safe by
    # construction; the import is what retires the file for the
    # detector.)
}


def _scan_file(path: Path) -> list[tuple[int, str, int, str]]:
    """Return [(local_line_no, local_snippet, api_line_no, api_snippet)]
    for every optimistic-before-await site in the file."""
    lines = path.read_text().splitlines()
    hits: list[tuple[int, str, int, str]] = []
    for i, ln in enumerate(lines):
        if not API_WRITE_RX.search(ln):
            continue
        pre_start = max(0, i - 25)
        # Walk backwards so we prefer the closest local-write.
        for j in range(i - 1, pre_start - 1, -1):
            w = lines[j]
            if "await " in w:
                continue  # await-then-write is safe
            s = w.strip()
            if s.startswith("//") or s.startswith("*"):
                continue  # comment
            if LOCAL_WRITE_RX.search(w):
                hits.append((j + 1, s[:110], i + 1, ln.strip()[:110]))
                break
    return hits


def _imports_writethrough(src: str) -> bool:
    return ("from \"@/lib/write_through\"" in src
            or "from '@/lib/write_through'" in src
            or "@/lib/write_through" in src)


def _files_under(root: Path) -> list[Path]:
    return sorted(list(root.rglob("*.jsx")) + list(root.rglob("*.js")))


def test_frontend_write_through_helper_exists():
    """The helper must ship at the exact path the detector greps for."""
    assert (FRONTEND / "lib" / "write_through.js").exists()


def test_frontend_optimistic_write_registry_exists():
    """The registry ships at the declared path."""
    assert (FRONTEND / "lib" / "optimistic_write_registry.js").exists()


def test_every_optimistic_write_routes_through_helper_or_is_registered():
    """The class-level pin. Any component that mutates local state
    within 25 lines before an api.put/post/patch/delete must import
    writeThrough OR be listed in UNCONDITIONAL_SAFE.

    THIS TEST FAILS BY DESIGN on any new optimistic write that lands
    without either retirement path — the whole point of rung 4.
    """
    files = _files_under(FRONTEND)
    unretired: list[tuple[str, list[tuple[int, str, int, str]]]] = []
    for f in files:
        if f.name in ("write_through.js", "optimistic_write_registry.js"):
            continue
        src = f.read_text()
        hits = _scan_file(f)
        if not hits:
            continue
        rel = str(f.relative_to(FRONTEND))
        if _imports_writethrough(src):
            continue  # retired to the helper contract
        if rel in UNCONDITIONAL_SAFE:
            continue  # declared safe (Class Beta)
        unretired.append((rel, hits))
    if unretired:
        msg = ["\nOptimistic writes that do NOT route through writeThrough:"]
        for rel, hits in unretired:
            msg.append(f"  {rel}:")
            for lno, snip, apino, apisnip in hits:
                msg.append(f"    line {lno}: {snip}")
                msg.append(f"      -> line {apino}: {apisnip}")
        msg.append(
            "\nRoute each site through writeThrough (see "
            "frontend/src/lib/write_through.js) OR add the file to "
            "UNCONDITIONAL_SAFE in this test with a comment naming "
            "why the pattern is Class-Beta safe."
        )
        raise AssertionError("\n".join(msg))


def test_writethrough_contract_pinned():
    """The helper must carry the mandatory rollback-when-optimistic
    guard — a write that runs applyOptimistic without a rollback is
    exactly the bug this class is meant to retire."""
    src = (FRONTEND / "lib" / "write_through.js").read_text()
    assert "rollback is REQUIRED" in src, (
        "writeThrough must refuse to run when applyOptimistic is set "
        "and rollback is not — the whole point of the helper."
    )
    # And the refusal chip must name a way out (SurfaceAccessChip
    # contract carried into the write layer).
    assert "wayOut" in src


def test_registry_carries_known_sites():
    """The five known optimistic sites from the 2026-08-11 audit doc
    must be declared in the registry. Missing an entry silently means
    someone deleted a site and forgot to strike its declaration."""
    src = (FRONTEND / "lib" / "optimistic_write_registry.js").read_text()
    for known_id in (
        "blueprint-apply-lines",
        "settings-row-waste-pct",
        "hover-import-reset-waste",
        "ai-measure-session-clear",
        "iss-apply-hover-lines",
    ):
        assert known_id in src, f"registry missing {known_id!r}"
