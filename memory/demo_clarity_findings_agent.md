# Demo Clarity Audit — Findings Catalog

**Audit run:** Jan 2026 (read‑only, no code touched, no data mutated)
**Estimate audited:** `8f95c9c2-add9-416a-92f3-786a4ea2ce83` — “letrick 7‑14‑26 7pm” (LP SmartSide kind, `lp_smart`)
**Contractor:** hhunt6677@yahoo.com (owner: Howard Hunt)
**Viewports:** 1920×900 desktop, 1366×768 laptop, 390×844 mobile (Accept page only)
**Constraints observed:** No emails sent. No dimensions saved. No accept confirmations. No field‑verify / relocate / remove clicks. Estimate left as found.

Severity legend
- **HIGH** — demo audience would think something is broken, or two numbers disagree
- **MED** — confusing / ambiguous; needs verbal explanation
- **LOW** — cosmetic polish

---

## ⚠️ Cross‑screen HIGH: three different totals show for the same estimate

The single most damaging finding in the whole audit. The same estimate presents **four totals across the demo path**, three of which disagree with each other:

| Location | Locator | Value shown |
|---|---|---|
| Estimate editor – LP Material List panel total | `[data-testid="lp-material-total"]` | **$11,055.71** ("Materials total: $11,055.71") |
| Estimate editor – Summary card "Your Price to Homeowner (30% Margin of Sale)" | `[data-testid="totals-summary"]` (bottom of `EstimateEditor.jsx`) | **$0.00** |
| Estimate editor – amber "LP SMART" pill above material list | text "LP SMART $0.00" | **$0.00** |
| Customer Quote email preview – "Total Price" | modal opened by `[data-testid="open-quote-btn"]` | **$24,005.01** |
| Public Accept page – "Total Price" & attestation | `[data-testid="accept-total"]`, attestation text under `accept-checkbox` | **$0.00** |

Root cause visible on screen: sticky pill top‑right reads **“LP SMART / Derived — not yet applied”**, meaning the LP‑derived material list is priced but never rolled into the editor’s legacy line‑item summary. Meanwhile the Customer Quote modal renders its OWN total from a different derivation (material + waste + labor + tax − margin), yielding $24,005.01.

For the demo, a contractor could open the Material List and see $11k, open the Customer Quote and see $24k, and land the customer on an Accept page that attests to **$0.00**. Any of the three, alone, will read as broken.

---

## Screen 1 — Estimate editor main page (LP SmartSide tab)

### HIGH
1. **“LP SMART / $0.00” amber banner above the Material List** (`EstimateEditor.jsx`, the amber card that reads `LP SMART` / `$0.00`). Immediately followed by a Material List whose own total is `$11,055.71`. Two numbers, same panel column, three inches apart, that disagree.
2. **Summary card row “Material”, “Material incl. 10% cut waste”, “Tax (7%)”, “Labor”, “Base cost”, “Your price to homeowner (30% margin of sale)” all read $0.00** while the LP category rollups directly above show priced sub‑items (e.g. `38 Series Lap 3/8" × 8" × 16'` — 227 PCS × $30.99 = **$7,034.73**, `540 Series OSC 5/4" × 4" × 16'` — 2 PCS × $271.69 = **$1,901.83**, etc.). Locator: `[data-testid="totals-summary"]` group. To a demo audience this reads as “nothing is priced” even though the panel above visibly is priced.
3. **LP category accordions ("LP Smart Siding", "LP SmartSide Trim", "LP Siding Accessories", "LP SmartSide Soffit", "Tear‑off / Clean up", "Seamless Gutter", "Misc. Labor and Material") each show `$0.00` in their collapsed right‑side rollup**, even though their child rows in the Material List clearly have prices. Locators: accordion headers in `LpMaterialListPanel.jsx`. The `$0.00` label directly contradicts the priced child rows once expanded.

