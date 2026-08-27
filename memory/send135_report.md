# SEND-135 — HOVER RESTORE ON A NEW ESTIMATE (P0, money) — 2026-08-27

Stamp: `2026-08-27 · CLEAN · 2943 passed, 9 skipped, 7 warnings in 451.90s`
(2932 → 2943 = the 11 new SEND-135 pins.)
Browser check: on a PHOTO-sourced estimate the restore button is GONE
(0) and the named reason renders (1); on a HOVER-sourced estimate the
button still renders (1) and no reason line shows (0). **PASS both ways.**
**EST-381546 was READ ONLY — 44 lines, `updated_at 09:50:22`, unchanged.
The 56 lines were never applied.**

---

## 1. WHERE THE 5:45 AM RESTORE WAS TRIGGERED

The dialog Howard saw is produced by **exactly one function**:
`HoverImportButton.restore()` — it is the only code that sets
`restoredAt`, which is the only thing that makes the header read *HOVER
Lines Restored (Cached)*.

Facts about that function, all pinned:
- `HoverImportButton.jsx` contains **NO `useEffect` of any kind** — there
  is no mount path, no page-load path, nothing that can call it;
- it has **one** call site: `onClick={restore}` on `hover-restore-btn`;
- **no other file** in the frontend calls `restore()` or reaches for that
  button by testid — no AI-Photo side effect, no wizard, no autoclick.

**So the trigger was a press on the "RESTORE HOVER LINES" button.** What
made that possible is the real defect: **that button should not have
existed on EST-381546, and it had appeared minutes earlier.** It renders
directly beneath "IMPORT HOVER" inside the HOVER tile — one tap-target
apart, and it was NOT there when the estimate was created.

I will not dress this up: I cannot prove which pixel his finger hit. What
IS proven is that nothing but a press can open that dialog, and that the
button's presence was itself the bug. **Both of Howard's named failures
reduce to ONE root cause** (see §2), and it is fixed.

## 2. WHICH CACHE KEY IT READ — AND THE CROSS-ESTIMATE QUESTION, HONESTLY

**The cache key is the estimate's own document: `est.hover_measurements`.**
Not account-wide, not `localStorage`, not "latest import", not another
estimate. Pinned: the restore body may not contain `localStorage`,
`sessionStorage`, `latest` or `recent`.

**And the data says the cross-estimate failure did NOT happen.** Checked
in Mongo:
- `EST-381546.hover_measurements._run_id = a48df681e2c1408e8e7fce122ae007ba`;
- that run's `estimate_id` **is EST-381546 itself** (created 09:45:05 UTC,
  done 09:47:12 UTC — the only run on the job);
- **no other estimate** carries that run id.

So the 1,243.8 ft² was **this job's own photo takeoff**, not another
job's Hover takeoff. What crossed was not the ESTIMATE. **It was the
LANE.** The photo apply writes its numbers into the shared blob stamped
`_source: "photo"` (the STEP-4 design, ruled 2026-08-01, which also uses
`hover_measurements._run_id` as the "which run was applied" marker for
`/pending-runs`). The HOVER door's guard was a **DENY-LIST** naming
`"blueprint"` and `"ai_photo"` — and the photo door writes `"photo"`, a
string that list never named. So the door opened for photo numbers and
labelled them *cached HOVER measurements*.

**A deny-list cannot hold**: every future door has to remember to add
itself, and this one did not.

## 3. WHERE EST-381546's VINYL DOLLARS CAME FROM

**From APPLY MEASUREMENTS (the photo run). Not from the restore. Not
from both.** Evidence:
- a fresh estimate is born with **zero** lines (now pinned), so an apply
  wrote them;
- the estimate carries **44** lines / **$10,320.95**; the restore dialog
  offered **56** and Howard **cancelled** — the counts do not match, and
  no restore write exists;
- `hover_measurements._run_id` is the photo run, and that field IS the
  "applied" marker the `/pending-runs` guard reads — i.e. the photo apply
  ran and stamped it (09:50:22 UTC);
- the applied rows are the photo apply's shared-rebuild signature (vinyl
  AND ascend siding + accessories in one pass).

## 4. THE FIX (build)

1. **THE HOVER DOOR IS NOW AN ALLOW-LIST.**
   `cachedIsHover = !cachedSource || cachedSource === "hover"` — only a
   HOVER stamp, or a legacy blob written before the stamp existed, can
   light the restore. Every other door — photo, blueprint, and anything
   built later — is shut **by default, without having to be named**.
2. **THE CLICK RE-CHECKS THE LANE.** `restore()` refuses at the moment
   of the press if the blob is not HOVER-sourced, naming the door the
   numbers actually came from. Belt and braces behind the allow-list.
3. **THE REFUSAL IS ENFORCED SERVER-SIDE.** The restore names its lane
   (`expect_source: "hover"`) and `POST /api/measure/map` refuses 400 —
   *"these measurements came from the PHOTO door, not HOVER — a lane
   restores only its own source"* — so a future UI that forgets cannot
   re-open the hole. The mapper is shared, so it only holds callers that
   NAME a lane: the photo and per-elevation doors (which name none) still
   work, and unstamped legacy HOVER data still restores.
4. **WHERE THE DOOR IS OFF, IT SAYS SO** —
   `hover-restore-off-reason`: *"No HOVER restore on this estimate — its
   measurements came from the PHOTO door, not a HOVER report. Another
   lane's numbers are never restored as HOVER lines."* A missing button
   with no reason is how a contractor ends up hunting for a restore that
   must not exist.
5. **NOTHING RUNS ON LOAD** — pinned: the component may never grow a
   `useEffect`, the restore may have exactly one call site, and no other
   file may reach that button.

## 5. THE PIN HOWARD ASKED FOR
`tests/test_send135_hover_restore_lane_lock_2026_08_27.py` (11 pins),
including:
- `test_a_fresh_estimate_is_born_with_no_hover_source_and_no_lines` —
  a real estimate is created over HTTP and **read twice** (what a page
  load does): no `hover_measurements`, **no lines**, no waste_pct, both
  passes. The dialog cannot exist without the blob, and reading writes
  nothing;
- `test_a_photo_sourced_estimate_offers_no_hover_restore` — the exact
  shape of the bug: a photo-stamped blob fails the door's own lock, the
  server refuses the map, and **the refusal writes no line**;
- `test_nothing_can_trigger_the_restore_except_the_click`,
  `test_the_hover_door_is_source_locked_by_allow_list`,
  `test_the_photo_apply_writes_a_source_the_hover_door_must_not_accept`
  (ties the two files together so a rename on either side cannot re-open
  it), `test_the_mapper_refuses_a_cross_lane_restore_by_name`.

## 6. WHAT I DID NOT DO
- **Did not touch EST-381546** (read-only; 44 lines and `updated_at`
  unchanged) and **did not apply the 56 lines**.
- **Did not move the photo numbers out of `hover_measurements`.** That
  shared blob is the ruled STEP-4 design and is load-bearing for
  `/pending-runs` ("which run was applied"). Splitting the storage is a
  cross-door change and is not authorised here — so the DOOR was locked,
  not the storage. **The residual risk, named:** any future door that
  writes into that blob is shut out of HOVER restore automatically
  (allow-list), but the blob remains shared, so `_source` must keep being
  stamped by whoever writes it. If Howard wants the lanes physically
  separated, that is its own send.
- Not authorised, not touched: name-the-plane · rectify · Annotate
  retirement · the import test · phase 2 trim · quote wiring.
