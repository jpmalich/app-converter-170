"""SEND-117 ITEM 1 (Howard authorized 2026-08-23) — PAGE ROTATION:
detect and normalize a rotated raster BEFORE anything reads it.

THE SIGNAL IS THE UPRIGHT-SHARE COLLAPSE across the three OCR passes.
The bands come from the observed data across every page of all three
houses (32 pages), exactly as Ruling UU's axis band did:
  - rotated pages (dart, 10 of 11): upright share 6.0–24.6%, the
    winning rot pass 1.9–8.8× upright;
  - upright pages (Boni 11/11, Letrick 10/10): 33.9–52.3%.
  - THE GAP IS 24.6 → 33.9. The cut sits inside it: ROTATED ≤ 25.0
    with a dominant rot pass ≥ 1.5× upright; UPRIGHT ≥ 33.5; between
    the bands (dart p8 at 33.3 is a real member) → INDETERMINATE —
    NEVER NORMALIZED ON A GUESS, read both ways, disagreement reported.

180° IS DETECTABLE ONLY AS AN ANOMALY: there is no rot180 OCR pass, so
an upside-down sheet collapses ALL THREE shares with no dominant winner
— that lands INDETERMINATE with the anomaly named. Correction is not
derivable from the store; a fourth pass would be a build to rule on."""
from __future__ import annotations

import io
from collections import Counter

import numpy as np
from PIL import Image

ROTATED_MAX_SHARE = 25.0   # max observed rotated page: 24.6 (dart p9)
UPRIGHT_MIN_SHARE = 33.5   # min observed upright page: 33.9 (Boni p8/Letrick p3)
ROT_DOMINANCE = 1.5        # min observed on rotated pages: 1.9× (dart p9)
MIN_RUNS = 12              # below this the page has no signal to read

_PIL_ROT = {90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}


def pass_counts(runs: list) -> Counter:
    return Counter(str((u or {}).get("src") or "?") for u in runs or [])


def rotation_verdict(counts) -> dict:
    """Verdict from per-pass run counts. rotation_ccw is the CCW degrees
    the raster must rotate to stand upright (the winning pass's angle)."""
    up = int(counts.get("upright", 0))
    r90 = int(counts.get("rot90", 0))
    r270 = int(counts.get("rot270", 0))
    n = up + r90 + r270
    if n < MIN_RUNS:
        return {"verdict": "INDETERMINATE", "rotation_ccw": None,
                "upright_share": round(100.0 * up / n, 1) if n else None,
                "why": f"only {n} runs — below the {MIN_RUNS}-run signal floor"}
    share = round(100.0 * up / n, 1)
    dom_angle, dom = (90, r90) if r90 >= r270 else (270, r270)
    if share <= ROTATED_MAX_SHARE:
        # share ≤ 25% forces rots ≥ 3× upright, so the winning rot pass
        # is always ≥ 1.5× upright — every low-share page with signal is
        # decisively rotated. A true 180° page reads garbage in ALL
        # passes and lands INDETERMINATE via the signal floor or the gap
        # — 180 IS NOT INDEPENDENTLY DETECTABLE with three passes; a
        # rot180 pass would be a build to rule on.
        return {"verdict": "ROTATED", "rotation_ccw": dom_angle,
                "upright_share": share,
                "why": f"upright {share}% ≤ {ROTATED_MAX_SHARE} and "
                       f"rot{dom_angle} dominates {dom}:{up}"}
    if share >= UPRIGHT_MIN_SHARE:
        return {"verdict": "UPRIGHT", "rotation_ccw": None,
                "upright_share": share, "why": f"upright {share}%"}
    return {"verdict": "INDETERMINATE", "rotation_ccw": None,
            "upright_share": share,
            "why": (f"upright {share}% falls in the gap "
                    f"({ROTATED_MAX_SHARE}–{UPRIGHT_MIN_SHARE}) — never "
                    "normalized on a guess; read both ways")}


def detect_image_bytes(img_bytes: bytes, ocr_runs_fn) -> dict:
    """Full-resolution detection (the bands were calibrated at full
    resolution — a downscale changes the shares)."""
    with Image.open(io.BytesIO(img_bytes)) as im:
        arr = np.array(im.convert("RGB"))
    counts = Counter()
    counts["upright"] = len(ocr_runs_fn(arr))
    counts["rot90"] = len(ocr_runs_fn(np.rot90(arr, 1)))
    counts["rot270"] = len(ocr_runs_fn(np.rot90(arr, 3)))
    v = rotation_verdict(counts)
    v["counts"] = dict(counts)
    return v


def rotate_image_bytes(img_bytes: bytes, rotation_ccw: int) -> bytes:
    """Lossless-transpose rotation, re-encoded JPEG (what the pipeline
    carries). Validated on dart p5: 9.6% upright → 74.2% after CCW 270."""
    with Image.open(io.BytesIO(img_bytes)) as im:
        out = im.convert("RGB").transpose(_PIL_ROT[int(rotation_ccw)])
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=88)
        return buf.getvalue()


def remap_loc_ccw(loc: dict, rotation_ccw: int) -> dict:
    """Remap a percent-box from the original raster frame into the frame
    of the raster rotated CCW by `rotation_ccw`. Percentages survive the
    axis swap, so no page dims are needed."""
    x, y = float(loc["x_pct"]), float(loc["y_pct"])
    w, h = float(loc.get("w_pct") or 0), float(loc.get("h_pct") or 0)
    r = int(rotation_ccw) % 360
    if r == 90:
        return {"x_pct": round(y, 2), "y_pct": round(100.0 - x - w, 2),
                "w_pct": round(h, 2), "h_pct": round(w, 2)}
    if r == 270:
        return {"x_pct": round(100.0 - y - h, 2), "y_pct": round(x, 2),
                "w_pct": round(h, 2), "h_pct": round(w, 2)}
    if r == 180:
        return {"x_pct": round(100.0 - x - w, 2),
                "y_pct": round(100.0 - y - h, 2),
                "w_pct": round(w, 2), "h_pct": round(h, 2)}
    return dict(loc)


_SRC_ANGLE = {"upright": 0, "rot90": 90, "rot180": 180, "rot270": 270}
_ANGLE_SRC = {v: k for k, v in _SRC_ANGLE.items()}


def normalize_runs(runs: list, rotation_ccw: int) -> list:
    """A normalized COPY of a page's runs: boxes remapped into the
    upright frame, src relabeled to the pass each run would need after
    the rotation ((old − rotation) mod 360). The store itself is never
    mutated — evidence stays raw; this is a derived view."""
    out = []
    for u in runs or []:
        if not isinstance(u, dict):
            continue
        nu = dict(u)
        nu["loc"] = remap_loc_ccw(u.get("loc") or {}, rotation_ccw)
        old = _SRC_ANGLE.get(str(u.get("src")), 0)
        nu["src"] = _ANGLE_SRC[(old - int(rotation_ccw)) % 360]
        out.append(nu)
    return out