### MED
4. **Header sticky pill "Derived — not yet applied"** (top‑right). Wording is meaningful only to somebody who already knows the internal state machine. A contractor watching a demo will just see the word "not yet applied" next to a big dollar figure and wonder what they forgot to click. Locator: `[data-testid="sticky-bar"]`.
5. **Two verification‑state vocabularies coexist inside the same screen**:
   - LP Material list header: "AI‑DERIVED", "DERIVED FROM: AI PHOTO MEASURE"
   - Field‑verify card: locations are **"UNCONFIRMED"** and become **"VERIFIED IN FIELD"**
   - "Confirm openings — pre‑derivation review" row: reads **"0/8 reviewed · 8 unconfirmed"** and offers **CONFIRM / WRONG TYPE / NOT PRESENT**
   - Geometry rows in the 3D panel show **"AI‑DERIVED"**, **"AI PER‑WALL"**, **"AI‑CLASSIFIED"**
   - Tape nudge (chase block): calls the same state **"assumed"** ("Tape it on site — optional quick entry — chase / This feature still carries assumed dimensions").
   Four different words for essentially the same idea (not yet ground‑truthed): *unconfirmed*, *derived*, *assumed*, *estimate*. Locators: `[data-testid="lp-field-verify-card"]`, `[data-testid="lp-tape-nudge-chase"]`, per‑opening confirm rows in `LpMaterialListPanel.jsx`.
6. **"Confirm openings" tier wording** uses "0/8 reviewed" while the LP field‑verify card counts "unconfirmed locations". Two different counters (`0/8 reviewed · 8 unconfirmed` vs the amber corner list) in the same panel refer to different things but the words feel interchangeable.
7. **"BAKED INTO LINE QTY ON IMPORT — CHANGE % TO RECOMPUTE"** waste factor helper text — the sentence is caps‑locked and the phrase "baked into line qty on import" is jargon a demo audience will not parse without help. `[data-testid]` unavailable; nearest label is the input inside the `WASTE FACTOR` card.

### LOW
8. **All uppercase everywhere** (`JOB INFORMATION`, `WASTE FACTOR`, `SALES TAX`, `PROFIT`, `SUMMARY`, `LP SMART OPTION`, `MATERIAL INCL. 10% CUT WASTE`, headers of every accordion, every field label). Reads as visually shouty and blurs hierarchy in screenshots.
9. **Address “1, Pittsburgh, PA 15215”** — the street number literally just "1". Shown in the editor header AND propagated to the Customer Quote preview AND to the Accept page ("Prepared for: letrick 7‑14‑26 7pm · 1, Pittsburgh, PA 15215"). Demo‑only artefact, but worth noting.
10. **"Add email to send quotes" chip in the Job Information header** sits half‑attached to the title on 1366×768 and reads like a status pill rather than a call to action. Locator: the amber pill inside the `JOB INFORMATION` header row.

---

## Screen 2 — AI Measure modal

Modal was opened via `[data-testid="ai-measure-btn"]`; the "Photo Checklist" onboarding dialog covered the modal on first open and had to be dismissed with **GOT IT, DON'T SHOW AGAIN**. The stored session was then resumed (toast: "Resumed your last AI Measure session").

### HIGH
11. **Openings count disagreement between AI Measure summary and the Confirm‑openings review below**. Confirm‑Openings row header (`LpMaterialListPanel.jsx`) reads **"0/8 reviewed · 8 unconfirmed"**. The AI Measure modal Preview panel header reads **"4 elevations · 1,781 ft² siding split"** and the Openings schedule inside the modal is labelled "OPENINGS SCHEDULE — GROUPED BY ELEVATION × SIZE"; the individual review chips visible under Confirm Openings show 8 line rows but two of them are qty‑2 (Front Window ×2, Back Window ×2) and one is qty‑3 (Back Window ×3), which sums to **10 physical openings** — yet the FRONT wall detail card in the 3D panel says **"Openings 4"** (2 windows‑pair + 1 window + 1 door = 4). The counts across the three surfaces (8 review rows vs 8 unconfirmed vs 4 per‑wall front vs implicit ~10 physical) are not obviously consistent to a demo viewer without the taxonomy explained. Locators: `[data-testid="lp-material-list-panel"]` (0/8 line), Confirm‑Openings row images inside same panel, and the "This Wall — AI Takeoff" card in `HouseModel3D.jsx` (`Openings 4`).

### MED
12. **Two confidence tiers named differently in the same modal**: header shows a green pill "CONFIDENCE: HIGH", right‑side classifier chips say "AI‑DERIVED / AI PER‑WALL / AI‑CLASSIFIED / 90% conf", the modal body prose says "estimate, not a survey", and the Photo Checklist copy talks about "the enumerated (tape‑provable) tier" vs "amber estimate". Four names for tiers.
13. **"1,781 ft² siding split"** shown in the Preview header disagrees on first read with the per‑wall AI takeoff for FRONT that shows **"Wall body 430 sf / Total (this wall) 430 sf"**. 4 × 430 = 1,720, not 1,781 — the 61 ft² delta is the gable triangle callout ("gable triangles add 271.5 ft²") but the arithmetic reconciliation is not shown; a demo audience will do the mental math and see the numbers don’t add up.
14. **"Whole‑house materials — from estimator" list inside the 3D panel** duplicates the same 22‑line LP material list already visible right underneath it but reformatted (`38 Series Lap 3/8" × 8" × 16' — 227 PCS`, etc., without prices). Two copies of the same list on one page, wrong-looking side by side.

