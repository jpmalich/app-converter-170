# ENTRY LINKS + SURFACE-GATING AUDIT + APPLY-GATING RULING (2026-08-11)

Ordered from Howard's 8-11 send (3), part 1 of item (a). Report answers three
questions at once. No fixes applied in this document — the code changes ship
with the same commit and are named at the end.

---

## 1 · WHY THE ENTRY LINKS "VERIFIED AS BUILT" WERE NOT REACHABLE

**Ruled at handback 2026-07-20** (see PRD.md "Elevation-sheet ruling
executed"): "Entry point shipped: EL-1..EL-4 chooser links on the Field
Verify card beside the source-view door **(photo estimates only** …)".
That ruling was for the PHOTO door. **Blueprint entry links were added
2026-08-10 to `BlueprintReadBackCard.jsx` lines 74–83** — the testids
`bp-rb-sheet-front / -left / -back / -right` exist in the JSX.

The class of test that "verified" the links is JSX-string presence:

- `tests/test_blueprint_readback_2026_08_06.py::test_readback_card_renders_heights_and_runs`
  asserts specific testids exist inside `BlueprintReadBackCard.jsx` — a
  read of the FILE, not of the mounted DOM.
- `tests/test_provenance_hardcode_sweep.py::test_field_verify_elevation_sheet_chooser_wiring`
  does the same for `FieldVerifyCard.jsx` (photo door).

**Neither test asserts WHERE the component mounts.** They only prove the
component *owns* the testid.

`BlueprintReadBackCard` is imported and mounted in ONE place:
`BlueprintMeasureButton.jsx:1080`. That component is the run dialog modal
— open only while the contractor is actively grading a fresh read. Once
the modal is dismissed (Apply, close-preview, or `setResult(null)`), the
card unmounts and the entry links vanish with it. There is no persistent
mount of `BlueprintReadBackCard` on the estimate page.

**So the test verified the links in a state Howard does not stand in.** A
verified-in-modal link is not a reachable link on the estimate page. The
class of failure is:

> Presence-in-file ≠ presence-in-mounted-DOM. A JSX-string check proves a
> component OWNS a testid; it cannot prove the component RENDERS on the
> surface the user is standing on.

Same shape as instances 1–3 (vinyl profile picker, accent injection,
sheets themselves): a surface built inside a conditional/modal, tested
by asserting the *conditional side* renders correctly, never tested for
reachability from the estimate page in the default state.

**RULING (Howard, 2026-08-11):** the sheet renders from any completed
read, applied or not. Backend already honors this — `blueprint_elevation`
route (`routes/blueprint_elevation.py:258`) queries any `status: done`
run and returns; no `applied` flag is required. **What broke was
reachability, not backend gating.** The link component must mount on
the estimate page and on the Takeoff Preview — the two moments where the
sheet is wanted.

Detector shipped with this doc: `tests/test_entry_link_mount_2026_08_11.py`
asserts (i) `BlueprintElevationEntry` is imported and used from
`JobInfoPanel.jsx` (persistent, estimate-page), (ii) it renders inside
`BlueprintMeasureButton.jsx` **outside** the readback card (Takeoff
Preview mount), (iii) the sheet page (`BlueprintElevationSheet.jsx`)
carries a "Back to the takeoff" link, and (iv) every state carries a
visible surface chip (never invisible). Fails on any regression.

---

## 2 · SURFACE-GATING AUDIT (walked estimate page + Blueprint card)

Every surface that gates behind a state Howard does not produce by
standing on the page. Format:
`<surface> · <required state> · <what renders today> · <what will render>`

The three-column ruling: today's surface is either INVISIBLE (nothing
renders — you find it by walking into a wall), DISABLED (rendered but
inert — worse than invisible only in that it lies about the way out),
or SPEAKS (renders + names its state + names the way out).

