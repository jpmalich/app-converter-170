# GAP AUDIT — Elevation Render Spec v2 (2026-07-20)
Report only. Zero code changed. Full text mirrored in the chat handback; this file is the durable copy.

## 0. Cover-strip handback status
SHIPPED with wording (c) — "AI-measured, tape-verified: every read scored against physical field
measurements." Applied to METHODOLOGY_LINE, live-verified on the print route (92.2% bound from
Letrick demo tape_check.history), CLEAN stamp: `RECORDED: 2026-07-20 21:08 UTC · 894f214 · CLEAN`,
`RESULT: 1145 passed, 1 skipped`. CLOSED.

## 1. Direct answers — does the pipeline read it today?
- Chase depth from corner shots: **NO.** corner_locations carry {type, walls, position_frac,
  locator, elevated} only — position along ONE wall plane, no projection depth. Depth enters
  ONLY via human lp_appendage_dims (assumed | user_measured). No ESTIMATED-from-corner-shots rung exists.
- Rooflines: **PARTIAL.** Per-wall eave height + gable_triangle_height_ft; per-photo
  pitch_ratio_observed (integer N/12, iter 79j.87) — NO reconciled top-level pitch; roof_type
  (gable | hip | gable-shed-dormer). No hip/ridge geometry, no per-view roofline.
- Dormers: **YES.** dormers[] (face/width_ft/knee_wall_height_ft/offset_x_ft + per-photo
  provenance), dormer_details w/ bbox, on_dormer openings, dormer_profile_callout, dormer_face_sqft.
- Garages: **PARTIAL.** garage_door openings (type/size/bbox/count, schedule roll-up,
  garage_door_count). NO garage massing — walls[] is a closed 4-label set, no plane decomposition,
  no forward/lower projection.
- Porches: **NO geometry.** Only accent_profiles ('porch face', 'column wrap') w/ profile + approx_sqft.
  No posts, no porch roof, no porch-wall heights. (Porch-ceiling exists in materials only — matches spec D.)
- Recesses/bump-outs: **PARTIAL.** Inside/outside corner pairs detected w/ position_frac + locator
  ('recessed entry', 'chase left edge'); NO recess depth, NO return-wall dims.

## 2. Gap table (classification / effort / fixture / conflicts)
See chat handback of 2026-07-20 for the full 16-row table + conflict register (items C-1..C-7)
and the proposed priority order P1..P6. Key latent defect found during audit:
**garage_door and patio_door openings currently render as "Entry door" D# rows**
(`_bind_openings`: `is_door = "door" in eff_type`) — misclassification inside the closed
three-key contract, surfaces the moment any fixture has a garage/patio door.

## 3. Fixture availability notes
- Red house (dormers/story-and-a-half): estimate doc 673707d5… **MISSING from live estimates
  collection**; 3+ live dormer runs + archived fixture run 8ddb8932 persist. Elevation-sheet route
  404s without the estimate doc — restoration/re-pairing required before dormer render testing.
- 261 Haugh: no live or archived AI runs (recorded payloads live in tests only).
- Letrick Ranch demo + Letrick pin estate: full chase machinery, live.
- doug jones: generic AI-basis estimate, live run, 8 corner_locations.
