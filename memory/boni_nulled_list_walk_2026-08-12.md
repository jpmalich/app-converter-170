# FULL NULLED LIST — BONI FRESH READ (5df22e6d) AFTER SEND-9 CALIBRATION

Howard ruled 2026-08-12 send-9 item 5: "Give me the full nulled list. All 19 paths, each with its VALUE, its QUOTE, and its REFUSAL REASON. I will tell you which are printed and true."

Under the recalibrated gate (sheet-scoped for cardinal wall paths + BACK↔REAR synonym + elevation/floor_plan sheet-kind acceptance), the counts changed:

| Slice | send-8 | send-9 (recalibrated) |
|:---|---:|---:|
| Located under gate | 18 | **22** |
| Refused | 29 | 25 |
| Fabricated (killed) | — | **5** |
| Unverified (kept, marked, not fed to money) | (all merged as nulled) | **10** |

**Howard's canary:** `walls.front.width_ft = 58'-0"` now LOCATES under the sheet-scoped rule (was falsely nulled under send-8). The instrument no longer kills that dim.

## FABRICATED — killed on `_dim_fabricated` (5 records)

The quoted normalized string does NOT appear in OCR anywhere on the claimed page in any orientation. The seam books it under `dims_nulled_quote_fabricated`.

| path | value | quote | reason | Howard verdict |
|:---|---:|:---|:---|:---|
| walls.left.width_ft | 39.0 | `39'-0"` | quote norm not present in OCR on p6 (FIRST FLOOR PLAN) | ? |
| walls.right.width_ft | 39.0 | `39'-0"` | quote norm not present in OCR on p6 | ? |
| porch.porch_width_ft | 32.5 | `32'-5 1/2"` | quote norm not present in OCR on p6 | probable fabrication (see purity: porch is 16'6") |
| roof_planes.porch.eave_lf | 50.0 | `32'-5 1/2"` | (same quote propagated) | probable fabrication |
| gutter_runs.porch.lf | 32.5 | `32'-5 1/2"` | (same quote propagated) | probable fabrication |

**Concern for Howard's review**: the two `walls.left/right.width_ft = 39'-0"` are flagged fabricated because OCR did not find "390" on page 6. If the plans DO print 39'-0" for those walls and OCR simply missed the token (possible on a dense floor-plan sheet), these are UNVERIFIED not FABRICATED. Only Howard can call that.

## UNVERIFIED — kept on `_dim_unverified`, marked on the card, NOT fed to money (10 records)

The quoted string exists in OCR but not within radius of the labelled feature anchor. The value rides `_dim_unverified` so the readback shows it MARKED unverified; downstream money pipes see None. Seam books it under `dims_nulled_quote_unverified`.

| path | value | quote | reason |
|:---|---:|:---|:---|
| roof_planes.main.rake_lf | 82.0 | `39'-0"; 7/12` | no feature anchor `['main']` on page |
| roof_planes.bonus room.rake_lf | 28.0 | `10/12` | matched but no candidate within radius of `['bonus room']` |
| roof_planes.garage.eave_lf | 70.0 | `35'-0" x 2 (front and back garage eaves)` | matched but no candidate within radius of `['garage']` |
| walls.front.segments.main body 2-story.width_ft | 34.0 | `34'-0"` | not within radius of `['front', 'main', 'body', '2story']` |
| walls.front.segments.garage wing 1-story.width_ft | 24.0 | `24'-0 1/2"` | not within radius of `['front', 'garage', 'wing', '1story']` |
| walls.back.segments.garage/bonus wing.width_ft | 24.0 | `24'-0 1/2"` | not within radius of `['back', 'garage', 'bonus', 'wing']` |
| roof_planes.main.eave_lf | 116.0 | `58'-0"; 58'-0"` | no feature anchor `['main']` on page |
| roof_planes.bonus room.eave_lf | 48.0 | `24'-0 1/2"` | not within radius of `['bonus room']` |
| walls.back.segments.main body 2-story.width_ft | 34.0 | `34'-0"` | no feature anchor `['back', 'main', 'body', '2story']` on page |
| walls.right.segments.main body 2-story.width_ft | 30.0 | `30'-0"` | no feature anchor `['right', 'main', 'body', '2story']` on page |

## LOCATED (22 verifiable dims — sample)

Verifiable dims flowing to money. Sample: `walls.front.width_ft`, `walls.back.width_ft`, `walls.left.height_ft`, `walls.right.height_ft`, `outside_corner_lf`, `walls.front.height_ft`, main body eave/rake fragments — the read's spine holds where the drawings back it.

## Class fix status

- ✅ Anchor recalibration for cardinal wall paths (elevation OR floor_plan sheet is the feature)
- ✅ BACK ↔ REAR synonym
- ✅ REFUSED vs FABRICATED as distinct states on rail (`dims_unverified` warn, `dims_fabricated` loud) and readback (`dim_unverified`, `dim_fabricated`)
- 🔲 Normalizer detector (item #4) — next commit

## Snapshot

Full JSON: `memory/boni_locate_nulled_list_2026-08-12.json`.

## Purity

9'-11 1/8" garage wall · 9'-6" is FABRICATED · **58'-0" front width IS REAL AND PRINTED and now LOCATES**. Nothing applies to EST-886440. Integral-J stays ON.