| # | Surface | Required state | Today | After 8-11 |
|---|---------|---------------|-------|------------|
| S1 | EL-1..EL-4 blueprint elevation links | any completed blueprint run (was mis-gated: modal open + readback populated) | INVISIBLE — only inside `BlueprintMeasureButton` modal, only after grading | SPEAKS — persistent on Blueprint tile and inside Takeoff Preview; renders SurfaceAccessChip when no completed run yet |
| S2 | EL-1..EL-4 photo elevation links | photo-door + completed AI run with walls | INVISIBLE unless BOTH → the FieldVerifyCard `photo` chip branch renders the empty-state "Elevation sheets — no completed run with walls" | Kept; empty-state OK; SurfaceAccessChip added on non-photo estimates so the door is named ("photo door only") |
| S3 | Vinyl profile picker (per-line) | photo door only | INVISIBLE on blueprint/HOVER estimates — no chip anywhere on the row | SPEAKS — SurfaceAccessChip on the row: "photo door only — this row's profile came from the schedule/import" |
| S4 | Accent injection dialog trigger | run dialog open (Blueprint or Photo) | INVISIBLE on the estimate page — only reachable inside the run dialog | SPEAKS — Blueprint/Photo tile shows chip: "requires a completed measurement run — start one to inject an accent" |
| S5 | Blueprint readback card (bp-readback-card) | run dialog open + `result.readback` populated | INVISIBLE on the estimate page — only inside the modal | Kept in modal; the READ-BACK CARD chips (planes/corners/porch) speak for themselves inside the modal. Entry-link chip (S1) is now separately mounted persistently — the audit target |
| S6 | Restore HOVER | HOVER upload cache, non-blueprint source | Renders quietly on the tile only when applicable | OK — the tile already speaks (button visible with label) |
| S7 | Print-all elevation sheets (`elevation-sheet-print-all`) | photo estimate + completed run + walls | Only visible inside FieldVerifyCard when sheetWalls > 0 | SPEAKS — SurfaceAccessChip added when no completed run: "print pack renders after a completed measurement" |
| S8 | Compare Drawings modal | ≥2 elevation-drawing sources | Renders as chip on JobInfoPanel when `numDrawingSources ≥ 2` | Already speaks (chip visible with count) — OK |
| S9 | LP Material List panel (`lp-package-panel`) | `est.kind === "lp_smart"` + governing run | On non-lp_smart, does not render — no chip | Non-lp_smart estimates: SurfaceAccessChip renders: "LP smart estimates only — this estimate is `<kind>`" |
| S10 | 3D snapshot / model canvas | AI photo measurement done | Chip present via ThreeCanvas gates | Already speaks — OK |
| S11 | Emit Quote / Freeze buttons | `assert_quote_gate` open | Renders 409 detail on click; gate banner at top of page also speaks | Already speaks — OK |
| S12 | Elevation Compare "add source" | HOVER + photo + blueprint sources | Modal opens if ≥1 source — else the chip explains | Already speaks — OK |
| S13 | Profile annotator "Re-read" | run dialog open | Only inside modal | This IS a modal-scoped action; not on the estimate page by design — no chip needed. Listed for completeness. |

**The four Howard walked into (from his send):**
1. Vinyl profile picker → S3 (photo door only)
2. Accent injection → S4 (run dialogs only)
3. The sheets themselves → S1 (applied runs only, ruled REVERSED today: any completed read)
4. The elevation links → S1 (mis-mounted inside a modal)

**Same shape:** each surface is INVISIBLE (not disabled) when its state
is not produced, and the JSX-string tests could not catch it because
they read the file, not the mounted DOM.

