"""RULING N/P/S — CENSUS PIN: the gateway guard against a sixth sibling
(Howard ruled 2026-08-14 send-17, hardened send-18 P/S).

THE RULE (positive / gateway form, send-18 Q): every priced path that needs
a wall width or height MUST obtain it through the status-carrying accessors
`wall_width_for_pricing` / `wall_height_for_pricing` (or the shared
`wall_body_gross_sqft`). A raw read of a wall-dimension source
(`width_ft` / `height_ft` / `avg_wall_height_ft` / `_ai_avg_wall_height_ft`)
anywhere ELSE in a priced module is a VIOLATION — a value that can outlive
its source without carrying its status.

HOW IT DETECTS (send-18 P condition, "does it SCAN or check known sites"):
it SCANS. An AST walk of every priced module collects each wall-dimension
read OUTSIDE the sanctioned accessors, keyed on FILE + ENCLOSING FUNCTION +
SYMBOL (line numbers are DELIBERATELY excluded — they shift on any edit and
force wholesale re-baselines, which is the same as deleting the pin). The
collected set is diffed against a recorded BASELINE catalog. A NEW read —
one not in the baseline — FAILS the test and is NAMED. A baseline diff gives
"fail on a genuinely new read" for free; a list-check would not.

THE RATCHET TURNS ONE WAY (send-18 P condition 1): entries may be REMOVED
(a Ruling-N conversion deletes its own baseline line), never ADDED. Adding
an entry requires an explicit ruling in a send, not a passing test. That
sentence lives at the TOP OF THE BASELINE FILE, where the person about to
append their new read will read it. A new read therefore cannot go green by
appending — it goes green only by routing through the gateway.

GREEN MUST NOT READ AS CLEAN (send-18 P condition 4): every run prints
"census pin GREEN — N baselined reads, K PENDING_CONVERSION (...)". GREEN
means NO NEW READS — which is what it actually proves, not that the three
known money-bearing readers are fixed.

THREE CLASSES (send-18 S): the baseline is not a flat list. Each entry is
classed by the discriminator "does this read feed a PRICED quantity" — never
"is it a wall dim":
  PENDING_CONVERSION        — leaves under Ruling Q as it converts
  OUT_OF_SCOPE_N_BUT_PRICED — feeds money via a non-wall dimension (dormer
                              fascia) or pitch input; candidate for a
                              follow-on ruling, not built against yet
  AUDITED_SAFE              — genuinely does not reach a priced quantity

OUT-OF-SCAN FINDING (send-18, reported not silently dropped): the BATTEN
reader Howard names as the third PENDING_CONVERSION does NOT appear in this
scan. Its height is `_bb_wall_height_ft` — a HUMAN checklist scalar summed in
lp_package_routes._apply_flag_checklist and consumed in routes/hover.py
(_bb_batten_sticks), which is outside the four scanned priced modules, and
bb_batten_lf takes it as a PARAMETER, not a raw `height_ft` read. The silent
zero there is the `... or 0` fallback on an unset checklist (the +1-run term
vanishes). It is tracked in the baseline header as a NOTED finding awaiting a
ruling on whether hover.py joins PRICED_MODULES; converted under Ruling Q at
the formula boundary regardless.
"""
from __future__ import annotations

import ast
import warnings
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

PRICED_MODULES = ["lp_package.py", "lp_smartside_formulas.py",
                  "measure_staging.py", "profile_callouts.py"]

# Raw reads INSIDE these functions are sanctioned — they ARE the
# status-carrying accessors every other priced reader must route through.
SANCTIONED_FUNCS = {"wall_body_gross_sqft", "wall_width_for_pricing",
                    "wall_height_for_pricing"}

WALL_DIM_SOURCES = {"width_ft", "height_ft",
                    "avg_wall_height_ft", "_ai_avg_wall_height_ft"}

BASELINE_FILE = Path(__file__).parent / "_raw_wall_dim_baseline.txt"


def _scan(path: Path) -> set[str]:
    """Return {"module::function::symbol"} for every wall-dimension read
    outside a sanctioned accessor. Line numbers are intentionally dropped."""
    tree = ast.parse(path.read_text(), filename=str(path))

    func_of: dict[int, str] = {}

    def _label(node, fname):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.FunctionDef):
                for n in ast.walk(ch):
                    func_of[getattr(n, "lineno", -1)] = ch.name
                _label(ch, ch.name)
            else:
                _label(ch, fname)

    _label(tree, "<module>")

    sanctioned_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in SANCTIONED_FUNCS:
            for n in ast.walk(node):
                sanctioned_lines.add(getattr(n, "lineno", -1))

    hits: set[str] = set()
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            name = node.value
        if name in WALL_DIM_SOURCES and node.lineno not in sanctioned_lines:
            hits.add(f"{path.stem}::{func_of.get(node.lineno, '<module>')}::{name}")
    return hits


def _all_offenders() -> set[str]:
    out: set[str] = set()
    for m in PRICED_MODULES:
        out |= _scan(BACKEND / m)
    return out


def _load_baseline() -> dict[str, str]:
    """key -> class. Reads the classed baseline catalog; a line is
    'module::function::symbol | reason' under a '# [CLASS]' header."""
    entries: dict[str, str] = {}
    cls = "AUDITED_SAFE"
    if not BASELINE_FILE.exists():
        return entries
    for ln in BASELINE_FILE.read_text().splitlines():
        s = ln.strip()
        if s.startswith("# ["):
            cls = s[3:s.index("]")]
            continue
        if not s or s.startswith("#"):
            continue
        key = s.split("|", 1)[0].strip()
        entries[key] = cls
    return entries


def test_no_new_raw_wall_dim_read_appears_in_a_priced_path():
    current = _all_offenders()
    baseline = _load_baseline()

    new = sorted(current - set(baseline))
    assert not new, (
        "NEW raw wall-dimension read in a priced path (Ruling N/P — a sixth "
        "sibling). The ratchet turns ONE WAY: do NOT append it to the "
        "baseline to go green. Route it through wall_width_for_pricing / "
        "wall_height_for_pricing so its status propagates, and it disappears "
        "from this scan:\n  " + "\n  ".join(new))

    # GREEN MUST NOT READ AS CLEAN — surface the pending count every run.
    pend = sorted(k for k, c in baseline.items() if c == "PENDING_CONVERSION")
    n = len(current & set(baseline))
    summary = (f"census pin GREEN — {n} baselined reads, {len(pend)} "
               f"PENDING_CONVERSION ({', '.join(pend) or 'none'})")
    print("\n" + summary)
    (BACKEND / "../memory/census_pin_status.txt").resolve().write_text(summary + "\n")
    warnings.warn(summary, stacklevel=1)


def test_ratchet_baseline_entries_still_exist_or_are_deliberately_gone():
    """A one-way ratchet: a baseline entry that no longer scans is a
    CONVERSION and is welcome — but the stale line must be pruned so the
    catalog never claims a read that is gone (a false PENDING_CONVERSION
    hides that the sibling was already fixed). Deleting the line IS the
    Ruling-Q hand-off, so this fails loudly until the converter prunes it."""
    current = _all_offenders()
    baseline = _load_baseline()
    stale = sorted(set(baseline) - current)
    assert not stale, (
        "A baselined read no longer scans — a conversion happened. Prune "
        "its line from _raw_wall_dim_baseline.txt citing Ruling N/Q (the "
        "ratchet turns one way, and a stale entry lies about a live "
        "sibling):\n  " + "\n  ".join(stale))


if __name__ == "__main__":
    for x in sorted(_all_offenders()):
        print(x)
