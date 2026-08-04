"""PRINT NEVER CRASHES — EN AND ES, EVERY JS PRINT SURFACE (Howard ruled
2026-08-04, the _lang ReferenceError).

THE CRASH: the Spanish sweep made renderLinesHtml call
translateNote(l.note, _lang) but _lang was defined inside printTakeoff()
— module-scope helper, out of scope. Every PRINT click on a takeoff
modal with a noted line threw ReferenceError. 1,824 tests were green
because no test ever EXECUTED the print render — these do.

CLASS SWEPT: ESLint no-undef across the whole frontend src found exactly
this one member left (2 sites, same file). RENDER_3D_ENABLED (accept-page
walk) was the first; the sweep pin below keeps the whole class dead.

SURFACES EXECUTED, BOTH LANGUAGES (esbuild bundle + node, DOM-stubbed,
real invocation — not an import check):
  printTakeoff  -> HOVER restore/import modal (crash site), ISS Hover
                   modal, Blueprint modal, AI Measure modal (all kinds)
  buildMaterialListHtml   -> estimate page + ISS editor Material List
  buildLpMaterialListHtml -> LP Material List panel
(The quote/customer PDF prints server-side through WeasyPrint — covered
by the backend suite; elevation sheets print the React page itself.)
"""
import re
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FE = Path("/app/frontend")
ESBUILD = FE / "node_modules" / ".bin" / "esbuild"
BUNDLE = Path("/tmp/print_smoke_bundle.cjs")

SURFACES = [
    "hover-restore-modal", "hover-lp-modal", "blueprint-ai-modal",
    "iss-modal", "estimate-material-list", "lp-material-list",
]


@pytest.fixture(scope="module")
def smoke_output():
    build = subprocess.run(
        [str(ESBUILD), str(HERE / "print_smoke" / "entry.mjs"), "--bundle",
         "--format=cjs", "--platform=node", "--jsx=automatic",
         f"--outfile={BUNDLE}"],
        capture_output=True, text=True, timeout=120)
    assert build.returncode == 0, f"esbuild failed:\n{build.stderr}"
    run = subprocess.run(
        ["node", str(HERE / "print_smoke" / "runner.cjs"), str(BUNDLE)],
        capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, (
        f"print render CRASHED — the _lang class is back:\n{run.stderr}")
    return run.stdout


def test_every_print_surface_renders_in_both_languages(smoke_output):
    for lang in ("en", "es"):
        for surface in SURFACES:
            assert f"PRINT-SMOKE-OK {lang} {surface}" in smoke_output, \
                f"{surface} did not render in {lang}"
    assert "PRINT-SMOKE-DONE" in smoke_output


def test_lang_reaches_render_lines_as_a_parameter():
    src = Path("/app/frontend/src/lib/printTakeoff.js").read_text()
    assert 'function renderLinesHtml(lines, kind, _lang = "en")' in src, \
        "renderLinesHtml must take lang as a DEFAULTED parameter — EN when unset, never a crash"
    assert "renderLinesHtml(lines, kind, _lang)" in src, \
        "printTakeoff must pass its resolved lang down to the line renderer"


def test_no_undef_class_stays_dead():
    """THE CLASS PIN: ESLint no-undef over the full frontend src — the
    detector that would have been red while PRINT crashed on stage.
    Second member of the class (after RENDER_3D_ENABLED); zero allowed."""
    import json
    r = subprocess.run(
        ["npx", "eslint", "src", "--format", "json"],
        capture_output=True, text=True, timeout=300, cwd=str(FE))
    assert r.returncode in (0, 1), f"eslint itself failed (exit {r.returncode}):\n{r.stderr[:2000]}"
    files = json.loads(r.stdout)
    undef = [f"{f['filePath']}:{m.get('line')} {m.get('message')}"
             for f in files for m in f.get("messages", [])
             if m.get("ruleId") == "no-undef"]
    assert not undef, "referenced-but-undefined variables in frontend src:\n" + "\n".join(undef)