### LOW
15. Photo Checklist purple modal covers the AI Measure content on entry. If a demo viewer expects to see the run summary immediately, they hit the checklist first.
16. "Fable 5" and "Claude Fable 5 ✓ Validated" — internal model name shown to the user with no gloss. LOW.

---

## Screen 3 — 3D tab inside the estimate (`data-testid="lp-material-3d"`)

Facade tabs FRONT/RIGHT/BACK/LEFT are present and clickable. Front is the default; the audit inspected the appendage rows under the BACK wall via the field‑verify card (which enumerates chase corners) — no dimensions saved.

### HIGH
17. **Appendage / chase corner list DOES NOT appear inside the 3D panel where a demo viewer expects it**. The panel is titled *"3D — colors repaint live (siding + opening trim mesh groups; corner/fascia meshes pending)"* and the sidebar shows per‑wall geometry, wall body sf, opening count, and a "Whole‑house materials" list — but the appendage / chimney chase rows (with Depth/Height "measure" edit rows) are actually rendered **inside the LP Material List Panel above, under `[data-testid="lp-field-verify-card"]`**, not inside the 3D panel. A demo viewer will click the 3D BACK tab expecting to see the chase editable rows there and won’t find them.

### MED
18. **3D panel header text** — *"colors repaint live (siding + opening trim mesh groups; corner/fascia meshes pending)"* is an implementation note leaking into UI copy. Locator: heading inside `HouseModel3D.jsx`.
19. **"TAP A WALL TO SEE ITS TAKEOFF · DRAG TO ORBIT · SCROLL TO ZOOM"** hint uses "tap" (mobile idiom) on a desktop demo screen. LOW‑MED.
20. **Geometry row provenance labels are inconsistent**: eave shows green **"AI PER‑WALL"**, pitch shows green **"AI‑DERIVED"**, roof type shows green **"AI‑CLASSIFIED"**, ridge shows green **"AI‑DERIVED"**. Four different labels for four fields — same green pill styling — even though from a demo viewer's perspective they all mean "AI put this here". Locators: `[data-testid="ai-measure-3d-eave-derived-front"]`, `[data-testid="ai-measure-3d-pitch-derived"]`, `[data-testid="ai-measure-3d-roof-type-ai"]`, and the ridge row.
21. **Tape nudge card title "Tape it on site — optional quick entry — chase"** with body "This feature still carries **assumed** dimensions (render‑only, footnoted on the customer PDF). Enter what you tape — entered values become **user‑measured** inputs (revertible, re‑derives quantities). Skipping keeps the assumed state." — introduces THREE more state names (**assumed**, **user‑measured**, and separately **render‑only footnoted**) not used anywhere else in the app. Locator: `[data-testid="lp-tape-nudge-chase"]`.

### LOW
22. Roof pitch select `3/12 … 14/12` has 12 options in the dropdown; on 1366×768 the dropdown label collides with the "AI‑DERIVED" pill visually (they overlap in the layout by ~8px). Locator: `[data-testid="ai-measure-3d-pitch"]`.

---

## Screen 4 — Material List / LP package panel

### HIGH
23. **Category rollup vs child‑line disagreement** (already noted at cross‑screen level, restating with locators): every collapsed accordion header (`LP SMART SIDING`, `LP SMARTSIDE TRIM`, `LP SIDING ACCESSORIES`, `LP SMARTSIDE SOFFIT`, `TEAR‑OFF / CLEAN UP`, `SEAMLESS GUTTER`, `MISC. LABOR AND MATERIAL`) shows **$0.00** on the right; expanding any of the first four reveals line rows with real unit prices ($30.99 → $7,034.73, $56.43 → $620.73, $85.83 → $514.98, etc.). The rollup number is wrong or is intentionally blank; either way it disagrees with the sum of its own children.

