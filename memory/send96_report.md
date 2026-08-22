# SEND-96 — RULINGS REGISTERED · REFUSED-BUT-BINDABLE CHASE SURFACES · CHASE ROW ON THE QUOTE · RECOVERY WARNING · HEIGHT CARDS
2026-08-22 · pins: `tests/test_chase_quote_2026_08_22_send96.py` (9) · UI verified by test agent (`test_reports/iteration_57.json`, 100%)

## RULINGS REGISTERED (so they do not reopen)
- **Letrick's chimney exterior face is SIDED.** The rear chase's 54.37 ft² stands.
- **The p7 "STONE FACADE" note at x≈62% is NOT the chase.** Recorded here and in the PRD ledger — closed, do not reopen.
- **Boni's 150 ft² chase REFUSES** — no locatable ink supports it.
- **Chase row on the quote — yes, basis labelled.**

## ITEM 1 — BONI'S REFUSAL HAS A SURFACE TO REFUSE INTO
**Report (as asked): did a chase surface exist on Boni before this send, and could a zone bind to it? NO on both counts** — `_face_ok` rejected `chase:*` ids and the partition only created surfaces where ink exists. That was the send-48 lesson about to repeat a third time. **Fixed:**
- `chase:front|back|left|right` are now first-class bindable surfaces everywhere (`_face_ok`, `_surface_of`, `surface_derived_snapshot`), on every house, ink or no ink. The snapshot refuses with its name: "no chase is ever derived by the walk — chase area enters only by a drawn zone" and binds at 0.0 (nothing to supersede).
- The propose payload now REFUSES the model's claim aloud: Boni's response carries `skipped: chase:left — "REFUSED — the run claims a chimney chase of 150 ft² on this wall; no chase ink locatable on any evaluable face — the model's claim feeds nothing; the chase surface still exists and stays bindable — draw a zone to bind it"` (verified live).
- The overlay editor gained a "**bind the chimney chase instead**" toggle beside the gable toggle (mutually exclusive; UI-verified) — Howard has somewhere to draw.

**What refusing 150 ft² does to Boni's total:** nothing priced moves. The money line is human-set 18.0 SQ (raw 17.5) and untouched; the derived total under current rules is 0 (all four faces refuse height). The 150 lives only inside the stored pre-height hypothesis figure (`siding_sqft` 4,113 ft² = 41.1 SQ → 39.6 SQ without it), which has never priced anything since heights became evidence-gated. The refusal makes that explicit instead of latent.

## ITEM 2 — THE QUOTE ROW, AND WHERE THE CONTEST LANDS
- A confirmed chase zone now becomes its **own quote row** ("Chimney Chase — rear"), never merged into the body line, with the basis printed on the row: `"Basis: rear chase width 5'-4" — supplied by Howard from the prints, not read from this drawing — HUMAN DIMENSION, never presented as derived"` vs a drawn-basis row for traced chases. Idempotent (rows rebuild from zones each pass), and proposals never create rows.
- **A chase on a CONTESTED-scale face REFUSES and BLOCKS the gate**: the row prices at NOTHING (qty null, `not_derivable`, reason naming Ruling L and the contest), the quote total is INCOMPLETE (banner listing every refused row), and the readiness registry (the ONE truth feeding the quote modal and the gate chips) emits `chase_contested_scale` — QUOTE-tier, BLOCKING, registered and sealed in `gates.py` with a firing pin. A quote never shows two numbers and never quietly picks one.

**Letrick's quote under that treatment (as asked):**
| chase | if confirmed | why |
|---|---|---|
| chase:left | **PRICES** ≈ 43.8 ft² (0.44 SQ), drawn basis | side scale is the uncontested 9'-1⅛" chain |
| chase:right | **PRICES** ≈ 44.6 ft² (0.45 SQ), drawn basis | same |
| chase:back | **REFUSES + BLOCKS THE GATE** | rear stays contested (9'-11" vs 9'-1⅛") — the row would be ~109 ft² at one contestant and ~100 at the other; a quote cannot show two numbers |
Today nothing is confirmed → no chase rows print, and the chase gate is silent (Letrick's pre-existing labor-pending blockers still gate print, unrelated). The cost of keeping rear contested now lands where Howard sees it: the rear chase cannot reach a customer until a tape resolves the contest — the rear HEIGHT CARD says exactly what to tape.

## ITEM 3 — WARN BEFORE THE RECOVERY MOVES OLD ESTIMATES
- Every propose response now carries a **recovery warning** naming the jump before it can happen: "the chase partition newly carries 101.09 ft² of above-plate chase area on this estimate — nothing moves until a human confirms a chase zone (proposals feed no quantity); confirming them will raise the siding takeoff by about that much" (live on Letrick).
- **Census of estimates that would change:** exactly **one — Letrick**, and only on human confirm: ≈ +88 ft² (≈0.9 SQ) from the two side chases; the rear chase (+~100–109 ft²) refuses at the gate until the contest resolves. **Boni: zero** (chase refused, nothing derived). No silent movement exists: proposals feed no quantity (SEND-48 law), chase rows exist only for human zones, and the refused class blocks rather than prices.

## ORDER ITEMS 2–3 — ALSO LANDED
- **Chase corner note (visible, unpriced):** every chase quote row and every partition payload carries "carries 4 corner verticals running the chase height — UNPRICED, corner count unchanged". No corner count changed (Ruling G seal untouched).
- **HEIGHT CARDS:** `GET /estimates/{id}/pdf-overlay/height-cards` + a printable card block in the overlay editor. A card = face, page, the refusal verbatim, and a plain TAPE instruction. Live: **Boni prints four** (front: conflicting heights — "tape plate-to-floor once, the tape decides"; rear: undimensioned joist band — "one pull, the missing band is inside it"; left: contested 6'-0" vs 9'-1" — "hook at TOP OF PLATE, read at FIRST FLOOR"; right: no floor line — "tape grade to top of wall"). **Letrick prints one** (rear contested — the same tape that unblocks the rear chase row). A card is a field instruction, never a quantity — the taped figure comes back as a human dimension.

## ORDER ITEMS 4–5 — NOT DONE, STATUS HONEST
- **Ruling V conversion** (downspout drop + gutter mitre count onto verified-height bases): NOT started this pass. The two reads still sit on `_ai_avg_wall_height_ft` with the census carrying them as PENDING_CONVERSION. The baseline note stands: it must be a full Q-conversion through the line builders (status-carrying height, refusal instead of a story default) — not half-done, to avoid a new silent zero.
- **Boni left cure**: NOT started. The face refuses on "all spanning boundaries sit at one corner" — a cure needs its ruling first. The candidates, for Howard to pick from: (a) accept the far member x=34.94 as the second corner when it is the ONLY full spanner beyond the fence-side corner (names its basis, weakest tier), (b) let a drawn human zone stand as the cure (already possible today), or (c) leave it refusing. Nothing wired without the ruling.

Standing rules held: no cross-drawing evidence, no estimate influences another, no job names in code, model heights hypothesis-only for quantities. EST-886440 untouched. 423 on every derived write. Purity pin holds — CCC carries UNVALIDATED at n=1 house.
