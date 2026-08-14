#!/usr/bin/env python3
"""DRAWN-GEOMETRY TOKEN REPORT — SEND-12 ruling 3 part 2 (2026-08-14).

WHAT IT IS. The content-based override Howard ruled for the two deny-list
entries (schedule / cover): a page mistyped as a table but actually
carrying drawn geometry must be re-checked against its OWN content so the
tight radius does not kill every dimension on it. The proposed signal is
the count of feet-inch DIMENSION tokens the OCR reads on the page
(`ab._feet_inch_dim_tokens`).

THE RULES IT LIVES BY (the ruling, not preferences):
  1. REPORT ONLY. No pass/fail, always exits 0. Nothing branches on the
     number. It is an observation used to SEE whether drawings and
     schedules separate cleanly on this signal.
  2. NO THRESHOLD IS INVENTED HERE. If drawings and schedules separate
     cleanly the threshold picks itself; if they do not, we ship the
     PLAIN deny-list and say so. Nothing is tuned to make a number land.
  3. IT NEEDS A REAL PLAN SET. Boni cannot validate this — none of its
     eleven pages types as schedule or cover (Howard's own note). The
     synthetic sheets below are a PREVIEW of the separation, not the
     validation. A real plan set with genuine schedule/cover pages must
     be added before the override is wired.

Run:  python3 scripts/drawn_geometry_token_report.py
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
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    fnt = _font(38)
    for text, x, y in placements:
        d.text((x, y), text, fill="black", font=fnt)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# Synthetic PREVIEW sheets — deliberately unlike Boni. Two genuine
# drawings, two genuine tables, and one MISTYPED page (a floor plan the
# model wrongly typed "schedule") — the exact door the override guards.
SHEETS = [
    ("elevation (drawing)", "elevation", (1400, 1000), [
        ("FRONT ELEVATION", 60, 40),
        ("32'-0\"", 300, 620), ("21'-6\"", 700, 620), ("14'-0\"", 1050, 620),
        ("9'-1 1/2\"", 300, 720), ("18'-0\"", 700, 720), ("40'-0\"", 1050, 720),
        ("8'-0\"", 300, 820), ("24'-0\"", 700, 820),
    ]),
    ("floor_plan (drawing)", "floor_plan", (1400, 1000), [
        ("FIRST FLOOR PLAN", 60, 40),
        ("58'-0\"", 300, 500), ("30'-0\"", 700, 500), ("12'-6\"", 1050, 500),
        ("16'-0\"", 300, 700), ("10'-0\"", 700, 700), ("42'-0\"", 1050, 700),
    ]),
    ("window_schedule (table)", "schedule", (1200, 900), [
        ("WINDOW SCHEDULE", 60, 40),
        ("MARK", 80, 160), ("SIZE", 380, 160), ("QTY", 780, 160),
        ("SH340", 80, 260), ("3040", 380, 260), ("4", 780, 260),
        ("SH360", 80, 360), ("3060", 380, 360), ("2", 780, 360),
        ("DH28", 80, 460), ("2846", 380, 460), ("6", 780, 460),
    ]),
    ("cover (title page)", "cover", (1200, 900), [
        ("SMITH RESIDENCE", 200, 200),
        ("2692 TIMBERGLEN DRIVE", 200, 320),
        ("SHEET INDEX", 200, 440), ("A1 A2 A3 S1 M1", 200, 520),
    ]),
    ("MISTYPED floor plan wrongly typed schedule", "schedule", (1400, 1000), [
        ("SECOND FLOOR PLAN", 60, 40),
        ("34'-0\"", 300, 500), ("22'-6\"", 700, 500), ("11'-0\"", 1050, 500),
        ("18'-0\"", 300, 700), ("9'-0\"", 700, 700), ("40'-0\"", 1050, 700),
    ]),
]


def run():
    print("=" * 74)
    print("DRAWN-GEOMETRY TOKEN REPORT — REPORT ONLY, NO THRESHOLD INVENTED")
    print("Signal = count of feet-inch dimension tokens OCR reads per page.")
    print("PREVIEW on synthetic sheets — a REAL plan set is still required.")
    print("=" * 74)
    rows = []
    for name, kind, size, placements in SHEETS:
        img = _render(size, placements)
        import numpy as np
        with Image.open(io.BytesIO(img)) as im:
            arr = np.array(im.convert("RGB"))
        runs = ab._ocr_runs(arr)
        n = ab._feet_inch_dim_tokens(runs)
        total = len(runs)
        rows.append((name, kind, n, total))
        print(f"  useful_for={kind:9s}  dim_tokens={n:3d}  of {total:3d} runs"
              f"   [{name}]")
    print("-" * 74)
    draw = [r for r in rows if r[1] in ("elevation", "floor_plan", "roof")]
    sched = [r for r in rows if r[1] in ("schedule", "cover")]
    if draw and sched:
        dmin = min(r[2] for r in draw)
        smax = max(r[2] for r in sched)
        print(f"  drawings min dim_tokens = {dmin}")
        print(f"  tables   max dim_tokens = {smax}")
        if dmin > smax:
            print(f"  SEPARATION: clean on this synthetic preview "
                  f"(a boundary sits in ({smax}, {dmin}]).")
            print("  BUT the mistyped floor plan below shows the real risk.")
        else:
            print("  SEPARATION: NOT clean on this preview.")
    print("  NOTE: the MISTYPED page is a floor plan typed 'schedule'. Its")
    print("  dim_token count matches the real drawings — that is exactly the")
    print("  content signal the override would use. It cannot be trusted")
    print("  until a REAL plan set with genuine schedule/cover pages is")
    print("  measured. Until then: SHIP THE PLAIN DENY-LIST (override held).")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