### MED
24. **Mixed pricing states**: the same panel mixes fully‑priced lines (`38 Series Lap 3/8" × 8" × 16'` $7,034.73) with lines that read **"PRICING PENDING"** in the editor or **"PRICING TO BE CONFIRMED"** in the customer preview (Gutter 6", Downspout 6", elbow, End Cap, Hangars with Screws, Mitre, Pipe Clips, Gutter Sealant, Cap window, Cap entry door, clean up/haul away). Different phrasing for the same idea across editor vs quote preview.
25. **Section item‑count badges next to accordion titles**: e.g. `LP SMART SIDING · 🔎 1`, `LP SMARTSIDE TRIM · 🔎 2` — but the underlying Material List shows *one* LP Smart Siding line (matches 1) and *three* LP SmartSide Trim lines (does NOT match `2`). Locator: the small pill next to each accordion title in `LpMaterialListPanel.jsx`.
26. **"How this number was derived"** disclosure caret next to every quantity — provenance is welcome, but on a 1366×768 laptop the caret and label collide with the QTY column on lines whose product name wraps to 2 lines (e.g. `540 Series OSC 5/4" x 4" x 16'` with `154 LF · $30.99/board · 4 whole boards` under it), producing visual overlap.
27. **Notes column (subtext under LP Starter — "field‑ripped from siding stock")** is truncated on 1366×768 — the "· 4 whole boards" wraps under the unit price and the LF value in the QTY column shifts down, causing a visual mis‑alignment between the QTY 154 and the unit label.
28. **"Read‑only — click Edit list to substitute products. Substitutions re‑derive from geometry and are not remembered after reload."** — the second sentence is alarming (a customer‑facing‑adjacent panel telling the estimator "your changes will be lost after reload"). Wording feels like a bug caveat leaked to UI. Locator: `[data-testid="lp-material-list-readonly-hint"]`.

### LOW
29. Every color chip in the "Colors — ExpertFinish" row is followed by a ⛔ (no‑entry) glyph except for `Snowscape White`. If ⛔ means "unavailable" the semantics aren't explained anywhere on the panel.

---

## Screen 5 — Customer Quote (email/PDF preview modal)

Opened via `[data-testid="open-quote-btn"]`. No email was sent; only the preview inside the modal was inspected. **Saved** toast fired when the modal opened — the preview appears to trigger a save on the estimate, not just a render.

### HIGH
30. **Customer Quote "Total Price" = $24,005.01** while the editor's own Summary/Sticky "Your Price to Homeowner" reads **$0.00** and the LP Material total reads **$11,055.71**. Same estimate, three totals, one preview click away from each other. This is the demo‑killer finding.
31. **"Prepared for: letrick 7‑14‑26 7pm"** — the estimate name is being surfaced as the customer name on the customer‑facing quote page. The Job Information card in the editor has phone `4129778509` and address `1, Pittsburgh, PA 15215` but no customer name field is populated, so the quote falls back to the estimate title. A live customer would receive a PDF that says "Prepared for: letrick 7‑14‑26 7pm".
32. **Bottom of preview: `Items marked "pricing to be confirmed" are awaiting supplier price confirmation and are not included in the total. They will be quoted before work begins.`** — combined with 11 "PRICING TO BE CONFIRMED" lines above (all of Seamless Gutter, both Cap window/Cap entry door under Misc. Labor and Material, and all of Tear‑off / Clean up), the customer sees a $24,005.01 total that explicitly excludes 11 substantive line items. Even though the wording is honest, on a demo the audience will read this as "these numbers aren't real".

### MED
33. **"MATERIALS SUPPLIED BY ALSIDE SUPPLY"** footer of the preview — the supplier co‑brand shows here but the header logo of the preview is the generic **"P — Pro‑Quote Estimating Tool"** ESTIMATOR mark, NOT Alside Supply’s uploaded branding. Two branding stories in the same PDF.
34. **Personal note textarea** is pre‑seeded with "Hi letrick," — because the greeting is templated from the estimate title (not the customer name). A contractor sending this quote as‑is would send the customer an email starting *"Hi letrick 7‑14‑26 7pm,"*.
35. **"Your Home — 3D Model"** section renders the same GLB model twice: once in the Accept page (Screen 6) and once here in the Quote preview PDF. The two renders may (silently) look different — the Quote preview render shows the back of the house at an angle that clips the roof out of frame at the top. On desktop 1920×900 the crop is severe (top of roof outside modal viewport). See screenshot `s5_cq_1_1920.png` for reference.

