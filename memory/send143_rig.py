"""SEND-143 ITEM 2 RIG — the trim report's NUMBERS, taken on a real photo.

Draws a small honest rig on EST-373526's FRONT photo through the live API
(scale + one body zone + one boxed window + one gable triangle), reads the
Phase-1 quantities back, then computes what EACH PHASE-2 TRIM WOULD PRINT
using formulas that are NOT YET WIRED — so the report can carry numbers
before a line of production code is written.

DELETES EVERY MARK AND THE SCALE AT THE END. Writes nothing else. No
apply. EST-886440 is never touched.
"""
import json
import math
import subprocess
import sys

sys.path.insert(0, "/app/backend")
from creds_for_tests import TEST_EMAIL, TEST_PASSWORD  # noqa: E402

API = [l.split("=", 1)[1].strip() for l in open("/app/frontend/.env")
       if l.startswith("REACT_APP_BACKEND_URL")][0]
EST = "8f95c9c2-add9-416a-92f3-786a4ea2ce83"          # EST-373526
PHOTO = "ai_c7b431a447e04426b92a99870a02dddf.jpg"
J = "/tmp/send143_cj.txt"


def curl(method, path, body=None, extra=()):
    args = ["curl", "-s", "-b", J, "-X", method, f"{API}{path}", *extra]
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out[:300]}


subprocess.run(["curl", "-s", "-c", J, "-X", "POST", f"{API}/api/auth/login",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"email": TEST_EMAIL,
                                  "password": TEST_PASSWORD})],
               capture_output=True, text=True)

# ── the rig ────────────────────────────────────────────────────────────
# scale: a 120 px span typed as 10'-0" → 1 in/px  (12 in per foot / 12 px)
print(curl("PUT", f"/api/estimates/{EST}/photo-takeoff/scale", {
    "photo_key": PHOTO,
    "anchor": {"p1": {"x": 100, "y": 900}, "p2": {"x": 220, "y": 900},
               "inches": 120},
    "tape_inches": 120}).get("scale"))

ids = []
BODY = [{"x": 100, "y": 500}, {"x": 460, "y": 500},
        {"x": 460, "y": 860}, {"x": 100, "y": 860}]          # 30' x 30'
WIN = [{"x": 200, "y": 600}, {"x": 236, "y": 600},
       {"x": 236, "y": 672}, {"x": 200, "y": 672}]           # 3' x 6'
GABLE = [{"x": 100, "y": 500}, {"x": 280, "y": 380},
         {"x": 460, "y": 500}]                               # 30' w, 10' rise

for kind, shape, pts, label in (
        ("siding_zone", "poly", BODY, "front body"),
        ("opening", "rect", WIN, "front window"),
        ("gable", "poly", GABLE, "front gable")):
    r = curl("POST", f"/api/estimates/{EST}/photo-takeoff/marks",
             {"photo_key": PHOTO, "kind": kind, "shape": shape,
              "points": pts, "label": label})
    mid = (r.get("mark") or {}).get("id")
    ids.append(mid)
    curl("PATCH", f"/api/estimates/{EST}/photo-takeoff/marks/{mid}",
         {"status": "confirmed"})
    print(f"  {kind:14} -> {mid} confirmed")

got = curl("GET", f"/api/estimates/{EST}/photo-takeoff?photo_key={PHOTO}")
q = ((got.get("per_photo") or {}).get(PHOTO) or {}).get("quantities") or {}
marks = [m for m in (got.get("marks") or []) if m.get("photo_key") == PHOTO]
print("\nPHASE 1 READS BACK:")
for k in ("scale_basis", "plane_basis", "siding_sqft", "opening_count",
          "opening_sqft", "gable_sqft", "gable_rows"):
    print(f"  {k}: {q.get(k)}")

# ── the DRY RUN — formulas not yet wired anywhere ──────────────────────
ipp = 120.0 / 120.0                      # inches per pixel, from the tape
ft_per_px = ipp / 12.0


def seg_ft(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"]) * ft_per_px


print("\nDRY RUN — WHAT EACH PHASE-2 TRIM WOULD PRINT ON THIS RIG:")
conf = [m for m in marks if m.get("status") == "confirmed"]
opens = [m for m in conf if m["kind"] == "opening" and len(m["points"]) >= 3]
gables = [m for m in conf if m["kind"] == "gable"]
zones = [m for m in conf if m["kind"] == "siding_zone"]

# J-channel — perimeter of each drawn opening box
if opens:
    tot = 0.0
    for m in opens:
        p = m["points"]
        per = sum(seg_ft(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))
        tot += per
        print(f"  J-CHANNEL  {m.get('label')}: perimeter "
              f"{round(per, 2)} LF  (box {round(seg_ft(p[0], p[1]), 2)} ft x "
              f"{round(seg_ft(p[1], p[2]), 2)} ft)")
    print(f"  J-CHANNEL  TOTAL: {round(tot, 2)} LF")
else:
    print("  J-CHANNEL  —  (no confirmed BOXED opening on this photo)")

# Rake — the two sloped sides of the drawn gable triangle
if gables:
    tot = 0.0
    for m in gables:
        p = m["points"]
        left, peak, right = p[0], p[1], p[2]
        rake = seg_ft(left, peak) + seg_ft(peak, right)
        base = seg_ft(left, right)
        tot += rake
        print(f"  GABLE RAKE {m.get('label')}: {round(rake, 2)} LF "
              f"(2 sides of the drawn triangle; eave span {round(base, 2)} ft)")
    print(f"  GABLE RAKE TOTAL: {round(tot, 2)} LF")
else:
    print("  GABLE RAKE —  (no confirmed gable triangle on this photo)")

# What the other four would have to read, and cannot
print("  STARTER    —  (no wall BASE mark exists; a zone polygon does not "
      "declare which edge is the base)")
print("  OUT CORNER —  (no corner mark exists, and no confirmed wall HEIGHT)")
print("  IN CORNER  —  (same)")
print("  SOFFIT     —  (no EAVE mark exists; a roof edge would have to be "
      "invented)")
print("  FASCIA(H)  —  (same — only the GABLE RAKE is actually drawn)")
if zones:
    p = zones[0]["points"]
    print(f"\n  for the record, the body zone's own edges: "
          f"{[round(seg_ft(p[i], p[(i+1) % len(p)]), 2) for i in range(len(p))]} ft")

# ── teardown ──────────────────────────────────────────────────────────
for mid in ids:
    curl("DELETE", f"/api/estimates/{EST}/photo-takeoff/marks/{mid}")
curl("PUT", f"/api/estimates/{EST}/photo-takeoff/scale",
     {"photo_key": PHOTO, "clear": True})
after = curl("GET", f"/api/estimates/{EST}/photo-takeoff?photo_key={PHOTO}")
left = [m for m in (after.get("marks") or []) if m.get("photo_key") == PHOTO]
print(f"\nTEARDOWN: marks left on this photo = {len(left)}, "
      f"scale = {(after.get('scale') or {}) or None}")
