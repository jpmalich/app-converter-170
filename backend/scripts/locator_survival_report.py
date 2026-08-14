#!/usr/bin/env python3
"""LOCATOR SURVIVAL REPORT (Howard ruled 2026-08-14, on Emergent's terms).

WHAT IT IS. After any change to the locator or a kill path, this counts
HOW MANY KNOWN-PRINTED DIMENSIONS STILL LOCATE. It would have caught all
three over-corrections (fraction skeleton, anchor gate, segment over-kill)
on the day they shipped instead of on the day Howard walked.

THE RULES IT LIVES BY (all four are the ruling, not preferences):
  1. REPORT ONLY. No pass/fail. Nothing branches on the number. It always
     exits 0. It is an observation, never a gate.
  2. NO THRESHOLD IS EVER NUDGED TO RAISE THE COUNT. If either of us
     catches ourselves twiddling a radius or a skeleton distance to make
     survivors go up, that is the barred move (tuning by instrument) —
     stop and find the PRINCIPLE, the way "drawings carry no text labels"
     was the principle behind the last fix.
  3. STANDALONE SCRIPT. Never a pytest assertion.
  4. IT NEVER RUNS ON HOWARD'S HOUSE ALONE. A survival number measured
     only on Boni implicitly optimises for Boni — the purity rider
     violated by instrument. The reference set below is SYNTHETIC and
     non-protected; its pre-kill evidence is inherent (built here, never
     pruned). A real house may be ADDED as one more reference later, but
     only with its pre-kill evidence captured deliberately, and never as
     the only reference.

The reference sheets are rendered deterministically from a spec, so the
"committed reference set" is this code. The numbers below are OBSERVATION
TARGETS FOR A COUNT — they are never assertion targets and nothing is
tuned to make them pass.

Run:  python3 scripts/locator_survival_report.py
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(str(Path(__file__).resolve().parents[1] / ".env"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import routes.ai_blueprint as ab  # noqa: E402


def _font(size):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _render(size, placements):
    """placements: list of (text, x, y). Black text on white — a clean
    stand-in for a plan sheet."""
    w, h = size
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    fnt = _font(40)
    for text, x, y in placements:
        d.text((x, y), text, fill="black", font=fnt)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# THE COMMITTED, NON-PROTECTED REFERENCE SET (synthetic — not Boni).
# Numbers deliberately unlike Howard's house so nothing can drift toward it.
# ---------------------------------------------------------------------------
REFERENCES = [
    {
        "name": "synthetic_front_elevation (drawing — presence-only)",
        "useful_for": "elevation",
        "sheet_title": "FRONT ELEVATION",
        "size": (1400, 1000),
        # Dimensions sit as GEOMETRY, nowhere near a 'MAIN BODY' text label.
        "placements": [
            ("FRONT ELEVATION", 60, 40),
            ("32'-0\"", 300, 620),      # main body — dimension line, no label
            ("21'-6\"", 900, 620),      # wing — dimension line, no label
            ("14'-0\"", 300, 720),      # a gutter run
        ],
        "evidence": {
            "walls.front.segments.main body 2-story.width_ft":
                {"v": 32.0, "page": 1, "from": "32'-0\""},
            "walls.front.segments.wing 1-story.width_ft":
                {"v": 21.5, "page": 1, "from": "21'-6\""},
            "gutter_runs.front main.lf":
                {"v": 14.0, "page": 1, "from": "14'-0\""},
            # FABRICATION CONTROL — never drawn; must NOT locate.
            "walls.left.width_ft":
                {"v": 88.0, "page": 1, "from": "88'-0\""},
        },
        "drawn": {
            "walls.front.segments.main body 2-story.width_ft",
            "walls.front.segments.wing 1-story.width_ft",
            "gutter_runs.front main.lf",
        },
        "controls": {
            "walls.left.width_ft": "absent from the sheet — fabrication, must stay killed",
        },
    },
    {
        "name": "synthetic_window_schedule (table — label-bound stays strict)",
        "useful_for": "schedule",
        "sheet_title": "WINDOW SCHEDULE",
        "size": (1200, 800),
        # On a schedule the label sits WITH its number — proximity is real
        # and earns its keep. KITCHEN 36" is a labelled row; the bare 40"
        # far from any label is a misattribution the strict gate must
        # still refuse (proving the tight radius survived on tables).
        "placements": [
            ("WINDOW SCHEDULE", 60, 40),
            ("KITCHEN", 140, 300),
            ("144\"", 360, 300),         # ~200px from its KITCHEN label
            ("132\"", 140, 620),         # bare number, no label near it
        ],
        "evidence": {
            "windows.kitchen.width_in": {"v": 144.0, "page": 1, "from": "144\""},
            # STRICTNESS CONTROL — drawn, but with no label near it.
            "windows.bath.width_in": {"v": 132.0, "page": 1, "from": "132\""},
        },
        "drawn": {"windows.kitchen.width_in"},
        "controls": {
            "windows.bath.width_in": "unlabelled on a schedule — must stay strict",
        },
    },
]


def _located(ev_entry):
    if not isinstance(ev_entry, dict):
        return False
    if ev_entry.get("loc"):
        return True
    return any(isinstance(s, dict) and s.get("loc")
               for s in (ev_entry.get("srcs") or []))


def run():
    print("=" * 72)
    print("LOCATOR SURVIVAL REPORT — REPORT ONLY, NO PASS/FAIL, NEVER TUNED")
    print("A count of how many known-printed dimensions still locate.")
    print("Reference set is synthetic & non-protected — never Boni alone.")
    print("=" * 72)
    grand_located = grand_known = 0
    controls_ok = controls_total = 0
    for ref in REFERENCES:
        img = _render(ref["size"], ref["placements"])
        ev = {k: dict(v) for k, v in ref["evidence"].items()}   # pre-kill copy
        raw = {"sheets_identified": [{
            "page": 1, "sheet_title": ref["sheet_title"],
            "useful_for": ref["useful_for"],
        }]}
        ab._ocr_locate_evidence(ev, [img], raw)
        drawn = ref["drawn"]
        controls = ref.get("controls", {})
        known_located = sum(1 for p in drawn if _located(ev.get(p)))
        grand_located += known_located
        grand_known += len(drawn)
        print(f"\n• {ref['name']}  [{ref['useful_for']}]")
        print(f"  survivors: {known_located} / {len(drawn)} known-printed dims located")
        for p in sorted(drawn):
            tag = ("LOCATED" if _located(ev.get(p)) else "killed ")
            print(f"    {tag}  {ev[p].get('from'):<10} {p}")
        for p in sorted(controls):
            still_killed = not _located(ev.get(p))
            controls_total += 1
            controls_ok += 1 if still_killed else 0
            mark = "ok" if still_killed else "LEAK"
            print(f"    control[{mark}]  {ev[p].get('from'):<8} {p}  — {controls[p]}")
    print("\n" + "-" * 72)
    print(f"TOTAL SURVIVORS: {grand_located} / {grand_known} known-printed dimensions located")
    print(f"CONTROLS HELD:   {controls_ok} / {controls_total} absent/misattributed dims stayed killed")
    print("Directional only. Do not adjust any threshold to move these numbers.")
    print("-" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(run())