### LOW
36. Email input placeholder "customer@example.com" and the send button "EMAIL" — the send button in the modal header is small and easy to click by accident. No confirmation modal defined for send.
37. "SEND IN: EN / ES" language toggle is *above* the Personal Note but the Personal Note itself doesn't preview in Spanish when ES is selected in the current view.

---

## Screen 6 — Public Accept page at `/accept/preview-accept-3d`

Inspected read‑only in an unauthenticated browser context, at 1920×900, 1366×768, and mobile 390×844. No accept confirmation was submitted.

### HIGH
38. **Total Price $0.00 on the Accept page** disagrees with the Customer Quote preview total **$24,005.01** on the same estimate. This is the customer's binding‑looking page and reads as "this estimate has no dollar value". Locator: `[data-testid="accept-total"]`.
39. **Attestation checkbox reads verbatim: "I, letrick 7‑14‑26 7pm, accept this estimate for $0.00 as quoted by Pro‑Quote Estimating Tool."** — customer name pulled from estimate title (same defect as Finding 31) AND the dollar amount is $0.00. Locator: text next to `[data-testid="accept-checkbox"]`. If the customer clicks Confirm on this page they attest to accepting an estimate for zero dollars.

### MED
40. **Header branding**: at 1920×900, the header row has "EN / ES" language toggle top‑right and "Pro‑Quote Estimating Tool" mid‑left with no logo image (the icon slot renders as a black square with a light "P"). Mobile version 390×844 same. The supplier ("Alside Supply") that the Customer Quote preview footer credits does NOT appear anywhere on the Accept page. Locator: top of `[data-testid="accept-page"]`.
41. **"Some details are subject to on‑site verification."** footnote under the 3D model (`[data-testid="accept-3d-footnote"]`) is the only reference to the confidence/verification story on this whole page. It does not enumerate which details, and the sibling "PRICING TO BE CONFIRMED" concept from the quote preview is entirely absent.
42. **Share block (`[data-testid="accept-share-block"]`)**: title "SHARE THIS ESTIMATE / Share with anyone who needs to see this — the link and QR code open this same page." The wording invites the customer to forward a link that lets anybody accept the quote. Combined with the $0.00 total showing, that pattern is at minimum surprising, and probably a MED trust concern.
43. **Ambiguous empty state on mobile 390×844**: Between the 3D model and the Share block, ~50–60px of empty white space appears with only "Some details are subject to on‑site verification." floating in it. Reads as "this section didn’t load".

### LOW
44. Footer text "Secure customer‑acceptance link." — small‑caps single‑line footer with no supporting branding line. Feels bare on mobile.
45. Optional note textarea placeholder "e.g. Can we start next week? Or, please bring extra trim samples." is friendly but the note textarea (`[data-testid="accept-note"]`) has no character counter and no explanation of who reads the note.
46. CONFIRM ACCEPTANCE button is disabled (grey) until the checkbox is ticked, but there is no inline copy telling the customer they need to check the box first — a demo viewer momentarily thinks the button is broken.

---

## Appendix — Item / opening counts observed (for cross‑checking later fixes)

| Where | Count observed |
|---|---|
| Confirm‑Openings review chips | 8 rows (front: 3 rows [×2, ×1, ×1 door], left: 2 rows, back: 3 rows [×2, ×3, ×1 door]) → 12 physical if ×qty summed |
| LP field‑verify card (chase corners on right/back wall) | 5 corner items (ISC ×3, OSC ×2) all marked assumed / unconfirmed |
| AI Measure Preview header | 4 elevations · 1,781 ft² siding split |
| 3D panel FRONT wall takeoff | Wall body 430 sf, Openings 4, 90% conf |
| LP Material List | 22 lines · run `d6679448` |
| Editor Material total | **$11,055.71** |
| Editor Summary total | **$0.00** |
| Customer Quote total | **$24,005.01** |
| Accept page total | **$0.00** |

---

## Suggested holding‑bucket for owner review (NOT applied)

- Reconcile Editor Summary, Customer Quote total, Accept page total to a single derivation path. Kill the "Derived — not yet applied" state or auto‑apply.
- Consolidate the state taxonomy (unconfirmed / derived / assumed / estimate / user‑measured / AI‑per‑wall / AI‑classified) to two or three tiers with one label per tier used everywhere.
- Populate "Customer name" field on the estimate; stop falling back to the estimate title for greetings and attestation copy.
- Fix the category rollup `$0.00` to sum its priced children — this alone will unbreak the audience’s trust in the LP panel.
- Move the appendage / chase editable rows into the 3D BACK tab where the panel title implies they live.