**Ruling — SurfaceAccessChip contract (Howard, 2026-08-11):**
- A surface that cannot render its output must still render a chip.
- The chip names the STATE ("needs an applied run", "photo door only",
  "needs a completed measurement") and the WAY OUT ("start a blueprint
  read to enable this", "this row's profile came from …").
- The chip is NEVER invisible. Disabled is acceptable; hidden is not.
- Applies to every surface listed as "SPEAKS" in the column above.

Detector shipped: `tests/test_surface_access_chip_contract_2026_08_11.py`
asserts the chip renders for the four instances Howard walked into and
that its message contains BOTH the state and the way out. Component
lives at `/app/frontend/src/components/estimate/SurfaceAccessChip.jsx`.

---

## 3 · APPLY-GATING RULING + GUARD REPORT

Howard's question (verbatim): "apply-takeoff is a route the guard does
not cover, or the guard is not doing its job. Report, do not tighten yet."

### The apply-takeoff route

`BlueprintMeasureButton.jsx` Apply flow (line 477–517):
1. `update({lines, vero_openings, mezzo_openings, hover_measurements})` — **local React state, no server call** (line 479)
2. `await save({...})` — invokes `useEstimate.save` → `api.put("/estimates/{id}", …)` (line 480–488)
3. For `lp_smart` estimates only: `await api.post("/estimates/{id}/lp-package/blueprint-applied", …)` (line 498)

The primary write is `PUT /estimates/{id}` → `routes/estimates.py:419
update_estimate` → **`await refuse_untouchable(est_id)` at line 420**.
The LP path (POST lp-package/blueprint-applied) also carries the guard
at `routes/lp_package_routes.py:590`.

### Live verification

`curl -X PUT $API/api/estimates/1f8b8b60-4b19-48eb-b1b5-0371276c8645 \
  -H "Content-Type: application/json" -d '{"customer_name":"…"}'`
→ **HTTP 423** with detail `"EST-886440 is UNTOUCHABLE (ruled 2026-08-09)
— the continuous grading chain. The server refuses every write to this
estimate; reads and reruns stay open."`

### Verdict

**The guard IS doing its job on the apply-takeoff path.** The PUT is
refused with 423. The estimate's `updated_at` is `2026-08-07T20:29:34`
— predates the untouchable ruling (2026-08-09) — proving no successful
write since the guard was armed. The applied state on EST-886440 is
from **before** the guard existed.

### Why the apply "went through" from Howard's chair

The Apply handler updates local React state on line 479 (`update({...})`)
**before** the server PUT fires. If the PUT then 423's, the local UI
reflects the "applied" state (lines merged, drawings persisted) — the
sheet page renders because it queries the run doc directly (not the
estimate). Refresh restores the DB truth. The toast on line 514 catches
the 423 as "Apply failed" but a contractor mid-workflow can miss it.

**No tightening ordered.** Two possible amendments listed for Howard's
ruling only:

- (i) Reverse the optimism order: run `save()` before `update()`, so a
  423 never paints applied-looking UI in the first place. Cheap.
- (ii) Or: on 423 from `save()`, revert the local `update()` state and
  print a persistent chip on the estimate page ("EST-886440 is
  UNTOUCHABLE — this write was refused"), not just a toast.

### Guard-coverage gaps (report only, not action items)

Write routes that touch `db.estimates` but do NOT call `refuse_untouchable`
today, walked from `routes/estimates.py`:

- PUT `/estimates/{id}/profile-annotations` (line 651) — writes `profile_annotations` + `updated_at`
- PUT `/estimates/{id}/tape-check` (line 1210) — writes `tape_check.walls/dormers`
- POST `/estimates/{id}/tape-check/score` (line 1254) — appends to `tape_check.history`
- POST `/estimates/{id}/accuracy-report/freeze` (line 1140) — freezes a snapshot
- POST `/estimates/{id}/accuracy-report/revoke` (line 1179) — sets revoke flag

Class summary: profile-annotation writes and tape-check writes bypass
the guard. On EST-886440 today, a tape entry or a re-scored history
row would land. Report only — Howard rules whether the guard extends
to these paths or whether these are considered "audit/history" writes
that ride above the freeze. The continuous grading chain per se does
not depend on tape_check history (which grows monotonically and is the
grading artifact), but profile-annotations mutate the run inputs.

---

## 4 · TTL BLAST RADIUS — the disabled gate

Howard's send (verbatim): "the reaping did not only destroy the chain
— it disabled the gate. The instrument that would have caught the
count disagreement had nothing to work with."

Captured in the elevation mechanisms report (§4):
> stability=None — the determinism compare found no prior run because
> the entire chain (a4cbce91 + 4 grading runs) was TTL-reaped. The C
> 5→9 mismatch would have flagged LOUD. The reaped chain cost a real
> detection.

**Named in the incident file:** TTL incident #3's real blast radius is
not one lost run — it is **the determinism gate blinded for every
follow-on read** while the chain is missing. Archive-on-view is
load-bearing precisely because it re-arms the gate that catches
disagreements the seams cannot.

Recorded in `memory/storage_layer_audit_2026-08-11.md` findings §1 and
now cross-referenced from the elevation mechanisms doc.

---

## 5 · CODE THAT SHIPS WITH THIS DOC

- `frontend/src/components/estimate/SurfaceAccessChip.jsx` — new. Never invisible; names state + way out.
- `frontend/src/components/estimate/BlueprintElevationEntry.jsx` — new. Always mounts; renders links if a completed run exists, else the chip.
- `frontend/src/pages/BlueprintElevationSheet.jsx` — new "← Back to the takeoff" link.
- `frontend/src/components/estimate/JobInfoPanel.jsx` — mounts `BlueprintElevationEntry` on the Blueprint tile.
- `frontend/src/components/estimate/BlueprintMeasureButton.jsx` — mounts `BlueprintElevationEntry` above the Takeoff Preview (inside the modal).
- `frontend/src/pages/ISSEstimateEditor.jsx` — same mount on the ISS Blueprint tile.
- `backend/routes/blueprint_elevation.py` — new `GET /estimates/{est_id}/blueprint-latest-run` endpoint returning `{run_id, status, walls, completed_at, applied}` or 404 with reason.
- `backend/tests/test_entry_link_mount_2026_08_11.py` — mount detector.
- `backend/tests/test_surface_access_chip_contract_2026_08_11.py` — chip-contract detector.

**Not shipped in this commit (Howard rules next):**
- Guard coverage over profile-annotations / tape-check / accuracy-report (report only, §3).
- Reversing the optimism order on the Apply handler (report only, §3).
- Marking EST-886440 `protected: true` — proposed as separate one-shot script under the pre-heal-backup rule (Iter 79j.63) since the untouchable guard refuses the flip route by design.
