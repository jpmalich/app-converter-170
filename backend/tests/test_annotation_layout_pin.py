"""ANNOTATION LAYOUT PIN (ruled 2026-07-26): no overlapping text anywhere
on a sheet — callouts stack, lead, or abbreviate. The layout is a PURE
function (frontend/src/lib/annotationLayout.js); this pin executes it
under node with adversarial overlapping inputs and asserts the no-overlap
guarantee, fixed panels never moving, and the sheet routing its callouts
through it."""
import json
import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "lib" / "annotationLayout.js"
SHEET_JSX = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" /
             "pages" / "ElevationSheet.jsx").read_text()


def _run_layout(blocks, gap=4):
    script = f"""
const src = require('fs').readFileSync({json.dumps(str(LIB))}, 'utf8')
  .replace(/^export /gm, '');
eval(src);
const out = layoutAnnotations({json.dumps(blocks)}, {gap});
console.log(JSON.stringify(out));
"""
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def _no_overlaps(blocks, out, gap_ok=0.0):
    placed = [{"x": b["x"], "w": b["w"], "y": out[b["id"]]["y"], "h": b["h"]}
              for b in blocks]
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            x_ov = a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
            y_ov = a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]
            assert not (x_ov and y_ov), f"overlap: {a} vs {b}"


def test_overlapping_callouts_stack_without_overlap():
    # five blocks all fighting for the same top-left slot
    blocks = [{"id": f"b{i}", "x": 64, "y": 226, "w": 300, "h": 22} for i in range(5)]
    out = _run_layout(blocks)
    _no_overlaps(blocks, out)


def test_fixed_panels_never_move_and_callouts_clear_them():
    blocks = [
        {"id": "panel", "x": 90, "y": 202, "w": 420, "h": 36, "fixed": True},
        {"id": "ridge", "x": 95, "y": 207, "w": 220, "h": 10},
        {"id": "callout", "x": 64, "y": 210, "w": 400, "h": 34},
    ]
    out = _run_layout(blocks)
    assert out["panel"]["y"] == 202 and out["panel"]["moved"] is False
    assert out["ridge"]["moved"] is True
    _no_overlaps(blocks, out)


def test_disjoint_blocks_stay_put():
    blocks = [
        {"id": "a", "x": 64, "y": 226, "w": 200, "h": 22},
        {"id": "b", "x": 700, "y": 226, "w": 200, "h": 22},
    ]
    out = _run_layout(blocks)
    assert out["a"]["y"] == 226 and out["b"]["y"] == 226
    assert not out["a"]["moved"] and not out["b"]["moved"]


def test_sheet_routes_callouts_through_the_layout():
    assert "layoutAnnotations" in SHEET_JSX
    assert 'from "@/lib/annotationLayout"' in SHEET_JSX
    for block_id in ("dormerCallout", "ridgeE", "ridgeGable", "gableCallout",
                     "roofNote", "chaseProf"):
        assert f'"{block_id}"' in SHEET_JSX, block_id
    assert "dprof-" in SHEET_JSX
