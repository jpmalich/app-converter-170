"""Phase 3 re-file — LAYER B: app conventions applied to the KEY's geometry.
Read-only engine invocation (code frozen). Key geometry translated to the
app measurement schema; corner inventory per the key's stated locations."""
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import json
import sys
sys.path.insert(0, "/app/backend")

from lp_package import assemble_lp_package, corner_sticks_for_length

KEY_MEASUREMENTS = {
    # key: raw 2,098.5 sqft, no window deductions (matches app convention:
    # siding_sqft carries openings)
    "siding_sqft": 2098.5,
    "siding_with_openings_sqft": 2098.5,
    "eaves_lf": 108.0,
    "rakes_lf": 69.6,           # 4 × 17.4
    "starter_lf": 165.0,        # 168 − 3' entry (key's deduction)
    "window_count": 10,
    "entry_door_count": 1,
    "patio_door_count": 1,
    "garage_door_count": 0,
    "opening_count": 12,
    "_ai_avg_wall_height_ft": 9.0,
}

# Key corner inventory: 4 house corners (≤16', 1 stick each per key),
# chimney 2 full-height edges 18.91' + 2 above-roofline edges (~55 LF
# chimney total → ~8.6' each), ISC 2 chase wall junctions at wall height.
H_FULL = 18.91
H_ABOVE = round((55.0 - 2 * H_FULL) / 2, 2)  # ≈ 8.59
KEY_CORNERS = (
    [{"type": "outside", "walls": [], "tier": "confirmed", "locator": f"house corner {i+1}"} for i in range(4)]
    + [{"type": "outside", "walls": ["chimney_full"], "tier": "confirmed", "locator": "chimney full-height edge"} for _ in range(2)]
    + [{"type": "outside", "walls": ["chimney_above"], "tier": "confirmed", "locator": "chimney above-roofline edge"} for _ in range(2)]
    + [{"type": "inside", "walls": [], "tier": "confirmed", "locator": f"chase wall junction {i+1}"} for i in range(2)]
)
KEY_WALL_HEIGHTS = {"chimney_full": H_FULL, "chimney_above": H_ABOVE}

pkg = assemble_lp_package(KEY_MEASUREMENTS, KEY_CORNERS, KEY_WALL_HEIGHTS)
targets = ["38 Series Lap", "540 Series OSC", '440 Series Trim 4/4" x 4"',
           '540 Series Trim 5/4" x 4"', '440 Series Trim 4/4" x 8"',
           "Soffit 16 x 16 Vented", "Starter"]
print("H_ABOVE per edge:", H_ABOVE)
for l in pkg["lines"]:
    if any(t in l["name"] for t in targets):
        print(f"{l['name']:46s} qty {l['qty']:>6} {l['unit']:4s} | {(l.get('note') or '')[:160]}")
print("---")
print("osc sticks on key inventory:",
      corner_sticks_for_length([9, 9, 9, 9, H_FULL, H_FULL, H_ABOVE, H_ABOVE], 16.0))
