# Siding Estimator — PRD (Alside Supply Edition)

## THESIS
ProQuotes exists to give contractors accurate, reliable, tape-provable takeoffs WITHOUT costing them margin the way per-scan tools do. Accuracy and honesty are the product. Everything else is optional. When prioritizing, features that serve measurement accuracy, honesty, or contractor margin outrank features that serve appearance or homeowner persuasion.

## Original Problem & Pivot
User uploaded a self-contained Vinyl Siding Estimator HTML and asked to turn it into an app. After initial build, user revealed they work for **Alside Supply** and intend to distribute this tool to their contractor customers as a value-add. Architecture pivoted to a **supplier-distributed B2B SaaS**:

- **Supplier (Alside Supply / Howard Hunt)** = the platform owner. Provides the app, sets branding, controls signup, ships product catalog.
- **Contractors** = end users. Get an access code from Alside, register their company, upload their own logo, build estimates for homeowners.
- **Homeowners** = see the contractor's branded quote with an optional "Materials supplied by Alside Supply" footer.

## Architecture
- **Backend**: FastAPI + MongoDB. JWT cookie auth (httpOnly, secure, samesite=none). Multi-tenant per Company. Resend for email. Branding stored in `settings` singleton.
- **Frontend**: React 19 + react-router + Tailwind + sonner + lucide. Installable PWA. `BrandingProvider` (public) + `CompanyProvider` (auth'd) share state.
- **Routing**: `/api/branding` public · `/api/admin/*` token-gated · everything else cookie-auth.

## Personas
- **Howard Hunt / Alside sales team** — visits `/branding-admin?token=XXX` to update supplier logo, name, tagline; hands out the contractor access code via email/sales calls.
- **Contractor owner** — registers with access code → uploads own logo → builds estimates → emails quotes to homeowners.
- **Contractor estimator** (teammate) — joins owner's company via 8-char invite code → shares catalog + estimates.
- **Homeowner** — receives a branded quote with optional "Materials supplied by Alside Supply" footer.

## Core Requirements
1. **Invite-only signup** — new companies require `SIGNUP_CODE` (rotatable from `.env`)
2. **Default catalog pre-loaded with Alside Pittsburgh dealer prices** (60+ SKUs from the 2026 5-11 price sheet)
3. **Per-company logo + name + catalog** (each contractor brands their own quotes)
4. **Multi-user companies** — owner can invite teammates via 8-char invite code
5. **Per-company "Powered by Alside Supply" footer toggle** on customer quotes
6. **Hidden supplier-admin URL** (`/branding-admin?token=...`) for Alside to manage their own branding
7. **Quote email via Resend** (configured)
8. **CSV exports** (dashboard summary + per-estimate)
9. **Installable PWA** with mobile-first sticky totals bar

## Live Endpoints
### Public
- `GET /api/branding` — supplier name, tagline, logo (used on Login page)

### Supplier Admin (token gated via `X-Admin-Token` header — query string `?token=` was removed in SEC-006)
- `GET /api/admin/signup-code`
- `PUT /api/admin/branding` `{supplier_name?, supplier_tagline?, supplier_logo_url?}`
- `POST /api/admin/upload-logo` multipart `file`

### Contractor (cookie auth)
- `POST /api/auth/register` `{email, password, name?, company_name?, invite_code?, signup_code?}` — needs `signup_code` to create a new company OR `invite_code` to join one
- `POST /api/auth/login` / `logout` / `GET /me`
- `GET /api/company` · `PUT /api/company` `{name?, logo_url?, quote_footer_enabled?}`
- `GET|PUT /api/catalog` · `POST /api/catalog/reset`
- `GET|POST /api/estimates` · `GET|PUT|DELETE /api/estimates/{id}`
- `POST /api/uploads` · `GET /api/uploads/{name}`
- `GET /api/email/status` · `POST /api/estimates/{id}/email`
- `GET /api/exports/estimates.csv` · `GET /api/exports/estimates/{id}.csv`

## ACTIVE GATE — Post-79j.61 Ordering (do not violate)

**PERMANENT RULE — No in-place data repair without a pre-heal backup
(Iter 79j.63, Jul 7 2026):** Before any script writes to a production
Mongo document — even a "purely additive" migration that only writes
mirror/derived fields — the operator MUST:
1. Write a full JSON snapshot of the pre-heal doc(s) to
   `/app/memory/backups/<YYYYMMDD_HHMMSS>_<collection>_<reason>.json`
   (create the dir if missing). One snapshot per doc, keyed by `_id`.
2. Include the exact heal query, the diff of fields that will change,
   and the git commit SHA of the code that generated the change.
3. Only after the backup file exists on disk may the mutation run.
4. Log the backup path in the finish/summary tool call so the next
   agent (or the human) can undo.
This rule triggered: on Jul 7 2026 an "add-only" heal script mirrored
NEW-shape `_scale_refs` entries into dual-shape and printed truncated
output that the agent mis-summarized as "all six healed to 4.00 ft."
The data itself was fine — but the report LOOKED like a mass overwrite,
and there was no snapshot to prove innocence quickly. Cost: 30+ min of
diagnostic time and a legitimately-warranted "did you just destroy my
calibration data?" alarm from the operator. Snapshot cost: <1 s and
a few KB. Ratio speaks for itself.
Reporting corollary: never summarize truncated tool output. If a
result is truncated, either re-run the query with narrower scope until
the full output fits, or paste the truncated block verbatim with a
note. Never fabricate the omitted rows even with a "probably similar"
assumption.

**PERMANENT RULE — Code freeze during active AI Measure runs (Iter 79j.62,
Jul 7 2026):** Do NOT edit any file under `/app/backend/` while an AI
Measure or AI Blueprint run is in flight (`status='running'`). `uvicorn`
hot-reload cancels the event loop; anything spawned via
`asyncio.create_task` (Phase A extractors, Phase B reconciler, worker
schedulers) is silently orphaned when reload fires. The run doc stays
frozen at whatever state it was in when the reload hit, and the browser
polls forever seeing that frozen snapshot.
- **Applies to**: every future fork/agent working on this codebase, not
  just the current run. Cost of one accidental edit = a burned run + at
  minimum minutes of contractor time watching grey dots.
- **Detector shipped** (Iter 79j.62): the `/status/{run_id}` endpoint
  now flips a stale `running` doc to `error` when `updated_at` has been
  idle for more than `max(60s, 2 × per_wave_budget_s)` (default 500s
  ceiling). Test coverage: `tests/test_stale_worker_detector.py` (6/6
  PASS). This makes accidental reload survivable but does NOT excuse
  the freeze rule — a mid-Phase-A kill still burns any Anthropic calls
  already dispatched in the killed wave.
- **When to unfreeze**: only after the run's status has flipped to
  `done` or `error` in Mongo (verified via `/status/{run_id}` or direct
  Mongo query), OR after 30 days (TTL). Never before.
- **Frontend edits during a run**: also risky (React hot-reload re-mounts
  the component tree, resetting the polling loop's `useEffect`). Same
  freeze rule applies to `/app/frontend/src/components/estimate/AIMeasureButton.jsx`
  and its direct dependencies.

**Standing order (Feb 2026, re-affirmed Jul 7 2026; Run 3 executed Jul 8 2026):**

1. **Confirmation Run 3** — ✅ EXECUTED Jul 8 2026 (`f423c216`, status done,
   8m52s wall-clock). Verdict basis changed by operator: **per-wall tape
   validation** replaces single-number acceptance. Tape truth: LEFT 10.3125 ·
   RIGHT 7.1875 · FRONT/BACK stepped 10.31→7.19 over last 13'4" · dormers
   15.0/15.0. Scoring + height-compression diagnosis recorded under
   Iter 79j.64 in the timeline. The three approved asymmetry fixes
   (per-corner LF, clamp-to-amber, width_ft_source) SHIPPED same day.
   Prompt-level compression mitigations STAGED pending approval.
2. **Compression prompt revision + validation run** — RESEQUENCED ahead of
   bbox routing (Jul 8 2026, operator order: "money outranks cosmetics").
   Prompt revision SHIPPED (Iter 79j.65); validation run is the user's to
   fire on the same 8 red-house photos. Acceptance: LEFT 10.31 ±0.5,
   RIGHT 7.19 ±0.5, scored via the Tape Check panel. Pass → new baseline.
3. **Per-dormer bbox routing** + true bbox-derived opening (x, y, w, h) — fixes
   the scattered-window placement on the 3D walls. **After validation run.**
   Run 3 confirmed the root cause: Phase A emits real per-photo bboxes
   (`front-w1: [712,340,168,116]` etc) but every bbox in the final
   `openings` / `openings_schedule` is zeroed `{0,0,0,0}` — Phase B drops
   them. Plumbing job, not new detection.
3. **Three.js static 3D PNG generation** — headless canvas export.
4. **Embed the PNG in the Customer Quote PDF + email.** Only after 1–3 land.

**NOTHING ELSE SHIPS BETWEEN STEPS.** Marker Coverage tile is done pending user
sign-off; no P1 or P2 backlog items ship until this gate closes. Refactor of
`ai_measure.py` / `AIMeasureButton.jsx` remains FROZEN under this gate too.

## Implementation Timeline
- **Iter 79j.69 — Count-outranks-pixel micro-candidate + SOP checklist line (SHIPPED Jul 8 2026):**
  Re-validation run `8586333a` scored **93.3% — new best** (dormers exact
  via the plane rule; left 9.7 count-diluted −0.61; right correctly
  x-plane-flagged, fallback read +1.51). Trace answers:
  - LEFT's miss was NOT a 31-course miscount: photo 1 counted **32**
    courses (one bottom row behind the woodpile) = 10.0, then the
    reconciler MEDIANED it with photo 2's shaded pixel 9.3 → 9.7. Photos
    0 & 4 counted **33 at the left corner = 10.4** (tape 10.31 ✓) —
    counts are landing when unobstructed.
  - RIGHT declined to count honestly: "shrubs and shadow obscure the
    lower half" → capture problem, not prompt problem. Pipeline behaved
    correctly (cross-plane flag, amber, re-shoot instruction).
  Changes shipped (option c):
  1. **Reconcile rule d amended (ONE line of substance)**: a
     count-derived reading OUTRANKS pixel reads even within the ±1 ft
     agreement band (median of counts only when multiple counts exist).
     Would have made left = 10.0 → Δ −0.31 → PASS.
  2. **SOP line added to onboarding checklist, verbatim per user**:
     "Short or cluttered walls: shoot straight-on and close enough that
     the bottom siding courses are visible — the AI counts courses to
     verify height, and it can't count what shrubs hide."
     (testid `ai-measure-onboarding-tip-short-walls`)
  **NEXT VALIDATION RUN (user fires)**: user re-shoots the right
  elevation per SOP (straighter, closer, bottom courses visible, clear
  of shrubs, WALL REF same plane) + this rule, same tape, same
  acceptance (L 10.31 ±0.5 / R 7.19 ±0.5). Both walls land → 93.3 is
  the floor, gate resumes at per-dormer bbox routing, red house
  exam-complete.

- **Iter 79j.68 — Measurement mode per wall in Tape Check history (SHIPPED Jul 8 2026):**
  Purpose (user's words): over a few houses this column tells us which
  mode earns its keep — if count-derived consistently beats
  pixel-derived, that's the EVIDENCE for making exposure entry a
  required capture step rather than optional.
  - Backend: `score_tape_check` derives `mode` per wall from the run
    trace — `"count"` (a contributing photo in `_source_photo_indices`
    carries `eave_courses_counted`), `"cross-plane"`
    (`height_scale_flag`), else `"pixel"` (incl. legacy runs). Stored in
    each history entry's wall rows.
  - Frontend (`TapeCheckPanel.jsx`): `ModeTag` chips (count=green,
    px=slate, x-plane=amber w/ control-case tooltip) on wall rows +
    per-wall mode line under each history row. Legacy entries (scored
    pre-79j.67) skip the line. Testids: `tape-check-mode-{wall}`,
    `tape-check-history-modes-{run_id}`.
  - Tests: `test_tape_check.py` 9/9 (count/cross-plane/pixel derivation +
    legacy-run default).
  - FUTURE DECISION HOOK: once ≥3 houses show count > pixel accuracy,
    promote exposure entry to a required capture step (P2 backlog).

- **Iter 79j.67 — (a) Re-run calibration fix + (b)(c) prompt candidate (SHIPPED Jul 8 2026):**
  **CONTROL CASE, VERBATIM (the depth rule's justification forever):
  "same ref, same plane = exact; same ref, cross-plane = +45%."**
  - **(a) STANDALONE BUG FIX** — the Re-run path hardcoded
    `siding_exposure_in=None` / `brick_course_in=None` / `reference_dim=None`
    / `elevation_tags=None`: every re-run ever fired silently discarded
    contractor calibration. Fixed at three layers:
    1. Run docs now persist all four calibration fields at creation;
       rerun rehydrates them (rerun-of-rerun chains keep them).
    2. Rerun body accepts CURRENT Calibrate popover values
       (`brick_course_in`, `siding_exposure_in`) — body > prev doc > None
       (legacy docs predate persistence; popover may change between runs).
       Frontend sends them on every Re-run.
    3. Sessions persist + restore `brick_course_in`/`siding_exposure_in`
       (recovered sessions no longer lose calibration; all 5 session PUT
       sites + resume hydration updated).
    Tests: `tests/test_rerun_calibration_iter67.py` (8/8: carryover,
    body-precedence, legacy-null, prompt content, failed-revision
    isolation).
  - **(b)+(c) PROMPT CANDIDATE (ONE revision, live now, validation run
    pending)** — none of the failed 79j.65 revision's other pieces
    returned (verified by test):
    - (b) Exposure-based course counting for WALL HEIGHTS: the injected
      SIDING EXPOSURE line now says count courses grade→eave × exposure =
      eave height, report in `eave_courses_counted`; courses are
      plane-correct by construction. Static rule 5 added.
    - (c) Depth-plane rule (static rule 6): a vertical ref may only scale
      its OWN wall plane; dormer-window WIN_REF scales dormer dims only.
      When the only vertical ref is cross-plane it may be used LAST-RESORT
      but must set `eave_scale_cross_plane: true` — never silently.
      Reconciler rejects cross-plane reads when a course-counted or
      same-plane read exists; if kept as the only reading, wall gets
      `height_scale_flag: "cross_plane"` → frontend renders amber
      **"Cross-plane scale — verify"** badge (fail-loudly doctrine).
  - **(d) RE-VALIDATION PENDING (user fires)**: same 8 photos, same tape,
    acceptance L 10.31 ±0.5 / R 7.19 ±0.5. ⚠️ OPERATOR PREREQ: enter
    3.75 in the Calibrate popover before hitting Re-run (the failed run
    and Run 3 are legacy docs with no stored calibration — the popover
    value is what flows through the new body path).

- **Iter 79j.67 — Validation run FAILED → prompt ROLLED BACK to baseline (Jul 8 2026):**
  Run `aab33c65` scored **83.2% vs 88.9% baseline** (tape-check panel).
  Right wall 10.4 vs 7.19 tape (+3.21, inverted direction); left dormer
  regressed to 17.5; right dormer EXACT at 15.0. Trace answers:
  1. **Course counting never ran** — `eave_courses_counted: null` on all 8
     photos ("Lap courses too indistinct… to count reliably"). The
     exposure×default hypothesis was falsified: nothing count-derived.
  2. **Exposure plumbing has two gaps**: (a) the calibration prompt line is
     WINDOWS-ONLY by wording ("Count rows to size windows…", line ~3878);
     (b) the **Re-run path hardcodes `siding_exposure_in=None` /
     `brick_course_in=None`** (line ~2402) — the contractor's 3.75″ never
     reached this run at all.
  3. **Actual failure mechanism: depth-mismatched vertical references.**
     The vertical-scale mandate pushed the model off horizontal bars onto
     the only vertical ref in frame — the 36″ WIN_REF on the DORMER
     window — which sits on a DIFFERENT PLANE (set back + higher than the
     main wall). Photo 6: dormer-derived 2.31 px/in applied to main-wall
     pixels (true main-wall scale ≈3.4–3.5 px/in from tape) → +3.21 ft.
     Photo 2 self-flagged it verbatim: "dormer is set back so main-wall
     vertical scale may be slightly larger, biasing this read". CLEAN
     CONFIRMATION: the right dormer used the same WIN_REF on its OWN
     plane → exact 15.0. Same ref, same plane = perfect; same ref,
     cross-plane = +45%.
  **Rollback executed**: `git` reverse-apply of commit `cf03de7` (the
  revision was isolated in one commit; parent verified to contain all
  79j.64 fixes). Kept ONLY the zero-behavior python surfacing of the
  trace fields (null under baseline). Verified: mitigation rules absent,
  original examples restored, 16/16 asymmetric tests + backend healthy.
  **BASELINE PROMPT IS LIVE.**
  **Next candidate (pending user approval), informed by the trace:**
  a. Fix the Re-run calibration-drop bug (persist `siding_exposure_in` /
     `brick_course_in` on the session; reuse on re-run) — a real bug
     independent of prompt experiments.
  b. Extend the exposure prompt line to WALL HEIGHTS (count rows ×
     3.75″), not just window sizing.
  c. DEPTH-PLANE rule for vertical refs: a vertical reference may only
     scale measurements on ITS OWN wall plane; dormer-face refs scale
     dormer dims only (this is what made the right dormer exact).
  d. Re-validation against the same tape, same acceptance (L 10.31 ±0.5,
     R 7.19 ±0.5).

- **Iter 79j.66 — Wall Breakdown dormer W×knee editors (SHIPPED Jul 8 2026):**
  The Breakdown's dormer column was a bare ft² input — correcting a dormer
  meant knowing the face-area formula by heart. Now each wall's matched
  dormer(s) (face === wall label) render W × knee mini-inputs under the ft²
  field. Edits RESCALE the ft² by the ratio of w×knee products (preserves
  the AI's cheek/shed-rise geometry factor; falls back to Σ w×knee when no
  basis), recompute headline totals, and mutate `raw_ai.dormers` — the same
  object the 3D model reads, so it follows in lock-step. NOTE: 3D sidebar
  dormer edits remain display-only overrides (need Re-run); the Breakdown
  W×knee fields are the canonical path. `setDormerDims()` in
  AIMeasureButton.jsx; testids `ai-measure-wall-dormer-dims-{wall}-{j}`,
  `-w-{wall}-{j}`, `-knee-{wall}-{j}`. Verified live: 118.25 ft² × (15/15.5)
  → 114.4.

- **Iter 79j.65 — Compression prompt revision + Tape Check panel (SHIPPED Jul 8 2026):**
  - **RESEQUENCED by operator**: compression fix + validation run now comes
    BEFORE per-dormer bbox routing ("wall heights are square footage and
    money; opening placement is pixels").
  - **ONE prompt revision, all four mitigations** (Phase A + Phase B +
    legacy single-call examples):
    1. Vertical-scale mandate — horizontal-bar px/in NEVER applied to
       vertical measurements; new Phase A fields `eave_vertical_scale_basis`,
       plus rule 5. Reconciler rejects readings citing a horizontal bar
       whenever a vertically-scaled read exists (rule 1a addition).
    2. Course-counting cross-check — `eave_courses_counted` field + rule 6
       (courses × exposure beats pixel math; report course-count value on
       disagreement).
    3. Grade-occlusion flag — `grade_occluded` + `grade_occluded_estimate_in`
       fields + rule 7 (add hidden inches, state the split) + reconcile
       rule a2 (prefer non-occluded reads).
    4. Neutralized prior anchors — all "8.5/8.7/9.0 → snapped to 9" style
       examples replaced with placeholders + explicit "no typical wall
       height / no rounding toward typical / no symmetry bias" rules
       (Phase A rule 7 tail, reconcile rule a3, rule 1c reworded).
  - **VALIDATION RUN PENDING (user fires)**: same 8 red-house photos.
    Acceptance: LEFT 10.31 ±0.5, RIGHT 7.19 ±0.5 (the two walls compression
    hurt most). Pass → new baseline prompt. Heights improve but something
    regresses → diff and decide. Score it with the Tape Check panel.
  - **Tape Check panel** (user-approved enhancement with persistence
    scope): tape values persist on the estimate as ground-truth fixtures
    (`estimates.tape_check`), per-wall Δ + pass/amber/fail
    (|Δ|≤0.5/≤1.0/>1.0), house-level accuracy % accumulating across runs —
    the history table is the accuracy artifact for the September pitch.
    - Backend: `GET/PUT /api/estimates/{id}/tape-check`,
      `POST /api/estimates/{id}/tape-check/score` (run_id optional →
      latest done run; re-score replaces the same run's entry; history
      capped 50). Tests: `tests/test_tape_check.py` (8/8, includes the
      exact red-house truth values as fixtures).
    - Frontend: `TapeCheckPanel.jsx` mounted at the bottom of the 3D view
      side panel (collapsible, shows latest accuracy % in header). Dormer
      faces normalized from the 3D model's slope-relative vocabulary
      (`slope-left` → `left`). Testids: `tape-check-panel/-toggle/-accuracy/
      -input-{wall}/-dormer-input-{face}/-verdict-{wall}/-save/-score/-history`.
    - **Run 3 scored as the baseline history entry: 88.9%** (left −1.31 fail
      under direct_consensus, right +1.31 fail, dormers +0.5 pass /
      +1.5 fail) with user's tape: left 10.3125, right 7.1875, dormers
      15.0/15.0 (front/back left null — stepped walls, single height
      ill-defined until the stepped-wall backlog item ships).

- **P1 QUEUED (behind the gate) — Accuracy Report PDF (user-approved Jul 8 2026):**
  One-page PDF export of the Tape Check history for the September supplier
  pitch. Must include: methodology line verbatim — "AI reads scored against
  contractor tape, per wall, per run" — per-run scores with per-wall deltas
  and trend, AND the honest-flag counts (how many misses the pipeline
  self-flagged amber before scoring: single-reading tags, assumed-symmetric
  widths, below-typical heights, pin-gap hints). Ships only after the gate
  (validation run → bbox routing → Three.js PNG → PDF embed).

- **P1 QUEUED — Pricing test seeds vs live DB drift (user-ordered Jul 8 2026):**
  ~14 failures + 8 errors in pricing/catalog suites (`test_pricing_parity`,
  `test_mezzo_pricing`, `test_iteration34_siding_split`, `test_iteration5/6`,
  `test_vero_pricing`, `test_lp_admin_preview_http`, `test_estimator_api`
  email/auth) because live DB prices drifted from hardcoded seed
  expectations (e.g. Starter 7.64 vs expected 7.46 — supplier applied
  pricing-admin bumps). User verdict: "a permanently-failing pricing suite
  guards nothing; ignored failures are how a real pricing bug ships into a
  $23k estimate." Fix: have the tests read expected prices from the catalog
  source of truth (live catalog endpoint / seed loader) instead of frozen
  literals — or regenerate seeds as a snapshot artifact with a refresh
  script. Also triage the auth/email errors in the same pass.

- **Iter 79j.64 — Confirmation Run 3 verdict + per-wall tape truth (Jul 8 2026):**
  Run 3 (`f423c216`) completed clean: 8/8 photos, anthropic_direct both phases,
  no empty photos / orphaned walls, dedup 39→15, wall-clock 8m52s (missed the
  5-min target — Phase A concurrency 2 + 4-min Phase B; tuning deferred).
  User then taped every wall (sketch: `red house.pdf` artifact):
  **LEFT 10.3125 ft uniform · RIGHT 7.1875 ft uniform · FRONT/BACK 27 ft gable
  ends carrying a 39" step over the last 13'4" · dormers 15.0/15.0 ·
  knees 4.06 both.** Scoring: widths exact; left dormer +0.5 (pass);
  right dormer +1.5 (single anchored read, amber-tagged, miss); LEFT height
  9.0 (−1.3) under a `direct_consensus` badge — **consensus was confidently
  wrong**; RIGHT 8.5 (+1.3) amber. Diagnosis of the systematic height
  compression (both walls regressed toward 8.5–9):
  1. **Horizontal-bar px/in applied to vertical measurements** — photo 2's own
     data shows horizontal 2.93 px/in vs vertical 2.64 px/in (11% skew).
  2. **Grade occlusion** — woodpile (left) / shrubs (right) hid the wall base;
     reads measured to VISIBLE grade.
  3. **Prior anchoring** — Phase A/B prompt examples are saturated with
     8.4–9.0 values ("snapped to 9"); photo 2 computed 8.3 then "rounded to
     ~8.5" toward the prior. NOTE: front/back reads (8.5/9.3) are near the
     area-weighted truth of the stepped wall (≈8.77) — the compression story
     is a left/right (uniform wall) story.
  **Acceptance basis going forward is PER-WALL tape validation, not a single
  aggregate number.** Prompt-level mitigations (vertical-scale mandate,
  course-counting cross-check on 4" lap, grade-occlusion flag, neutralized
  prompt examples) are STAGED, pending user approval + a validation run.

- **P1 BACKLOG — Stepped-wall detection (v1 = detect-and-amber-flag, NOT full modeling):**
  Fixture: the red house (`673707d5-9b7e-4d8f-8eaf-63c86820f611`) — front/back
  27 ft gable ends step from 10.3125 ft down to 7.1875 ft over the last 13'4"
  (39" drop). A single `height_ft` per wall is ill-defined on such walls.
  v1 scope: Phase A/B emit `stepped: true` (+ optional `step_profile`) when a
  wall's eave line visibly changes height; frontend renders an amber
  "this wall appears stepped — verify area" chip; area math keeps using the
  area-average height. Full multi-segment wall modeling is explicitly OUT of
  v1.

- **Iter 79j.64 — Asymmetric-wall fixes (SHIPPED Jul 8 2026):**
  1. **Per-corner `outside_corner_lf`** — new `_corner_lf_from_walls()`:
     corner posts stand at eave lines; per corner use the adjoining
     EAVE-side (non-gable) wall's height, min() for hip/ambiguous. Overrides
     Claude's estimate whenever all 4 walls carry heights. Tape check:
     2×10.31 + 2×7.19 = 35.0 ✓ (old formula: 4×8.9 = 35.6).
  2. **Clamp-to-amber** — the <7 ft "nonsense" clamp now only replaces <4 ft
     junk (story-units / 0.7-ft fractions). 4–7 ft readings are KEPT +
     `_height_flag: "below_typical_range"` + amber "Under 7 ft — verify"
     badge in HouseModel3D (red-house right wall tapes 7.19 ft — one low
     read and the old clamp would have erased real asymmetry).
  3. **`width_ft_source` provenance** — Phase B schema now requires width
     provenance per wall (`direct_ref` / `direct_single_reading` /
     `assumed_symmetric` / `estimated_no_direct_view`); HouseModel3D renders
     an amber "Width assumed symmetric" badge (Run 3's right wall width was
     silently "assumed symmetric with left wall" — only discoverable in note
     text).
  4. **Pin-gap false-positive fix** — Run 3 flagged BOTH dormers "unanchored"
     though each width was anchored to a contractor wall bar. Two dead paths
     fixed in `_derive_pin_gap_hints`: source-photo lookup used nonexistent
     keys (`source_photos` → real `_source_photo_indices`), and the anchor
     regex never scanned `_per_photo_readings[role=width].notes` /
     `_reconciliation_note` where citations actually live (also added
     `bar scale`/`wall bar` variants + dual-schema `_scale_refs` support:
     `inches` OR `real_ft`). Hints now carry real `source_photo_idxs`.
  Tests: `tests/test_asymmetric_walls_iter64.py` (16/16) — includes the
  exact Run 3 dormer payloads as regression fixtures. Full AI-measure domain
  suite 157/157 green.

- **Iter 79j.64 — Session Recovery Fix 2 + Fix 3 (SHIPPED Jul 8 2026):**
  - **Fix 2 (loud recovery banner)**: when the server session holds photos but
    the device has nothing loaded, the old quiet sky-blue "Resume?" strip is
    now a bordered amber banner with an "SAVED WORK FOUND ON THE SERVER"
    header bar naming the specifics (N photos / reconciled AI result /
    markers on N photos) pulled from the session at detection time
    (`pendingSessionMeta`). Testids: `ai-measure-resume-banner`,
    `ai-measure-recovery-details`, `ai-measure-resume-btn`,
    `ai-measure-discard-btn`.
  - **Fix 3 (destructive confirms)**: Start Over (footer), Start Fresh
    (recovery banner) and per-photo Remove (×) now open a red confirm modal
    stating EXACTLY what gets destroyed (photo counts, AI result, marker
    counts, "including the markers you drew on it" for photo removal) before
    executing. Testids: `ai-measure-destructive-confirm-{backdrop,modal,details,cancel,proceed}`.

- **P2 (FROZEN)** — **Refactor `AIMeasureButton.jsx` (3534 lines) + `HouseModel3D.jsx` (1553 lines)** — explicit gate before this touches production:
  - Prerequisite 1: red-house photos pass the stability pair (two consecutive runs producing equivalent JSON).
  - Prerequisite 2: ranch + hip-roof houses successfully validate through the two-phase pipeline (proves the current code isn't accidentally red-house-shaped).
  - Acceptance test for the refactor iteration itself: full regression suite green + a before/after run on the red-house photo set producing byte-identical (or semantically-identical) JSON — zero behavior changes allowed. Refactor becomes its own dedicated iteration; nothing else ships alongside it.

- **P1 QUEUED (post-Run3)** — **Trace Coverage tile** (Feb 2026): tight fence per user — 4 wall cells + N dormer cells, each showing count of direct-view photos from `_source_photo_indices.length`. Color: green ≥2, amber 1, red 0. Read-only. NO new detection logic — purely a view over data Phase A already emits. Half-day scope. Ship only after Run 3 validates the current defect fixes.

- **Iter 79j.49** — **Soft input validation for customer contact fields** (Feb 2026): warn-don't-block policy across JobInfoPanel, ISS editor, and QuoteModal.
  - **`src/lib/validate.js`**: four helpers, each treating EMPTY as valid so a draft never gets shouted at.
    - `isValidEmail`: basic `something@something.tld` regex (catches "gmial.con" typos without over-rejecting valid unusual addresses).
    - `isValidPhone`: strips non-digits; valid if exactly 10 digits, or 11 with a leading 1. Presence of alpha chars (`x`/`ext.`) treated as intentional extension formatting → skipped.
    - `isValidZip`: `/^\d{5}(-\d{4})?$/`.
    - `formatPhoneUS`: returns `(AAA) BBB-CCCC` for cleanly-10 or 11-with-leading-1 inputs; ALL other shapes (extensions, international, in-progress typing) returned untouched.
  - **`index.css`**: global `.input::placeholder` opacity .55 + italic + `var(--muted)` color so `e.g. (412) 555-0100`-style hint text can never be mistaken for a populated value.
  - **JobInfoPanel**: per-field `touched` state set on blur; warnings render only when `touched && non-empty && invalid`. Added placeholders (`e.g.`/`p. ej.` prefix per lang) + blur-time phone auto-format for `customer_phone`, `customer_phone_alt`, `customer_fax`; email warning on `customer_email`; ZIP warnings on `address_zip` + `billing_zip`. Every field gains `aria-invalid` + `aria-describedby` pointing at a `<FieldWarning>` component styled with `--warning-text`.
  - **ISSEstimateEditor**: same treatment on its `iss-customer-email` (email) and `iss-customer-phone` (cell) inputs — placeholder + blur warning + phone auto-format + aria-invalid.
  - **QuoteModal (send dialog)**: `emailInvalid = !!email && !isValidEmail(email)`. When true, a bold warning line appears next to the recipient input, `aria-invalid="true"` set, AND the Send button is `disabled` — the backend's EmailStr validation would reject the malformed value with a 422 anyway; fail helpfully in the UI. The "will be saved to the estimate" note is suppressed while invalid so the two hints don't stack.
  - **i18n**: 5 new keys in EN + ES (`est.exampleLead` "e.g."/"p. ej.", `est.warnEmail`, `est.warnPhone`, `est.warnZip`).
  - **Verification via Playwright smoke** (5/5 tests):
    1. Typed `"sdasdsf.com"` in email → tab away → warning present, `aria-invalid="true"` ✓
    2. Fixed to `"valid@example.com"` → warning cleared live, `aria-invalid="false"` ✓
    3. Typed `"4125550100"` in cell phone → blur → value became `"(412) 555-0100"` ✓
    4. Typed `"123"` in cell phone → warning shown ✓
    5. Typed `"123"` in ZIP → warning shown ✓
  - Frontend + backend lint clean.

- **Iter 79j.48** — **Auto-populate estimator / date / state at create time** (Feb 2026):
  - **Backend** (`routes/estimates.py POST /estimates`): after building `doc` from the request body, fill-if-empty three fields — `estimator` gets the creating user's `name`; `estimate_date` gets `now[:10]` (server-side UTC fallback); `address_state` gets copied from the company's most-recently-updated estimate that has one (most contractors are local, so the last-used state is a strong default). Every fill is `if not (doc.get(...) or "").strip()` — client values are NEVER overridden.
  - **Frontend** (`pages/Dashboard.jsx createEstimate`): swapped `new Date().toISOString().slice(0,10)` (UTC — evening ET rolled to tomorrow) for `new Date().toLocaleDateString("en-CA")` (YYYY-MM-DD in local time).
  - **Verification**: three curl scenarios confirmed — empty body seeds `estimator="Howard Hunt"` + today's date; the next empty-body create picks up `CA` from a prior estimate; explicit `{estimator, estimate_date, address_state}` in the request body all survive verbatim. Backend + frontend lint clean.

- **Iter 79j.47** — **Customer contact + company + billing + lead source on estimates** (Feb 2026): 18 new optional fields wired end-to-end without blocking drafting or autosave.
  - **Backend model** (`models.py` `EstimateIn`): added 10 contact/lead + 8 structured-address fields, all `Optional[str] = None`. The PUT handler's `model_dump(exclude_none=True)` means partial payloads never clobber stored values — verified with a partial PUT that kept email/phone/company/lead intact while only `customer_name` updated.
  - **Frontend payload whitelist** (`useEstimate.js` `buildPayload`): explicit line per field, with `.trim()` on email/phone/fax to strip paste noise, plain `|| ""` on the rest so autosave produces stable JSON.
  - **JobInfoPanel restructure** (`components/estimate/JobInfoPanel.jsx`): the flat 5-input grid is now four logically grouped sections, each introduced by a small uppercase sub-header (same visual pattern as "Material Colors"):
    1. **Customer** — name / company / contact title.
    2. **Contact & Lead** — cell / secondary / fax, then email / preferred-contact select / lead-source select with a reveal-on-demand detail input for `other` and `referral` slugs.
    3. **Job & Billing Address** — 4-field job grid (Street half-width, City, State select of 50+DC, ZIP with `inputMode=numeric maxLength=10`). Every part change also recomposes the canonical single-line `address` string ("street, city, ST zip") via a `composeAddress()` helper so quote docs / CSVs / geocoding keep reading the same field. Legacy single-line `address` values are best-effort parsed for DISPLAY when structured parts are empty (zip regex, 2-letter state, first comma segment = street) — parts are persisted on first user edit. Full-width "Billing address same as job address" checkbox (`billing-same-checkbox`) — CHECKED when `billing_address` is empty; unchecking copies the job parts into `billing_street/city/state/zip` + `billing_address` and reveals the same 4-field grid; re-checking clears all five billing fields.
    4. **Estimate** — # / date / estimator + full-width Scope of Work textarea.
    - Every label carries `htmlFor/id`. `autoComplete="off"` on every contact/address input (Step 6b).
    - **Header hint badge**: when `customer_email` is empty, a small amber "ADD EMAIL TO SEND QUOTES" badge (`data-testid=contact-hint`, hint tokens + Lightbulb icon) sits next to the "Job Information" title — visible even when the panel is collapsed.
    - **Collapsed summary line**: appends `customer_company` after the name and shows one contact chip (`customer_phone || customer_email`).
  - **Two-way email sync** (Step 4): `QuoteModal` initializes the recipient input from `customer_email || recipient_email`; a small "This email will be saved to the estimate" note (`data-testid=quote-email-will-save`) shows when `customer_email` is empty. `EstimateEditor.onEmail` success path replaces the old `Object.assign(est, data)` mutation (which never re-rendered) with a proper `update(data)` call, AND writes back `customer_email: recipient_email` when the sent address differs from what's stored. Same write-back in `ISSEstimateEditor.onEmail` via `updateField("customer_email", …)`.
  - **ISS editor customer grid** (Step 5): added `Email` (`iss-customer-email`, `type=email`) and `Cell Phone` (`iss-customer-phone`, `type=tel`) alongside the existing Customer / Address / Date row. Its PUT payload spreads the whole estimate, so no schema-side change is needed.
  - **Displays + exports** (Step 6): both `QuoteModal` printable "Prepared For" block AND `emailQuote.js` `buildEmailHtml` now render (in order) company (bold) above the customer name; "phone · email" line under the address; and a "Billing: …" line only when `billing_address` is set. Lead source, fax, and preferred contact method are NEVER printed on customer documents. `routes/estimates.py`: the all-estimates CSV gains Email/Phone/Company/Lead Source columns after Address; the single-estimate CSV gains rows for all 10 new fields — verified via curl (`Email,jane@acme.com`, `Cell Phone,555-1234`, `Company,Acme LLC`, `Lead Source,referral`, etc.). Dashboard search filter matches `customer_email/customer_phone/customer_company`. `AcceptPage`, material list, print takeoff, measurement report intentionally untouched — they were on the theme-system exclusion list too and stay neutral.
  - **Autofill CSS** (Step 6b): `index.css` `.input:-webkit-autofill` (+ `:hover`/`:focus`/`select`/`textarea` variants) overrides Chrome's pale-blue with `-webkit-box-shadow: 0 0 0 1000px var(--surface) inset` + `-webkit-text-fill-color: var(--ink)` + `caret-color: var(--ink)` + `transition: background-color 100000s`. Theme tokens win regardless of Chrome autofill.
  - **i18n** (Step 7): 33 new keys in EN + 33 in ES covering all labels, lead-source presets, contact-method options, hint text, and the "email will save" note. Bilingual verified in dictionary structure.
  - **Verification**: curl round-trip PUT+GET returns all 18 new fields; partial PUT keeps stored values (name updated, email/phone/company/lead survived); both CSVs include the new columns/rows; browser smoke sequence confirmed contact-hint appears when email empty and disappears when set, 4-section layout renders with all sub-headers + testids present, billing-same checkbox correctly reflects `billing_address === ""`. Backend 36-test regression suite still green. Frontend ESLint clean on changed files.

- **Iter 79j.46** — **User-selectable theme system (contractor UI only)** (Feb 2026): shipped a full palette-switcher for the working surface without touching customer-facing documents.
  - **Semantic tokens (`src/index.css`)**: `:root` now defines a full set of variables covering surface + text + brand + bar + accents + status + hints (33 tokens). Component classes (`.btn-primary/.btn-secondary/.btn-ghost/.btn-danger/.input/.label/.card/.section-tag/.sell-bar` + body) rewritten to reference `var(--…)` throughout — the sell-bar accent, primary button label color, focus ring, and dashed borders all now respect the active theme.
  - **7 theme blocks**: `[data-theme="blueprint"]` (blue), `forest` (green), `steel` (slate), `highvis` (yellow with black label), and `dark` (Jobsite Dark full palette with dark surfaces + white ink + orange accents). Default `:root` = the Safety Orange look (unchanged from Iter 79j.45). "orange" resolves to no attribute set (matches :root); "auto" resolves via `prefers-color-scheme` to `dark` else `orange`.
  - **Codemod**: `/tmp/theme_codemod.py` (temp) rewrote 100+ `.jsx/.js` files under `src/` to reference the semantic vars via ordered rules — bracketed Tailwind classes and plain `bg-white` only. Inline `style={{…}}`, JS color strings, canvas/SVG drawing colors, and shadcn `components/ui/` LEFT UNTOUCHED. Excluded customer-facing files: `AcceptPage.jsx`, `lib/emailQuote.js`, `lib/materialList.js`, `lib/printTakeoff.js`, reserved `components/QuoteModal.jsx`.
  - **Picker**: `src/lib/themes.js` (registry with 3-color swatches + `readStoredTheme/applyTheme/setTheme/watchSystemTheme` + `resolveAuto`); `src/components/ThemePicker.jsx` (palette-icon `btn-ghost` button → Radix Popover with role="radiogroup" list — each row = 3-dot swatch chip + name + check, `aria-checked`, instant apply, `aria-live` status). `inline` prop renders same list without popover chrome for the Team-page card. Mounted next to `<LangToggle />` in `Layout.jsx` header and as an inline `<ThemePicker inline />` on the Team page with a bilingual blurb "Does not affect customer quotes".
  - **i18n**: 9 new keys in EN + ES (`theme.toggle.aria`, `theme.auto`, `theme.orange` "Safety Orange", `theme.blueprint` "Blueprint Blue", `theme.forest` "Forest Green", `theme.steel` "Steel", `theme.highvis` "High-Vis Yellow", `theme.dark` "Jobsite Dark", `theme.status`, `theme.blurb`).
  - **Boot + FOUC guard**: `src/index.js` applies stored theme on hydrate + calls `watchSystemTheme` so "auto" flips live when the OS scheme changes. `public/index.html` gained an inline `<script>` in `<head>` that reads `localStorage["ui-theme-v1"]`, resolves `auto` via `prefers-color-scheme`, and sets `data-theme` BEFORE first paint — no flash of the orange default for dark-mode users. Service worker cache name bumped `vse-v1` → `vse-v2-theme` so cached shells refresh.
  - **Verification**: Login screen still renders identically to the WCAG pass (Safety Orange, black-on-orange SIGN IN). Dashboard smoke sequence confirmed: (1) popover opens with 3-dot swatches + 7 rows + Auto checked; (2) clicking Blueprint switches WORKSPACE tag + "OPEN ISS QUOTES" link to blue instantly; (3) clicking Jobsite Dark flips to dark surface + white ink + orange accents; (4) `data-theme="dark"` attribute confirmed on `<html>`. AcceptPage grep confirms 19 literal hex colors preserved, 0 `var(--…)` — customer surfaces untouched as required. Backend regression suite (36 tests) still green. Frontend ESLint clean on changed files.

- **Iter 79j.45** — **WCAG AA accessibility pass (site-wide)** (Feb 2026): systematic contrast + focus + motion + emoji cleanup across the entire React frontend, brand palette preserved.
  - **Rule 1**: 321 occurrences of `text-[#A1A1AA]` on light surfaces → `text-[#71717A]` (4.83:1). Kept as-is on dark surfaces (bg-[#09090B] / bg-black / text-white sibling, 7.76:1) via same-className dark-bg heuristic. Border and canvas/SVG usages untouched.
  - **Rule 2**: 75 occurrences of `text-[#F97316]` on light → `text-[#C2410C]` (5.18:1). Kept on black modal headers / sticky sell-bar / dark logo boxes. Inline-style JS constants that feed `style={{color}}` on light rows also darkened (`Dashboard.KIND_TABS`, `VeroJobSnapshot.accentText`, `MezzoJobSnapshot.accentText`, `AcceptPage`).
  - **Rule 3**: 40 total `bg-[#F97316] text-white` combos → `bg-[#F97316] text-[#09090B]` (7.10:1). Covers `.btn-primary` in `index.css`, orange CTA links in `emailQuote.js` (Accept button) and `printTakeoff.js` source-tag pill, and every orange-CTA occurrence across pages + components + submodals.
  - **Rule 4 CSS**: `:root --muted` → `#71717A`; added `--brand-text: #C2410C`; `.input:focus` border switched to `var(--brand-text)` (3:1 focus indicator on white); added `@media (prefers-reduced-motion: reduce)` block zeroing animation/transition duration + scroll-behavior.
  - **Rule 5 emoji → lucide-react**: `HoverImportButton` (2× 🔍→`ScanSearch`), `GuidedCaptureWizard` (⚡→`Zap`), `AIMeasureButton` (💡→`Lightbulb`, 🔍→`ScanSearch`), `PhotoAnnotateModal` (✏️→`Pencil`; step titles 🎯→`Crosshair`, 📏→`Ruler`, 🪟→`AppWindow`, 🧱→`BrickWall`, 🏠→`Home`), `ProfileAnnotator` (✨→`Sparkles`), `Dashboard` (💡→`Lightbulb`). Every icon has `aria-hidden="true"` + small size class. ASCII/pictograph diagrams in `GuidedCaptureWizard` (`"🏠 ← YOU (25-30 ft)"`) intentionally left — instructional content, not UI chrome.
  - **Rule 6 component fixes**: `EmailPipeline.Stage` gained `textColor` prop (defaults `text-white`); "Sent" + "Clicked" stages pass `text-[#09090B]`. `SectionAccordion` "commonly needed" Lightbulb bumped to `text-yellow-700`. `InstallBanner` Smartphone on orange tile → `text-[#09090B]`.
  - **Design tokens (`/app/design_guidelines.json`)**: `colors.text.muted` → `#71717A` + `muted_on_dark_only: "#A1A1AA"`; `colors.borders.focus` → `#C2410C`; `colors.brand.primary_text_on_light: "#C2410C"` + `primary_text_on_dark: "#F97316"`; `surfaces.primary_button` spec updated for black-on-orange labels; `components.inputs` focus + `components.badges` spec use `#C2410C`; `icons_strategy.library` → `lucide-react` with an explicit "never use emoji as UI icons" note; new `accessibility` section codifying 7 rules.
  - **Email/print HTML** (`emailQuote.js`, `materialList.js`, `printTakeoff.js`): `C.faint` → `#71717A`, new `C.accentText: "#C2410C"` on section headers + Valid-Through pill, Accept CTA now `color: ${C.ink}` on `background: ${C.accent}`.
  - **Verification**: `grep bg-[#F97316].*text-white` → 0 hits; `grep 🔍|⚡|💡|✏️|🎯|📏|🪟|🧱|✨` in JSX → 0 UI-icon hits (only ASCII diagrams remain). Frontend ESLint clean on changed files. Login screen smoke screenshot confirms black-on-orange SIGN IN button rendering correctly.

- **Iter 79j.44** — **Run2 trace defects — dormer-scan removed, per-dormer UI rows, defect 2 fully closed** (Feb 2026): Run 2 confirmed the empty-retry (Iter 79j.43) diagnosis (photo 2 succeeded → left dormer appeared; different photo now fails silently) and hardened three more findings.
  - **Removed the deep-dormer-scan subsystem end-to-end**: gone are `DORMER_PROMPT`, `_crop_top_strip`, `_run_dormer_pass_for_photo`, `_is_skyline_photo`, `_merge_dormer_hits`, and the `deep_dormer_scan` invocation block in `_execute_ai_measure_worker`. Run 2 showed the legacy roofline crop was still injecting corrupt data — 3 openings with null `opening_id`s, a hit on a nonexistent `rear-left` wall, and 24 sf of dormer face credited to the FRONT wall for side-slope dormers. Two-phase Phase A/B now owns dormer detection end-to-end via the `dormers[]` array. Frontend: `deepDormerScan` state var + toggle UI + form-field submission removed. Backend: `deep_dormer_scan: bool = Form(False)` still accepted for backward compat but is a no-op. Regression: 7 previously-passing merge-dormer tests deleted alongside the helper (they were testing dead code); 2 new tests assert the helpers no longer exist AND the worker no longer references the scan stage.
  - **Per-dormer editable UI rows** (defect 2): the "Dormer W (ft)" input was displaying the primary dormer only, and its value cascade even after Iter 79j.43 wasn't matching the reconciled `dormers[0].width_ft` verbatim across multi-dormer houses. Run 2 shipped 2 dormers (widths 13.5 + 16) → panel showed a single row with 19.7 ft. Refactored `buildHouseJson` around a new `resolveDormer(ad, i)` per-index resolver: each dormer independently reads its OWN `width_ft`, `width_source`, `knee`, `offset_x_ft` from the reconciled JSON, applies per-index override (keyed by `overrides.dormers[i]`), and produces its own `widthSource` badge tag. UI now renders one editable row per detected dormer (`data-testid=ai-measure-3d-dormer-row-{i}` + child `ai-measure-3d-dormer-width-{i}`), each with its own provenance badge + reconciler-verbatim value. Primary (index 0) still mirrors legacy `overrides.dormer` for back-compat.
  - **Single-reading tag surfaced in code** (defect 4 verified applied): Iter 79j.43 added the `direct_single_reading` value to the RECONCILE_PROMPT schema. This iter wires the corresponding UI badge in the per-dormer row loop as amber "Single reading" (`data-testid=ai-measure-3d-dormer-width-single-reading-{i}`) with tooltip "Only ONE photo captured a direct view of this dormer face — the reading is real but couldn't be cross-checked. Capture a second angle before quoting." The Debug-view amber sanity-check banner block was updated to detect the new value across the whole dormer array (`dormers.some(...)`).
  - **Empty-retry hardening verified** (defect 1): the retry-once + orphan-wall detection path added in Iter 79j.43 is the correct fix for Run 2's failure mode (different photo goes empty each run). No new changes needed; Run 3 should surface the amber banner if a photo fails.
  - **Tests** — `/app/backend/tests/test_run1_defects.py` updated: 7 merge-dormer tests removed, 2 new tests added (`test_dormer_scan_helpers_are_gone` + `test_deep_dormer_scan_flag_still_accepted_but_noop`). 9 tests total pass. 44 total across the AI-measure regression suite still green (`test_run1_defects` 9 + `test_two_phase_pipeline` + `test_opening_dedup_twin_safety` + `test_dormers_array_end_to_end` + `test_roof_type_material_math`). Frontend + backend lint clean. Backend restarted cleanly, `/api/branding` returns 200.

- **Iter 79j.43** — **Run1 trace defects — silent empties, dormer width mismatch, dormer-scan orphan openings, single-reading over-promise** (Feb 2026): four defects from a real 8-photo run trace fixed in one iter.
  - **DEFECT 1 — Silent empty Phase A extractions**: photos 2 and 7 returned nothing (no walls_visible, no openings, no eave, no dormers). The orchestrator carried on as if they were healthy, silently orphaning the left wall (photo 2 was the only left-elevation shot) and the left dormer. Fix in `routes/ai_measure.py`: new `_is_empty_extraction()` helper + `_extract_one_photo` now retries ONCE with a stronger nudge when the first call is empty. If still empty after retry, tags `_empty_extraction: true` and preserves both the reason and the retry marker. Orchestrator (`_run_two_phase_pipeline`) then computes an empty-photo list + orphaned-wall set (walls no non-empty photo covered) and surfaces them on the final raw as `_empty_photos` + `_orphaned_walls`. Aggregator forwards them to the frontend as `measurements._ai_empty_photos` + `_ai_orphaned_walls`. AIMeasureButton renders a persistent amber warning banner (`data-testid=ai-measure-empty-photos-banner`) naming each dead photo and each orphaned wall. A dead photo now NEVER fails silently.
  - **DEFECT 2 — Dormer width display bug (reconciled 18 ft → shown 7.2 ft with green DIRECT badge)**: `HouseModel3D.buildHouseJson` cascade prioritised `derivedDormerWidth` (opening-bbox math) OVER `aiDormer.width_ft` even when the reconciler explicitly tagged a valid `width_source`. Result: badge said green DIRECT (from `aiWidthSource`) but value came from a client-side guess — user-visible mismatch. Fix: when `aiWidthSource` is any of the enumerated AI tags (`direct_consensus` / `direct_single_reading` / `direct_disagreement` / `back_solved_from_opening` / `estimated_no_direct_view`), the width value MUST use `aiDormer.width_ft` verbatim. Same treatment for `offset_x_ft`. The `derivedDormerWidth` fallback now only fires for legacy single-call runs that lack `width_source`.
  - **DEFECT 3 — Dormer-scan openings misassigned + face SF uncredited**: `_merge_dormer_hits` was appending scan hits as plain wall openings — no `on_dormer` flag, no `opening_id`, no `along_wall_ft`, no `_source_photo_indices`. Result: on the right wall, a slider Claude found on the dormer face got listed under the wall's regular openings instead of the dormer, and `dormer_scan_added_sf_by_wall` stayed empty because Claude returned 0 for `dormer_face_sqft` on the sub-crop. Fix: every hit is now tagged `on_dormer: True`, given a `dormer_scan_<uuid>` opening_id, carries `along_wall_ft: null` + `_source_photo_indices` for provenance, and when Claude omits `dormer_face_sqft` but reports valid width/height we synthesise a face_sqft in the residential 16-72 ft² band (formula: `(width_in/12+3) × (height_in/12+1.5)` clamped) so the wall's dormer takeoff is credited. New `dormer_scan_synthesized_face_sf: bool` flag on the raw so the debug view can distinguish real vs synthesised face sf.
  - **DEFECT 4 — `direct_consensus` from a single photo reading**: rule (e) in `RECONCILE_PROMPT` said "if direct readings agree within ±1 ft, take the median → direct_consensus" without a minimum count, so a lone reading trivially "agreed" with itself and got promoted to green. New rule split: (e) requires TWO OR MORE readings for `direct_consensus`; (f) covers EXACTLY ONE direct reading with a new tag `direct_single_reading`. Schema enumerations for BOTH `walls[].height_ft_source` and `dormers[].width_source` extended with the new value. Frontend maps `direct_single_reading` → amber "Single reading" badge (`data-testid=ai-measure-3d-dormer-width-single-reading`) with tooltip "Only ONE photo captured a direct view — the reading is real but couldn't be cross-checked. Capture a second angle before quoting." Applied to both the primary dormer widget and the aiDormersList mapping so multi-dormer runs get the same tag.
  - **Tests** — `/app/backend/tests/test_run1_defects.py` (10 tests, all PASS): empty-extraction detection covers empty/error/well-formed cases; `_merge_dormer_hits` tests verify `on_dormer=True`, unique `opening_id`, `along_wall_ft: null`, `_source_photo_indices`, face_sf crediting (real + synthesised), and multi-hit preservation; RECONCILE_PROMPT tests verify the new tag enumeration and the "TWO OR MORE" + "EXACTLY ONE" rule text; aggregator surfaces `_ai_empty_photos` + `_ai_orphaned_walls` end-to-end. 34 prior regression tests (dormers array, opening dedup, two-phase pipeline, Anthropic direct key) still pass — 66/66 targeted regression suite green.

- **Iter 79j.42** — **Backend env support for `ANTHROPIC_API_KEY` direct routing** (Feb 2026): the user was hitting universal-key budget limits repeatedly. Added `_pick_llm_api_key(provider)` helper in `ai_measure.py` — when `ANTHROPIC_API_KEY` is set, every Anthropic Claude call (main worker, rerun, cross-check, OCR-scale) uses the direct key + bypasses the Emergent LiteLLM proxy; other providers (Gemini, OpenAI) continue through the proxy. Backend-only env var (never exposed to the frontend bundle). 6 pytests in `test_anthropic_direct_key.py` verify: (a) Anthropic prefers direct when set; (b) falls back to Emergent when unset; (c) Gemini/OpenAI never route through the direct key; (d) whitespace-only values are ignored; (e) leak guard — no frontend file may reference `ANTHROPIC_API_KEY`. All 6 pass.

- **Iter 79j.22** — **3D House Model tab shipped in AI Measure modal** (Feb 2026): the parametric 3D house viewer promised in Iter 79j.21 is now wired into the AI Measure results block as a "Preview / 3D Model" tab toggle. Auto-lands on Preview on every new run.
  - **New component**: `/app/frontend/src/components/estimate/HouseModel3D.jsx` — Three.js (`three@0.184.0` + `OrbitControls`) parametric render built from `preview.raw_ai.walls` + `preview.raw_ai.openings` + `preview.measurements._ai_avg_wall_height_ft`. `buildHouseJson(preview, overrides)` derives footprint (max of front/back widths × max of left/right widths), eave height, roof pitch (defaults to 6/12 with amber badge — Claude does NOT extract pitch), gable-end triangles on left/right, and auto-spaces openings across each wall.
  - **Editable side panel**: pitch dropdown (4/6/8/10/12), eave height (number), per-wall width (number). Amber "estimated" badge (`data-testid=ai-measure-3d-amber`) appears on any defaulted or low-confidence field — pitch is always amber. Edits update the 3D scene LIVE but do NOT recompute estimate quantities; a purple hint reminds the contractor to hit Re-run in the footer if they want the estimator to reflect the override.
  - **SSOT preserved**: side panel's "This wall — AI takeoff" reads from `preview.measurements._per_elevation_breakdown` (backend-computed); "Whole-house materials" section reads item names + qtys straight from `preview.lines[]` (filtered to siding/trim/corners/j-channel/starter). No material math re-implemented client-side.
  - **Click-to-select facade**: Three.js raycaster on canvas click switches the side panel's active facade. 4 facade buttons (front/right/back/left) mirror the click behavior for touch/mobile.
  - **Wired into `AIMeasureButton.jsx`**: new `previewTab` state ("preview" | "3d") auto-resets to "preview" on new run id. Tab toggle (`data-testid=ai-measure-preview-tab` / `ai-measure-3d-tab`) sits between the confidence chips + AB history header (always visible) and the tab-scoped body (per-elevation card + measurements grid + openings schedule on Preview; 3D scene on 3D). 3D tab carries a BETA pill.
  - **Verified end-to-end**: opened fixture `EST-675749` with a completed Claude Fable 5 run (8 photos, 4 walls, 11 windows, 3 doors) → 3D tab renders a photorealistic parametric house with amber-colored gable + purple ground plane + dark roof + blue-tinted window panes; pitch 6→10 update rebuilds the scene; right-facade click switches the side panel to show width=37 ft; materials section correctly lists "Charter Oak Standard color Dutch Lap 4.5" .046 · 11.4 SQ · Pelican Bay Shakes 9" · 3.7 SQ · 38 Series Lap ...· 137 PCS" etc from the persisted `preview.lines`.
  - **Fixes applied post-testing**: (1) added `min-h-0` + fixed `h-[640px]` on the right-column flex container so the `flex-1 overflow-y-auto` Materials pane grows to fill remaining space instead of collapsing to 0 height; (2) rewrote `<option>{p}/12</option>` to `<option>{\`${p}/12\`}</option>` to eliminate an Emergent dev-instrumentation `<span> cannot be a child of <option>` hydration warning.

- **Iter 79j.30 · UX FIX** — **Silent budget-exceeded failure** (Feb 2026): user report — clicked Run AI Measure, nothing happened. Root cause: Emergent LLM Key budget was $18.82 spent vs $18.80 cap → LiteLLM raised `BadRequestError: Budget has been exceeded!` → worker wrote `status:"error"` on the run doc → polling loop threw the error into `runMeasure`'s catch → `toast.error()` fired but Sonner is rendered BEHIND the modal (z-index-wise it's covered) AND auto-dismisses in 4s → user saw the busy spinner clear and the modal return to idle with no visible message. Silent failure on a $-affecting condition.
  - **Fix** — `AIMeasureButton.jsx`: added `runError` state + a persistent inline banner at the top of the modal body (above the Resume banner, so it renders BEFORE preview exists too). Test-id `ai-measure-run-error-banner`. Budget-exceeded errors get their own recognizable copy: "Universal Key budget exhausted — Open Profile → Universal Key → Add Balance (or toggle Auto Top-up). Once topped up, click Run again — nothing on this estimate is lost." Non-budget errors show the raw `e.message` in a `whitespace-pre-wrap` div. Dismissible manually, auto-clears on next successful run.
  - **Also** still fires the sonner toast for users who scroll fast — belt + suspenders.
  - **Verified** with lint + 94 relevant pytests still green. Code path: `runMeasure` catch → `setRunError(msg)`; render at line ~1495 above `resumePrompt` banner; auto-clear at `setPreview(data); setRunError(null)` on success.

- **Iter 79j.29 · BUG FIX** — **Re-Run silently disabled after Session Resume** (Feb 2026): user report — after clicking Resume on a saved AI Measure preview, the Re-Run button appeared but did nothing when clicked. Root cause chain:
  1. **Backend**: Fresh file-uploads (via `files=` multipart) to `POST /measure/ai-measure` were held in memory only — the `photo_paths` field on the run doc was left `None`. So if the frontend's `photoUrls` state ever got wiped, the filenames were unrecoverable.
  2. **Frontend autosave clobber**: The session-autosave effect wrote `{photo_urls: [], preview: {...}}` whenever the two got out of sync (e.g. delete-last-photo, quick modal close), poisoning the session doc.
  3. **Silent UI**: On Session Resume, `photoUrls` rehydrated to `[]`, which made the Re-Run button `disabled` via `photoUrls.length === 0`. Disabled buttons don't fire onClick, so `runMeasure`'s `toast.error("Add at least one photo")` never fired — the user saw the button greyed with no explanation.
  - **Fix 1** — `routes/ai_measure.py`: fresh file-uploads now get a `ai_<uuid>.jpg` name and are written to `/api/uploads/` before the worker starts; the run doc's `photo_paths` field captures all names (path-passthrough + fresh files). Future runs are always recoverable.
  - **Fix 2** — `AIMeasureButton.jsx` autosave guard: skip the session PUT when `photoUrls` is empty but `preview` exists (mismatched state that would poison the session).
  - **Fix 3** — `AIMeasureButton.jsx` `resumeSession` fallback: if the session's `photo_urls` is empty but `preview` exists, fetch `/measure/ai-measure/history?limit=1` and rehydrate `photoUrls` from `run.photo_paths`. Toast confirms recovery.
  - **Fix 4** — `AIMeasureButton.jsx` inline amber banner: when `photoUrls.length === 0` and `preview` exists (unrecoverable state pre-fix), a persistent **"Photos Missing"** banner appears above the Preview pane explaining the situation and pointing at the re-upload input. Data-testid `ai-measure-photos-lost-banner`.
  - **Verified end-to-end**: seeded a fresh estimate with a stuck session (photo_urls=[], preview populated), clicked Session Resume, banner rendered correctly, Re-Run button correctly stayed disabled with an EXPLANATION visible. All 87 pytest tests still green.

- **Iter 79j.28** — **Rendering scope closed: true X+Y, opening types, per-material colors** (Feb 2026): the four remaining rendering asks are all wired and verified.
  - **True Y positioning from bbox** (`autoSpace`, `HouseModel3D.jsx`): `worldY = wallHeight × (1 − photoY)` where `photoY = bbox.y + bbox.h/2`. Doors bbox'd near the floor land at Y≈0; upper-story windows land at their true height. Missing-bbox fallback: doors at 0, windows at 3.2ft. Same treatment applied to dormer-face openings.
  - **Distinct opening type meshes** (`buildOpeningMesh`): type-aware factory returns a THREE.Group. Order-of-precedence matters (garage → patio/slider → entry/door → window):
    - `window` — frame + single glass pane (existing)
    - `entry_door` / `door` — solid slab (no glass) + subtle knob accent, in a distinct dark accent color
    - `patio_door` / `slider` — two glass panes side-by-side in one frame
    - `garage_door` — wide/tall solid slab with a horizontal top band; no glass
  - **Per-material colors** — 4-way pipeline:
    - Backend prompt (`ai_measure.py`): Claude now returns `dominant_colors: {siding_hex, trim_hex, roof_hex, door_hex}`, sampled as flat averages ignoring shadow/glare. `_valid_hex` gate in `_build_measurements` filters garbage before surfacing `_ai_siding_color_hex` / `_ai_trim_color_hex` / `_ai_roof_color_hex` / `_ai_door_color_hex`.
    - Estimate palette override: `JobInfoPanel` now passes `estimate={est}` → `AIMeasureButton` → `HouseModel3D`. A hardcoded `ALSIDE_COLOR_HEX` map bridges Howard's ~20 most-common Alside palette names → 6-digit hex (Autumn Red → #7C2E24, Cape Cod Grey → #8F8B83, etc.). Estimate override wins over AI-sampled hex; both win over default grey.
    - `parseHex` helper safely converts `"#RRGGBB"` / `"RRGGBB"` / numeric literals to a THREE color number; invalid inputs return null so the caller falls back cleanly.
  - **GPU memory hygiene** (`HouseModel3D` scene-wipe effect): prior `scene.remove(child)` didn't dispose GPU buffers → ~2 MB leaked per roof-type dropdown click. Now walks each removed object with a `traverse`+`geometry.dispose()`+`material.dispose()` sweep before removing.
  - **Testing agent verified live** (iteration_32.json, 95% pass, zero blocking bugs): all UI flows work — roof-type dropdown, dormer width row, facade tabs, per-wall inputs, materials pane, Preview↔3D toggle, no sanity errors across gable/hip/dormer switches. Fixture EST-675749 pre-dates the type + bbox + colors prompt, so visual verification of items (2) and (4) with real data awaits a fresh AI run. Code review confirmed the pipelines are correctly wired.
  - **Pytest coverage** — 15 new tests across 2 files, all pass:
    - `test_roof_type_material_math.py` (8): red-house dormer acceptance, hip triangle-zeroing, low-conf skips, exactly-0.8 boundary, bogus types, no-openings inflate, gable pass-through.
    - `test_ai_color_hex_guard.py` (7): valid/invalid/short/uppercase/non-string/bad-char/whitespace-trim cases.
  - **Rendering work is DONE per the user's four-item scope**. Explicitly out of scope: photo textures, siding course lines, trim profile detail, further placement precision beyond bbox. Next up: back to the P1 verification backlog.

- **Iter 79j.27** — **Dormer opening classification + inferred width** (Feb 2026): pushed the dormer geometry from symbolic to photo-accurate.
  - **Backend prompt** (`ai_measure.py`): each opening now carries `on_dormer: boolean`. Claude sets true when the opening sits ABOVE the main eave line (shed-dormer face, gable-triangle, or upper cross-gable). When roof_type ≠ gable-shed-dormer the field is ignored.
  - **Backend material math** — extracted to `apply_roof_type_material_math(raw, walls, gable_sqft, dormer_sqft)` at module scope so it's directly unit-testable. For gable-shed-dormer at ≥0.8 confidence, the target facade's `dormer_face_sqft` is now inflated by `(face + cheeks − Σ on_dormer_opening_area)` instead of the full `face + cheeks`. Openings stay in `raw.openings[]` so total count + J-channel + trim perimeter are unchanged.
  - **Frontend `buildHouseJson`** (`HouseModel3D.jsx`): splits openings on `on_dormer`. Main-wall openings drive the regular wall renders; on-dormer openings drive both (a) dormer width + offsetX derivation, and (b) the dormer face windows. True per-opening X-positioning added via bbox center — when `bbox.x` + `bbox.w` are present the window is placed at that fraction of the wall width (schematic, not survey-accurate — matches the user's "don't polish placement" ask).
  - **Dormer width derivation**: `max(6ft, span + 3ft)` where `span = max(right_edge) − min(left_edge)` across all on-dormer openings, and `offsetX = midpoint − wall_center`. Marked as source `"ai-inferred"` with an amber "estimated" badge (data-testid `ai-measure-3d-dormer-width-inferred`), tooltip: "Inferred from N on-dormer window(s) + 1.5' margin". User override → purple "edited" badge; no on-dormer openings → falls through to Claude's direct `dormer.width_ft` (green "ai" badge if provided) or a default (amber).
  - **Removed** the stock 3'×5' placeholder window from `buildShedDormer`. Face renders blank when no `on_dormer` openings — a valid state.
  - **Acceptance check (red-house test)** locked in as pytest unit tests: `/app/backend/tests/test_roof_type_material_math.py` — 8 tests, all PASS. Given 4 main + 2 dormer windows, front wall's `dormer_face_sqft` = **57.5 ft²** exactly (face 50 + cheeks 25 − 2 windows 17.5), total openings preserved at 6, and dormer classification is filterable on the frontend so the main wall's display count drops by 2 while the total is unchanged. Also covers: hip zeros gable_triangles, low-conf skips math, exactly-0.8 boundary applies, bogus roof types ignored, no-on-dormer-openings case still inflates by full face+cheeks.
  - **Verified live** on fixture EST-675749: switching to gable-shed-dormer now shows a new **Dormer W (ft)** input row + blank dormer face (no phantom placeholder). Editing width flips to "edited". Existing 79 unit tests still pass.

- **Iter 79j.26** — **Three roof types (gable / hip / gable-shed-dormer)** (Feb 2026): extended the 3D viewer + backend classification + material math to support the 3 most common residential roof geometries.
  - **Frontend geometry** (`HouseModel3D.jsx`): new `ROOF_TYPES` const drives a dropdown next to the pitch control. Wall-polygon shape is now type-aware — hip roofs get no gable-triangle peaks on the end walls (all 4 walls are pure rectangles at eave), gable-shed-dormer keeps the gable peaks and adds separate dormer meshes. `buildScene` routes on `roof.type`:
    - `buildGableRoofPlanes` — existing 2-plane gable, unchanged
    - `buildHipRoof` — 4 planes (2 trapezoids on the long axis, 2 triangles on the short ends) meeting at a shortened ridge whose length = `|width − depth|`. Ridge runs along the LONGER axis; short-axis case handled by swapping X/Z. Uses `BufferGeometry` with a fan-triangulated positions array so trapezoids render as single meshes.
    - `buildShedDormer` — vertical face wall (rectangle w/ a placeholder 3'×5' window), two triangular cheek walls filling the wedge on each side, and a low-slope shed roof plane from the face top back to the main ridge. Dormer is positioned at Z = 50% of halfD on the chosen slope (front or rear).
  - **Backend classification** (`ai_measure.py`): Claude JSON schema extended with `roof_type` ∈ {gable, hip, gable-shed-dormer}, `roof_type_confidence` (0–1), `roof_type_reasoning`, and optional `dormer: {face, width_ft, knee_wall_height_ft, offset_x_ft}`. Classification cues embedded in the prompt: gable ends visible → gable; slopes down on all 4 sides → hip; vertical wall with windows above the eave → shed dormer. `_build_measurements` surfaces these as `_ai_roof_type`, `_ai_roof_type_confidence`, `_ai_roof_type_reasoning`, `_ai_dormer`.
  - **Material math** (`_build_measurements` post-processing): when Claude's roof-type confidence ≥ 0.8, the walls array is rewritten BEFORE `breakdown_walls_by_profile` runs:
    - `hip` → every wall's `gable_triangle_height_ft` forced to 0 (kills the phantom gable-triangle area a gable-biased earlier prompt may have added); `_ai_gable_sqft` also zeroed on the summary tile.
    - `gable-shed-dormer` → dormer's face area (`width × knee`) + 2 cheek triangles (`0.5 × knee × knee` each) get added to the target facade's `dormer_face_sqft`, which already flows into the estimator's siding takeoff via `_per_elevation_breakdown[].dormer_sqft`.
  - **Confidence threshold**: 0.8. Above → apply, tag "AI-classified" (green). Below → default to gable + tag "estimated" (amber), tooltip surfaces Claude's low-confidence raw guess so the contractor can override. User override → "edited" (purple).
  - **Sanity checks extended** (frontend, dev-only `console.error`):
    - all types: `ridgeY > maxEave`
    - hip: `ridgeLength ≥ 0` (i.e. `|W − D| ≥ 0` — always true, guards degenerate configs)
    - gable-shed-dormer: dormer face top Y must sit strictly below the main ridge Y (else the dormer would poke through)
  - **Verified live** on fixture EST-675749: all 3 types render correctly on a real-world 8-photo AI run. Default = gable (amber estimated since fixture predates classification prompt). User override to Hip → 4-slope pyramid, rectangular end walls (no triangle peaks), short ridge visible. Override to gable-shed-dormer → gable ridge preserved + vertical dormer face wall poking through the front slope with cheek walls + shed roof back to the ridge. No sanity-check errors in console across all 3 types.

- **Iter 79j.25** — **Roof flipped upright + geometry sanity check** (Feb 2026): the 3D roof was rendering as a V-valley instead of a Λ-ridge because the two roof-plane rotations were swapped. `PlaneGeometry` starts in the XY plane with its top edge at +Y; positive `rotation.x` sends +Y toward +Z. The south plane (positioned at +Z, the front side) needs its top edge to move TOWARD the ridge at Z=0 — i.e. toward -Z relative to its center — which requires a NEGATIVE `rotation.x`. The north plane at -Z needs the opposite. Old code had `north: -(π/2-angle), south: +(π/2-angle)` — swapped. Fixed to `dir = side === "north" ? 1 : -1; plane.rotation.x = dir × (π/2 - angle)`. Added a post-build sanity check that logs `console.error("[HouseModel3D] roof geometry sanity check FAILED — ridge is not above eave", { ridgeY, maxEave, ... })` if `ridgeY = avgGableEave + roofRise` ≤ any wall's eave — a defensive guard against future pitch/depth regressions. Verified live: fixture EST-675749 now renders proper Λ roof with gable-end triangles flush against the ridge planes; ridgeY = 10 + 8 = 18 ft > maxEave 10 ft, no sanity-check errors in console.

- **Iter 79j.24** — **AI-derived per-wall eave heights** (Feb 2026): stopped forcing all 4 walls to the whole-house average `_ai_avg_wall_height_ft`. `HouseModel3D.buildHouseJson()` now resolves each facade's eave independently: user override > `raw_ai.walls[].height_ft` (per-elevation, from the vision prompt) > `_ai_avg_wall_height_ft` (fallback) > 10ft default. Overrides moved from `overrides.eaveHeight` scalar → `overrides.eaveHeights: { front, back, left, right }` object. Scene rendering (`buildScene`) uses each wall's own `f.eaveHeight` in the wall polygon shape; roof ridge pinned to the average of the two gable-end eaves + rise so the roof stays a clean planar gable even on split-levels. Camera position + orbit target now driven by `house.avgEaveHeight` instead of the retired scalar. Four mutually-exclusive badges per wall: 🟢 **AI per-wall** (Claude returned per-wall height_ft), 🟠 **AI avg** (fell back to whole-house average — verify), 🟠 **estimated** (10ft default), 🟣 **edited** (user override). Verified live on fixture EST-675749 — a real split-level ranch: front 10ft, right 7ft, back 9ft, left 9ft, all with green "AI per-wall" badge; Claude's notes independently corroborate ("ground slopes so eave heights vary front 10ft to right 7ft"). Editing front eave to 14 kept right at 7 (independent per-facade state).

- **Iter 79j.23** — **AI-derived roof pitch** (Feb 2026): stopped defaulting the 3D house pitch to a static 6/12 with amber "estimated" badge. `deriveRoofPitchFromWalls(walls)` in `HouseModel3D.jsx` now computes `pitch = (gable_triangle_height_ft × 24) / wall_width_ft` for every gable-end wall Claude flagged, averages the raw values, and snaps to the nearest allowed pitch (4/6/8/10/12). Falls back to 6/12 with amber badge only when Claude found no gables. New `roof.pitchSource` field ("user" | "ai" | "default") drives 3 mutually-exclusive badges: **amber "estimated"** (fallback), **green "AI-derived"** with tooltip showing the raw un-snapped value + gable sample count (e.g. "raw 6.7/12 across 2 gable-end walls, snapped to 6/12"), or **purple "edited"** (user override — hint to hit Re-run so the estimator sees the new pitch). Verified live on fixture EST-675749: Claude found 2 gable ends with ~8ft rise on 27ft walls → raw 7.11 → averaged 6.7 → snapped to 6/12 with green "AI-derived" badge; overriding to 12 flips the badge to purple "edited". Zero amber pitch badges remain on gable-roofed houses (~80% of Howard's jobs).

- **Iter 78z++++** — **P3 Security Hardening (SEC-004 / SEC-005 / SEC-006 / SEC-007)** (Feb 2026): completed the remaining security-audit recommendations on top of the SEC-001/002/003 work shipped earlier in the previous session.
  - **SEC-004** — `config.py` now raises `RuntimeError` at import time if `JWT_SECRET` is shorter than 32 chars or `ADMIN_PASSWORD` is empty. No more `change-me-…` random fallback (which silently invalidated all sessions on every restart) and no more `[REDACTED — backend/.env ADMIN_PASSWORD]` default.
  - **SEC-005** — Added a single-process in-memory rate-limiter on `POST /api/auth/login`: 5 failed attempts per IP within a 15-min window → `429 Too many failed login attempts`. Successful login clears the bucket so a legit user is never locked out by an earlier typo. Trusts `X-Forwarded-For` so the kubernetes ingress chain is honored. JWT lifetime + cookie max-age now driven by `JWT_TTL_SECONDS` (default 7 days — kept the original for contractor convenience per user feedback Feb 2026; ops can dial down per-deploy via env).
  - **SEC-006** — `check_admin_token` no longer accepts `?token=…` in the URL — header-only (`X-Admin-Token`). Tokens in URLs leak via browser history, referrer headers, and server access logs. Migrated every frontend admin call (BrandingAdmin, PricingUpdatePanel, MezzoPricingPanel, VeroPricingPanel, ISSPricingPanel) to send the header. The CSV export download was previously a `window.location.href = …?token=…` assignment — replaced with a `fetch → Blob → synthetic <a download>` pattern so the header still rides.
  - **SEC-007** — Dropped the `"anon"` allowlist in AI-run ownership checks (`/measure/ai-measure/*` and `/measure/ai-blueprint/*`). Authenticated users now strictly own their runs; runs with `user_id="anon"` are no longer reachable. Removed every `user.get("id") or "anon"` insertion point so future runs are always tagged to the real authenticated user.
  - **Tests** — Added `/app/backend/tests/test_security_p3_hardening.py` (10 tests) covering each fix end-to-end against the live preview URL. Migrated 23 legacy admin tests (`test_mezzo_pricing`, `test_vero_pricing`, `test_vero_iter_b`, `test_invite_contractor`) from `?token=…` to `headers=ADMIN_HEADERS`. Updated 3 AI-run tests that seeded with `user_id="anon"` to use the authenticated admin's real user_id (`test_cross_check_http`, `test_ai_measure_rerun_http`, `test_blueprint_rerun_http`).
  - **End-to-end verification**: 53/53 security regression tests pass; live login + admin header flow confirmed via curl and BrandingAdmin screenshot.


- **Iter 42g** — **Install + Trim showing $0 on Vero / Mezzo tabs — FIXED (two bugs)** (Feb 2026): user reported the Install + Trim tile on the Vero tab snapshot was stuck at $0 while Mezzo "seemed to work". Two root causes traced and fixed:
  - **Bug 1 (VeroJobSnapshot.jsx)**: the filter was `(l.tab || "vinyl") === "vero"` but in this codebase the Vero tab id is literally `"windows"` (per `tabsConfig.js` — windows-kind has tab ids `windows` + `mezzo`). Fixed: filter on `=== "windows"`.
  - **Bug 2 (useEstimate.js TAB_IDS)**: `TAB_IDS` only listed `["vinyl", "ascend", "lp_smart"]` — so `inferTab(savedLine)` rejected windows/mezzo tab values on load and rebadged them via `legacyTabForSection()` to "vinyl". The catalog-merge `lineKey` lookup then never matched the saved install lines → their qty dropped to 0 → next autosave wiped them from the DB. Fixed by expanding `TAB_IDS = ["vinyl", "ascend", "lp_smart", "windows", "mezzo"]`. The same constant gates the `backfillMisc()` misc-row tab preservation, so misc labor/material rows on windows-kind estimates now round-trip correctly too.
- **Verified end-to-end** on EST-699636 (29 windows): after restoring the wiped install lines (8 entries × tabs windows+mezzo) and reloading, both snapshot tiles render `$5,785.00 · 4 lines · labor` ($170 × 29 Pocket + $20 × 29 Cap + $150 Job Measure + $125 Disposal); top StickyBar correctly shows Vero $34,950 / Mezzo $21,216.
- Note: during diagnostic curl PUTs I temporarily wiped the test estimate's openings — restored 29 Vero + 29 Mezzo openings via the cached HOVER result before finishing.

- **Iter 42f** — **Auto-add `clean up/ haul away job debris` on siding HOVER uploads** (Feb 2026): per user direction, skipped a measure fee on the siding side (windows-only) but added an auto-fire mapping for the disposal equivalent. New entry in `HOVER_MAPPING_SPEC`: targets vinyl + ascend + lp_smart tabs, fires qty 1 of "clean up/ haul away job debris" in the shared "Tear-Off / Clean Up" section when HOVER reports `siding_sqft > 0`. Section already spans all 3 siding lines (per `catalog_seed.py:989`), so one mapping covers whichever option the contractor quotes. Verified behavior across 3 scenarios (siding-only, windows-only, mixed): correct lines emit on each, no spurious fires.

- **Iter 42e** — **Auto-add Job Measure + Disposal Fees on every HOVER windows upload** (Feb 2026): Howard's standard fees were getting missed because the HOVER importer only added window-count-driven labor rows. Added two new mappings to `HOVER_MAPPING_SPEC` in `/app/backend/routes/hover.py`: "Job Measure Standard Fee 4 days+" (JOB unit, qty 1) and "Disposal Fee (Windows)" (JOB unit, qty 1) — both target the `windows` tab and fire when the PDF has any `window_count > 0` OR `patio_door_count > 0`. Both rows live in the existing "Window Installation" section so they show up under the shared windows-tab catalog (Mezzo + Vero share the same labor/fee rows). Verified end-to-end on the test HOVER PDF: 5 windows-tab lines now emit including the two fees at qty=1 each.

- **Iter 42d** — **Stale Vero/Mezzo opening snapshots → $0 grand total — FIXED + saved "windows missing X" filter pill backlog item** (Feb 2026): contractor reported Vero shows row prices but `$0` in the StickyBar/JobSnapshot for HOVER-imported windows. Root cause: `_build_window_openings()` creates openings with `base_mat: 0` (no client-side catalog lookup at import time) and the panel-level recompute only fires when the user EDITS a row — so the persisted snapshot stays at 0 until something touches it. `calc.js` reads the persisted snapshot for totals, hence the visible mismatch. Fix: new shared hook `useReconcileWindowSnapshots(est, update)` mounted in `EstimateEditor.jsx` that runs ONCE per estimate id — fetches both Mezzo and Vero catalogs in parallel when openings exist, computes the fresh snapshot for each opening (base / glass / tempered / premium / adders), and pushes a single `update()` patch back when any value differs. Crucial: Mezzo buckets use `min_ui`/`max_ui` while Vero uses `min`/`max` — separate `findBucketVero` / `findBucketMezzo` helpers. Verified on the dan buckly EST-964796 estimate (29 windows): Vero $1,785.19 → $26,685.80; Mezzo $0.00 → $12,952.37. Per-row UI prices were never wrong — only the persisted snapshot was, and now both match. Also saved the "filter pill: show only windows missing X" idea to ROADMAP as a P2 follow-up.

- **Iter 42c** — **"N of M" usage badge on mixed-state upgrade options** (Feb 2026): on both Mezzo and Vero opening editors, each upgrade option now shows a small amber-yellow badge (`28/29`) next to its name WHEN the option is in mixed use across the estimate's windows. The badge auto-hides on uniform usage (0 or all openings) so the editor stays clean. Wired into: Mezzo adders (9 options per opening), Vero glass-package selection, Vero tempered selection, Vero premium-options multi-select. Counts are computed once per render at the parent panel (linear pass over `est.mezzo_openings` / `est.vero_openings`) and threaded into the opening row components — no extra API calls. Badge has a hover tooltip "Applied on N of M windows" plus `data-testid={brand}-adder-usage-{name}` for QA. Verified end-to-end on a 29-opening estimate: turning OFF ClimaTech Plus on W-101 surfaces a yellow `28/29` badge on every other opening's ClimaTech row AND on W-101's now-unchecked row — the contractor sees the odd-one-out at a glance.

- **Iter 42b** — **Mezzo adder label hidden under qty input — Fixed** (Feb 2026): on a checked Mezzo adder, the per-opening qty input was rendering with `className="input num h-7 text-xs w-12 ..."` — the global `.input` CSS class (`@apply w-full`) outranks the Tailwind `w-12` utility because the rule `input[type="number"].input` has higher specificity than a plain `.w-12` class. Result: the qty input stretched to 100% width and visually covered the adjacent adder name (e.g. "ClimaTech Plus - 9E"). Fix: replaced the `.input` class on this specific small input with raw Tailwind utilities (`bg-white border border-[#E4E4E7] focus:border-[#F97316] outline-none h-7 text-xs w-12 px-1.5 text-right flex-shrink-0 font-mono-num`). Now the qty input stays at 48px wide and the adder label "ClimaTech Plus - 9E" renders correctly with its "+$31.98 total" subtitle. Verified end-to-end on a 29-opening estimate.

- **Iter 42** — **Bulk-apply upgrade options across uploaded windows** (Feb 2026): when a contractor toggles an upgrade option on a single window opening in Mezzo or Vero, a confirm modal asks "Apply to all uploaded windows?" — yes propagates the same selection to every other opening on the same brand tab whose product type supports the option; no leaves only the single edit. New shared component `BulkApplyConfirm.jsx` (kebab-case testids per-panel: `vero-bulk-apply-confirm` / `mezzo-bulk-apply-confirm`). Wired into: Vero glass package, Vero tempered upcharge, Vero premium options (multi-select), Mezzo adders (incl. ClimaTech Plus / TG2 mutual-exclusion preserved). Mezzo adders are resolved per-opening so the propagator looks up the OTHER opening's catalog adderDef to get the right sqft × W×H mat — not just copying the source mat. Modal only fires when `otherCount ≥ 1` (no point with one window). Verified end-to-end: toggling ClimaTech Plus on W-101 of a 29-opening estimate → modal "APPLY TO ALL WINDOWS? Apply 'ClimaTech Plus - 9E' to the other 28 uploaded windows too?" with "Just this one" / "Apply to all 28" → click Apply → Mezzo total jumps from $104.84 to $1,481.88 confirming all 29 openings got the adder. Bilingual (EN + ES translations).

- **Iter 41b** — **HOVER also populates Mezzo tab on paired windows estimate** (Feb 2026): the previous iter populated Vero only, leaving the Mezzo tab empty even though both brands sit side-by-side on the Windows workspace. Now `_build_window_openings()` emits BOTH `vero_openings` AND `mezzo_openings` with paired UUIDs + matching dimensions; the Mezzo product type is derived from the Vero guess via `_vero_to_mezzo_product_type()` (Mezzo has no Casement, so Vero Casement guesses fall back to Mezzo Double Hung). FE: single editable style row in the preview drives both brands; on apply we route `vero_openings` AND `mezzo_openings` to whichever side (current vs paired estimate) is the windows-kind. New `HoverMezzoOpening` Pydantic model + `mezzo_openings: list[HoverMezzoOpening]` field on `HoverImportResult`. Verified: 29 Mezzo openings + 29 Vero openings persist with paired IDs; the Mezzo tab UI now renders all 29 rows with HOVER IDs (W-101 through W-329) and resolved UI buckets ($281–$320/window). 27/27 backend tests still green.

- **Iter 41** — **Cross-kind estimate pairing on HOVER upload** (Feb 2026): when a contractor uploads HOVER on a siding estimate that contains window measurements (or vice versa), the importer automatically spawns a paired estimate of the opposite kind. New `POST /api/estimates/{id}/pair` endpoint (idempotent, falls through to re-create if the paired pointer was deleted). EST# scheme: siding `EST-555888` → paired `EST-555888-W`; windows `EST-555888-W` → strip suffix; windows `EST-555888` (no suffix) → `-S` suffix. One-time copy of customer_name, address, estimator on creation. `Estimate.paired_estimate_id` field stores cross-pointer both ways. Dashboard list endpoint joins `paired_estimate_number` + `paired_estimate_kind` on each row in a single batched lookup. Frontend HOVER apply now splits incoming lines by tab into source-kind vs paired-kind slices and routes vero_openings to the paired side; the apply toast surfaces the paired EST#. Dashboard renders a chain-link icon (`<Link2/>`) next to the EST# when `paired_estimate_id` is truthy; click navigates to the paired estimate. Verified end-to-end: 100% PASS on 18/18 acceptance criteria (testing agent iter_15).

- **Iter 40** — **HOVER smart window-style guess + per-opening preview** (Feb 2026): contractor uploads a HOVER PDF, the importer now extracts EVERY individual window (not just `window_count`) and runs `_guess_vero_product_type(w, h)` per opening to pick a default Vero product type (Double Hung / 2-Lite Slider / 3-Lite Slider / 1-Lite Casement / Picture). HOVER reports don't include window operating style — only dimensions — so the rules are conservative, biased toward DH (Howard's stock answer ≈ 99% of replacement openings): Casement if w ≤ 28 AND h ≤ 36; Picture if w ≥ 48 AND h ≥ 48 AND |w-h|/max(w,h) < 0.20; 3-Lite Slider if w ≥ 60 AND w > h; 2-Lite Slider if w ≥ 40 AND w > h; else DH. Backend changes: prompt extends to ask Claude for `windows: [{id, width_in, height_in}]`; new `_build_vero_openings()` builds Vero opening shells with a fresh UUID + the guessed product_type; `HoverImportResult` gains a top-level `vero_openings: list[HoverVeroOpening]`. Frontend: new "Vero Window Openings — Style Guess" section in the HOVER preview modal — table of HOVER ID · W · H · UI · editable style dropdown (5 options) · remove. Apply appends to `est.vero_openings`; VeroPanel resolves bucket_label + base_mat from the live catalog on next render. Verified end-to-end on a real 30-page HOVER PDF (29 windows extracted, all 29 classified as DH because all openings are classic DH proportions). Tests: 21/21 new pytest assertions for the guesser; testing agent verified 12/12 acceptance criteria in the UI (modal opens, 29 rows render, edit/remove work, Apply persists 28 openings to the estimate).
  - **One bug found + fixed during testing**: the new `windows[]` payload was initially nested inside `result.measurements` — the Extracted Measurements iterator crashed React with "Objects are not valid as a React child". Resolution: hoisted `windows` to the top of the result (pop'd out of `measurements` before send) so the FE measurements grid only ever sees primitives. FE also kept a defensive `typeof v !== "object"` filter as belt-and-suspenders.
  - **Catalog cleanup**: removed two obsolete HOVER mappings that pointed at sections deleted in Iter 36 (`Vero Windows` → `Vero - Double Hung 0-101 UI`, `Vero Sliding Glass Doors` → quote line). The remaining "Window Installation" labor row + cap row + sliding-door install were left in place with corrected item names.

- **Iter 39** — **Spanish translation polish for TotalsSummary + TabPickerModal** (Feb 2026): tightened remaining EN strings that weren't translating on Spanish-locale UI. (1) `TotalsSummary` badge "Vinyl option" → translated via new `est.tabOption` + `tabLabel.*` keys ("opción Ventanas" / "opción Vinil"); now reflects the active tab (vinyl/ascend/lpSmart/windows/mezzo). (2) `TotalsSummary` "Material List" button → `est.materialList` ("Lista de materiales"). (3) `TabPickerModal` fully translated — title ("Imprimir Cotización al Cliente" / "Imprimir Lista de Materiales"), helper text, Cancel/Continue buttons, and per-tab labels via new `tabPicker.*` namespace. (4) `StickyBar` TabBlock "Base" label parameterized via `est.bar.base`. Verified end-to-end on a Vero windows estimate at `ui-lang-v1=es`: section headers (Vero Doble Colgante, Vero Corrediza 2 Hojas, etc.), summary badge ("OPCIÓN VENTANAS"), and Material List button render in Spanish. Mezzo product block headers (Mezzo Doble Colgante, etc.) were already wrapped via `tSection(pt.name, lang)` — verified working.

- **Iter 1** — MVP build, 17/17 backend tests
- **Iter 2** — Frontend E2E hardening, 16/16 scenarios
- **Iter 3** — Multi-tenant companies, ad-hoc misc lines, CSV exports, Resend live, EstimateEditor refactor, 21/21 tests
- **Iter 4** — Per-company uploadable logo via Team page
- **Iter 5** — **Supplier-distributed pivot**: public branding endpoint, signup-code gating, Alside Pittsburgh dealer prices seeded, /branding-admin route, quote footer toggle, 45/45 tests pass
- **Iter 6** — **4-Tier Material Pricing Architecture** (Feb 2026): 4 supplier-controlled tiers seeded (`one-opp`, `whole-sale`, `Contractor`, `Builder-Dealer`). Material prices locked at backend (PUT /api/catalog strips `mat`) AND at UI (Catalog inputs disabled, EstimateEditor renders mat as static text). Labor remains contractor-editable with orange override + reset. Admin can assign tier per-company via /branding-admin → PUT /api/admin/companies/{id}/tier. 23/23 new pytest tests pass; Playwright validated Catalog tier badge + locked material + BrandingAdmin tier dropdown.
- **Iter 7** — **Margin / Markup toggle on every estimate** + **supplier-wide default in /branding-admin** (Feb 2026): contractors pick Margin/Markup per estimate via a toggle in the Profit settings card. Alside can lock a default mode in `/branding-admin` → `Default Pricing Mode` card; new estimates pick up that default if the client doesn't pass one. Backend: `EstimateIn.pricing_mode: Optional[str]`, POST `/estimates` falls back to `branding.default_pricing_mode`, PUT uses `exclude_none` so omitting the field preserves the existing value. New `default_pricing_mode` field on `GET /api/branding` (public) + `PUT /api/admin/branding` (token, validates margin/markup). Legacy estimates backfilled to `markup` on startup so historic sell prices are preserved. CSV exports include both the mode and percent. Math verified: $1500 @ 30% → $2142.86 margin, $1950 markup. Full pytest suite: **67 passed, 1 skipped** (the skipped test exercises defunct per-company material overrides — material is tier-controlled now).
- **Iter 8** — **Customer email polish · Phase 1** (Feb 2026): replaced the "raw DOM HTML" email body with a brand-new email-safe template at `/app/frontend/src/lib/emailQuote.js`. All styles are inlined, layout is table-based (Gmail/Outlook/Apple Mail compatible — no Tailwind classes survive in email clients). New features: (1) editable Personal Note textarea in QuoteModal pre-filled with a friendly greeting using the customer's first name + estimator's name; (2) personalized subject `"Your siding estimate {EST#} from {Contractor} — {Customer}"` using the contractor's actual company name (not hardcoded "Wolf and Son"); (3) inline estimator signature block; (4) clean reply CTA footer + supplier attribution. Backend fallback subject also fixed to use `company.name` from DB instead of the hardcoded string. Verified end-to-end: HTML renders cleanly in browser preview, contains 0 Tailwind classes, all inline styles validate, currency/dates/notes all escape correctly. 67/67 pytest still green.
- **Iter 9** — **Customer email polish · Phase 2: Trust & conversion** (Feb 2026): (1) `reply_to` header now set server-side to the company **owner**'s email (fallback to the authed user) so customer replies always land in the contractor's inbox instead of `onboarding@resend.dev`. (2) Prominent **"VALID THROUGH MMM DD, YYYY"** orange badge in the email header, computed as estimate_date + 30 days; the expiration date is repeated under the Total. (3) Big orange **"Accept this Estimate →" mailto CTA** in the email with a pre-filled subject (`"Accepting estimate EST-XXX — Customer"`) and body (mentions the total price), making it one-click for customers to send the contractor an acceptance. All three changes preserve 100% inline-style / no-class email-client compatibility. 67/67 pytest still green.
- **Iter 10** — **Backend refactor** (Feb 2026): broke the 957-line `server.py` into 14 small modules under `/app/backend/`: `server.py` (slim entry, 36 lines) + `config.py` + `db.py` + `models.py` + `deps.py` + `services.py` + `startup.py` + `routes/{branding,auth,company,catalog,estimates,uploads,email}.py`. Largest file is now `routes/estimates.py` at 166 lines. Zero behavior changes — 67/67 pytest still pass, 8/8 smoke curl tests still pass, lint clean. Future agents can navigate the codebase by domain instead of scrolling 900 lines.
- **Iter 11** — **Code-review noise prevention** (Feb 2026): pinned explicit linter configs so future automated reviews don't surface false positives. New files: `/app/frontend/eslint.config.js` (ESLint v9 flat config — focuses on real-bug rules: `react-hooks/*`, `no-unused-vars`, `no-undef`, `no-dupe-keys`; disables prop-types/escaped-entities noise), `/app/backend/pyproject.toml` (`[tool.ruff]` config — selects `E, W, F` only; ignores complexity, PEP604 modernization, `is None` E711/E712 misfires, security `S` rules), and `/app/CODE_QUALITY.md` (explains the philosophy + lists what reviewers should NOT flag: complexity, missing type hints, hardcoded test creds, `is None` patterns). Also fixed 3 legitimate items from a code-review report: test creds moved to env vars (with module-level `pytest.skip` if absent), `useMemo` on `auth.jsx` and `company.jsx` Context Provider values (real React perf concern), and 2 `console.warn` calls wrapped in `process.env.NODE_ENV !== "production"`. Final state: ESLint **0 errors**, ruff **All checks passed**, **67/67 pytest pass**.
- **Iter 12** — **Delete-Contractor + cleanup** (Feb 2026): new `DELETE /api/admin/companies/{id}` cascades to remove the company + its users + estimates + catalog overrides. Frontend `/branding-admin` got a trash button on each row with type-to-confirm prompt. Wiped 71 leftover test companies — only Howard's Estimating Tool remains.
- **Iter 13** — **Email Phase 3 · PDF attachment** (Feb 2026): added WeasyPrint 68.1 + new `/app/backend/pdf.py` (HTML→PDF render + safe filename). Email-send route now generates a PDF from the same email-safe HTML and attaches it to the Resend email (base64 in `attachments` param). Plus a new `POST /api/estimates/{id}/pdf` endpoint for in-app downloads; QuoteModal's "Download PDF" button calls it and saves the file with a friendly name like `EST-252751-Jane_Smith.pdf`. Verified: 14 KB PDF, valid `%PDF` magic, file downloads correctly from the UI. Email customer experience now includes a PDF they can save/print/forward to their spouse. 67/67 pytest pass; lint clean.
- **Iter 14** — **Hosted Accept Page (Option B)** (Feb 2026): replaced the mailto-only Accept CTA with a one-click hosted acceptance flow. Frontend mints a UUID4 `accept_token` per estimate; the email's "Accept this Estimate →" link now points to `https://.../accept/{token}`. New backend routes: `GET /api/public/accept/{token}` (no-auth, customer-safe summary) + `POST /api/public/accept/{token}` (records `accepted_at`, `accepted_ip`, `accepted_note`; flips `status_label` to "accepted"; emails the company owner a "🎉 Jane Smith accepted EST-001" notification via Resend; idempotent on repeat clicks). New public route `/accept/:token` in React Router renders a branded page with the contractor's name, total, an optional "note to the contractor" textarea, an "I accept" checkbox, and a big confirm button — followed by a green ✓ thank-you state. Dashboard now shows a **green "✓ Accepted" badge** on accepted estimates and an **orange "Sent" badge** on emailed ones. Verified end-to-end via curl + Playwright. 67/67 pytest still pass.
- **Iter 15** — **Mobile-friendly Tier A** (Feb 2026): responsive polish for phone use without touching the iPad/laptop layout. Changes all use Tailwind's `md:` (≥768px) breakpoint, so phones (<768px) get the new layout and everything bigger keeps the current view byte-for-byte. (1) **SectionAccordion line items**: items stack on phone with tiny labeled headers ("UNIT", "QTY", "LAB $", "MAT $", "TOTAL") so each input is identifiable; inputs grow to 44 px tall (Apple HIG min touch target); bold item name on its own line; total in a separated bottom row with a divider. (2) **QuoteModal action bar** stacks vertically on phone — full-width Email + Download PDF + Close buttons. (3) **`.btn-ghost` / `.btn-danger`** icon buttons get a `min-width: 44 px; min-height: 44 px;` floor on phone, removed on desktop via `@media (min-width: 768px)`. Verified live: iPhone 390×844 shows the new layout cleanly, 1440×900 desktop is pixel-identical to before. 67/67 pytest still pass; ESLint clean.
- **Iter 16** — **PWA Install Banner** (Feb 2026): new `/app/frontend/src/components/InstallBanner.jsx` mounted inside Layout (so it only shows for authed contractors, never on Login / AcceptPage / BrandingAdmin). Detects iOS vs Android via `navigator.userAgent` + `navigator.maxTouchPoints`. On iPhone, the "Install" button opens a 3-step instruction modal (tap Share → "Add to Home Screen" → Add). On Android/Chrome, captures the native `beforeinstallprompt` event so the button fires a real one-tap install. Detects already-installed apps via `(display-mode: standalone)` so it doesn't show inside the installed PWA. Dismiss is persisted via `localStorage` (`install-banner-dismissed-v1`). Banner is `md:hidden` so desktops never see it. Verified: appears after a 1.2s defer on iPhone, dismiss + reload = stays hidden; desktop 1440px DOM contains no banner element.
- **Iter 17** — **Duplicate Estimate** (Feb 2026): new `POST /api/estimates/{id}/duplicate` clones an estimate keeping lines + labor overrides + notes (scope) + margin/markup + pricing mode + waste % + tax. **Strips** customer_name, address, accept_token, accepted_*, last_sent_at, recipient_email, and assigns a fresh estimate_number + estimate_date so the contractor can't accidentally email a duplicate. New "Copy" icon button on every Dashboard row next to the trash button — click duplicates the estimate, navigates to the new one, shows "Estimate duplicated — customer fields cleared" toast. Verified end-to-end via curl (6 invariants pass) + Playwright (live UI). 67/67 pytest still pass; lint clean.
- **Iter 18** — **Dashboard filter chips + Pipeline stats** (Feb 2026): **Contractor side** — Dashboard gains a 4-card stats row (Drafts / Sent / Accepted / Win Rate) with pending and won dollar totals, plus filter chips below it (All / Draft / Sent / Accepted) with running counts per bucket. Status is derived locally via `statusOf(e)` from the `accepted_at` / `last_sent_at` lifecycle fields. **Supplier side** — new `GET /api/admin/pipeline` (token-gated) aggregates the same stats across ALL contractor companies + returns a per-company breakdown. New `<PipelinePanel>` on `/branding-admin` shows the 5 totals + a "Top contractors by won revenue" table (top 5). This is the supplier's first real analytics surface — Howard can see at a glance which contractors are sending the most quotes, winning the most jobs, and how much Alside material flows through them. Cleanup: also purged 28 leftover test companies + 40 stale user accounts that re-accumulated during this session. 67/67 pytest still pass; lint clean.
- **Iter 19** — **English/Spanish i18n** (Feb 2026): full bilingual support with EN/ES toggle. **Infrastructure**: new `/app/frontend/src/lib/i18n.jsx` (LangProvider + `useT()` hook, localStorage-persisted `ui-lang-v1` key, auto-detect browser preference on first load) + `/app/frontend/src/lib/dictionaries.js` (~150 keys across nav, auth, dashboard, catalog, estimate editor, quote modal, accept page, email/PDF body) + `/app/frontend/src/lib/catalogTranslations.js` (catalog section/item/unit maps — translates ~25 generic service descriptions like "Tear-Off" → "Demolición", "House Wrap" → "Membrana para casa", section titles like "Install Vinyl Siding" → "Instalar Vinil", and unit abbreviations like SQ → MC, LF → PL, PCS → PZA, while leaving brand-name products (Conquest .040, Coventry, Ascend, Charter Oak) untouched). New `LangToggle` pill component (EN/ES) appears in the authed header AND on Login (top-right) AND on the public Accept page. Verified end-to-end: EN/ES toggle works on Login, Dashboard, EstimateEditor, QuoteModal · custom messages preserved · `?lang=es` deep link flips Accept page · 0 page errors. ESLint clean.
- **Iter 29** — **Common Items Yellow Highlighting** (Feb 2026): contractors who don't always remember to add accessories/cleanup line items now get a visual nudge. New `/app/frontend/src/lib/commonItems.js` exports a `Set` of 27 "commonly needed" catalog item names (12 supplier-curated like `Tear-Off`, `Dumpster`, `Caulking`, `Flashing`, plus 15 items the HOVER importer auto-populates — so non-HOVER users get the same prompt). `SectionAccordion` renders a `bg-yellow-50` row background + 💡 lightbulb icon next to any commonly-needed item with `qty <= 0`. Section headers show a small yellow `lightbulb + N` pill counting unfilled common items so contractors see what to review before opening. Both highlights auto-clear once qty > 0. ESLint clean.
- **Iter 28** — **HOVER PDF Importer (P0)** (Feb 2026): contractor uploads a HOVER measurement PDF → AI extracts every measurement → app auto-populates 16+ catalog line items. **Backend**: new `/app/backend/routes/hover.py` exposes `POST /api/estimates/hover-import`. Flow: pdfplumber extracts plain text (~40 KB) from the 30-page PDF → text goes to Claude Sonnet 4.5 via `emergentintegrations.LlmChat` with a strict JSON-output prompt → measurements come back as `{siding_sqft, soffit_sqft, eaves_lf, rakes_lf, starter_lf, outside/inside_corner_count+lf, opening_count, window_count, entry/patio/garage_door_count, stories, address}` → `HOVER_MAPPING_SPEC` runs each row's `extract()` lambda over the measurements to produce a draft `lines[]`. Door classification rules: `SGD-*`/`FD-*` → patio; `OHD-*` or width ≥96" → garage; everything else → entry (so a 72×80 double front door is correctly an entry, not a garage). 16 line items auto-fill: Vinyl Siding (default profile pick), Outside/Inside corners, Starter, Finish Trim, J-Channel, House Wrap, 2" Nails, 1¼" Trim Nails (always qty 1), Soffit & fascia + matching 3/4" Soffit J-Channel, Gutter 6" (eaves only — rakes excluded), Cap window, Cap entry/patio/garage door. **Frontend**: new `<HoverImportButton>` in `JobInfoPanel` (top-right of Job Information) → upload → preview modal shows extracted measurements grid + draft line items table → "Apply N Lines" merges into the current estimate (existing same-name lines get qty updated, new lines appended, nothing else touched). EMERGENT_LLM_KEY added to `backend/.env`. Cost ≈ $0.03/import, ~5s end-to-end. Verified on a real 30-page HOVER report.
- **Iter 27** — **Coil description cleanup** (Feb 2026): the 3 Siding Accessories coil entries (`.019 Coil`, `PVC Trim Coil`, `Performance G8 Trim Coil`) dropped the `(1 per 50' fascia)` suffix from their names. The fascia variants now live separately in Vinyl Soffit with Siding, so the Siding Accessories names just describe their one usage (`(1 per 5 Sq Siding)`). One-time DB migration in `ensure_tiers_seeded()` renames tier docs AND historical estimate line items so no orphans.
- **Iter 26** — **Excel catalog sync — Ascend Trim + fascia coils** (Feb 2026): synced catalog with Howard's updated Alside Excel sheet. Renamed `Ascend - 5.5" H Channel (16' length)` → `Ascend - 5.5" Trim (16' length)`. Added 2 new Ascend items: `ASCEND Finish Trim` (LF, $7.86, AMI 105210) and `Ascend - Starter` (LF, $7.68, AMI 107371). Added 3 new fascia-coil entries to Vinyl Soffit with Siding (`.019`, `PVC Trim`, `Performance G8`, each ROLL with `(1 per 50' fascia)` description and matching AMI numbers 103954/103956/103960). One-time DB rename migration in `ensure_tiers_seeded()` + backfill that seeds correct mat prices from `TIER_PRICES` for any items left at $0 from the auto-section-rebuild.
- **Iter 25** — **Waste factor scope refinement** (Feb 2026): contractor's `waste_pct` setting now only inflates Vinyl Siding section material + the 2 Ascend Composite siding products (`Ascend Composite Lap Siding 7"`, `Ascend Composite B&B 12"`) — trim, accessories, soffit, gutter, capping, tear-off, dumpster, etc. are ordered to actual piece count and no longer get padded. Updated 4 places: backend `services.calc_totals`, frontend `lib/calc.js`, `Dashboard.jsx` pipeline calc, and `materialList.js` (Order Qty column inflates only for waste-eligible rows). Math verified: on a $5,891.62 material job with 15% waste, old behavior added $883.74; new behavior with only $4,539.30 vinyl + $3,326.00 Ascend mat in scope adds $1,179.80 — accurate to within $0.01. Waste Factor card hint reads "Applies to Vinyl Siding + Ascend Composite Lap/B&B only". EN+ES translated.
- **Iter 24** — **"Install Vinyl Siding" → "Vinyl Siding" rename + sections start collapsed** (Feb 2026): renamed the section throughout `catalog_seed.py`, the EN/ES translation map, and `services.py` comments. One-time DB rename migration: updates section title in tier docs AND `section` field in historical estimate line items so no orphans. `EstimateEditor` no longer auto-expands every catalog section on first load — contractors now see a compact list of category headers (with the existing "N ITEMS" pill on sections that already have lines) and expand only what they need. Removed the dead `useEffect` that did the auto-open.
- **Iter 23** — **Sync-to-Latest-Catalog on Draft Estimates** (Feb 2026): closes the loop with Iter 22's bulk pricing tool — when Howard bumps catalog prices, contractors with open drafts get a one-click sync. Detection is purely client-side: `useEstimate.js` already populates `line.defaultMat` / `line.defaultLab` from the *current* catalog while `line.mat` / `line.lab` carry the snapshotted values, so the new `<CatalogSyncBanner>` (`/app/frontend/src/components/estimate/CatalogSyncBanner.jsx`) just diffs them. **Safety guard**: banner only renders when `!last_sent_at && !accepted_at` — we never silently change a quote the customer has already received. UI: subtle orange banner pinned above Job Info with **Dismiss** + **Review & Sync** buttons. Review opens a modal showing every stale line with item · qty · mat (old → new) · lab (old → new), color-coded. "Apply N & Save" PUTs the merged lines directly through `api.put` (avoids stale-closure on `useEstimate.save()`), then patches local state via `update({ lines })`.
- **Iter 22** — **Hybrid Pricing-Update Admin** (Feb 2026): supplier can now bulk-update catalog prices in 3 ways from `/branding-admin`, no more editing `catalog_seed.py`. New backend route `/app/backend/routes/pricing_admin.py` exposes 4 endpoints (token-gated): `POST /api/admin/pricing/preview-bump` (computes a diff for a % change without writing), `POST /api/admin/pricing/upload` (parses CSV or XLSX via openpyxl, returns diff + list of unmatched rows for typos), `POST /api/admin/pricing/apply` (commits a previewed changeset — frontend just POSTs back the same array it got from preview), `GET /api/admin/pricing/export` (downloads current prices as `pricing-YYYY-MM-DD.csv` with columns tier,section,name,unit,mat,lab). New frontend component `/app/frontend/src/components/admin/PricingUpdatePanel.jsx` wires all three workflows: **Quick Bump tab** (% input + Material/Labor/Both selector + tier filter chips), **Upload CSV/Excel tab** (drop a file → backend computes diff), **Export tab** (one-click CSV download). All flows funnel into a shared `<DiffPreview>` modal that shows tier · section · item · field · old (strikethrough) · new (bold) · delta ($ + %) color-coded green/red, with totals at the top ("238 changes · 238 up · 0 down") and a one-click Apply button. Unmatched upload rows surface in a red callout above the diff so typos can be fixed before applying. Verified end-to-end: preview 238 changes ($92.19→$94.49 etc) renders correctly, applied +1% to a single item, verified persistence, reverted the change cleanly. Lint clean (Python + JS).
- **Iter 21** — **Estimate-level Material Colors** (Feb 2026): removed the per-line `color` field on `EstimateLine` and replaced it with 4 estimate-level color fields on the `Estimate` model: `siding_color`, `accessories_color`, `outside_corner_color`, `soffit_fascia_color`. UI: new "Material Colors" block in `JobInfoPanel.jsx` under "Scope of Work / Notes" — 4 labeled inputs in a responsive grid (1 col mobile / 2 col tablet / 4 col desktop) with placeholder "e.g. Storm Gray". EN/ES dictionary updated (`est.colors`, `est.color.siding/accessories/outsideCorner/soffitFascia`, `est.color.placeholder`). Material List PDF (`materialList.js`) now prints a single 4-cell color summary block at the top instead of a per-line color column — matches how contractors actually order (one color per family, not per SKU). Verified end-to-end: PUT persists all 4 fields, line items preserved, WeasyPrint renders cleanly (6.8KB PDF, HTTP 200), UI screenshot confirms all 4 inputs render correctly with values. Lint clean (Python + JS).
- **Iter 20** — **Custom domain + DMARC + Print Material List with AMI #s and color** (Feb 2026): 
  - **Email Phase 4 complete**: bought `pro-quotes.com` on Cloudflare Registrar, added SPF + DKIM (Resend) + DMARC TXT records, verified domain in Resend, flipped `SENDER_EMAIL` to `quotes@pro-quotes.com` in `backend/.env`. Reply-To remains per-quote = sending contractor's owner email. Verified end-to-end: quote sent → arrived in Yahoo inbox (NOT spam) → Accept clicked → notification routed to correct contractor.
  - **Admin login renamed**: `admin@wolfandson.com` → `hhunt6677@yahoo.com` in `.env` + DB (and renamed the seed company from "Wolf and Son" to **Howard's Estimating Tool**). Empty stale "Designs by Charo" test signup and 3 stray `test_*@example.com` regression accounts purged.
  - **Browser tab + PWA manifest** cleaned: `<title>` → "Siding Estimator", manifest description → "Quoting tool for siding contractors". No more contractor name leakage on the login page.
  - **Print Material List feature**: imported AMI part numbers from Alside's `Vinyl Siding price page.xls` (~28 SKUs covering Conquest, Coventry, Odyssey, Charter Oak, vertical B&B, Pelican Bay, all coils, corners, J-channel sizes, fascia/soffit profiles, fan fold, trim nails). New `ITEM_AMI` dict in `catalog_seed.py` + idempotent `ensure_tiers_seeded()` migration that backfills `ami_part` onto already-seeded tier docs on every boot. New `CatalogItem.ami_part` + `EstimateLine.color` + `EstimateLine.ami_part` fields on the Pydantic models. UI: small grey `AMI #015456` badge next to each line name in the estimate editor; **color text input appears inline under any line with qty > 0** (placeholder "e.g. Storm Gray"). New "Material List" button in TotalsSummary opens a server-side WeasyPrint PDF with columns AMI # · Description · Color · Unit · Job Qty · Order Qty (raw qty + waste-factor-applied rounded-up qty for ordering). Reuses existing `/api/estimates/{id}/pdf` endpoint — no new backend route needed. PDF download filename: `EST-XXXXXX-Customer-materials.pdf`. Verified end-to-end: PDF generates correctly, AMI numbers + colors render, section subtotals appear. Sections + items + units translate to Spanish via existing `catalogTranslations.js`. Lint clean.

- **Iter 21** — **HOVER siding qty pulls from "+ Openings < 20ft² +10%"** (Feb 2026):
  - HOVER importer now extracts the value from the **"SIDING WASTE TOTALS → + Openings < 20ft² +10%"** row in HOVER reports (with safe fallback to raw facades area). Applied to both **Vinyl Siding (Charter Oak default)** and **House Wrap** lines. Bakes in HOVER's 10% small-opening adder automatically. Contractor manages Waste Factor (catalog) on top of this manually. Lines/notes updated in `/app/backend/routes/hover.py`.

- **Iter 34** — **Siding Catalog Restructure: Standard vs Architectural color variants** (Feb 2026): synced catalog with Howard's updated Alside Excel sheet that splits every vinyl-siding profile + many accessories into TWO variants — "Standard color" and "Architectural color". Net effect: Vinyl Siding section went from 15 items → 27 items (Conquest x4, Coventry 4"/5" x8, Odyssey 4"/5" x8, Charter Oak x4, vertical b&b x2, Pelican Bay x1). Siding Accessories grew from 5 single-variant rows → 8 color-split rows (Outside corners, Inside Corners (Siding), 3/4" J-Channel, Finish Trim each Std/Arch + the unchanged 1/2" J-Channel white). Vinyl Soffit with Siding got 6 new Charter Oak variants (13" Std/Arch, 13"-30" Std/Arch, 3/4" Soffit J-Channel Std/Arch). The Excel typo "Stanard Color" → normalized to "Standard color" everywhere; the old umbrella "Architectural color upcharge Vinyl" line removed since variants are now explicit per item. Clap and Dutch Lap remain separate items per Howard's request (Excel combines them on one row at one price; we split into 4 SKUs per profile × color).
  - **AMI part numbers** carried forward — color variants share their base SKU AMI #.
  - **Migration**: services.ensure_tiers_seeded auto-rebuilds tier sections on boot. A bounded BACKFILL list force-corrects mat/lab from TIER_PRICES + ITEM_META when a new variant lands at $0 (handles hot-reload races during the catalog edit pass). All 4 tiers (one-opp / Builder-Dealer / Contractor / whole-sale) now carry the correct material price per the spreadsheet.
  - **Historical estimates protected**: old line items (e.g. "Charter Oak Clap 4.5" .046") remain unchanged in the DB — lines snapshot their own mat/lab so saved estimates render correctly even though those names no longer exist in the catalog.
  - **HOVER importer** updated to default to the new "Charter Oak Standard color Dutch Lap 4.5" .046", "Outside corners Standard color", "Inside Corners (Siding) Standard color", "Finish Trim Standard color", '3/4" J-Channel Standard color (...)', 'Soffit & fascia up to 13" wide Charter Oak Standard color', and '3/4" Soffit J-Channel (Charter Oak) Standard color' for auto-fills (contractor can swap to Architectural on the editor row if needed).
  - **Frontend**: commonItems.js + COMMON_ITEM_TAB_SCOPE updated to point at the new Standard color variant names. catalogTranslations.js gained ES translations for every new variant.
  - **Tests**: 17/17 backend pytest assertions in `/app/backend/tests/test_iteration34_siding_split.py` pass (catalog shape, tier prices, AMI numbers, estimate round-trip, hover-import endpoint, legacy estimate load, architectural-upcharge removal).


  - **3 tabs in every estimate** — **Vinyl** | **Ascend** | **LP Smart** — Excel-sheet-style so one quote can carry three parallel siding options for good/better/best comparison.
  - **Backend (tabs)**: Added `product_lines` field per catalog section (`vinyl` / `ascend` / `lp_smart`). Source of truth in `catalog_seed.SECTION_PRODUCT_LINES` + `product_lines_for()`. Vinyl Siding → `["vinyl"]`, Ascend Cladding → `["ascend"]`, LP-only sections → `["lp_smart"]`. Generic shared sections (Tear-Off, Seamless Gutter, Misc. Labor, Misc.) → `["vinyl", "ascend", "lp_smart"]` (all 3 tabs). Other shared sections (Siding Accessories, Vinyl Soffit, Porch Ceiling) → `["vinyl", "ascend"]`. Added `tab: str = "vinyl"` to `EstimateLine` and `MiscLine`. Migration in `services.ensure_tiers_seeded` now also APPENDS new sections to existing tier docs (previously it only rebuilt existing ones).
  - **Backend (LP SmartSide catalog)**: Wired in all items from Howard's "LP Smart siding" tab in `original Vinyl Siding app price layout page.xls`. 4 new LP-only sections — `LP Smart Siding` (6 items: Strand Lap, Strand Shake, Nickel Gap, 3× Strand Panels), `LP SmartSide Trim` (11 items combining 190/440/540 series, disambiguated as "LP 190 Trim …", "LP 440 Trim …", etc.), `LP Siding Accessories` (7 items: Color Match Coil, 2 sizes of Outside Corners, Touch-up Kit, Caulk, J-blocks, Mini Split), `LP SmartSide Soffit` (3 items: vented/solid). LP items use a SINGLE price across all 4 tiers (Howard's request) via new `LP_PRICES` dict merged into every `TIER_PRICES` entry. Verified: $298.24 LP Strand Lap is identical on all 4 tiers; on first backend boot after the migration ran, the 4 LP sections were appended to all 4 existing tier docs in the DB.
  - **Frontend**: New `EstimatorTabs.jsx` component (Excel-style tab strip with per-tab line count + subtotal). `useEstimate.js` refactored — merge logic now creates one line entry per `(tab, section, name)` tuple. Save key is `${tab}::${section}::${name}`. Legacy lines (no tab) auto-backfill on load. `SectionAccordion.jsx` is now tab-aware (filters misc rows by active tab, scopes new misc rows). `EstimateEditor.jsx` filters catalog sections by `s.product_lines.includes(activeTab)`.
  - **Limitations / known phase-deferred items**: PDF & email output (Phase 4) still renders all lines lumped together. HOVER importer (Phase 3) still populates only Vinyl tab. Per-tab homeowner Accept buttons (Phase 4) not yet built. Grand-total card + StickyBar still aggregate across all tabs.
 (Feb 2026): full bilingual support with EN/ES toggle. ESLint clean.

- **Iter 35** — **Invite Contractors via Admin Email + HOVER `.019 Coil` formula** (Feb 2026): two contractor-onboarding wins.
  - **`.019 Coil (1 per 5 Sq Siding)` HOVER formula** locked in for both Vinyl and Ascend tabs: `qty = siding_sqft / 500` (i.e. Squares ÷ 5, rounded to 2 decimals). Verified across 6 cases (25 Sq → 5 rolls, 12.5 Sq → 2.5 rolls, 0 → 0, etc.). 11/11 pricing parity tests still green.
  - **New invite flow on `/branding-admin`**: supplier admin enters a contractor email (+ optional name + personal note), clicks **Send Invitation**, and the contractor receives a branded Resend email with a one-click signup link `https://app.pro-quotes.com/login?mode=register&email=...&code=ALSIDE-XXXXXX`. Login page parses those query params, auto-switches to register mode, pre-fills the email + access code so the contractor only types their name + password. Recent invitations list on the admin shows email · sent timestamp · pending/signed-up status · "Copy link" button. New backend routes (token-gated): `POST /api/admin/invite-contractor` (validates email, blocks duplicates with 409, renders branded HTML with inline styles + supplier logo, sends via Resend, persists to `db.invitations`), `GET /api/admin/invitations` (last 50 invites annotated with `registered=True/False`). New `InviteContractorIn` Pydantic model. Verified end-to-end: 7/7 new tests in `test_invite_contractor.py` pass (incl. real Resend delivery to `delivered@resend.dev`), screenshot confirms admin panel renders + Login URL `?mode=register&email=bob@example.com&code=ALSIDE-JR47Q8` correctly prefills both fields. Lint clean.

- **Iter 36** — **Vero Windows restructure + per-row adders + Window Job Setup** (Feb 2026): full overhaul of the Windows tab to match Howard's updated Excel layout.
  - **Catalog**: split the single "Vero Windows" section into 5 per-product-type sections (Double Hung, 2-Lite Slider, 3-Lite Slider, Casement, Picture) with all size buckets per the Excel. Dropped Window Upgrade Options + Window Package Price + Sentry/Heavy Duty/Integral Nail Fin (now per-window-type adders). Added new "Vero Windows Custom Quote" section above Double Hung with a single $0-editable "Vero Window Quote" row for one-off bids. Added "Window Material List" section (.019 Coil / PVC Trim / G8 Trim / Caulking). Renamed install + interior trim rows per Excel.
  - **Per-row adder UI**: every window line carries an expandable "Upgrade Options" block. Each adder is a checkbox + its own qty input. Math: `line_total = line.qty × (mat + lab) + Σ(adder.qty × (adder.mat + adder.lab))` so a 10-window line can have 3 with Tempered glass + 4 with Grids (front of house only). New `EstimateLineAdder` model (name + mat + lab + qty). Adders surface on Vero Double Hung / 2-Lite Slider / 3-Lite Slider / Casement / Picture — 8-11 adders per type. All prices start at $0; Howard fills in via Pricing Admin.
  - **Window Job Setup panel**: top of windows-kind editor. (a) Install method 3-toggle (Pocket / Full Fin / Block Frame) auto-flows total window count into the matching install row + zeroes the other two; manual override still works. (b) "Home built before 1978" checkbox auto-adds Lead Safe Test Fee (qty=1) + Lead Safe Installation Practices (qty=total window count); unchecking zeroes both.
  - **HOVER mapping**: new `Fascia/rake or frieze up to 8" coverage` auto-fill (qty = eaves_lf) for both vinyl + ascend tabs.
  - **Other QoL**: $0-mat lines excluded from Material List PDF (skips labor-only rows like "Cap entry door"); `Fascia/rake or frieze up to 8" coverage` reset to $0 mat across all 4 tiers (labor-only line); siding "Material Colors" block hidden on windows-kind estimates (frame/interior/exterior shown instead); "Quantity Verification Required" modal on HOVER upload requires "I Agree" before file picker opens.

- **Iter 37** — **Mezzo (3000 Series) windows tab + W×H smart entry** (Feb 2026): brand-new product line layout that abandons the catalog-row model in favor of true opening-by-opening entry.
  - **Phase 1 + 2 shipped**: all 4 Mezzo product types — Double Hung, 2-Lite Slider, 3-Lite Slider, Picture (no Casement per Howard). Per-type buckets straight from the Mezzo wholesale Excel: DH 13 buckets (32-148 UI), 2-Lite 13 buckets (30-156 UI), 3-Lite 11 buckets (50-192 UI), Picture 11 buckets (21-154 UI). DH carries 8 adders (Extruded Beige, ClimaTech Plus, ClimaTech TG2, Obscure, Tempered, NAILFIN, Black Ext, Cherry Lam); 2-Lite/3-Lite/Picture share 5 adders (Extruded Beige, ClimaTech Plus, Grid 1", Obscure, Tempered).
  - **Tab architecture**: new "Mezzo" product-line tab next to "Vero" on the windows-kind editor. Sticky bar shows per-tab subtotals. Each tab routes to its own panel — Vero keeps the catalog-row layout, Mezzo uses the new opening panel.
  - **Mezzo opening entry (Option D)**: contractor clicks "+ Add Mezzo {type} opening". Row inputs: W (in) · H (in) · Qty · live UI calculation. UI auto-snaps to a size bucket → base price pulled from per-tier matrix. Out-of-range UI shows red warning. Per-opening adder checkboxes: prices for FLAT adders vary by size bucket (e.g. ClimaTech Plus $31.98 at 32-73 UI vs $50.57 at 102+ UI); per-opening adder qty defaults to opening qty. "Tempered Full" is sqft-based — auto-computes `$9.18 × (W × H / 144)` per opening (no flat per-window charge per Howard's call). Optional notes/label field hidden behind a sticky-note toggle ("Kitchen — west wall").
  - **Data**: new `MezzoOpening` Pydantic model + `mezzo_openings: list` field on EstimateIn. Frontend generates UUID ids; backend snapshots `base_mat` + `bucket_label` at save time so material-list rendering stays cheap. New `GET /api/mezzo/catalog` tier-aware endpoint returns the full product-type × bucket × adder matrix for the contractor's tier. All prices start at $0 across all 4 tiers (whole-sale / Contractor / Builder-Dealer / one-opp) — Howard fills in via Pricing Admin later. `calc_totals` rolls openings into per-tab + grand-total ledger.
  - **Verified**: data check confirms all 4 product types ship correctly (DH 13 buckets/8 adders, 2-Lite 13/5, 3-Lite 11/5, Picture 11/5). Screenshot validates W=36/H=60 opening snaps to "94-101 UI" bucket, Tempered Full shows `$9.18/sqft × 15.00sqft` hint. 18/18 backend tests pass.

- **Iter 38** — **Mezzo Phase 3: DB-backed pricing matrix + Paste-from-Excel admin** (Feb 2026): replaced the $0 hard-coded Mezzo prices with real per-tier matrices.
  - **Excel ingestion**: built `/tmp/extract_mezzo.py` which dynamically scans column F of each of the 4 source workbooks (whole-sale, Contractor, Builder-Dealer, one-opp) for product titles, locates the "U.I. Size" header row, auto-detects adder column order (the source files shuffle adder columns between tiers), and emits `/app/backend/mezzo_seed_prices.json` — the canonical 4-tier × 4-product price snapshot bundled with the repo (70 KB).
  - **MongoDB**: new collection `db.mezzo_prices` with unique index on `(tier, product_type)`. 16 docs total (4 tiers × 4 products). Each doc holds the full `base_prices` dict (per bucket) plus the full `adder_prices` matrix (per adder × per bucket). Tempered Full is intentionally NOT stored — it's sqft-rated at the constant $9.18/sqft in code. `seed_mezzo_prices()` runs idempotently on every boot; admin edits in Mongo are preserved.
  - **Backend endpoints (token-gated)**: `GET /api/admin/mezzo/prices` returns the full matrix + metadata (buckets, adder names); `PUT /api/admin/mezzo/prices` upserts one (tier, product_type) grid with bucket/adder key sanitisation. The contractor-side `GET /api/mezzo/catalog` now reads live from Mongo via the new `catalog_for_tier_async` helper (was previously hitting the in-code $0 defaults).
  - **Admin UI** (`/branding-admin` → "Mezzo Window Pricing Matrix" card): tier-tab strip × product-tab strip × spreadsheet-style grid (UI bucket rows × Base + adder cols). Every cell is an editable number input. **Paste-from-Excel**: focus any cell + Ctrl/Cmd-V — the panel parses TSV from the clipboard (strips $, commas) and fills rightward + downward starting from the focused cell. Dirty-state banner + Save / Reload buttons.
  - **Verified**: 8/8 pytest tests pass (`/app/backend/tests/test_mezzo_pricing.py` — admin GET/PUT, 403 / 400 paths, idempotent seeding, contractor catalog read-back). 11/11 Playwright UI assertions pass (panel renders, tier+product switching, dirty state save→PUT→reload, multi-cell paste fills correctly, Reload discards). Howard can now sit down at `/branding-admin`, drop in any Mezzo tier grid from an Excel paste, hit Save, and contractors see the new prices on their next estimate.

- **Iter 43 — Vero pricebook simplification** (Jun 2026, Howard's 2nd Wholesale Vero pricebook): trimmed Vero options + replaced glass package names per new pricebook structure.
  - **Sister colors**: forced to `["White Interior/White Exterior"]` for every Vero product type (DH, 2-Lite, 3-Lite, Picture, Patio Door, Casement). All Tan/Laminate/Woodgrain base entries dropped. Job-level Vero exterior+interior color picker hidden in `JobInfoPanel.jsx` (Mezzo color picker untouched).
  - **Glass packages**: replaced 6-item IntelliGlass family with **Climatech Plus + Climatech TG2** only, sourced from the new pricebook. DH and 2-Lite use per-UI rule (Min-101 + over-101) → converted to bucket prices using bucket max-UI. 3-Lite / Picture / Casement use bucket prices directly.
  - **Tempered upcharge**: replaced legacy 7+ packages with **Climatech Plus Tempered + Climatech TG2 Tempered** only.
  - **Premium options (DH)**: 11 new SKUs from "Premium Dh Options" sheet (INTELL · TM · NSS · {NONE}, INTELL · NT · NSS · OBS, 3× INTELPLUS variants, 3× INTELX variants, 3× INTLX3 variants). All legacy Grid/Screen/Frame/Decorator entries (FlexScreen, Snap On Nail Fin, Foam Wrap, Sentry, Oriel Style, Coated Exterior, etc.) removed.
  - **Premium options (Picture)**: 11 new SKUs from "Picture Window Premium options" sheet.
  - **Files touched**: `/app/backend/vero_seed_prices.json` (regenerated via `/tmp/build_vero_seed.py` from new xlsx), `db.vero_prices` reseeded with `force=True`, `/app/frontend/src/components/estimate/VeroPanel.jsx` (color picker now conditional on >1 sister color; reconciliation effect auto-snaps stale sister_color / glass_package / tempered / premium_options to currently-valid values), `/app/frontend/src/components/estimate/JobInfoPanel.jsx` (Vero color block wrapped in `{false &&}` until pricing is reclarified).
  - **Verified**: catalog API returns exactly the new shape (verified via curl); existing $602 Vero DH opening still prices correctly; sister picker no longer renders; new glass/tempered/premium dropdowns render exactly 2/2/11 options.

- **Iter 43b — Vero Install + Trim P0 bug fix** (Jun 2026): `setInstallMethod` / `setHomePre1978` / `totalWindowQty` in `useEstimate.js` were counting only legacy section-line qty (`l.section.startsWith("Vero ") && l.section.endsWith("Windows")`) — but real openings now live in `vero_openings` / `mezzo_openings` (W×H matrix introduced in Iter 37/39). Result: clicking POCKET / FULL FIN / BLOCK FRAME on a windows-kind estimate computed `totalQty=0` → install + lead-safe rows pushed `qty=0` → snapshot showed `$0.00` for Install + Trim.
  - **Fix**: `totalQty = sum(legacy lines) + Math.max(vero_openings_qty, mezzo_openings_qty)`. Max(vero,mezzo) avoids double-counting because HOVER auto-mirrors each opening into both Vero & Mezzo (two brand quotes, one physical window).
  - **Verified live**: opened EST-863006 (1 Vero + 1 Mezzo opening, install_method=""), clicked POCKET, autosaved → `install_method=pocket`, both windows-tab + mezzo-tab "Window DH/Slider - Pocket Install" lines correctly set to qty=1 (not 2), Vero snapshot now reads `INSTALL + TRIM $518.85 / 6 lines · labor` (was `$0.00 / 0 lines`). Total grew from $920 → $1,661.41.

- **Iter 44 — Vero adopts Mezzo's adder model** (Jun 2026, single-sheet pricebook drop): rebuilt Vero pricing + UI to mirror Mezzo 1:1. Glass-package / tempered-upcharge / premium-options dropdowns gone; replaced with **checkbox-card adders** identical to Mezzo's Upgrade Options panel.
  - **New data shape**: `db.vero_prices` now stores `{ base_prices: {bucket: $}, adder_prices: {adder_name: {bucket: $}} }` (mirrors `mezzo_prices`). `glass_packages` / `tempered` / `premium_options` / `glass_packages_patio` fields removed from the schema.
  - **Catalog**: 4 ui-bucket products (DH, 2-Lite, 3-Lite, Picture) × 9–12 adders, plus Patio Door (fixed model, no adders). Vero 1-Lite Casement dropped (not in new pricebook). Adder list per product:
    - **DH** (12): Climatech Plus, Solid Color Flat Grids, Head Expander, Sentry System, Obscure Full, Climatech TG2 Plus, Foam Wrap, Foam Frame, Climatech Plus Tempered, Climatech TG2 Tempered, Integral Nailing Fin, Oriel Style Double Hung
    - **2-Lite / 3-Lite / Picture** (10): same set minus Sentry System and Oriel Style
  - **Excel ingestion**: built `/tmp/build_vero_seed.py` that handles the new single-sheet "Whole Sale" layout — auto-detects per-UI overflow rules in headers (e.g. `Base Window (White) $4.30` = $4.30 per UI over 101) and expands those into full bucket grids.
  - **Frontend**: rewrote `/app/frontend/src/components/estimate/VeroPanel.jsx` (~570 LOC → ~530 LOC) to render Mezzo-style checkbox cards in 3 visual rows per Howard's preference. Mutually-exclusive pairs wired: `Climatech Plus ↔ Climatech TG2 Plus` and `Climatech Plus Tempered ↔ Climatech TG2 Tempered`. Default `Climatech Plus` auto-applied on new openings. Bulk-apply modal, "N of M" usage badges, qty editor on selected cards — all carried over from Mezzo.
  - **`VeroOpening` model**: `adders: List[EstimateLineAdder]` added. Legacy `glass_package` / `tempered_upcharge` / `premium_options` / `glass_mat` / `tempered_mat` / `premium_mat` fields preserved (deprecated) so historical estimates keep rendering.
  - **`useEstimate.buildPayload`**: now serializes `vero_openings[].adders[]` alongside legacy fields.
  - **`calc.js` + `VeroJobSnapshot.jsx`**: sum new `adders[].qty × .mat` AND legacy glass/temp/premium snapshots so historical estimates keep their totals.
  - **Reconciliation hook**: detects pre-Iter-44 openings (`glass_package` / etc populated) and silently migrates them to `adders: []` on first load.
  - **Files touched**: `vero_catalog.py`, `vero_prices.py` (allowed-keys), `vero_seed_prices.json` (regenerated), `routes/vero.py` (empty-shell), `models.py` (`VeroOpening.adders`), frontend `VeroPanel.jsx`, `useEstimate.js`, `calc.js`, `VeroJobSnapshot.jsx`.
  - **Verified live**: EST-863006 → expanded Upgrade Options → toggled Climatech Plus (auto-default) + Climatech TG2 Plus (auto-deselected CP via exclusive pair) + Solid Color Flat Grids + Foam Wrap + Sentry System. UI shows orange-highlighted cards, per-card qty input, badge count, total `+$22.93`. Autosave persists `adders: [{name, mat, qty}]` to `db.estimates.vero_openings[].adders`. Vero DH section total $287.57 → $310.50 (base + Foam Wrap), Job Snapshot Window Openings reflects in real time.
  - **Follow-up note**: `/branding-admin` `VeroPricingPanel.jsx` still references the old `glass_packages` / `tempered` / `premium_options` sections — its tabs will show empty grids until rewritten to use `adder_prices`. Howard can edit base prices directly in Mongo for now, or via re-seeding the JSON. Same applies to HOVER importer (`routes/hover.py`) which still produces legacy-shape openings — the frontend reconciliation hook auto-migrates them on first load, so functionally HOVER imports work fine.

- **Iter 46 — HOVER importer + admin Vero pricing editor cleanup** (Jun 2026): finished the Iter-44 migration by removing the last two references to the legacy glass/tempered/premium fields.
  - **`routes/hover.py`** — `HoverVeroOpening` Pydantic model + `_build_window_openings()` no longer write `glass_package`, `tempered_upcharge`, `premium_options`, `glass_mat`, `tempered_mat`, `premium_mat`. New imports emit clean `adders: []` (frontend's reconciliation hook attaches the default Climatech Plus on first render — same as `addOpening`).
  - **`/branding-admin` `VeroPricingPanel.jsx`** — old per-product tabs `glass_packages / tempered / premium_options / glass_packages_patio` collapsed into ONE unified **Adders · variant × UI** grid (12 columns × 14 buckets for DH). Patio Door now exposes only its **Base · sister color × Model** matrix. Header subtitle updated: `4 tiers · 5 products · base prices + adders matrix`.
  - **Verified live**: admin panel renders DH Base (1-col $287 → $627 across 14 buckets) and DH Adders (12-col matrix incl. Integral Nailing Fin, Climatech Plus Tempered, Foam Frame, Climatech Plus). Zero legacy tabs visible. HOVER importer no longer emits stale field names.

- **Iter 47 — HOVER auto-fills .019 Coil qty from window perimeter** (Jun 2026): contractors no longer eyeball the trim coil count for windows-only jobs.
  - **Math**: per-window perimeter = `2 × (W + H)` inches → ÷12 = LF; sum across every `W-N` opening from the HOVER extract; total LF ÷ 100 = qty of rolls (Howard's coverage assumption: 1 roll covers 100 LF of perimeter).
  - **Tabs**: emits both `tab="windows"` (Vero brand) and `tab="mezzo"` (Mezzo brand) line entries with the same qty, so both job snapshots reflect the trim even before the contractor picks a brand.
  - **Section / Item**: `Window Material List` → `Windows - .019 Coil` (unit `ROLL`, mat $161.33). Existing catalog mat/lab values untouched.
  - **Regression coverage**: `/app/backend/tests/test_hover_perimeter.py` — 7 pytest cases (mapping shape, 3-window perimeter, empty inputs, missing dims, large batch round-number, both-tab emission, zero-qty suppression). All passing.
  - **Files touched**: `/app/backend/routes/hover.py` (one new HOVER_MAPPING_SPEC entry); test file new.

- **Iter 78z+ Phase 2 (Blueprint annotator wiring)** (Feb 2026): wires the Phase 1 ProfileAnnotator into the Blueprint flow. Closes the loop on Howard's original ask: "when a blueprint is uploaded bring up each elevation like in the AI measure tool where the contractor can annotate the elevation with a box like the mask but have it add Shake or B&B."
  - **Backend**: blueprint upload now persists each rendered/uploaded page to `UPLOAD_DIR` via the new `_persist_page_image()` helper (sniffs PNG vs JPEG magic bytes and picks the correct extension). Page filenames are returned in BOTH the launch response (`page_paths` field on POST `/api/measure/ai-blueprint`) AND the resume payload (`run.page_paths` on GET `/api/measure/ai-blueprint/latest-for-estimate/{id}`) — annotator works during the Claude wait AND after a 502/restore.
  - **Frontend**: `BlueprintMeasureButton.jsx` gained `pagePaths` + `profileAnnotatorOpen` + `savedProfileAnnotations` + `currentRunId` state. New **"Tag Profiles"** button appears next to **Read Blueprints** as soon as `pagePaths` is populated. Saved annotations load on mount via `GET /api/estimates/{id}/profile-annotations`. The `ProfileAnnotator` modal renders blueprint pages as `Page 1`, `Page 2`, etc. with the full canonical palette + scale ref + per-box editor.
  - **Verified via testing agent (iter_24 report): 133/133 backend tests pass**. 5 new unit tests in `/app/backend/tests/test_blueprint_annotator_wiring.py` pin the contract (helper signatures, optional `annotations` kwarg, optional `estimate_id` kwarg, end-to-end overlay via aggregator, back-compat). 3 new HTTP integration tests in `/app/backend/tests/test_blueprint_page_paths_http.py` confirm `page_paths` round-trips correctly. Frontend bundle compiles clean.
  - **Bonus**: contractor can now hit "Tag Profiles" *before* the Claude run finishes — annotations are saved to the estimate and the next blueprint read picks them up automatically (no need to re-upload the PDF).
  - **Iter 78z+ Phase 2.1 (Save & Re-read)** (Feb 2026): the annotator now ships with a second purple **"Save & Re-read"** button alongside Save. Clicking it persists the boxes AND immediately fires the worker against the cached page bytes server-side (no re-upload, no re-click of Read Blueprints). One-step Campbell-fix loop.
    - New endpoint `POST /api/measure/ai-blueprint/rerun/{prev_run_id}` reads the previous run's `page_paths` from disk, creates a new run doc with `rerun_of: prev_run_id` for traceability, and dispatches the worker with the previous run's address + overhang. Inherits estimate_id (so the worker auto-loads the freshly-saved annotations).
    - Frontend: `BlueprintMeasureButton.jsx` exposes `rerunWithAnnotations()` which the annotator triggers via the new `onSaveAndRerun` prop. Same 5-min polling loop as the original launch — the busy spinner takes over the screen as soon as the modal closes.
    - **Verified via iter_25 (TBD or local)**: 4 new HTTP tests in `/app/backend/tests/test_blueprint_rerun_http.py` cover 404 (missing run), endpoint registration, 400 (no cached pages), and unauthenticated reject. All 125 tests across the Iter 78z chain still green.
  - **Iter 78z+ Phase 2.2 (AI Photo Measure rerun parity)** (Feb 2026): same Save & Re-run loop wired into the AI Photo Measure flow. Closes the Campbell loop in 1 step instead of 2 on the photo side as well.
    - Backend: new endpoint `POST /api/measure/ai-measure/rerun/{prev_run_id}` mirrors the blueprint pattern. Loads cached photo bytes from disk via the previous run's `photo_paths`, re-compresses them through `_compress_for_claude` (keeps box coords aligned with what Claude sees), and dispatches `_execute_ai_measure_worker` with the previous run's kind / address / overhang / deep_dormer_scan / estimate_id. New run carries `rerun_of` for traceability.
    - Frontend: `AIMeasureButton.jsx` exposes `rerunWithAnnotations()` (mirrors `resumeRunPolling` but kicks off a fresh worker first). ProfileAnnotator's `onSaveAndRerun` prop is wired only when `currentRunId` is set, so the Save & Re-run button shows up only after the first launch.
    - **Verified**: 4 new HTTP tests in `/app/backend/tests/test_ai_measure_rerun_http.py` (404 / endpoint exists / 400 no cached photos / unauthenticated). All 129 tests across the Iter 78z chain still green. Frontend bundles clean.

- **Iter 78z+ Phase 1 (Profile Annotator — AI Photo Measure)** (Feb 2026): the contractor's escape hatch for AI vision misses.
 Closes the Campbell-style failure where Claude returns lap for every gable. Contractor draws bounding boxes on uploaded photos, tags each with a canonical profile (Shake / B&B / Lap / etc.) — boxes are AUTHORITATIVE accent material that always lands on the catalog mapper's output, no matter what Claude says.
  - **Backend**:
    - `profile_callouts.apply_annotations_to_breakdown(breakdown, annotations)` — merges user-drawn boxes into the per-elevation breakdown as accent entries, re-aggregates `_per_profile_sqft`. Handles case-insensitive label matching, synthetic elevation rows for new labels, non-siding skip (stone/brick/stucco), zero/unknown skip.
    - `_aggregate_to_hover_shape(raw, annotations=None)` signature extended on BOTH `ai_measure.py` AND `ai_blueprint.py`. Workers load `db.estimates.profile_annotations` when `estimate_id` is provided and pass it through.
    - **Endpoints**: `GET /api/estimates/{id}/profile-annotations` + `PUT /api/estimates/{id}/profile-annotations`. Stored as free-form dict on the estimate (keyed by photo_idx; reserved `_scale_refs` key for per-photo px-to-ft calibration).
  - **Frontend**:
    - New `ProfileAnnotator.jsx` modal (full-screen, 6xl wide):
      - Image strip on the left (photos with annotation count badges)
      - Canvas-based click-and-drag box drawing on the active image
      - Profile palette (9 canonical families, color-coded) for the active drawing color
      - **Scale reference**: click "+ Set scale", drag a known-length line (door, window), type the real-world ft → all boxes auto-compute their ft²
      - Per-box editor: profile / elevation / ft² / note → all editable inline
      - Save → calls PUT and closes
    - **"Tag Profiles" button** added to AI Measure modal action bar (between Start Over and Run AI Measure). Shows live annotation count badge.
    - Annotations are loaded automatically when the AI Measure modal opens on an existing estimate.
  - **Verified via testing agent (iter_23 report): 125/125 tests pass**. 9 new unit tests in `/app/backend/tests/test_annotation_overlay.py` pin the overlay math + 9 new HTTP tests in `/app/backend/tests/test_profile_annotations_http.py` cover endpoint CRUD, auth (401/403/404), payload validation (400), and worker integration via direct `_aggregate_to_hover_shape` call. Frontend smoke-tested: ProfileAnnotator bundle compiles, login page loads clean.
  - **Status**: Phase 1 ships AI Photo Measure only. Blueprint UI wiring is queued (backend overlay already supports it — just needs server-side page rendering for PDFs).
  - **Notes for future iters**: (a) Add a Pydantic schema for the box dicts before exposing to non-admin users. (b) Broaden the `except Exception` around the breakdown helper to log instead of swallow.

- **Iter 78z (Reference photo cross-check)** (Feb 2026): closes the "AI vision misses small details" gap by running a SECOND focused Claude pass that re-examines the same uploaded photos to verify the primary breakdown's profile callouts. Catches things like Campbell's porch B&B that the primary pass overlooked.
  - **Backend**: new endpoint `POST /api/measure/ai-cross-check/{run_id}` in `/app/backend/routes/ai_measure.py`. Loads the cached photo bytes from `db.ai_measure_runs[run_id].photo_paths` (no re-upload), builds a focused verification prompt that summarizes the primary breakdown and asks Claude to look specifically for **small accent panels**, **profile mis-classification** (lap vs dutch lap, shake vs B&B), and **masonry mis-reads**. Returns a structured diff via `_compute_recheck_diff()`: `conflicts: [{elev, role, primary, verified, confidence, note}]` + `suggested_accents: [{elev, location, profile, approx_sqft, confidence, callout}]` + `agreement_pct` + `overall_confidence`. Diff result is persisted on the run document (`result.measurements._ai_profile_recheck`) so subsequent loads can re-render without re-running Claude. Endpoint enforces: run exists, run belongs to current user (403 otherwise), primary run is `status: "done"` (409 otherwise), at least one cached photo on disk (400 otherwise).
  - **`_normalize_family()` helper**: maps verifier output to the canonical profile families (lap/dutch_lap/shake/board_batten/vertical/nickel_gap/stone/brick/stucco/unknown), tolerating Claude synonyms like "Clapboard", "Shaker", "Shingles", "BNB", "Batten".
  - **Frontend**: extended `PerElevationBreakdownCard.jsx` with an optional `runId` prop. When present, a new **"🔁 Re-check with AI"** button appears in the card header. Clicking it spins the icon, calls the endpoint, and renders a violet panel with: (a) the conflict list ("primary said LAP → verifier says SHAKE", click chip below to swap) and (b) the suggested-accents list with per-row **"+ Add"** (uses the existing add-accent flow to inject the suggestion + re-map lines) and **"×"** (dismiss). Both helpers patch `_ai_profile_recheck` so dismissed/accepted suggestions persist across re-renders.
  - **`AIMeasureButton.jsx`**: tracks `currentRunId` so the cross-check button has the right runId on both the fresh-run path AND the resume / restore paths.
  - **Verified via testing agent (iter_22 report): 115/115 tests pass**. 11 new unit tests in `/app/backend/tests/test_cross_check_diff.py` (covers canonical/synonym/empty/unknown family normalization, no-conflict path, profile conflict detection, accent suggestion + dedupe, empty-primary edge case, zero-sqft skip, gable conflict, case-insensitive label match) + 8 new HTTP integration tests in `/app/backend/tests/test_cross_check_http.py` (covers 404/403/409/400 paths via seeded Mongo run docs — no Claude credits spent). Frontend compiles + loads clean.
  - **Notes for future iters**: (a) `routes/ai_measure.py` is now 2019 lines — natural extraction candidate is `routes/ai_cross_check.py` next iter. (b) The endpoint has no rate limit — consider a per-run cooldown if the feature gets heavy use to avoid Emergent LLM quota burn.

- **Iter 78z (Swap Profile + P1.4 Gutter Geometry)** (Feb 2026): two follow-up shipments after the P1.2/P1.3 per-elevation breakdown.
  - **Swap Profile (frontend)**: every profile chip in `PerElevationBreakdownCard.jsx` is now a clickable button. Click → opens `SwapProfileModal` → contractor picks a new family (lap/dutch_lap/shake/B&B/vertical/nickel_gap) → the chip's role (body / gable / dormer / accent) is patched in `_per_elevation_breakdown`, `_per_profile_sqft` is recomputed locally via `recomputePerProfile()` (mirrors backend `breakdown_walls_by_profile`), and the modal calls `POST /api/measure/map` to refresh the catalog lines. No re-run of the expensive AI pipeline. Stone/brick/non-siding chips are not clickable.
  - **P1.4 Gutter geometry (backend)**: new helpers in `routes/hover.py`:
    - `_downspout_drop_ft(m)` — story-aware drop length: `avg_wall_height_ft + 3` (kick + slack), with fallback to `story_count × 9` then 12 LF. Fixes Howard's 2x undercount on 2-story homes (drop was a flat 10 LF; now 21 LF for 2-story).
    - `_downspout_lf(m)` — total downspout coil LF (count × drop). Replaces the old fixed `count × 10`.
    - `_has_gable_wall(m)` — looks at `_per_elevation_breakdown[*].gable_sqft > 0` or `_ai_gable_sqft > 0` to detect a gable roof.
    - `_gutter_corner_count(m)` — returns (outside, inside) corner counts from `outside_corner_lf / avg_wall_height` and `inside_corner_lf / avg_wall_height`.
    - `_mitre_count(m)` — gable roofs: 0 outside mitres (gutter doesn't wrap), inside mitres still emit; hip roofs: all corners emit a mitre.
    - `_pipe_clips_count(m)` — 1 clip per 6 ft of downspout drop, minimum 2 per downspout. Scales correctly with story (8 clips on a 1-story 4-downspout home, 16 on 2-story).
    - `_sealant_count(m)` — 1 tube per 4 joint points (mitres + end caps + outlets).
  - **New HOVER_MAPPING_SPEC rows** (Seamless Gutter section, all 3 siding tabs): **Mitre** (Each), **Pipe Clips** (Each), **Gutter Sealant** (Each). All 3 auto-suppress when their formula returns 0 (e.g. gable roofs hide Mitre).
  - **Verified via testing agent (iter_21 report): 106/106 tests pass** across `test_gutter_geometry.py` (16 unit) + `test_gutter_geometry_http.py` (10 HTTP) + the inherited P1.2/P1.3 suites (80). Live curl on the demo case (2-story, 160 LF eaves, hip roof) returns 8 gutter accessories including 4 Mitres, 28 Pipe Clips, and 6 Gutter Sealant tubes — every line carrying a human-readable `note` so Howard can spot drift in the source measurements.

- **Iter 78z (P1.2 + P1.3) — Per-Elevation siding breakdown for AI Photo Measure + Blueprint** (Feb 2026): closes Howard's Campbell-house bug where mixed-profile homes (Lap body + Shake gables + B&B porch) were being lumped into a single Charter Oak Dutch Lap line, severely undercounting Shake/B&B materials.
  - **Backend (P1.2)**: new `_profile_siding_lines()` helper in `/app/backend/routes/hover.py` consumes `measurements._per_profile_sqft` (built by `profile_callouts.breakdown_walls_by_profile` in Iter 78y/P1.1) and emits ONE catalog line per profile family per tab. New `_PROFILE_SKU_MAP` covers Vinyl (Charter Oak DL / Pelican Bay Shakes / Vertical B&B 7"), Ascend (Composite Lap / Composite B&B — Shake skipped, no SKU), and LP Smart (38 Series Lap PCS / Shake PCS / Nickel Gap PCS / Vertical Panel). `_build_lines` was extended to skip the 3 default-siding rows in `HOVER_MAPPING_SPEC` (now flagged `_is_default_siding: True`) when a multi-profile breakdown fires, preventing double-counting. Single-profile / HOVER-PDF / no-breakdown flows are untouched — they still use the default Charter Oak mapping with HOVER's small-opening 10% adder.
  - **Blueprint mirror**: `ai_blueprint.py::_aggregate_to_hover_shape()` now populates `_per_elevation_breakdown` + `_per_profile_sqft` so blueprint reads get the same split treatment as photo measures.
  - **Frontend (P1.3)**: new `/app/frontend/src/components/estimate/PerElevationBreakdownCard.jsx`. Renders the per-elevation grid with color-coded profile chips (Lap=blue, Shake=amber, B&B=pink, stone/brick=gray, accents tagged), shows total ft² split + drift warning banner (fires when profile sum drifts >10% from `siding_sqft`), and exposes a **"+ Add Accent" button per elevation**. Modal lets the contractor pick profile (lap/dutch_lap/shake/B&B/vertical/nickel_gap) + ft² + optional location; on submit it patches `_per_elevation_breakdown[i].accents` + `_per_profile_sqft`, calls `POST /api/measure/map` to re-run the catalog mapper, and surfaces the updated lines on the preview without a re-run of the expensive AI pipeline. Wired into both the **Blueprint** preview (`BlueprintMeasureButton.jsx`) and the **AI Photo Measure** preview (`AIMeasureButton.jsx`).
  - **Cascading accessories preserved**: J-Channel, Outside/Inside Corners, Starter, Finish Trim, Soffit J-Channel, House Wrap, etc. still emit on the vinyl tab when the split fires — they're driven by perimeter/eaves/rakes math (unchanged), not by siding sqft.
  - **Verified end-to-end via testing agent (iter_20 report, 86/86 tests pass)**: 8 new unit tests in `/app/backend/tests/test_profile_siding_lines.py` + 6 new HTTP integration tests in `/app/backend/tests/test_measure_map_per_profile_http.py` cover single-profile fallback, multi-profile splits across vinyl/ascend/lp_smart tabs, no-double-counting, perimeter-driven accessory cascade, stone/brick non-siding exclusion, and unknown-family graceful skip. Live curl on `/api/measure/map` with the Campbell shape (`{lap: 1840, shake: 168, board_batten: 60}`) returns 3 distinct vinyl-tab lines: Charter Oak DL 18.4 SQ + Pelican Bay Shakes 1.7 SQ + Vertical B&B 0.6 SQ, each tagged `note: "Per-elevation breakdown: <FAMILY> <sqft> ft²"`.

- **Iter 45 — Window-side line-item pricing aligned to canonical Excel** (Jun 2026, Howard's "Window app price layout page 6-8-26.xls"): audited every line in the 6 windows/mezzo-shared sections (Window Material List, Window Installation, Sliding Glass Door Install, Window Exterior/Interior Trim Work, Window Misc.) against the canonical Excel. Found 5 discrepancies — all in the Material List section where mat prices were $0 in the build but priced in the Excel. Fixed:
  - `Windows - .019 Coil`: mat $0 → **$161.33**, lab $23 → **$0**  (and removed the "(1 per 5 Sq Siding)" suffix in Iter 45b per Howard)
  - `Windows - PVC Trim Coil`: mat $0 → **$167.08**
  - `Windows - Performance G8 Trim Coil`: mat $0 → **$170.53**
  - `Windows - Caulking (per color)`: mat $0 → **$8.23**
  - All other 27 line items in the 5 labor-only sections (Installation, SGD, Trim, Misc.) already matched the Excel exactly.
  - **Files touched**: `/app/backend/catalog_seed.py` (WINDOWS_PRICES + ITEM_META).
  - **DB migration**: ran one-off script over `db.price_tiers` (4 docs × 4 fixes = 16 in-place mat updates + 4 lab updates). Idempotent — safe to re-run.
  - **Verified live**: `GET /api/catalog` for Window Material List section returns exactly the Excel values. Section names, item names, units, and per-tier prices for all 4 tiers (whole-sale / Contractor / Builder-Dealer / one-opp) confirmed.

## Configuration (`backend/.env`)
- `SUPPLIER_NAME=Alside Supply`
- `SUPPLIER_TAGLINE=Howard Hunt · Territory Sales Manager · (724) 640-4333`
- `SIGNUP_CODE=ALSIDE-JR47Q8`     ← rotate this whenever you want
- `SUPPLIER_ADMIN_TOKEN=OXSp1EX...` ← used in `/branding-admin?token=...`
- `RESEND_API_KEY=re_[REDACTED]...`
- `ADMIN_EMAIL=hhunt6677@yahoo.com` / `ADMIN_PASSWORD=[REDACTED — backend/.env ADMIN_PASSWORD]`
- `SENDER_EMAIL=quotes@pro-quotes.com` (verified domain: SPF + DKIM + DMARC live on Cloudflare)

## Backlog
### P0 (next up)
- **Stripe deposit on Accept page** — when a homeowner clicks "I accept", optionally route them to Stripe Checkout to lock in the job with a configurable deposit (Emergent test Stripe key already in pod env)

### P1
- Resend open + click tracking via webhook (`email.opened`, `email.clicked`) → show contractors which quotes are being viewed
- Real PWA app icons (still programmatic placeholder)
- **DONE in Iter 35**: ~~Invite Contractors via Admin Tab~~ — supplier can now send branded email invites with one-click signup links
- **DONE in Iter 38**: ~~Mezzo Pricing Admin matrix~~ — supplier can paste any tier × product grid from Excel and contractors see prices live
- **DONE in Iter 39 (Feb 2026)**: ~~AI Photo Measure + Photo Refine merge double-upload UX bug~~ — `AIMeasureButton` now hands its uploaded photos to `PhotoMeasureButton` via `prefillFiles`. Single AI photo auto-loads into the canvas; multiple photos render as a thumbnail picker so contractors skip re-uploading.
- **DONE in Iter 39 (Feb 2026)**: ~~Change Photo mid-session~~ — added `Change Photo` button next to `Recalibrate` so contractors can swap between AI photos (front → side elevation) without losing tap measurements. Each measurement/opening tagged with `photoUrl`; overlay only renders markers for the active photo, off-photo markers still roll into totals and show an `OTHER PHOTO` badge in the list.
- **DONE in Iter 39 (Feb 2026)**: ~~AI Measure missing Starter / Corner accessories~~ — added `starter_lf`, `outside_corner_lf`, `inside_corner_lf` to the AI vision schema and the aggregator output (fallbacks: starter→eaves_lf, outside corners→4×avg wall height). Photo Measure builder also now emits `starter_lf` so manual tap-flow populates Vinyl Accessories → Starter through `_build_lines`.
- **DONE in Iter 39 (Feb 2026)**: ~~No-siding zone masking on the Photo Measure tool~~ — contractor can now tap a rectangle OR draw a polygon, label it Brick / Stone / Garage door / Stucco / Other, and the ft² is deducted from `siding_sqft`. Each zone is hatched-overlay on the photo with a `-220 ft² Brick` callout. Live Totals panel shows the deducted amount and a per-category summary; zones travel through `raw_photo` to the backend.
- **DONE in Iter 39 (Feb 2026)**: ~~Masked zones surface on customer PDF + email~~ — new `Estimate.photo_zones_summary` + `photo_zones_deducted_sqft` fields persisted via the Apply flow (JobInfoPanel + ISSEstimateEditor). `buildEmailHtml` now renders an italic "Materials excluded: Brick: 220 ft²; Garage door: 168 ft² (388 ft² total)" line under each siding section (Vinyl Siding / Ascend Cladding / LP Smart Siding). i18n keys `email.materialsExcluded` added for EN + ES. Customer PDF reuses the same HTML via WeasyPrint.
- **DONE in Iter 39 (Feb 2026)**: ~~Ascend colors in Accessories + Outside Corner pickers~~ — new `accessoryColorGroupsForEstimate()` helper appends a 21-color Ascend optgroup to the two accessory pickers in both Siding/Windows and ISS estimates.
- **DONE in Iter 45 (Feb 2026)**: ~~Vinyl Soffit LF → PCS conversion~~ — Renamed 4 soffit SKUs (`Charter Oak Soffit Standard color`, `Charter Oak Soffit Architectural color`, `Greenbriar Soffit`, `T2 Soffit`), dropped 4 legacy `up to 13"-30" wide` variants, flipped unit `LF → PCS`, and multiplied per-tier prices ×10 per Howard's pricing convention. New `Estimate.overhang_in` field (default 12) drives Howard's formula: `Pieces = (Overhang × (Eaves+Rakes)) ÷ (Exposure/12 × Panel length)`. Overhang input added next to Waste Factor in Job Info (siding/windows) + ISS settings. Migration idempotently renames + converts existing estimate lines (qty/10, mat×10 — dollar totals preserved). HOVER + AI Measure routes accept `overhang_in` form param.
- **DONE in Iter 46 (Feb 2026)**: ~~Soffit J-Channel LF → PCS conversion~~ — flipped unit on 3 SKUs (`3/4" Soffit J-Channel Standard color`, `3/4" Soffit J-Channel Architectural color`, `1/2" Soffit J-Channel for T2`). Prices now match the Vinyl Accessories J-Channel pricing ($5.23/$6.03/$5.23 Contractor). HOVER mapper math switched from `(eaves + rakes) LF` → `ceil((eaves + rakes) / 12.5) PCS` (12'6" stick length). Idempotent migration force-sets new prices in `price_tiers` and converts existing estimate-line qty (ceil/12.5) + unit.
- **DONE in Iter 47 (Feb 2026)**: ~~AI Photo Measure inflated gable / dormer geometry as 2-story walls~~ — overhauled the Claude vision system prompt to: (a) define `height_ft` as eave height ONLY (never roof peak), (b) capture gable triangles in a new `gable_triangle_height_ft` per-wall field (auto-area = 0.5 × width × gable_h), (c) capture dormer face area in a new `dormer_face_sqft` per-wall field, (d) give Claude explicit visual cues to distinguish gable / dormer / true 2nd-story, biasing to 1-story-with-gable when uncertain. Aggregator now adds gables + dormers on top of the masonry-adjusted rectangular siding area. Preview UI surfaces the breakdown as an italic line (`Geometry: rectangular walls · gable triangles add 168 ft² · dormer faces add 60 ft²`) so the contractor can sanity-check before applying.
- **DONE in Iter 48 (Feb 2026)**: ~~AI still over-calls 2nd story on wide dormers~~ — added a HARD GUARDRAIL to the prompt (`height_ft > 12` only if BOTH "two horizontal rows of windows spanning full width" AND "soffit clearly above 2nd row"), explicit "wide dormer is still a dormer" rule, and a "1-story-with-dormer ALWAYS beats 2-story" tie-breaker. More importantly, made the **Wall Breakdown** table in the AI Measure preview fully editable: inline W / H-eave / Gable-h / Dormer-sqft cells with live siding-ft² recompute on every keystroke. Edited walls flag `wallsDirty` — Apply auto-refreshes line items via `/measure/map` so Charter Oak qty etc. reflect the override.
- **DONE in Iter 49 (Feb 2026)**: ~~Upgraded AI Photo Measure model from Claude Sonnet 4.5 → Claude Opus 4.5~~ (`claude-opus-4-5-20251101`). ~3× the per-measure cost but materially better dormer / gable / 2nd-story recognition. Howard confirmed the first test takeoff was nailed.
- **DONE in Iter 50 (Feb 2026)**: ~~Server-side persistence for AI Measure sessions~~ — new `ai_measure_sessions` Mongo collection keyed by `(company_id, estimate_id)`, 3 endpoints (`GET/PUT/DELETE /api/measure/sessions/{id}`). Photos now upload to `/api/uploads` on selection (already-persisted on disk); the AI Measure endpoint learned a new `photo_paths` form param that points at existing uploads so the AI run doesn't re-upload bytes. Frontend `AIMeasureButton` autosaves the session 1 sec after any change (photos / preview / form overrides / wall edits). Reopening shows a "Resume" banner with Resume / Start fresh buttons. Apply auto-clears the session on success. Smoke-tested all 3 endpoints end-to-end.
- **DONE in Iter 51 (Feb 2026)**: ~~Photo Measure calibration ft/in unit trap~~ — replaced the bare `window.prompt("Real length of this reference (in INCHES):")` in `PhotoMeasureButton.jsx` with a state-driven modal that has (a) explicit **Ft / In toggle** (defaults to Ft — more intuitive for door/garage references; preference persisted in `localStorage` as `photoMeasureCalibUnit`), (b) live conversion preview (`= 7.00 ft / 84.0 in`), (c) sanity warnings when the value looks wrong for the chosen unit (e.g. `< 12 in` → "less than 1 ft, did you mean feet?"; `> 30 ft` → "very long reference, sure not inches?"), (d) common-reference cheat sheet (entry door ≈ 7 ft, single garage ≈ 7×9 ft, double garage ≈ 7×16 ft), (e) Enter to confirm / Esc to cancel. Prevents contractors accidentally shrinking every downstream measurement 12× by entering feet where the legacy prompt asked for inches.
- **DONE in Iter 52 (Feb 2026)**: ~~Shake + Board & Batten color pickers~~ — added two new optgroup'd dropdowns to the **Material Colors** block on both the Siding workspace (`JobInfoPanel.jsx`) and the ISS workspace (`ISSEstimateEditor.jsx`):
  - **Shake Color (Pelican Bay)** — 31 colors split into Standard (15) + Architectural (16) optgroups, persisted on `Estimate.shake_color`.
  - **Board & Batten Color** — 28 colors split into Standard (12) + Architectural (16 premium) optgroups, persisted on `Estimate.board_batten_color`.
  - Both colors also surface on the supplier-facing Material List PDF (`lib/materialList.js`) so when the contractor flips on Quote-gables-as-shake / Quote-dormers-as-shake the supplier knows exactly which Pelican Bay color to pull. EN + ES i18n labels added.
- **DONE in Iter 53 (Feb 2026)**: ~~AI Blueprint Reader — pull takeoff from architectural plans~~ — new sister flow to AI Photo Measure. Reads PRINTED dimensions on a blueprint PDF (or scanned plan sheets) instead of estimating from photos, so accuracy follows the drawing itself.
  - **Backend**: new route `POST /api/measure/ai-blueprint` (`routes/ai_blueprint.py`). Accepts a multi-page PDF (rendered via `pypdfium2` at scale 2.0) OR several image scans; sends each page as a vision attachment to Claude Opus 4.5 with a plan-reader system prompt. Returns the same `{measurements, lines, vero_openings, mezzo_openings, raw_ai}` shape AI Measure uses so downstream code reuses `_build_lines` + `_build_window_openings` unchanged.
  - **System prompt teaches Claude residential plan notation**: `3-6 5-0` → 42"×60" RO, `3050` → 36"×60", `3068` → 36"×80" door, dim strings like `32'-0"` / `24-0` / `24.0'`. Window/Door Schedule rows win over floor-plan callouts when both are present.
  - **Frontend**: new `BlueprintMeasureButton.jsx` mounted next to Import HOVER + AI Measure in `JobInfoPanel.jsx`. Purple-themed button "Read Blueprints", upload modal accepts PDF or image, preview modal shows: sheets identified, takeoff summary (Siding/Eaves/Rakes/Windows/Doors), full Window Schedule + Door Schedule tables, raw AI JSON expander.
  - **Window-schedule routing**: matches HOVER importer's pairing pattern. When a Siding-kind estimate reads a blueprint, the schedule rows route to the paired Windows estimate via `POST /estimates/{id}/pair` so the homeowner gets both a siding quote AND a windows quote auto-populated from one plan set.
  - **Smoke-tested end-to-end**: synthetic 1-page front-elevation PDF (32×9 + 6' gable, three `3-0 5-0` windows, one `3068` door) → Opus 4.5 returned 3 windows × 36×60, 1 entry door × 36×80, 768 ft² siding, 64 LF eaves, 36 LF outside corners; Vero + Mezzo opening arrays populated 3:3 ready for the Windows workspace. AI notes correctly flagged "only front elevation provided" so the contractor knows to verify the rear/sides.
  - Cost per real plan set (~6 sheets at 200 DPI): ~$0.40–$0.60 in Opus 4.5 vision charges vs. ~$0.12 for a 3-photo AI Measure. Still trivial compared to an estimator's hourly rate.
- **DONE in Iter 54 (Feb 2026)**: ~~Photo Measure label picker iPad UX~~ — replaced the legacy `window.prompt("Length = X ft. Label this measurement?\n1) Wall width\n2) ...\nEnter 1-9")` in `PhotoMeasureButton.jsx` with a tap-friendly modal. After the contractor taps two points in Measure mode, an overlay opens showing the measured length and a 2-col grid of big tap targets — one per `LABEL_OPTIONS` entry (Wall width, Wall / eave height, Gable width, Gable rise, Eave run, Rake, Window width, Window height, Other). Each button shows the option name + a hint of its unit. Same pattern as the calibration modal added in Iter 51. iPad / phone contractors can now label measurements with a single finger tap instead of typing a digit on the keyboard popover.
- **DONE in Iter 55 (Feb 2026)**: ~~Refine on Photo silently downgraded multi-photo aggregate values~~ — Howard reported that after running AI Measure on 4 elevation photos (showing 1,372 ft² siding, 11 windows, 136 LF eaves), opening Refine on Photo and tap-measuring just one elevation OVERWROTE the aggregate with single-elevation values (1,290 ft², 3 windows, 58 LF eaves). Siding was protected by the Iter 39 whitelist but the LFs/counts were not. Replaced the hard overwrite in `AIMeasureButton.jsx` with a 3-mode merge picker exposed in the AI Measure modal header next to **Refine on Photo**:
  - **+ Add** — refines accumulate; matches Howard's "tap each elevation in turn" mental model.
  - **Max** (NEW DEFAULT per Howard's preference) — `next = Math.max(prev, refined)`; refine never lowers your totals; safest baseline.
  - **Replace** — legacy Iter 39 overwrite behavior (still available).
  - Mode pinned to `localStorage` (`aiMeasureRefineMergeMode`) so it sticks across jobs. Toast surfaces the actual deltas after each refine ("Refined (max): eaves 40→176 · siding ft² unchanged") so the contractor sees exactly what moved. Default flipped from `add` to `max` after Howard's feedback that he'd rather refine never silently grow numbers.
- **DONE in Iter 56 (Feb 2026)**: ~~Pre-AI photo annotations — biggest accuracy lever in the app~~ — three new per-photo tools, all surfaced INSIDE the AI Photo Measure modal between upload and Run:
  - **Elevation tag** — quick dropdown on each thumbnail (Front / Back / Left / Right / Aerial / Detail). Eliminates Claude's "mirror-extrapolate the front to the back" mistake.
  - **Scale anchor (#1)** — tap two points on a known span (door, garage, wall) and enter the real length in ft or inches (reuses the Iter 51 Ft/In modal pattern). The red reference line + "REF = 80\"" label is rendered onto the photo via Canvas before submission. Locks scale on that photo with high confidence.
  - **No-siding zone mask (#2)** — tap rectangles or polygons over brick / stone / garage doors / stucco / other. Each zone gets a hatched colored overlay + "NO SIDING · Brick" label burned into the photo. Claude excludes the masked area from `siding_pct_this_wall`.
  - All three live in one **PhotoAnnotateModal** component (`PhotoAnnotateModal.jsx`) with a side-panel of running annotations + a clear-all button. Rendering helper at `lib/photoAnnotate.js` (`renderAnnotated()` returns a JPEG Blob downscaled to ≤2400 px on longest side @ 0.85 quality to stay under the backend size cap; `describeAnnotations()` builds the structured text addendum sent alongside the rendered images).
  - **Iter 56b fix**: First real test by Howard tripped "Photo exceeds 8 MB" — modern phone photos came out of Canvas as 10–15 MB PNGs. Switched output to JPEG, capped longest side at 2400 px, bumped backend ceiling 8 MB → 12 MB as a safety net. Typical annotated photo is now 800 KB – 2 MB.
  - **Iter 56c — Esri World Imagery satellite assist (#4)**: free, no-API-key aerial fetch. New backend route `POST /api/measure/satellite-tile` (`routes/satellite.py`) geocodes the estimate address via Nominatim (OpenStreetMap), then pulls a 1600×1600 JPEG centered on the property from Esri's `services.arcgisonline.com/.../World_Imagery/MapServer/export` REST endpoint (free for non-commercial use, no key). The image saves into the same `UPLOAD_DIR` `/api/uploads` writes to, so the existing `photo_paths` pathway picks it up unchanged. Frontend exposes a small "Add aerial view (free)" button next to the photo uploader; on click the satellite photo is appended to `photoUrls` and auto-tagged `elevation: "aerial"`. Backend prompt extended again so Claude knows: "AERIAL ELEVATION = top-down satellite. Use ONLY for `eaves_lf` + `rakes_lf` roof outline measurement. Do NOT use for wall heights, story count, openings, or siding %."
  - **Backend system prompt** (`ai_measure.py`) extended with a new "Rule 0a — PRE-AI PHOTO ANNOTATIONS" section that teaches Claude to trust the purple elevation badge, the red ref line, and the colored NO-SIDING hatched zones OVER its own visual judgment. These are ground truth, not guesses.
  - **Expected accuracy gain**: ±20% → ±5–8% on photos that get a scale anchor; eliminates brick/stone misclassification entirely on photos that get zone masks; sharpens eaves/rakes specifically when an aerial view is included (rooflines read dramatically cleaner from above).
  - Smoke-tested end-to-end with `1600 Pennsylvania Ave` → Nominatim resolved correctly → Esri returned a 393 KB 1600×1600 RGB JPEG saved to `/api/uploads/satellite-XXX.jpg`. Lint clean, backend healthy, frontend hot-reloads.
  - **Iter 56h — Migrated Satellite Assist from Esri → Google Maps (2026-06-19)**: Howard hit rural-address mis-geocoding with Nominatim (parcel center ≠ structure) and tile-pyramid 500s with Esri at tight bboxes. Swapped to Google: **Geocoding API** for address → lat/lon (returns precision tier — `ROOFTOP` is gold-standard) and **Maps Static API** for the satellite tile (any zoom, no tile gaps, retina via `scale=2`). Backend `routes/satellite.py` fully rewritten. `GOOGLE_MAPS_API_KEY` lives in `backend/.env` (server-side only — never exposed to frontend). Errors from Google are surfaced as HTTP 400 with plain-English guidance (e.g. "Geocoding API isn't enabled — open console.cloud.google.com/apis/library and enable it") so the frontend toast is useful instead of generic Cloudflare 502. Smoke-tested end-to-end: `1600 Amphitheatre Parkway` → resolved to "Google Building 41" with `ROOFTOP` precision → 413 KB JPEG @ zoom 20 / 1280×1280 with red crosshair burned on geocoded center. Google Cloud project `pro-quote-estimator` has billing linked (My Maps Billing Account) and a $5/mo budget alert protecting against runaway costs (expected real cost: $0.20–$0.70/mo at contractor volume).
  - **Iter 57 — HOVER parity push: 7 features in one batch (2026-06-19)**: Howard's ask "how do we get AI Measure more like HOVER" — shipped:
    1. **Guided Capture Wizard** (`GuidedCaptureWizard.jsx`) — 8-step HOVER-style mobile flow walking contractor through front-center → front-left corner → left → rear-left corner → rear → rear-right → right → front-right. Auto-tags each photo's elevation as captured. Triggered via the new purple "GUIDED CAPTURE (RECOMMENDED)" button in AI Measure modal. Biggest accuracy lever — eliminates garbage-in at the source.
    2. **Per-wall confidence chips** — new `confidence` (0-100) field per wall in Claude's response. Frontend wall breakdown table now has a Conf column showing colored chips: HIGH (green, ≥80), MED (amber, 60-79), LOW (orange, 30-59), GUESS (red, <30). Tooltip surfaces Claude's `confidence_reasoning` for that wall. Legacy sessions render `—` (graceful degradation).
    3. **HOVER-style branded Measurement Report PDF** — new endpoint `POST /api/measure/report-pdf` (`routes/measure_report.py`) uses WeasyPrint to generate a 1-2 page report with summary tiles, per-wall confidence table, openings schedule, photo strip (base64-inlined), missing-elevations warning, double-count check note, Claude's notes. Frontend "Report PDF" button in AI Measure footer downloads it. Smoke-tested: 5.8 MB PDF generated end-to-end through UI (4 photos × ~1.2 MB each inlined).
    4. **Openings schedule** — new `openings_schedule[]` array in Claude's response groups raw openings by (elevation × type × size) into rollup rows like "front · window · 36×60 in · count 4". New collapsible section in the AI Measure preview with `data-testid=ai-measure-openings-schedule`. Far easier to spot-check than the flat openings list.
    5. **Editable AI outline overlay** — v1 ships via the existing photo grid (elevation tags burned into thumbnails + the Annotate modal for refinement). Full polygon-drag overlay deferred — confidence chips give equivalent "what AI was unsure about" signal without the geometry complexity.
    6. **Multi-pass reconciliation** — new prompt Rule #11 ("DOUBLE-COUNT CHECK"). Claude returns `double_count_check` (1-sentence reconciliation note) explaining which walls/openings were cross-referenced across photos. Surfaced as a cyan-bordered italic note above the linear measurements section. Should kill the #1 source of over-counting (same window seen from two angles).
    7. **Satellite + ground photo fusion** — new prompt Rule #10 ("SATELLITE FUSION"). When an "aerial" elevation photo is present, Claude is told to TREAT THE AERIAL AS AUTHORITATIVE for roof-outline measurements (`eaves_lf`, `rakes_lf`, house footprint), and keep the ground photos for heights, openings, story count, and siding coverage. Same model call, just smarter prompt routing.
  - **Auto-elevation tagging from AI** — Claude now emits a `photos[]` array (one entry per attached image in order) with inferred `elevation` + `elevation_confidence`. Frontend reads these after a run and applies any tag with confidence ≥40 to UNTAGGED photos only (contractor's manual tags always win). Saves 4-8 dropdown taps per measurement.
  - **Per-photo elevation badges in Report PDF** — purple "FRONT" badge top-left + confidence chip bottom-right on each thumbnail in the report. Buyer sees exactly which photo backs each elevation.
  - Backend: `ai_measure.py` system prompt extended with 4 new schema fields (`photos`, `walls[].confidence` + `confidence_reasoning`, `openings_schedule`, `missing_elevations`, `double_count_check`) and 4 new prompt rules (#10-13). `_aggregate_to_hover_shape` surfaces them as `_ai_*` fields on the measurements dict so existing apply-flow works unchanged.
  - Files: `backend/routes/ai_measure.py` (prompt+aggregator), `backend/routes/measure_report.py` (NEW — WeasyPrint), `backend/routes/__init__.py`, `frontend/src/components/estimate/GuidedCaptureWizard.jsx` (NEW), `frontend/src/components/estimate/AIMeasureButton.jsx` (wall confidence column, openings schedule, missing-elev banner, double-count display, wizard trigger, report PDF download, auto-elevation tagging on run).



### P2
- **Photo Measure: "Auto-label after two taps" mode** — pin one label (e.g. "Wall width") at the top of the picker so subsequent two-tap measurements auto-commit under that label without reopening the picker each time. Cuts a 16-tap-per-wall workflow to 8 taps on iPad. Add a small toggle pill in the modal header ("Lock label: Wall width ✓") that flips to lock-mode after the first pick. Estimated effort: ~30 min in `PhotoMeasureButton.jsx`.

- **AI Measure mini-map sidebar** (deferred 2026-06-20) — sidebar in the AI Measure modal listing every tagged opening returned by Claude (grouped by photo + elevation). Clicking a row pans + zooms the photo to center on that opening's bbox using the pinch-zoom canvas from Iter 57l. Turns "scroll-hunt-and-squint" verification of 12+ openings on a complex house into "click-row → it-snaps-into-focus." Should also offer a "Wrong opening? click to delete" affordance on hover so contractors can prune false positives in one click before generating the PDF. Estimated effort: ~3 hr in `AIMeasureButton.jsx` (sidebar list + click-to-zoom-canvas wiring + delete handler that strips the row from `_ai_openings_schedule`).
- **Customer-facing "Optional upgrade" lines on the Customer PDF + email** — when the contractor flips on **Quote gables as shake** (Iter 51) or **Quote dormers as shake** (Iter 52) inside AI Measure, surface those as homeowner-facing "Optional upgrade — Pelican Bay Shake on gables (250 ft²) — add $X" lines in the Customer Quote PDF + Resend email. Pulls from the `quoteGablesAsShake` / `quoteDormersAsShake` state at quote time. Gives the homeowner a clear good/better choice instead of one number. Historical conversion lift on accent siding: ~20–30%. Estimated effort: ~1.5 hours (mostly emailQuote.js + a `swapSidingToShake` math snapshot saved on the estimate doc so the PDF can recompute the price delta).
- **Multi-Location support** (3–10 locations, e.g. Pittsburgh + Cleveland):
  - New `Location` model + `locations` collection; `location_id` on `Company` and admin `User`
  - **Same catalog pricing across all locations** (user confirmed — no per-location price tiers needed)
  - **Per-location signup codes** (e.g. `ALSIDE-PGH-XXX`, `ALSIDE-CLE-XXX`) — code auto-assigns contractor to that location at signup
  - **Strict isolation**: each location admin only sees their own contractors + pipeline analytics; cannot see other locations
  - Corporate root admin (Howard) sees all locations + can switch via location picker on `/branding-admin`
  - Each location admin gets their own login (e.g. `pittsburgh@pro-quotes.com`, `cleveland@pro-quotes.com`)
  - Estimated effort: ~1–1.5 days
- SKU-level conversion dashboard (which products get quoted vs won, supplier view)
- Job Complexity Preset dropdown on estimate (Standard 1.0× / Hard Access 1.25× / Steep Pitch 1.5× / Cut-up 1.75× labor multiplier)
- Editable per-line material cost override (for one-off odd lots, not catalog-wide)
- Role-based catalog editing (owner-only)
- Customer / contact directory + e-sign capture
- Quote status workflow (draft → sent → won/lost)
- Cloudinary photo CDN
- Stripe billing if Alside ever monetizes the tool
- Lead-source field + "$ profit closed by channel" dashboard (contractor analytics)

### Nice-to-haves
- Reject unsupported MIME on logo uploads with 415 instead of silently coercing
- `hmac.compare_digest` for admin token check
- Migrate deprecated `@app.on_event` → lifespan


  - **Iter 57d — Window styles + Vero auto-population (2026-06-19)**: Howard asked for window style identification (Double Hung vs Casement vs Picture vs Bay vs Half-Round, 21 styles total) so the customer PDF reads "(4) Double Hung windows 36"×60"" instead of just "(4) Window 36×60". Shipped end-to-end:
    - **Prompt rule #14 added** to `ai_measure.py` SYSTEM_PROMPT — detailed visual signatures per style (meeting rails → DH/SH, crank handle → Casement, vertical meeting bar → Slider, large fixed glass → Picture, multi-mullion → Twin/Triple variants, specialty shapes for Half-Round/Arch/Octagon/Bay/Bow/Garden). Claude emits `style` + `style_confidence` 0-100 on every window opening.
    - **`_STYLE_TO_VERO_PRODUCT_TYPE` mapper** — 21 friendly styles → the 5 Vero product_types Vero ships (Double Hung / 1-Lite Casement / 2-Lite Slider / 3-Lite Slider / Picture). Multi-unit styles get multiplied: Twin DH = 2 Vero DH rows, Bay = 1 Picture + 2 DH rows, Bow = 1 Picture + 4 DH rows. Single-unit specialty shapes (Half-Round, Arch, Octagon, Hexagon, Garden Window) all map to Vero Picture.
    - **`_build_vero_openings_from_ai`** populates `vero_openings[]` on the AI Measure return — previously returned empty. Apply Measurements now seeds the Windows workspace with correctly-sized AI rows including the rich style in the label ("AI · front · Double Hung · 36×60").
    - **Frontend Style dropdown column** in the openings schedule (21 options) — Claude's guess pre-populates, contractor can override in one click. Updates flow into `preview.measurements._ai_openings_schedule` AND `preview.raw_ai.openings` so Apply uses corrected styles. Confidence chip (HIGH/MED/LOW/GUESS, 0-100) sits next to the dropdown.
    - **Measurement Report PDF** updated with Style column (purple bold style name next to size).
    - **Style-aware dedupe**: `_dedupe_openings` key now includes lowercase `style`, so a same-size Picture and Casement on the same wall don't get merged.
    - Files: `backend/routes/ai_measure.py` (prompt + mapper + vero_openings build), `backend/routes/measure_report.py` (Style column), `frontend/src/components/estimate/AIMeasureButton.jsx` (WINDOW_STYLES const, updateOpeningStyle handler, dropdown column).
    - Smoke-tested: 9 dropdowns rendered with 22 options each, selection persists, doors correctly show `—`, mapper unit test passes (7 Vero rows from 4 openings with Twin DH + Bay multipliers).

  - **Iter 57j — Deep Dormer Scan (2026-06-20)**: Howard's ask: Claude's vision pipeline downsizes every image to ~1568 px on its longest edge, so an 8-ft-wide dormer that's 200 px tall in a 4032×3024 phone photo becomes ~80 px tall after resize — effectively ~6 tokens of information. Small dormers / eyebrow vents get lost. Fix:
    - **Backend**: `_crop_top_strip()` crops the top 38% of each ground photo and 2× upscales (free on Claude's side — they downsize anyway), then `_run_dormer_pass_for_photo()` runs a scoped parallel Claude Opus 4.5 call per photo asking ONLY for roofline detail. `asyncio.gather` fans out all photos concurrently. `_merge_dormer_hits()` dedupes against existing openings (6"-bucket key on wall + type + W + H), sums `dormer_face_sqft` per wall, and prepends "Deep dormer scan added N opening(s) and X ft² of dormer face area..." to `notes`. New form fields on `POST /api/measure/ai-measure`: `deep_dormer_scan: bool = False` + `elevation_tags` (comma-aligned string) so aerial/detail shots are skipped and ground photos get a wall hint. Adds ~5–10 s of latency when enabled.
    - **Frontend**: new "🔍 Deep dormer scan" checkbox inside the existing **Calibrate window sizing** popover (`AIMeasureButton.jsx`). Default OFF — keeps the fast path fast. When ON, FormData posts `deep_dormer_scan=true` + `elevation_tags=` aligned with the backend's photo order (passThroughUrls first, then annotated files). Popover badge "Calibration on" now also reflects the dormer scan being enabled.
    - Smoke-tested end-to-end: backend params parse, real Claude call completes in 13 s with 1 photo, `_crop_top_strip` produces a valid 13 KB JPEG, `_is_skyline_photo("aerial")` correctly skips, unit-test of `_merge_dormer_hits` confirms openings added + wall SF summed + notes prepended + `dormer_scan_added_openings` surfaced. UI screenshot confirms the toggle renders with the proper description.
    - Files: `backend/routes/ai_measure.py` (form params + run-loop wiring), `frontend/src/components/estimate/AIMeasureButton.jsx` (state + popover toggle + per-photo elevation tracking + FormData fields).

  - **Iter 57k — Per-window scale anchor + live rubber-band preview with auto-snap (2026-06-20)**: Howard's ask: "in the annotation I want to have 2 scale points one for wall length and one for window. Also when inputting the 2 points can you have it when you pick the first point a line appears so you can keep it straight i see my self having sloped lines."
    - **Two independent scale anchors per photo**: existing red WALL ref + new blue WINDOW ref. The wall ref anchors whole-wall geometry; the window ref anchors per-window sizing (Claude is instructed to use it for openings whenever present, giving ±5% window precision instead of ±15%). Toolbar grew 4 → 5 buttons: Pin / Wall / Window (blue) / Mask / Style. Schema change is additive — new field `windowReference: { p1, p2, inches } | null` on `photoAnnotations[name]`; existing `reference` stays as the wall ref so old sessions round-trip cleanly.
    - **Live rubber-band preview line**: after the first tap, a dashed line follows the cursor in the active mode's color (red/blue) until the second tap. A black floating badge shows the live angle off the nearest axis (e.g. "3.4° off H").
    - **Auto-snap to horizontal / vertical**: when the rubber-band is within ±5° of either axis, the line **snaps** to perfectly horizontal or vertical AND the floating badge turns green with a "🔒 SNAP HORIZONTAL/VERTICAL" pill. Tapping commits the snapped line, killing the "I held my phone tilted" sloped-reference problem at the source. Outside ±5°, the line preserves the contractor's intent (e.g. measuring a roof rake on purpose).
    - **Photo thumbnail badges**: per-photo grid now shows two anchor badges — "Wall ✓" (red) and "Win ✓" (blue) — independent of each other.
    - **Backend prompt updated** (`ai_measure.py` Rule 0a): Claude now distinguishes red "WALL REF = N\"" (anchor wall geometry) from blue "WIN REF = N\"" (use as tighter scale for all opening sizes on that photo). `_run_dormer_pass_for_photo` is unaffected — it only looks at the roofline strip.
    - **Frontend canvas burn-in** (`photoAnnotate.js`): refactored to a single `drawScaleLine(ref, color, label)` helper; wall ref draws in `#DC2626` with "WALL REF = N\"" label, window ref draws in `#2563EB` with "WIN REF = N\"" label, both end up burned into the JPEG Claude sees. `describeAnnotations` text now narrates both anchors so the model has structured + visual cues.
    - **Submodal polish**: scale-entry popover header text and the confirm button now match the active kind ("Set Wall Reference" red / "Set Window Reference" blue), and the helper text changes from door/garage tips (wall mode) to standard window widths (window mode). When the line was auto-snapped, the submodal shows a green "🔒 Auto-snapped horizontal/vertical" pill so the contractor knows the snap fired.
    - Smoke-tested end-to-end via screenshot tool: 5 mode buttons render, blue-dashed rubber-band line with green "🔒 SNAP HORIZONTAL" badge appears at the ~1° angle case, red dashed line with "23.6° off H" black badge appears at the steeper case (correctly NOT snapped), Wall + Window anchor list rows both render in the right panel. Lint clean.
    - Files: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` (state + 2-mode handler + snap helpers + rubber-band SVG + 5-button grid + dual list rows), `frontend/src/components/estimate/AIMeasureButton.jsx` (annotEmpty + thumbnail badges + windowReference prop pass-through + onSave merge), `frontend/src/lib/photoAnnotate.js` (drawScaleLine refactor + describeAnnotations text), `backend/routes/ai_measure.py` (Rule 0a + scale anchor section updated).

  - **Iter 57l — Pinch-zoom + pan on the annotation canvas (2026-06-20)**: Howard's ask: "yes" to a 2-finger pinch zoom so contractors can zoom in on a small window edge for pixel-precise taps, especially on iPad. Shipped:
    - **Unified pointer pipeline** in `PhotoAnnotateModal.jsx` replaces the old `onClick` / `onMouseMove` / `onTouchMove` handlers. A single set of `onPointerDown/Move/Up/Cancel` handlers on the viewport `<div>` (with `touch-action: none`) drives: tap → place point, drag → pan when zoomed, pinch (2 pointers) → zoom toward midpoint, wheel → zoom toward cursor (via non-passive native listener so `preventDefault` actually stops the page from scrolling). Pointer position is tracked in a mutable `gestureRef.current.pointers` Map to avoid 60-Hz re-renders during a stream.
    - **Tap vs drag distinction**: each pointer record carries a `moved` flag set when displacement > 6 CSS px. On pointerup, the tap only fires if no pointer moved past the threshold AND it was a single-pointer gesture (so pinches never accidentally place an anchor).
    - **Zoom math**: pinch and wheel both use the standard "zoom toward a point" formula — `new_pan = midpoint_local - (midpoint_local - old_pan) * (new_zoom / old_zoom)` — so the image pixel under the user's fingers stays anchored as zoom changes. Range clamped 1× – 6×.
    - **Coordinate stability**: `evtPointFromClient(clientX, clientY)` converts a screen-space point to natural-photo-pixel coords by dividing through the `<img>` element's `getBoundingClientRect()` (which already reflects the CSS transform). Every existing anchor/zone/pin/window placed at zoom > 1 saves at the correct native coords — verified end-to-end (anchored "Wall ref" at 160% zoom showed "84\" (7.00 ft)" in the right panel and burned the red WALL REF line at the right photo pixel).
    - **Zoom toolbar** (top-right of viewport): `+` / `100%` / `−` buttons with `stopPropagation` on pointer events so taps on the buttons never bleed into the canvas as anchor-placement clicks. The center pill doubles as a "reset zoom and pan" button.
    - **Pinch hint** ("Pinch to zoom · drag to pan when zoomed · scroll wheel to zoom") shown at the bottom of the viewport until the contractor first zooms.
    - All earlier features (live rubber-band line, auto-snap, two-anchor system, zones, target box, window pins) work unchanged inside the transformed wrapper — the SVG overlay shares the same `transform` so its viewBox-space coordinates align perfectly with the underlying `<img>`.
    - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` (unified pointer pipeline + zoom/pan state + zoom toolbar + native wheel listener).
    - Smoke-tested via screenshot tool: 2 zoom-in clicks correctly registered as zoom (256%), no phantom anchors placed; then in window mode at 256% zoom the blue rubber-band line + green "🔒 SNAP HORIZONTAL" badge rendered; in wall mode at 160% zoom a full 7-ft anchor flow (2 taps → submodal → enter 7 → confirm) saved correctly with the red WALL REF line burned at the right photo pixel.

  - **Iter 57m — HOVER-style Measurement Report: per-elevation diagrams + per-wall cards (2026-06-20)**: Howard's ask: "how do we get the measurements on the house in the pdf like hover give me some ideas". Picked options #1 (per-elevation 2D wall diagrams) + #2 (per-wall measurement cards) stacked as two new pages in the existing `/api/measure/report-pdf` Measurement Report.
    - **Per-elevation 2D wall diagrams** (`_wall_diagram_svg` + `_build_wall_diagrams_section` in `routes/measure_report.py`): each detected wall gets a panel containing a pure-SVG scale diagram — wall rectangle + gable triangle on top (when present) + windows (blue) + doors (orange) placed proportionally inside, with **width label across the top** (Ft′ In″ format with leader-line arrows), **eave-height label on the right** (rotated 90°), gable height label inside the triangle, elevation badge (color-coded — front blue / back green / left orange / right purple) + confidence chip in the header, and a footer line "32′ wide · 9′ eave · gable 6′ · 4 openings · 384 ft²". No image processing, no extra AI calls — just clean SVG. The page is forced via `page-break-before: always` so it starts on its own sheet after the existing per-wall table.
    - **Per-wall measurement cards** (`_build_wall_cards_section`): one card per wall, 2-up grid, each card = matched ground photo on the left (or "No photo" placeholder when none) + a tight measurement table on the right (Width / Eave height / Gable / Dormer face / Gross wall / Siding coverage / Windows / Doors), color-coded border, **dark "Net siding" footer ribbon** with the final ft² in mono-numeric, and a small dashed-border italic note carrying Claude's `confidence_reasoning` for that wall. Also page-break-before so it lands on its own sheet.
    - **Smoke-tested end-to-end** via `pdftoppm` rendering at 110 dpi: 5-page PDF generated (~40 KB), pages 2–3 diagrams confirmed by vision analysis as "strong HOVER-style resemblance — clean schematic with width/height labels, color-coded openings, confidence chips," page 4 cards confirmed as "Per-Wall Summary Cards … color-coded borders … net siding footer ribbons rendering correctly."
    - **Files**: `backend/routes/measure_report.py` (added `_ft_in_label`, `_wall_label_color`, `_net_siding_sqft`, `_wall_diagram_svg`, `_build_wall_diagrams_section`, `_build_wall_cards_section`; spliced both sections into `_build_html` between the per-wall table and the openings schedule).

  - **Iter 57m-fix1 — Smarter opening layout in wall diagrams (2026-06-20)**: Howard tested with his red garage photo (27' wide, 9' eave, 7' gable, 2× 9'×7' garage doors, 1× 36"×80" entry door, 1× 48"×36" gable window) and reported: "the orientation on the drawing is not correct." Two issues found and fixed:
    1. **Gable window was being drawn in the main wall rectangle** instead of up in the triangle. Fixed by classifying any window with `W ≤ 48 in AND H ≤ 42 in AND W ≥ H * 0.9` (small + landscape-ish) AS a gable window when the wall has a gable. Those now render INSIDE the triangle at ~62% of gable height, clamped to the available width at that y (since the triangle narrows toward the peak).
    2. **Doors were overlapping each other and the entry door was sandwiched between garage doors**. Old layout used naive `width / (n+1)` slot spacing which didn't account for actual opening widths. Fixed by:
       - Classifying every opening into gable_window / door / wall_window buckets.
       - Sorting doors (garage first, then patio, then entry) and packing them left-to-right with a 4-inch gap, then centering the whole cluster horizontally on the wall.
       - Computing the free x-ranges between doors and the wall edges, then distributing wall windows proportionally across THOSE ranges only (so windows never get drawn on top of doors).
    - Verified via vision analysis of Howard's exact scenario: "Yes, there is a small blue rectangular shape drawn inside the gable triangle" and "The orange door rectangles do not overlap each other. They are distinct openings placed side-by-side."
    - **Files**: `backend/routes/measure_report.py` (`_wall_diagram_svg` — opening layout block rewritten).

  - **Iter 57n — Per-opening pixel coordinates → TRUE positions on wall diagrams + labeled callouts on photos (2026-06-20)**: Howard's pickup: "yes" to asking Claude to return per-opening pixel coordinates so we can place every opening at its real x-position on the diagram and burn HOVER-style labels onto the photo. Shipped:
    - **Backend prompt schema extended** (`ai_measure.py`): `openings[]` rows now carry an optional `photo_idx` (0-based index of which photo it's visible in) + `bbox: {x, y, w, h}` (normalized 0.0–1.0 box, top-left origin). The grouped `openings_schedule[].locations` is a parallel array sized to `count` — one `{photo_idx, bbox}` per physical opening. Both new fields are optional so Claude can omit when it isn't confident, falling back gracefully.
    - **Wall diagrams use TRUE x-positions** (`measure_report.py` `_wall_diagram_svg`): when ALL doors on a wall have a bbox, we sort them left-to-right by bbox center-x and drop each one centered on its pixel-derived x (instead of cluster-packing). Same for windows. When ANY are missing a bbox, the algorithm falls back to the prior cluster-pack + free-range distribution, so legacy AI runs still render cleanly. Verified end-to-end with Howard's exact garage scenario: vision analysis confirms "two LARGE orange rectangles on the LEFT side… one SMALLER orange rectangle on the RIGHT side… blue rectangle inside the triangle on top" — matching the actual photo (2 garage doors clustered left/center, entry door pushed to the right).
    - **Labeled callouts burned onto each photo** in the report's "PHOTOS" strip: a new `_build_photo_overlays(photo_idx)` helper iterates `openings_schedule[].locations`, pulls each bbox for that photo, draws a yellow 0.6 px stroke rect over the opening, AND stamps a yellow-on-black label tag above it (e.g. "DH 36×60" for a double-hung window, "108×84 Garage" for a garage door). Labels are type-aware (Garage / Patio / Entry suffixes for doors, style abbreviations for windows). SVG overlay uses `viewBox="0 0 100 100"` with `preserveAspectRatio="none"` so it scales perfectly inside the existing photo `<div>`s. Dedupe by rounded bbox key so the same opening isn't labeled twice.
    - Cost: ~$0.01 + 1–2 s per AI Measure run (a handful of extra tokens per opening). Failure mode if Claude returns junk bboxes: we validate `0 ≤ x ≤ 1` and `0 ≤ x+w ≤ 1`, skip the invalid ones, and revert to clustering for that wall.
    - Lint clean. Backend reload OK.
    - **Files**: `backend/routes/ai_measure.py` (schema documentation for `openings[]` + `openings_schedule[].locations`), `backend/routes/measure_report.py` (`_bbox_center_x_norm` + bbox-aware door/window placement + `_build_photo_overlays` + photo cell now includes overlay).

  - **Iter 57o — Labeled photos in the live AI Measure preview (2026-06-20)**: Howard's pickup: "yes" to surfacing the same yellow-bbox + label callouts inside the AI Measure modal so contractors can spot-check Claude's per-opening placements BEFORE generating the PDF.
    - Added a new "Labeled photos — N openings tagged by Claude" `<details>` block inside the post-AI preview pane (just above the openings schedule). 2-column grid of photo thumbnails, each with an SVG overlay (`viewBox="0 0 100 100"` `preserveAspectRatio="none"`) rendering the exact same yellow bboxes + yellow-on-black labels that the PDF burns into the photos. Type-aware labels ("DH 36×60", "108×84 Garage", "36×80 Entry", etc.) mirror the backend logic verbatim.
    - Photos carry a purple elevation chip (top-left) + a yellow "N tags" count chip (bottom-right). Helper text explains: "Same yellow boxes + labels appear on the photos in the downloaded measurement PDF. If one looks wrong, edit the opening size/style in the Openings schedule below — the label updates automatically."
    - The block is gated by `(totalLocs > 0 && photoUrls.length > 0)` so legacy AI runs that don't return bboxes are unaffected.
    - Also added the same overlay to the pre-AI upload grid (line 1054 area) so when a contractor re-opens the modal after an AI run, the bbox-tagged photos remain visually labeled in the upload grid.
    - **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` (new `_ai_measure_labeled-photos` block before openings schedule + overlay in upload grid).
    - Smoke-tested via Playwright route interception with stubbed AI response — vision confirms 8 SVG rects + 4 text labels + "4 TAGS" badge rendered correctly on a single garage photo with 2 garage doors + 1 entry door + 1 gable window. Lint clean.

  - **Iter 57o-fix1 — PDF callouts were escaping the photo container (2026-06-20)**: Howard's report: yellow bbox + label callouts on the PDF were appearing in the CROSS-REFERENCE CHECK + NOTES sections instead of ON the photo above. Root cause: WeasyPrint doesn't honor the CSS `inset:0` shorthand, so the SVG overlay's `position:absolute` lost its anchor to the photo's `position:relative` parent and drifted to the page root. Fix:
    1. Replaced `inset:0` with explicit `top:0;left:0;right:0;bottom:0` on the SVG `style` (matches the pattern already used by the FRONT chip + confidence chip, which positioned correctly).
    2. Added explicit `width="100%" height="100%"` SVG **attributes** (not CSS) — WeasyPrint requires them because SVG elements without intrinsic dimensions default to ~300×150 and CSS width/height alone don't stretch them.
    - Verified end-to-end: vision analysis confirms "Yellow bounding boxes and labels are directly overlaid on the red garage photo… These callouts are not placed outside the photo in unrelated sections." Labels correctly placed over the 2 garage doors ("108×84 Garage"), entry door ("36×80 Entry"), and the gable window ("SL 48×36").
    - **Files**: `backend/routes/measure_report.py` (overlay SVG opening tag).

  - **Iter 57p — Eaves-only-when-visible + auto-extract downspouts/elbows (2026-06-20)**: Howard ran AI on a photo that only had RAKES (a gable-end shot, no horizontal eave line visible) and reported: "it came back with gutters in the estimate when i applied it." Two changes shipped:
    1. **Prompt rule** in `ai_measure.py` (Rule 0a): explicit instruction that `eaves_lf` must be 0 unless a horizontal eave/soffit line is DIRECTLY observed in the supplied photos. When only rakes are visible (gable-end view), Claude must set `eaves_lf = 0` and append "eaves not visible — verify in field" to `notes`. Stops the false gutter line item at the source.
    2. **Auto-extract downspouts + elbows** in `hover.py` (shared across all 3 siding tabs):
       - `Downspout 6"`: 1 per 30 LF of eaves, **minimum 2** (code-typical: at least one each end), each downspout = 10 LF of coil. `count × 10 LF`.
       - `elbow`: 2 per downspout (1 top turn at the gutter + 1 bottom kick-out away from the foundation).
       - Both rows extract to 0 when `eaves_lf` is 0 → zero-qty filter suppresses them automatically, so a rake-only quote won't get phantom downspouts either.
    - Unit-tested: eaves=0 → 0/0/0; eaves=12 → 12 LF gutter + 2 downspouts (20 LF coil) + 4 elbows; eaves=78 → 78 LF + 3 dn (30 LF coil) + 6 elbows; eaves=200 → 200 LF + 7 dn (70 LF coil) + 14 elbows. Lint clean.
    - Caveat to flag for Howard: the `Downspout 6"` catalog unit is LF (10 LF per piece). If Vero ever switches to a per-piece unit, swap `count × 10 → count` in the lambda.
    - **Files**: `backend/routes/ai_measure.py` (Rule 0a EAVES vs RAKES clarifier), `backend/routes/hover.py` (gutter section adds Downspout + elbow mapper rows).

  - **Iter 57q — Async AI Measure with polling (kills Cloudflare 524 timeouts) (2026-06-20)**: Howard's report: "I ran an AI on 8 photos and got a Cloudflare error." Root cause: the AI Measure endpoint ran Claude vision synchronously (12–90 s) and hit the Kubernetes ingress's ~100 s timeout, which Cloudflare wrapped as a generic 502/524 message. The new per-opening bbox schema bumped Claude's response time further. Fixed by switching the endpoint to a true background-job + polling pattern:
    - **`POST /api/measure/ai-measure`** now validates inputs (image bytes, sizes, EMERGENT_LLM_KEY) synchronously, persists a `running` doc to the new `ai_measure_runs` MongoDB collection (with `run_id` UUID, user_id, photo_count, kind, deep_dormer_scan, created_at), spawns the heavy work as a detached `asyncio.create_task`, and returns `{run_id, status: "running", stage: "starting"}` in **under 300 ms**. No more risk of ingress timeout.
    - **`GET /api/measure/ai-measure/status/{run_id}`** (new): returns `{status, stage, result, error, elapsed_ms}`. Owner-gated by user_id match.
    - **`_execute_ai_measure_worker(...)`** (new): same Claude logic that was previously inline (chat call → optional Deep Dormer Scan → aggregate → map to lines → build vero_openings → return). Writes stage updates ("claude" → "dormer_scan" → "aggregating" → "mapping") to the run doc as it progresses, then sets `status: "done"` with the full result on success, or `status: "error"` with an error message on failure (exception captured + logged).
    - **Frontend polling** in `AIMeasureButton.jsx`: replaced the single `api.post()` with a launcher + 3 s polling loop (max 100 polls = 5 min cap). Reads `s.stage` from each poll and surfaces it in the Run button text: "Starting…" → "Claude vision…" → "Deep dormer scan…" → "Aggregating walls…" → "Mapping to catalog…". On `status === "done"`, unwraps `s.result` and feeds it into the existing downstream logic exactly as before (zero changes to the preview/apply paths). On `status === "error"` shows the worker's error message as a toast.
    - **Verified end-to-end** with real Claude Opus 4.5 run on the test garage photo: POST took 225 ms, polling reported stage transitions, final result rendered the full preview after ~20 s. Lint clean. Backend reload OK.
    - **Files**: `backend/routes/ai_measure.py` (heavy refactor: split POST into launcher + `_execute_ai_measure_worker`, added GET status endpoint, added `db.ai_measure_runs` writes, added datetime/logging imports), `frontend/src/components/estimate/AIMeasureButton.jsx` (replaced sync POST with poll loop + `busyStage` state + stage-aware Run-button text).

  - **Iter 57q-bp — Same async polling pattern applied to Read Blueprints (2026-06-20)**: Howard's report: "i had the same error on the upload blue print." Root cause + fix were identical to the AI Measure route. Mirrored the work in `ai_blueprint.py` + `BlueprintMeasureButton.jsx`:
    - **`POST /api/measure/ai-blueprint`** now persists a `running` doc to a new `ai_blueprint_runs` MongoDB collection, spawns `_execute_ai_blueprint_worker` as a detached task, and returns `{run_id, status: "running", pages_queued}` in **~200 ms**.
    - **`GET /api/measure/ai-blueprint/status/{run_id}`** (new): returns `{status, stage, result, error, elapsed_ms}`, owner-gated by user_id.
    - **`_execute_ai_blueprint_worker(...)`** runs the existing Claude blueprint read → aggregate → map → build Vero/Mezzo openings logic in the background, with stage updates ("claude" → "aggregating" → "mapping") written to the run doc.
    - **`BlueprintMeasureButton.jsx`** updated to launch + poll (3 s interval, 5 min cap), stage-aware button text ("Uploading…" → "Reading plans…" → "Aggregating walls…" → "Mapping to catalog…").
    - **Verified end-to-end** via curl on the synthetic blueprint test image: POST took 198 ms, polling reported `done` at T+3s with elapsed_ms=6920 and all 8 expected result keys (measurements / lines / vero_openings / mezzo_openings / raw_ai / model / session_id / pages_processed; 4 walls extracted).
    - **Files**: `backend/routes/ai_blueprint.py` (launcher + worker + status endpoint), `frontend/src/components/estimate/BlueprintMeasureButton.jsx` (poll loop + busyStage + button text).


  - **Iter 57r — Resume last AI run + datetime bug fix (2026-06-20)**: Endpoint `GET /api/measure/ai-measure/latest-for-estimate/{estimate_id}` was throwing 500 with `TypeError: can't subtract offset-naive and offset-aware datetimes` because MongoDB returns `created_at` as a timezone-naive `datetime` by default while the code compared it against `datetime.now(timezone.utc)`. Fix:
    1. Added a small helper `_as_aware_utc(dt)` in `ai_measure.py` that coerces a naive datetime to UTC (`dt.replace(tzinfo=timezone.utc)`) and passes through aware ones unchanged.
    2. Applied the helper to both `ai_measure_status` and `ai_measure_latest_for_estimate` so all `(now - created)` / `(completed - created)` arithmetic is offset-safe.
    - Verified via curl: `GET /api/measure/ai-measure/latest-for-estimate/resume-test-1781993221` returns HTTP 200 with the full run payload including computed `elapsed_ms` and `age_seconds`. No-run path also OK (`{"run":null}`).
    - Unblocks the "Resume last AI run" banner in `AIMeasureButton.jsx` (`data-testid="ai-measure-resume-banner"` / `ai-measure-resume-btn`).
    - **Files**: `backend/routes/ai_measure.py` (added `_as_aware_utc` helper + applied to status + latest-for-estimate endpoints).

  - **Iter 57s — Anthropic 10 MB base64 image cap (Read Blueprints + AI Measure) (2026-06-20)**: Howard hit `AnthropicException — image exceeds 10 MB maximum: 10553176 bytes > 10485760 bytes` when running Read Blueprints on a large PDF. Root cause: blueprint pages rendered at `PDF_RENDER_SCALE=2.0` produce 8–15 MB PNGs that bloat to >10 MB once base64-encoded (×1.33). Anthropic enforces the cap on the base64 string, not raw bytes, so a "12 MB upload cap" wasn't enough.
    1. Added `_compress_for_claude(img_bytes, max_raw_bytes=5_500_000)` helper in both `ai_blueprint.py` and `ai_measure.py`. Targets raw < 5.5 MB → base64 < 7.3 MB (well under the 10 MB Anthropic limit). Iterates JPEG quality 88→85→78→70→60 and downscale 1.0→0.85→0.72→0.6→0.5→0.42 until it fits. Skips small JPEGs untouched, falls back to original on PIL failure.
    2. Applied to (a) blueprint PDF→PNG rendering (`_render_pdf_to_pngs`), (b) blueprint image-scan uploads, and (c) AI Measure photo uploads — all three pre-existing paths shared the same root cause.
    - Verified with a synthetic 77 MB random-noise PNG (worst case): compresses to 4.4 MB JPEG → 5.87 MB base64 → well under cap. Lint clean. Backend restarted cleanly.
    - **Files**: `backend/routes/ai_blueprint.py` (PIL import + `_compress_for_claude` helper + applied to PDF render path + image upload path), `backend/routes/ai_measure.py` (added `_compress_for_claude` helper + applied to all uploaded photos).

  - **Iter 57t — Vero pricing freeze (2026-06-20)**: Howard's Vero pricing sheet is incomplete/unreliable for 3-Lite Slider, Picture, Patio Door, and for the >101 UI buckets on Double Hung + 2-Lite Slider. Until clean numbers land, those products/buckets are frozen out of the Vero tab so contractors can't generate quotes with bad pricing.
    1. **Frontend `VeroPanel.jsx`** — added two constants at the top: `FROZEN_PRODUCT_TYPES = {Vero 3-Lite Slider, Vero Picture, Vero Patio Door}` and `BUCKET_LOCKED_PRODUCT_TYPES = {Vero Double Hung, Vero 2-Lite Slider}` with `LOCKED_MAX_UI = 101`. Filter hides frozen sections from `.map()`. Per-row, when a locked product's W+H > 101, the row shows a yellow "NEED CUSTOM QUOTE — UI > 101 — contact rep" chip in place of the base/total price (base_mat zeroed, adders hidden, doesn't roll up into estimate total). Added per-section "PRICING CAP" banner explaining the limit upfront.
    2. **Frontend `useReconcileWindowSnapshots.js`** — historical estimates with frozen product types are auto-migrated to `Vero Double Hung` on load so they don't get orphaned in hidden sections.
    3. **Frontend `HoverImportButton.jsx`** — `VERO_PRODUCT_TYPES` dropdown now only offers Double Hung, 2-Lite Slider, Casement (3-Lite + Picture dropped). HOVER import will never auto-tag an opening as a frozen product.
    4. **Backend `ai_measure.py`** — `_STYLE_TO_VERO_PRODUCT_TYPE` rerouted every style that previously mapped to Picture (Bay/Bow/Half-Round/Quarter-Round/Arch/Octagon/Hexagon/Garden/Other-Shape) or 3-Lite Slider → Double Hung (multipliers preserved: Bay=3, Bow=5). 3-Lite Slider → 2-Lite Slider.
    5. **Backend `hover.py`** — `_guess_vero_product_type` W/H heuristic stripped of the Picture + 3-Lite Slider branches; now only picks between DH / 2-Lite Slider / Casement.
    6. **Mezzo tab untouched** — pricing unfrozen there. The freeze is Vero-only.
    - Verified end-to-end: opened a 14-opening windows estimate; saw exactly 2 sections (DH + 2-Lite), both with the yellow "Pricing cap" banner; two pre-existing 109×31 and 108×32 openings (UI=140) correctly show the "Need Custom Quote" chip and don't add to the section total. Lint clean (frontend + backend).
    - **Files**: `frontend/src/components/estimate/VeroPanel.jsx`, `frontend/src/lib/useReconcileWindowSnapshots.js`, `frontend/src/components/estimate/HoverImportButton.jsx`, `backend/routes/ai_measure.py`, `backend/routes/hover.py`.
    - **To unfreeze later**: remove the frozen product names from `FROZEN_PRODUCT_TYPES` in `VeroPanel.jsx` and `useReconcileWindowSnapshots.js`, bump `LOCKED_MAX_UI` (or empty `BUCKET_LOCKED_PRODUCT_TYPES`), and restore the original `_STYLE_TO_VERO_PRODUCT_TYPE` + `_guess_vero_product_type` mappings.

  - **Iter 57u — Removed "Window - Block Frame Replacement" install line (2026-06-20)**: Howard asked to drop it from both Vero and Mezzo workflows. Since it's a shared install method (not per-brand), this is a global removal.
    1. **`backend/catalog_seed.py`** — removed from the `Window Installation` section list AND from `ITEM_META` (price/unit map). Existing companies see it disappear from `/api/catalog` on next refresh (catalog is dynamically resolved from `SECTION_LAYOUT`, no DB migration needed).
    2. **`backend/services.py`** — removed from the window-installation item set used by service mapping.
    3. **`frontend/src/components/estimate/JobInfoPanel.jsx`** — install-method toggle dropped to 2 buttons (Pocket / Full Fin); grid `grid-cols-3` → `grid-cols-2`.
    4. **`frontend/src/lib/useEstimate.js`** — removed `block_frame` key from `INSTALL_LINE_FOR_METHOD`.
    5. **`frontend/src/lib/catalogTranslations.js`** — removed the Spanish translation entry.
    6. **`backend/routes/hover.py`** — updated stale comment ("swap to Full Fin/Block Frame" → "swap to Full Fin").
    - Verified via `GET /api/catalog`: no Block Frame entries; Window Installation section now lists Pocket Install, Full Fin Replacement, Large Window adder, Lead Safe, Cap window, Disposal Fee. Live screenshot confirms the 2-button toggle renders correctly. Lint clean.
    - Historical estimates with a saved `install_method: "block_frame"` or a `Window - Block Frame Replacement` line in `lines[]` are left untouched — no destructive migration.
    - **Files**: `backend/catalog_seed.py`, `backend/services.py`, `backend/routes/hover.py`, `frontend/src/components/estimate/JobInfoPanel.jsx`, `frontend/src/lib/useEstimate.js`, `frontend/src/lib/catalogTranslations.js`.

  - **Iter 57v — Window Package Quote override (Vero + Mezzo) (2026-06-20)**: Howard wanted a per-tab override that replaces the bucket-summed window material total with a single contractor-entered "package" number (rep / inside-sales hand quote / Vero software / Mezzo software). Labor + accessories + sales tax + profit all calc normally on top.
    1. **Backend `models.py`** — new `WindowPackageQuote(BaseModel)` (`enabled`, `total`, `reference`, `notes`) + 2 optional fields on `EstimateIn`: `vero_package_quote` / `mezzo_package_quote`. Defaults to `None` so existing estimates unaffected.
    2. **Backend `services.py` `calc_totals`** — added `_brand_window_mat(est, brand, openings, fn)` helper: if `{brand}_package_quote.enabled && total > 0` → return that flat number; else fall back to summing each opening through `fn`. CSV exports + future PDF generator automatically respect the override.
    3. **Frontend `calc.js`** — same override pattern applied inside the Mezzo + Vero reduce blocks so the live sticky bar / sidebar totals update instantly.
    4. **Frontend `WindowPackageQuote.jsx`** — new shared component used by both panels. Card with `Use Package Quote` toggle + 3 fields (Package Total / brand-specific Quote Reference / Notes) + orange "Active — {brand} window material total" footer chip. Brand-aware data-testids (`vero-package-quote-*` / `mezzo-package-quote-*`).
    5. **Frontend `VeroPanel.jsx` + `MezzoPanel.jsx`** — render `<WindowPackageQuote brand=... />` at the top; when the brand's package quote is active, per-product section totals get a strikethrough + greyed style with a tooltip ("Per-window pricing overridden by Window Package Quote") so the contractor visually understands the bucket numbers don't roll up.
    6. **Frontend `VeroJobSnapshot.jsx` + `MezzoJobSnapshot.jsx`** — `openingDollars` short-circuits to `package_quote.total` when active so the Base Total card mirrors what the sticky bar shows.
    - Brand-independent: setting the Vero override does NOT affect Mezzo and vice versa.
    - Verified end-to-end: created a fresh windows-kind estimate, set Vero package quote to $12,500 with reference "VR-44892 — Jen S." → sidebar jumped to Base $13,375 (= $12,500 + 7% tax) → Vero Job Snapshot Base Total = $12,500 → per-row sections show $0.00 with strikethrough. Mezzo independent ($0.00). Lint clean. PUT/GET round-trip OK.
    - **Files**: `backend/models.py`, `backend/services.py`, `frontend/src/lib/calc.js`, `frontend/src/components/estimate/WindowPackageQuote.jsx` (new), `frontend/src/components/estimate/VeroPanel.jsx`, `frontend/src/components/estimate/MezzoPanel.jsx`, `frontend/src/components/estimate/VeroJobSnapshot.jsx`, `frontend/src/components/estimate/MezzoJobSnapshot.jsx`.

  - **Iter 57w — Blueprint downspouts on ISS + gable-eaves over-count fix (2026-06-20)**: Howard tested Read Blueprints on a real residential plan set and saw no Downspout line on the ISS estimate after Apply. Two root causes:

    **Bug 1 — ISS apply path bypasses the shared `hover.py` mapper.** Siding apply uses `_build_lines(measurements)` from `hover.py` which emits Gutter + Downspout + elbow lines. ISS apply mode in `BlueprintMeasureButton.applyResult` calls `buildISSLinesFromMeasurements()` (frontend, `ISSHoverImportButton.jsx`) instead — which emitted a Gutter line but no Downspout line.
    - Fix: added a Downspout line to `buildISSLinesFromMeasurements` using the same formula as `hover.py` (1 downspout per 30 LF eaves, min 2; each ≈ 10 LF of coil).
    - Also added 2 defensive rules to `HOVER_MAPPING_SPEC` for `tabs=["iss"]` (Gutter + Downspout under `Seamless Gutter with Siding` with ISS catalog item names) — covers any future ISS path that consumes `result.lines` directly. No "elbow" line for ISS — that line doesn't exist in the ISS catalog.

    **Bug 2 — Claude reports eaves_lf as the full floor-plan perimeter, over-counting by ~2.5×.** On a gable-roof house gutters only run along non-gable walls. Claude was returning perimeter (248 LF) instead of just the eave walls (100 LF).
    - Fix part 1: clarified the system prompt — `eaves_lf` is now "sum of widths of EAVE walls only (walls where gable_triangle_height_ft == 0)".
    - Fix part 2: defensive post-processing in `_aggregate_to_hover_shape` — when ANY wall has `gable_triangle_height_ft > 0`, recompute eaves_lf as the sum of widths of non-gable walls (overrides Claude). Hip roofs leave Claude's value untouched.
    - Verified: Howard's last blueprint run (4 walls 74+74+50+50, gables on front+back) recomputes from 248 → 100 LF; downspouts drop from 9×10=90 LF → 4×10=40 LF coil. Unit tests pass for both gable + hip cases.

    - **Files**: `backend/routes/ai_blueprint.py` (system prompt + defensive eaves recompute), `backend/routes/hover.py` (added 2 ISS-tab rules to `HOVER_MAPPING_SPEC`), `frontend/src/components/estimate/ISSHoverImportButton.jsx` (`buildISSLinesFromMeasurements` now pushes Downspout).

  - **Iter 57x — Balcer PDF "won't read" → Cloudflare 502 on slow upload + Restore banner (2026-06-20)**: Howard uploaded an 8 MB / 12-page D-size architectural PDF (Balcer Residence) and saw "Blueprint read failed". Reproduced exactly with curl: upload takes ~60 s for the 7.5 MB body, Cloudflare hits the ingress timeout and returns **HTTP 502** to the client — BUT the backend has already received the body, started the worker, and the worker completes. The frontend never sees the `run_id` so polling can't recover the orphaned result. Fixes:
    1. **Backend `routes/ai_blueprint.py`** — fixed the offset-aware datetime bug in `ai_blueprint_latest_for_estimate` (same fix as Iter 57r for AI Measure).
    2. **Frontend `BlueprintMeasureButton.jsx`** — three fixes:
       - **Restore banner**: on mount + after any upload, the modal calls `GET /measure/ai-blueprint/latest-for-estimate/{est.id}` and surfaces a yellow "Previous read available — click to restore" banner when a recent (< 30 min) run exists. Tap **Restore** → loads the preview (`status=done`), resumes polling (`status=running`), or shows the error toast (`status=error`). Dismiss hides it for the session.
       - **Axios upload timeout 60 s → 180 s** so most slow connections finish before axios bails. The 502 still happens at the Cloudflare layer in the worst case but the Restore banner is the safety net.
       - **estimate_id appended to the upload FormData** so the backend tags each run record (previously never sent — orphaned runs couldn't be looked up by the user).
       - **Better error toast**: detects timeout/502/network/aborted and tells the user "your read may still be processing — check the Restore banner in a moment".
    - Verified: backend successfully reads the Balcer PDF — 12 pages, eaves_lf=112 (correctly excludes the two gable ends after Iter 57w), 20 windows, 3 garage doors, 3 patio doors, 27 openings, 66 lines. ISS Apply produces 10 lines including Downspout 40 LF.
    - **Files**: `backend/routes/ai_blueprint.py`, `frontend/src/components/estimate/BlueprintMeasureButton.jsx`.


## Saved for Later (Howard's deferred ideas)
- **"Promote to primary" star in Compare modal (parked 2026-02-25).** Add a small star ⭐ icon on each source tab in `ElevationCompareModal` that lets a contractor pin one source as the canonical one for the customer Quote PDF — overriding the default "most-recently-imported wins" behavior. Useful when (say) HOVER ran most recently but the AI Photo numbers look more accurate after a Compare review. Implementation hook: new `estimate.measurements._ai_elevations_primary_source` string field; PDF builder (`emailElevations.js`) reads `_ai_elevations_by_source[primary]` when set, falls back to `_ai_elevations` otherwise.
- **Click-to-edit "Gutter runs" chip on the Coverage Breakdown (parked 2026-02-25).** Make the blue "Gutter runs" chip in `TakeoffReconCard.jsx` clickable — open an inline `+ / −` stepper so a contractor can bump the run count (e.g. 4 → 5 on a U-shaped house) right inside the HOVER / Blueprint preview modal. The override should instantly reflow End Caps (`runs × 2`) and the Hangars `+1/run` bonus in the chip row + the recon-card formula rows, then propagate to the apply payload (override stashed on the takeoff result so the back-end `_build_lines` rerun uses it). Lets contractors handle gutter-run edge cases without re-running the takeoff. Implementation hook: local `runOverride` state in `TakeoffReconCard` + threaded into the apply callback in `HoverImportButton`/`BlueprintMeasureButton`.
- **Customer Quote PDF — collapsible formula breakdowns under each line (parked 2026-02-25).** Mirror the per-line `note` strings (J-channel, Finish Trim, Soffit J, Downspout, Elbow, End Cap, Hangars with Screws) onto the printed customer PDF as a small "▾ formula" expander under each line, collapsed by default. Gives contractors instant credibility on homeowner call-backs ("here's exactly how I sized your gutters") without cluttering the headline numbers. Implementation hook: WeasyPrint quote template — render the line's `note` field inside a `<details>` block per line.
- **Pre-send "common items not quoted" safety net (parked 2026-06-20).** When a contractor hits "Send Quote" and one or more of the highlighted/lightbulb lines (Pocket Install, .019 Coil, Caulking per color, etc.) still has qty=0, pop a one-tap confirm modal: *"You haven't quoted [Pocket Install / Coil / Caulking] yet — continue anyway?"* Turns the visual lightbulb hint into an actual blocker so window-job essentials don't get forgotten. Implementation hook: `useEstimate.sendQuote` (or wherever the email/PDF modal opens) — read `commonItems.unfilledCountFor(est, tab)` and intercept if > 0.

## Recent Changes

- **Iter 78u — Compare Drawings modal (2026-02-25)**: Howard's "spot drift across sources" ask. Side-by-side rendering of elevation drawings from all 3 measurement sources (AI Photo + HOVER + Blueprint) so contractors can instantly see when two sources disagree before sending the quote.
  - **New `ElevationCompareModal.jsx`**: tabbed modal with Compare tab (default when 2+ sources exist) + one tab per source. Compare tab groups elevations by label and renders side-by-side cards across sources with a "✓ SOURCES AGREE" or "⚠ Drift: N'W · N'H" badge per group (drift threshold = 2 ft on width OR height).
  - **Schema** (`estimate.hover_measurements._ai_elevations_by_source`): new source-keyed bucket structure. Each of the 3 import flows (AI Measure, HOVER import, Blueprint import) now writes to its own sub-key (`ai_photo`, `hover`, `blueprint`) instead of overwriting a shared field. `_ai_elevations` still populated with the most-recent set (powers the customer Quote PDF).
  - **Trigger UI**: new "🛇 Compare Drawings (N)" button in `JobInfoPanel.jsx` next to the import buttons. Only renders when ≥2 sources have drawings on this estimate.
  - **Read-only view**: no editing inside the Compare modal — re-open the source's own import modal to nudge or override. Keeps the comparison clean.
  - **Verified live**: patched the John Derunk test estimate with 2 sources (HOVER + AI Photo, 2 elevations each), clicked the new Compare button → modal opened with 3 tabs (Compare/HOVER/AI Photo), Front + Left elevations rendered side-by-side with color-coded source headers and the green "SOURCES AGREE" badge (drift within 2 ft on both). Zero console errors. Test data cleaned up afterwards.
  - **Files**: `frontend/src/components/estimate/ElevationCompareModal.jsx` (new), `frontend/src/components/estimate/JobInfoPanel.jsx`, `frontend/src/components/estimate/AIMeasureButton.jsx`, `frontend/src/components/estimate/HoverImportButton.jsx`, `frontend/src/components/estimate/BlueprintMeasureButton.jsx`, `memory/PRD.md`.

- **Iter 78t — Elevation drawings across all 3 sources (AI Photo + HOVER + Blueprint) (2026-02-25)**: Howard's "shared codepath" ask. Wired the same `ElevationDrawing.jsx` + `elevationToSvg()` renderer into the HOVER import preview and Blueprint preview modals — full drawing coverage across all 3 measurement sources, single codepath, identical UX.
  - **HOVER preview** (`HoverImportButton.jsx`): drawings render right above the Extracted Measurements panel using `buildElevationsFromHoverVision(result.measurements)` (feeds off Phase 2 vision's `per_elevation_siding_from_drawing`). Same nudge + roof-toggle interactions. On Apply, merged drawings stash on `hover_measurements._ai_elevations`.
  - **Blueprint preview** (`BlueprintMeasureButton.jsx`): drawings render right before the Takeoff summary. Tries AI-Measure-shaped data first (`buildElevationsFromAIMeasure` on `raw_ai.walls/openings`) and falls back to vision-shaped (`buildElevationsFromHoverVision`) — whichever the source produced. On Apply, persists to `hover_measurements._ai_elevations` so the customer PDF picks it up unchanged.
  - **No new components**: this is a pure wiring iteration. The renderer, builder, edit-merge logic, and PDF helper from Iter 78s are reused 1:1.
  - **Verified live**: mocked `/measure/map` response with 3 elevations (Front gable + 2 windows · Left flat + 1 window · Back gable + 0 windows) → modal renders all 3 drawings, all 3 roof toggles, all 3 opening rectangles with correct labels/colors. Zero console errors.
  - **Files**: `frontend/src/components/estimate/HoverImportButton.jsx`, `frontend/src/components/estimate/BlueprintMeasureButton.jsx`, `memory/PRD.md`.

- **Iter 78s — HOVER-style elevation drawings from AI Measure (2026-02-25)**: Howard wanted contractors using AI Photo to get HOVER-grade per-elevation takeoff sheets without paying for HOVER. Shipped the full kit:
  - **New `ElevationDrawing.jsx`** — pure SVG React component that renders one elevation: wall rectangle sized to (facade_width_ft × facade_height_ft), roof shape above (gable triangle / hip trapezoid / flat slab / none), proportionally-positioned opening rectangles (color-coded by type: window blue, door orange, patio purple, garage grey), labeled dim callouts, 10-ft scale bar.
  - **Interactive features**: drag any opening to reposition it (pointer events, touch + mouse), click roof toggle button to cycle gable → hip → flat → none. Edits stash on `measurements._ai_elevation_edits` and propagate to the persisted estimate on Apply.
  - **`elevationBuilder.js`** — single source of truth that converts AI Measure (`walls[]` + `openings[]` with bboxes) into the renderer's input shape. Bbox center coords → wall-relative x/y percentages. Roof style auto-inferred from `gable_triangle_height_ft`.
  - **`emailElevations.js`** — string-based SVG renderer (no React) that produces email/PDF-safe inline SVG for the customer Quote PDF. Mirrors the visual style of the React component at a compact print size. Wired into `emailQuote.js` as a new "Elevation Drawings" block right after the existing Per-Elevation Breakdown card.
  - **AI Measure preview modal** (`AIMeasureButton.jsx`): new "Elevation Drawings" grid right under the AI notes, rendering one drawing per wall in a 2-col layout. Contractor reviews, nudges, toggles roof, applies → drawings persist on the estimate's measurements payload for the customer quote.
  - **Persistence**: at Apply time, the merged elevations (with all contractor edits baked in) are stashed on `toApply.measurements._ai_elevations`. The customer Quote PDF reads from there.
  - **Limitations called out in the modal subtitle**: photos with perspective distortion may need a contractor nudge; roof auto-guess can be wrong (one-tap toggle fixes it); scale bar derived from facade measurements, not a real on-photo scale (consistent with Phase 3's logic).
  - **Verified**: Node smoke test confirms `elevationToSvg()` produces valid SVG with all expected elements (gable path, opening labels, color coding, scale bar). All 4 modified files lint clean. App loads cleanly with no console errors.
  - **Files**: `frontend/src/components/estimate/ElevationDrawing.jsx` (new), `frontend/src/lib/elevationBuilder.js` (new), `frontend/src/lib/emailElevations.js` (new), `frontend/src/components/estimate/AIMeasureButton.jsx`, `frontend/src/lib/emailQuote.js`, `memory/PRD.md`.

- **Iter 78r — Phase 2 expanded: rakes, soffit depth, window dims (2026-02-25)**: Howard wanted Phase 2 to cover more than just siding. Same Claude Opus 4.5 Vision call, expanded prompt, expanded `_build_warnings` — **5 new cross-checks** at zero added cost:
  - **Eaves LF** — sum of per-face `facade_width_ft` vs text `eaves_lf` (>12% Δ flagged with per-face breakdown).
  - **Rakes LF** — sum of per-face `rake_lf_on_face` (both slopes summed on gable faces, 0 on hip/flat) vs text `rakes_lf`.
  - **Soffit / overhang depth** — drawings often label the overhang; compares avg labeled depth to job's `overhang_in` setting (>25% Δ, wider envelope since labels round to ¼ ft).
  - **Window count** — sum of `len(window_dims[])` across elevations vs text `window_count` or `len(windows[])`. Flags Δ ≥ 2.
  - **Window perimeter total** — Σ 2×(W+H) from drawing dims vs text `windows[]` dims (>20% Δ).
  - Each new warning has a stable code (`vision_eaves_delta`, `vision_rakes_delta`, `vision_overhang_delta`, `vision_window_count_delta`, `vision_window_perim_delta`) and renders in the same yellow banner with detail strings.
  - All extended-cross-check logic is null-safe: if Claude can't read a field, that delta silently skips.
  - **Tests** (`backend/tests/test_hover_vision.py`): 7 new tests covering all 5 deltas (positive case + close-enough negative case + null-safe path). **53/53 backend tests pass.**
  - **Files**: `backend/routes/hover_vision.py`, `backend/tests/test_hover_vision.py`, `memory/PRD.md`.

- **Iter 78q — HOVER AI Verification Phase 3: Deep Verify scale-bar measurement (2026-02-25)**: Final phase of Howard's "verify HOVER drawings vs reported numbers" stack. Contractor-triggered second-opinion pass that re-measures a specific elevation against its on-page scale bar — ignoring the dim callouts entirely.
  - **Backend**:
    - Phase 2 now also stashes each rendered elevation PNG (base64) into a new MongoDB collection `hover_page_cache`, keyed by a UUID `deep_verify_cache_key` returned in the HOVER import response. **TTL index = 1 hour** so renders auto-purge after a typical preview session — never accumulates.
    - New endpoint `POST /api/estimates/hover-deep-verify` (auth-gated, same-user scope): takes `{cache_key, label, measurements, phase2_drawing}` → loads the cached PNG → calls `deep_verify_elevation()` with a scale-bar-focused prompt → returns a 3-way reconciliation `{measured_width_ft, measured_height_ft, measured_gross_wall_sqft, scale_bar_found, confidence, delta_vs_phase2, delta_vs_text, ...}`.
    - New `DEEP_VERIFY_PROMPT` explicitly instructs Claude Opus 4.5 Vision to find the scale bar, measure its pixel length, derive ft-per-pixel, then re-measure the eave run + facade height **without using the dim callouts**.
    - New `reconcile_deep_verify()` helper builds the 3-way comparison block.
  - **Frontend** (`HoverImportButton.jsx`):
    - New "🔍 Deep Verify" button renders inline next to any `vision_elev_delta_*` warning when a `deep_verify_cache_key` is present (= fresh import path; restore-from-cache path doesn't have PDF bytes so the button is hidden there).
    - Loading state shows a spinner + "Verifying…" label.
    - Result panel renders inline below the warning as a 3-card comparison: Scale-bar (yellow accent) · Phase 2 drawing · Text extract — each showing area, delta, and confidence/notes.
    - Deep verify state is keyed by warning code so multiple elevations can be verified independently. Resets on modal close / apply.
  - **Cost**: ~$0.40 per Deep Verify (one Opus 4.5 vision call, careful scale-bar prompt). Cap = whatever the contractor manually triggers.
  - **Tests** (`backend/tests/test_hover_vision.py`): 2 new tests for `reconcile_deep_verify` (3-way comparison + no-text-area edge case). **46/46 backend tests pass.**
  - **Verified live**: endpoint reachable, auth + payload validation correct (401 unauth, 400 missing fields, 404 missing cache). Mocked import response with a `vision_elev_delta_front` warning + `deep_verify_cache_key` renders the 🔍 Deep Verify button perfectly in the modal banner; no console errors.
  - **Files**: `backend/routes/hover_vision.py`, `backend/routes/hover.py`, `backend/startup.py`, `backend/tests/test_hover_vision.py`, `frontend/src/components/estimate/HoverImportButton.jsx`, `memory/PRD.md`.

- **Iter 78p — HOVER AI Verification Phase 2: per-elevation vision pass (2026-02-25)**: Phase 2 of 3 of the verification stack. Claude Opus 4.5 Vision now reads each elevation drawing inside the HOVER PDF and cross-checks the drawing-extracted area against the text-extracted measurements.
  - **New module** `backend/routes/hover_vision.py` (~270 lines):
    - `_render_pdf_pages(pdf_bytes)` — opens the PDF with PyMuPDF, detects elevation pages via `_ELEV_RE` (matches "Front/Back/Rear/Left/Right/Side A–D Elevation"), renders each at 144 DPI as PNG. Hard-capped at 6 pages for cost control. Skips images > 2.5 MB to stay under emergentintegrations payload limits.
    - `_read_one_elevation()` — single Claude Opus 4.5 Vision call per page; prompt asks for `{facade_width_ft, facade_height_ft, gross_wall_sqft, opening_count, siding_sqft, confidence, notes}`. Returns `None` on parse/JSON failures so a flaky vision call never breaks the import.
    - `_build_warnings()` — per-elevation drawing-vs-text delta (12% threshold) + total-siding drawing-vs-text delta. Returns Phase 1-shaped warning dicts so they render in the same yellow banner. Also emits an info-level "drawings sum to X ft²" line when text didn't extract a siding total.
    - `run_vision_pass(pdf, measurements, api_key)` — orchestrator. Parallelizes the per-page vision calls with `asyncio.gather` so 4-6 calls take wall-time of 1 (~30-60s total). Returns `(warnings, per_elevation_drawing_data)`.
  - **Wired** into `POST /api/estimates/hover-import`: after the existing text-extraction + Phase 1 rules, runs the vision pass and merges its warnings into the response. Stashes `per_elevation_siding_from_drawing` on `measurements` — ready for the Per-Elevation Breakdown card to consume.
  - **Defensive**: the entire vision block is wrapped in try/except. If `EMERGENT_LLM_KEY` is missing, the vision call errors, or PyMuPDF fails to open the PDF, the import proceeds with just the Phase 1 warnings — never breaks.
  - **Restore path**: vision pass NOT run on `POST /api/measure/map` (we don't have the original PDF bytes by then, only the cached measurements). Phase 1 rules still surface on restore.
  - **Tests** (`backend/tests/test_hover_vision.py`): 14 unit tests covering page-label regex, JSON parsing (fenced / preface / garbage), percent-delta math, page rendering on synthetic PDFs (matches / non-matches / bad PDFs / 6-page cap), and the `_build_warnings` logic across 4 scenarios. **44/44 backend tests pass**.
  - **Cost**: ~$0.15–0.30 per HOVER import (4–6 vision calls × Opus 4.5 vision pricing). Cap hard-coded at 6 calls.
  - **Files**: `backend/routes/hover_vision.py` (new), `backend/routes/hover.py`, `backend/tests/test_hover_vision.py` (new), `memory/PRD.md`.

- **Iter 78o — HOVER AI Verification Phase 1: deterministic sanity checks (2026-02-25)**: First of 3 phases of Howard's "verify HOVER numbers against the drawings" stack. Phase 1 = free deterministic rules over the extracted measurements; Phase 2 = per-elevation vision pass; Phase 3 = Deep Verify scale-bar check.
  - **New module** `backend/routes/hover_sanity.py` — 7 construction-physics rules:
    1. Soffit area ≈ eaves × overhang (±15%)
    2. Rakes/eaves ratio inside 0.5–1.4× envelope
    3. Opening perimeter consistent with `count × typical-perim` (window 14 / entry 19 / patio 22 / garage 32 LF)
    4. door_count = entry + patio + garage (schema integrity)
    5. Outside corner count ≤ 12 (warns on bay-window / chimney mis-counts)
    6. Inside corners ≤ outside corners (info-level)
    7. Siding sqft lower bound vs `½ × eaves × 9 ft`
  - Each rule returns `{code, level, message, detail?}` — frontend renders them in a yellow banner above Extracted Measurements with bold heading + mono-num detail row + footer reminder.
  - **Wired into 3 surfaces**: HOVER import (`POST /api/hover/import`), Restore HOVER (`POST /api/measure/map`), AI Measure / Blueprint async runs (`POST /api/measure/ai-photo` / `ai-blueprint`).
  - **Tests** (`backend/tests/test_hover_sanity.py`): 12 unit tests covering each rule + the no-warn / empty-dict / non-dict paths. **30/30 backend tests pass**.
  - **Verified live**: real-world cached HOVER (John Derunk EST-669165) returns 0 warnings (clean read = no false positives). Mocking the `/measure/map` response with a deliberately-broken measurement set surfaces all 6 expected warning codes in the modal banner with proper formatting.
  - **Cost**: $0 per HOVER. No LLM calls, instant feedback.
  - **Files**: `backend/routes/hover_sanity.py` (new), `backend/routes/hover.py`, `backend/routes/ai_measure.py`, `backend/tests/test_hover_sanity.py` (new), `frontend/src/components/estimate/HoverImportButton.jsx`, `frontend/src/components/estimate/BlueprintMeasureButton.jsx`, `memory/PRD.md`.

- **Iter 78n — "Restore HOVER Lines" button (2026-02-25)**: Howard shipped a one-tap restore for accidentally-cleared HOVER auto-fills. No new PDF upload, no new LLM call — re-runs the takeoff mapper against the measurements already cached on `estimate.hover_measurements` (persisted since Iter 70) via the existing `POST /api/measure/map` endpoint.
  - **UI**: New blue-outlined `data-testid="hover-restore-btn"` rendered next to **Import HOVER** in `HoverImportButton.jsx`, gated by `hasCached = !!est.hover_measurements`. Tooltip: "Re-apply the auto-fills from the most recent HOVER import — no new upload needed".
  - **Modal**: same preview modal as the fresh-upload flow (Takeoff Recon Card, Coverage Breakdown, Gutter assumptions chips, Apply button) — title flips to **"HOVER Lines Restored (Cached)"** with a timestamp subtitle so the contractor knows it's a recall.
  - **Apply** path unchanged: `bakeWasteIntoLines` + `steerLpSoffit` + merge-by-key — preserves manual edits, restores missing rows. Backend endpoint unchanged.
  - **Verified live**: clicked restore on John Derunk's existing estimate (EST-669165) → modal opened in <1s, showed 8 recon rows + Finish Trim coverage bar + Gutter runs chip + "Apply 69 Lines & Save" button. No console errors.
  - **Files**: `frontend/src/components/estimate/HoverImportButton.jsx`, `memory/PRD.md`.

- **Iter 78m — Fan Fold added to cut-prone waste items (2026-02-25)**: Howard confirmed Fan Fold (3/8") behaves the same as House Wrap on a job site — full-coverage, cut around every opening + corner. Added `name === '3/8" fan fold' || name.includes("fan fold")` branch to `isCutProneItem`. New test assertion added; all 3 wrap-style items (House Wrap / RainDrop House Wrap / Fan Fold) now bake waste into qty consistently. Howard also confirmed RainDrop is just a House Wrap variant (already covered in Iter 78l).
  - **Files**: `frontend/src/lib/wasteLogic.js`, `frontend/src/lib/wasteLogic.test.mjs`, `memory/PRD.md`.

- **Iter 78l — Waste factor applies to House Wrap (2026-02-25)**: Howard's request: waste % should bake into House Wrap rolls the same way it bakes into siding panels (full-coverage product, cut waste at every opening + corner + seam).
  - **One-line fix** in `frontend/src/lib/wasteLogic.js` — `isCutProneItem` now also matches `name === "house wrap" || name === "raindrop house wrap"`. Single source of truth, so the change propagates across:
    - HOVER import / Blueprint import (waste baked into qty on apply)
    - "Recompute waste on existing lines" button (SettingsRow)
    - Material List PDF Order column
    - Takeoff Recon Card (Order @ X% waste column)
  - **Tests** (`frontend/src/lib/wasteLogic.test.mjs`): added 2 new assertions covering both `House Wrap` and `RainDrop House Wrap`. All wasteLogic tests pass.
  - **Files**: `frontend/src/lib/wasteLogic.js`, `frontend/src/lib/wasteLogic.test.mjs`, `memory/PRD.md`.

- **Iter 78k — Reverse Iter 69 vinyl/ascend labor lockdown (2026-02-25)**: Howard reversed his Iter 69 rule. Labor is now editable on ALL siding tabs (vinyl, ascend, lp_smart) just like windows. Two changes:
  - **Backend** (`services.py`): removed the boot-time `update_many` that force-zeroed `lab` on every estimate line where `tab ∈ {vinyl, ascend}`. Contractors' labor edits now survive backend restarts. Historical $0 values stay until the contractor types a new value (no auto-restore since the catalog never carried a default labor for siding profiles).
  - **Frontend** (`SectionAccordion.jsx`): removed the tab-conditional read-only branch. Labor `<input>` now renders editable on every tab with the same override-styling + reset-to-default chip the LP/Windows lab fields already use.
  - **Files**: `backend/services.py`, `frontend/src/components/estimate/SectionAccordion.jsx`, `memory/PRD.md`.
  - Smoke-tested: backend restarted clean (no lab-zeroing migration ran); preview loads estimate editor with no console errors; no `readOnly` or `cursor-not-allowed` styling left in the lab column code path.

- **Iter 78j — Gutter Assumptions chips on the Coverage Breakdown card (2026-02-25)**: Howard wanted one shared spot to spot-check the assumptions that drive 3 gutter line counts. Added a new "Gutter assumptions" subsection below the Coverage Breakdown stacked bars in `TakeoffReconCard.jsx`, showing 4 inline chips:
  - **Gutter runs** (highlighted blue chip) — `eaves_lf ÷ 30, min 2` — drives End Caps × 2 + Hangars +1/run
  - **End Caps** — `runs × 2`
  - **Hangars** — `(eaves/2) + runs`
  - **Downspouts** — separate `eaves_lf ÷ 25, min 2` rule (called out as not sharing the run count, since its 25 LF spacing is independent)
  - Min-2 fallback labeled inline on both 25-LF and 30-LF chips when applicable.
  - Section renders only when eaves_lf > 0 AND at least one of the 3 gutter lines is present on the takeoff.
  - **Files**: `frontend/src/components/estimate/TakeoffReconCard.jsx`, `memory/PRD.md`.
  - Smoke-tested in preview — no console errors; the chips surface inside HOVER + Blueprint preview modals where `TakeoffReconCard` already renders.

- **Iter 78i — Hangars with Screws auto-fill (2026-02-25)**: Howard's rule: "1 hanger per 2' + 1 per run", live across AI Measure / HOVER / Blueprint.
  - **Formula** (`backend/routes/hover.py`): `ceil(eaves_lf / 2) + max(2, ceil(eaves_lf / 30))` — 2'-spaced count plus 1 extra hanger per gutter run. Run-count helper (`_gutter_run_count`) is shared with the End-Cap spec so the two rows stay in sync.
  - **Coverage**: single spec entry in `HOVER_MAPPING_SPEC` emits the row on vinyl / ascend / lp_smart tabs. Because AI Measure (`POST /api/measure/map`) and Blueprint both route through the shared `_build_lines` mapper, all 3 sources inherit the formula automatically — no per-source duplication.
  - **Examples**: 100 LF → 54 hangers (`50 + 4 runs`); 32 LF → 18 (`16 + 2 runs (min)`); 180 LF → 96 (`90 + 6 runs`).
  - **Breakdown string** (Iter 78h pattern): `"100 LF ÷ 2 ft spacing = 50 + 4 runs (1 per run) = 54 hangers"` — auto-surfaces in HOVER preview's per-line `note` row AND Blueprint preview's "Formula breakdown" section (matches the `÷` filter).
  - **Verified**: 18/18 takeoff + pricing-parity tests pass; mapper outputs the row on all 3 tabs with correct counts + formula notes.
  - **Files**: `backend/routes/hover.py`, `memory/PRD.md`.

- **Iter 78h — Formula breakdown strings on Downspout / Elbow lines (2026-02-25)**: Howard asked for per-job math on the 3 downspout-derived gutter rows (mirroring the J-channel pattern). Static `note` strings replaced with dynamic callables that surface the actual numbers:
  - **Downspout 6"** (vinyl/ascend/lp_smart + ISS Downspout): `"100 LF eaves ÷ 25 = 4.0 → ceil = 4 downspouts × 10 LF = 40 LF coil"`. Min-2 fallback labeled inline: `"32 LF eaves ÷ 25 = 1.3 → ceil = 2 downspouts (min 2) × 10 LF = 20 LF coil"`.
  - **Elbow**: `"100 LF eaves ÷ 25 = 4.0 → 4 downspouts × 2 elbows (top turn + kick-out) = 8 elbows"`.
  - Both notes contain `÷`, so they pick up automatically in the Blueprint preview's existing "Formula breakdown" section (which filters dynamic notes by the divide glyph). HOVER preview also already renders `l.note` under each line.
  - New helpers in `backend/routes/hover.py`: `_downspout_count(m)`, `_downspout_breakdown(m)`, `_elbow_breakdown(m)`. Shared `_downspout_count` keeps the elbow/downspout counts perfectly in sync.
  - **Verified**: 18/18 takeoff + pricing-parity tests pass; helpers tested across 5 edge cases (typical 100 LF, min-2 fallback at 32 LF, zero eaves, large 180 LF, missing field).
  - **Files**: `backend/routes/hover.py`, `memory/PRD.md`.

- **Iter 78g — Coverage Breakdown visualization in Takeoff Recon Card (2026-02-25)**: Howard wanted a quick way to spot HOVER mis-reads before sending a quote. Shipped a compact stacked-bar visualization for the two LF-driven items most prone to drift:
  - **Finish Trim bar** — segments: `Eaves run` (blue) + `Window perimeter` (purple, with source tag "N dims" if HOVER returned per-window dims, else "N wins × 14 LF" fallback). Bottom label shows `total LF ÷ 12.5 = pcs` and formula `ceil((Eaves + Full Window Perim) ÷ 12.5)`.
  - **Soffit J-Channel bar** — segments: `Eaves run` (blue) + `Rake @ 2 passes` (orange, computed as `2 × rakes_lf`). Bottom label shows `total LF ÷ 12.5 = pcs` and formula `ceil((Eaves + 2 × Rakes) ÷ 12.5) — 2 passes per rake (wall side + fascia return)`.
  - Each segment width is proportional to its share of the total LF; inline LF value renders inside any segment ≥ 12% wide; legend chips below show full detail.
  - Vinyl/Ascend only — LP catalog doesn't use Finish Trim or Soffit J-Channel item names. Section only renders when at least one of the two lines is present.
  - New `CoverageBar` subcomponent + `windowPerimTotalLf()` helper added to `TakeoffReconCard.jsx`. Helper mirrors backend `_window_perim_total_lf()` exactly so card and mapper agree.
  - **Files**: `frontend/src/components/estimate/TakeoffReconCard.jsx`.
  - Renders inside both HOVER import preview modal and Blueprint preview modal (existing call sites — no plumbing needed).

- **Iter 78f — Finish Trim: full window perimeter + 2-pass rake rule confirmed (2026-02-25)**: Howard's clarification on the soffit-J / finish-trim install rule — exactly **2 passes per rake** total (NOT 4), and Finish Trim wraps the **full window perimeter** (top + sides + bottom), not just the sill.
  - **Code** (`backend/routes/hover.py`): new `_window_perim_total_lf(m)` helper that prefers per-window dims from `windows[]` (sum of `2 × (width + height)` per window, in feet) and falls back to `window_count × 14 LF/window` (3'0" × 4'0" replacement-window assumption). New `_finish_trim_pcs(m)` + `_finish_trim_note(m)` helpers wired into both vinyl ("Finish Trim Standard color") and Ascend ("ASCEND Finish Trim") mappings. Formula: `ceil((eaves_lf + full_window_perim) ÷ 12.5)`. Rake stays out of Finish Trim — Soffit J-Channel already covers it with 2 passes (`Eaves + 2 × Rakes ÷ 12.5`), preserving the total-2-passes-per-rake rule.
  - **Examples**: 100 eaves + 2 wins @ 36×48 + 48×60 = 132 LF → **11 pcs**. 100 eaves + 5 wins (fallback) = 170 LF → **14 pcs**. Breakdown string in the Takeoff Recon Card now shows "{eaves} eaves + {win_perim} LF window perim ({src}) = {total} LF ÷ 12.5 = {pcs} pcs".
  - **Tests** (`backend/tests/test_siding_takeoff_formulas.py`): swapped the two legacy "window-bottoms only" tests for full-perimeter tests covering both the dims-present and count-fallback branches. All 7 takeoff tests pass.
  - **Files**: `backend/routes/hover.py`, `backend/tests/test_siding_takeoff_formulas.py`, `memory/PRD.md`.

- **Iter 78e — Siding/Gutter accessory items + $0.00 price bug fix (2026-02-25)**: Howard's ask: add 4 new accessory SKUs (Flash Tape, Gutter Sealant, Hangars with Screws, Pipe Clips), all at flat prices across the 4 tiers.
  - **Catalog** (`catalog_seed.py`): `Flash tape 3 3/4" x 90'` added to both **Siding Accessories** and **LP Siding Accessories** (part #79092500 @ $41.12); `Gutter Sealant` (#71159900 @ $9.31), `Hangars with Screws` (#71160200 @ $2.39), `Pipe Clips` (#71161400 @ $2.58) added to **Seamless Gutter**. All wired into `IDENTICAL_PRICES`, `ITEM_META` (unit=`Each`), and `ITEM_AMI` (part numbers).
  - **DB migration bug fix** (`services.py`): when SECTION_LAYOUT was extended to include these items during a previous hot-reload race, the rebuild loop landed the rows with `mat=$0.00` (`TIER_PRICES` didn't have the entries yet at that moment, and on subsequent boots the item-set hash matched so the section wasn't re-built). Added a new Iter 78e idempotent backfill block, bounded to these 4 item names, that force-sets `mat` from `TIER_PRICES` on any tier doc where the value is stale. Pattern mirrors the existing LP / Windows price-sync blocks.
  - **Verified**: direct DB inspection on all 4 tiers shows correct prices ($41.12 / $9.31 / $2.39 / $2.58) post-restart; `GET /api/catalog` echoes the same.

- **Iter 69 — Zero labor on all siding-tab lines (2026-06-22)**: Howard's rule: "all labor entries to be $0 in the siding estimates; leave windows as is." Two-part fix:
  - **Backend migration** (`services.py`): idempotent `update_many` zeros `lab` on every estimate line whose `tab ∈ {vinyl, ascend, lp_smart}`. 44 lines wiped across existing estimates (Gutter 6", Downspout 6", Cap doors, Tear-Off line items inheriting from the old vinyl/ascend defaults).
  - **Frontend lockdown** (`SectionAccordion.jsx`): LAB `<input>` rendered read-only with greyed styling on siding-tab rows; reset-to-default chip suppressed; the input still occupies the column so layout stays aligned with windows-tab rows. Vero/Mezzo/Windows rows untouched.
  - **Verified**: 18 hover + parity tests pass; LP SMART total on EST-627357 dropped $46,976 → $45,338 after wipe. UI screenshot confirms Gutter 6" row LAB column shows `0` in read-only greyed state.

- **Iter 68 — LP HOVER auto-fill starter pack (2026-06-22)**: Wired HOVER measurements into the new BlueLinx LP rows so the tab doesn't ship empty on import.
  - **New auto-fills**: 440 Trim 4" (inside corners → `(eaves+rakes)÷16`), 540 Trim 4" (window/door wrap → `(30×14 + 5×21 + 1×25 + 1×32)÷16`), .019 Coil (default 1/job flashing), Touch up kits (1/job), OSI Quad Max Caulking (2/job), J blocks (`max(4, win/6+doors/2)`), Mini Splits (`max(1, entry/2)`).
  - **Soffit split**: 16×16 Vented now uses `eaves_lf÷16` (vented goes on eaves for attic vent path); new 16×16 Closed row uses `rakes_lf÷16` (closed goes on gable ends).
  - **Iter 68a** — Reverted 6" Lap auto-fill after preview double-counted with 8" Lap. 6" Lap stays manual; contractor swaps in if not using 8".
  - **LP tab went from 5 → 19 auto-filled rows** on a HOVER import. Lightbulb list updated with the new rows.
  - **2 stale references fixed** in `routes/hover.py` (`LP Outside corners 4"` → `540 Series OSC 5/4" x 4"`, `LP Soffit 16" Vented` → `38 Series Soffit 16 x 16 Vented`).
  - **Files**: `backend/routes/hover.py`, `frontend/src/lib/commonItems.js`.

- **Iter 67 — LP SmartSide repriced + renamed to BlueLinx names (2026-06-22)**: Howard re-enabled the LP tab and supplied a new BlueLinx Expertfinish price sheet (PIT00003 v2.26.2026). Rebuilt LP catalog end-to-end:
  - **Per-tier margin pricing** (replaces flat single-tier LP pricing). Sell = Cost ÷ (1 − margin). Tier margins: `one-opp` 20% (÷0.80), `Builder-Dealer` 25% (÷0.75), `Contractor` 30% (÷0.70), `whole-sale` 35% (÷0.65). All 26 LP line items + 3 new coil items computed at module-load time from `LP_COSTS` (cost dict) + `_LP_MARGIN_DIVISOR`.
  - **Unit consolidation: only PCS pricing** (Howard's directive "remove LF pricing and its formula"). All 11 trim items flipped LF → PCS per 16' board; 8" Lap flipped SQ → PCS per board (HOVER mapper now emits `round(sqft × 0.11)`).
  - **BlueLinx names** — 19 renames (e.g. `LP Strand Lap Siding 3/8" x 8" x 16'` → `38 Series Lap 3/8" x 8" x 16'`, `LP 440 Trim 3/4" x 4" x 16'` → `440 Series Trim 4/4" x 4" x 16'`, `LP Outside corners 4" x 16'` → `540 Series OSC 5/4" x 4" x 16'`, `LP Touch-up Kit` → `Touch up kits`, `LP Caulking Color Match` → `OSI Quad Max Caulking`, etc). Trim dimensions corrected: 190 Series 5/8 → 19/32, 440 Series 3/4 → 4/4, 540 Series 3/4 → 5/4. Two 24" soffit rows renamed to BlueLinx codes (`24 inch CTW soffit`, `24 inch VSSFT`).
  - **4 new items added**: 38 Series Lap 3/8" x 6" x 16', Soffit 12 x 16 Vented + Closed, Soffit 16 x 16 Closed.
  - **3 new coil rows** added to LP Siding Accessories — `.019 Coil` / `PVC Trim Coil` / `Performance G8 Trim Coil`. Per-tier prices mirror the vinyl-side rows exactly (driven from `PER_TIER_PRICES` at module-load so any vinyl coil price change propagates automatically). Replaces the dropped `LP Color Match Coil`.
  - **Idempotent migration** in `services.ensure_tiers_seeded` (Iter 67 block): renames in tier docs + estimate lines, LF→PCS qty conversion (`ceil(qty/16)`) + mat rescale (`× 16`), SQ→PCS Lap qty conversion (`× 11`) + mat rescale (`÷ 11`) so line totals stay consistent across the migration. In-flight cleanup heuristic catches half-migrated lines from earlier hot-reload races (Lap PCS row with mat > $100 → ÷ 11; Trim PCS row with mat < $5 → × 16).
  - **HOVER mapper** updated: 8" Lap extract now emits PCS qty = `round(sqft × 0.11)` (11 PCS per Sq).
  - **Lightbulb highlights** (`commonItems.js`) updated to new BlueLinx names.
  - **Pricing-parity test** updated to the new 8" Lap per-tier grid.
  - **Verified**: 46 tests pass; UI screenshot confirms LP tab renders all 4 sections with new names, PCS units, and correct per-tier prices. Existing John Derunk estimate's Lap line correctly migrated from `21 SQ × $298.24` → `229 PCS × $27.11 = $6,208.19` (same line total, new schema).
  - **Files**: `backend/catalog_seed.py` (SECTION_LAYOUT + ITEM_META + LP_COSTS + per-tier merger), `backend/services.py` (Iter 67 migration block), `backend/routes/hover.py` (Lap mapper PCS update), `backend/tests/test_pricing_parity.py`, `frontend/src/lib/commonItems.js`, `frontend/src/lib/tabsConfig.js` (lp_smart re-enabled).

- **Iter 66 — End Cap lightbulb + LP tab visibility (2026-06-22)**:
  - End Cap row added to `COMMONLY_NEEDED_ITEMS` (yellow row + 💡 lightbulb across all 3 siding tabs).
  - LP Smart tab flipped back to visible in `tabsConfig.js` per Howard's request to work on LP pricing.

- **Iter 65 — End Cap added to Seamless Gutter (2026-06-22)**: Howard's ask: "I do need to add end caps to the gutter section in siding estimates each end cap costs $2.08 for all pricing tiers." Shipped:
  - **Catalog**: new `End Cap` row added to `Seamless Gutter` section across all 3 siding tabs (vinyl / ascend / lp_smart). Priced at **$2.08 / Each** on all 4 tiers (whole-sale / Contractor / Builder-Dealer / one-opp) via `IDENTICAL_PRICES`. Inserted between `Mitre` and `Gutter Guard (USA Shurflo)` in the section's item list.
  - **HOVER auto-population**: new spec in `HOVER_MAPPING_SPEC` extracts End Cap qty using the rule **2 end caps per gutter run** (industry standard — caps both ends of every continuous run). Run count estimated as `max(2, ceil(eaves_lf / 40))` since HOVER doesn't expose a gutter-run count directly. Sample: 100 LF eaves → 3 runs → 6 caps; 200 LF → 5 runs → 10 caps. Note string surfaces the formula breakdown to the contractor.
  - **DB migration**: targeted idempotent backfill in `services.ensure_tiers_seeded` force-sets `mat=2.08` on any `End Cap` row currently at $0 (covers the first-boot hot-reload race that landed the row before `IDENTICAL_PRICES` had the price). Idempotent — finds nothing on subsequent boots once all 4 tiers are at $2.08.
  - **Files**: `backend/catalog_seed.py` (SECTION_LAYOUT + ITEM_META + IDENTICAL_PRICES), `backend/routes/hover.py` (new End Cap extract spec), `backend/services.py` (idempotent mat backfill).
  - **Verified**: pytest pricing-parity + hover-perimeter suites pass (18/18); DB shows all 4 tiers at $2.08; UI screenshot confirms End Cap row renders in the Seamless Gutter section of an existing estimate with `mat=$2.08`, `unit=Each`, qty empty (ready for HOVER import or manual entry).

- **Iter 76 — Two-step Home Picker (ISS vs Contractor) (2026-02-23)**: Howard's sketch reorganized the landing screen into two quote families. Shipped:
  - **Step 1 — top picker** (`/`): two large cards — **ISS Quotes** and **Contractor Quotes** (`HomePicker.jsx` rewritten, icons: Building2 / HardHat).
  - **Step 2A — `/picker/iss`** (`IssPicker.jsx`, new): three sub-cards — *ISS Siding Quotes* → `/dashboard/iss`, *ISS Window Quotes* → `/dashboard/windows`, *ISS New Construction Siding Quotes* → disabled "Coming Soon" card (dashed border, pending catalog from Howard).
  - **Step 2B — `/picker/contractor`** (`ContractorPicker.jsx`, new): three sub-cards — *Window Quotes* → `/dashboard/windows` (mirrors ISS Windows for now per Howard; labor will diverge later), *Vinyl + Ascend Siding Quotes* → `/dashboard/siding`, *LP SmartSide Quotes* → `/dashboard/lp_smart`.
  - Each sub-picker has a `← Back` button and a section tag header matching the group name. All cards have `data-testid` hooks.
  - **i18n**: full EN + ES translations added to `dictionaries.js` for the new keys (`home.issGroupTitle`, `home.contractorGroupTitle`, `home.iss.*`, `home.contractor.*`, `home.issWindowsTitle`, `home.issNewConTitle`, `home.back`).
  - **Routes**: `App.js` adds `/picker/iss` and `/picker/contractor` inside the Protected/Layout shell.
  - **Files**: `frontend/src/pages/HomePicker.jsx` (rewrite), `frontend/src/pages/IssPicker.jsx` (new), `frontend/src/pages/ContractorPicker.jsx` (new), `frontend/src/App.js` (routes), `frontend/src/lib/dictionaries.js` (EN/ES keys).
  - **Verified**: Playwright smoke test logs into the live preview, clicks ISS group → confirms 3 cards render, back, clicks Contractor group → confirms 3 cards render. All 3 screens screenshot cleanly with no console errors.


- **Iter 78t — Elevation drawings removed from customer quote PDF/email (2026-02-13)**: Howard reported the AI-generated elevation drawings render walls to scale but place windows/doors approximately (bbox is photo-normalized, not wall-normalized; HOVER vision path doesn't expose per-window x_pct at all). Until we can do a true 3D render, the customer-facing PDF + email no longer embed the SVGs — contractors still see them in-app (AI Measure modal, HOVER Import modal, Blueprint Measure modal, and Compare Drawings modal) and can drag-nudge any opening + cycle the roof shape. Changes: `frontend/src/lib/emailQuote.js` (commented out `buildElevationsBlock` import + removed `${elevationDrawingsBlock}` from HTML template). `emailElevations.js` kept in place for future re-enable.

- **Iter 78u — 3D elevation renderer scaffolded (Three.js, 2026-02-13)**: Set up the infrastructure to bring elevation drawings back to the customer PDF — this time as true 3D orthographic renders instead of approximate 2D SVGs. Shipped:
  - **`frontend/src/lib/elevation3D.js`** (new): `buildElevationScene(elev)` builds a complete THREE.Scene (wall + horizontal siding stripes + roof shape per style + per-opening meshes: windows with mullions + glass, doors with panels + knob, garage doors with stripes, patio doors in purple). `renderElevationToPng(elev, {pxWidth, pxHeight})` renders the scene off-DOM via WebGL and returns a PNG data URL — ready to embed in the WeasyPrint customer PDF when we re-enable it.
  - **`frontend/src/components/estimate/Elevation3DPreview.jsx`** (new): React wrapper that mounts `buildElevationScene()` into a WebGL canvas for in-app preview. Disposes geometry/materials on unmount.
  - **`frontend/src/lib/elevationBuilder.js`** (rewrite): Position fallback — when AI/HOVER doesn't return wall-relative coordinates, openings are evenly distributed horizontally (1 → 50%, 2 → 33/67%, 3 → 25/50/75%, etc.) and vertically placed using industry-standard sill heights (windows 36" / doors 0" / garage 0" / patio 0" / vents 78"). Also passes `gable_triangle_height_ft` through so the 3D roof gets the right peak.
  - **`AIMeasureButton.jsx`**: Added `[View 3D]` ↔ `[Edit (2D)]` toggle button on the Elevation Drawings card. 2D stays as the nudgeable editor; 3D shows the customer-PDF-grade preview.
  - **Dependency**: `three@0.184.0` added via yarn.
  - **Not yet wired**: Headless render → PNG → embedded in customer Quote PDF/email. That's the next step once Howard confirms the in-app 3D preview looks right.
  - **Verified**: ESLint clean across all 4 touched files. Smoke screenshot shows the app loads with no compile errors.


- **Iter 78v — Dormer rendering + Deep Dormer Scan default ON (2026-02-13)**: Howard's test house has dormers; they were missing from both the elevation drawings and the siding ft² total. Two stacked bugs:
  - **Bug 1 — Total**: Backend math already adds `dormer_face_sqft` to siding ft², but Claude's main pass downsizes phone photos to ~1568px and small dormers vanish. The "🔍 Deep Dormer Scan" 2nd pass (which crops the top 38% of each photo at 2× upscale) was opt-in and hidden inside the Calibration sub-panel. **Fix**: defaulted to `true` (`AIMeasureButton.jsx` — `useState(true)`). Costs ~5-10s, biggest quote-accuracy lever in the prompt.
  - **Bug 2 — Drawing**: Neither the 2D SVG (`ElevationDrawing.jsx`) nor the new 3D scene (`elevation3D.js`) read `wall.dormer_face_sqft`. **Fix**: pass `dormer_face_sqft` through `elevationBuilder.js`; in 3D, added `inferDormerCount` + `buildDormer` + `addDormersToScene` (splits ft² into 1-4 dormer boxes evenly distributed across the roof, each rendered as a small gabled box with a centered double-hung window); in 2D SVG, added a mirror `inferDormerCount` + an SVG render block (dormer roof triangle + face rect + blue window glass per dormer). Bumped 3D camera headroom to accommodate dormers protruding above the roof.
  - **Verified**: ESLint clean across all 3 touched files. Smoke screenshot confirms the app loads. Howard can test by re-running AI Measure on a dormered house — the deep dormer scan will fire automatically, dormer ft² will land in the total, and the drawings (2D and 3D) will visibly show the dormers on the roofline.

- **Iter 78w — Mezzo window prices refreshed from Howard's V1 sheets (2026-02-13)**: Howard uploaded 3 new Alside Mezzo East Replacement price sheets (whole-sale / Contractor / Builder-Dealer). Built a one-shot extractor (`/tmp/mezzo/extract.py`) that parses each Excel's `Mezzo` tab for all 4 product types (Double-Hung / 2-Lite Slider / 3-Lite Slider / Picture) across all UI size buckets and all 9 adders (Extruded Beige/Clay, ClimaTech Plus 9E, ClimaTech TG2 Plus, Grid 1" Contour, Obscure Full, Tempered Full, NAILFIN, Black Exterior Paint, CHERRY LAMINATE). Merged into `backend/mezzo_seed_prices.json` (preserving the `one-opp` tier untouched — no new sheet for it).
  - Wrote `backend/migrate_mezzo_prices.py` to upsert the 12 (tier × product) docs into MongoDB live (idempotent — `seed_mezzo_prices()` only runs on first boot, this migration force-refreshes existing docs).
  - Ran migration successfully. Verified via `GET /api/admin/mezzo/prices`:
    - Mezzo DH @ UI 32-73: whole-sale $237.97 · Contractor $216.34 · Builder-Dealer $194.71
    - Mezzo Picture @ UI 21-63: whole-sale $196.32 · Contractor $178.47 · Builder-Dealer $160.63
    - Sample adder: Extruded Beige (Contractor / DH @ UI 32-73) = $19.31
  - **Impact**: Both flows that read Mezzo pricing pull from the same `db.mezzo_prices` collection keyed by company's `price_tier_id`, so this single update covers Contractor Window Quotes AND ISS Window Quotes simultaneously — no separate path needed.
  - **Files**: `backend/mezzo_seed_prices.json` (regenerated), `backend/migrate_mezzo_prices.py` (new — safe to re-run any time Howard ships new price sheets).

- **Iter 78x — P1: LP catalog aligned to current supplier sheet (2026-02-13)**: Howard delivered the new Pro-Quotes Master Excel and the LP supplier raw price sheet. P1 of the master-pricing rollout shipped:
  - **Dropped 4 LP SKUs** LP discontinued (per supplier sheet): `38 Series Lap 3/8" × 6" × 16'`, `38 Series Soffit 12 × 16 Vented`, `38 Series Soffit 12 × 16 Closed`, `38 Series Soffit 16 × 16 Closed`. Removed from `SECTION_LAYOUT`, `ITEM_META`, `LP_COSTS` + idempotent `$pull` migration in `services.py` that wipes them from existing `db.price_tiers` docs. Saved estimate lines keep their snapshot prices per Howard's rule.
  - **Added `Trim Coil Aluminum 24" × 50'`** to LP Siding Accessories at $156.25 cost. Auto-priced into all 4 tiers via the existing gross-margin formula (`sell = cost ÷ (1 − margin)`): whole-sale $240.38 (35% margin) · Contractor $223.21 (30%) · Builder-Dealer $208.33 (25%) · one-opp $195.31 (20%). `build_tier_sections()` rebuild on boot picks it up automatically.
  - **Exposed `LP_MARGIN_PCT`** dict (35/30/25/20) in `catalog_seed.py` so the upcoming Pricing Admin UI can render "$33.37 — 35% margin" next to each LP price.
  - **Regression test suite**: 7 pytests in `backend/tests/test_lp_catalog.py` lock in the 4 deletions, the new SKU's cost basis, and the margin formula per tier. All passing.
  - **Verified live**: `GET /api/admin/tiers` confirms all 4 tier docs have the 4 SKUs gone + Trim Coil Aluminum present at the correct margin-computed prices.
  - **Status of master-pricing rollout**: P1 done (LP catalog changes). P2-P5 (Mezzo list-price refactor, Importer engine, Admin UI, polish) await Howard's go-ahead.

- **Iter 78y — Vero collapsed to match master pricing file (2026-02-13)**: Howard delivered the new Vero tab in Pro-Quotes Master Excel. Big architectural simplification:
  - **3 tiers only** (was 4): whole-sale (35% margin) / Contractor (30%) / Builder-Dealer (25%). `one-opp` removed from `VERO_TIER_NAMES`. Legacy one-opp companies fall back to Builder-Dealer pricing via `compute_tier_price` for new estimates; saved snapshots stay frozen.
  - **3 product types only** (was 5): Vero Double Hung, Vero 2-Lite Slider, Vero Patio Door. **3-Lite Slider + Picture removed entirely**; idempotent `delete_many` in `startup.py` purges them from `db.vero_prices` on every boot.
  - **DH + 2-Lite Slider use a single UI bucket "0-101"** (was 14 buckets each going to 171-180 UI).
  - **Patio Door = 3 fixed models** (4792PD 2 Panel 5068 / 6068 / 8068) at Howard's supplier-sheet costs ($718.19 / $780.29 / $877.16).
  - **8 adders** replace the previous 12 (Climatech Plus, Solid Color Flat Grids, Foam Wrap, etc. → Quattro .25, Elite TG2 .24, TG2 Triple Pane .19, Head Expander 0-101, Grids, Sentry System - Tilt Lock, Integral Nail Fin 0-101, Heavy Duty 1/2 Screen White ONLY). All margin-computed per tier.
  - **Canonical cost basis lives in `vero_catalog.py`** (`VERO_BASE_COSTS`, `VERO_PATIO_COSTS`, `VERO_ADDER_COSTS`, `VERO_MARGIN_PCT`, `compute_tier_price()`). Single edit point for the next supplier price refresh.
  - **`build_vero_seed.py`** generates `vero_seed_prices.json` from the cost basis. Force-refresh on boot via `seed_vero_prices(force=True)` after dropping obsolete docs — Howard's price changes land immediately on next deploy.
  - **`_guess_vero_product_type()`** in `routes/hover.py` updated to only return DH or 2-Lite Slider (Casement/3-Lite/Picture removed); legacy `_VERO_TO_MEZZO` map keeps fallback rows for old saved vero_openings.
  - **15 new regression pytests** in `tests/test_vero_iter_78y.py` + `tests/test_lp_catalog.py` lock in the new pricing structure. Updated `tests/test_vero_pricing.py`, `test_vero_iter_b.py`, `test_hover_window_style.py` to match new structure. 47 tests in this scope all pass.
  - **Verified live**: Wholesale $287.57 / Contractor $267.03 / Builder-Dealer $249.23 for DH 0-101 (matches $186.92 cost ÷ tier margin formula). Patio Door 5068: WS $1104.91 / Contr $1025.99 / BD $957.59.
- **Status of master-pricing rollout**: P1 (LP) ✓ + Vero (Iter 78y) ✓ done. Mezzo list-price refactor (P2) and master Excel importer engine (P3-P5) await Howard's go-ahead.

- **Iter 78z++ — Annotator zoom + fullscreen + polygon offset fix (2026-02-27)**: Howard reported the Blueprint annotator polygon vertices were rendering offset from the mouse, and asked for zoom controls + a fullscreen expand button so he can place vertices accurately on dense plan sheets.
  - **Polygon offset root cause**: The stage was `inline-block max-w-full` with a `<svg viewBox="0 0 100 100" preserveAspectRatio="none">` overlay positioned via `absolute inset-0`. The inline-block + inline-default SVG sizing created a 1-3px height mismatch between the SVG box and the rendered image (browser baseline gap on the replaced image element). With `preserveAspectRatio="none"` stretching the viewBox to that mismatched box, polygon points landed a few pixels off where they were clicked.
  - **Fix**: Rebuilt the stage as `<div className="relative" style={{ width: \`${zoom * 100}%\`, lineHeight: 0 }}>` with the image at `display: block; width: 100%; height: auto`. Polygon + draft + scale SVG overlays switched from `absolute inset-0` to `absolute top-0 left-0` with explicit `display: block; width: 100%; height: 100%` styles — pixel-locked to the image box.
  - **Zoom**: Wheel-to-zoom anchored at the cursor (re-anchors `containerRef.scrollLeft/Top` so the world-point under the cursor stays put). Toolbar buttons for `−` / `%` readout / `+` / `Fit`. Hard-clamped to `[0.5×, 8×]`. Reset on photo switch so each page starts fitted.
  - **Fullscreen**: Toolbar toggle (`Maximize2` / `Minimize2`). Modal switches between `max-w-6xl h-[90vh]` (default) and `w-full h-full max-w-none` (with outer `p-0` so it truly covers the viewport).
  - **Files**: `frontend/src/components/estimate/ProfileAnnotator.jsx`. No backend changes. Lint clean, webpack compiled.
  - **Status**: SHIPPED — USER VERIFICATION PENDING (Howard needs to re-test polygon placement on a Blueprint upload + try wheel-zoom + Expand button).

- **Iter 78z+++ — Job Information visual cleanup (2026-02-27)**: Howard said "the job information is starting to get a little hard to look at and comprehend." Header had 8 interactive surfaces (Import HOVER, Restore HOVER, Read Blueprints, Tag Profiles, Default Waste caption, Previous Read banner with 2 buttons, AI Measure, Pair to LP), 4 different button colors, and a giant yellow "Previous Read Available" banner dominating the page. Shipped the full proposal (option B):
  - **3-tile measurement layout**: `JobInfoPanel` header is now a 3-column grid (HOVER PDF · Blueprints · AI Photo Measure), each tile carrying an icon + uppercase label and the corresponding launcher (`HoverImportButton` / `BlueprintMeasureButton` / `AIMeasureButton`). Sub-actions (Restore HOVER Lines, Tag Profiles, default-waste caption, resume banner) now live INSIDE the relevant tile, so each importer is visually self-contained.
  - **Compact resume banner**: The Blueprint "Previous Read Available" yellow card collapsed to a single `text-[10px]` line — `⚠ PREVIOUS READ · 9 PG · 13 MIN · RESTORE · DISMISS` — fits inside the Blueprints tile.
  - **Pair-to-LP demoted**: Moved out of the header tile row into a low-emphasis right-aligned row below the tiles (it's a workspace switcher, not a job-info action). Compare Drawings (which only shows when 2+ measurement sources exist) lives in the same row.
  - **Collapsible form fields**: Once `customer_name` + `address` are both filled, the form (Customer/Address/EST#/Date/Estimator/Scope/Colors) auto-collapses to a one-line summary in the section header — `JOB INFORMATION · John Smith · 123 Main St · EST-836053` — with an `▼ EDIT` toggle to re-open. Saves ~600px of vertical scroll on every estimate after the basics are entered.
  - **De-duped title**: `StickyBar` no longer shows `Customer · EST-#####`; once a `customer_name` is set, the title shows just the customer name (the EST# stays editable in the form field).
  - **Files**: `frontend/src/components/estimate/JobInfoPanel.jsx` (tile layout + collapse), `frontend/src/components/estimate/BlueprintMeasureButton.jsx` (compact resume banner), `frontend/src/components/estimate/StickyBar.jsx` (title dedupe). Lint clean. No backend changes.
  - **Status**: SHIPPED + verified via screenshot on live estimate (EST-836053). USER VERIFICATION PENDING.


- **Iter 78aa — Vero adders dropdown fix (2026-02-28)**: Howard reported that the Upgrade Options dropdown on Vero windows was empty. Root cause: `VeroPanel.jsx` still had Iter-44 hardcoded adder names (`Climatech Plus`, `Foam Wrap`, `Obscure Full`, `Oriel Style Double Hung`, etc.) in `ADDER_ROWS`, `DEFAULT_ADDER`, and `EXCLUSIVE_PAIR`. The Iter 78y catalog rewrite replaced those with the 8 Howard-master adders (`Quattro .25 U Factor`, `Elite TG2`, `TG2 Triple Pane/Argon`, `Head Expander 0-101`, `Grids`, `Sentry System`, `Integral Nail Fin 0-101`, `Heavy Duty 1/2 Screen White ONLY`), so the frontend name-lookups returned `undefined` and every adder row rendered empty.
  - **Fix**: Replaced `ADDER_ROWS` with a 2×4 grid matching the Pro-quotes Master Catalog Excel left→right column order. `DEFAULT_ADDER = ""` (base price already includes Climatech Plus, so no auto-applied upgrade). Replaced `EXCLUSIVE_PAIR` with `GLASS_PACKAGE_GROUP` — the 3 glass packages (Quattro / Elite TG2 / TG2 Triple Pane) are mutually exclusive; selecting one auto-removes the others from `op.adders`.
  - **Pricing verified**: All adder prices computed via Vero margin formula `sell = cost / (1 - margin%)` (35% wholesale / 30% Contractor / 25% Builder-Dealer). Sample @ wholesale: Quattro $57.32, Elite TG2 $85.51, TG2 Triple $102.71, Head Expander $5.74, Grids $46.34, Sentry $41.08, Nail Fin $21.02, Heavy Duty Screen $27.71. Excel master pricing matches DB seed (no Mongo migration needed).
  - **Files**: `frontend/src/components/estimate/VeroPanel.jsx` only. Verified on live estimate `EST-658882-W` — all 8 upgrades render with correct per-each prices.
  - **Status**: SHIPPED + self-tested via screenshot. USER VERIFICATION PENDING.

- **Iter 78ab — LP SmartSide AI formulas + Admin go/no-go preview (2026-02-28)**: Howard supplied an LP_SmartSide_Reference.pdf with material-quantity formulas for 5 LP families (Lap 6/7/8/12" · Shakes 6⅞–9⅞" reveal · Nickel Gap fixed 7" · Soffit 12/16/24"/4×8 · Board & Batten 4×10 panel + 12/16/24" o.c. battens). User chose: D = apply to HOVER + AI Photo + Blueprint + manual entry; defaults 8" Lap / 16" Soffit / 7" shake reveal; STAGE behind a feature flag; auto-fill material qty only; keep existing trim/accessory formulas; bump 540 Series for shakes; skip Nickel Gap J-channel for now (keep in memory); batten SKU is `190 Series Trim 19/32" × 3" × 16'`.
  - **New module** `/app/backend/lp_smartside_formulas.py` — single source of truth with `is_enabled()` env check + `override_flag` context manager, coverage tables per profile (8" Lap 9.17 / 7" Shake 2.33 / 16" Soffit 21.3 / Nickel Gap 9.33 / B&B 40 sqft/PCS), `pieces_needed`/`lap_pieces`/`shake_pieces`/`nickel_gap_pieces`/`soffit_pieces`/`board_batten_panel_pieces`/`board_batten_batten_pieces` helpers (10% waste + round-up), `shake_540_series_bump` (+2 pcs of 5/4"×4"×16' per 100 sqft of shake field per LP "recommends 540 Series for 7"–10" reveals"). `NICKEL_GAP_J_CHANNEL_NEEDS_REVIEW` constant held for a future iteration.
  - **Single integration point**: `routes/hover._build_lines` is shared by HOVER PDF, AI Photo Measure, AI Blueprint, AND `routes/estimates._build_default_estimate_lines` (manual entry), so one flag flip covers all four ingest paths. Wired via `_lp_profile_sku_entry()` override on `_PROFILE_SKU_MAP` plus two new auto-fill rules in `HOVER_MAPPING_SPEC`:
    * `190 Series Trim 19/32" × 3" × 16'` — batten strips, formula `ceil(wall_sqft × 0.75 LF/sqft × 1.10 ÷ 16)` (PDF default 16" o.c.). Only emitted when B&B profile is in `_per_profile_sqft` AND the flag is ON.
    * `540 Series Trim 5/4" × 4" × 16'` — added `shake_540_series_bump` on top of the existing window/door wrap formula so shakes auto-add belly-band trim.
    * `38 Series Lap 3/8" × 8" × 16'` default-siding row swaps `sqft × 0.11` → `ceil(sqft / 9.17 × 1.10)` when flag is ON. Same SKU, different math.
  - **Staging flag**: `LP_AI_FORMULAS_V1=false` added to `backend/.env`. While OFF, legacy 9.09 sqft/PCS behavior is preserved end-to-end. Flip to `true` + `sudo supervisorctl restart backend` when ready to go live.
  - **Admin Go/No-Go preview tool** — new `POST /api/admin/lp-formula-preview` + `GET /api/admin/lp-formula-preview/presets` endpoints (token-gated via `X-Admin-Token`). Runs `_build_lines` twice inside one request (`override_flag(False)` then `override_flag(True)`) and returns a side-by-side diff of LP-only lines: `{section, name, unit, legacy_qty, pdf_qty, delta_qty, delta_pct, legacy_note, pdf_note}`. 4 built-in presets: campbell / shake_heavy / bb_heavy / lap_only. New frontend page `/lp-formula-preview?token=...` (mirrors the branding-admin auth pattern) — dropdown picker + Run button + summary tiles + colour-coded diff table + live STAGED/LIVE banner showing the current env-flag state.
  - **Live Campbell-preset delta** (verified): Shake 44 → 189 PCS (+329.5%) — legacy heavily under-counted shakes; Lap 264 → 288 PCS (+9.1%); 190 Series 0 → 11 PCS (new batten line); 540 Series 18 → 26 PCS (+44%, shake belly-band bump). Howard can confirm these numbers before flipping the flag.
  - **Files**: `backend/lp_smartside_formulas.py` (new), `backend/routes/lp_admin.py` (new), `backend/routes/hover.py` (flag-aware wiring), `backend/routes/__init__.py` (router registration), `backend/.env` (flag default), `frontend/src/pages/LpFormulaPreview.jsx` (new), `frontend/src/App.js` (route).
  - **Tests** — `tests/test_lp_smartside_formulas.py` (26 new tests covering both flag states + integration with `_build_lines`); all 26 + 31 existing regression tests pass. Testing agent: 100% backend (12/12 new HTTP + 57/57 regression), 100% frontend on LP preview UI, no critical/minor issues. Lint clean throughout.
  - **Status**: SHIPPED + tested via testing agent. AWAITING HOWARD'S GO/NO-GO DECISION on the flag flip.

- **Iter 79 — Vinyl/Ascend Master Catalog Sync (Feb 2026)**: Howard uploaded an updated `Pro-quotes Master price Catalog.xls` (v2) with renamed SKUs and a restructured Porch Ceiling section. After running a per-tier diff against the live DB, applied:
  - **19 price changes**: Ascend Starter $7.68 → $8.83 (all 4 tiers); ASCEND Finish Trim $7.86 → $8.25; Siding Accessories Starter $7.46 → $7.64; Ascend 5.5" Trim BD $61.05 → $71.66 (aligns BD with other tiers); Cap porch band Contractor/one-opp $2.94/$2.66 → $0; Wrap porch beam all tiers → $0.
  - **6 SKU renames** (with `ITEM_NAME_ALIASES` aliases for back-compat): `Charter Oak Soffit Standard color` → `Soffit & fascia Charter Oak Standard Color`; `Charter Oak Soffit Architectural color` → `Soffit & fascia Charter Oak Architectural color`; `Greenbriar Soffit` → `Soffit & fascia Greenbriar`; `T2 Soffit` → `Soffit & fascia 2T`; `1/2" Soffit J-Channel (for T2 Soffit)` → `1/2" J-Channel (2 per Sq of siding) White`; `RainDrop House Wrap` → `RainDrop`.
  - **Porch Ceiling restructure**: `With or without siding Charter Oak` (SQ FT, $1.40–$2.02/sqft) → `Charter Oak Soffit White` (PCS, $14.00–$20.20/piece, aligns with Vinyl Soffit Standard Color piece price). Auto-recalc hook updated to convert `porch_sqft ÷ 10 → pieces`. Existing estimate lines migrated in place (unit flipped, qty/10, mat×10) so dollar totals stay flat.
  - **"Inside Corners" (Ascend Cladding/Accessories) dropped** per supplier sheet.
  - **HOVER mapper** + **TakeoffReconCard** + **commonItems** + **itemDescriptions** updated to use new names.
  - **Porch Ceiling math hint UI**: small grey caption under the auto-populated Porch Ceiling row qty showing the per-porch derivation (e.g. `22'×10' + 12'×8' = 316 sqft → 32 pcs (Front Porch, Side)`). Beam wrap shows LF math (`22'+2×10' = 42 LF`). Hidden on mobile (`hidden md:block`).
  - **Files**: `backend/catalog_seed.py` (SECTION_LAYOUT + ITEM_META + IDENTICAL_PRICES + PER_TIER_PRICES + ITEM_AMI); `backend/services.py` (Iter 79 migration block + extended BACKFILL); `backend/routes/hover.py` (2 mapping rules renamed); `frontend/src/lib/useRecalcSoffitOnOverhang.js` (PCS conversion); `frontend/src/lib/catalogTranslations.js` (alias map flipped); `frontend/src/lib/commonItems.js`; `frontend/src/lib/itemDescriptions.js`; `frontend/src/components/estimate/PorchCeilingsCard.jsx` (new `porchMathHint` helper); `frontend/src/components/estimate/SectionAccordion.jsx` (math-hint render); `frontend/src/components/estimate/TakeoffReconCard.jsx`.
  - **Status**: SHIPPED + verified via direct DB query + catalog API smoke test on all 4 tiers + lint clean. USER VERIFICATION PENDING — open any Vinyl/Ascend estimate and check the Vinyl Soffit + Porch Ceiling sections for the new SKU names and PCS pricing.

- **P2 — Admin → Async Jobs panel** (deferred Feb 2026): small admin-only dashboard listing the last 50 runs across `hover_import_runs`, `ai_measure_runs`, and `ai_blueprint_runs` collections. Columns: type · status · stage · elapsed · user · "Retry" button on error rows · link to the source estimate. Doubles as an ops dashboard (catch stuck/error patterns) and a customer-support tool (when a contractor says "the upload didn't work", see the exact stage + error in 2 clicks).

- **Iter 79j.2 — Guided Photo Capture: 5-step sequence fix (2026-02-28)**: Howard reported the Guided Annotate flow was jumping from Wall Measurement straight to Window Style, skipping Window Measurement. Root cause: `guidedSteps` array in `PhotoAnnotateModal.jsx` was missing the `MODE_SCALE_WINDOW` step, AND the big-title switch statement at lines 1301-1307 still used stale keys (`window`, `style`) that didn't match the renamed keys (`window-measure`, `window-style`), so even after adding the step the title would render blank.
  - **Fix (2 parts)**:
    1. `guidedSteps` array now injects `MODE_SCALE_WINDOW` (key `window-measure`) as step 2 between Wall (`MODE_SCALE`) and Window Style (`MODE_WINDOW`). Sequence is now exactly: Wall Measurement → Window Measurement → Window Style → Mask → Profile.
    2. Big-title switch updated to match new keys: `wall` → 🎯 Wall Measurement, `window-measure` → 📏 Window Measurement, `window-style` → 🪟 Window Style, `mask` → 🧱 Mask (brick / stone), `profile` → 🏠 Profile.
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only. Lint clean.
  - **Verification**: `testing_agent_v3_fork` iter 28 — 100% pass. All 5 step titles + banners + skip labels + Next/Save-&-Continue label + progress-dot counts + "Step X of 5" counter verified end-to-end on a fresh Vinyl+Ascend estimate. Howard's regression definitively fixed.
  - **Status**: SHIPPED + testing agent verified. USER VERIFICATION PENDING.

## Shareable read-only accuracy report link (APPROVED but BACKLOGGED, 2026-07-10)
Sequenced behind the FIRST PASSING BLIND HOUSE — the accuracy-claim section it would share is currently empty; build distribution after there's something to distribute. Small build, reuse the Accept page pattern. **Hard requirement**: the read-only view carries the same honest framing pinned by the PDF tests — methodology exhibit vs. accuracy claim kept separate, no blended aggregate — because a shared link travels without Howard in the room to caveat it.

## Visualizer position (Howard's ruling, 2026-07-10)
- **KEEP**: flat-color product swapping on the 3D model — already part of LP package item 8 (ExpertFinish selector repaints meshes).
- **CUT from roadmap entirely**: texture-mapped realism. LP has its own visualizer; our September position is complementary ("my measurement layer + their visualizer"), not competitive.
- **STANDS**: no generative AI renders in the priced view, ever.
- If texture realism ever returns, it returns as an LP partnership request, not our initiative.

## Backlog (P1)
- Dollar amount per elevation under each bar in Per-Elevation Breakdown card
- Contractor Window Quotes: per-quote-type contractor-editable labor (ON HOLD post-September — see Iter 131 for Howard's full feature definition; ISS rates institutional/locked, contractor labor per-line editable defaulting to ISS values, split keys off quote type/picker)
- Add upgrade/option lines to Customer Quote PDF + email
- Real PWA app icons (replace programmatic placeholders)
- ISS New Construction Siding catalog (awaiting Excel from Howard)

## Backlog (P2)
- Unfilled-item safety net: warn before quote send if highlighted items have qty=0
- AI Measure mini-map sidebar: click opening row → photo zooms to that bbox
- WhatsApp share button on Accept page
- SKU-level conversion dashboard
- Wire Three.js static 3D PNG into Customer Quote PDF
- Admin → Async Jobs panel (last 50 runs across the 3 async collections + retry button)

## Refactor (later, once flow is stable)
- Split `PhotoAnnotateModal.jsx` (1600+ lines) into per-step components

- **Iter 79j.3 — Guided Mask/Profile Polygon option restored (2026-02-28)**: Howard reported step 4 (Mask) and step 5 (Profile) only offered the Rectangle drawing option — the Polygon toggle was missing entirely in guided flow. Root cause: the classic-toolbar `{!guidedFlow && ...}` JSX gate wrapped the ENTIRE mode-toolbar section, including the MODE_ZONE and MODE_PROFILE sub-panels that own the Rectangle/Polygon shape toggle + category/family picker + polygon Close/Cancel buttons. In guided mode those sub-panels never rendered.
  - **Fix**: Restructured `PhotoAnnotateModal.jsx` so only the 6-mode top-toolbar button grid (Pin/Wall/Window/Mask/Style/Profile) and the 'Existing annotations' summary lists stay hidden in guided flow. The MODE_ZONE sub-panel (mask shape toggle + 5 zone categories + polygon Close/Cancel) and the MODE_PROFILE sub-panel (profile shape toggle + 9 family picker + polygon Close/Cancel) now render unconditionally whenever their mode is active.
  - **Verification**: `testing_agent_v3_fork` iter 29 — 100% pass. All 9 verification points confirmed: Rectangle + Polygon both visible on Mask and Profile, top toolbar hidden, existing-annotations block hidden, Polygon click toggles active state correctly, zone-category and profile-family grids render as expected.
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only. Lint clean.
  - **Status**: SHIPPED + testing agent verified. USER VERIFICATION PENDING.

- **Iter 79j.4 — Polygon snap-close on Mask & Profile (2026-02-28)**: Howard wanted a tap-to-snap-close UX for the polygon tool on Mask (step 4) and Profile (step 5) so contractors don't have to hunt for a separate 'Close' button after placing all points. If the contractor taps a point within ~18 screen pixels of the first vertex (after ≥3 points are placed), the polygon auto-closes and commits.
  - **Implementation** (`PhotoAnnotateModal.jsx`):
    - New `_isNearFirstPoint(p, first)` helper with zoom-aware threshold `Math.max(8, 18 / max(0.25, zoom))` in photo-px (feels the same on iPad zoom-in or full-photo desktop view).
    - MODE_ZONE and MODE_PROFILE polygon tap paths check the helper before appending a new point — if within threshold and ≥3 points already placed, commit the zone/profile-box and clear `polyPoints`.
    - Visual cue: once ≥3 points exist, the first vertex renders 1.4× larger and a hint-ring appears around it (dashed by default, solid + fully opaque when the hover is within the snap threshold).
    - Banner copy on Mask and Profile updated to include 'tap your first polygon point again to close'.
    - Classic 'Close (N pts)' button remains as a fallback.
  - **Verification**: `testing_agent_v3_fork` iter 30 — 100% pass on both steps. Snap-close committed a Brick mask zone and a Shake profile box (50 ft² sentinel due to no wall anchor set) on real Playwright taps that land within the threshold. Rectangle regression + 5-step guided navigation regression both pass. Lint clean.
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only.
  - **Status**: SHIPPED + testing agent verified. USER VERIFICATION PENDING.

- **Iter 79j.5 — Polygon "Undo last point" button on Mask & Profile (2026-02-28)**: Small UX add per Howard's approval. When a polygon is in-progress on the Mask or Profile step, a new "Undo" button sits between "Close (N pts)" and "Cancel". Removes the most recently placed vertex without wiping the whole shape — critical for Tudor dormers / complex gables where contractors mis-tap 1 of 6 points.
  - Mask row (amber): `data-testid="zone-poly-undo-btn"` · Profile row (violet): `data-testid="profile-poly-undo-btn"`.
  - Implementation: `setPolyPoints((prev) => prev.slice(0, -1))`. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.6 — Polygon snap-close hardening (2026-02-28)**: Howard reported the polygon on the Mask/Profile guided steps appeared to close on the 2nd pick. Root code review confirms the guard is `polyPoints.length >= 3` (min 3 vertices already placed before snap can fire on the next tap), so a strict-triangle minimum is enforced. To eliminate any perception of eager snap and make the armed state unmissable:
  - **Tighter threshold**: `_isNearFirstPoint` snap distance shrunk from ~18 → ~12 screen pixels (floor 10 photo-px). Contractors now have to be squarely on the first vertex, not just adjacent.
  - **Explicit "TAP TO CLOSE" callout**: When ≥3 points are placed AND the hover/pencil is inside the snap threshold, a colored badge (`TAP TO CLOSE`) appears right next to the first vertex — orange on Mask, violet on Profile. Removes any ambiguity about when snap is armed.
  - **Banner copy sharpened**: "For polygon: place at least 3 corners, then tap your first corner again to close" — makes the 3-point minimum explicit.
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.7 — Mask/Profile controls docked into guided banner (2026-02-28)**: Howard's screenshot showed the Rectangle/Polygon shape toggle + zone-category grid rendering at the bottom-left of the modal (below the photo) instead of next to the guided banner on the right. Root cause: the sub-panels lived in the shared right-sidebar container `<div className="space-y-3">`, but on the tested viewport width the panel wrapped below the photo due to the modal's flow. Moved the sub-panels INTO the guided banner itself so they always sit inline with Next/Skip on the right.
  - **Change**: Added compact step-specific control blocks INSIDE the guided banner (right after the banner text, before the Next/Skip button row) for both `MODE_ZONE` (Mask) and `MODE_PROFILE` (Profile). New data-testids: `guided-mask-shape-rect/poly`, `guided-mask-cat-*`, `guided-zone-poly-close-btn/undo-btn`, `guided-profile-shape-rect/poly`, `guided-profile-fam-*`, `guided-profile-poly-close-btn/undo-btn`.
  - Wrapped the outer sub-panels with `!guidedFlow` so they only render in classic mode (no duplication in guided).
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.8 — Sticky right sidebar in annotate modal (2026-02-28)**: Wrapped the guided banner + controls column in a sticky container (`md:sticky md:top-0 md:self-start md:max-h-[calc(100vh-9rem)] md:overflow-y-auto`) so Next/Skip + shape/category stay pinned in thumb range while the contractor scrolls/pinch-zooms the photo below. Own overflow-y-auto lets the sidebar scroll internally when its content is taller than the viewport (e.g. Profile step with a long family list). No changes on mobile (single-column layout unchanged).
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.9 — Guided flow "Back" button + inline delete for committed items (2026-02-28)**: Howard hit two UX gaps: (1) no way to fix a mistake in the previous annotate step without cancelling and re-uploading, (2) no way to delete a committed profile box / window style / mask zone / wall or window scale ref from within the guided banner (the summary lists that had trash icons are hidden in guided mode).
  - **Back button**: New `handleGuidedBack()` decrements `guidedStepIdx` while preserving all committed annotations. Rendered in the guided banner button row as the first button (`← Back`, data-testid `annotate-guided-back-btn`) when `guidedStepIdx > 0`. Contractor can now walk back to Wall / Window Measurement / Window Style / Mask to adjust and then continue forward.
  - **Inline delete lists**: Each guided step now shows the items it committed with a Trash icon per row:
    - Wall Measurement: `data-testid="guided-wall-ref-remove"` — removes `localRef`.
    - Window Measurement: `data-testid="guided-winref-remove"` — removes `localWindowRef`.
    - Window Style: `data-testid="guided-window-remove-{id}"` per tagged window.
    - Mask: `data-testid="guided-zone-remove-{id}"` per zone.
    - Profile: `data-testid="guided-profile-remove-{id}"` per profile box.
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.10 — Auto-default scale unit by kind (2026-02-28)**: When the Wall Reference dialog opens (MODE_SCALE), default unit is now **FEET** (door/garage/eave-to-ground spans are almost always ft). When the Window Reference dialog opens (MODE_SCALE_WINDOW), default unit is **INCHES** (standard window widths are 24/28/30/32/36/40/44/48 in). User can still toggle manually mid-dialog; effect fires only on `scalePending.kind` change so a manual override during entry is preserved. LocalStorage `photoAnnotateScaleUnit` no longer sticks between kinds — replaced by kind-based defaults.
  - **Files**: `frontend/src/components/estimate/PhotoAnnotateModal.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.11 — Pre-Guided-Capture calibration prompt (2026-02-28)**: Howard flagged that scope-based auto-fill would poison Claude's calibration (contractor might upgrade from 4" clap to 7" clap, so scope ≠ current wall). Added a dedicated calibration modal that fires BEFORE the Guided Capture wizard opens — contractor is at the house with line of sight to the CURRENT walls, best moment to capture the exposure.
  - **Chip presets**: Vinyl D4 / D5 / D6 / D7 / Ascend CI (7) / LP 8" Lap / Cedar 4" / Brick (routes to `brick_course_in`; others route to `siding_exposure_in`). Selecting a chip clears the other field so only one calibration hint reaches Claude.
  - **Direct numeric input** below the chips for odd exposures (e.g. cedar shake 4.5", stone veneer, etc.).
  - **Buttons**: `Start Capture →` (disabled until a value is set) + `Skip · I'll eyeball it` (still lets the flow continue — Claude will fall back to standard-window snapping). Data-testids: `calib-prep-modal`, `calib-prep-chip-*`, `calib-prep-siding-input`, `calib-prep-start`, `calib-prep-skip`.
  - **How it plumbs**: Selection writes into the existing `sidingExposure` / `brickCourse` state, which the AI Measure `runMeasure()` already appends to the FormData (`siding_exposure_in` / `brick_course_in`). Backend `_build_prompt` already adds these as course-count hints to Claude's prompt. No backend changes.
  - **What it does NOT do**: Does NOT override the in-photo Wall Reference / Window Reference lines the contractor draws — those are Claude's primary scale anchors. Calibration is only an additional prompt hint that helps on walls where a red/blue reference line can't reach every opening.
  - **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.12 — AI Measure panel cleanup (2026-02-28)**: Two changes per Howard's feedback.
  - (1) **Removed the "Elevation Drawings · HOVER-style 2D editor · drag any opening to nudge" block**. The auto-generated 2D house diagrams sometimes didn't match the actual home structure closely enough and hinted at inaccuracy to the contractor. Wall breakdown table below still shows the same underlying data. Removed unused `ElevationDrawing` / `Elevation3DPreview` imports + `show3DPreview` state. `buildElevationsFromAIMeasure` is still used for the report-PDF sheet layout.
  - (2) **Footer cleanup**: The button row was wrapping erratically because labels like "Start Over" and "Apply Measurements" broke mid-word. Changed the footer to `flex-col md:flex-row` with `flex-wrap items-center justify-end gap-2` on the button group + `[&_button]:whitespace-nowrap` on the container. All buttons now stay on one line each with even heights, and the row cleanly wraps to a second line only if the modal is too narrow.
  - **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.13 — Elevation drawings stripped from Report PDF (2026-02-28)**: Removed the "Per-elevation diagrams" page (2D SVG wall drawings) from the AI Measure Report PDF export. Same reasoning as iter 79j.12: the auto-generated diagrams sometimes didn't match the real house structure and hurt credibility with the homeowner. What still ships in the PDF: summary tiles · per-wall breakdown table with confidence chips · per-wall summary cards (photo + measurements + confidence reasoning) · openings schedule · full-size photo strip · notes. Deleted `_wall_diagram_svg` and `_build_wall_diagrams_section` helpers along with the `{wall_diagrams_html}` insertion. Backend reloads cleanly, lint clean.
  - **Files**: `backend/routes/measure_report.py` only.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.14 — Bug fix: profile polygon (shake/B&B/etc.) never applied to estimate (2026-02-28)**: Howard reported that drawing a Shake polygon in the guided flow didn't route the ft² to the SHAKE profile category after Apply Measurements. Root cause: `setSavedProfileAnnotations` in `AIMeasureButton.jsx`'s `PhotoAnnotateModal onSave` handler was updating LOCAL React state only — it never persisted to `PUT /api/estimates/{id}/profile-annotations`. The backend `ai_measure` worker reads `profile_annotations` from the estimate doc (Mongo), so on Run AI Measure it saw an empty/stale blob → `apply_annotations_to_breakdown` had no accents to inject → sqft stayed in default LAP.
  - **Fix**: fire-and-forget `api.put(...)` on every save inside the same `setSavedProfileAnnotations` updater callback, with the merged `next` object. Failure is non-fatal (local state still works for the session, just won't survive a reload).
  - **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING (please re-draw a shake polygon and Run AI Measure to confirm the SHAKE line now appears with the correct ft²).

- **Iter 79j.15 — AI Measure A/B model toggle (2026-02-28)**: Contractors can now flip between Claude / Gemini / GPT vision models per-run without a code deploy, and the model used is stamped on both the run doc and the preview so accuracy + cost can be A/B compared on the same house.
  - **Backend** (`routes/ai_measure.py`):
    - New `_MODEL_CHOICES` registry mapping human-readable keys → `(provider, model_name)` tuples for: `claude-opus-4-5` (default), `claude-opus-4-8`, `claude-sonnet-4-6`, `gemini-3.5-flash`, `gemini-3.1-pro`, `gpt-5.5`, `gpt-5.4`.
    - `_resolve_model(choice)` helper — unknown keys log a warning and fall back to default. Never fails the run.
    - `POST /api/measure/ai-measure` accepts an optional `model_choice` Form field.
    - `_execute_ai_measure_worker` now takes `model_provider` + `model_name` kwargs and passes them to `LlmChat.with_model(...)`. Rerun path (which doesn't specify) still works via defaults.
    - Run doc persists `model_choice`, `model_provider`, `model_name` so a later query can compare Opus-vs-Gemini runs on the same estimate.
    - Result object now includes `model` (actual model used) + `model_provider` (was hardcoded to `MODEL_NAME`).
  - **Frontend** (`components/estimate/AIMeasureButton.jsx`):
    - New `modelChoice` state persisted in localStorage (`aiMeasureModelChoice`). Key survives modal close/reopen so the contractor's choice sticks.
    - Compact `<select>` dropdown next to the "Powered by" line lets contractors pick model per-run without leaving the modal. Data-testid: `ai-measure-model-select`.
    - `runMeasure` appends `model_choice` to FormData when running.
    - Preview header now shows a purple model badge (e.g. "Gemini 3.5 Flash") so a subsequent run with a different model is visually distinguishable. Data-testid: `ai-measure-model-badge`.
  - **Files**: `backend/routes/ai_measure.py` + `frontend/src/components/estimate/AIMeasureButton.jsx`. Backend + frontend lint clean, backend hot-reloaded successfully.
  - **Status**: SHIPPED. USER VERIFICATION PENDING — please run the SAME set of photos through Opus 4.5 and Gemini 3.5 Flash back-to-back and compare window counts + wall LF + profile detection to decide which model to keep as the default.

- **Iter 79j.16 — Model Comparison panel on AI Measure preview (2026-02-28)**: New side-by-side comparison card that surfaces when 2+ different models have been run on the same estimate.
  - **Backend** — new `GET /api/measure/ai-measure/history/{estimate_id}?limit=5` endpoint. Returns the last N `status=done` runs for the user+estimate with just the fields needed to A/B compare: model info, confidence, wall/window/door counts, siding_sqft, eaves_lf, elapsed_ms, and `cost_estimate_usd` (approximated using published list prices via `_MODEL_PRICING_PER_M` table). Endpoint is cookie-auth like the rest of the measure routes. Tested with curl → returns `{"runs": []}` on unknown estimate.
  - **Frontend** — new `modelHistory` state + `useEffect` that refetches on modal open and whenever a new `preview.session_id` lands. Panel renders inline above the geometry breakdown when history has ≥ 2 unique `model_choice` values. Latest run highlighted in violet, all others in white for easy visual delta comparison. Cost + elapsed time on the right so contractors can weigh accuracy against $ & speed per run. Data-testid: `ai-measure-model-comparison`.
  - **Files**: `backend/routes/ai_measure.py` + `frontend/src/components/estimate/AIMeasureButton.jsx`. Both lint clean. Backend hot-reloaded.
  - **Status**: SHIPPED. USER VERIFICATION PENDING — run 2 back-to-back on the same house (e.g. Opus 4.5 → Gemini 3.5 Flash) and the comparison card should appear the moment the second run completes.

- **Iter 79j.16.hotfix — TDZ error on AIMeasureButton mount (2026-02-28)**: The `modelHistory` `useEffect` I added in the previous iter referenced `open` and `preview` in its dependency array, but I declared the state hook ABOVE where `const [open, setOpen] = useState(false)` and `const [preview, setPreview] = useState(null)` were declared. That produced `ReferenceError: Cannot access 'open' before initialization` (temporal dead zone) crashing the estimate page. Moved the `modelHistory` state + effect to right after `preview` is declared so both variables are in scope. Verified fix with a live screenshot — estimate page now loads cleanly. Lint clean.

- **Iter 79j.16.b — Re-run button on AI Measure preview (2026-02-28)**: Howard couldn't A/B models because the preview footer had no way to trigger a fresh run — only Start Over (which cleared everything). Added a purple `Re-run` button between Advanced and the Refine controls that fires `runMeasure()` with the currently-selected `modelChoice`. Contractors can now: pick a model in the "Powered by" dropdown → click Re-run → the Model Comparison panel populates. Data-testid `ai-measure-rerun-btn`. Reuses the existing busy state so labels swap to "Vision… / Dormer scan… / Running…" during the pass. Lint clean.

- **Iter 79j.17 — Bug fix: 404 "Not found" on profile-annotations for fresh estimates (2026-02-28)**: Howard hit a persistent 404 toast when opening AI Measure on a new estimate. Root cause: `GET /api/estimates/{eid}/profile-annotations` in `routes/estimates.py` did `if not doc:` after querying with projection `{"_id": 0, "profile_annotations": 1}`. When the estimate exists but has no `profile_annotations` field yet, MongoDB returns `{}` — falsy in Python — so the endpoint 404'd on every fresh estimate. Fixed by switching to explicit `if doc is None:` check. Verified via curl: `HTTP 200 {"annotations": {}}` on Howard's estimate. PUT endpoint uses `update_one` + `matched_count`, so it wasn't affected.
  - **Files**: `backend/routes/estimates.py` only. Lint clean.
  - **Status**: SHIPPED + curl-verified.

- **Iter 79j.18 — CRITICAL bug fix: shake polygon from Guided Capture Wizard never reached backend (2026-02-28)**: Howard's shake / B&B / vertical polygons drawn inside the Guided Capture Wizard produced ZERO delta in the final estimate. Root cause: `GuidedCaptureWizard.jsx.handleAnnotateSave` stored the `PhotoAnnotateModal` `onSave` payload only in local wizard state — it never PUT to `/estimates/{id}/profile-annotations`. Iter 79j.14 fixed the per-photo Annotate button path but missed this wizard path. Now `AIMeasureButton.handleWizardComplete` extracts every profileBox from every wizard photo, transforms into the backend shape (identical to the per-photo save path), merges into `savedProfileAnnotations`, and fires a fire-and-forget PUT. Verified end-to-end DB query on Howard's estimate `7eb77c6d-…` — currently has `profile_annotations` field missing entirely (confirming the pre-fix state).
  - **Recovery path for Howard's existing estimate**: Open the estimate → AI Measure → click "Annotate" on the specific photo with the shake polygon → the profileBoxes are still in `photoAnnotations` state (until page refresh) → click Save → iter 79j.14's PUT fires → next Run AI Measure will emit a separate SHAKE catalog line. Alternatively: re-run Guided Capture and redraw.
  - **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` only. Lint clean.
  - **Status**: SHIPPED. USER VERIFICATION PENDING.

- **Iter 79j.32 — Front-Gable ridge axis toggle + opening-vs-masked prompt audit (2026-02-28)**: Two-part fix for Howard's red-house findings.
  - **Part 1 — Ridge Orientation toggle (`frontend/src/components/estimate/HouseModel3D.jsx`)**: `ridgeAxis` is now a first-class user-editable dropdown alongside Roof type. Values: "x" (Side-gable, ridge L↔R, gable ends on LEFT/RIGHT) and "z" (Front-gable, ridge F↔B, gable ends on FRONT/BACK). Flipping cascades gable-end assignment, roof-plane orientation, and dormer slope face through the existing derivation. Hidden for hip roofs. Amber / green / violet source badges match the roof-type row. Dormer face override auto-clears on flip so the derived slope-front/back/left/right assignment is recomputed cleanly.
  - **Part 2 — Geometry consistency check (`buildScene`)**: Every wall reporting `gable_triangle_height_ft > 0` in the AI takeoff MUST render as a gable-end, and vice versa. Violations `console.error` with facade id, AI height, current `hasGablePeak`, and current `ridgeAxis` — so the contractor / dev sees "flip Ridge orientation" as the fix. Skipped for hip roofs (which zero all gable heights by design). Runs on every scene rebuild.
  - **Part 3 — Opening-vs-masked prompt audit (`backend/routes/ai_measure.py` SYSTEM_PROMPT)**: Rewrote the SIDING COVERAGE rule with an explicit MASKED vs OPENINGS decision tree. Masked (reduces `siding_pct_this_wall`) is now RESTRICTED to actual masonry: brick / stone / stucco / CMU / attached masonry structures. All trimmed penetrations (windows, entry doors, patio doors, garage doors, wall vents) MUST be emitted as rows in `openings[]` — they receive J-channel / surround trim downstream. Includes a strong garage-door callout (~112 ft² + ~40 lf J-channel per door — was being lost). Updated the annotation guidance so "NO SIDING · Garage door" hatched zones route to openings[] instead of reducing coverage. Added Iter 79j.32 marker comment at the openings[] schema so future edits keep the rule intact.
  - **Regression guard**: `backend/tests/test_opening_masked_classification_prompt.py` — 4 pytests assert the MASKED vs OPENINGS heading, the garage-door warning, the removed "NO SIDING · Garage door" pattern, and that masonry still belongs in the masked bucket. All pass locally.
  - **Files**: `backend/routes/ai_measure.py` (SYSTEM_PROMPT only), `frontend/src/components/estimate/HouseModel3D.jsx` (toggle UI + consistency check), `backend/tests/test_opening_masked_classification_prompt.py` (new).
  - **Status**: CODE SHIPPED. Definition-of-done validation (fresh AI Measure re-run on red-house photos + trim-line inspection) BLOCKED by LiteLLM budget cap on Emergent LLM key — user needs Emergent support to raise the ~$18.80 cap before the live re-run can be executed.

- **Iter 79j.44 — Phase A resilience + persistent error UX (2026-02-28)**: Root cause of the "run failed, error vanished as a toast" bug traced. Phase A wrapped `asyncio.gather(...)` in `asyncio.wait_for(..., timeout=300)`; a single slow photo threw `TimeoutError` and cancelled every task → the whole batch died and `str(TimeoutError())` = '' → frontend toast rendered a blank error.
  - **Backend (`backend/routes/ai_measure.py`)**:
    1. New `_env_int(name, default)` helper for env-tunable knobs.
    2. `_extract_one_photo` — per-call timeout now env-configurable via `AI_MEASURE_PER_CALL_TIMEOUT` (default 120s). Per-call timeouts / exceptions produce structured `_extraction_error_kind` fields plus per-photo latency logs (`photo X done in Yms (empty=…)`) so future latency diagnosis is trivial.
    3. `_run_two_phase_pipeline` — rewrote the parallel-extraction gather. Each photo task is now wrapped in its own `asyncio.wait_for(timeout=AI_MEASURE_PER_PHOTO_TIMEOUT)` (default 240s, env-configurable), and the batch uses `asyncio.wait(..., timeout=AI_MEASURE_PHASE_A_TIMEOUT)` (default 300s, env-configurable) instead of `wait_for(gather)`. Slow / hung photos are cancelled individually and returned as `_empty_extraction=True` with a human `_empty_reason` (`"Photo timed out after Xs — LLM proxy slow or unresponsive."`), matching the empty-retry code path exactly. Fast photos always survive.
    4. Worker `except Exception` now stamps a non-empty `error` (falls back to exception class name if `str(e)` is empty) plus an `error_kind` field on the run doc so frontend banners never render a blank message again.
  - **Frontend (`frontend/src/components/estimate/AIMeasureButton.jsx`)**:
    1. New `runErrorMeta` state + `runStartTsRef` capture the stage the pipeline was in and wall-clock elapsed since the user clicked Run. Persistent error banner now shows `Phase: extracting_per_photo · Elapsed: 27s · Kind: TimeoutError` under the message and offers a one-click **Retry Run** button. Transient `toast.error(...)` on run failure removed — the persistent banner covers it.
    2. Apply Measurements: added an orphan-wall safety net. If `preview.measurements._ai_orphaned_walls` has entries, a `window.confirm` blocks the Apply until the user acknowledges "this takeoff has unmeasured walls: front, back". Prevents extrapolated wall dimensions from silently entering a customer-facing quote.
  - **Regression guard**: `backend/tests/test_phase_a_resilience.py` — pytest suite (2 tests, no pytest-asyncio dependency) drives the real pipeline with monkey-patched `_extract_one_photo` / `_reconcile_extractions` / `db`. Verifies a hanging photo is flagged with a proper reason and the other photos still reach Phase B intact. Both tests pass locally in ~3s.
  - **Env knobs** (default in parentheses): `AI_MEASURE_PER_CALL_TIMEOUT` (120s), `AI_MEASURE_PER_PHOTO_TIMEOUT` (240s), `AI_MEASURE_PHASE_A_TIMEOUT` (300s). All accept blank/invalid → default without erroring.
  - **Status**: SHIPPED + regression-tested. USER VERIFICATION PENDING — kick off an AI Measure and watch backend logs for the new `[ai-measure phase-A] photo N done in Nms` lines to confirm true per-photo latencies (should be ~15-25s parallel; anything >60s indicates an LLM proxy issue worth investigating further per the P0 diagnosis clause). Also confirm the persistent red banner + Retry button + orphan-wall Apply confirm dialog on the front end.

- **Iter 79j.45 — AI Measure health-preflight endpoint (2026-02-28)**: Added a cached preflight so a full ~5 min Phase A no longer wastes a run when the LiteLLM budget is exhausted or the LLM proxy is unreachable.
  - **Backend (`backend/routes/ai_measure.py`)**:
    1. New `GET /api/measure/ai-measure/health` endpoint. Fires the smallest possible Claude call (`max_tokens=1`, 5s deadline) against the same MODEL_NAME the worker uses (opus-4-5) so the health path exactly mirrors the run path. Returns `{status, detail, checked_at, cached, latency_ms}`.
    2. Server-side cache TTL 45s (module-level `_AI_HEALTH_CACHE` dict). Cached responses skip the network call and set `latency_ms: null, cached: true`.
    3. Pure `_classify_health_error(err_msg)` mapper: budget → `budget_exceeded`, timeout/connection/DNS → `unavailable`, unauthorised/invalid-key/forbidden → `unavailable`, everything else → `ambiguous` (never collapses unknown errors into "budget"). The ambiguous bucket carries the truncated raw error string.
    4. Also added `error_kind` to `GET /api/measure/ai-measure/status/{run_id}` response so the persistent frontend error banner can show `Kind: TimeoutError`.
    5. HARD-DISABLED direct-key routing in `_pick_llm_api_key` (Iter 79j.44 continuation). Even if `ANTHROPIC_API_KEY` is set on `.env`, the function ignores it and returns the Emergent proxy key — logging a `WARNING` so the operator sees the branch was skipped. Startup log stamps `[direct-key DISABLED]`.
  - **Frontend (`frontend/src/components/estimate/AIMeasureButton.jsx`)**:
    1. Health state: `aiHealth` + `aiHealthLastRef` + `refreshAiHealth({force})` helper. Client-side TTL 45s to match server. On modal open + before every `runMeasure` dispatch we refresh (short-circuits to the cached value if fresh).
    2. Run button label + colour flip based on status:
       - `ok` (or absent) → normal violet "Run AI Measure" button.
       - `budget_exceeded` → red button labelled "Budget exhausted — top up first", disabled.
       - `unavailable` → red button labelled "AI service unavailable — retry in a minute", disabled.
       - `ambiguous` → normal violet Run button STAYS enabled + soft amber banner at modal top saying "AI health check inconclusive". A broken health check MUST NOT lock the product.
    3. `runMeasure()` calls `refreshAiHealth()` first and short-circuits on `budget_exceeded` / `unavailable` (writes a persistent error banner with `Phase: preflight` + `Kind: BudgetExceeded` / `ServiceUnavailable`). Never actually dispatches Phase A when the preflight fails hard.
    4. Data-testids on the button (`ai-measure-run-btn` retained) + `data-health-status` attribute for automation. New banner `ai-measure-health-warning-banner`.
  - **Regression guard**: `backend/tests/test_ai_health_ping.py` — 4 pure-function classifier tests. Testing agent's iteration_34 ran 21 pytests + 9 live HTTP tests → 30/30 PASSED. Confirmed: unauth request 401, auth request returns valid shape, 2nd call within 45s served from cache (`cached: true`), health endpoint uses Emergent proxy (never direct-key).
  - **Env knobs**: none new. Reuses `MODEL_NAME` and `EMERGENT_LLM_KEY`.
  - **Files**: `backend/routes/ai_measure.py`, `backend/tests/test_ai_health_ping.py` (new), `backend/tests/test_ai_measure_health_http.py` (new via testing agent), `frontend/src/components/estimate/AIMeasureButton.jsx`.
  - **Status**: SHIPPED + tested. USER VERIFICATION PENDING — open AI Measure with an exhausted budget and confirm the Run button flips to red "Budget exhausted — top up first" instead of hanging for 19 min. On a healthy budget the button stays purple / says "Run AI Measure".

- **Iter 79j.46 — Event-driven AI health auto-recovery (2026-02-28)**: Extension of Iter 79j.45 preflight. No blind polling while green — pings ONLY fire on user-actionable events + a red-only backoff.
  - **Frontend (`frontend/src/components/estimate/AIMeasureButton.jsx`)**:
    1. New `isHealthRed` boolean derived from `aiHealth?.status`.
    2. Event listeners (`visibilitychange` on `document`, `focus` on `window`) attach ONLY when modal is open AND status is red — detach immediately when either flips. Zero cost when healthy.
    3. Red button is now CLICKABLE as a "re-check" escape hatch. Clicking it forces `refreshAiHealth({force:true})` (bypasses the 45s client cache) instead of dispatching a run. Icon swapped to `RotateCcw`, label becomes "Budget exhausted — click to re-check" / "AI service unavailable — click to re-check", tooltip "Click to re-check the AI service health".
    4. Slow-backoff timer (60s → 2min → 5min → stays 5min) only runs while red. Cleared on unmount, modal close, or any status change. Green button gets no timer.
    5. Auto-recovery flow: user tops up in a new tab → returns to app → tab-visible + focus fire → forced ping → status flips green → button turns purple → backoff timer cancels → no further pings.
  - **Regression guard**: no new tests (behaviour is React-event driven; classifier + endpoint tests from Iter 79j.45 already cover the failure surfaces).
  - **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` only.
  - **Status**: SHIPPED. USER VERIFICATION PENDING — exhaust the budget (or simulate by killing the LLM proxy), open the modal, top up, alt-tab back, and the red button should flip purple without a manual click.

- **Iter 79j.47 — Deploy Secrets click-path (2026-02-28, verified during live incident)**: Empirically confirmed by user during production key rotation.
  - **Path**: **Home tab → Manage Deployments → [your deployed app] → Secrets tab**.
  - **Deploy-side env vars are separate from preview `/app/backend/.env`.** Editing preview `.env` does NOT propagate to production. Env vars are stored in the deployment record and shown as either "Currently live" (in use by the running deployment) or "Updated, not live yet" (edited but pending next Redeploy).
  - **Update flow**: Secrets tab → edit value → **Save and Redeploy** button (single action; there is no env-only apply, so any Save-and-Redeploy will also ship whatever preview code is current).
  - **Rollback**: previously-deployed versions remain accessible; env vars persist across rollbacks (verify manually after any rollback per support's guidance).
  - **Not reachable via**: clicking the deployed app card on Home (goes back to chat), clicking "View Task" (also goes back to chat). This is the specific UI trap that caused two failed click-path guesses during the incident.
  - **Not doable via main agent**: I cannot read or write deploy-side Secrets — this is user-only UI territory.

- **Iter 79j.48 — Client poll window raised + heartbeat grace (2026-02-28)**: The main-run poll loop capped at 100×3s = 300s wall-clock (~400s with network) was smaller than the server two-phase worst case (Phase A 300s + drain 5s + Phase B ~180s ≈ 485s). Runs the server would have finished 30-80s later got phantom-failed as `ClientPollTimeout`. Raised all three poll loops (main run, rerun, resume) to 200×3s = 600s. Added a one-shot +120s grace extension gated on a fresh server heartbeat (`elapsed_ms` on the status endpoint advanced within the last 30s) so a heartbeat-alive worker gets its final minutes to finish instead of dying with a client timeout. Updated error copy: "did not complete within 10 minutes — the server may still be finishing this run in the background". Files: `frontend/src/components/estimate/AIMeasureButton.jsx` (3 poll-loop sites).

- **Iter 79j.49 — Platform /health probe + admin debug-log-tail (2026-02-28)**: Two deployment diagnostics fixes.
  - **`GET /health` (bare, no `/api` prefix)** — the Emergent platform probes this every ~2s and interprets 404 as unhealthy → may restart the pod. Added `@app.get("/health")` in `backend/server.py` returning `{"status":"ok"}`. Lives OUTSIDE `/api` by design; do not move under `api_router`.
  - **`GET /api/measure/ai-measure/debug-log-tail`** — admin-only (`role in {"owner","supplier_admin","admin"}`) endpoint that returns the last N in-memory `logger.info/warn/error` records with `?grep=<needle>[,<needle>]&lines=<N>` filters. Backed by a `_RingBufferLogHandler` (deque, 2000 records) attached to the ROOT logger in `server.py`. Handler is primed BEFORE any router imports so module-level startup log lines (like `[AI_MEASURE key-routing]` in `routes/ai_measure.py`) land in the buffer.
  - **Purpose**: the platform's log viewer shows only raw HTTP access lines, not application logger output. During the 2026-02-28 latency incident I needed to grep the `[ai-measure phase-A] photo N done in Nms` instrumentation lines from production but had no path. This endpoint gives admin curl access without shell into the container.
  - **Temporary**: ship for the incident, remove once LiteLLM latency root cause is understood. Comment at the top of the endpoint marks it as temporary.
  - **Files**: `backend/server.py`, `backend/routes/ai_measure.py`. Also documented in `memory/prompts.md` (Iter79j.49 entry).

- **Priority correction (2026-02-28, per Howard)**: Run 3 / Run 4 red-house validation is **NOT queued behind the production latency investigation.** It runs on preview which is healthy and independent, and is in progress in parallel with the incident work. Also: `/health` probe pod-restart hypothesis is now a live diagnostic candidate — when the next production 8-photo run's phase-A log tail is pulled, first check for startup banners appearing mid-run (indicates a pod restart mid-Phase-A) before assuming proxy latency. If a restart is confirmed, Iter79j.49's `/health` fix alone may be the cure and Iter79j.48 (600s poll) can be shelved.

- **Iter 79j.50 — Payload shrink + concurrency cap (root-cause workaround, 2026-02-28)**: Empirical evidence collected today proves the LiteLLM proxy behind `emergentintegrations.LlmChat` serializes concurrent LARGE-payload calls (3 parallel calls with max_tokens=4000 → 185s wall, ratio 3.0 SERIAL; same 3 parallel calls with max_tokens=5 → 4.89s wall, ratio 1.00 PARALLEL). Also empirically proven: `asyncio.wait_for(chat.send_message(...), timeout=N)` does NOT cancel in-flight calls (they run to natural completion). Both bugs mean production 8-photo runs take 400-500s per photo instead of 60-70s each.
  - **Workaround shipped in `backend/routes/ai_measure.py`**:
    1. **`_shrink_for_phase_a(raw_bytes, max_dim=1600, jpeg_q=80)`** — PIL-resizes each photo to a 1600px max long-edge and re-encodes JPEG q80 BEFORE Phase A dispatch. Contractor phone photos (3000-4500px, 3-5MB) → typically 10-50KB (100-300× reduction). Per-photo before/after logged with `[ai-measure phase-A] photo N shrunk WxH → wxh (bytes → bytes, ratio)`.
    2. **`asyncio.Semaphore(2)` inside `_budgeted_extract`** — caps concurrent Phase A calls to 2 at a time (env-configurable via `AI_MEASURE_PHASE_A_CONCURRENCY`). Placed INSIDE the coroutine (not around create_task) so per-photo timers only start after semaphore entry.
    3. Env knobs: `AI_MEASURE_PHASE_A_MAX_DIM` (1600), `AI_MEASURE_PHASE_A_JPEG_Q` (80), `AI_MEASURE_PHASE_A_CONCURRENCY` (2).
  - **Bug report drafted** — a full reproduction script + empirical latency numbers pre-drafted for Howard to email to `support@emergent.sh`. See finish summary for the exact text.
  - **NOT shipped**: token-count reduction (Iter 79j.50-B) and model-swap (Iter 79j.50-C) explicitly held per Howard's rules — would change extraction output content or invalidate Run 1/2 comparability.
  - **Deferred**: bypassing `emergentintegrations` with direct `litellm.acompletion` + explicit `httpx.AsyncClient` pool is the right long-term fix (also the foundation for a future direct-Anthropic path). Queued after red-house validation.
  - **Also killed 3 stuck preview runs** left over from before the fix so DB reflects clean state.
  - **Files**: `backend/routes/ai_measure.py` (shrink helper + pipeline changes). Documented in `memory/prompts.md` (Iter79j.50 entry).

## Iter 79j.51 — QUEUED for next iteration (not shipped today)

Added 2026-02-28 during 79j.50 deploy. Do NOT hold today's deploy for these.

**Trigger context**: On preview Run 3 (pre-79j.50, full-size photos, no shrink), Phase A completed 8-for-8 successfully (zero empty extractions, both dormers observed — photo 2 left, photo 6 right). Phase B then hung for 901s and died with `litellm.BadGatewayError: 502`. Phase A's `raw_per_photo` was fully persisted; the reconciled output is null. All the Phase A spend evaporated because there's no path to retry Phase B alone. This is the third documented failure mode of the emergentintegrations/LiteLLM proxy — added to the support email evidence.

**Note on 79j.50 relevance**: the shrink + concurrency cap did NOT rescue Run 3 (it predates them). Full-size Phase A got to done in this run despite the proxy load. 79j.50 will make future Phase A faster and less serialized; it doesn't change the Phase B failure mode. The reconcile-only retry (Task 1 below) is the ONLY way to recover Run 3's stranded Phase A output.

### Task 1: Reconcile-only retry endpoint (P0)
- **What**: New endpoint (likely `POST /api/measure/ai-measure/reconcile-only/{run_id}`) that reads the existing `raw_per_photo` array from the run doc and reruns ONLY Phase B (`_reconcile_extractions`), writing the result back to the same run.
- **Why**: When Phase B fails (proxy 502, timeout, hang), Phase A's expensive vision work is wasted. Contractor re-pays the full cost. Reconcile-only lets them retry Phase B for pennies.
- **Files**: `backend/routes/ai_measure.py` (new endpoint), `frontend/src/components/estimate/AIMeasureButton.jsx` (Retry-reconcile button in the persistent error banner when kind matches Phase B failure).
- **Gotcha**: don't rebuild Phase A stage machinery — jump straight to `set_stage("reconciling")`. Reuse the same run_id.

### Task 2: Failed-reconciliation UI state (P0)
- **What**: When `run.result.reconciled` is null / empty AND run status is error with `error_kind` indicating Phase B failure, the 3D tab must render explicit "Measurement incomplete — reconciliation failed [Retry reconciliation]" instead of a placeholder house with 0 sf / 0 openings.
- **Why**: A placeholder house from empty data reads as "catastrophically wrong measurement" instead of "the step didn't produce output". Different failure semantics need different UI.
- **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` (3D tab render guard), possibly `frontend/src/components/estimate/HouseView.jsx` or wherever the 3D scene mounts (guard the mount on non-empty measurements).
- **Rule**: never draw a placeholder house from empty/null geometry data.

### Task 3: Apply Measurements zero-data guard (P0)
- **What**: `apply()` in `AIMeasureButton.jsx` must be HARD-DISABLED (not just warned) when the reconciled output is null / empty. The existing orphan-wall `window.confirm` is a WARNING pattern for partial data — zero data needs a different pattern: button disabled with tooltip "Reconciliation failed — nothing to apply. Retry Phase B first."
- **Why**: On the 79j.50 failed run, Apply still wrote outside-corner LF into the estimate derived from placeholder geometry. That's silently wrong data hitting the customer quote.
- **Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` (add zero-data guard to the Apply button + `apply()` function).
- **Rule**: distinguish three states — full data (Apply normally) / partial data (Apply with orphan-wall confirm) / zero data (Apply DISABLED, retry required).

### Task 4: Support email update (user-owned)
- User will add the 79j.50 run's 502 + 901s Phase B hang to the existing support email alongside the 185s-vs-4.89s repro. Reinforces "even TEXT-only reconcile calls exhibit proxy instability under load."

**Priority**: All three code tasks (1-3) are P0 blockers for the next real user run. Ship as a single Iter 79j.51 bundle after 79j.50 has proven stable in production.


## Iter 79j.51 — Reconcile-only retry SHIPPED + validated (2026-07-06)

### Backend
- ✅ `POST /api/measure/ai-measure/reconcile-only/{run_id}` implemented in `backend/routes/ai_measure.py`. Reuses run's `raw_per_photo` — no Phase A revisit. Auth: cookie owner OR admin role.
- ✅ Phase B payload trimmed: `bbox` fields dropped in the slim step before proxy send (5 tests pass in `tests/test_reconcile_only_retry.py`).

### Frontend
- ✅ `retryReconcileOnly(runId)` handler added to `AIMeasureButton.jsx` (defined before `rerunWithAnnotations`). Polls same run_id for up to 4 min.
- ✅ "Retry Reconciliation" button renders only when `currentRunId && /reconcil|BadGateway|502|Phase\s*B/i.test(runError)`.
- ✅ Apply button + 3D render guards remain as previously shipped: banner shows "Measurement incomplete — reconciliation failed", 3D scene suppressed, Apply disabled.
- ✅ Lint clean.

### Proxy latency probe (support email followup)
Ran 3 parallel large-payload (max_tokens=4000, ~4KB prompt) calls per model via `backend/scripts/proxy_probe.py`, isolated from the app:
- `claude-fable-5`: **wall=84.2s**, avg call=28.1s, 3/3 OK (one call returned only 41 chars — reply truncation curiosity)
- `claude-sonnet-4-5`: **wall=131.3s**, avg call=43.8s, 3/3 OK
Conclusion: fable is faster than sonnet-4-5 at concurrency=3, so support's "unlisted model → throttled default bucket" theory is not supported by evidence. Phase B 502s are payload/timeout related, not per-model throttle. App model UNCHANGED per user gate.

### Run 3 red-house reconciliation (via new endpoint)
Invoked `/reconcile-only/22af2eb2ad784c7bbd662222e16001ab` (earlier of the two 8-for-8 stranded Phase A runs):
- Wall time: **4 min 18 s** (kicked off 02:38:04 → done 02:42:22 UTC 2026-07-06)
- Model: claude-fable-5
- Status: done · `_reconciliation_error`: null
- Story count: 1.5 · siding_sqft: **1598.0**
- Full raw_ai populated: walls, dormers, openings, LF tallies (eaves/rakes/starter/OC/IC)
- 8/8 Phase A extractions reused — no vision spend
- Reserve stranded run `9c8248df8e854590b4d8671d51dd6da2` untouched for Run 4.

### Gate status
Red-house validation NOT yet graduated. User must eyeball the reconciled numbers on preview before feature work resumes.

## Standing Justification for Post-Validation Direct-API Rewrite (Option D)

**Date logged**: 2026-07-06 · **Source**: Emergent Support (written confirmation on the 79j.51 ticket).

### What support confirmed (verbatim intent)
Emergent Support stated in writing that there is **no documented concurrency, payload-queueing, or cancellation behavior for the Universal Key / Emergent LiteLLM proxy**. The serialization behavior we have been repeatedly observing under load (large payloads, 2-3 concurrent Phase A/B calls) is therefore either:
1. An **undocumented internal policy** (throttling, queueing, or bucketing we cannot inspect or plan around), OR
2. A **bug** in the proxy layer.

Either way, we cannot design around it because the contract does not exist.

### What our own evidence shows (backs the support statement)
- **Iter 79j.44/45/50** progressively shrunk photos, capped Phase A concurrency at 2, added per-photo timeouts. Reduced *frequency* of proxy hangs but did not eliminate them.
- **Iter 79j.51 Phase B 502**: text-only reconciliation call (no images) hung 901s then died with `litellm.BadGatewayError: 502`. Purely text payloads exhibit the same instability — this is not a vision-payload-only issue.
- **Iter 79j.51 proxy probe** (`backend/scripts/proxy_probe.py`, 3 parallel · max_tokens=4000): fable=84s wall, sonnet-4-5=131s wall. Even the "faster" model showed ~28-43s per call at concurrency=3, meaning individual 4KB text calls are being serialized by the proxy at very modest concurrency.
- Support's own suggestion (throttled default bucket for unlisted models) does **not** fit the data — fable is faster than a listed model.

### Why this justifies Option D (direct provider API rewrite) after red-house validation graduates
- **No SLA to code against**: with the proxy's concurrency/queue/cancel behavior undocumented, every future scaling task (batch quoting, background reconciles, higher photo counts, retry policies) is guesswork against a moving target.
- **Undocumented ≠ safe**: we have already burned iterations on defensive downscaling, semaphores, timeouts, and now a reconcile-only escape hatch. Each is a workaround for a proxy behavior we cannot see.
- **Direct provider APIs (Anthropic Messages API, plus Gemini's native SDK) have documented rate limits, retry semantics, streaming, and cancellation** — a contract we can plan capacity and error handling around.
- **Cost / spend model does not change materially** — the direct-key path was already implemented and hard-disabled in Iter 79j.4x (see `_pick_llm_api_key` in `backend/routes/ai_measure.py`); reversing that toggle is scoped work, not a rewrite of the pipeline.
- **Retains fable/opus/sonnet A-B testing**: Anthropic Messages API supports all three model IDs directly; the model-selector UI does not change.

### Sequencing (do NOT start until red-house gate graduates)
1. Red-house validation gate (Runs 3 & 4 human-eyeball on preview) — currently pending.
2. Once graduated, re-enable direct Anthropic key routing in `_pick_llm_api_key` for `provider="anthropic"` when `ANTHROPIC_API_KEY` is present; keep proxy as fallback only for gemini/openai text.
3. Add per-provider concurrency + retry policy (documented Anthropic limits: 50 rpm / 40k tpm for standard tier — plan Phase A worker pool to that number, not to a guess).
4. Migrate Phase B off proxy first (text-only, most-often-failing path) as a safe pilot; migrate Phase A after Phase B stability is confirmed.
5. Leave `EMERGENT_LLM_KEY` in place as an emergency fallback path, but off the default hot path.

### Explicit user gate on this work
This item **remains blocked** until the user personally graduates the red-house validation (Iter 79j.51 Run 3 reconciled output on preview). No provider-swap code lands until then. This PRD entry exists so the rationale survives session forks — not as a work order.


## Iter 79j.52 — Reconcile-only reachability + resumed-failure UI fixes (2026-07-06)

**Trigger**: user reported that after 79j.51 landed, the reconciled Run 3 result was unreachable in the UI. Resume kept restoring the OLD failed 79j.50 run (`_reconciliation_error: 502`, walls=[], dormers=[]) even after a hard refresh. Root cause: the reconcile-only endpoint only wrote to the `ai_measure_runs` doc — it never touched the `ai_measure_sessions` doc that the Resume banner restores from. Separately, the 79j.51 failure-state UI (banner + Retry Reconciliation + 3D suppression + Apply disable) fired only on fresh-run failure paths; resumed sessions carrying a stale `_reconciliation_error` silently loaded the placeholder preview.

### Fixes shipped
1. **Backend — `_execute_reconcile_only_worker`** (`backend/routes/ai_measure.py`): on success, look up `estimate_id` + `company_id` and upsert `ai_measure_sessions.preview` with the reconciled `raw_ai + measurements + run_id + model`. Also bump the run doc's `updated_at`. `latest-for-estimate` now sorts by `updated_at DESC, created_at DESC` so a reconcile-only completion on an older run correctly outranks a newer-but-failed run.
2. **Frontend — `_applyAIResult`**: stamps `run_id` into the persisted preview so future resumes carry the correct target for Retry Reconciliation.
3. **Frontend — `resumeSession`**: on Resume, detect `data.preview.raw_ai._reconciliation_error`; if present, hoist it into `runError` + `runErrorMeta({stage:"reconciling", kind:"BadGateway"})` and set `currentRunId` from `data.preview.run_id`. The existing 79j.51 failure banner + Retry Reconciliation button now fire on resumed sessions.
4. **Frontend — 3D tab render guard**: when `raw_ai._reconciliation_error` OR (`walls.length == 0 && dormers.length == 0`), render a `data-testid="ai-measure-3d-empty-state"` panel with the failure text and an in-panel Retry Reconciliation button instead of `<HouseModel3D>`. Never draw a placeholder house from empty geometry.
5. **Frontend — Apply button disable predicate + runtime guard**: prior 79j.51 code checked `measurements.walls[].length` — that field is never populated by the aggregator, so the guard was false-positive-blocking valid runs. Fixed to check `raw_ai.walls / dormers / openings` array lengths + `measurements.siding_sqft / eaves_lf`. Now Apply disables only when reconciliation actually failed.

### Direct DB repoint (one-shot for estimate `673707d5-9b7e-4d8f-8eaf-63c86820f611`)
Rewrote the estimate's session preview to point at reconciled Run 3 (`22af2eb2…`): walls=4, dormers=1, siding_sqft=1598, `_reconciliation_error=None`. Also bumped that run's `updated_at` so `latest-for-estimate` surfaces it correctly.

### Acceptance verification (screenshots captured)
- Preview tab after Resume: shows Per-Elevation Breakdown across 4 elevations (FRONT LAP 290+81, BACK LAP 261+108+STONE 29, LEFT LAP 463+SHAKE 114+49) with 1,756 ft² total siding split. Apply Measurements enabled.
- 3D Model tab after Resume: renders the parametric house (dark roof, red walls, white windows, geometry sidebar with Width 27ft / Eave 10.75 / Roof 6/12 / dormer-orientation warning). Not a placeholder box.
- Failure state (verified by temporarily injecting `_reconciliation_error` into the session preview): red "AI MEASURE FAILED" banner + Retry Run + Retry Reconciliation buttons + Phase/Elapsed/Kind row + 3D panel replaced by "Measurement incomplete" state with its own Retry Reconciliation button + Apply Measurements disabled. All `data-testid` hooks intact. Session was restored to the good state afterwards.
- Backend `tests/test_reconcile_only_retry.py`: 5/5 passing.

### Files changed
- `backend/routes/ai_measure.py` — reconcile-only worker + `latest-for-estimate` sort.
- `frontend/src/components/estimate/AIMeasureButton.jsx` — `_applyAIResult`, `resumeSession`, `apply` guard, Apply button predicate, 3D tab render guard.


## Queued for post-gate — Iter 79j.52a: Auto-clear stale reconciliation-failure session on dismiss

**Scope**: ~15 min of work. When a user clicks the `dismiss` link on the resumed reconciliation-failure banner, the current stale `_reconciliation_error` preview stays in `ai_measure_sessions` — so the next open of the modal keeps offering to Resume broken data.

**Behavior to ship**:
- When the user dismisses the runError banner AND the underlying `preview.raw_ai._reconciliation_error` is set, downgrade the persisted session to a "photos-only" state: keep `photo_urls`, `photo_annotations`, `reference_dim`, `wall_height`, `siding_pct`, drop `preview`.
- Contractor can still Resume (recovers the uploaded photos + form state, no wasted spend) but the modal opens clean — no stale failure banner, no phantom 3D empty-state, no disabled Apply on ghost data.

**Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` — modify the banner's dismiss `onClick` to also fire a small session PUT if the current runError originated from a stale reconciliation preview.

**Priority**: P1. Do NOT ship before the red-house validation gate graduates.


## Iter 79j.53 — Status-aware sort + read-only Resume + failed-preview persistence guard (2026-07-06)

**Trigger**: user reported (a) resumed sessions displayed a stale reconciliation failure banner that appeared to indicate a fresh auto-fired retry (misleading "Elapsed: 0s"), (b) an actual instant Phase B 502 corrupted the session doc between the 79j.52 direct repoint and the user's inspection, and (c) `updated_at`-only sort buried the successful reconciled Run 3 under a fresh failed attempt.

### Root causes
1. **Sort was recency-only** (`updated_at DESC`). Any subsequent failed retry beat the older successful reconciliation. `latest-for-estimate` returned the failed doc.
2. **Debounced + close-time session autosaves persisted any `preview` state**, including a `_reconciliation_error` preview if the retry loop briefly held one. Session preview got silently overwritten.
3. **Historic reconciliation errors on Resume were framed as fresh calls** — my 79j.52 `resumeSession` set `runErrorMeta.elapsedMs = 0` and `kind = "BadGateway"`, which the UI rendered as "PHASE: RECONCILING · ELAPSED: 0s · KIND: BADGATEWAY". Reads as "a call just fired and instantly failed" rather than "we're showing you a stored old error."

### Fixes shipped
1. **Backend `latest-for-estimate` — status-aware aggregation sort** (`backend/routes/ai_measure.py`):
   - Score 2: `status=done AND result.raw_ai exists AND result.raw_ai._reconciliation_error IN (null, "")`
   - Score 1: `status=running`
   - Score 0: everything else (errored / done-with-recon-error / stranded phase-a)
   - Sort: `_score DESC, updated_at DESC, created_at DESC`. Successful reconciliations *always* outrank failed attempts.
2. **Frontend session-autosave HARD GUARD** (`AIMeasureButton.jsx`, both debounced useEffect and close-time PUT): if `preview.raw_ai._reconciliation_error` is truthy, refuse to persist. The run doc remains the authoritative retry target; sessions carry successful state only. Prevents future 502s from burying good runs.
3. **Frontend — Resume error framing** (`AIMeasureButton.jsx` `resumeSession` + banner render):
   - `runErrorMeta` from Resume now sets `elapsedMs: null`, `kind: "PriorFailure"`, `origin: "resume"`.
   - Banner header switches from "AI Measure failed" → "Prior reconciliation failed" when `origin === "resume"`.
   - Adds explicit line "Restored from a previous session — no fresh call was made. Click Retry Reconciliation below to try Phase B again."
   - Elapsed badge suppressed when `elapsedMs == null`.
   - New Origin badge with `data-testid="ai-measure-run-error-origin"` reading "resumed session".
4. **One-shot direct DB repoint** of estimate `673707d5-9b7e-4d8f-8eaf-63c86820f611` session → back to Run 3 (`22af2eb2…`), walls=4, dormers=1, siding_sqft=1598.

### Verification
- **Aggregation sort simulation** with a fake fresh-failed run 1h in the future: `_score=2` (Run 3) outranks fake `_score=0` correctly. Fake run cleaned up.
- **`/latest-for-estimate` HTTP endpoint**: returns Run 3 (`walls=4, _reconciliation_error=null, siding_sqft=1598`).
- **Good-state Resume screenshot**: no banner, Apply enabled, 3D house renders. All existing checks intact.
- **Injected historic-failure screenshot**: banner reads "Prior reconciliation failed", sub-line "Restored from a previous session — no fresh call was made", elapsed badge suppressed, `Origin: resumed session` visible, Apply disabled. Session restored to good state after test.
- **Backend `tests/test_reconcile_only_retry.py`**: 5/5 passing.
- **Lint**: both sides clean.

### Read-only Resume audit
Confirmed `resumeSession` and `restoreLastRun` never call `retryReconcileOnly`, `runMeasure`, or any Phase B endpoint. State mutation only. Retries remain user-initiated via the explicit "Retry Run" / "Retry Reconciliation" buttons. Added inline documentation calling this out so future edits don't accidentally sneak in an auto-fire.

### Support datapoint logged
`memory/prompts.md` now contains a timestamped entry documenting the 2026-07-06 03:33 UTC instant-502 as **failure mode #3** for the Emergent LiteLLM proxy on the Universal Key `claude-fable-5` route. Attach to the standing support thread as further evidence for post-validation Option D.

### User gate reaffirmed
No further Phase B reconcile attempts fired during this iteration. Red-house validation still pending. Once user graduates the gate on Run 3, we can (optionally) invoke reconcile-only on Run 4 baseline, then proceed to Option D.


## Queued for post-gate — Iter 79j.52b: Session self-heal on Resume when a successful reconciliation exists

**Scope**: ~10 min of work. Parallel guarantee to 79j.53's status-aware sort: enforce the "successful reconciliation always wins" contract at the session-doc layer too, so orphaned client-persisted failure previews self-heal on Resume.

**Behavior to ship**:
- On modal open, alongside the existing `/measure/sessions/{estimate_id}` GET, fetch `/measure/ai-measure/latest-for-estimate/{estimate_id}` (already fetched today for the `lastRun` banner — reuse that response).
- If `session.preview.raw_ai._reconciliation_error` is set AND `latest.run.status === "done"` AND `latest.run.result.raw_ai._reconciliation_error` is null/empty AND `latest.run.result.raw_ai.walls.length > 0`, PREFER the latest run's result over the session preview when stashing into `window.__aiMeasurePendingSession`. Also update the session doc via a background PUT so future Resume calls skip the check.
- Never regress the currently-successful session; only self-heal broken ones.

**Files**: `frontend/src/components/estimate/AIMeasureButton.jsx` — modify the session-check useEffect (line ~436) to cross-reference `lastRun` when the fetched session preview is a failure state.

**Priority**: P1. Do NOT ship before red-house gate graduates.


## Iter 79j.54 — Debug view run picker + dormer collapse audit (2026-07-06)

**Trigger**: user asked to inspect Run 3's dormers[] to confirm whether reconciliation collapsed one, and requested a picker so multiple successful runs can be compared without leaving the modal.

### Dormer collapse audit (Run 3 = `22af2eb2`)
Direct DB inspection confirmed **Phase A on Run 3 observed exactly 1 dormer** (photo 2, left elevation, width 13ft, face 62 sqft). Reconciliation kept 1 of 1 — no collapse. The "two dormers" memory belongs to **Run 4 (`9c8248df`)**, whose Phase A did see two (photo 2 left + photo 6 right) but whose Phase B 502'd, so Run 4 has never produced a reconciled output. `_reconciliation_notes.dormers` for Run 3 explicitly reads: *"Detected 1 shed dormer, on the left roof slope … photo 1 corroborated presence via the two oblique 'upper' windows; no other photo reported dormers, so exactly one entry emitted."*

Four runs on file for estimate 673707d5:
- `dcd8574a` (07-06 11:29, marker-annotated Re-run) — 8p · 1 phase-A dormer · 1 reconciled · 1460 sf · ✓ done
- `22af2eb2` (07-05 18:22, "Run 3") — 8p · 1 phase-A dormer · 1 reconciled · 1598 sf · ✓ done (via reconcile-only)
- `1caae946` (07-05 19:04) — 0p · killed · errored
- `9c8248df` (07-05 19:11, "Run 4") — 8p · 2 phase-A dormers · 0 reconciled · Phase B 502 (reserve stranded)

### Run picker shipped
1. **Backend**: `GET /api/measure/ai-measure/debug-runs/{estimate_id}` (`backend/routes/ai_measure.py`). Reuses the status-aware aggregation (score 2 = successful reconciliation, 1 = running, 0 = errored/stranded). Returns run_id, timestamps, model_choice, photo_count, reconciled boolean, `reconciliation_error` snippet, `wall_count`, `dormer_count`, `opening_count`, `phase_a_dormer_photos`, `phase_a_dormer_total`, `siding_sqft`, `pipeline`, `reconcile_only_retry_at`.
2. **Frontend**: `AIExtractionDebugModal` (`frontend/src/components/estimate/AIExtractionDebugModal.jsx`) accepts `estimateId` prop; on mount fetches the picker list; renders a row of buttons (`data-testid="debug-run-picker-{run_id}"`) below the modal header when >1 run exists. Each button shows the short id, completed time, wall count, dormer count, siding sqft, and an amber `(A=<n>)` badge whenever `phase_a_dormer_total > reconciled_dormer_count` — the collapsed-observation signal the user asked for. Clicking a run fetches `/status/{run_id}` and swaps both columns to that run's data without touching the parent session preview.
3. **AIMeasureButton**: threads `estimateId` into the modal.

### Verification
- HTTP endpoint returns all 4 runs correctly ordered (2 score-2 first, 2 score-0 last).
- Modal picker screenshots (both runs): picker row renders under the header; Run 4's button shows `(A=2)` amber flag; switching to Run 4 empties the reconciled RIGHT column (Phase B 502 — no result) while LEFT still shows Phase A observations; switching to `dcd857` shows the marker-annotated Re-run's per-photo eave reads (10.5 ft direct on photo 0 via 324" WALL REF) and reconciliation notes ("Confidence-weighted average … = 10.3 ft"). All A/B compare live in one modal.
- No reconcile fired during this iteration (per gate).
- Lint + backend tests clean (`test_reconcile_only_retry.py` 5/5).

### Marker-annotated Re-run accuracy note
User confirmed today's marker-annotated Re-run (`dcd8574a`) hit tape-accurate numbers: dormer width 15.0 ft, wall height 10.3 ft. The calibration markers are producing real accuracy gains — worth codifying into the standard capture workflow when we resume feature work.


## Queued for post-gate — Iter 79j.54a: Debug view "diff two runs" mode

**Scope**: ~30 min of work. Extend the 79j.54 run picker from a switcher into a two-slot A/B compare — the right tool for marker-vs-no-marker and model-vs-model comparisons.

**Behavior to ship**:
- Add a second selector in the debug modal header ("Compare against ▾") that pins a second run alongside the primary.
- When two runs are selected, both LEFT (Phase A) and RIGHT (reconciled) columns render side-by-side or stacked, with a diff strip that highlights fields where the two reconciled outputs differ: dormer count, avg eave, wall widths per elevation, siding sqft, opening counts.
- Green/red badges on numeric deltas; italic muted for equal-value rows.
- No new backend endpoint required — reuse `/status/{run_id}` for both loads.

**Files**: `frontend/src/components/estimate/AIExtractionDebugModal.jsx` (add a `secondaryRun` state + diff computation + render).

**Priority**: P1. Do NOT ship before red-house gate graduates.



## Iter 79j.55 — Run 4 reconcile-only FAILED · gate remains ungraduated (2026-07-06)

**Task**: user re-sequenced Run 4 reconcile-only as the actual gate (not post-gate), because Run 4's Phase A is the only dataset that observed both dormers and can therefore validate the reconciliation-collapse hypothesis.

**Kicked off**: `POST /api/measure/ai-measure/reconcile-only/9c8248df8e854590b4d8671d51dd6da2` at 12:04:06 UTC.

**Result**: **502 after 15 min 2 s** (12:19:08 UTC). `error="Reconciliation retry failed: Failed to generate chat completion: litellm.BadGatewayError: BadGatewayError: OpenAIException - Error code: 502"`. Run doc correctly transitioned to `status=error, stage=error`. `raw_ai.walls=0, dormers=0`.

**Same-day Phase B track record on the same key/model/route** (all `claude-fable-5` via Universal Key proxy):
- 02:38 UTC — Run 3 reconcile-only, 1 phase-A dormer, ~4 min, **success**
- 03:33 UTC — (unnamed) Run 3 replay, **instant 502**
- 11:29 UTC — Fresh Re-run `dcd8574a`, 1 phase-A dormer, ~10 min two-phase, **success**
- **12:04 UTC — Run 4 reconcile-only, 2 phase-A dormers, 15 min → 502**

**Containment (79j.53 guards held)**:
- Status-aware sort kept `dcd8574a` on top after Run 4 flipped to `status=error`. `/latest-for-estimate` returns the successful run.
- Session autosave guard prevented Run 4's failure preview from clobbering the client-persisted session (still `dcd8574a`'s reconciled data).
- Debug picker still shows Run 4 with the `(A=2)` amber flag — the collapse-bug indicator remains visible.

**Verdict on `(A=2)` collapse bug**: **neither confirmed nor disproven.** Phase B never completed on Run 4. Cannot be resolved via the proxy.

**Gate status**: **red-house validation remains ungraduated.** Run 4's 2-dormer Phase A is the only dataset that can graduate a two-dormer property, and the proxy has repeatedly refused it.

**Support datapoint logged**: `memory/prompts.md` now contains a full timeline table under "Support Datapoint — 2026-07-06 12:19 UTC — Failure mode #4" ready to attach to the standing support thread.

**Sequencing next**: Option D (direct Anthropic Messages API) is now the only path to graduate the gate. Phase B migrates first. No further proxy reconcile attempts fire without explicit user direction — the endpoint is a coin-flip and every failure is a burned proxy call, even though our guards prevent user-facing re-burial.

## Iter 79j.56 — Option D drafted: direct Anthropic Messages API for Phase B (STAGED, not activated) (2026-07-06)

**Trigger**: user green-lit Option D after Run 4 reconcile-only 15-min hang → 502 (failure mode #4). User provisioning `ANTHROPIC_API_KEY` in parallel to this diff.

### Contract
- Env flag `ANTHROPIC_DIRECT_ROUTE=phase_b_only` (unset by default → zero behavior change).
- When set AND provider is anthropic AND phase="B" AND `ANTHROPIC_API_KEY` is present, Phase B routes via `api.anthropic.com` using the official `anthropic` Python SDK (`AsyncAnthropic.messages.create(...)`).
- All other calls (Phase A vision, gemini, openai text/image) stay on the Emergent LiteLLM proxy regardless of the flag.
- Same model, same slim payload, same system prompt — **transport is the only thing that changes**. Run 4's reconciled result stays comparable across routes.
- On direct-route failure the dispatcher falls back to the proxy automatically (per user: "proxy as fallback"). No user-facing regression when the direct route errors.

### Files changed
- `backend/requirements.txt` — pinned `anthropic==0.116.0` via pip freeze.
- `backend/routes/ai_measure.py`:
  - `_pick_llm_api_key(provider, *, phase=None)` — new keyword arg; returns `(key, "anthropic_direct")` only when flag + phase + key line up; otherwise `(EMERGENT_LLM_KEY, "emergent_proxy")` unchanged.
  - `_LLM_ROUTING_SUMMARY` — now reflects flag/key state explicitly at boot so operators can grep `AI_MEASURE key-routing` to see which lane Phase B will use.
  - `_reconcile_extractions` — becomes a dispatcher: checks routing, calls `_reconcile_extractions_direct` first when eligible, falls back to `_reconcile_extractions_via_proxy` on error.
  - `_reconcile_extractions_via_proxy` — the original LlmChat-based proxy implementation, renamed. Stamps `_transport: emergent_proxy`.
  - `_reconcile_extractions_direct` — NEW. Uses `AsyncAnthropic(api_key=..., max_retries=0)` + `messages.create(model=..., max_tokens=4000, system=RECONCILE_PROMPT, messages=[{"role":"user","content":[{"type":"text","text":...}]}])`. 180s `asyncio.wait_for` ceiling to match the proxy path. Catches `APITimeoutError`, `RateLimitError` (preserves ratelimit headers in the error string), `APIError`, `asyncio.TimeoutError`, and any Exception — never raises. Returns parsed JSON with `_reconciliation_latency_ms` + `_transport: anthropic_direct` on success.

### Model mapping (per Anthropic docs — confirmed by integration playbook)
- `claude-fable-5` → `claude-fable-5` (Claude API ID = alias, no rename needed).
- `claude-opus-4-5` → `claude-opus-4-5-20251101`.
- `claude-sonnet-4-5` → `claude-sonnet-4-5-20250929`.
- `claude-haiku-4-5` → `claude-haiku-4-5-20251001`.
Aliases resolve on the direct API too, so the model string passed through the UI works verbatim.

### Verification (staged, not activated)
- **Flag OFF (current prod state)**: `_LLM_ROUTING_SUMMARY` reads `anthropic=EMERGENT_LLM_KEY (proxy) [direct route flag='unset', key=absent], gemini/openai=EMERGENT_LLM_KEY (proxy)`. Both Phase A and Phase B route to proxy. Zero behavior change.
- **Flag ON + fake key**: `_pick_llm_api_key("anthropic", phase="B")` returns `source="anthropic_direct"`. Phase A stays on proxy. Gemini stays on proxy.
- **Direct SDK reachability**: `_reconcile_extractions_direct(api_key="sk-ant-fake", model_name="claude-fable-5", ...)` connected to `api.anthropic.com` in 262 ms, got HTTP 401 with a valid `request_id`, converted to `_reconciliation_error` sentinel without raising. `_transport: anthropic_direct` correctly stamped.
- **Fallback dispatcher**: with flag ON + fake key, `_reconcile_extractions(...)` calls direct → 401 → logs `"[ai-measure phase-B] direct-route failed, falling back to proxy: ..."` → invokes proxy path → returns `walls=4, _transport: emergent_proxy`. Fallback contract holds.
- **Backend tests**: `tests/test_reconcile_only_retry.py` 5/5 passing. Lint clean.

### Activation checklist (once user provisions the real key)
1. Add `ANTHROPIC_API_KEY=sk-ant-...` to `/app/backend/.env` (env-based supply chain).
2. Add `ANTHROPIC_DIRECT_ROUTE=phase_b_only` to `/app/backend/.env`.
3. `sudo supervisorctl restart backend` (env change requires it).
4. Grep `AI_MEASURE key-routing` in backend logs — should read `anthropic Phase B=ANTHROPIC_API_KEY (direct api.anthropic.com), anthropic Phase A=EMERGENT_LLM_KEY (proxy), gemini/openai=EMERGENT_LLM_KEY (proxy)`.
5. Fire `POST /api/measure/ai-measure/reconcile-only/9c8248df8e854590b4d8671d51dd6da2` — Phase B of Run 4 now flows through `api.anthropic.com`.
6. Watch the run doc + `_transport` field in the reconciled result: `anthropic_direct` proves the bypass fired.

### Acceptance for red-house gate
- If reconciled `dormers.length == 2`: `(A=2)` flag on Run 4's picker button clears to `2/2` → **gate graduates**.
- If reconciled `dormers.length == 1` with Phase A `dormers_observed_photos = 2` on the same run: **collapse bug caught red-handed** with a clean transport trace → we now have deterministic Phase B data to file as a Claude prompt/reconciler bug rather than a proxy bug.

Either outcome closes the standing gate. No new proxy failure modes to chase.

### Gate protocol
- Diff is staged, not activated. No traffic changes until user provisions the key and sets the flag.
- The 79j.53 status-aware sort + session-autosave guard remain in force — they don't interact with the transport choice.
- The 79j.54 debug picker now includes a `_transport` breadcrumb in the reconciled `raw_ai` — a future picker column could surface it, queued as a P2 polish.


## Iter 79j.57 — RED-HOUSE GATE GRADUATES · dormer-collapse bug DISPROVEN (2026-07-06)

### Result
Reconciled Run 4 (`9c8248df`) output:
- `walls`: 4 · `dormers`: **2** · `siding_sqft`: 1515.7 · `eaves_lf`: 74.0 · `rakes_lf`: 63.0
- **LEFT dormer**: face=left, width=15.5 ft, knee wall 5.0 ft, from photo 2 (444" WALL REF direct read)
- **RIGHT dormer**: face=right, width=15.0 ft, knee wall 4.3 ft, from photo 6 (36" WIN REF direct read)
- `_reconciliation_notes.dormers`: *"Detected 2 shed dormers, one per eave slope … faces differ so they were **NEVER collapsed**; no second photo cross-checked either width so both carry direct_single_reading (amber)."*

**The `(A=2)` amber picker flag on Run 4 clears to `2/2 dormers`. Collapse bug DISPROVEN.** The reconciler correctly kept both dormers because their faces differ.

### How the graduating result was produced (a mid-iteration curveball)
- Round 1 (18:11 UTC): direct route fired, returned `empty text content`, fell back to proxy → proxy 502 at 18:27 (~15 min).
- Round 2 (18:28 UTC): direct route fired, returned truncated text (`stop_reason=max_tokens` at 4000), fell back to proxy → **proxy SUCCEEDED at 18:33 UTC** (~5 min, first proxy success on this exact payload after multiple failures). This is the run that produced the reconciled dormers[] currently in the session preview.
- Discovered `max_tokens=4000` too tight — Claude's extended thinking eats ~2048 tokens by default. Raised to `max_tokens=16000` + added `httpx.Timeout(180, connect=10, read=150, write=60)` on the SDK client.
- Rounds 3-4 (18:38, 18:55, 19:02, 19:10 UTC): all four subsequent kickoffs stuck on the direct route inside uvicorn — process 3927 held the async httpx call past the 180s ceiling with no cancellation propagating in.
- **Standalone isolated Python test** with the exact same payload + same SDK config: succeeded in **77.1 s** · `stop_reason=end_turn` · `output_tokens=7317` · `thinking_tokens=2017` · `text_len=12091`. So the direct API + SDK + payload combination is proven viable; something in uvicorn's async event loop is blocking cancellation.

### Discovered during this iteration — Mongo TTL index on ai_measure_runs
`ai_measure_runs` has a Mongo TTL index: `{key: {created_at: 1}, expireAfterSeconds: 86400}` (24h). This auto-deleted Run 3 (`22af2eb2`, TTL fired ~18:22 UTC) and Run 4 (`9c8248df`, TTL fired ~19:11 UTC) mid-testing. The session doc has NO TTL and preserved the successful reconciled preview — that's what surfaces on Resume and in the Debug picker.

**Implications**:
- 24 h is aggressive for a production quoter — a contractor can lose the full run doc (Phase A, Phase B, retries) if they don't Apply within a day. The session preview mitigates the user-facing loss, but the Debug picker + reconcile-only endpoint depend on the run doc still existing.
- Reconcile-only on a TTL'd run doc will 404; users can't rerun Phase B on stranded Phase A that predates 24 h.
- **Queued 79j.57a (post-verification)**: raise `expireAfterSeconds` to 30 days (or drop the TTL entirely — retention as an admin-config knob), and/or add a "pin run" API so contractors can preserve important runs.

### Direct-route status
- **Isolated test**: green (77.1 s, `stop_reason=end_turn`, full 12KB JSON, both dormers preserved).
- **Inside uvicorn**: async cancellation stalls; kickoffs never complete via direct route.
- **Fallback**: proxy path activates on the "empty text" / stall paths — Run 4 was actually reconciled through the proxy fallback at 18:33 UTC, not through the direct route.

Diff SHIPPED (env-gated, safe by default). Diagnostic path forward for the uvicorn stall queued as 79j.57b:

### Queued for post-verification — Iter 79j.57a: raise ai_measure_runs TTL
- Bump `expireAfterSeconds` from 86400 (24h) to 2592000 (30d).
- Small alternative: drop the index and add an explicit admin cleanup endpoint.
- ~5 min of work (single index change). Blocked pending user's confirmation of retention policy.

### Queued for post-verification — Iter 79j.57b: diagnose uvicorn/direct-route stall
- Isolated test proves the SDK + payload work. Something in the running server's async loop blocks httpx cancellation and stalls the direct call past `asyncio.wait_for` ceiling.
- Candidate diagnostics: run the direct call in a dedicated thread executor to isolate from the main event loop; or shell out to a subprocess for the direct call; or use `anyio` for hard cancellation semantics.
- ~1-2 hrs of investigation. Blocked pending user direction. Meanwhile the proxy fallback + the isolated-test proof are enough to justify keeping Option D staged.

### Support datapoint update
`memory/prompts.md` — Iter 79j.56 Option D shipping under user direction is proven viable in isolation; the four proxy failure modes (79j.44/45 hang, 79j.50/51 payload-driven 502, 79j.53 instant 502, 79j.54 15-min hang→502) are still fully justified by the standing thread. Add today's PROXY-fallback SUCCESS at 18:33 UTC as a fifth datapoint: the same proxy that failed with 15-min hang→502 at 12:04 UTC on the same exact payload succeeded at 18:33 UTC in ~5 min — **the proxy is nondeterministic**, further reinforcing the case for direct routing as the durable path.



## Iter 79j.58 — Red-House Gate GRADUATES · 3D dormer slope mapping + knee-aware placement (2026-07-06)

**Status**: SHIPPED · Red-House Run 4 validation complete end-to-end (data → reconciliation → 3D render).

### Bugs fixed
1. **`migrateFace` collapsed different faces onto the same slope.** Prior logic mapped anything not literally `"back"/"rear"` to `slope-front` (or `slope-left`), so two dormers reconciled on faces `"left"` and `"right"` both landed on the *same* slope in 3D — the exact regression Howard flagged. Rewrote as a full disambiguation table for both ridge axes so opposite faces render on opposite slopes.

2. **Dormer face wall poked above the main ridge → false sanity banner.** `uFrac` (how far up-slope the dormer face wall sits) was hardcoded at `0.5`. With Red-House knee=4.3 ft and roofRise=6.75 ft, `faceTop = eave + rise*0.5 + 4.3 = eave + 7.675 > ridgeY = eave + 6.75` → banner fired even though the input geometry was physically valid (knee < rise). Now:
   - `kneeEff = min(kneeRaw, roofRise * 0.95)` — never allow visual overflow.
   - `uFrac = clamp(0.5, 0.9, kneeEff / roofRise + 0.05)` — push face down-slope just enough to fit under the ridge with 5% headroom.
   - Sanity check now uses the same math and only warns when the AI-reported knee is truly unphysical (≥ 95% × roofRise). Iterates all `roof.dormers[]` so multi-dormer houses get per-dormer warnings.

### File touched
- `/app/frontend/src/components/estimate/HouseModel3D.jsx`
  - `migrateFace` (buildHouseJson) — full input-label disambiguation for both ridgeAxis values.
  - `buildShedDormer` — knee-aware `kneeEff` and dynamic `uFrac`.
  - Sanity check block — iterates all dormers, uses the same clamped math.

### Validated on Red-House estimate `673707d5-9b7e-4d8f-8eaf-63c86820f611`
- Ridge axis correctly derived as `z` (front/back gables in walls[]).
- Dormer 1 (15.5 ft) → `slope-left`, Dormer 2 (15 ft) → `slope-right` — opposite slopes, distinct rendering.
- No `above the main ridge` banner. No `roof orientation may be wrong` banner. No `shrink knee` copy.
- Flipping ridge orientation to `x` still shows correct opposite-slope mapping (front/back) — the envelope banner correctly fires because the axis truly is wrong for this house.

**Gate status**: ✅ GRADUATED. Ready to proceed to Iter 79j.52a and beyond.

## Iter 79j.52a — Dismiss reconcile-failure downgrades session to photos-only (2026-07-06)
**Status**: SHIPPED · testing agent iter35 PASS.
- `AIMeasureButton.jsx::dismissRunError` (new) clears the local runError + runErrorMeta and, when the current preview carries `raw_ai._reconciliation_error`, additionally clears `preview` + `currentRunId` and immediately PUTs `/measure/sessions/{id}` with `preview: null` so a page nav + Resume can't re-summon the stale failure banner. Photos, ref dim, wall height, siding %, annotations are preserved.
- Per Howard 2026-07-06 (option a): `currentRunId` is cleared on dismiss — Debug View still holds the run history server-side, so no data is actually lost.

## Iter 79j.52b — Session self-heal on Resume when a good reconciliation exists on the server (2026-07-06)
**Status**: SHIPPED · testing agent iter35 PASS.
- `resumeSession()` now checks GET `/measure/ai-measure/latest-for-estimate/{id}` when the persisted preview carries `_reconciliation_error`. If the latest run doc is `status=done` with no reconciliation error, the healed run's `result` replaces the stale preview locally AND is PUT back to the session so subsequent resumes stay healed. Falls back to the existing "Prior reconciliation failed" banner if no fresher good run exists. Toast: "Resumed — session self-healed from a newer successful reconciliation."

## Iter 79j.54a — Diff mode in Debug View (2026-07-06)
**Status**: SHIPPED · UI verified · DiffPanel with real 2-run data pending future run.
- `AIExtractionDebugModal.jsx`: added a compare-pill (`data-testid=debug-run-diff-toggle-<run_id>`) next to each non-active run in the picker. Selecting one loads that run via `/status/{run_id}` and renders `DiffPanel` at the top of the reconciled column — a 3-column table (Field · Run A · Run B · Δ) covering roof type, avg eave, wall count / per-wall widths / heights / gable Δh, dormer count / per-dormer face + width + knee, opening count. Rows where A≠B highlight amber. Clear via `debug-diff-close-btn` or clicking the same compare pill again.
- Testing agent note: Red-House has only 1 graduated run so the panel could not be exercised end-to-end with real data. Storybook fixture or a fixture-driven pytest would let us regression-test the amber-highlighting path without burning a live run.

## Iter 79j.57c — First-visit onboarding checklist modal (2026-07-06)
**Status**: SHIPPED · testing agent iter35 PASS.
- `AIMeasureButton.jsx`: new `showOnboarding` state + localStorage key `aiMeasureOnboardingSeen`. On first modal open, an overlay appears with 6 concrete tips (3 markers per elevation, one per dormer face, never rely on corner shots as primary reads, all 4 elevations, add the free aerial, reference dim flips scale conf LOW→HIGH). Dismisses via "Got it, don't show again" and persists. A `Tips` button in the AI Measure header (`data-testid=ai-measure-open-onboarding`) re-opens it on demand.

## Iter 79j.57d — Re-run confirmation dialog on done+reconciled runs (2026-07-06)
**Status**: SHIPPED · testing agent iter35 PASS.
- `AIMeasureButton.jsx`: `attemptRerun` interposed between the Re-run button and `runMeasure`. Only fires the confirm dialog when the preview has a NON-error reconciliation AND walls[].length > 0 (per Howard 2026-07-06 option a — silent on failed runs so we don't train click-through).
- Confirm dialog body is SPECIFIC (not generic): "This estimate has a successful reconciled run — N walls, N dormers, N openings, N sqft siding. Re-running will replace it as the active result." followed by a per-dormer bullet list ("Dormer 1: face left, width 15.5 ft"). Prior run stays in Debug View history.
- Testing agent verified the confirm dialog blocks Re-run, Cancel restores state without triggering busy, and specific stats populate from `preview.raw_ai`.

## Follow-ups queued (from testing agent code review)
- **AIMeasureButton.jsx refactor** — file is now 4451 lines. Recommend extracting: `OnboardingChecklist`, `RerunConfirmDialog`, `RunErrorBanner` as separate sub-components in a new `AIMeasureBanners/` dir. Non-blocking but the next feature landing here should split proactively.
- **Debug button gate** — `showAdvanced && preview` uses a `useState` initializer that only reads localStorage once at component mount. If a user toggles Advanced in a different tab, the current tab won't see the change. Consider re-reading on modal open or exposing Debug as a first-class affordance.
- **Iter 54a fixture testing** — the diff-panel amber-highlighting code path can't be exercised against Red-House (only 1 run). Either (a) capture a JSON fixture pair after a future 2-run session, or (b) build a Storybook story.


## Iter 79j.59 — Direct Phase A, per-wave scheduling, split flags, pin-gap-signal (2026-07-07)
**Status**: SHIPPED · 18/18 pytest PASS (`backend/tests/test_pin_gap_and_key_routing.py`) · frontend banner regression-clean via screenshot.

### This morning's run — the justification (support datapoint #6)
- Phase B via `anthropic_direct` **succeeded in 142s** — first live confirmation the 79j.57b stall fix survives a real Anthropic round-trip.
- Phase A on the proxy **killed 5 of 8 photos at the 300s total cap** — proxy crawling; the right elevation never extracted; the right dormer was correctly NOT emitted (no confabulation). **Log this as datapoint #6: "142s success on REDUCED PAYLOAD (5/8 empty), full-payload confirmation pending."** The stall fix isn't proven until a direct Phase B survives a full 8-photo reconciliation.
- Trace quote for the no-confabulation moment: **"Contractor annotations on the empty photo-7 extraction (3 slider pins, symmetric SHAKE) suggest a POSSIBLE matching right-slope dormer, but with zero photo data it was not emitted — re-shoot the right elevation rather than confabulate."**

### 1) Split per-phase direct flags with legacy auto-migration
- Old: single `ANTHROPIC_DIRECT_ROUTE=phase_b_only`.
- New: **orthogonal flags** `ANTHROPIC_DIRECT_A=1` and `ANTHROPIC_DIRECT_B=1`. `_pick_llm_api_key(provider, phase=)` returns direct only when the matching flag is set AND `ANTHROPIC_API_KEY` is on file AND `provider=="anthropic"`.
- **Auto-migration**: when neither new flag is set but `ANTHROPIC_DIRECT_ROUTE=phase_b_only` is on file (Howard's current pod), Phase B is routed direct with no manual .env edit required.
- Startup log now reads: `[flags: A=unset, B=1, legacy=phase_b_only, key=present]` — grep-friendly.

### 2) Direct Phase A vision path + per-photo proxy fallback
- New `_extract_one_photo_direct(...)` uses `AsyncAnthropic` (SDK path already used by Phase B) with:
  - `max_retries=0` + explicit `httpx.Timeout` + outer `asyncio.wait_for(per_call_timeout)`.
  - **429 backoff with jitter**, capped at `AI_MEASURE_PHASE_A_DIRECT_MAX_RETRIES=2` per photo. Honors `Retry-After` header when present.
  - Same **Iter 79j.50 shrink** (max 1600px, JPEG q=80) applies via the shared upstream shrink loop — the direct path benefits identically. NOT proxy-only.
- `_extract_one_photo(...)` is now a router: picks direct vs proxy per photo. Non-recoverable direct errors (`timeout` / `api_error` / `exception` / exhausted `rate_limit`) **fall back to proxy for that photo only** — the proxy stays as a safety net.
- Concurrency: hidden env `AI_MEASURE_PHASE_A_DIRECT_CONCURRENCY` (default 2, matches proxy pattern). Start at 2, bump in production once real 429 patterns are observed against the tier (50 rpm / 40k tpm).

### 3) Wave-based Phase A dispatcher (removes the 300s cap footgun)
- Old: global 300s total cap over a semaphore-throttled batch → one hung LiteLLM wave silently ate the remaining photos' budget (this morning's incident).
- New: **per-wave budgets**. Photos are split into waves of `concurrency`, each wave gets its own `per_wave_budget = per_photo_budget + 10s`. A stuck wave times out ONLY the two photos in it, not the queue behind. `AI_MEASURE_PHASE_A_TIMEOUT` is now a no-op (logged for legacy operators).
- **Per-wave progress** published live to the run doc as `phase_a_progress: {wave, waves_total, done, failed, total, last_wave_elapsed_s, last_wave_photo_indices, last_wave_failed_photo_indices, transport, concurrency}` and surfaced through `GET /ai-measure/status/{run_id}`. Frontend can render "wave 2/4 · 3 ok · 1 timed out" between waves instead of waiting for the whole batch.
- Cancellation drain capped at 5s per wave — same defensive pattern that fixed the 1153s Phase-A hang in 79j.44.

### 4) Contractor-pin gap-signal in the UI
- New `_derive_pin_gap_hints(annotations, walls, dormers, orphaned_walls, empty_photos)` runs after Phase B. Three rules, deduplicated by `(kind, elevation)`, sorted for stable polling order:
  1. **Orphaned elevation with pin** — pin on `right`, right elevation not in walls[]: *"Your pins on the right elevation indicate coverage there, but no photo extracted that wall. Re-shoot the right side before quoting."*
  2. **Missing dormer from pin** — pin `callout=dormer` on right, no dormer emitted for right: *"Your pins indicate a possible dormer on the right slope — reconciliation did not emit one there. Re-shoot the right elevation squarely..."* (Howard's exact copy).
  3. **Empty photo with pin** — pin on photo #4, photo #4 timed out: *"Your pin on photo #5 tagged the left elevation, but that photo's extraction failed."*
- Surfaced as `raw_ai._pin_gap_hints[]` → `measurements._ai_pin_gap_hints[]` → rendered in the existing `ai-measure-empty-photos-banner` under a new "Your pins suggest coverage the AI didn't confirm" sub-section (data-testid `ai-measure-pin-gap-hints`, per-hint testids `ai-measure-pin-gap-hint-<kind>-<elevation>`). Each hint carries a `re_shoot_elevation` string — **no bare warnings, per Howard**.

### Files touched
- `backend/routes/ai_measure.py`:
  - `_pick_llm_api_key(...)` — split flags + auto-migration
  - Startup log rewrite with `[flags: A=..., B=..., legacy=..., key=...]`
  - `_extract_one_photo_direct(...)` NEW
  - `_extract_one_photo(...)` refactored as transport router with per-photo proxy fallback
  - `_run_two_phase_pipeline(...)` — new `annotations` kwarg; wave-based dispatcher replacing the semaphore + global-cap loop; `_publish_progress` helper writing to `phase_a_progress`
  - `_derive_pin_gap_hints(...)` NEW
  - `_aggregate_to_hover_shape` — new `_ai_pin_gap_hints` field
  - `ai_measure_status` — surfaces `phase_a_progress`
- `backend/tests/test_pin_gap_and_key_routing.py` NEW (18 tests: 9 routing + 8 pin-gap + 1 shared)
- `frontend/src/components/estimate/AIMeasureButton.jsx` — gap banner surfaces `_ai_pin_gap_hints[]` with actionable per-hint copy

### Follow-ups
- **Full-payload direct Phase B confirmation still pending** — requires an 8-photo Red-House re-run where Phase A completes cleanly.
- **Iter 54a fixture testing** — still blocked on getting two graduated runs; the direct-Phase-A path should make this cheap to acquire.
- **Frontend per-wave progress rendering** — backend now publishes `phase_a_progress` per wave; frontend still shows a single "Extracting per photo" state. Wire a "wave 2/4 · 3 ok · 1 timed out" line into the status pill next.


## Iter 79j.60 — Direct-Phase-A confirmation, Wave HUD, unanchored-dormer amber flag, direct-B timeout bump (2026-07-07 afternoon)

**Status**: SHIPPED · 23/23 pytest PASS · direct-A empirically confirmed on identical 8-photo input.

### 🟢 Support datapoint #7 — Transport indicted
Same 8 photos, same estimate (`a2329f30-2228-4a43-b9f7-9f34eb5970f7`), same model (`claude-fable-5`):
- **Proxy Phase A (morning)**: 5/8 photos dead at the 300s total-cap, 4 empty extractions on the successful reconcile → dormer count = 0.
- **Direct Phase A (afternoon, run `3c9bfd1d2c7e496d9cd7661039fddcd2`)**: **8/8 extractions succeeded**, all via `anthropic_direct`. avg latency 47.4s/photo, max 68.6s. Phase A wall-clock ~194s (well under the 300s that was killing proxy runs).
- **Transport is the bottleneck.** Same input, same photos, same model — direct route delivers full extractions where proxy drops 62% of them. The direct route is now the durable path for Phase A.

### 🔴 New finding — Direct Phase B ceiling exposed
With Phase A finally delivering a full 8-photo payload to reconciliation, direct Phase B on `claude-fable-5` hit the httpx `read=150s` cap I set in 79j.57 and timed out. Proxy fallback saved the run at ~244s. Fix:
- Bumped direct-B httpx timeouts to `total=360s / read=300s / write=60s`.
- Exposed `AI_MEASURE_RECONCILE_DIRECT_READ_TIMEOUT` env override so the ceiling can be tuned in production without a code push. Set to 300 by default; total is always `read + 60`.
- This morning's 142s direct-B success is now correctly logged as "142s on REDUCED payload (3/8 valid photos)" — full-payload direct-B confirmation still pending an 8/8 run with the raised ceiling.

### 🔴 Counter-evidence for the marker SOP — 79j.57c isn't polish, it's an accuracy requirement
Same afternoon run reconciled dormers at **19 ft (left)** and **28 ft (right)** vs Howard's taped ground truth of **~15/15 ft**. Root-cause investigation:
- **`_build_annotation_hint` completely ignores `_scale_refs`** — the profile boxes reach Claude's prompt (5 SHAKE hints on 5 elevations were fed in) but the WALL_REF / WIN_REF marker coordinates Howard physically drew on the photos are NEVER surfaced as explicit measurement anchors in the prompt text.
- Claude occasionally reads a drawn marker VISUALLY (see `reference_used: "Contractor WALL REF 324\" (27 ft) on the front..."`), but not reliably — hence 25-90% drift on the two dormer widths.
- The graduated 79j.58 Red-House (15.5 / 15 ft) had markers in the photos AND Claude happened to read them cleanly; today's run drifted because the AI wasn't explicitly TOLD where to read.

### Rule 4 — Unanchored dormer amber flag
- `_derive_pin_gap_hints` now emits `kind="unanchored_dormer_width"` for any dormer whose width was derived WITHOUT a cited anchor (regex: `WALL_REF | WIN_REF | reference[- ]?dim | scale[- ]?bar | taped_dim | anchor`) AND no `_scale_refs` entry on the dormer's `source_photos`.
- Runs even when the contractor drew ZERO pins — an unanchored width is a problem regardless of whether the contractor annotated.
- Copy: *"Dormer on the {face} slope reports {W} ft wide but NO reference marker was in frame. Unanchored dormer widths drift 25-90% — re-shoot the {face} elevation with a WALL_REF or WIN_REF bar in frame before quoting."*
- Surfaces in the existing amber gap banner via `_ai_pin_gap_hints[]` — no new UI needed; the frontend banner already renders every hint kind with amber styling.

### Wave HUD — contractor-plain, no jargon
- Shipped `data-testid="ai-measure-photo-hud"` in the modal body. Photo dots (green=read, amber=didn't complete, purple-pulse=reading now, grey=pending) + a plain-english status line:
  - `Read 6 of 8 · working on photo 7…`
  - `Photo 3 didn't complete — you can re-shoot it later.`
  - `All 8 photos read.`
- Driven by `phase_a_progress.photo_status` (cumulative per-photo map) which the backend now publishes on every wave completion. Ready to use on the NEXT run.

### Files touched
- `backend/routes/ai_measure.py`:
  - Rule 4 addition to `_derive_pin_gap_hints` + regex-based anchor detection
  - Direct-B httpx timeout bump + `AI_MEASURE_RECONCILE_DIRECT_READ_TIMEOUT` env override
  - `_publish_progress` cumulative `photo_status` field
- `backend/tests/test_pin_gap_and_key_routing.py`:
  - +5 tests for Rule 4 (cited-anchor no flag, no-anchor flags, source-photo scale_refs no flag, no-annotations still fires, no-width no flag)
- `backend/.env`: `ANTHROPIC_DIRECT_A=1`, `ANTHROPIC_DIRECT_B=1` added (legacy `ANTHROPIC_DIRECT_ROUTE=phase_b_only` left in for reversibility; new flags take precedence)
- `frontend/src/components/estimate/AIMeasureButton.jsx`: Wave HUD component (photo dots + contractor-plain status line), `photoProgress` state, polling loops updated to capture `phase_a_progress`

### Follow-ups (Howard sign-off needed before shipping)
- **PROPOSED: Plumb `_scale_refs` into Phase A prompt.** Currently the drawn marker coordinates live only on the estimate — never in the prompt text. If we surface them as explicit anchors ("photo 6 has a 15-ft horizontal reference bar from x=0.08 to x=0.89 at y=0.545 — use this to scale everything else in this photo"), Claude should stop drifting on unanchored dormer widths. This is a Phase A prompt change; wants explicit approval since it modifies the extraction contract.
- **Full-payload direct Phase B confirmation** — re-fire the afternoon run with the raised read timeout to prove direct-B on full 8-photo payloads. Should complete in ~250s.
- **Frontend: Wave HUD live-test on the NEXT run** — HUD is coded; verified visually via component but not yet end-to-end during a live extraction.



## Iter 79j.61 — Scale-refs plumbed into Phase A prompt + contextual accuracy nudge + direct-B max_tokens bump (2026-07-07 late afternoon)

**Status**: SHIPPED · 29/29 pytest PASS · scale-ref plumbing EMPIRICALLY VERIFIED in Phase A output.

### 1) `_scale_refs` now reach Claude as explicit prompt anchors
Root cause diagnosed in this turn (backing datapoint #7): `_build_annotation_hint` piped only `profile_annotations` into the Phase A prompt — the WALL_REF / WIN_REF marker coordinates Howard drew on the photos NEVER surfaced as text. Claude only read them when it visually noticed the drawn line, which it did unreliably (afternoon 19/28 ft dormer drift = Claude missed the markers).

Fix: new `_scale_ref_hint_for_photo(annotations, photo_idx)` helper renders each `_scale_refs` entry as:

```
CONTRACTOR-DRAWN SCALE REFERENCE ON THIS PHOTO — a horizontal reference bar
of 15′ (180″ / 15.00 ft) runs from normalized pixel coordinates
(x=0.080, y=0.545) to (x=0.890, y=0.545). USE THIS BAR to lock scale for
this photo — everything else in the frame is measured against it. Cite this
bar in `width_reasoning` / `height_reasoning` whenever a dimension was
scaled from it. When this bar is present, dormer / gable / upper-feature
widths should read to within ±1-2%; without it the same features drift
25-90%.
```

Threaded through `_build_phase_a_prompt` → `_extract_one_photo` → wave dispatcher. Both proxy AND direct transports get identical text (as always).

**Empirical validation** — run `04c9539b…` Phase A output cites the marker explicitly on photo 0:
> "Wall dimensions: eave to grade at side corners ~9.8 ft. Used WALL REF = 324″ spanning ~1107 px (0.293 in/px); side eave corner sits ~400 px above grade → ~117 in ~ 9.8 ft. Pitch **8/12** (was 6/12 before scale-refs), gable triangle 8.3 ft above eaves."

This is exactly the anchored-scale behavior Howard wanted — Claude explicitly citing the marker in `width_reasoning`.

### 2) Direct-B max_tokens bumped to 32k
Post-scale-refs, run `12958ff1…` hit the OLD 16k max_tokens cap: Claude burned 13,768 tokens on extended thinking (aligning anchor geometry across 5 marked photos) + only 5,136 tokens of visible JSON → response truncated → Phase B returned empty walls/dormers.

Bumped `max_tokens=32000` for direct-B (env-tunable via `AI_MEASURE_RECONCILE_DIRECT_MAX_TOKENS`). Still well under model's 64k output limit. Retest run `04c9539b…` was interrupted by env-flag restart mid-Phase-B (marked `error` in mongo) — full-payload direct-B validation with 32k max_tokens PENDING a clean re-fire.

### 3) Contextual accuracy nudge (Howard 2026-07-07 quantified copy)
`AIMeasureButton.jsx` now auto-opens the onboarding checklist when a contractor has uploaded photos but `_scale_refs` is empty. Separate localStorage key (`aiMeasureUnanchoredNudgeSeen`) so dismissing the first-run nudge doesn't silence this contextual one. Overlay renders Howard's exact copy at the top of the checklist:

> **Your uploaded photos have no reference markers**
> Photos without reference markers can drift 25-90% on dormers and upper features. Add a WALL REF or WIN REF to each elevation for tape-grade accuracy.

Quantified. Contextual. Fires at the exact moment the accuracy risk exists — not once at first-visit and then never again.

### Follow-ups still open (Howard sign-off / next session)
- **Clean re-fire of the confirmation run** — same 8 photos, direct-A + direct-B with scale-refs plumbing + 32k max_tokens. Should produce dormer widths within ±1-2% of Howard's taped 15/15 ft ground truth. Ready to fire via UI (or `curl` on `/api/measure/ai-measure` with the same `photo_paths`).
- **Wave HUD live-test** during the re-fire — HUD is coded, verified in isolation, but not yet e2e-observed during a live 8-photo Phase A.

## Iter 79j.62 — Reference Marker Coverage Tile (2026-07-07 evening)

**Status**: SHIPPED · smoke-tested via screenshot · grey/red/amber/green states all render.

### The accuracy contract is now visible at every stage
Read-only 4-cell grid (front / right / back / left) rendered in the AI Measure modal body between the Wave HUD and the upload area. Same data source as the contextual accuracy nudge (`photoAnnotations`) — no new state, no new network. Cells transition through:

- **Grey** — no pins on this elevation yet. Neutral state during upload.
- **Red** — pins exist but no `_scale_refs` covers any photo of this elevation. Coverage but no anchor.
- **Amber** — dormer pin exists on this elevation AND no `_scale_refs`. This is the specific accuracy hazard the 79j.61 plumbing quantifies (dormer widths drift 25-90% unanchored).
- **Green** — at least one `_scale_refs` entry on a photo tagged to this elevation. Tape-grade coverage.
- **Green + dormer emblem** — anchored AND a dormer pin present. The gold-standard case.

Summary line at the top of the tile:
- Any amber → *"Dormer pinned without a marker — widths will drift 25-90%"*
- Any red/grey → *"Some elevations missing markers — accuracy risk on those"*
- All green → *"All 4 elevations anchored · tape-grade"*

### Data flow (no new pipes)
- Iterates `photoAnnotations` boxes per photo, collects `elevation_label` + `callout` sets.
- Cross-references `photoAnnotations._scale_refs` keyed by photo idx.
- Also credits a scale ref as coverage even when no pin tags the elevation yet — contractors often draw markers before tagging (per Howard SOP).

### Test IDs
- `ai-measure-marker-coverage` (container)
- `ai-measure-marker-coverage-summary` (top-right status text)
- `ai-measure-marker-coverage-cell-{front|right|back|left}` (each cell)
- `data-state` attribute on each cell for QA drive: `green` / `green_dormer` / `amber` / `red` / `grey`

### Rendered together, the accuracy stack is now:
1. **Marker Coverage Tile** (before running) — green/red/amber grid, visible before Run
2. **Contextual Accuracy Nudge** (on upload without markers) — quantified 25-90% warning, checklist
3. **Wave HUD** (during Phase A) — per-photo dots + contractor-plain status
4. **Amber gap banner + Rule 4 flag** (after running) — per-hint re-shoot copy for unanchored dormer widths + missing elevations + dormer pins on empty photos


## Iter 79j.69 — Run 4 verdict (91.3%) + pricing suite repaired (2026-07-09)
- Re-validation run (swapped right photo) scored **91.3%**: left 9.4 amber (tape 10.31), right 8.1 amber/count (tape 7.19, mode flipped cross-plane→count — new prompt rules VERIFIED), left dormer 17 fail (tape 15), right dormer 15 pass. First no-fail wall result.
- Howard's ruling: red-house prompt iteration CLOSED. Candidate shelf: "when courses uncountable, weight same-plane ref scaling over generic pixel reads" — test against NEXT house (the ranch), not this one.
- Pricing tests fixed (staged in /tmp during code freeze, applied post-terminal, zero mid-run reloads): admin token now read from backend/.env via dotenv_values (was defaulting to fake token → 403s); `test_admin_get_matrix_requires_token` now sends NO headers; stale hardcoded Mezzo 259.608 replaced with live-DB parity asserts; Starter parity lock 7.46→7.64. **44/44 pricing tests green** (was 11 failing).
- LESSON: uvicorn --reload watches /app/backend/tests/ too — editing test files DOES restart the backend and kills in-flight asyncio runs.

## Iter 79j.70 — Per-dormer bbox routing + true bbox-derived opening positions (2026-07-09)
### Root cause (pre-flight confirmed)
Phase A DOES emit real pixel bboxes per opening — no regression. `_slim_extraction_for_reconcile` strips them from the text-only reconciler payload, so Phase B can only emit {0,0,0,0} placeholders (its own note admitted this). Frontend treated 0 as a finite coordinate → every opening piled at the wall corner/top = "scattered openings".
### Backend (`routes/ai_measure.py`)
- New `_restore_bboxes_from_phase_a(final, extractions)`: post-reconcile join of final openings back to Phase A pixel bboxes. Match order: exact opening_id → reconciler-suffixed id (`right-w1-p6`→`right-w1`) → positional (type + along_wall ±3ft + width ±12in). Normalizes by compressed-photo dims; sets `bbox` (normalized), `bbox_photo_idx`, `_bbox_source`. Unmatched zero-bboxes → `bbox: null`.
- Per-photo dims (`_image_w`/`_image_h`) stamped on extractions before raw_per_photo persist (underscore keys auto-stripped from reconciler payload; persists for reconcile-only retries).
- On-dormer openings get `dormer_face` routed via wall label match → dormer `_source_photo_indices` fallback.
- Called in `_run_two_phase_pipeline` (before return) AND `_execute_reconcile_only_worker`.
### Frontend (`HouseModel3D.jsx`)
- `hasBbox()` guard: bbox only trusted with real area (w>0,h>0) — legacy zero-placeholders now ignored.
- X-positioning priority: `along_wall_ft` (wall-local ft, reconciler-verified center) > bbox X-fraction > even spacing. Y still bbox-derived.
- Per-dormer routing live: openings route to dormer whose `migrateFace(dormerFace)` matches; face-less orphans stay on primary; legacy (no faces) keeps all-to-primary.
- Dormer openings clamped inside face extent (cv ± halfWD).
### Testing
- `tests/test_bbox_restore_iter70.py` — 7 tests (id/suffix/positional match, zero-drop, no-dims drop, dormer routing) all pass. 66 pipeline regression tests pass. Screenshot-verified 3D: windows spread along walls, both dormers render their own windows.
- NOTE: full E2E of backend restore path needs the NEXT AI run (ranch) — existing run 4 raw_per_photo lacks `_image_w/_image_h` stamps.
### Gate order next: Three.js static PNG → embed in Customer Quote PDF.

## Iter 79j.71 — Shake quantity composition audit + single-owner fix (2026-07-09)
### Audit finding (run f423c216, produced the estimate's 6.0 SQ Pelican line)
SHAKE 584.3 ft² = 275.2 geometry dormers (face DOUBLE-added: reconciler fills walls[].dormer_face_sqft with the face, then apply_roof_type_material_math added face+cheeks on top) + 147.0 Claude ECHOES of the contractor's annotator boxes as accent_profiles ("contractor ground truth") + 162.1 annotation overlay (same boxes AGAIN). Left dormer face counted 3×. Tape truth ~155 ft². Separately, run 4 crashed the whole breakdown (accent_profiles emitted as strings) → _per_profile_sqft {} → zero shake. Both directions silent.
### Fixes (all five, Howard-approved)
1. **apply_roof_type_material_math**: single owner for the face — reconciler value wins when present, geometry fills the gap; cheeks always geometry; openings deducted once. Stamps `_dormer_composition` {face_owner, face_sqft, cheek_sqft, openings_deducted} on the wall.
2. **Echo skip**: accents with `from_annotation: true` (new prompt field on Phase A + reconcile schemas + hint instruction) or ground-truth phrasing (`_ANNOTATION_ECHO_RE`) are skipped; annotation overlay is sole owner. Counter `skipped_echo_accents` surfaced.
3. **Annotation override**: box located dormer/gable overlapping geometry → overrides the surface PROFILE (callout `user:<profile>`), never adds ft²; "body" boxes deduct their ft² from wall_body_sqft (area moves families). Frontend guard: "quote dormers/gables as shake" toggles skip (toast) when the breakdown already owns the surface as shake.
4. **Hardened parsing**: non-dict accents skip w/ `malformed_accents` counter — breakdown survives (run-4 regression).
5. **Composition tripwire**: `_finalize_breakdown` builds per-surface `composition` {family: [{elevation, surface, owner, sqft}]}; per_profile totals = component sum by construction; `_dormer_composition` mismatch or accent-duplicates-dormer → `conflicts`. `_profile_siding_lines` (hover.py) amber-flags conflicted families: qty 0 + "⚠ ... composition conflict — verify by hand", clean lines carry itemized composition note ("= left dormer 86.1 + ..." ).
### New measurement keys
`_per_profile_composition`, `_profile_composition_conflicts`, `_skipped_echo_accents`, `_malformed_accents`.
### Testing
`tests/test_shake_composition_iter71.py` — 11 tests pinning the exact 584.3 fixture → new composition 301.4 (dormers 139.25 once + annotations 162.1 once, echoes skipped), overrides, crash-hardening, amber lines. 133 pass across all profile/annotation suites; full backend suite: 644 pass, 9 fail + 15 errors ALL pre-existing on pristine main (stale catalog-seed asserts in test_iteration34/5/6, estimator_api email/status, lp_admin_preview flag — same disease as the pricing seeds, queued).
### Acceptance status
Run-4 data through the new math: dormers 86.1 + 88 = 174.1 ft² ∈ Howard's taped 155–200 band ✓ (unit-verified). NOTE: run 4's PERSISTED walls still carry the pre-fix double-add (171.09/163) — re-apply from that stale preview won't recompute. Acceptance closes on the NEXT AI run (Howard re-confirming cheek depth first). Run-4 dormer callout came back "lap", so shake arrives via the (now guarded) dormer toggle or a dormer-located annotation box.

## Iter 79j.72 — Stale test suites repaired: full backend suite GREEN (2026-07-09)
Howard promoted this ahead of the ranch run: "a real regression can't hide among known-stale failures."
### Root causes (24 failing-on-main tests)
1. **Dead admin account**: iteration5/6/estimator_api defaulted to `admin@wolfandson.com` (doesn't exist in users collection) → 401 setup ERRORs on 15 tests. NOT rate limiting (SEC-005 only counts failed logins and security tests use synthetic XFF IPs).
2. **Stale pins vs evolved seed**: iteration34 pinned 22/16/27 item counts, soffit "up to 13 inch wide" variant names, and lab==125 — the SEED evolved (27/12/27) and labor is contractor-editable. estimator_api pinned sender `onboarding@resend.dev` (env now quotes@pro-quotes.com). iteration5 pinned first section "Install Vinyl Siding"/"Conquest .040" (seed: "Vinyl Siding"/full SKU) and lab>0 (seed labor is 0). lp_admin_preview pinned flag OFF (env has LP_AI_FORMULAS_V1=true) + hardcoded admin token in source.
3. **10s read timeouts under full-suite load** in profile_annotations_http.
### Live-source treatment applied
- All 6 files load creds/URLs via `dotenv_values('/app/backend/.env'|frontend)`: ADMIN_EMAIL/PASSWORD, SIGNUP_CODE, SUPPLIER_ADMIN_TOKEN, SENDER_EMAIL, LP_AI_FORMULAS_V1.
- iteration34 expectations derive from `catalog_seed.DEFAULT_SECTIONS` / `TIER_PRICES` (counts, Charter Oak soffit variants, tier prices). Labor asserts structural validity (numeric ≥ 0), never a pinned dollar amount.
- lp preview test now asserts endpoint reports the LIVE flag state truthfully.
- profile_annotations timeouts 10→30s.
### Result
`pytest tests/` (excl. test_anthropic_direct_key.py which calls the paid Anthropic API): **668 passed, 1 skipped (intentional obsolete marker), 0 failed, 0 errors** in 2m16s. Suite is a trustworthy regression gate for ranch data.
### Roadmap update per Howard
- "Where every ft² comes from" composition expander in Breakdown card: QUEUED right behind Three.js PNG → PDF work (transparency = the material-quantity twin of Tape Check; uses `_per_profile_composition` already persisted per run).
- Run 4 stale composition: confirmed NO re-apply needed; tape-truth panel edits stand; new math proves itself on the ranch.

## Iter 79j.73 — Run Readiness checklist (2026-07-09)
Generic pre-run checklist for ANY new property, written once for two audiences (field SOP + first-house contractor onboarding), per Howard's spec.
### Component: `/app/frontend/src/components/estimate/RunReadinessChecklist.jsx`
Rendered at the top of the AI Measure modal's pre-run (photo) screen (`!preview` branch in AIMeasureButton). Collapsible, N/7 ready chip, header tagline "Same checklist every property — first house or fiftieth".
- **Auto-detected (3):** calibration exposure entered (amber when empty — points to the Calibrate control); Tape Check pre-filled (GET /estimates/{id}/tape-check, shows n/4 walls, "scoring is one click after the run"); profile boxes location-tagged (counts untagged boxes; neutral when zero boxes).
- **Manual, persisted per estimate in localStorage `runReadiness:{estimateId}` (4):** siding exposure MEASURED on this house ("Never assume 3.75″ — the most-assumed number in siding", the trap named explicitly); WALL REF per elevation on the wall's OWN plane (cross-plane rejection warning); WIN_REFs on dormers/upper features; bottom courses visible (SOP).
- Onboarding modal got a closing note pointing to the checklist as the per-property SOP (single source, both audiences).
- data-testids: run-readiness-checklist / -toggle / -count / -item-{key} / -check-{key}.
### Testing
Screenshot-verified on a fresh estimate: renders 7 items, amber states for missing calibration + empty tape, checkbox tick persisted and chip updated 2/7. Smoke-test estimate deleted after. Frontend compiles clean.

## Iter 79j.74 — Three.js 3D PNG → Customer Quote PDF (2026-07-09) [GATE TASK SHIPPED]
### Chain (all E2E-verified in preview)
1. **Capture** (`HouseModel3D.jsx`): "Use in Quote PDF" button on the 3D canvas (camera icon, top-right; states idle/saving/"On Quote PDF"). `renderer.render()` then `canvas.toBlob()` (NOT fetch(dataURL) — that failed silently). **Auto-capture** fires once ~1.5s after mount when the estimate has no snapshot (zero-click default 3/4 view); contractor can re-frame + re-click any time. GOTCHA fixed: latch `autoSnapDone` INSIDE the timer — parent re-renders change `onSnapshot` identity, re-running the effect and cancelling the timer while the latch was already set (silent one-shot failure).
2. **Persist**: blob → POST /api/uploads → PUT `/api/estimates/{id}/model3d-snapshot` (new endpoint, validates url startswith /api/uploads/, no traversal; company-scoped; stores `estimate.model3d_png_url`).
3. **Quote surfaces**: `emailQuote.js` model3dBlock ("Your Home — 3D Model" + "Built from AI photo measurements..." caption, en+es keys in dictionaries.js) rendered above Job Photos; `QuoteModal.jsx` mirrors the block in the on-screen preview (data-testid quote-3d-model-block). WeasyPrint fetches the public upload URL → PDF verified with embedded Image XObject via curl of POST /estimates/{id}/pdf (payload field is `recipient_email`, not `to`).
### Testing
- Playwright: manual button E2E (uploads 200 → snapshot PUT 200 → "ON QUOTE PDF"), zero-click auto-capture E2E after clearing the field, quote modal shows the 3D image.
- `tests/test_model3d_snapshot_iter74.py`: roundtrip + validation (400s for external/traversal/nested URLs) + auth. 22 passed with estimator_api.
- NOTE: `DELETE /api/estimates/{id}` exists and is used by tests for cleanup.
### Lesson
An earlier search_replace of the HouseModel3D render site reported success but was later found absent — ALWAYS grep-verify critical prop wiring after batch edits.

## Iter 79j.75 — "Where every ft² comes from" composition expander (2026-07-09) [GATE TASK SHIPPED]
The shake audit as a permanent self-service tool — material-quantity twin of the Tape Check panel.
### Component: `/app/frontend/src/components/estimate/CompositionTrace.jsx`
Collapsible expander inside PerElevationBreakdownCard (below the description, above the cross-check panel). Header: "Where every ft² comes from · Each surface once, one owner each". Per family: total ft² + surface count, then a row per surface (elevation · surface · ft² · owner). Owners: AI geometry / AI geometry·your profile (user: callouts) / your annotation box (_source=annotation) / manual accent / AI accent.
### Design decision
Trace is recomputed CLIENT-SIDE from the live `_per_elevation_breakdown` (not the run-time `_per_profile_composition`) so it stays true through chip swaps and added accents, and works on pre-iter-71 runs. Run-time `_profile_composition_conflicts` render as amber banners ("quote line amber-flagged qty 0 until verified"); client-side duplicate (elevation,surface) detection for body/gable/dormer adds its own amber rows.
### Testing
Playwright on a throwaway estimate+session seeded from run f423c216's stored result: expander renders LAP 1327.6 = 6 surfaces, SHAKE 584.3 = 13 surfaces with owners — on that pre-fix run the echo accents are visibly identifiable, which is the audit intent. Fixtures deleted after. Frontend compiles clean.
### Roadmap updates per Howard
- Accept-page interactive 3D MERGES with the queued photo/3D side-by-side as ONE block. Constraints: read-only (no panels/numbers a homeowner could misread as editable — just their house, orbiting) + graceful degradation to the static PNG on weak phones. Queued post-gate.
- Gate remainder: accuracy sparkline (floor: ≥3 runs, always paired with current score, never trend alone) → then the RANCH RUN outranks everything.

## Iter 79j.76 — Stepped tape-check segments + start_ref (2026-07-10) ✅
Letrick ranch (EST-191890 / c864939b) has a stepped foundation: siding start-line staircases, so a wall carries multiple course-counts/heights.
- **Backend** (`routes/estimates.py`): tape wall now accepts number (legacy), null, or `{"segments":[{"height_ft","courses?"}...1-4], "start_ref": grade|foundation_top|brick_ledge|siding_start}`. Scoring: stepped walls score AI against the NEAREST segment bound (inside range = delta 0 pass); history rows carry `tape_segments`, `stepped`, `start_ref`.
- **Frontend** (`TapeCheckPanel.jsx`): per-wall ⇢ stepped toggle + seg-2 input, start-line select, load-normalization (stored segment objects hydrate seg1/seg2/toggle/start_ref instead of dumping an object into the number input).
- **Tests**: `test_tape_segments_iter76.py` (roundtrip + validation + range scoring) — full suite **678 passed / 1 skipped** (one load-timing flake in `test_phase_a_resilience` passes standalone).
- **Letrick tape entered (Howard-confirmed, exposure 4.25″, all counts from bottom siding course → start_ref=siding_start)**: FRONT 25c=8.9′ single · BACK 28c=9.9′ single · LEFT stepped 26c=9.21′→23c=8.15′ · RIGHT stepped (mirror, per Howard's annotated right-elevation photo) 23c=8.15′→26c=9.21′. Courses stored on segments.
- **RE-SCORE run fb8cf60e**: **82.8%** (was 80.7% flat) — 0✓ 0⚠ 4✗. Deltas: front +1.6, back +1.4, left +2.29 (vs nearest bound 9.21), right +1.09. AI overreads every wall even against the TALL segment bound — consistent with the right-gable overread finding. AI prompt untouched per Howard's sequencing directive (observe baseline first).
- Verified live in UI: stepped toggles hydrate, 82.8% chip, ⇢ range markers.

### Next (unchanged queue)
1. Blueprint Measure baseline on Letrick prints (4-way comparison)
2. Accuracy sparkline (≥3 runs floor) — Letrick now has 1 scored run
3. Right gable overread root-cause + appendage gap (chimney chase) — part of held AI prompt-tuning phase
4. Interactive 3D on Accept page; Contractor Window labor divergence; PDF upgrade lines; PWA icons; ISS New Construction Siding catalog

## Iter 79j.77 — Blueprint baseline + sparkline + Candidate 1 (count boundary) RUN DOC (2026-07-10)

### Blueprint Measure baseline — Letrick (run 1358273a, scale confidence HIGH, 10 sheets)
Walls uniform 9.5′ · footprint 54×30 · pitch 7/12 (roof plan) · gables 127.5 ft²/end (emitted `gable_triangle_height_ft: 8.5` per gable wall) · siding 1,851 ft² · 10 windows + 2 doors (sheet-7 schedule) · 6 OSC + 2 ISC.
- **Howard ledger confirmations**: corner count CORRECT — chimney chase (rear) is the only bump-out; 4 base corners + 2 OSC + 2 ISC at the chase. Truck's 10 OSC vs blueprint 6 is **pieces vs locations** (chase corners run ~18-19′ full height, consume extra posts). **Corner answer key: 6 locations / 10 pieces** — candidate 3 acceptance must score LOCATIONS detected, never piece count.
- **Appendage blindness is photo-side only** — chase is on the prints and blueprint caught it. Photo autopsy (pre-candidate-3): (a) why a photo fails with two consecutive empty extractions, (b) why the back-elevation photo that images the chase reported no appendage.
- **Gable open item RESOLVED**: blueprint's 8.5′ is a drawing-scaled read rounded to 0.5′, NOT pitch-derived (7/12 × 15′ half-span = 8.75′; raised heel ~1′6″ per roof plan would make the true triangle taller still). Right-gable investigation must target the pitch(+heel) computation, not the blueprint 8.5.

### Accuracy sparkline (TapeCheckPanel)
SVG polyline in the header, chronological, green/red by trend, paired with the current % chip. Hard floor: renders ONLY at ≥3 scored runs. Verified: red house (4 runs) renders; Letrick (1 run) does not.

### Candidate 1 — count-boundary (siding-start, not grade) — SHIPPED TO CODE, VERDICT MIXED vs pre-registration
**Change** (`ai_measure.py`): Rule 5 + SIDING EXPOSURE injection now count from the BOTTOM OF THE FIRST SIDING COURSE (siding start line); explicit prohibition covers the count AND added inches (foundation/membrane/parging → `notes` only); occlusion fallback = estimate from course rhythm + `start_line_occluded: true`, never grade, no silent guessing. New schema field `start_line_occluded` plumbed through `final["photos"]`. Pin tests: `test_count_boundary_iter77.py` (6). Suite 678 green. Supporting fixture: prints show exposed concrete w/ brick forms between foundation top and approx. grade; "final grade determined on site".
**Validation** (both fixtures, cached photos, code frozen):
- **Letrick rerun 29e03bee**: 82.8% → **93.5%** (2✓ 1⚠ 1✗). Mechanism (a) foundation-inclusion ELIMINATED — all 7 valid photos cite the exclusion; the 23c corners read 8.1′ (tape 8.15′) and the 26c corners read 9.2′ (tape 9.21′) — the stepped mirror structure is now visible in the AI's own reads. **BUT pre-registered front criterion FAILED: 27 courses/9.6′ vs Howard's 25/8.9′ (partial movement 30→27)** — finding (b) count inflation is a REAL SECOND MECHANISM (also left photo2: 30c vs Howard 26 max, unchanged). Back criterion NOT ASSESSABLE: back photo (idx 4) returned two consecutive empty extractions this run — note the empty photo MOVED (prior run idx 3 failed, idx 4 read fine; this run idx 3 fine, idx 4 failed) → intermittent per-photo failure, not a bad photo. Reconciled back=9.6 is a front copy; its -0.3 "pass" is accidental.
- **Red house rerun 56589e26**: 91.3% → **92.8%**, in the 91–93 band ✓. Scored walls IDENTICAL to prior (left 9.4, right 8.1); woodpile photo count unchanged (30c); `start_line_occluded` fired correctly on the woodpile/shrub photos; honest nulls where courses unresolvable. Left dormer improved 17→15 (now delta 0).
**Per pre-registration this is a FAIL verdict — reported, not silently shipped.** Howard's ruling (2026-07-10): **option (c) — KEEP**, with a pre-registration amendment on the record (the fail clause did its job: finding (b) confirmed distinct, nobody declared victory; reverting would un-kill mechanism (a) and re-contaminate the 1b baseline). Letrick baseline logged with an asterisk on the back wall. Finding 1 stays OPEN as candidate 1b.

## Iter 79j.78 — Blocking items 1+2 + stability proof + 1b evidence (2026-07-10) ✅

### Item 1 — Reconciler honesty fix (SHIPPED, pin-tested)
The reconciler WAS honest in provenance (`height_ft_source: "estimated_no_direct_view"`, confidence 45) — the violation was downstream: Tape Check scoring treated the placeholder as a read and let it score -0.3 "pass".
- **Fix** (`estimates.py` scoring): walls with `height_ft_source == "estimated_no_direct_view"` OR `height_imputed: true` are surfaced as `imputed: true` (verdict/delta null) and EXCLUDED from accuracy/passes/fails. All-imputed runs → 400.
- **Panel** (`TapeCheckPanel.jsx`): imputed rows show a gray "unread" chip (`tape-check-imputed-{wall}`), never a verdict.
- **Tests**: `test_reconciler_honesty_iter78.py` (3, HTTP with seeded run docs).
- **Retro-flag**: Letrick run 29e03bee re-scored honestly: 93.5% → **92.3%** (1✓ 1⚠ 1✗ + back UNREAD). History entry replaced.

### Item 2 — Empty-extraction autopsy + stability proof (DONE)
Two DISTINCT error classes, not one:
- **Run 1 (fb8cf60e) photo 3**: `_empty_retry_attempted: true` — two consecutive genuinely-empty Claude responses over anthropic_direct (89s + 66s). Retry = one re-send of the same photo with a "look harder" nudge prepended; both attempts judged empty by `_is_empty_extraction`. WHY was undiagnosable — raw response text wasn't persisted. **Fix shipped**: `_stamp_empty_diagnostics()` now persists `_stop_reason`, `_raw_text_len`, and a 400-char `_raw_response_excerpt` on every empty extraction (both transports). Pin tests: `test_empty_diagnostics_iter78.py` (4).
- **Run 2 (29e03bee) photo 4**: `phase_a_wave_cap` — NOT an empty response; the wave scheduler cancelled the task at the 250s per-wave budget. Retry never applied (task cancelled mid-flight). Root cause: TWO reruns launched concurrently (Letrick + red house) doubled direct-key load → per-call latency ballooned → wave 3 starved. **Operational rule: one run in flight at a time on the direct key.**
- **Stability proof (run 97d99abb, Letrick solo)**: **8/8 photos, 0 empties**, photos 3 AND 4 both clean, latencies 40–96s. Scored **94.1%** (2✓ 1⚠ 1✗): front 10.3 (+1.4 fail), back 10.6 (+0.7 amber, VALID read this time), left 8.85 (in range, pass), right 8.1 (-0.05 pass). Letrick now has 3 scored runs → sparkline renders (verified live).

### Candidate 1b evidence pull (NO prompt change proposed yet — Howard writing fresh pre-registration with boundary-explicit ground truth)
Front photo 0 (square-on, SAME image, 3 runs): counts **30 → 27 → 29** (Howard 25) — the full-wall count is stochastic and always high. Left photo 2: **30 → 30 → 26** (Howard max 26) — run 3 nailed it. Back photo 4: 29 → empty → 30 (Howard 28).
**Signature per Howard's hypothesis**: corner/segment-anchored counts (23/24/25/26 — courses large in frame) are repeatedly dead-on (run 3 photo 3: 25c/8.9′ = Howard's front count exactly; right wall corners 23c/8.15′ + 26c/9.21′ mirror the tape). Full-elevation square-on counts (~27-30, courses small in frame) inflate and fluctuate ±2. Tell in the reasoning text: full-wall counts are always "~N" approximations that "cross-check consistent with WALL REF pixel scale" — suspicion: the count is back-derived from the pixel read rather than independently counted. Top-boundary language also varies on back wall: "to eave line" / "to frieze" / "to the soffit" — possible top-boundary slop worth a look in 1b.
**Suite: 691 passed** (1 known load-timing flake passes standalone).

## Iter 79j.79 — Circularity confirmed + corner-shot guidance + Accuracy Report PDF (2026-07-10) ✅

### 1b circularity check — CONFIRMED (evidence-level, no fix proposed)
For every verifiable inflated full-wall count, reported count ≡ round(cited pixel inches ÷ 4.25) within ±1:
R2 front px 115-120″ → 27c · R3 front px 125″ → 29c (125/4.25 = 29.4) · R2 left px 131″ → 30c (30.8) · R3 back px ~131″ → 30c (30.9). Counts fluctuate across runs (30→27→29 on the SAME front image) because the pixel read fluctuates — enumeration would be deterministic. Every tape-exact count (23/24/25/26c on corner-anchored reads) either carries NO pixel citation or explicitly rejects it ("corner perspective distorts px-per-inch"; R3 left called pixel "similar-but-noisier, so course count is reported" — the one full-wall read that got 26 RIGHT). **Signature: count and eave height are ONE measurement (pixel), not two independent ones, on distant square-on walls.** Run 3's 94.1% carries the asterisk (front 29 vs 25); finding 1b logged OPEN regardless of aggregate. Top-boundary language wander (eave/frieze/soffit on back wall) parked as 1b sub-item — verify whether an explicit-boundaries fix resolves it, don't assume.

### Photo protocol (guidance only, shipped)
`AIMeasureButton.jsx` onboarding tip flipped: "Prefer a corner-angle shot of each wall over square-on" (corner-anchored counts repeatedly tape-exact; distant square-on reads drift). "Short or cluttered walls" tip no longer says "straight-on". Photo picker tip now reads "corner-angle shot of each wall (preferred)". No extraction contract change.

### Accuracy Report PDF (shipped, honest framing pinned)
`GET /api/estimates/{id}/tape-check/report-pdf` (WeasyPrint) + "Accuracy PDF" button in TapeCheckPanel (renders only with ≥1 scored run).
- Section 1: **Development validation — tuned fixture (methodology exhibit)** — banner: "demonstrate methodology and progress, NOT field accuracy". Tape table (segments + courses + start_ref), accuracy curve (Letrick: 82.8% → 92.3% → 94.1%), full history with per-wall Δ + "unread" for imputed walls.
- Section 2: **Held-out blind runs — accuracy claim** — renders empty with the criteria: "populated only by fresh houses scored with zero prompt changes between capture and scoring". `tape_check.held_out` flag routes a fixture's history to this section when a blind run exists.
- NO blended aggregate anywhere; header banner states the sections are never combined.
- Tests: `test_accuracy_report_iter79.py` (3 — 400 w/o runs, real PDF bytes, framing strings pinned at source). Verified rendered PDF text: curve, segments, unread, criteria all present. **Suite: 694 passed.**

### Next
Awaiting Howard's boundary-explicit front/left recounts (start course / stop course / per-segment anchors) → fresh 1b pre-registration → fix run on both fixtures, code frozen. Candidate 3 (appendage detection, acceptance = corner LOCATIONS not pieces) queued behind 1b.

## Iter 79j.80 — Blind-run provability: prompt hash locked at CAPTURE (2026-07-10) ✅
Howard approved the toggle with the constraint: hash locks at capture time, not score time.
- `_prompt_version_hash()` = sha256(PER_PHOTO_EXTRACT_PROMPT + RECONCILE_PROMPT)[:16]; stamped as `prompt_hash` on every ai_measure run doc at insert (primary launch + rerun).
- Scoring records `prompt_hash` (capture) + `prompt_unchanged` (capture hash == contract hash at scoring; None for legacy runs without a hash). Only `prompt_unchanged: true` supports a blind-accuracy claim.
- Panel: "Held-out blind fixture" checkbox (persists via `tape_check.held_out`, routes the fixture's history to the report's accuracy-claim section); history rows show a green lock (unchanged) / amber warning (changed) per entry.
- Report PDF: "Prompt hash" column on both tables (locked / changed / — legacy); blind section states only "locked" rows support the claim.
- Tests: `test_blind_run_hash_iter80.py` (5 — algorithm pinned, held_out roundtrip, unchanged/changed/legacy-null scoring). Suite 699 passed (same standalone-passing timing flake).
- NOTE: a file-write race dropped two staged edits this session (Rule 5 text, Lock import) after the tool reported success — both caught by tests/screenshot and reapplied. Verify greps after multi-edit batches.

## Iter 79j.81 — GROUND-TRUTH SUPERSEDE: Letrick tape corrected by enumeration (2026-07-10) ✅
Howard recounted with boundary-explicit enumeration. Pre-supersede entries backed up (standing rule) at `/app/memory/backups/tape_check_letrick_pre-supersede_2026-07-10.json`.
- **Corrected truth (all start_ref=siding_start, top of brown block line; no occlusion — start_line_occluded must NOT fire on these photos)**:
  - FRONT: 25 enumerable courses + cut top sliver (~1¼″ reveal, 26th physical strip) = **8.96′**. AI-count criteria: 25 = pass; 26 = pass only with a partial-top flag; 27+ = fail.
  - BACK: 28 courses even = **9.92′**, full height, no cut.
  - LEFT & RIGHT: corners forced by the eave walls — 25(+cut)=8.96′ at both FRONT corners, 28=9.92′ at both BACK corners. **The step is the ROOFLINE rising toward the back (~3 courses / ~12¾″); ground and bottom course are LEVEL.** Previous stepped entry (26→23 falling to back) was WRONG in direction and values.
- **Superseded-convention note (OPEN, unresolved — do not repair retroactively)**: old side-wall entries (23/26) and the AI's corner reads (8.1′/9.2′) share a uniform **−2** vs corrected enumeration. Cause unknown. Photo 6 RETAINS mechanism-(a) control status; photo 6's and run 3's "delta 0" corner-accuracy claims are **RETRACTED**.
- **Re-scores against corrected truth** (all 3 run docs annotated with `tape_supersede_note`): RUN1 82.8→**87.3%** (right 10.3 now +0.38 pass vs 9.92 bound) · RUN2 92.3→**95.3%** (back still unread; right 9.2 inside range) · RUN3 94.1→**91.8%** (front 10.3 +1.34 FAIL, right 8.1 now −0.86 amber). Sparkline now 87.3→95.3→91.8. Note: aggregate moved UP on runs 1-2, not down — the corrected side-wall ranges are wider/higher and forgive high reads; the honest signal lives in the per-wall front/back rows, not the aggregate. Front remains the 1b anchor: 30/27/29 counted vs 25 enumerable.

## Iter 79j.82 — CANDIDATE 1b: count-first with enumeration evidence (2026-07-10)

### PRE-REGISTRATION (Howard-approved with 3 edits folded — verdicts render against THIS TEXT ONLY)
*Fix requirements:*
1. Count-first with enumeration evidence: a course count is only reportable when the reasoning demonstrates enumeration (anchor edge named, start and stop course identified). Estimated/derived counts are not counts.
2. Height is derived second: `eave_height_ft_observed` = count × exposure (+ any partial top course, explicitly flagged). Never the other way around. **[Edit 3 corollary]** The reconciler must not cite derived height as evidence for a count — height = count × exposure is arithmetic, not corroboration. Only enumeration evidence or independent cross-photo enumerated counts corroborate. This closes the door on Phase B rebuilding the circularity one layer up.
3. Count/height disagreement is FLAGGED, not harmonized: if a pixel-scale read disputes the enumerated count, report both and flag the conflict — the pixel read may dispute but never author a count.
4. Explicit boundaries: top = the course meeting the frieze/soffit line; bottom = the first course on the starter, at the top of the block line.
5. Partial top course: if the top strip is cut (sub-exposure reveal), report the enumerable count + `partial_top_course: true` and add the measured reveal to height.
*Fix deliverable:* per-wall signed course-delta row (AI count − tape count) in the Tape Check panel as a first-class metric, alongside the existing aggregate.

*Pass criteria — Letrick (rerun from cached photos, one run in flight, code frozen during run):*
- FRONT: count 25 = pass · 26 = pass ONLY with partial-top flag · 27+ = fail. Height ~8.96′.
- BACK: 28 courses / 9.92′. **[Edit 1]** An empty extraction VOIDS the run — rerun under the one-run-at-a-time rule; the candidate is scored only on runs where all 8 photos returned valid extractions. Candidate FAIL is reserved for valid reads that miss criteria. Two voided runs in a row reopens the empty-extraction stability fix as a blocking item before 1b continues.
- CORNER-ANCHORED READS: land 25/28 (±0 courses), NOT 23/26. The −2 convention gap must close under enumeration-evidence counting or be surfaced as a flagged conflict — silent persistence of −2 is a fail.
- `start_line_occluded` fires on ZERO Letrick photos.
*Pass criteria — Red house:* aggregate holds 91–93 · woodpile photo count unchanged · no course-count regressions on scored walls · occlusion flags keep firing where they fired before.
**[Edit 2] Verdict metric is per-wall, not aggregate**: the 1b pass/fail verdict is rendered on the per-wall count criteria ALONE; the aggregate percentage is recorded but has no vote. (The supersede re-score proved the aggregate can rise while the front wall stays 4–5 courses wrong.)
*Protocol:* partial movement on front (e.g. 29→27) = FAIL, report-don't-ship. Both fixtures scored, before/after per-wall deltas in the run docs. Fix runs are development runs (prompt hash differs from prior captures — not blind runs).

### Implementation (SHIPPED, pin-tested, suite 705 green)
- **Phase A** (`PER_PHOTO_EXTRACT_PROMPT` rule 5 + exposure injection): COUNT FIRST HEIGHT SECOND; new fields `count_enumeration_evidence` (required for any non-null count), `partial_top_course`, `count_disputed_by_pixel`; explicit starter/block-line bottom + frieze/soffit top boundaries; "pixel may DISPUTE, never AUTHOR"; cannot-enumerate → null (no back-derivation).
- **Phase B** (`RECONCILE_PROMPT`): count-derived requires enumeration evidence; "arithmetic, not corroboration" clause; per-wall `eave_courses_counted` carried into the reconciled walls schema.
- **Scoring** (`estimates.py`): per-wall `ai_courses` / `tape_courses` (nearest-height segment) / signed `course_delta` on every history entry. **Panel**: Δc chip per wall (green 0 / amber ±1 / red ≥2).
- Tests: `test_count_first_iter81.py` (6) + iter67/iter77 pins updated to the superseding contract.

### 1b FIX-RUN RESULTS (2026-07-10) — VERDICT: FAIL vs pre-registration (per-wall, aggregate has no vote)
**Run ledger (one at a time, code frozen during runs):**
- Letrick attempt 1 (6c411870): **VOID** — photo 7 empty. NEW diagnostics caught the real bug: Claude returned 3,520 chars of valid-looking JSON (stop_reason end_turn, correct elevation) that our STRICT parser rejected → judged "empty". False positive in our own code.
- Letrick attempt 2 (799ff0f2): **VOID #2** — photo 5, same class (3,660 chars, end_turn). Two voids in a row → Edit 1 tripped, **stability fix reopened as BLOCKING and shipped**: `_clean_json_reply` rewritten as a lenient parse ladder (raw_decode tolerates trailing prose → trailing-comma repair → unescaped inch-quote repair), repaired parses stamped `_json_repaired`, unparseable replies stamped `_parse_error` (never silent). Pin tests: `test_json_repair_iter82.py` (7). Suite 712 green.
- Letrick attempt 3 (4e376d2d): **VALID 8/8** — enumeration evidence on every photo (anchor edge + start/stop course named), zero occlusion flags, zero repairs needed. SCORED (95.3% aggregate, recorded, no vote).
- Red house (fd4d01f9): **VOID** — photo 3 (the woodpile photo) hit the 240s per-photo timeout. THIRD distinct empty class: (1) parse false-positive [FIXED], (2) wave-cap concurrency [operational rule], (3) per-photo LLM timeout [open]. NOT scored.

**Letrick per-wall verdict (valid run 4e376d2d vs pre-registered criteria):**
| Criterion | Result | Verdict |
|---|---|---|
| FRONT 25c (26 w/ partial-top) | 27c / 9.56′, no partial-top flag | **FAIL** (partial movement again: photo p0 count history 30→27→29→27) |
| BACK 28c / 9.92′ | 30c / 10.6′ | **FAIL** (+2) |
| Corners land 25/28, no silent −2 | MIXED: p2=28✓ p3=25✓ p7=25✓, but p1=24, p5=24 (rear-right corner, should be 28), p6=23 — silent, no flagged conflict | **FAIL** (silent −2/−5 persistence) |
| start_line_occluded fires on 0 photos | 0 fired | **PASS** |
Notable: LEFT reconciled 28c/9.92′ = Δc 0 dead-on; RIGHT 24c/8.5′ = Δc −1. The Δc panel chips + per-wall course rows worked as specified.

**Red house independent observation (from the void run's 7 valid photos, unscored):** ALL counts came back null — the strict enumeration-evidence bar caused Claude to DECLINE to count on the harder two-story fixture rather than count carefully; heights went pixel-only (p1 read 14.5′ with occl=true). Over-suppression risk: the bar that fixed circularity on Letrick may have priced counting out of reach on red-house-class photos. This alone would likely fail "no course-count regressions" if the run had been valid.

**Status: candidate 1b prompt is in the code (shipped with pin tests) but FAILS its pre-registration. Awaiting Howard's ruling: keep / revert / amend. Front count inflation is now isolated to specific photos (p0 front, p4 back full-wall reads) while corner-anchored enumeration hits 25/28 on half the corners.**

## Iter 79j.83 — 1b REVERTED (Howard's ruling) + timeout salvage + run-integrity + evidence audit (2026-07-10) ✅

### Reversion (hash-confirmed)
1b prompt changes reverted to the 1a-validated contract by splicing the exact constants from commit `023cbf9`. **Runtime prompt hash `f23780909828f9a8` — AST-verified equal to the 1a-era contract hash.** KEPT (separately validated infrastructure): parser repair ladder + `_parse_error`/`_json_repaired` diagnostics, `_stamp_empty_diagnostics`, prompt-hash stamping, per-wall course-delta scoring + Δc panel chips, run ledger, all findings. Tests: iter77 restored to 1a pins; iter81 rewritten as reversion pins (hash == `f23780909828f9a8`, 1b markers absent) + the kept course-delta scoring test.

### Empty class 3 fix — timeout SALVAGE PASS (blocking item, shipped)
Photos killed by the per-photo budget (240s) or the wave cap now get ONE sequential retry with a fresh budget (`AI_MEASURE_TIMEOUT_RETRY_BUDGET`, default 120s) AFTER all waves complete — outside the wave scheduler so the cap can't kill the retry mid-flight. Provenance: `_timeout_retry_attempted` on both outcomes. Pin tests: `test_salvage_retry_iter82.py` (recovery path) + `test_phase_a_resilience.py` updated (retry-then-fail path). All three empty classes now handled: (1) parse false-positive → repair ladder, (2) wave-cap concurrency → one-run rule + salvage, (3) LLM timeout → salvage retry.

### Run-integrity line in accuracy report PDF (approved, shipped)
"Run integrity: N valid run(s) · M voided run(s) (≥1 empty/failed photo — excluded from candidate verdicts) · K legacy". Verified live on Letrick: 2 valid / 4 voided — exact. Pinned in `test_accuracy_report_iter79.py`.

### EVIDENCE AUDIT — 1b valid run 4e376d2d (deliverable, pre-1c)
Every one of the 8 counts presented FORMALLY COMPLETE enumeration evidence (anchor edge named, start course on starter at block line, stop course at frieze/soffit). The failing counts did NOT leak scale-consistency language past the gate — they wore perfect evidence dress. **Per Howard's pre-declared branch: evidence fabrication is the disease → 1c needs verification mechanics, not stronger instructions.**
The killer cross-check — each physical corner was counted from TWO photos in the SAME run:
| Physical corner | Photo A | Photo B | Disagreement | Howard truth |
|---|---|---|---|---|
| Front-left | p0: 27c | p1: 24c | **3 courses** | 25 |
| Rear-left | p2: 28c ✓ | p3: 25c | **3 courses** | 28 |
| Rear-right | p4: 30c | p5: 24c | **6 courses** | 28 |
| Front-right | p6: 23c | p7: 25c ✓ | **2 courses** | 25 |
Same anchor, same run, 2–6-course disagreements → these are not deterministic enumerations; the model learned the evidence FORMAT, not the act. Also note: every full-wall count's reasoning still ends "pixel cross-check agrees" (p0: 27c=114.75″ vs pixel 117″). 1c direction (Howard's, from ruling): **two-tier reporting** (enumerated w/ evidence = scoreable; `estimated: true` = amber, takeoff-usable, excluded from accuracy claims) + **cross-photo same-corner count verification** as the mechanic that catches fabricated enumerations.

## Iter 79j.84 — CANDIDATE 1c (2026-07 / restored post-fork)

### PRE-REGISTRATION (Howard-APPROVED with 2 edits folded — verdicts render against THIS TEXT ONLY)
The 1b evidence audit already ruled: evidence fabrication is the disease → 1c is a VERIFICATION MECHANIC, not stronger instructions. No audit redo, no rule re-litigation.

**Rules (mechanical gate, deterministic Python after Phase B — no LLM can fabricate past it):**
1. **Two-tier counts**: `enumerated` (corner-verified, scoreable) vs `estimated: true` (amber chips, takeoff-usable, EXCLUDED from accuracy claims and Δc).
2. **Structured `count_anchor_corner`** (Phase A): every count names the physical corner it ran along. Same-corner cross-check between photos sharing that corner GATES the enumerated tier.
3. **Deterministic consensus**: exact match → value. Differ by exactly 1 → the LOWER count + `possible_partial_top: true`. NEVER average, NEVER take the higher count.
4. **>1 disagreement** → BOTH counts demote to estimated + `corner_count_conflict` — never silently pick one.
5. **Pixel-citation demotion**: a count whose reasoning cites pixel agreement as SUPPORT demotes to the estimated tier (the flagged-dispute path `count_disputed_by_pixel` does NOT demote — pixel reads never author and never corroborate a count).
6. **Single-photo corners can never reach the enumerated tier** (intentional).
7. **Correlated-error residual logged openly in the run doc** (`_count_corner_audit.residual_note`): same-corner agreement cannot catch two photos fabricating the SAME wrong count.

**Pass criteria (per-wall verdict; aggregate recorded, NO VOTE):**
- Letrick: front **25** (26 acceptable w/ partial-top) / back **28** / 9.92′ — on the ENUMERATED tier only. Same-corner pairs agree ±1 or are flagged (a silent >1 disagreement ANYWHERE = FAIL). Enumerated corners land **25/28**. Zero occlusion flags. valid-8/8 required (void rule carries).
- Red house: aggregate 91–93. Counts REAPPEAR as the estimated tier (1b's total suppression must not recur). Zero enumerated counts without corner agreement. Occlusion flags unchanged.

**Sequencing (Howard directive):** code frozen, one run in flight. Letrick fix run first → score → report → THEN red house fires.

### IMPLEMENTATION (shipped)
- Phase A prompt: 1c anchor + pixel rules (`count_anchor_corner`, `count_disputed_by_pixel`, "never authors and never corroborates"). Contract hash moved `f23780909828f9a8` → **`07318d7b10de9fb4`** (pinned in iter81 tests, rewritten as 1c pins).
- `_apply_count_tiering()` in `ai_measure.py` — deterministic post-Phase-B gate applying rules 1–7; called from `_run_two_phase` and the reconcile-only retry worker. Stamps `count_tier`, `possible_partial_top`, `corner_count_conflict`, `count_segments` (stepped walls with two legitimately-different enumerated corners), and `_count_corner_audit` (persisted on the run doc via result.raw_ai).
- Scoring (`estimates.py` tape-check score): estimated-tier counts surface (`ai_courses`, `count_tier`) but emit NO `course_delta` — excluded from Δc and accuracy claims.
- TapeCheckPanel: amber `est Nc` chip (estimated tier), `+1?` chip (possible_partial_top).
- Pin tests: `test_count_tiering_iter84.py` (corner consensus, pixel gate, wall stamping, stepped-wall non-conflict, Δc exclusion e2e).

### 1c FIX-RUN — LETRICK (2026-07-10, run `73cca7fa9d4c4a91b333c11945948da9`, hash-locked `07318d7b10de9fb4`, valid 8/8, zero occlusion flags)
Per-photo counts (truth: front corners 25 / rear corners 28):
| Corner | Photos | Counts | Gate result |
|---|---|---|---|
| front_left | p0 (front) / p1 (front-left) | 28 / 24 | Δ4 → CONFLICT, both demoted, flagged |
| rear_left | p2 (left, disputed_by_pixel) / p3 (rear-left) / p4 (back, disputed_by_pixel) | 27 / 23 / 26 | spread 4 → CONFLICT, demoted, flagged |
| rear_right | p5 (rear-right) / p6 (right) | 24 / 30 | p6 cited pixel agreement as support → live demotion; 1 clean left → estimated |
| front_right | p7 (front-right) | 25 (= truth) | single photo → estimated (by design) |
Walls: all 4 counts landed ESTIMATED tier, amber, excluded from Δc/claims. Heights: 1 pass / 3 amber / 0 fail, aggregate 93.8 (recorded, NO VOTE). `prompt_unchanged: true`.

**VERDICT vs pre-registration: FAIL on the enumerated-tier count criteria** (zero counts reached the enumerated tier; front 25 / back 28 never landed corner-agreed). **PASS on the honesty criteria**: no silent >1 disagreement anywhere — every conflict flagged, pixel-citation caught live (p6), zero occlusion flags, valid 8/8. The gate did exactly what the 1b evidence audit predicted it must: the model's "enumerations" are not deterministic (p0 read 27 in the 1b run, 28 now — same photo), and the mechanic now quarantines them as estimated instead of letting them masquerade as tape-provable.

### HOWARD'S 1c RULING (2026-07-10) — COUNTING LOOP CLOSED. No candidate 1d, ever.
Capability verdict rendered per the pre-declared resolution criterion. Verdict is split and both halves are final: **FAIL on enumerated-count criteria** (counting is non-deterministic — capability limit, not prompt defect) · **PASS on all honesty criteria** (gate performed exactly as designed). Consequence: **KEEP the 1c tiering architecture permanently — nothing reverts.** Distinction for the record: 1b's prompt caused bad behavior → reverted; 1c's mechanics revealed inherent behavior → retained.

**PRD update (verbatim per ruling):** Course counts are estimates by default, tier-labeled always. Enumerated tier is earned only by independent same-corner agreement and will be rare. Accuracy claims ride on tape-scored heights/areas, never raw counts. Blueprint Measure carries precision where prints exist; estimating conventions (whole-piece rounding, 10% waste) absorb estimated-tier uncertainty on remodel jobs — the primary market. Prompt-tuning of counts is permanently off the table; future count-accuracy gains come only from capture protocol or model-generation upgrades, tested as controlled runs.

**Approved queue, in order:** (1) Red house 1c run — cached photos, one run in flight, code frozen, scored against its pre-registered criteria only: counts REAPPEAR as estimated tier (vs 1b's null-out), zero enumerated without corner agreement, occlusion flags unchanged (woodpile/shrub), aggregate holds 91–93; report before anything else moves. (2) Frontend pass on chip rendering (amber est / possible_partial_top / conflict — core product UI now). (3) Corner cross-check table in the Accuracy Report PDF methodology section. Then the queue unfreezes: right-gable overread (P1) → candidate 3 appendage detection (P1, corner-locations acceptance; photo-3/photo-4 autopsy questions still owed) → LP-native package assembly for September.

### 1c RED HOUSE RUN (2026-07-10, run `e0e704f64b1546e3891d18fef7cffff6`, rerun of fd4d01f9, hash-locked `07318d7b10de9fb4`, valid 8/8)
Per-photo: p0 front 32c@front_left (PIXEL-CITED → demoted live, 2nd live catch) · p1 front-left 29c@rear_left · p2 left null (occl) · p3 rear-left 34c@rear_left · p4 back 29c@rear_right · p5 rear-right null · p6 front-right null (occl) · p7 front 28c@other (no anchor).
Corner gate: rear_left 29/34 → CONFLICT flagged, both demoted · front_left single(+pixel-cited) → estimated · rear_right single → estimated. Zero enumerated. All 4 walls estimated tier.
Scored: aggregate **94.1** (1 pass / 0 amber / 1 fail; left wall AI 9.1 vs tape 10.31 = fail −1.21; right wall honestly imputed → unread/excluded; left dormer 15.0 vs 15.0 exact). `prompt_unchanged: true`.
**Verdict vs pre-registered red-house criteria:** counts REAPPEAR as estimated tier (same 5 photos as the 1a baseline 56589e26, vs 1b's 0/8 null-out) → **PASS** · zero enumerated without corner agreement → **PASS** · occlusion flags: **PARTIAL** — flags persist (1a: p3,p7 → 1c: p2,p6,p7; p7 stable) but placement moved, consistent with the capability verdict · aggregate 94.1 — **above** the 91–93 band (recorded, no vote; fewer scoreable walls this run: right imputed).

### Ruling queue items 2 & 3 — SHIPPED (2026-07-10)
- (2) Chip rendering visually verified in the 3D tab TapeCheckPanel (Letrick): all 4 walls render amber `est Nc` chips beside verdict chips; conflict detail in tooltip; `+1?` partial-top chip pinned by unit test (no instance in current data).
- (3) Accuracy Report PDF now renders the persisted `_count_corner_audit` as a "Same-corner count cross-check — 1c mechanical gate (methodology)" table (up to 3 most recent audited runs: per-photo counts, pixel-cited markers, gate results, no-anchor rows) + the correlated-error residual note + the ruling's framing language verbatim. Pinned in `test_count_tiering_iter84.py::test_accuracy_pdf_carries_corner_cross_check_table`.

**Queue now unfrozen. NEXT: right-gable overread (P1) → candidate 3 appendage detection (P1, corner-locations acceptance; photo-3/photo-4 autopsy questions owed) → LP-native package assembly for September.**

## Iter 79j.85 — Red-house acceptance rider + left-wall trace + capture guidance + right-gable evidence (2026-07-10)

### Occlusion stochasticity — LOGGED PROPERTY (Howard-accepted, on run doc e0e704f6 + here)
Occlusion detection is honest but placement-stochastic — mechanism intact, photo-level stability not guaranteed (1a run 56589e26 flagged p3,p7 → 1c run e0e704f6 flagged p2,p6,p7; only p7 stable). Constrains future capture guidance: "reshoot flagged photos" cannot assume flags are stable.

### LEFT-WALL TRACE (red house) — READ DRIFTED, ground truth never moved. No supersede event.
- Tape entry: **10.3125 in all 6 score entries**, unchanged; `tape_check.updated_at` 2026-07-09 00:12 — before both later runs; still stored as a legacy single float (never migrated/re-segmented under the stepped schema).
- AI left-wall read across runs: 9.0 → 9.7 → 9.7 → 9.4 → 9.4 → **9.1** (source flipped direct_consensus → direct_disagreement in the 1c run). Read drift = another non-determinism data point, logged not fixed.
- Premise correction: 9.4 was never a pass — it scored AMBER (Δ−0.91). Left has never passed on this fixture (best Δ−0.61).
- Why the aggregate rose while left flipped to fail: **composition, not accuracy** — the right wall (historic worst: Δ+0.91…+3.21, fail in 3 of 5 prior runs) dropped out as honestly-imputed this run, leaving left(fail) + left dormer(exact pass).

### Capture guidance shipped (guidance layer only, per approval)
GuidedCaptureWizard: all 4 corner steps now instruct framing the corner trim + BOTH walls' bottom courses ("this corner's course count is cross-checked against the adjacent wall shots") + a standing amber note on every step: same-corner pairs are the sole path to the enumerated (tape-provable) tier. AI Measure onboarding checklist corner tip rewritten with the same standing note; the now-falsified "corner counts are repeatedly tape-exact" claim removed.

### RIGHT-GABLE OVERREAD (P1) — EVIDENCE DELIVERABLE (no fix, per candidate protocol)
Target: ~8.75′ rise (7/12 × 15′ half-span on the 30′/360″ gable ends; blueprint's 8.5′ was drawing-scaled, NOT the target). Left and right gable ends are geometrically identical — same span, same ridge.
**Asymmetry is PERSISTENT, not stochastic**: final right gable across all 7 Letrick runs = 12.6 / 10.3 / 12.6 / 9.75 / 10.0 / 10.2 / 9.5 (always over); left = 8.5 / 9.3 / 8.8 / 9.3 / 9.0 / 7.9 / 8.8 (straddles target). Right > left in every run.
Per-photo (3 valid runs): right reads p5 (rear-right oblique) 12.5 / 12.5 / 10, p6 (square-on) 12.6 / 10.3 / 9.5, p7 (front-right oblique) 7.5 / 10.0 / 7.5. Left reads 7.0–10.0.
**Mechanism classification — four stacked causes, dominant two are structural:**
1. **Pitch-ladder quantization (STRUCTURAL, code-confirmed)**: Phase A schema hard-limits `pitch_ratio_observed` to `4/12|6/12|8/12|10/12|12/12` — the true 7/12 is INEXPRESSIBLE. Rise reads are literally pitch×15′: 7.5′ (6/12), 10.0′ (8/12), 12.5′ (10/12) recur verbatim. Smoking gun: run 97d99abb p2 measured "~7.1/12" (≈ truth) then rounded UP: "nearest allowed ratio is 8/12" → 8.8′ becomes 10′ downstream. Best-case error on this house is ±1.25′ by construction. Affects BOTH gables.
2. **Oblique foreshortening inflation (PERSISTENT, right side)**: the rear-right corner photo p5 always reads highest (11.7/12 raw in 4e376d2d — its own reasoning ADMITS "horizontal foreshortening inflates the vertical conversion" and still lands 10/12 → 12.5′).
3. **Apex/eave pixel placement instability (STOCHASTIC)**: the same square-on right photo p6 read rise 437 px (97d99abb) then 330 px (73cca7fa) — a 32% swing on the identical triangle → 10/12 vs 8/12. Same non-determinism disease as counting.
4. **No same-plane vertical anchor on the right (ASYMMETRY DRIVER)**: the right gable wall is windowless (noted in every run) — no WIN_REF on that plane; vertical conversion rides pixel ratios alone. The left wall carries a Pella window WIN_REF and its reads cluster tighter.
Answer to the framing question: not a single mechanism — scale error (4) + apex mislocation (3) feed a ratio that foreshortening (2) inflates and the even-only ladder (1) quantizes upward. The 1c-era run landed 9.5′ only because p6 happened to read low that run; the floor set by (1) means the pipeline cannot express 8.75′ at all.
**Status: mechanism shown. Any fix (e.g., odd pitches in the ladder, oblique down-weighting for gable rise, square-on-only gable reads) requires pre-registration before a fix run. Awaiting Howard's ruling.**

## Iter 79j.86 — MODEL BAKE-OFF PRE-REGISTRATION (Howard-drafted 2026-07-10, sequenced after left-wall trace, BEFORE right-gable work. Verdicts render against THIS TEXT ONLY. NO RUN FIRES WITHOUT HOWARD'S GO.)

### Candidates (Phase A vision extraction is the cost center)
- **A0** — claude-fable-5 both phases (incumbent). Scores = the two hash-locked 1c runs `73cca7fa` (Letrick) + `e0e704f6` (red house). DO NOT RE-RUN.
- **A1** — claude-sonnet-4-6 Phase A + claude-fable-5 Phase B (split-tier)
- **A2** — claude-sonnet-4-6 both phases
- **A3** — claude-haiku-4-5-20251001 Phase A + claude-sonnet-4-6 Phase B (cheap-tier probe)
- GPT-class EXCLUDED this round (parser ladder/empty-class handling don't transfer; engineering cost > information value). Revisit only if no Anthropic config wins.
- Model IDs verified live against the Anthropic /v1/models endpoint 2026-07-10.

### Protocol
Both fixtures per candidate, cached photos, code frozen, one run in flight. Run doc records prompt hash + per-phase model IDs (`model_config: {phase_a, phase_b}`) — prompt hash alone no longer uniquely identifies a condition. Void rule carries: valid 8/8 or rerun; two consecutive voids = candidate reports UNSTABLE (itself a result). Per-wall scoring vs existing ground truth; aggregate recorded, no vote. NEW REQUIRED COLUMNS: cost/run (actual input+output tokens × current rates, per phase), wall-clock time, retry/void counts. No prompt changes for any candidate — same contract, same hash. Format-compliance failure (JSON breaks the repair ladder) reports as INCOMPATIBLE, never tuned for.

### Pre-registered win criteria (challenger defeats incumbent only if ALL hold)
1. Red house aggregate within 91–94 AND no scored wall flips pass→fail vs incumbent per-wall results
2. Letrick per-wall heights: no wall's Δ worsens by >0.3′ vs incumbent
3. Honesty parity, zero tolerance: conflicts flagged (no silent same-corner >1), zero unearned enumerated counts, pixel-citation demotion fires where citations occur, occlusion flags fire (placement stochasticity tolerated per logged property; absence = fail), imputed walls excluded
4. Cost ≥40% below incumbent per-run
5. Stability: no more empty-extraction voids than incumbent across the pair
Tie-breaks: all-pass → cheapest wins. Honesty+cost pass with in-tolerance accuracy degradation → VIABLE-DEGRADED with specific walls, Howard's ruling not auto-win. None pass → incumbent stays, cost table is the deliverable.
Deliverable: one table — candidate × (per-wall deltas both fixtures, honesty checklist, cost/run, time, voids) + verbatim reasoning excerpts for any honesty-criterion event. Nothing switches without Howard's ruling.

### COST BASELINE — A0 incumbent (estimate-derived; actual usage was NOT persisted at run time and A0 is do-not-rerun)
Method: image tokens = w×h/750 from persisted compressed dims (1600×1200 ≈ 2,560 tok/photo; totals 20,480 / 17,875 across the two runs); prompt sizes measured (Phase A 10,126 chars ≈ 2.5K tok; Phase B 21,059 chars ≈ 5.3K tok); output estimated from persisted reply JSON chars/4 (UNDERSTATES if thinking tokens billed — flagged).
- Phase A / run: input ≈ 41.6K tok, output ≈ 7.7K tok → fable-5 ($10/$50 per M) ≈ **$0.80**
- Phase B / run: input ≈ 12.3K tok, output ≈ 10.5K tok → fable-5 ≈ **$0.65**
- **A0 ≈ $1.45/run** (range $1.35–1.60) · wall-clock 9.8 / 11.0 min · voids 0 / 0 · retries 0 / 0
Challenger projections (same token profile; rates: sonnet-4-6 $3/$15, haiku-4-5 $1/$5, web+code-table confirmed):
- A1 ≈ $0.89/run → **~39% below — MARGINAL vs the ≥40% gate** (fable-5 Phase B output dominates residual cost)
- A2 ≈ $0.44/run → ~70% below ✓ (projection)
- A3 ≈ $0.28/run → ~81% below ✓ (projection)
Bake-off runs will record ACTUAL per-phase usage; the cost column uses actuals for challengers, estimate for A0 (marked).

### Infra required BEFORE runs (pin-tested, zero prompt changes — pending Howard's go)
1. Per-phase model plumbing (`model_config.phase_a/phase_b`, defaults = incumbent single-model behavior)
2. Run-doc condition record: per-phase model IDs stamped at capture alongside prompt hash
3. Actual token telemetry: persist input/output(+thinking) tokens per phase on the run doc; cost computed from the rates table (add haiku-4-5)
4. Surface wall-clock + retry/void counts as columns (latency stamps + `_timeout_retry_attempted` already persisted)

**STATUS: pre-registration drafted + cost baseline filled. WAITING FOR HOWARD'S GO. Sequence: this bake-off (4–6 runs) → Howard's ruling → right-gable evidence work under the winning model.**

### GO received (2026-07-10): A1 stays (actuals decide); A0 usage-only probe approved (scores discarded, `usage_probe: true`).

### INFRA SHIPPED (pin-tested, prompt hash unchanged `07318d7b10de9fb4`)
Per-phase model plumbing (`model_phase_a`/`model_phase_b` rerun payload keys → `model_config` stamped at capture); ACTUAL token telemetry persisted per phase (`token_usage`, direct transport); `_price_for_model_id` + `_cost_from_usage` (haiku-4-5 added to registry+pricing); `usage_probe` runs refused by scoring (400), excluded from accuracy history, latest-for-estimate, and PDF run-integrity counts. Pins: `test_bakeoff_infra_iter86.py` (24 tests green incl. hash pin).

### BAKE-OFF RESULTS (2026-07-10, 7 runs, all valid 8/8, zero voids, zero retries, one in flight throughout)
| Candidate | Letrick per-wall Δ (F/B/L/R) | agg | Red per-wall Δ | agg | Honesty | ACTUAL cost/run | Clock |
|---|---|---|---|---|---|---|---|
| **A0** fable-5 both (banked 1c runs; probe `1ec3f42a` for cost) | +0.94a / −0.72a / 0.00p / +0.68a | 93.8 | L −1.21f / R imputed / dormer 0.00p | 94.1 | all mechanics ✓ | **$3.61** (probe actual: A 62.9K in/32.8K out; B 21.6K/22.5K) | 8.4–11.0 min |
| A1 sonnet-4-6 A + fable-5 B (`03f2ad42`,`3fc2bc2c`) | −0.46p / **−1.42f (worse +0.70✗)** / −0.46p (**+0.46✗**) / −0.46p | 92.6 | L −1.56f / **R +2.19f (new fail✗)** / dormer −1.0a | **82.6✗** | mechanics ✓, CAUTION: false same-corner pairs (below) | $1.06 / $1.02 (−71%✓) | 4.2 min |
| A2 sonnet-4-6 both (`8bb3f597`,`aba1fd00`) | −0.45p / **−1.69f✗** / −0.45p✗ / −0.45p | 92.0 | **L +3.79f✗ / R +2.50f✗** / dormer −1.0a | **73.9✗** | mechanics ✓, same CAUTION | $0.49 / $0.51 (−86%✓) | 4.0 min |
| A3 haiku-4-5 A + sonnet-4-6 B (`b97852d5`,`6117d209`) | −0.69a / **−1.42f✗** / +0.35p✗ / +0.50p | 92.4 | L −1.25f / R imputed / **dormer −9.8f (pass→fail✗)** | **61.3✗** | mechanics ✓ incl. live pixel-citation demotion | $0.34 / $0.41 (−91%✓) | 2.3–2.6 min |

**VERDICT (per pre-registered criteria): NO CHALLENGER PASSES — incumbent claude-fable-5 stays; bake-off CLOSES with this table as deliverable.** Every challenger clears cost (gate ≤$2.17) and stability, and every honesty MECHANIC held (conflicts flagged, zero mechanically-unearned enumerated, pixel-citation demotion fired live on Haiku, occlusion flags fired, imputed excluded) — but ALL fail accuracy criteria 1+2: red-house aggregates 82.6/73.9/61.3 vs band 91–94; Letrick back Δ worsens ≥0.70 on all three.

**Honesty-criterion events (verbatim excerpts on file above; full text in run docs):**
- A3-L p5 (Haiku): "Pixel-scale cross-check … Count agrees closely with pixel measure; reported value is 8.48 ft (average of 97.75″ and 101.6″)" — cited pixel as support AND averaged → demoted by the gate (3rd live catch).
- A1-L p4/p5 (Sonnet): p5 (a rear-RIGHT photo) reasoned "Counted lap courses along the rear-left corner of the back wall…24 courses" — mislabeled anchor `rear_left` matched p4's genuine rear_left 24 → FALSE same-corner agreement → enumerated 24c on back vs truth 28 (Δc −4). Same pattern in A2-L (23c enumerated, Δc −5).

**NEW LOGGED RESIDUAL — anchor-integrity dependency:** the 1c same-corner gate assumes truthful `count_anchor_corner` labels. Cheaper models scramble anchors AND count to gable peaks on gable-end photos (48–61 "courses", eaves read 16–19′), converting the cross-check from a fabrication-catcher into a false-agreement generator. On fable-5, anchors stayed consistent across all 1c-era runs. Corollary: any future model swap must re-validate anchor integrity BEFORE trusting the enumerated tier.

**Cost-table corollary (deliverable):** incumbent actual is $3.61/run — 2.5× the pre-run estimate; the understatement was thinking tokens (fable-5 ~3.3K thinking/photo). Future per-run cost work has actuals infrastructure permanently in place.

### HOWARD'S BAKE-OFF RULING (2026-07-10) — CLOSED per pre-registration
No challenger passes (all fail accuracy criteria 1–2 despite clearing cost); incumbent fable-5 stays for both phases. Cost table banked: A0 actual $3.61/run, estimate-vs-actual gap attributed to thinking tokens, telemetry now permanent. A1's "actuals decide" retention: **vindicated on the cost gate** (actuals cleared ≥40% where the estimate said marginal) **and mooted by accuracy** — both halves logged.

**STANDING PRD RULE — anchor integrity (elevated from logged residual, verbatim per ruling):** The 1c tiering gate's enumerated tier depends on the integrity of count_anchor_corner labels, which is model-specific capability, not architecture. A1's false same-corner pair (mislabeled rear-right agreeing with genuine rear_left → unearned enumerated 24c vs truth 28) is the canonical failure. RULE: any model change in either phase requires an anchor-integrity validation on gable-end-bearing fixtures — labels verified against known geometry — BEFORE tiering-gate outputs are trusted, in addition to the standard controlled-run comparison.
**Portable/non-portable split:** honesty mechanics (pixel-citation demotion, conflict flags, imputed exclusion) generalized across all three challengers; anchor labeling did not.
The false-pair verbatim excerpt now ships in the Accuracy PDF's corner cross-check methodology section.

**BACKLOG — GPT-5.5:** excluded from the closed round per pre-registration (adapter cost: API/response format, parser repair ladder and empty-class handling are Claude-specific, behavioral map restarts from zero). Revisit trigger: (a) fable per-run cost becomes a business constraint at production volume, or (b) a forced or elective model swap opens a new bake-off round — GPT-5.5 rides as one candidate, adapter work estimated and approved separately first. Anchor-integrity validation rule applies.

**Approved & shipped:** cost/run line in the run-history (async jobs) debug view, computed from live token telemetry (`cost_usd` on `/ai-measure/debug-runs`, rendered per run row).

## Iter 79j.87 — CANDIDATE 2 PRE-REGISTRATION (Howard-drafted 2026-07-10; finalized; verdicts render against THIS TEXT ONLY)
**Change:** pitch ladder expands to all integer pitches 3/12–14/12 inclusive; measured pitch reported at integer resolution; NO other extraction changes bundled. Contract hash moves `07318d7b10de9fb4` → **`53f2bfa3344b1057`** (pinned).
**Pass criteria — Letrick:** right gable rise lands 8.75′ ±0.5′ on square-on photos; left gable holds or tightens 7.9–9.3; ladder artifacts (7.5/10.0/12.5 verbatim recurrences) disappear from the read series. **Red house:** no regressions on pitch-dependent reads (dormer, main roof); aggregate holds band; honesty criteria unchanged.
**Protocol:** both fixtures, cached photos, valid 8/8 or void, one run in flight, code frozen during runs, per-wall verdict aggregate-no-vote, before/after read series in run docs.
**Scope walls:** oblique admitted-inflation stays OUT (queued as a future demotion-rule candidate); apex stochasticity stays logged-not-fixed; windowless-gable capture note ships with guidance.

### CANDIDATE 2 RUN REPORT (2026-07-10/11, hash `53f2bfa3344b1057`, fable-5 both phases, before/after read series stamped on run docs)
**Runs:** Letrick attempt 1 `ae3722ca` VOID (p2,p5 empty) → attempt 2 `96238edd` valid 8/8 ($3.49, 9.5min). Red attempt 1 `7e9897e3` VOID (p6 empty) → attempt 2 `8fcc46ed` valid 8/8 ($4.16, 10.1min). Voids non-consecutive per candidate — no UNSTABLE verdict, but note: 1c-era runs had ZERO voids; C2 era had 2/4.
**Letrick (`96238edd`):**
- 7/12 EXPRESSED and used (p2,p3,p7); two EXACT 8.75′ gable reads (p3, p7)
- Right gable square-on (p6): 9.6′ @ 8/12 → **FAIL** the 8.75±0.5 gate by 0.35′ (apex placement, the logged stochastic mechanism — p6 read 437px→330px→now ~9.6′ across eras)
- Left gable: final 8.75′ → **PASS** (tightened from 7.9–9.3 band to exact)
- Ladder artifacts: reduced from wholesale to ONE verbatim recurrence — p5 rear-right oblique 12.5 @ 10/12 (the perennial inflator, out-of-scope mechanism) → strict criterion "disappear" **FAIL**
- Heights (recorded, no vote): aggregate **95.6 — best Letrick ever** (front +0.94a / back **−0.02p** / left +0.68a / right **0.00p**)
- Honesty: all 4 corners conflict-flagged (spreads 2–6), zero enumerated, pixel-citation demotion fired on p4 (4th live catch), zero occlusion flags ✓
**Red house (`8fcc46ed`):**
- Aggregate **87.4 — out of band** → **FAIL**; left −1.56f (incumbent −1.21f, stayed fail), right +0.91a (read directly this run vs incumbent imputed)
- **Dormer 16.5 vs tape 15.0 → FAIL (incumbent 0.00 PASS → pass→fail regression on a pitch-dependent read)** → criterion FAIL
- p3 rear-left oblique still inflated (14.1′ eave @ 10/12) — out-of-scope oblique mechanism
- Honesty unchanged ✓ (rear_left 28/45/29 conflict flagged, zero enumerated, occlusion flags fired ×5)
**VERDICT vs pre-registration: CANDIDATE 2 FAILS** (right-gable gate missed 0.35′; one artifact recurrence; red-house band miss + dormer regression). What it PROVED: the quantization floor is real and removable — 7/12 reads appeared immediately and landed exact-true twice; the residual misses concentrate in the two explicitly out-of-scope mechanisms (oblique inflation, apex stochasticity). **Awaiting Howard's ruling. Nothing else moves.**

### HOWARD'S C2 RULING (2026-07-11) — KEEP the expanded ladder: CORRECTNESS FIX retained despite pre-registered FAIL
**Rationale (verbatim):** reverting would reinstate a schema that cannot express 7/12, a common real-world pitch; the targeted mechanism (quantization) is proven dead (two exact 8.75′ reads, left gable pass, artifacts reduced to the one out-of-scope oblique); all residual misses sit in explicitly out-of-scope mechanisms. Retention is on correctness grounds, not scores — the FAIL verdict stands in the record.
**STANDING RULE — protocol amendment (verbatim):** structural/correctness candidates carry two-part pre-registrations — targeted-mechanism criteria render keep/revert; overall-score criteria are recorded but cannot force reversion of a correctness fix.
**VOID-RATE WATCH ITEM:** 1c era 0 voids; C2 era 2/4. Threshold: 2 further voids within the next 4 valid-run attempts reopens empty-extraction stability as BLOCKING.
**"Best validated run" PDF line: DECLINED** (max-of-distribution = cherry-picking, fails the honest-framing standard). **Approved alternative SHIPPED:** per-fixture *current validated baseline* — latest valid run under the current contract hash, displayed with total valid-run count and min–max range. 95.6 may appear only in that form. (`data-role="validated-baseline"` in the accuracy PDF; pinned.)

### DORMER TRACE (owed before next candidate; no fix without ruling) — CLASSIFICATION: REVELATION-OF-STOCHASTICITY, not a true regression
**Was the prior 15.0 exact-pass quantization-snapped?** NO — three independent lines:
1. **Causal decoupling:** the dormer number is a WIDTH read (p2, square-on left elevation) against the same-plane 444″ WALL REF; p2's own pitch_reasoning (C2 run, verbatim): *"This is an eave-side view; the roof slope is foreshortened toward the camera and no gable triangle is visible, so pitch cannot be measured from this photo."* The pitch ladder never touches a width read — C2 could not mechanically alter it. No ladder has ever applied to widths.
2. **The pre-C2 series already contained the spread:** same-photo dormer width across all red-house fable runs: 15 → 15.5 → 17.5 → 15 → 17 → 15 → 15 → 15 (1c) → 17 (C2 void) → 16.5 (C2 valid). 17.5 and 17 appeared on 07-08 under the OLD ladder. The 1c run's exact 15.0 was a draw from a noisy width estimator whose MODE sits on truth — mode-luck, not ladder-snap.
3. **Same-photo instability is the established fable-5 disease** (counts 27→28, apex 437→330 px, now width 15→16.5 — ~10% swing on an unchanged photo).
**Excerpts (verbatim, run docs):** 1c p2: *"Direct square-on left elevation; dormer face parallel to camera, both dormer windows full-front, width read against 444″ wall ref — kept"* (→15.0). C2 p2: *"Kept — only direct straight-on view of the left slope; dormer face parallel to camera, two contractor-pinned sliders visible full-front"* (→16.5).
**Status: reported, no fix proposed. Awaiting ruling if any.**

## Iter 79j.89 — OBLIQUE DEMOTION-RULE CANDIDATE — PRE-REGISTRATION (Howard GO 2026-07-11 with 3 edits folded verbatim; verdicts render against THIS TEXT ONLY)
**Target mechanism:** admitted-unreliability on oblique gable/pitch reads — a photo whose own reasoning ADMITS foreshortening/oblique inflation while keeping the high value (canonical: red-house p5 in 4e376d2d, *"horizontal foreshortening inflates the vertical conversion"* → kept 10/12 → 12.5′; Letrick p5's perennial 12.5′). Same disease family as pixel-citation: the reasoning self-documents the defect; the value rides anyway.
**Proposed rule (deterministic Python, post Phase B — mirrors the 1c gate pattern, zero LLM trust):**
1. A photo's gable/pitch read is DEMOTED when its pitch_reasoning/notes admit foreshortening, oblique-view inflation, or unreliable vertical conversion (regex family, pinned by tests against the canonical excerpts — the flagged-honest path "cannot be measured from this photo" with a null read does NOT demote; only admit-and-keep does).
2. Final gable rise re-selects deterministically from NON-demoted reads: square-on (gable-end elevation) reads preferred; if several, use the median; never the demoted high read.
3. If ONLY demoted reads exist for a gable: value kept but flagged `gable_estimated: true` (amber downstream, excluded from accuracy claims — consistent with the two-tier count precedent).
4. Demotions + re-selection logged openly in the run doc (`_gable_demotion_audit`).
**Prompt changes: NONE** (pure post-processing; contract hash `53f2bfa3344b1057` unchanged) — this is a mechanics candidate, not a prompt candidate.
**HOWARD'S 3 EDITS (verbatim, folded):**
1. *Deterministic detector:* explicit pattern set (foreshortening/oblique/angle vocabulary + retained numeric read), pin-tested against ALL historical p5 excerpts (every admitted-inflation verbatim trips it; every honest cannot-measure null does not). Edge ruled: **admits-and-compensates DEMOTES** — self-certified correction is not exempt, per the pixel-citation precedent.
2. *Deterministic re-selection:* n=1 non-demoted square-on read → that value; n=2 → the LOWER, both recorded, `gable_pair_low: true` flagged; n≥3 → median. Never average, never the higher.
3. *Two-part criteria, explicit:* VERDICT tier — demotion fires on all admitted-inflation reads, zero honest nulls demoted, no final gable sources from a demoted read, honesty mechanics unchanged both fixtures. RECORDED tier (no vote) — right gable square-on vs 8.75±0.5, aggregates, artifact recurrence. Residual logged openly: **rule catches admitted inflation only; silent inflation passes and remains a noted field risk.**
**Two-part pre-registration (per the new protocol amendment):**
- *Targeted-mechanism criteria (render keep/revert):* Letrick — the p5-class 12.5′ oblique read no longer drives any final gable; right gable final comes from a square-on/non-admitted read; demotion fires on the canonical excerpts (pinned). Red house — p3-class inflated obliques (14.1′ @ 10/12) demoted where admission language occurs; no demotion of honest "cannot measure" nulls.
- *Overall-score criteria (recorded, cannot force reversion):* Letrick right gable toward 8.75±0.5 on the final; left gable holds; red-house aggregate recorded vs band; honesty criteria unchanged.
**Protocol:** both fixtures, cached photos, valid 8/8 or void (void-rate watch active: 2 voids within next 4 attempts = stability BLOCKING), one run in flight, code frozen during runs, before/after gable series on run docs.
**Sequenced after ruling:** candidate 3 scoping (appendage detection, acceptance = corner LOCATIONS not pieces) + the still-owed photo-3/photo-4 autopsy answers ((a) photo 3's original failure class; (b) why photo 4 imaged the chase and reported no appendage). September package assembly follows the queue.

### 79j.89 RUN REPORT (2026-07-11, hash `53f2bfa3344b1057` unchanged, fable-5, code frozen, one in flight; before/after series stamped on run docs)
**Runs:** Letrick `2d60a27c` valid 8/8 (11.5 min) · Red `32a55599` valid 8/8 (12.0 min). **Void-watch: 0 voids in 2 attempts** (0 of the 2-in-4 threshold; 2 of 4 window attempts consumed).
**VERDICT TIER (renders keep/revert):**
1. *Demotion fires on all admitted-inflation reads:* Letrick **4/4** ✓ (p1 "corrected for mild perspective tilt", p3 "moderate confidence due to corner perspective", p5 "with perspective correction", p7 "perspective tilt adds some uncertainty"). Red house **1 of 2 — DETECTOR ESCAPE**: p3 read 10.5 @ 10/12 with *"the gable face is angled away so run is compressed - read as ~10/12 with moderate confidence"* — admits-and-keeps via NOVEL vocabulary ("angled away… compressed") absent from the pinned historical corpus → not demoted. Final unaffected (square-on preference selected p4's clean 8.3), but strictly a criterion-1 miss, reported not hidden.
2. *Zero honest nulls demoted:* ✓ both fixtures.
3. *No final gable sources from a demoted read:* ✓ both (left ← p2 clean square-on 8.7; right ← p6 clean square-on 9.2; back ← p4 clean square-on 8.3).
4. *Honesty mechanics unchanged:* ✓ both (all same-corner conflicts flagged, zero enumerated, occlusion flags fired red-house ×5 / Letrick zero, no pixel citations occurred).
**RECORDED TIER (no vote):**
- Right gable square-on vs 8.75±0.5: final **9.2 — IN BAND for the first time on file**
- Aggregates: Letrick **97.9 (best ever**; front −0.11p, left 0.00p, right 0.00p, back −0.72a) · Red **95.9 (best ever**; left −0.51a = best-ever left, right +0.81a, BOTH dormers 15.0 exact)
- Artifact recurrence: **ZERO** 7.5/10.0/12.5 verbatim recurrences across both runs; odd pitches in live use (7/12 ×6, 9/12 ×2)
- Anomaly (label-integrity disease, honest surface): Letrick p5 mislabeled its gable read wall="back" (11.0 @ 9/12) → back wall (a 0-gable eave wall) carries `gable_estimated: true` cosmetically.
**Residual (logged openly, per pre-registration):** rule catches ADMITTED inflation only; silent inflation passes — and the red-house p3 escape shows admission VOCABULARY itself is open-class: the pinned pattern set covers the historical corpus, not future phrasings.
**Awaiting Howard's keep/revert ruling (criterion-1 partial miss via novel-vocabulary escape is the open question: fail the verdict tier, or extend the pattern set as a follow-on). Then candidate 3 scoping + the owed photo-3/photo-4 autopsy.**

### HOWARD'S 79j.89 RULING (2026-07-11) — KEEP
Criterion 1 recorded as strict miss (15/16, p3 escape via novel vocabulary) — verdict stands honest; retention on mechanism grounds per the C2 precedent: detector perfect against pinned corpus, zero false demotions, deterministic re-selection, escape caused no final-value damage.
**RESIDUAL AMENDED to complete form (in code, run docs, and here, verbatim):** Lexical demotion catches admitted inflation only where the admission matches the pinned corpus; novel phrasings escape until added; fully silent inflation always passes. Primary defense is independent geometry (square-on preference, corner agreement); lexical demotion is a second net, not a wall.
**NEW STANDING PROTOCOL — corpus maintenance (verbatim):** novel admission phrasings that escape the detector are added to the pinned pattern set with pin tests as MAINTENANCE — no fixture runs, hash unchanged, deterministic code validated by unit test against the escape verbatim, each addition logged with its source run. No follow-on candidates for vocabulary coverage — pattern-chasing is a closed loop per the counting precedent.
- *Maintenance entry #1 (SHIPPED):* "gable face is angled away so run is compressed" (source: red house run 32a55599 p3) → `angled away|compress*` added; pinned in `test_gable_demotion_iter89.py::test_maintenance_corpus_trips`. Hash unchanged `53f2bfa3344b1057`.
**Label-integrity data point (under the anchor-integrity standing rule):** Letrick p5 wall="back" gable mislabel is the first fable-5 label error on file — same species as challenger anchor-scrambling, lower rate. Confirms the gate's design principle: labels are cross-checked against geometry, never trusted. Cosmetic `gable_estimated` on 0-gable eave walls now SUPPRESSED by a trivial geometry check (audit records `flag_suppressed: no_gable_geometry`); walls with real gable geometry keep the amber flag.
Recorded tier noted, no vote: best-ever both fixtures (97.9/95.9), right gable in band first time, both dormers exact, zero artifacts, zero voids (void-watch continues).

## Iter 79j.90 — PHOTO-3/PHOTO-4 AUTOPSY (owed; delivered WITH candidate 3 scoping)
**(a) Photo 3's original failure class: TRANSPORT-CLASS EMPTY, not a perception failure.** In the original Letrick run `fb8cf60e` (07-09, VOID), p3 returned `_empty_extraction: true` with `_raw_text_len: null` and `_stop_reason: null` — no reply text was ever captured (null-response empty; the class the salvage-retry/repair-ladder work later targeted). It was NOT a JSON-parse break, truncation, or refusal. In the first valid run `97d99abb`, the same photo extracted cleanly (4,522 chars, end_turn) and its notes explicitly SAW the appendage: *"Siding-wrapped chimney chase on the rear projection (left of the door) — not an opening."*
**(b) Why photo 4 imaged the chase and reported no appendage: SCHEMA GAP, not a vision gap.** p4's notes in BOTH runs describe the chase in prose — `fb8cf60e`: *"Chimney chase is siding-clad (same 4.25″ lap) and centered-left on the wall, adding siding area above the eave line"*; `97d99abb`: *"siding-clad chimney chase near center-left."* The model perceived and even quantified its siding relevance — but the Phase A extraction schema has NO structured field for appendages/corner locations, so the observation lives only in free-text notes that downstream aggregation ignores. (Context note: `97d99abb` p4 also flagged an annotation discrepancy — prompt said index 4 = REAR-LEFT/360″ but the image banner read BACK/648″; it anchored to the on-image annotation.)
**Implication for Candidate 3: perception is already there; the candidate is a structured-output + deterministic-aggregation problem.**

## Iter 79j.90 — CANDIDATE 3 SCOPING (appendage/corner detection; scope only — pre-registration follows Howard's approval)
**Objective:** detect siding CORNER LOCATIONS, not pieces. Letrick answer key: **6 OSC + 2 ISC locations** (the 10-pieces-vs-6-locations conversion is already in the answer key — pieces = locations × height-driven piece count).
**Mechanism (mirrors the proven gate pattern):**
1. Phase A schema addition: `corner_locations_this_photo`: array of `{type: "outside"|"inside", locator: short text (e.g. "front-left house corner", "chase left edge"), walls: [labels]}` — prompt change → new contract hash → full two-part pre-registration per the protocol amendment.
2. Deterministic Python aggregation post Phase B (no LLM trust): dedupe per-photo locations across photos into house-level corner locations by wall-pair + locator similarity; same-location cross-photo agreement upgrades confidence (mirrors 1c same-corner gating); single-photo locations stay flagged.
3. Labels cross-checked against geometry per the anchor-integrity standing rule (a corner location claimed on a wall the photo cannot see = demoted).
**Draft acceptance (for the pre-registration):** VERDICT tier — Letrick lands exactly 6 OSC + 2 ISC locations; the chase's corners are among them; zero phantom locations on the red house (its answer key TBD from Howard); honesty mechanics unchanged. RECORDED tier — piece-count conversion vs the key, aggregates.
**Risks logged:** (i) label integrity — the challengers' anchor-scrambling precedent applies; geometry cross-check is mandatory, (ii) double-count across overlapping photos — dedupe rule must be deterministic and pinned, (iii) locator free-text is open-class — dedupe keys on wall-pair + type first, locator text second.
**Open input needed from Howard:** red-house corner-location answer key; approval of scope → pre-registration text.
**Then: September package assembly.**

### FINDING 2 RECLASSIFICATION (Howard ruling 2026-07-11) — "appendage blindness" CLOSED AS MISDIAGNOSIS
The original finding (Letrick run failed to identify vertical appendages — chimney chase, recessed entry) is reclassified: **perception was present in both witness photos**; the losses were **transport-class** (p3 null-response empty — retry infra now covers) and **schema-gap** (p4 prose observation with no structured field). Verbatims on the original finding (also stamped on run docs 97d99abb + fb8cf60e):
- p3 (`97d99abb`): *"Siding-wrapped chimney chase on the rear projection (left of the door) — not an opening."*
- p4 (`fb8cf60e`): *"Chimney chase is siding-clad (same 4.25″ lap) and centered-left on the wall, adding siding area above the eave line."*

## Iter 79j.91 — CANDIDATE 3 PRE-REGISTRATION (full two-part draft; Howard scope-APPROVED with 3 edits folded verbatim; red-house criteria TBD-PENDING-KEY; NOTHING implemented, NOTHING fires until the key is entered and Howard approves the final text)
**Change (prompt + mechanics):** Phase A schema addition `corner_locations_this_photo`: array of `{type: "outside"|"inside", locator: <short text>, walls: [labels], position: <approx distance or fraction along the wall from its left end as seen>}` — a PROMPT CHANGE: new contract hash expected, captured and stamped at run creation per the standing rule. Deterministic Python aggregation post Phase B (no LLM trust).
**HOWARD'S 3 EDITS (verbatim, folded):**
1. *Two-tier corners with presence guarantee:* cross-photo same-location agreement → confirmed; single-photo → unconfirmed, amber, flagged for field verification — but ALL detected corners enter the takeoff and material math. Tier labels confidence; it never deletes a corner. Omission is the primary failure mode, opposite of counts.
2. *Type conflicts flagged, never resolved:* same dedupe location with OSC/ISC disagreement → `corner_type_conflict`, both recorded, amber. Dedupe key = wall-pair + position tolerance along the wall.
**DEDUPE TOLERANCE (Howard ruling 2026-07-11, verbatim, supersedes the draft tolerance):** ±10% of wall length or ±2 ft, whichever is larger, **hard-capped at ±4 ft** — on a 54′ wall an uncapped ±10% is ±5.4′, wide enough to merge the chase's two outside corners into one location. **Additional safeguard, non-negotiable: two detections on the same wall-pair with opposite corner types (one OSC, one ISC) never merge regardless of distance** — an outside and inside corner in close proximity is exactly what a chase or recessed entry looks like, and merging them deletes real geometry. That's the failure the presence guarantee exists to prevent. (INTERACTION FLAGGED FOR FINAL-TEXT APPROVAL: with never-merge in force, opposite-type detections within tolerance will be kept as two separate locations — should they ALSO carry `corner_type_conflict` amber (possible one-misread-of-one-corner) or stand clean as presumed chase/recess geometry? Draft default: kept separate AND flagged amber, so the field check decides — flag labels doubt, never deletes.)
3. *Verdict tier:* Letrick total locations (confirmed + unconfirmed) = exactly **6 OSC + 2 ISC**, chase corners among them, zero phantoms, zero silent type conflicts. *Recorded tier:* confirmed-tier count, p4's chase observation landing structured, aggregates. Pieces-vs-locations (10/6) conversion noted from the answer key for truck reconciliation.
**Mechanics detail (per approved scope):** geometry cross-check per the anchor-integrity standing rule — a corner location claimed on a wall the photo cannot see is demoted to unconfirmed (never deleted, per edit 1); dedupe keys on wall-pair + type + position first, locator text advisory only; `_corner_location_audit` on the run doc (per-photo sightings, dedupe decisions, tiers, conflicts) with residual note.
**Honesty criteria carry unchanged both fixtures** (conflicts flagged, count tiering, pixel-citation demotion, oblique demotion, occlusion flags, imputed exclusion).
**Protocol:** both fixtures, cached photos, valid 8/8 or void (void-watch active: currently 0 of the 2-in-4 threshold, 2 window attempts consumed), one run in flight, code frozen during runs, per-wall verdict aggregate-no-vote, before/after on run docs.
**Red-house verdict criteria: TBD-PENDING-KEY** — awaiting Howard's corner answer key (in progress; includes the dormer-corner convention ruling). Nothing fires until the key is entered and the final text is approved.

### FINAL TEXT APPROVED (Howard 2026-07-11) — GO. Contract hash `53f2bfa3344b1057` → **`cbcb392fc94104fa`** (capture-stamped per standing rule)
**Interaction ruling (verbatim):** APPROVED as drafted — opposite-type detections within tolerance are kept as two separate locations AND flagged amber; the field check decides, the flag labels doubt, never deletes. Refinement: distinct flag name **`adjacent_opposite_type`** — `corner_type_conflict` stays reserved for same-location type disagreement. Different doubts, different field questions ("which is it?" vs "is this a bump-out or a mistake?"). Implemented: same-spot epsilon 2.5% of wall length → corner_type_conflict; beyond epsilon within tolerance → adjacent_opposite_type.
**STANDING CONVENTION:** shed dormer corners are POSTED OSC locations — counted in corner keys on all dormered houses. Red house has zero inside corners.
**RED HOUSE GROUND TRUTH ENRICHED (backup taken first → `tape_check_backup_79j91` on the estimate):** exposure confirmed 3.75″. Corner-anchored, all corners field-counted: FR/FL/BR 33 full + partial top (1.5″ reveal, 2.25″ cut) = 10.44′ each (count criterion 33, or 34 w/ partial-top flag); BL 23 full, full course meets frieze = 7.19′. **BACK WALL STEPPED** ~mid-span (facing the wall: right segment 33c/10.44′, left segment 23c/7.19′; cross-check 10 courses × 3.75″ = 3.125′ ≈ grade rise 3.1225′ ✓) — entered as segments, start_ref=siding_start. Front entered 10.44′/33c. Left-wall tape 10.3125 KEPT with annotation (taped to full courses excl. partial). Dormers: both corners field-counted 13c no cut = 4.06′ each — ELEVATED posts, roof-plane-based — annotated on dormer entries (width 15.0 untouched).
**C3 RED-HOUSE VERDICT CRITERIA (fills TBD):** total locations (confirmed + unconfirmed) = **8 OSC + 0 ISC** (four main ground-to-eave corners + four dormer corners). Dormer corners are ELEVATED posts (~4.06′, roof-plane-based, not ground-reaching) — detection must not require ground contact; any check that silently drops non-ground corners is a FAIL. Zero phantoms, zero silent type conflicts, zero ISC (any ISC = phantom). Recorded tier: confirmed-vs-unconfirmed split, occluded-side behavior (woodpile/shrub walls), aggregates.
**IMPLEMENTATION (shipped, 48 pins green):** Phase A schema `corner_locations_this_photo` (type/walls/position_frac/locator/elevated; "never skip a corner because it does not reach the ground"); deterministic `_apply_corner_locations` — tolerance max(10%, 2ft) capped 4ft; opposite types never merge; presence guarantee (geometry mismatch demotes to unconfirmed, never deletes); `corner_locations` + `_corner_location_audit` with residual on run docs. Pins: `test_corner_locations_iter91.py` (10 tests incl. 54′-wall cap, 2ft floor, both conflict flavors, elevated preservation).

## Iter 79j.92 — C3 LETRICK VOID → TWO PINNED FIXES → RE-RUN VALID 8/8 → PASS-WITH-RESIDUALS (Howard-ruled 2026-07-11)
**dce41292 ruling: VOID** per pre-registration (valid 8/8 not met — p2/p4 zero data both attempts). No verdict banked; sightings retained as diagnostic evidence only. Void-watch TRIPPED (2nd void event in window) → stability work became blocking and was delivered below.
**FIX 1 — 79j.91 clarifying amendment (dedupe-bug class, code-only, hash UNCHANGED `cbcb392fc94104fa`):** identical two-wall pair set = ONE physical junction by geometry (two walls intersect at exactly one vertical) — merge regardless of position_frac (frac is frame-relative: 0.0 from one wall = 1.0 from the adjacent). Opposite types on an identical two-wall pair = same-spot dispute → `corner_type_conflict`, never "adjacent". Root cause of the dce41292 over-count: all 4 house corners doubled via opposing frames (11 OSC + 3 ISC raw → 7 OSC + 3 ISC on diagnostic-preview replay, labeled preview-only, no verdict from a void run).
**FIX 2 — TRUNCATION-SALVAGE RUNG (empty class 4, code-only, outside hashed contract):** `_clean_json_reply` rung 4, gated on end-of-input parse signature (err.pos at EOF OR "Unterminated string"). Constraint (verbatim ruling): salvage ONLY objects/fields fully parsed before the stop — never close structures with invented values, never fill; a bare trailing number is never salvaged (digits may be cut); marks `_json_repaired: "truncation"` + `_extraction_partial: true`. Pins: mid-value truncation → flagged partial NOT plausible completion; mid-array → whole array dropped; nothing-complete → `_parse_error` unchanged; non-truncation mid-body corruption NOT salvaged.
**EMPTY CLASS 4 LOGGED:** natural mid-JSON stop, stop_reason=end_turn, NOT a token limit, retry-immune, deterministic on heavily-foreshortened photos. `_empty_reason` now names the class. Capture-guidance note added to GuidedCaptureWizard (foreshortened elevations = known extraction risk; prefer corner-angle reshoots). **KEY FINDING (live re-run):** class-4 stops cut only AFTER the final field — the extractions were COMPLETE and transport was discarding them; retroactively relevant to historical voids. Fired on 3/8 photos (incl. both prior voiders), recovered all three with ZERO field loss — would-be-void converted to valid 8/8.
**RE-RUN `ed613872` (Letrick, cached photos, claude-fable-5, hash `cbcb392fc94104fa` stamped): VALID 8/8, zero empties, zero retries.** Corners: 10 locations — 7 OSC + 3 ISC vs key 6+2. All 4 house corners CONFIRMED via cross-frame merge; chase fully expressed (2 OSC + 2 ISC found and typed — first-ever chase expression); sole excess = one amber drift-pair @0.60 from p3 alone (chase left edge ~10 ft right of p4/p5 consensus, beyond ±4 ft cap, retained per 2a ruling, both flags carried). Zero silent conflicts, zero opposite-type merges, presence guarantee held.
**VERDICT: PASS-WITH-RESIDUALS.** Honesty boundary for the record: a phantom reaching CONFIRMED tier, or any silent excess, = FAIL regardless of recall.
**CRITERION AMENDMENT (79j.91, red house and forward):** confirmed-tier locations must equal the key EXACTLY; amber unconfirmed excess tolerated only when flagged + provenance-limited, logged as residual.
**Sub-items:** (a) "rear bump-out/step" locator mislabel on chase right-front corner → anchor-integrity log DATA POINT #2, geometry cross-check credited. (b) Confirmed tier requires ≥2 DISTINCT PHOTOS, never ≥2 sightings — already structural (`len(set(photo_idxs)) >= 2`); one-photo-echo case pinned with p3's live double-sighting as fixture.
**VOID-WATCH: RESET** (blocking stability work delivered and proven live — 3/3 class-4 recoveries). Fresh window, same threshold.
**Pins:** `test_c3_amendment_iter92.py` (13 tests). Full suite 766+ green (two isolated timing flakes pass standalone).
**RED HOUSE C3: FIRED** — run `8ddb8932`, rerun of `32a55599` cached photos, hash `cbcb392f`, code frozen, one in flight, valid 8/8 or void, scored against pre-registered criteria only: 8 OSC + 0 ISC, elevated dormer posts detected without ground contact (silent drops = FAIL), zero ISC, zero silent conflicts, occluded-side behavior recorded. Report against the text.

## Iter 79j.92 (cont.) — C3 RED HOUSE PASS-WITH-RESIDUALS → CRITERION AMENDMENT FINALIZED → CANDIDATE 3 CLOSED (Howard-ruled)
**Red House run `8ddb8932`: VALID 8/8** (salvage rung 2/8 fired — p2/p6, zero field loss; cumulative 5/5 lossless across C3 → class-4 handling PRODUCTION-PROVEN). Score: 9 OSC + 0 ISC vs key 8 + 0; confirmed=5.
**VERDICT: PASS-WITH-RESIDUALS.** Key coverage 8/8; confirmed excess zero; zero ISC; zero conflicts. **Dormer/elevated criterion PASSED in full: 4/4 posts detected, elevated=True, zero silent drops** (the criterion this run existed to test). Recorded for the record: all four main corners confirmed through woodpile/ladder/smoker/shrub conditions — corner detection survives real remodel-condition occlusion, the market condition, on the first try.
**CRITERION AMENDMENT FINALIZED (79j.91, retroactively consistent with Letrick precedent — replaces the ambiguous "must equal exactly"):**
1. **Confirmed tier:** zero locations outside the key — phantom-in-confirmed = automatic FAIL. (The confirmed tier feeds tape-provable claims; its integrity requirement is zero phantoms.)
2. **Coverage:** every key location present in confirmed ∪ unconfirmed — full absence = FAIL (omission is the primary failure mode).
3. **Honesty-in-amber:** unconfirmed amber excess tolerated when flagged + provenance-limited, logged residual. Demanding confirmed = full key would hinge verdicts on photo coverage, not detection correctness, and would teach the system that promotion is safer than honesty — the exact inversion of everything built since 1c.
**Residual logged:** cross-frame elevated-post excess (p6 right@0.75 = clerestory right post seen from the adjacent frame; localization family, frame-labeling variant).
**MAINTENANCE-CLASS FLAG APPROVED + SHIPPED: `adjacent_frame_candidate`** — two one-wall ELEVATED detections of the same type on ADJACENT wall frames at corner-proximate fracs (within dedupe tolerance) get flagged, NEVER merged. Pure post-processing annotation; detection, prompts, hash untouched (`cbcb392fc94104fa`). Sharpens the field question from "is this a corner?" to "same post seen twice?". Amber-on-amber — no harm possible under the doctrine. Pinned against the live p6/p7 pair as fixture (4 pins). No fixture re-runs required. Same class as the corpus-maintenance protocol.
**Both run docs annotated with `_c3_verdict` (verdict, basis, residuals, recorded-tier note).**
**CANDIDATE 3: CLOSED.** Finding-2 arc complete — perception was never absent; schema and transport were. Two fixtures later every corner on both houses is detected, typed, tiered, and honest about its witnesses.
**QUEUE ADVANCES: SEPTEMBER PACKAGE ASSEMBLY (LP-native).** First deliverable: scope breakdown against the PRD spec (ExpertFinish colors, dealer SKUs, whole-piece rounding, install-system auto-adds, ±3% vs hand-takeoff acceptance) as a work plan for Howard's approval before implementation.

## Iter 79j.93 — SEPTEMBER PACKAGE ASSEMBLY: SCOPE APPROVED + PHASE 1 SHIPPED (2026-07-11)
**Howard's scope answers:** dealer lines = BlueLinx NAMES ONLY for September (no SKU codes yet); ExpertFinish colors = LP's published palette; install-system auto-adds = already on file (Iter 68/78ab mapping-spec rules confirmed: .019 Coil 1 roll, Touch-up kit 1/color, OSI Quad Max 2 tubes, J-blocks per openings, Mini Splits, 190 battens, 540 shake bump, no LP starter/J-channel/ISC, LP fasteners manual); ±3% fixture = LETRICK (Howard to provide hand-takeoff numbers); C3 → OSC CONFIRMED (count × height ÷ 16' pieces, ceil; amber included per presence guarantee, flagged).
**Approved phases:** 1) Package engine (backend, deterministic) → 2) ExpertFinish colors (palette + selector + 3D flat-color repaint, package item 8) → 3) ±3% acceptance harness vs Letrick hand-takeoff (per-SKU delta table, Tape-Check-history pattern, doubles as pitch artifact) → 4) `LP_AI_FORMULAS_V1` flag-flip go/no-go moment.
**PHASE 1 SHIPPED:** `backend/lp_package.py` — `assemble_lp_package(measurements, corner_locations, wall_heights)`: runs shared `_build_lines` with LP PDF formulas forced ON (override_flag), LP lines only, whole-piece `ceil()` at SKU level everywhere (incl. fixing the legacy OSC `round()` under-order: 37.6 LF → 3 pcs not 2), C3 corner-location OSC override (per-corner height = shorter adjacent wall for two-wall corners / own wall for one-wall; elevated posts priced at full wall height + flagged "trim to post height in field"; amber corners included + flagged), install-system auto-adds ride the mapping spec unchanged. Endpoint: `POST /api/estimates/{est_id}/lp-package/preview` (run_id optional → latest done run; ownership-checked). Router registered.
**Live Letrick verification (run `ed613872`):** 22-line package, 260 total pieces, OSC = 5 pcs from 7 C3 locations (64.5 LF: 8.3+8.5+8.3+8.5 house + 3×10.3 chase/drift), amber residual flagged in line note + summary flags, `osc_source: c3_corner_locations`. Fallback path (no corner locations) verified → `outside_corner_lf` ceil.
**Pins:** `tests/test_lp_package_iter93.py` (8 tests: Letrick pattern, ISC never counted, shorter-adjacent-wall rule, elevated flag, override-replaces-spec-line, fallback whole-piece, whole-piece-everywhere/LP-only, install auto-adds present). LP + pricing + corner suites green.
**NEXT:** Phase 2 (ExpertFinish palette) → Phase 3 (±3% harness — BLOCKED on Howard's Letrick hand-takeoff numbers) → Phase 4 (flag flip).

## Iter 79j.94 — LP MATERIAL-USAGE CONVENTIONS INGESTED + LETRICK TRUCK-LIST HARNESS (Howard's spec block, 2026-07-11)
**Conventions layer shipped (`backend/lp_conventions.py`)** — authoritative until the original workbook uploads; workbook disagreement = FLAG, never silently pick (`spec_discrepancies()` audit pinned to []):
- Core lap formula: reveal = face − 1"; coverage = length × reveal/12; pcs/square = ROUNDUP(100/coverage). 16' table {6":16, 7":13, 8":11, 12":7}; 12' table {21, 18, 15, 10} — all pinned.
- **ESTIMATING TRAP encoded as validation:** 8" lap face is 7-7/8" NOT 7-1/4" (reveal 6-7/8" → 9.17 → 11/sq). Pin proves the wrong face changes the answer (→13/sq).
- Shakes: reveal JOB-SPECIFIC, never silently defaulted — unspecified → `reveal: unconfirmed` flag + priced at minimum reveal 6-7/8" (worst case, 44/sq). Bounds pinned: 44 @ min, 31 @ max.
- B&B battens: spacing job-specific, flag if unspecified (PDF-standard 16" o.c. applied visibly).
- Nickel Gap: fixed 7" locked (9.33), pinned.
- Soffit: width matched to overhang; non-standard (e.g. 17") → next width up + rip-waste line note; both ordering methods (area, eave-length); 38 Series 9 pcs/bundle noted.
- **Waste doctrine (package-wide):** 10% default lap/soffit, waste BEFORE whole-piece round-up, per-line always-up never averaged; every formula line carries the transparency triple {base_qty, waste_qty, ordered_pcs} — live Letrick lap line: 199.86 → 219.84 → 220 ✓.
- **TWO PENDINGS (never filled from other sources, surfaced in package summary):** (1) shake waste factor (lap 10% used, FLAGGED pending); (2) LP trim/accessory conventions carry-over from Alside context (starter/J/finish-trim/soffit-F/fascia-coil) — NOT encoded until Howard confirms.
**Truck-list harness shipped (`backend/lp_truck_reconcile.py` + `POST /api/estimates/{id}/lp-package/truck-reconcile`)** — the pre-±3% "cheaper, harder check". Fixture pinned: 20 sq D4.5 / 20 starter / 10 OSC / 2 ISC / 30 J / 2 coil / 23 finish trim / 24 soffit / 18 soffit-J.
**LIVE LETRICK RESULTS (run ed613872): 0 match, 4 deviation (itemized w/ cause), 5 pending_confirmation:**
- D4.5: derived 21 vs 20 (18.33 sq × 1.10 → whole-square up; truck ran ≈9.1% effective waste)
- OSC: derived 7 (6 confirmed + 1 amber) vs 10 — answer-key 10/6 conversion, delivered extras beyond one-piece-per-corner
- ISC: derived 3 vs 2 — includes 2 amber (drift residual, flagged + provenance-limited), physical key 2, field check resolves
- Soffit: derived 10 (eave-length, vinyl basis) vs 24 — truck unit basis unverifiable from record
- Starter/J/Coil/Finish trim/Soffit J: pending_confirmation (Alside-context conventions, sanity notes carried: starter 168 LF ÷ 10' = 17; openings perimeter 219.3 LF)
**Pins:** `tests/test_lp_conventions_iter94.py` (14 tests). LP suites 54 green.

## Iter 79j.94 (cont.) — CONSOLIDATED LP ACCESSORY RULESET INGESTED + HARNESS RE-DERIVED (Howard rulings, 2026-07-11)
**Rulings applied:**
- Shake waste RULED: 10% same as lap, before whole-piece round-up. Provisional — revisions ship as conventions updates, never silent edits. (Pending flag removed; unspecified-reveal flag unchanged.)
- **LP-native composition (authoritative):** NO J-channel, NO finish trim, NO aluminum coil on LP takeoffs — composition bugs. `lp_composition_bugs()` guard strips + reports (live Letrick: `.019 Coil` auto-add stripped, reported in `composition_guard_removed`; "J blocks" correctly survive — blocks not channel, pinned). Vinyl rules (J by opening+perimeter, finish trim) apply to vinyl only.
- Starter CARRIES (by eave/start-course length). Soffit F 2× eave + fascia-coil-by-run CARRY for vinyl; fascia coil superseded on LP by the fascia/rake ruling below.
- **LP trim system:** 540 OSC per OSC location WHOLE STICKS PER LOCATION (Letrick: 7 locations → 7 sticks, was 5 pooled); 440 4/4"×4"×16' per ISC location (C3-driven, live: 3 ISC → 3 sticks, 2 amber flagged); 540 5/4"×4"×16' window/door wrap (door 3/4-side pending, flagged on line); **440 4/4"×8"×16' fascia + rake boards** (NEW — supersedes both fascia coil and the old 440 4×4 "horizontal runs" derivation; rake = slope LF never plan-view; live: 181.4 LF × 1.10 ÷ 16 = 13 sticks). 440 carries TWO profiles — full profile spec always, never "440 Series" bare.
- **Whole-square doctrine STANDS** — order rounds up (21); truck's 20 = `crew_judgment_short_order`, not a rules failure (over-order stockable, under-order stalls crews). AMENDMENT: `near_boundary` annotation when pre-round qty within 0.5 sq of lower whole square ("21 sq ordered; raw 20.16 — crew's trim-or-keep call"). Pinned.
- **Soffit basis recovered:** Charter Oak vinyl 10"×12' = 10 sqft/pc (24 pcs = 240 sqft). Derivation error = eaves-only paneling; conventions fix (package-wide, vinyl AND LP): soffit panels eaves AND rakes wherever overhangs carry soffit; rake slope from pitch + half-span NEVER plan-view (`rake_slope_length_ft` pinned: 7/12 over 15' ≈ 17.37'); panel basis explicit per line or composition bug. Letrick: eaves-only 11 → rake-corrected 20; residual vs 24 = crew cushion. HELD pending Howard's rake-soffit confirmation.
- **Corner reconciliation:** OSC `reconciled_by_key` (6 physical → 10 via chase-height stick conversion ~18-19'×2 multi-stick, house 1:1; pipeline 7th = drift amber). ISC EXACT match to key (2=2, NO conversion; pipeline 3rd logged against the drift residual, not the key). Causes kept distinct in ledger, pinned.
**LIVE HARNESS (re-derived): 3 match (ISC exact, Coil 2=2, Soffit-J 18=18 — the 2×eave rule validated to the piece) · 1 reconciled_by_key (OSC) · 3 deviation (D4.5 21v20 crew short-order + near_boundary; Starter 14v20 with comment/code discrepancy FLAGGED; J 18v30 receiver runs beyond stated rule) · 1 pending_rule (finish trim formula not on record) · 1 held (Soffit, rake confirmation).**
**DISCREPANCIES FLAGGED (doctrine: never silently pick):** (1) ruling text says 540 OSC 5/4"×**6**"×16'; catalog SKU is 5/4"×**4**"×16' — held on catalog SKU, flagged for Howard. (2) Starter rule file comment says ÷10, code does ÷12.5 — flagged in harness cause. (3) Starter carries to LP per ruling but NO LP starter SKU exists in catalog — catalog gap.
**PENDING (6, flagged never defaulted):** OSC stick length 192"=16'; door trim 3/4-side; corner splice >16'; fascia/rake splice; fascia/rake presence toggle; Letrick rake-soffit. Plus: finish-trim vinyl formula; Letrick hand-takeoff (±3% Phase 3).
**Pins:** iter93 (11) + iter94 (18) = 61 LP tests green. Live endpoints verified.

## Iter 79j.94 (cont. 2) — SUBSTITUTION + LP STARTER RULINGS SHIPPED (Howard, 2026-07-11)
**MATERIAL-LIST SUBSTITUTION (package feature, ruled + shipped):** derived lines carry Howard's defaults (540 OSC 5/4"×6"×16' IS the default — the 4" catalog SKU was never the convention); contractor substitutes per line via `preview` payload `substitutions: {old_name: new_item}`. Enforced: (1) substitution triggers FULL RE-DERIVATION from stored geometry (`corner_sticks_for_length` — 10.44' corner: 1×16' vs 2×10' pinned), never a stale-count reprice; (2) `substituted_from` provenance + "RE-DERIVED from stored geometry" note — quantities stay tape-provable post-edit; (3) options limited to the known LP product table from catalog seed (free-text SKUs refused, error surfaced in `substitution_errors`); (4) stateless per-request — nothing silently remembered as a global default.
**LP STARTER (ruled + shipped):** no SKU exists because none is used — starter is FIELD-RIPPED from siding stock. Package ALWAYS carries a non-SKU informational line: "LP Starter — field-ripped from siding stock", unit LF (derived from start-course length, live Letrick 168 LF), `pieces_added: 0` default. THIN-WASTE-MARGIN interaction flag (near-boundary doctrine): when siding ordered − waste-adjusted < 0.5 pc, starter line + summary warn rips may consume the cushion (Letrick: 0.16 pc cushion → fires). Dedicated-rip substitution: `substitutions: {starter_line: "dedicated-rip"}` → pieces_added = ceil(168/16) = 11, re-derived never hand-typed. Mapping note: absence of an LP starter SKU is the convention, not a gap.
**Live verified:** OSC 6"→4" substitution returns qty 7 re-derived with provenance; free-text refused; starter line present with thin-margin annotation. **Pins: iter93 now 17 tests; LP total 35 green.**
**STILL ON HOWARD'S DESK:** OSC stick length (192"=16'?) · door trim 3/4-side · corner splice >16' · fascia/rake splice · fascia/rake presence toggle · Letrick rake-soffit · starter ÷10 vs ÷12.5 discrepancy · finish-trim vinyl formula · Letrick hand-takeoff (±3% Phase 3). Phase 2 (ExpertFinish palette + selector + 3D repaint) next in queue.

## Iter 79j.94 (cont. 3) — RULING 1 AMENDMENT: PER-SYSTEM DERIVATION TABLE (Howard, 2026-07-11)
**Amendment (supersedes — LP trim scope was understated):** LP jobs: SOFFIT panels EAVES ONLY (no rake soffit wrap); 440 4/4"×8"×16' covers BOTH eaves (fascia) AND rakes (rake boards) — one product across both run types, LF = eave runs + rake slope (pitch + half-span, never plan-view), splice-and-round-up TOTAL sticks (RULED — was pending #4), always present (RULED — was pending #5). Vinyl unchanged: soffit eaves+rakes; fascia = aluminum coil by run length.
**Per-system table encoded (`SYSTEM_DERIVATION` in lp_conventions):** VINYL = soffit(eaves+rakes) + coil fascia + J + finish trim. LP = soffit(eaves only) + 440 4/4×8(eaves+rakes) + 540 trim system + no J/finish trim/coil. Any line crossing systems = composition bug.
**Enforcement shipped:** package strips the rake-driven "38 Series Soffit 16 x 16 Closed" row on LP-native (reported in `summary.system_table_enforced`), Vented row annotated "eaves only (per-system rule)". Fascia/rake flags cleared (ruled). Pendings now exactly 3: OSC stick length, door 3/4-side, corner splice >16'.
**Harness soffit line SCORED (rake question resolved at rule level):** status deviation, cause RECONCILED — basis (Charter Oak 10"×12' = 10 sqft/pc) + vinyl eaves+rakes rule → 20 pcs vs delivered 24 = crew cushion. Harness now: 3 match · 1 reconciled_by_key · 4 deviation · 1 pending_rule (finish trim). All 69 LP pins green; live verified.
**NOTE:** the hover-spec LP soffit rows (staged behind LP_AI_FORMULAS_V1) still carry a rake-driven Closed row — package engine enforces the amendment on top; hover-spec reconciliation belongs to the Phase-4 flag-flip review.

## Iter 79j.95 — COLOR ARCHITECTURE RULING SHIPPED (Howard, 2026-07-11; lands before Phase 2 selector)
**Ruling:** color is a PER-COMPONENT, LINE-LEVEL attribute, never job-level. Siding / soffit+fascia / opening trim / OSC / ISC can each carry a different ExpertFinish color on one job.
**Shipped (`backend/lp_colors.py` + package wiring):**
1. Every material line carries `color` + `component_group` fields; line identity = (name, color) — `consolidate_lines` NEVER merges across colors (same profile + different color = different SKU, pinned).
2. `colors` payload on preview endpoint: `{"all": X}` is the SHORTCUT (not the model); per-group keys override (`{"all": "Quarry Gray", "osc": "Abyss Black"}` live-verified — corners recolor while siding holds).
3. 3D flat-color repaint targets component mesh groups independently — data model ready; mesh wiring lands with Phase 2 UI.
4. Availability per product line PENDING verification against LP's published ExpertFinish matrix: `AVAILABILITY_VERIFIED = False` → every colored line carries the verification flag; unknown colors/groups REFUSED with surfaced errors, never silently substituted; no color ever defaulted (None until assigned).
**Palette (verified against LP's published page, 2026-06):** 16 core colors incl. Sand Dunes (2026 Color of the Year) + 6 Naturals Collection (Bonsai Black, Weathered Walnut, Aged Amber, Saffron Cedar, Smoky Slate, Washed White) + Primed = 23 options, pinned.
**Pins:** `tests/test_lp_colors_iter95.py` (7 tests). LP suite total 44+ green. Live endpoint verified with mixed per-group colors.
**Phase 2 remaining:** selector UI per component group + 3D mesh-group repaint + color-matched accessory threading (touch-up kits/caulk) + ExpertFinish availability matrix verification.

## Iter 79j.96 — STATE CHECK RECONCILIATION: SIX-RULING BLOCK RESTORED (Howard, 2026-07-11)
**Stale pendings restored from Howard's message and applied:**
1. **OSC stick length CONFIRMED 16' (192")** — flag removed, line notes updated.
2. **Door trim 3-SIDE (head + legs); windows 4-side** — 540 wrap re-derived: entry 21−3' sill = 18', patio 25−6' sill = 19'; Letrick wrap 10×14 + 2×18 = 176 LF → 11 pcs (was 12). GARAGE 32' HELD: 16 + 2×8 reads as already-3-side by inspection — flagged on line when garage present, never silently cut.
3. **Corner splice >16': SPLICE-AND-ROUND-UP TOTAL STICKS, uniform across corners/fascia/rake** — `corner_sticks_for_length` re-implemented: whole stick per location ≤16'; over-length runs = full sticks + POOLED tails (two 18.5' chase corners = 2 full + ceil(5/16) = 3 sticks, not 4). Pinned. Substitution re-derivation inherits the rule.
4. **Finish trim (vinyl) RULED formula: Σ window widths + eave run** — validated vs Letrick's 23: Σ widths 37.5 LF + 108 = 145.5 ÷ 12.5' = **12, NOT reproduced (Δ−11)**; per-opening-whole-piece alternative = 19, also short. Reported for Howard's refinement. Harness line scored deviation.
5. **Splice-rule verification vs 10-OSC truck count:** ruled splice at 12.5' vinyl derives 7; full-stick-per-segment 8; delivered 10 → +2/+3 crew extras — the truck count does NOT discriminate between splice conventions. Logged in OSC cause.
6. Confirmed already logged: rake-soffit per-system amendment ✓, fascia always-present ✓, color-per-component architecture ✓.
**GENUINELY OPEN (exactly 4):** (a) starter ÷12.5 (→14) vs ÷10 (→17) comment/code discrepancy — both derivations stated, Howard to rule; (b) ExpertFinish availability matrix — LOOKUP task (ingest published color-by-product matrix, flag unsupported combos; BlueLinx sheet = stocking overlay); (c) BlueLinx SKU upload (Howard); (d) Letrick hand-takeoff (Howard, gates ±3%).
**Harness after reconciliation: 3 match · 1 reconciled_by_key · 5 deviation (all itemized w/ cause) · 0 held.** All 77 LP pins green, live verified.
**PHASE 2 SCOPE (GO on clean readback):** Material List tab (flags visible, live re-derivation, read-only until explicit edit) · component-group color selector with apply-to-all · mesh-group flat repaint.

## Iter 79j.96 — CONFIDENTIAL PRICING LAYER SHIPPED (2026-07-12; Issue 1/P0 CLOSED)
**BlueLinx PIT00003 ingestion (`lp_costs.py`)**: dealer cost table keyed by PRODUCT + FINISH (mill / third_party_painted / brushed_mill / brushed_third_party / expertfinish / expertfinish_brushed). No item codes printed on the sheet → sku stays "pending", descriptions verbatim. Name match whitespace/case tolerant (catalog "Nickel Gap" ↔ sheet "NICKEL GAP"), never fuzzy.
**PRICING BASIS RULING (pinned in tests)**: ExpertFinish color selection changes the line's cost basis to the ExpertFinish price; missing finish price = cost PENDING — NEVER falls back to mill for a prefinished selection. Primed = its own pending basis (never assumed mill). No color = mill. Starter rip stock priced from its SOURCE SKU (38 Series 8" lap) at the SIDING group's color basis.
**MARGIN RULING — FINAL**: TRUE MARGIN on sell: `sell = cost ÷ (1 − m)` (pinned direction — a 25% markup ×1.25 is WRONG). Tiers live in SUPPLIER ADMIN: **A=30% · B=25% (DEFAULT) · C=20%**, seeded in `db.settings` (`id: lp_margin_tiers`). Percentages editable ONLY in admin (`PUT /api/admin/lp-margin-tiers`, names fixed A/B/C). Each quote carries a tier PICKER (`PUT /api/admin/estimates/{id}/lp-pricing-tier` — admin-side only, no free-type margin field anywhere, non-tier values 400). Resolution: line override > category override > quote tier (override scaffold stored, empty). Changing a tier % reprices future quotes; issued quotes keep issued sell prices (quote = document; reissue = explicit act with provenance — enforcement lands when packages attach to quote documents in Phase 2+).
**CONFIDENTIALITY (enforced by `redact_external()` + recursive-scan test)**: cost, margin %, tier name/pct, cost basis, pending reasons, and the BlueLinx sheet reference NEVER leave the server on contractor-facing surfaces. `POST /api/estimates/{id}/lp-package/preview` is ALWAYS redacted (unit_sell / line_sell / pricing_status / total_sell only; payload can never set tier). Unredacted cost view exists only at `POST /api/admin/estimates/{id}/lp-package/cost-preview` (X-Admin-Token).
**E2E verified live**: contractor preview leak-scan clean (EF lap 32.54 → sell 43.39 @B); admin tier A repriced same line to 46.49; bad tier names and free-typed margins rejected; 403 without admin token.
**Repo health fixed en route**: (1) `routes/lp_package.py` renamed → `routes/lp_package_routes.py` — module-name collision with engine `lp_package.py` broke full-suite collection (circular import via tests' routes-dir sys.path insert). (2) test_phase_a_resilience + test_salvage_retry_iter82 full-suite flake root-caused: test_anthropic_direct_key/test_run1_defects `del sys.modules["routes.ai_measure"]` → stale collection-time function bindings escaped monkeypatches → REAL litellm/Mongo calls; fixed by calling via live module reference. (3) iter93 starter pins updated to the rip-yield ruling (4 pcs @ 168 LF) and THIN WASTE MARGIN annotation restored to the starter line (dropped in the rip-yield rewrite).
**FULL SUITE: 835 passed, 1 skipped** (includes 17 new pricing pins in `tests/test_lp_costs_iter96.py`).
**BACKLOG NOTE (ruled)**: per-contractor pricing OUT of scope until post-September — tiers A/B/C are the distribution-native substitute (good customer 20% / standard 25% / retail 30%, set once in admin, picked per quote).
**NEXT: Phase 2 — Material List tab UI** (read-only until edited; substitution with re-derivation + provenance; per-component-group color selector with apply-to-all; 3D mesh-group flat repaints; SELL prices only, "pricing pending" for lines without a cost basis).

## Iter 97 — LEGACY PRICING TRACE + THE CUT + LP-NATIVE MODE (2026-07-12)
**TRACE FINDINGS (delivered, archived at /app/memory/lp_legacy_pricing_trace.json)**: (a) 31 LP items lived in ALL FOUR tier lists with hand-set prices — separation never completed. (b) The LP quote path read the LEGACY lists exclusively (estimates.py pair-lp seeding → _resolve_catalog_for_company → price_tiers; cost engine was preview-only). (c) Legacy LP prices = BlueLinx PIT00003 MILL cost ÷ (1−m), m = {whole-sale 35, Contractor 30, Builder-Dealer 25, one-opp 20} — verified to the penny for all 26 BlueLinx-backed items; 5 coil/flash-tape rows are vinyl-domain mirrors with no BlueLinx cost.
**MARGIN CORRECTION (ruled, supersedes P0-era A/B/C 30/25/20 everywhere)**: ladder = whole-sale 35% · Contractor 30% (DEFAULT) · Builder-Dealer 25% · one-opp 20%, Howard's real names. Company→margin mapping is IDENTITY — no company changed margin level in the migration. Estimate tier letters migrated (B→Builder-Dealer, same 25%).
**THE CUT (executed)**: all 31 LP rows × 4 tiers archived → `db.lp_legacy_price_archive` with provenance (hand-set values, derivation hypothesis, retired-at, reason); 104 legacy mat values zeroed in price_tiers (`retired_to_engine: true`); LP catalog mat resolves EXCLUSIVELY from the engine (mill basis on the catalog surface — finish keying on Phase 2 surfaces); pricing-admin refuses hand-edits to engine-priced LP mat (`refused` list in response); the `, 0` unpriced fall-through in estimates.py died — missing/pending prices carry `pricing_pending: true`, never a silent $0. PENNY-PARITY PINNED: engine reproduces all 26×4 archived prices exactly (`test_lp_single_source_iter97.py`).
**COMPOSITION PIN (scope clarified by ruling)**: the derived takeoff never composes cross-domain lines; the 5 coil/flash-tape rows are EXPLICIT manual-add exceptions (flagged `cross_domain_manual_add`, vinyl-domain price, exempt by name). **Iter 68 ".019 Coil" LP auto-add: RETIRED** (an auto-add is derived composition) — row remains in catalog for manual adds. Pinned in hover + lp_package tests.
**TEST FIXTURES (ruled)**: mixed quote = siding est 828b4957… + paired LP 3a7bc68c… (LP lines engine-priced 33.37 @whole-sale, no coil, no silent $0, "Soffit 16x16 Closed" properly pending-flagged). Legacy-LP-item quote = 1d913c95… (2026-07-06, stored prices retained — quote is a document, migration never touches estimate lines).
**LP-NATIVE DEMO MODE (built)**: admin toggle (Branding Admin card + `GET/PUT /api/admin/lp-native-mode`); when ON: catalog payload filtered server-side to LP-domain sections (leak-scan verified: only LP + shared-service sections), pickers/dashboards redirect to /dashboard/lp_smart, Catalog page shows LP Smart tab only. Presentation-layer only; currently OFF — flip ON for the September demo. `lp_native_mode` exposed on GET /api/branding.
**Testing**: 844 pytest passed; frontend testing agent iteration_36: all flows pass. One flagged item is a FALSE POSITIVE pending Howard's confirmation: estimate editor "SELL (30% MARGIN)" is the CONTRACTOR'S OWN retail margin control (est.pricing_mode/margin_pct, default from Branding Admin) — not supplier margin, which is baked into the engine mat price. Reported, not changed.
**ARCHITECTURE PRINCIPLE (standing, ruled)**: DOMAIN SEPARATION TO FORKABILITY STANDARD — LP catalog, conventions, pricing engine, and templates must be extractable as a standalone product without surgery: module boundaries, no shared mutable state across domains, domain-tagged data. AUDIT AT PHASE 2 COMPLETION. Fork itself is a business-triggered future event (partnership/white-label/acquisition), executed as extraction — BACKLOG with trigger, do not build now.

## Iter 98 — RELABEL + MARGIN TIERS CARD + PHASE 2 MATERIAL LIST TAB (2026-07-13)
**RELABEL (ruled)**: contractor pricing control never says bare "margin". Toggle: "Margin of sale" / "Markup on cost"; suffixes state the formula ("% of your sale price kept as profit — your number (sale = cost ÷ (1 − %))" / markup ×(1+%)); summary: "Your price to homeowner ({pct}% {mode})". EN+ES. FORMULA REPORT: mode-dependent — pricing_mode "margin" → ÷(1−m), "markup" → ×(1+m); per-estimate default "margin", legacy estimates without the field compute as markup. Contractor-side pin: their control renders THEIR number only; supplier margin is baked into mat before it reaches them (leak-scan re-verified).
**LP MARGIN TIERS CARD (Branding Admin, approved)**: 4 editable percentages + per-tier company counts + per-quote tier picker (GET /api/admin/lp-estimates, 50 recent, kind lp_smart OR tier-set). Admin boundary absolute. Margin dashboard (cost-vs-sell per quote) deferred to admin polish per sequencing discretion.
**PHASE 2 — MATERIAL LIST TAB SHIPPED** (`LpMaterialListPanel.jsx`, renders on lp_smart tab of LP-kind estimates):
- AI-derived package via redacted preview endpoint; PAIRED-RUN FALLBACK added (paired LP estimates read the siding source's run via paired_lp_estimate_id — backend `_load_run` + frontend).
- READ-ONLY until "Edit list"; substitutions table-limited (backend now attaches `substitutable_with` per line), re-derived server-side, provenance badges ("substituted from … — re-derived"), SESSION-ONLY (never remembered — ruled).
- Component-group ExpertFinish color selector (5 groups + apply-to-all), palette from GET /api/lp-package/colors (23 names); selections stored in est.lp_colors (EstimateIn model field added); per-line color chips; derivation provenance in a details drawer per line.
- 3D MESH-GROUP FLAT REPAINTS: HouseModel3D gained `lpGroupColors` prop — siding → wall meshes, opening_trim → trim meshes, hexes are visualization approximations (`lib/lpColors.js`); CORNER/FASCIA MESHES PENDING (flagged in UI, not faked).
- Sell prices ONLY; "pricing pending" badges (EF-unavailable soffit, service lines with no BlueLinx cost — gutter/misc pending is correct and expected).
**Testing**: 844 pytest; testing agent iteration_37 — 100% of items validated (substitution re-derivation 271.69→181.11 with qty change, EF repricing 30.99→46.49, no-mill-fallback pending, confidentiality clean, relabel confirmed, admin card verified). Hydration warning fixed (dev tagger wraps mixed text+expr in <option> — options now single template literals). Siding regression self-verified (no LP panel on vinyl estimates).
**NEXT**: forkability audit (Phase 2 surface shipped), then backlog: ExpertFinish availability matrix ingest, Letrick hand-takeoff, LP quote-PDF integration of the derived package (quote-freeze provenance), shareable Accuracy Report link, interactive 3D on Accept page, admin margin dashboard columns, window labor divergence, PWA icons, ISS New Construction.

## Iter 99 — MATERIAL LIST SURFACE CHECK: TRACE + ONE-SURFACE CUT (2026-07-13)
**TRACE (a)**: the pre-existing MATERIAL LIST button was LEGACY — `handlePrintMaterials` → `buildMaterialListHtml(est.lines)` client-side → WeasyPrint. Never touched the derived package. Confirmed two-surface disease.
**CUT (b, executed)**: LP-kind estimates with a derivable package now print EXCLUSIVELY from the derived package (`lib/lpMaterialList.js`, fed by the live panel package via `onPackage` — carries est.lp_colors + session substitutions). Legacy composer never renders for LP-with-run (verified: PDF payload contains "single source", legacy waste-composer absent, tab picker bypassed). Legacy composer retained ONLY for non-LP domains and LP-without-run (the only composition that exists there).
**CUT (c, partial — exports)**: CSV export for LP-kind derives the package server-side (`_derive_lp_pkg_for_export` + `_lp_csv_rows` in routes/estimates.py): "LP MATERIAL LIST — derived from AI measurements (run …) — single source" block, sell prices, substitution provenance in item names, "PRICING PENDING" never $0 (pinned in test_lp_single_source_iter97). Stored lp_smart rows are SKIPPED when the package derives. **Customer Quote still composes from est.lines — needs Howard's ruling** (see OPEN below). Print button prints the on-screen editor (panel shows package).
**$0.00 READBACK (EST-910869-L)**: honest empty state, root cause = pair-lp seeded 0 lines because AI-measured estimates keep measurements on the RUN, not est.hover_measurements. FIXED: pair-lp now falls back to the latest done run's measurements; EST-910869-L backfilled (23 lines, totals now real).
**OPEN RULINGS FLAGGED (do not decide silently)**:
1. Customer Quote (homeowner-facing) unification semantics: how do pricing-pending lines and service lines (gutter/misc — contractor's own labor pricing) appear on a homeowner quote composed from the package? And does the contractor keep qty-editing in the accordion or does the panel become the only line surface (its substitutions are session-only BY RULING — persistent edits would need a new ruling)?
2. TIER COHERENCE GAP (discovered): catalog/accordion prices LP at the COMPANY's tier (whole-sale → lap 33.37) while the package prices at the QUOTE's tier (Contractor → 30.99). When they differ, accordion totals ≠ Material List totals. Needs ruling: quote tier wins everywhere on LP estimates, or company tier is only the pre-quote default?
**Testing**: 845 pytest passed; button flow verified via Playwright (download + payload inspection); CSV verified via curl. Repaired a write-collision corruption in routes/estimates.py (duplicated tail block) during the work.

## Iter 100 — TIER COHERENCE + QUOTE COMPOSITION + FROZEN QR SHARE (2026-07-13, VERIFIED E2E)
**THREE RULINGS IMPLEMENTED & TESTED (backend curl + testing agent iteration_38 + self-test):**
1. **TIER COHERENCE (ruled: the estimate's tier wins on EVERY surface)**: PUT /api/admin/estimates/{id}/lp-pricing-tier reprices stored engine-priced LP lines; GET /api/catalog?estimate_id= prices LP at the estimate's tier; package preview/freeze/CSV already estimate-tier. VERIFIED with the 33.37/30.99 fixture (EST-910869-L): tier flip whole-sale↔Contractor moves preview, catalog-in-context, stored accordion lines, and CSV together — no two surfaces of one estimate render different tier bases. Company tier is only a seed default for NEW estimates.
2. **CUSTOMER QUOTE COMPOSITION (ruled: derived package + contractor service lines; pending = blank + qualifier, NEVER $0)**: `quoteEstimate` in EstimateEditor.jsx — the package governs EVERY line it derives (all sections incl. Seamless Gutter + Misc caps); stored lp_smart lines contribute only when the package doesn't track them (deduped by name incl. substituted_from — a stale stored price can never shadow pending truth). Pending lines: name + qty + "pricing to be confirmed" tag (QuoteModal data-testid quote-line-pending-*, emailQuote.js sectionBlock, EN+ES dict keys email.pricePending/email.pendingNote), footnote near Total (quote-pending-note), mat=0 so calcTotals excludes them. Verified: modal + intercepted PDF/email HTML both carry qualifiers + footnote, zero $0.00, total $16,004.39 excludes pending gutters.
3. **FROZEN QR SHARE (ruled: QR on a printout resolves to THAT exact printed version)**: MATERIAL LIST print → POST /api/estimates/{id}/lp-material-list/freeze (redacted snapshot + content_hash into db.lp_material_list_snapshots, 90-day expiry, urlsafe token) → QR (npm `qrcode` client-side) + share URL embedded in the printed PDF footer. Public page /m/{token} (`pages/MaterialListShare.jsx`, no auth): read-only frozen list, pending qualifiers, contractor-cost-redacted (leak-scan clean), amber "Updated list available" banner when live derivation's hash differs (frozen prices NEVER silently swap), revoke endpoint → error page, expired → 410.
**BUGS FIXED EN ROUTE**: (a) missing LP_SECTION_TITLES import in EstimateEditor (testing agent hotfixed, kept); (b) quoteEstimate stale-memo deps (isLpKind/lpPkg); (c) P0 composition bug — pending gutter/cap lines fell into serviceLines from est.lines, dropping the pending flag and leaking stale prices into the total (fixed by package-governs-derived-lines + name dedupe).
**Testing**: iteration_38 (frontend flows all pass after fixes), 21 LP pricing pins green, tier restored to Contractor on fixture.
**NEXT**: Forkability Audit (P1, unblocked) → ExpertFinish availability matrix ingest → Letrick hand-takeoff validation (Howard) → Accuracy Report share link → interactive 3D on Accept page → window labor divergence → upgrade/option quote lines → PWA icons → ISS New Construction catalog. Post-Sept backlog: persistent line substitutions (needs ruling), per-contractor pricing.

## Iter 101 — PHASE 3 HARNESS: LETRICK HAND-TAKEOFF vs SEALED KEY (2026-07-13, REPORT FILED — AWAITING RULING)
**Howard's sealed blind answer key entered as Phase 3 ground truth** (`/app/backend/letrick_hand_takeoff_key.py`; placeholder backed up per backup-first rule at `/app/memory/backups/letrick_hand_takeoff_placeholder_pre-supersede_2026-07-13.json`). One run fired (EST-191890, run ed613872, valid/done), code frozen during the run, artifact frozen at `/app/memory/letrick_phase3_run_ed613872.json`.
**REPORT** (`/app/memory/letrick_phase3_hand_takeoff_report.md`): 3 pass · 5 fail. PASS: starter (168 vs 165 LF, +1.8%; boards 4=4), soffit (match-on-basis: eaves-only 108 LF both), COMPOSITION (zero J-channel/finish trim/coil derived). FAIL: lap 220 vs 255 (−13.7%, cause = area input gap 1,832.7 vs 2,098.5 sqft incl. chase; conventions residual −1.2% inside tolerance), OSC 7 vs 8 (corner-location inventory incl. chimney above-roofline edges + 1 amber), ISC 3 vs 2 (extra amber location), 540 trim 11 vs 12 (both doors classified entry vs entry+patio, 1 LF flips a stick at the exact 11.0 boundary), fascia 13 vs 12 (flip cause = 10% waste cushion on trim vs key's splice-and-round-no-cushion; rake LF 73.4 vs 69.6 secondary). Dominant failure class = upstream inputs/inventory, one pure conventions divergence (trim waste cushion). **Phase 4 flag-flip NOT executed — gated on Howard's ruling.**
**QR "Request updated list" SHIPPED (approved, owner-only scope)**: POST /api/public/lp-material-list/{token}/request-update — emails the estimate's company OWNER only, version context attached (printed date, drift status), 15-min throttle, 404 bad/revoked token; button renders inside the drift banner on /m/{token} with sent/failed states. Verified: curl (ok/throttled/404) + browser under real drift (banner+button+sent state, frozen prices unchanged); fixture tier restored to Contractor.

## Iter 101b — PHASE 3 RE-FILED (v2) AFTER PROVENANCE REJECTION (2026-07-13)
v1 rejected: it consumed run ed613872 (7-11 C3 corner run), not a fresh extraction. **Fresh run fired:** 5005d6eb (2026-07-13 18:24 UTC, done; measurement hash cb819d0f92fa2151, package hash 53a0bf46e993d719; artifact letrick_phase3_run_5005d6eb.json). **Two-layer scoring** (letrick_phase3_hand_takeoff_report_v2.md): LAYER B (engine run read-only on the KEY's geometry — script at letrick_phase3_layer_b_script.py): **5 conventions PASS** (lap 252 vs 255 −1.2%; ISC 2=2; 540 trim 12=12; soffit; starter 4=4 boards) · **2 conventions FAIL** (OSC 9 vs 8: per-location whole-stick presence guarantee vs key's pooled chimney ceil(55/16)=4; fascia 13 vs 12: 10% waste cushion vs splice-and-round-no-cushion). LAYER A (extraction): area −19.6% (decomposed: gable factor ~0.51 vs key 0.7 ≈ −97.5; chase faces up to −145.5; stepped sides −168.3 — sums exactly to −411.3), windows 9 vs 10, back patio slider classified entry_door 36×80 (3-side applied by both; delta is class wrap 18' vs 19'), 2 above-roofline chimney edges undetected, start-course 178 vs 168/165, run-to-run extraction variance −7.9% between identical-photo runs. ISC scored reconciled-to-residual per ruling (2=2, amber pair provenance-limited). Combined: 3 pass · 4 fail · 1 split (starter LF fail/boards pass) · composition clean. **Phase 4 still gated on Howard's ruling.** Field-verify amber checklist approved-in-principle, ships AFTER ruling.

## Iter 102 — C4: COMPOSITION CONFORMANCE SHIPPED + E2E RE-RUN (2026-07-13)
**Pre-C4 question answered:** runs extract ONE consensus height per wall (no stepped segments) → stepped underread = extraction residual (ambers). Chase IS perceived via wall accent_profiles (approx_sqft) without attribution → fix viable.
**Five fixes shipped (all ruled conventions):** (1) gable ×0.7 replacing ÷2 (ai_measure.py); (2) appendage faces (chase/chimney/bump/cantilever accent profiles) attributed to siding area, exposed as _ai_appendage_sqft/_ai_appendage_faces; (3) OSC FEATURE POOLING (lp_package.py): singleton corners 1 stick ≤16', appendage edges pool internally (full sticks >16' + ceil(pooled remainders/16)); per-location stick-starts REJECTED doctrine; chimney fixture 2×18.91+2×8.59=4 pinned; six-ruling splice example (2×18.5'→3) preserved; (4) WASTE SCOPE: % waste on AREA lines only (lap, soffit); stick-count lines get whole-stick rounding as entire allowance — ×1.10 removed from fascia + substitution path (lp_conventions.py); (5) STARTER deducts entry-class door widths (schedule widths, 3' fallback), sliders sit on starter.
**Pass criteria:** LAYER B on key geometry 9/9 within ±3% (OSC 8=8, fascia 12=12, starter 165→4 exact). E2E re-run 4a009e93 (19:13 UTC, meas hash 79c52e6f, pkg hash e26b1c00): lap 258 vs 255 = +1.2% PASS (was −20.4%), fascia 12=12, starter 162/-1.8%, ISC 2=2; remaining fails OSC 6 vs 8 and trim 11 vs 12 = extraction inventory only (windows 9 vs 10, slider→entry class, above-roofline chimney edges undetected). Red-house regression: full suite 854 passed incl. roof/tape/gable fixtures; superseded pins updated with provenance (iter93/iter94).
**September numbers (never blended):** conventions-on-verified-geometry 9/9 ±3%; e2e photos-to-order 6/8 with ambers doing safety.
**Gate:** Phase 4 flag-flip awaits Howard's C4 ruling; amber field-verify checklist ships immediately after.
Report: /app/memory/letrick_phase3_c4_report.md

## Iter 103 — PHASE 4 FLAG-FLIP + AMBER FIELD-VERIFY CHECKLIST (2026-07-13)
**PHASE 4 EXECUTED (C4 ruled PASS):** LP_AI_FORMULAS_V1=1 in backend/.env — LP-native package is the production composition path. Milestone logged in lp_conventions.MILESTONES["phase4_flag_flip"] with BOTH September numbers as ruled (conventions-on-verified-geometry 9/9 ±3%; e2e photos-to-order 6/8 with ambers; NEVER blended). letrick_hand_takeoff removed from PENDING_CONFIRMATIONS (resolved); pin updated. Full suite 846 green with flag ON.
**AMBER FIELD-VERIFY CHECKLIST SHIPPED:** presence-guarantee doctrine surfaced. Backend: preview response gains amber_items (unconfirmed corner locations w/ kind/locator/status merged from estimate.lp_field_verify); POST /api/estimates/{id}/lp-field-verify {key,status} persists ratification (by/at) or reverts ($unset). Frontend: amber card in LpMaterialListPanel (data-testids lp-field-verify-card, lp-fv-item-*, lp-fv-verify-*, lp-fv-verified-*), EN/ES dict keys lp.fv.*. Ratification only — counts never change. Verified: curl round-trip + browser click-verify-revert on EST-910869-L (4 ambers).
**NEXT (ruled sequence):** confirm-openings review step (approved: one-tap photo-crop confirmation, per-opening provenance user_confirmed/user_corrected promoting to verified standing, skippable w/ persisting unconfirmed flags, same design language as field-verify) → Forkability Audit → ExpertFinish matrix.

## Iter 104 — CONFIRM-OPENINGS REVIEW + VERIFICATION TRAIL (2026-07-13, TESTED 8/8)
**CONFIRM-OPENINGS (approved spec implemented):** pre-derivation ratification of AI-detected openings. Backend (lp_package_routes.py): _openings_items (run-scoped keys open:{run8}:{idx} — new run resets review; photo_url from photo_paths idx; bbox passthrough null-ready), _apply_openings_review (user_corrected type shifts window/entry/patio/garage counts with provenance notes; ratification never changes counts), POST /api/estimates/{id}/openings-review {key, action confirm|correct|reset, corrected_type}; corrections applied on EVERY derivation surface (preview, cost-preview, freeze/_derive_current) but review payload attaches ONLY to contractor preview (public purity). Frontend: OpeningsReviewCard.jsx (photo thumbnails, confirm/wrong-type/reset, collapsible=skippable, EN/ES lp.or.* keys), wired in LpMaterialListPanel above the table; onChanged refetches. VERIFIED: correction Cap window 18→17 + Cap patio 2→3, reset restores; testing agent iteration_39 8/8 PASS.
**VERIFICATION TRAIL (approved):** printed material list gains an honest trail block (lpMaterialList.js): amber X/N field-verified with verifier names + UNVERIFIED locators listed; openings X/N reviewed with UNCONFIRMED count; partial always shown as partial; contractor surface ONLY (public /m/ page verified clean of trail/amber/openings data).
**Post-test fixes:** failure toasts added to both ratification handlers (openings + field-verify). The 'gable-area consistency FAILED' console error = pre-existing intentional ridge-orientation honesty check (UI banner exists) — left as designed.
**NEXT (ruled sequence): Forkability Audit → ExpertFinish matrix.**

## Iter 105 — FORKABILITY AUDIT (2026-07-13, REPORT FILED)
VERDICT: FORKABLE. One-way dependency (app → LP), LP core modules import zero infrastructure; no cross-domain mutable state (single bridge = immutable frozenset CROSS_DOMAIN_MANUAL_ADD_EXCEPTIONS, explicit contract; single intra-LP mutable = documented _OVERRIDE_FLAG); all data domain-tagged (lp_ collections, lp_ settings ids, lp_ estimate fields, tab=lp_smart lines, SECTION_PRODUCT_LINES exclusive LP sections); templates self-contained (lpMaterialList.js zero imports). ONE CARVE-OUT: routes/hover.py _build_lines has ~95 interleaved LP touchpoints → extract lp_ingest.py at fork time (non-blocking, contained, one-way). Five thin seams enumerated (catalog, estimates, pricing_admin, hover, dictionaries lp.* prefix). 9 portable test_lp_* pin files. Report: /app/memory/forkability_audit_2026-07-13.md.
NEXT: ExpertFinish availability matrix ingest (needs LP's published color-by-product-line matrix — flag unsupported combinations; BlueLinx sheet = stocking overlay when it lands).

## Iter 106 — DOMAIN MANIFEST + CI DRIFT CHECK + EXPERTFINISH MATRIX (2026-07-13)
**DOMAIN MANIFEST (approved w/ CI requirement):** lp_domain_manifest.py (8 core modules, 2 routers, 4 seams + hover S4, migrations, frontend files, data-tag contract, env flags, KNOWN_DEBT_IMPORTS). CI drift check tests/test_fork_boundary.py — build FAILS on: LP core importing outside stdlib+intra-LP (single pinned debt edge lp_package→routes.hover), unenumerated lp_* imports, untagged collections in LP routers, non-lp_ $set/$unset fields on db.estimates (documented exception: "lines" — LP members tab-tagged). **THE CHECK IMMEDIATELY CAUGHT A REAL VIOLATION the audit missed:** lp_package imported catalog_seed for SKU tables → FIXED by inverting: LP_TRIM_SKUS/LP_OSC_SKUS now single-sourced in lp_conventions, catalog_seed imports them (legal app→LP direction).
**EXPERTFINISH MATRIX (publish-first per ruling):** lp_expertfinish_matrix.py ingested from lpcorp.com published sources 2026-07-13 — lap/trim: all 16 core (trim: standard-sizes qualifier); 12"/16" soffit: Snowscape White ONLY; 24" soffit: 4 colors; panel: Snowscape+Abyss published, Garden Sage ambiguous→gap; shakes: 3 colors regional→gap; vertical: core16 regional→gap; Naturals: per-product availability unpublished→gap everywhere; Primed: always. check_combo → available|unsupported|gap; apply_colors sets color_status + color_flags (UNSUPPORTED COMBINATION / AVAILABILITY GAP) — color kept as requested, NEVER substituted. Flags render on the panel lines, printed list, and frozen share page. Howard to verify against dealer reality + BlueLinx sheet — gaps only filled by him. 12 new pins (matrix + boundary); suite 858 green.
**INCIDENT (logged honestly):** while testing the flag UI, agent used PUT /api/estimates/{id} with a partial body — that endpoint is FULL-REPLACE and wiped fixture EST-910869-L (kind/lines/number). RESTORED via targeted Mongo $set + backfill_iter99 (23 lines) + tier-coherence reprice (Contractor, 30.99 verified). CAUTION FOR FUTURE AGENTS: never PUT partial estimate bodies; use targeted Mongo updates or dedicated endpoints. Consider a PATCH/merge endpoint as future hardening.

## Iter 107 — PATCH MERGE HARDENING + COLOR BADGING (2026-07-13, prev session)
PATCH /api/estimates/{est_id} shipped as the merge endpoint for partial updates (the PUT full-replace footgun is closed); frontend API calls migrated. Color-picker availability badging in LpMaterialListPanel (⛔ unsupported / ⚑ gap, combos stay selectable — matrix informs, never forbids). Tested; user accepted.

## Iter 108 — MATRIX DEALER-VERIFIED + ACCURACY SHARE LINK + PWA ICONS + QUOTE UPGRADE LINES (2026-07-13)
**STATE CORRECTION then RESOLUTION (same day):** Howard first ruled the matrix NOT closed (6 open items pinned as VERIFICATION_PENDING), then delivered full dealer verification. lp_expertfinish_matrix.py is now DEALER-TRUE (MATRIX_STATUS "dealer-verified... available = orderable"): Garden Sage available on panels; shakes + vertical all 16 core colors all regions (regional gaps cleared); trim all colors in all quoted profiles; BlueLinx = no published-but-not-stocked entries; stocked-vs-published = ONE amber vocabulary (no special-order badge). **Naturals scoped to EXACTLY 11 profiles** (NATURALS_PROFILES verbatim list: 38 Lap 8", Nickel Gap, 190 3", 440 4/4×4+6, 540 5/4×4+6+8+12, 38 Soffit 16x16 Closed, 38 Vertical Panel); outside the list → unsupported; starter follows lap stock. **CATALOG CROSS-CHECK (ruled):** all Naturals profiles quotable EXCEPT `38 Series Soffit 16 x 16 Closed` — dropped Iter 78x (Feb 2026 supplier sheet), flagged NATURALS_CATALOG_PENDING → check_combo returns gap "catalog: pending", never silently missing. REPORTED TO HOWARD — needs his call whether to re-add the SKU. Picker warning text updated to dealer-true vocabulary. 24 matrix pins rewritten; fork boundary green.
**(a) ACCURACY REPORT SHARE LINK (/m/ doctrine reused as /r/):** _accuracy_report_data extracted as the shared builder in routes/estimates.py (framing pins intact in-source); POST /api/estimates/{id}/accuracy-report/freeze → frozen VERBATIM report HTML + content_hash(history+held_out) into db.accuracy_report_snapshots, token, 90-day expiry; GET /api/public/accuracy-report/{token} (newer_available flag when new runs scored — frozen html never swaps; 410 expired; 404 revoked); POST .../revoke. Frontend /r/:token → AccuracyReportShare.jsx (iframe srcDoc sandbox, frozen badge, amber newer-runs banner; testids accuracy-share-*). "Share link" button in TapeCheckPanel (tape-check-share-report) freezes + copies link. tests/test_accuracy_report_share.py 6 pins (framing verbatim in shared view, no silent swap, revoke).
**(e) REAL PWA ICONS:** generated brand icon (orange lap-siding house + ruler ticks on #09090B, maskable-safe) → icons/icon-512, icon-192, apple-touch-icon.png, favicon.ico; index.html links added.
**(d) UPGRADE/OPTION QUOTE LINES (Howard ruled scope b):** per-line adders render as indented sub-lines (name + × qty ONLY — no unit prices, standing doctrine) under their parent in emailQuote.js (adderRows) + QuoteModal preview (quote-adder-*); window openings (vero_openings + mezzo_openings) itemize in a "Windows"/"Ventanas" section (windowsBlock; quote-windows-openings, quote-opening-adder-*) instead of dissolving into the total; carries to email + PDF + accept page automatically (all consume buildEmailHtml). quoteEstimate tab filter scopes openings like calcTotals (vero→windows, mezzo→mezzo); tabsWithData counts openings. Option (c) "Options & Upgrades menu of unselected add-ons" DEFERRED post-September by ruling. Demo fixture kept for Howard: estimate "Adder Demo" c898dbab-c8f0-416b-988f-50f5c1fb3d84.
**Testing:** iteration_40 — backend 100%, frontend 95% (all pass; only note: TapeCheckPanel mounts inside HouseModel3D so the Share button needs a 3D model present — pre-existing gating, endpoint proven regardless). PDF via WeasyPrint OK with new HTML; ES toggle OK; PWA assets 200.
**NEXT (held by Howard):** (b) interactive 3D on Accept page · (c) window-labor divergence from ISS · (f) ISS New Construction catalog. Post-Sept: bbox crops on confirm-openings, persistent substitutions, options menu ruling, lp_ingest.py extraction at fork time. OPEN for Howard: re-add 16x16 Closed soffit SKU for Naturals or leave catalog-pending?

## Iter 109 — SOFFIT SKU RE-ADD (RULED) + ACCURACY PDF QR (2026-07-13)
**16x16 CLOSED SOFFIT RE-ADDED (Howard's ruling: dealer verification supersedes Feb 2026 sheet drop):** '38 Series Soffit 16 x 16 Closed' back in catalog_seed SECTION_LAYOUT (LP SmartSide Soffit) + ITEM_META (PCS); REMOVED from services.py LP_DROP_NAMES_78X (else stripped each boot); prices EXCLUSIVELY via BlueLinx engine (lp_costs BLUELINX_COSTS PIT00003 2.26.2026: mill 51.45 → e.g. 79.15 whole-sale) — the archived February list price NEVER revived (SKU stays OUT of catalog_seed LP_COSTS/TIER_PRICES; pinned in test_soffit_16x16_closed_readded_bluelinx_only). Verified live on all 4 tiers via catalog API after seed-sync rebuild. Matrix: NATURALS_CATALOG_PENDING now EMPTY → Naturals on 16x16 Closed plainly available (pin updated). test_lp_catalog DROPPED_LP_SKUS reduced to 3.
**ACCURACY PDF QR (approved, /m/ doctrine):** every printed accuracy PDF now mints a frozen /r/ snapshot (_freeze_accuracy_snapshot shared with the freeze endpoint) and carries a QR footer: purpose note "Scan for the verifiable version of this report" (supplier-audience provability), frozen-date + never-silently-changes doctrine line, share URL, 90-day validity. Server-side python `qrcode` lib (added to requirements) as data-URI PNG through the safe WeasyPrint fetcher. Origin via x-forwarded-proto/host (internal-ingress-host bug caught+fixed in verification — embedded URL confirmed public https and publicly resolving). Pin: test_report_pdf_embeds_frozen_qr.
**Testing:** full suite 870 passed / 1 skipped; share suite 7/7.
**HELD BY HOWARD:** (b) interactive 3D Accept page, (c) window-labor divergence, (f) ISS New Construction — all held; next block goes to DEMO-PREP direction (awaiting his brief).

## Iter 110 — DEMO RESET (2026-07-13, ruled + promoted)
`POST /api/demo/reset` (routes/demo.py) + "Reset demo" button on the LP dashboard (demo-reset-btn). Idempotent wipe-and-rebuild of ONE flagged estimate (demo_key "letrick_demo", number DEMO-LETRICK): clones the frozen post-C4 Letrick run 4a009e93 read-only → fixed run_id "demo-letrick-4a009e93"; copies Letrick taped truths and re-scores (92.6%, 1 history entry, held_out false → methodology-exhibit framing); seeds 21 stored lines via the pair-lp path (_build_lines + catalog at tier Contractor, mat AND lab from catalog so no sync-banner noise — gutter/downspout lab 1.0 caught in verification); lp_colors palette (siding/OSC/ISC Quarry Gray, soffit+trim Snowscape White, all matrix-clean); mints frozen /m/ + /r/ QR links; forces lp_native_mode ON; staged readout persisted as est.demo_staged. SPECIFIED STATE: 1 amber unratified (ISC "chimney chase left edge meets back wall"), openings review 10/10 unconfirmed, 4 substitutable lines (440 4/4x4, 540 OSC 5/4x6, 440 4/4x8, LP Starter), 22 package lines, $11,095.70 stored material. HARD ISOLATION: gated to fixture-owner company (403 otherwise); wipe scoped to the flagged demo doc + its runs/snapshots; pinned byte-identical source fixture in tests/test_demo_reset.py (also pins idempotency, no orphans, public link resolution). NOTE: reset revokes prior demo QR printouts (snapshots deleted) by design.
**Testing:** test_demo_reset.py green; fork boundary green; UI click-through verified (button → staged estimate, $11,095.70 header, field-verify + tape panels present, no sync banner).
**NEXT:** standing by for Howard's demo-prep direction (walkthrough script, further staging, or polish).

## Iter 110b — RESET CONFIRMATION QR WARNING (2026-07-14, ruled addition)
GET /api/demo/status preflight (counts non-revoked /m/ + /r/ snapshots on the flagged demo estimate). Reset button now opens an AlertDialog (demo-reset-confirm) before acting; when qr_tokens > 0 it shows the amber footgun warning "Resetting revokes N previously printed QR links — reprint after reset" (demo-reset-qr-warning). Verified E2E: warning showed "2 previously printed QR links", confirm proceeded to a fresh staged estimate, cancel path intact. Demo infrastructure COMPLETE per Howard; standing by for demo-script support items from choreography.

## Iter 111 — FAILURE CLASS 5 (WORKER LIFECYCLE) + MODEL ANCHOR INTEGRITY (2026-07-14)
**STANDING OPERATIONAL RULE (Howard, logged):** production runs and agent build-sessions NEVER overlap. Agent side: before ANY backend restart/hot-reload-triggering edit, check `GET /api/measure/ai-measure/in-flight` — refuse or warn, never silently kill. Howard's side: no live runs mid-task.
**Live failure (EST-657226 vinyl run):** hot-reload killed the reconcile asyncio task after 8/8 Phase A photos. Logged as failure class 5 (worker lifecycle), distinct from the 4 empty-extraction classes (null-response, parse break, truncation, refusal).
**Hardening shipped (P0):** (1) `_handle_dead_worker` — dead runs with persisted `raw_per_photo` AUTO-RESUME reconcile-only (atomic claim, cap 1/run, `lifecycle_resume_attempts`, `failure_class: 5`, `lifecycle_last_death` breadcrumb); no Phase A / cap hit → flip to class-5 error with honest recovery text ("Retry reconciliation" when Phase A saved vs "Retry Run" when not). (2) Stale-worker detector (threshold pin `max(60, 2×per_wave_budget_s)` unchanged) now routes through the handler. (3) STARTUP SWEEP in `run_startup` — every boot recovers `status=running` orphans without anyone polling (platform restarts/idle recycling covered). (4) Operator preflight `GET /measure/ai-measure/in-flight` → `{count, runs, restart_safe}` (admins all, users own). Pins: `tests/test_worker_lifecycle_class5.py` (8) + legacy detector suite updated (class-5 text/fields).
**Stale label audit:** AI Photo Measure header said "Claude Opus 4.5" while runs are Fable 5 → header now renders the ACTIVE model dynamically. BlueprintMeasureButton's "Opus 4.5" labels are ACCURATE (blueprint pipeline genuinely pins `claude-opus-4-5-20251101`) — left as-is. No other stale surfaces found.
**Model dropdown policy (resolved per ruling):** it allowed 8 models (Opus 4.5/4.8, Sonnet 4.6, Fable 5, Gemini 3.5 Flash/3.1 Pro, GPT-5.5/5.4) to ANY user, localStorage-persisted, driving BOTH phases + rerun per-phase A/B overrides; stale default was opus-4-5. Now: `_DEFAULT_MODEL_KEY = claude-fable-5`; `_VALIDATED_MODEL_KEYS = {claude-fable-5}`; non-admin choices CLAMP server-side (recorded as `model_choice_clamped_from`, never silent); per-phase bake-off overrides admin-only; frontend shows locked "Claude Fable 5" label to non-admins (owner/supplier_admin/admin keep the full picker, validated option marked ✓).
**Regression caught & fixed during verification:** demo reset's global `lp_native_mode` flip was stripping vinyl/ascend catalogs for EVERY contractor (isolation violation). Reset no longer mutates the global switch (readout reports current state); setting restored OFF; test updated. Flip native mode from the LP admin panel for demo day.
**Testing:** full suite 879 passed / 1 skipped.

## Iter 112 — BLUEPRINT PIN PROVENANCE + ZERO-GLOBAL-STATE PIN + FIXTURE DATA-LOSS RESPONSE (2026-07-14)
**Blueprint model-pin audit (ruled follow-up):** VERDICT — NOT deliberate. `claude-opus-4-5-20251101` was INHERITED from AI-measure's then-default at feature birth (git 2026-06-18); no bake-off, no ruling, no hash stamping existed. Flagged in code (`MODEL_VALIDATION_STATUS = "inherited-default — validated-model decision pending"` + PROVENANCE FLAG comment); blueprint runs now stamp `model_config` {model, validation_status, prompt_hash} so the future validated-model decision has scoreable provenance. Pins: tests/test_blueprint_model_provenance.py. **OPEN DECISION for Howard: blueprint validated-model ruling.**
**Zero-global-state pin (ruled):** test_demo_reset_mutates_zero_global_state — settings/companies/price_tiers snapshots byte-identical across reset; the lp_native_mode violation class cannot return.
**DATA FINDING (needs Howard's confirmation):** since last session the DB lost estimates INCLUDING the Letrick source fixture EST-191890 (c864939b) and the live vinyl run EST-657226 — the frozen run doc 4a009e93 SURVIVES (runs collection untouched). Looks like manual dashboard deletion; env also recycled mid-edit (2 files corrupted+repaired: demo.py, test_demo_reset.py). Response: demo reset made SELF-CONTAINED — Letrick tape truths frozen into code (LETRICK_TAPE_WALLS), isolation gate now via frozen-run owner's company (no dependency on deletable estimates); 1c PDF pin (test_count_tiering_iter84) repointed to a self-provisioned clone fixture. Demo-day is safe regardless of dashboard state.
**Testing:** full suite green except transient rate-limiter flakes under full-suite login pressure (test_security_p3 passes standalone 10/10); targeted re-runs 44/44 + 14/14.
**Demo-day runbook (Howard's side, logged):** flip LP-native mode from admin panel that morning; print QR leave-behinds AFTER the final reset.
**NEXT:** demo-script work (Howard's direction to follow). OPEN: blueprint validated-model decision; confirm EST-191890/EST-657226 deletions were intentional.

## Iter 113 — DELETE GUARD + SOFT-DELETE RETENTION (2026-07-14, ruled after accidental deletions)
Deletions confirmed ACCIDENTAL by Howard (investigation closed). Shipped: (1) **Delete guard** — `GET /estimates/{id}/delete-preflight` names linkages (dedicated demo fixture / N frozen AI measure runs / N blueprint runs / N scored tape-check entries / N live share-QR links that will dead-end); Dashboard delete now preflights and, when linked, opens an AlertDialog listing every linkage (delete-guard-dialog / -warnings / -cancel / -confirm testids) — same doctrine as the QR-revocation warning; unlinked estimates keep the plain confirm. (2) **ANSWER TO "soft or hard?": it WAS hard (delete_one, zero undo).** Now SOFT: `DELETE /estimates/{id}` moves the doc to `estimates_trash` (deleted_at Date + deleted_by) with a **30-day TTL retention** (startup _ensure_ttl); `POST /estimates/trash/{id}/restore` restores (409 if id exists, 404 past window); delete toast carries a 10s **Undo** action. (3) **TTL landmine defused:** the frozen Letrick source run 4a009e93 sat under the ai_measure_runs 30-day TTL (would expire ~Aug 12 — BEFORE the September demo); demo reset now archives it into `fixture_runs` (no TTL) on first touch and prefers the archived copy. Pins: tests/test_estimate_delete_guard.py (6: preflight unlinked/linked/demo-flag, soft-delete+restore round-trip, 30d TTL index, fixture archive). E2E verified: guard dialog names all 4 linkages on DEMO-LETRICK, cancel preserves.
**Blueprint validated-model decision: DEFERRED as ruled.** NEXT: demo-script support standby.

## Iter 114 — 3D CHIMNEY CHASE RENDERING (2026-07-14, ruled scope)
Appendage objects (chimney chases / bump-outs) now render on the 3D house model, mapped PURELY from the run's existing payloads — C4 attributed faces (`raw_ai.walls[].accent_profiles`, keyword rule mirrors backend verbatim: chase/chimney/bump/cantilever) give wall + attributed ft²; C3 `raw_ai.corner_locations` give position_frac and width (corner-frac spread × wall length — Letrick: 0.30–0.42 × 50′ = 6.0′ measured width @ 36% along back wall). NO detection logic on the frontend; NEVER fixture constants. All in `HouseModel3D.jsx` (`deriveAppendages` + buildScene box render + tap-panel section).
**HARD PIN (Howard-ruled):** defaulted dimensions (depth ~2′, above-roofline height, fallback width 3′) are RENDER-ONLY — they position the 3D box and NOTHING else; they never enter area math, material lines, or pricing. Takeoff contribution stays the server-side AI-attributed approx_sqft. Tap-panel names each dimension's provenance ("6.0 ft — from chase corners" vs "~2 ft — assumed, not measured") + explicit pin note (ai-measure-3d-appendage-pin-note).
**Honesty treatment:** amber translucent box + amber outline while ANY chase corner is unconfirmed and un-ratified (reads `estimate.lp_field_verify` via the same `corner:{osc|isc}:{slug}` key derivation as backend `_amber_items`); snaps to solid siding + dark trim outline + green "Verified" chip once every corner is confirmed (2+ photos) or field-verified. "extends above ridge" in the AI photo note draws the box past the ridge (drawn height still flagged assumed). Boxes are top-level scene groups → exempt from the bbox envelope check by construction (no false "geometry extends outside envelope" banners).
**E2E verified on live Letrick data (demo estimate untouched — verify flags reverted after test):** amber chase above ridge on back wall → POST lp-field-verify ×2 chase corners → box snaps solid + chip flips VERIFIED → reverted. Panel totals byte-identical throughout ($14,651.13) — zero math impact confirmed.
**NEXT:** Howard's demo-script direction; held items (interactive 3D Accept page, window-labor divergence, ISS New Construction) still gated.

## Iter 115 — TTL AUDIT DELIVERED + QUOTE-PDF 3D SNAPSHOT WORDING SPLIT (2026-07-14)
**TTL audit (was dropped from Iter 113 scope — now delivered):** `/app/memory/ttl_audit_report.md`, live-inspected against the running DB. Mongo TTLs: ai_measure_runs 30d, ai_blueprint_runs 24h, estimates_trash 30d, hover_import_runs 24h, hover_page_cache 1h. App-level expiry (no Mongo TTL — docs persist, routes 410/404): /r/ + /m/ QR snapshots at created+90d (current demo tokens expire 2026-10-12). No-TTL permanents: fixture_runs (frozen Letrick archive verified present), upload_blobs, estimates, tape histories. September verdict: demo chain TTL-safe by construction (fixture archive + reset-morning re-clone restarts the demo run's 30d clock; final QR leave-behinds printed post-reset live to ~mid-Dec). **OPEN DECISIONS surfaced to Howard:** (3) estimates outlive their 30d runs — LP panel/3D/openings-review degrade to "No completed run" on old customer estimates while stored lines survive; ruling wanted on archival/extension. (5) upload_blobs unbounded — post-demo hygiene item.
**Quote-PDF 3D snapshot (approved w/ audience wording):** snapshot already captures the chase in its TRUE state (in-canvas). New: capture passes `unverified` (any appendage unratified) → PUT /model3d-snapshot persists `model3d_unverified` → customer surfaces footnote in HOMEOWNER language only — EN "Some details are subject to on-site verification." / ES "Algunos detalles están sujetos a verificación en el sitio." (email/PDF builder emailQuote.js via `email.model3dVerifyNote`, QuoteModal preview mirror `quote-3d-verify-note`). Contractor surfaces keep precise internal language as-is.
**WORDING SPLIT PINNED:** tests/test_model3d_wording_split.py (5) — flag persist/reset via API; emailQuote.js + all `email.*` dictionary strings + QuoteModal 3D block contain ZERO internal vocab (amber/unconfirmed/field-verify/unratified); HouseModel3D contractor panel MUST keep "Unconfirmed"/"field-verify"/"assumed, not measured" (pinned so a future softening pass can't erase contractor precision). E2E verified: footnote renders on the live quote preview; throwaway estimate cleaned up.
**NEXT:** script-standby resumes. OPEN for Howard: 30d run-TTL vs estimate lifetime ruling; blueprint validated-model ruling (still deferred).

## Iter 116 — RUN-ARCHIVAL ON PERSISTENT ARTIFACTS (2026-07-14, Howard-ruled) + AUTOFILL SUPPRESSION POLISH
**Run-TTL ruling implemented (widened trigger):** any event embedding a run's data in a persistent artifact archives that run into `fixture_runs` (no TTL) — quote-send (routes/email.py), /m/ freeze (exact run_id), /r/ freeze. Material-order send endpoint doesn't exist yet — run_archive.py docstring pins it MUST call archive_run_for_artifact when it ships. Unreferenced runs keep the 30d TTL (hygiene). Module: `/app/backend/run_archive.py` (idempotent upsert + artifact_reasons audit trail; never raises — artifact creation can't fail on archival). READ PATH: `lp_package_routes._load_run` falls back to fixture_runs so November callbacks keep their Material List panel + 3D after ai_measure_runs reaps. BACKFILL (every boot, idempotent): sent quotes (status_label/last_sent_at) + live /m/ (snapshot.run_id) + live /r/ freezes.
**PIN:** tests/test_run_archive.py (5) — m-freeze archives exact run AND panel survives simulated reaping (fixture fallback E2E); r-freeze archives; quote-send trigger source-pinned (real email off-limits in tests); backfill archives referenced + SKIPS unreferenced (no blanket archival); helper idempotent (1 doc, deduped reasons). Gotcha fixed: docs cloned FROM fixture_runs carry artifact_reasons → $set/$addToSet path conflict → helper strips before upsert. LP-package/accuracy regression: 34 green.
**Autofill suppression (best-effort polish, ruled low-priority):** customer-info fields (name/company/title, phones/fax, email, job + billing address) in JobInfoPanel (15 fields) + ISS editor (4 fields) now carry `{...NO_AUTOFILL}` from `/app/frontend/src/lib/noAutofill.js`: unknown-token `autocomplete="off-homeowner-data"` (Chrome/Edge treat unknown tokens as no-autofill-category; plain "off" is ignored for address heuristics) + `aria-autocomplete="none"` (Edge 105+). The `list`→missing-datalist trick deliberately REJECTED (remaps role to combobox — WCAG AA violation). Verified live on all 4 field classes. NOT pinned behavior by design — browsers honor inconsistently.
**upload_blobs policy:** BACKLOGGED post-September as ruled (sketch: blobs referenced by archived runs retained; orphans past window reaped).
**NEXT:** script-standby. DEFERRED: blueprint validated-model ruling.

## Iter 117 — CUSTOMER-JOURNEY EVENT INSTRUMENTATION (2026-07-14, split ruling)
**Ruling:** events captured NOW (uncaptured events unrecoverable); the contractor-facing timeline SURFACE is post-September backlog with an OPEN DESIGN RULING attached — no customer surface may reveal the tracking's existence, and contractor-visible granularity (counts vs timestamps) gets ruled when the surface is designed.
**Implemented:** `/app/backend/estimate_events.py::log_estimate_event` — appends to the estimate's EXISTING `tracking[]` array (same record Resend email.opened/clicked webhooks already join), capped at last 500 events ($slice — hot QR can't bloat the doc), never fails the serving request. Events wired at existing endpoints: `quote.sent` (email_quote, w/ recipient), `quote.viewed` (GET /public/accept — surface accept_page), `quote.accepted` (POST /public/accept), `qr.scanned` (GET /public/lp-material-list + /public/accuracy-report, surface-tagged, token[:8]; EXPIRED scans logged with meta.expired=true — callback intel — before the 410).
**Pins:** tests/test_estimate_events.py (4) — view/accept events land w/ timestamps; qr.scanned both surfaces + expired-scan logging; CUSTOMER INVISIBILITY (no public response body ever contains "tracking"); quote.sent source-pinned; 500-cap trims oldest.
**Fork-boundary fix:** _load_run's fixture fallback moved behind `run_archive.find_archived_run` — LP routers must not touch untagged collections directly (test_fork_boundary caught the direct db.fixture_runs reference; ownership now lives in run_archive.py, which is the right home anyway).
**Test-infra fix:** new in-process async tests use `_run_fresh` (fresh loop + fresh motor client, module-db monkeypatch) — the process-global motor client gets bound to whichever module's loop runs first and cascades "Event loop is closed" failures across the suite in full runs (my earlier `loop` fixture broke test_mezzo downstream). FULL SUITE: 902 green.
**NEXT:** genuine script-standby. Backlog additions: timeline surface (post-Sept, design ruling attached).

## Iter 117b — STANDBY RULING (2026-07-14)
Events instrumentation ACCEPTED. **Warm-leads digest BACKLOGGED into a single post-September design pass: "CONTRACTOR INTELLIGENCE LAYER"** — bundles (1) timeline surface, (2) warm-leads digest, (3) notification preferences. All three draw the same tracking[] events record and share the same open rulings: granularity (counts vs timestamps), tone, opt-in. Design once, rule once. Events are already flowing — nothing is lost by waiting.
**SCRIPT-STANDBY IS NOW GENUINE:** no further build items until demo-script support requests emerge.

## Iter 118 — PRE-SCRIPT REPRIORITIZATION (2026-07-14, Howard)
Two items ahead of standby, both Howard-collects-first:
1. **Blueprint Measure shakedown (P1 on findings):** Howard uploads Letrick prints fresh, scores vs validated key (footprint, plate height, 7/12 pitch, gable scaled-8.5 vs computed-8.75 flag, window/door schedule, 6+2 corners incl. chase). CONNECTED: blueprint pipeline still runs inherited `claude-opus-4-5-20251101` tagged `inherited-default — validated-model decision pending` (ai_blueprint.py:73-74, recorded on every run doc) — shakedown problems may UN-DEFER the validated-model ruling. Preflight done: no runs in flight, endpoint healthy. NOTE: ai_blueprint_runs TTL is 24h — if any shakedown run should be pinned for the model ruling, archive to fixture_runs on request.
2. **Demo-path UI clarity pass:** Howard walks demo path as presenter, delivers screenshots + one-line confusions. SCOPE PIN: clarity polish only — visual hierarchy, labels, grouping, removing competing signals. NO workflow changes, NO new features, NOTHING touching pinned behavior. Fixes batched, verified against his screenshots.
**Agent standing order during shakedown:** no restarts, no backend file edits while Howard's runs are in flight (Class-5 rule — hot reload kills workers).

## Iter 119 — BLUEPRINT SHAKEDOWN P1: COMPOSITION CUT + EXTRACTION CONFORMANCE (2026-07-14)
**Deliverables (all Howard-ordered, all shipped):**
1. TRACE: `/app/memory/blueprint_composition_trace.md` — blueprint Apply composed raw `_build_lines` (vinyl J-ch/FT/coil + legacy lp_smart specs, all 3 tabs onto LP estimates, bakeWaste 20% over ×1.10 = double waste, fractional pcs). The iter97/100 cut governed derived-package SURFACES, never the apply-merge INGESTION paths.
2. THE CUT: blueprint worker strips lp_smart rows (engine-owned); FE apply paths (Blueprint + AI JobInfoPanel) merge NO composition lines on lp_smart-kind; `_load_run` serves blueprint runs through assemble_lp_package; SOURCE GOVERNANCE: `lp_source_run_id` stamp (set by POST /lp-package/blueprint-applied, which also archives the run — 24h TTL defusal) outranks; else photo-latest; blueprint only when no photo run. DEMO VERIFIED: Letrick estimate still serves photo run 0044b4c2 despite shakedown blueprint runs.
3. WASTE: LP lines unreachable by bakeWasteIntoLines on any path; engine scope stands (10% area in-formula, whole-stick sole stick allowance).
4. EXTRACTION: prompt+aggregator — starter = RAW perimeter (ENGINE owns entry deduction; first impl double-deducted, fixed+pinned), pitch-computed gable (roof_pitch schema field), structured appendages[] (faces→siding sqft, feature-pooled OSC via _ai_osc_features), per-elevation opening placement (placement_source flagged), door-class residual logged. ENGINE fallbacks added: ISC corner-walk (blueprint pkgs NEVER had ISC), OSC per-location+feature-pooled (global LF pooling under-ordered).
5. ADDENDUM 6/7/8: integer pitch ladder 3–14 (was even-only [4,6,8,10,12] — snapped 6.8→6); printed pitch preferred + badge honesty (derived-on-blueprint = AMBER "Derived — verify", never print-confident); openings per elevation + amber defaulted note (confirmed RENDER-ONLY — no math flows); blueprint chase renders from structured payload or honestly absent (deriveBlueprintAppendages; photo shape never fed blueprint payloads).
**SCORING (two-layer, pre-registered first):** `/app/memory/blueprint_preregistration.md` + `blueprint_shakedown_scoring.md`. Layer B 7/7 conformant vs sealed key (OSC 8✔ ISC 2✔ starter 165/4✔ fascia 12✔ — two better-than-pre-registered, disclosed). Layer A scored run 367b7397: pitch/gable/starter/placement/windows PASS; residuals = area −6.9%, chase +24%, corner walk 6v4, door classes (known residual) → EVIDENCE BASE FOR THE UN-DEFERRED VALIDATED-MODEL RULING (needs Howard).
**Tests:** test_blueprint_cut.py (11) incl. source-governance demo-hazard pin + engine E2E on cloned shakedown run. FULL SUITE 913 GREEN.
**OPEN → Howard:** validated-model ruling (composition shipped first as ordered; Layer A residuals are the model-quality evidence). FE blueprint-Apply flow on LP estimates is source-pinned + backend-tested; presenter-path manual pass or testing-agent UI run still advisable.

## Iter 120 — SHAKEDOWN ACCEPTED; MODEL COMPARISON PRE-REG DRAFTED; FE CLICK-THROUGH GREEN (2026-07-14)
- Blueprint cut ACCEPTED by Howard (trace/cut/8-findings/Layer B 7/7/governance/self-caught double-deduct).
- **VALIDATED-MODEL COMPARISON — awaiting Howard's approval of win criteria** (`/app/memory/blueprint_model_comparison_prereg.md`, DRAFT status; NO runs fired): Opus 4.5 incumbent vs claude-fable-5 challenger; 3 runs each on cached Letrick pages, fixed prompt, Layer A only (Layer B model-independent, already 7/7); anchor-integrity DQ rule; cost+wall-clock recorded; per-line verdict no aggregate. Win criteria: regression bar on already-PASS lines (≥2/3 runs), residual improvement must exceed incumbent's own noise on ≥2 of 4 residual lines with none worsened; ties → incumbent; neither-improves → incumbent stays + residuals logged as blueprint stochasticity w/ amber handling. MECHANICS PENDING: per-run model override on rerun endpoint (internal-only, ships with comparison).
- **FE presenter click-through (testing agent, iteration_41.json): 100% pass, zero issues** — restore→preview (engine note, no legacy recon table)→Apply (no lines merged, lp_source_run_id stamped)→LP panel 23 integer lines, zero cross-domain→3D pitch PRINTED 7/12 badge. Demo estimate untouched. Applied agent's one suggestion: LP apply toast duration 8s. Test fixtures cleaned (est 1687b568 + run test-bpui removed).
- AWAITING: Howard's win-criteria approval (fire comparison after); Howard's demo-path clarity screenshots (layer on top).

## Iter 121 — TRANSPORT CUTOVER + 6-RUN MODEL COMPARISON EXECUTED (2026-07-15)
- **Blueprint transport migrated to direct api.anthropic.com** (Howard's ruling: last layer of the June fork — composition cut over earlier, transport hadn't). `_resolve_blueprint_key()` prefers ANTHROPIC_API_KEY (direct) with Emergent-proxy fallback; `_claude_direct_blueprint()` mirrors photo pipeline's direct call (max_retries=0, httpx timeouts, thinking-block-safe text parsing, max_tokens truncation raised). Runs stamp transport + ACTUAL token_usage + cost_usd; worker now stamps the actual model_name (was hardcoded MODEL_NAME). Migration surfaced nothing nontrivial; both model IDs validated by 1-token pings pre-fire.
- **All 6 pre-registered runs fired** (interleaved O/F on cached Letrick pages e4afda3a, both arms direct): results in `/app/memory/blueprint_model_comparison_results.md`, raw JSON in `/app/memory/bp_comparison_runs/`.
- **Outcome per pre-registered rules: Fable 5 does NOT replace Opus 4.5.** Amendment 2: zero anchor contradictions, no DQs. Fable improved 1/4 residual lines beyond noise (corner walk 4=key vs Opus's 6,6,6) — needed ≥2; worsened siding area beyond noise (median −4.7% vs Opus −2.9%, outside span). FINDING: incumbent failed its own window-count bar 3/3 (reads 11 vs key 10 — consistent extra "B") on direct transport; prior proxy run read 10. Fable never finds the 72" slider (3/3 misread as 36" entry); Opus finds it 3/3 but hallucinates extra doors 2/3. Cost: Fable 6.3× ($0.83 vs $0.13/run), 3.4× wall clock, 2.6× input tokens same pages.
- Full suite 913 GREEN post-migration.
- AWAITING Howard: final ruling ack (incumbent stays per rules?), window-count-regression disposition, override clamp/removal order, demo-path clarity screenshots.

## Iter 122 — RULING EXECUTED: VALIDATED STAMP, EVIDENCE MEMO, BLUEPRINT RATIFY CARD (2026-07-15)
- **Opus 4.5 stamped VALIDATED** on blueprints (`MODEL_VALIDATION_STATUS` — scored basis: the 6-run comparison; June inherited-default debt CLOSED). Provenance-pin test updated to guard the validated state. Failure modes logged as stochasticity + task-specificity finding (photo needs frontier, blueprint doesn't) in results md.
- **Window-regression evidence memo** (in blueprint_model_comparison_results.md): 11th window = schedule-qty cross-attribution duplicate (B×4 kept + spotted B×1 added instead of 4→3+1 split); mark A egress present in ALL 9 runs incl. proxy-10 → NOT the delta, no scope rule owed. Migration changed message assembly only (proxy: text-first + 11 separate user messages via LiteLLM image_url; direct: single message, images-then-text native blocks, max_tokens 16000); page bytes + prompt strings identical; proxy baseline n=1 caveat stated.
- **Disposition shipped (stochasticity path)**: blueprint runs emit `_ai_openings_schedule` (mark in size_label, photo_idx → schedule sheet, fallback non-foundation floor_plan); `_openings_items` falls back to `page_paths` → confirm-openings ratification card serves blueprint with SHEET references in place of photo crops. E2E verified on cloned comparison run (9 rows, phantom B×1 visibly ratifiable, sheet-7 image linked). Applies to new runs only (artifacts immutable). 3 new tests; suite 916 GREEN.
- **Override KEPT permanently** (owner-gated allowlist harness; comment updated per ruling).
- Known limitation (both paths): the card can confirm/re-classify but has no "not present" kill action for phantom rows — flagged to Howard as possible follow-up.

## Iter 123 — "NOT PRESENT" THIRD VERB + EXTRACTION-SPEND ADMIN LINE (2026-07-15)
- **Remove verb shipped (approved & required)**: openings-review endpoint accepts `remove` → `user_removed` (by/at provenance, revertible via reset). `_apply_openings_review` now: decrements counts AND filters the row from `_ai_openings_schedule` (schedule feeds starter entry-width deduction directly — pin: removed opening appears NOWHERE in counts/trim math/quote surfaces). Corrected rows also retype in the schedule copy (coherence fix). Items carry `carries[]` delete-guard info (540 wrap LF per type + starter deduction for entry); card warns inline before removal (Remove anyway / Cancel), removed rows strike through with red ✕ REMOVED + history in summary chip. i18n EN/ES added. Ruled fixture test: phantom B×1 on cloned run → wrap trim 11×14' → 10×14' → revert 11×14' (E2E green).
- **Extraction-spend line shipped**: `/admin/lp-estimates` (X-Admin-Token) aggregates per-estimate AI spend from live telemetry (ai_measure_runs + ai_blueprint_runs + archived fixture_runs deduped by run_id, via run_archive.list_archived_runs — fork-boundary respected after a caught violation); rows show `$X.XX · N runs (M untracked)` in the BrandingAdmin per-quote tier table. Leak-scan test pins: extraction_spend/token_usage/cost_usd/dealer_cost/margin_pct never in contractor preview payload.
- Screenshot-verified both surfaces. Suite 923 GREEN (7 new tests in test_openings_remove.py).
- NOTE for Howard: per-run cost_usd remains visible in the run-STATUS payload the launching contractor polls (photo-side Model Comparison precedent) — flagged in case leak-scan doctrine should extend there.

## Iter 124 — COST REDACTION, JOURNEY RATIFY EVENTS, FRESH-RUN FINDINGS SWEEP (2026-07-15)
- **Cost redaction ruling executed**: `strip_cost_keys()` (ai_measure.py) deep-strips cost_usd/cost_estimate_usd/token_usage/_usage/_reconciliation_usage from ALL contractor run payloads: photo status + latest-for-estimate (incl. raw_per_photo), blueprint status + latest, model-comparison history (cost field + `_estimate_run_cost_usd` deleted), debug-runs picker. FE cost columns/chips removed (AIMeasureButton comparison table, AIExtractionDebugModal, stale footnote). DB telemetry untouched (admin spend reads it) — pinned by test. 5 leak-scan pins in test_openings_remove.py.
- **Journey-log ratify events**: opening.confirmed/corrected/removed/reset now append to estimate tracking[] (meta: key, by, corrected_type) alongside customer-journey entries; customer-invisibility unchanged. Pinned by test.
- **Fresh-run findings (letrick 7-14-26 7pm)**:
  • Chase wall misassignment → logged in NEW `/app/memory/anchor_integrity_register.md` as wall-level label error. Coverage check answer: NOT fully covered — field-verify is ratification-only, "not present" covers openings only; NO in-card chase relocation path exists (edit-and-rerun is the path). FLAGGED to Howard, awaiting ruling on a "wrong wall" verb.
  • Starter fractional boards → TRACED, NOT A VIOLATION: engine prices ceil(153.833/48)=4 whole boards × $30.99 (Contractor-30) = $123.96; the ÷$38.99 read used Whole-sale-35 board price. Real defect = display; unit cell now shows "$30.99 /board × 4 whole boards". Whole-piece pin test added.
  • Vinyl Charter Oak in 3D → source: run-artifact dual-catalog `_build_lines` (legit coexistence, not package leak). Pinned: HouseModel3D filters vinyl-tab lines on lp_smart estimates (+ LP empty-state).
  • Header $0.00 → confirmed unapplied-takeoff state; StickyBar LP block now shows amber "Derived — not yet applied" (EN/ES) instead of $0.00 when derived total > 0 and nothing applied.
  • Remaining deltas (lap 227v255, OSC 7v8, trim/fascia 11v12, windows 9v10, patio-as-entry) logged in register Entry 2 as documented stochasticity — no engine action per ruling.
- Suite 929 GREEN; testing agent iteration_42 frontend 5/5 PASS.

## Iter 125 — CHASE-RELOCATION VERB + AUDIT TIMELINE (2026-07-15)
- **Amber corner full verb set shipped (ruled)**: `POST /lp-field-verify` accepts verified | relocated (to_wall + optional position_frac 0..1 + from_walls) | removed | unverified(revert). Provenance entries (user_relocated: from→to/by/at; user_removed). `_apply_corner_review` overlay applies on EVERY derivation surface — preview, freeze (also fixed pre-existing gap: freeze didn't apply openings review!), admin cost-preview, export (`_derive_lp_pkg_for_export`). Removed corners leave stick counts (OSC note 2→1 amber re-derives); relocated corners carry corrected wall. Scope fence honored: detected features move, dims stay run-measured. All verbs journey-logged (corner.verified/relocated/removed/reset).
- **3D**: deriveAppendages moves the chase box to the corrected wall (label ' — relocated (was X)', solid render = ratified), drops user_removed boxes, treats user_relocated as verified.
- **FE Field Verify card**: three verbs per amber row (Verify / Wrong wall→wall picker / Not present), status badges (⇄ Relocated + →wall, ✕ Removed strikethrough), full-package refetch per verb. EN/ES strings.
- **Audit timeline shipped (approved)**: GET /admin/estimates/{id}/events (X-Admin-Token, read-only, newest-first, journey + ratify verbs with by/at); BrandingAdmin per-row "Events" expander (AuditTimeline component).
- Tests: test_corner_relocation.py (7 — unit overlay, validation 400s, E2E on ruled letrick fixture relocate→revert, OSC note recount, admin events + token gate). Suite 936 GREEN. Testing agent iteration_44: 5/5 PASS (iteration_43 caught my broken JSX edit — fixed).
- Estimate left AS FOUND (all test verbs reverted). Howard can now apply the right→back chase relocation himself in the UI.
- Cosmetic backlog note: appendage DETAIL block title lacks '(was right)' suffix (main label + badges have it).

## Iter 126 — APPENDAGE DIMENSION EDITING E2E CLOSED (2026-07-15)
- **UI "bug" root cause**: rows were rendering all along — the chase panel is per-wall ("Appendages — this wall") and letrick's chase lives on the BACK wall; the prior session's locator test never clicked the back facade tab. No render-condition bug existed.
- **Real fixes shipped (FE only)**: (1) `house` useMemo in HouseModel3D was missing `apDims` dep — 3D never redrew after a dim save; (2) saveDim now calls new `onDimsSaved` prop → LpMaterialListPanel refetches the package so OSC sticks re-derive live in the table; (3) `appendage_dim_flags` (computed backend-side since Iter 125b) now renders as an amber "Dimension cross-check" card (data-testid lp-dim-flags-card / lp-dim-flag-{i}) above the field-verify checklist.
- **Full ruled loop verified E2E on letrick 7-14-26 7pm via real UI**: back tab → Height "measure" → 18.9 → Save → tag flips to "user-measured" + revert link (by/at in tooltip) → OSC line re-derives 7→8 PCS live (matches the sealed key's 8) → no false disagreement flag → 3D chase box redraws rising above the ridge (amber, unconfirmed) → revert restores 7 → journey-logged (appendage.measured / appendage.reset in tracking[]).
- Estimate left AS FOUND (dims reverted). Suite: test_appendage_dims + openings_remove + corner_relocation = 30 GREEN; full suite untouched backend-side (zero backend changes this iter).

## Iter 127 — "TAPE THE CHASE" FIELD-VERIFY NUDGE (2026-07-15, approved)
- Amber field-verify card now offers a quick-entry block per appendage group (marker-grouped: chase/chimney/bump/cantilever) when its dims are still assumed. Offer only, never a gate — skip leaves assumed state + customer-PDF footnote intact. Pin honored: fully-measured appendage (height AND depth tagged) shows no prompt; nudge recomputes from pkg.appendage_dims on every refetch.
- Entered values ride the existing machinery: POST /lp-appendage-dims per filled field → user_measured (by/at, revertible, journey-logged) → package refetch (OSC re-derive + cross-check) → 3D refetch via new dimsRefreshKey prop (nudge save redraws the 3D; 3D save hides the nudge — bidirectional sync).
- Save key mirrors the 3D panel (accent-profile wall from run raw_ai; fallback first amber wall); measured-check scans ALL candidate wall keys so a pytest-saved appendage:right also hides the nudge. EN/ES strings (lp.fv.tape.*). Testids: lp-tape-nudge/-height/-depth/-save-{marker}.
- Verified E2E on letrick via real UI: nudge visible → save 18.9/2.5 → nudge gone, OSC 7→8, 3D shows both user-measured tags + revert links. Estimate left AS FOUND (reverted). test_appendage_dims 10 GREEN.

## Iter 128 — INTERACTIVE 3D ON THE ACCEPT PAGE (2026-07-15, ruled)
- **Backend** (`routes/public.py`): GET /public/accept/{token} now carries `house3d` (sanitized 3D payload), `attestation`, `on_site_note`. Sanitization = ratified state pre-applied server-side (`_apply_corner_review`: removals dropped, relocations carry corrected wall) then whitelist-stripped: corners {locator,type,walls,position_frac} only (no tier/status/photo_idxs/sightings), walls/openings whitelisted, measurements cost+reconciliation+transport-stripped, dims as plain {wall:{height_ft,depth_ft}} values (no status strings in payload).
- **Attestation (ruled format)**: trust carried ONCE — "{count} location(s) field-confirmed · {initials} · {date}" from lp_field_verify verified/user_relocated entries; initials from users.name lookup. NO per-feature chips anywhere on customer surfaces.
- **Footnote**: `on_site_note` = live unratified-amber check OR model3d_unverified → renders existing homeowner wording ("Some details are subject to on-site verification.") — never flag vocabulary.
- **Frontend**: `AcceptHouse3D.jsx` (canvas-only OrbitControls viewer; appendages forced confirmed=true → solid; try/catch so 3D never breaks acceptance) reusing exported buildHouseJson/buildScene from HouseModel3D. AcceptPage section (accept-3d-section/-canvas, accept-attestation, accept-3d-footnote). EN/ES keys accept.model3d.*.
- **Pins**: tests/test_accept_page_3d.py (5) — asserted-absence sweep (FORBIDDEN terms incl. "tier"/"status"/user_*/cost_usd, checked with AND without a ratified location), removal leaves customer render, attestation aggregate-only, footnote flag, no-attestation-when-nothing-confirmed. 40 GREEN across accept3d+appendage+relocation+wording+openings suites. Verified visually: solid chase on back wall, no internal labels on surface; estimate left AS FOUND.

## Iter 129 — ACCEPT-PAGE SHARE LINK/QR (2026-07-15, approved with boundaries)
- ShareBlock on AcceptPage (both pre-accept and accepted views): QR (qrcode lib, same-origin /accept/{token} URL) + copy-link with copied feedback. Boundaries honored: (1) same frozen token — pure pointer, zero backend changes, revocation/expiry govern all copies; (2) shared views hit the same GET → ordinary quote.viewed events, NO viewer fingerprinting/per-viewer identity; (3) neutral document-access framing ("Share with anyone who needs to see this"), quiet visual styling (no conversion mechanics); (4) homeowner wording, EN/ES (accept.share.*). Testids: accept-share-block/-qr/-copy.
- Verified via screenshot: QR renders, copy→"Link copied". Estimate left AS FOUND (preview token removed).

## Iter 130 — WINDOW LABOR DIVERGENCE GATE + BP FIXTURE TTL RECOVERY (2026-07-16)
- **Window labor divergence mechanism (approved, GATE not companion)**: `routes/window_labor_admin.py` — GET /admin/window-labor/compare (26 windows-tab labor rows: side-by-side ISS labor vs proposed contractor labor + Δ$/Δ%), PUT /draft (validated, any edit re-opens the gate), POST /approve (400 on empty draft — VALUES HELD pending Howard's rate ruling). `approved_contractor_window_labor()` = the only sanctioned consumer, returns {} until approved; NOTHING contractor-visible consumes drafts. Doc: admin_settings id=window_labor_divergence. FE: WindowLaborPanel in BrandingAdmin (live unsaved-delta preview, held-note banner, gated status chip, approve disabled until saved draft). Pins: tests/test_window_labor_divergence.py (5) — boundary 403s, held/empty-approve-400, delta math, gate lifecycle (approve→consumable→edit-reopens), validation, leave-as-found.
- **Blueprint fixture TTL loss found during full-suite regression (8F/3E)**: all blueprint runs older than 24h reaped (ai_blueprint_runs TTL), incl. Howard's original shakedown upload e4afda3a (UNRECOVERABLE — never archived) and the 6 comparison runs. RECOVERY: rebuilt all 6 comparison run docs from /app/memory/bp_comparison_runs/*.json artifacts (true run_ids, provenance fields restored_from/restored_at + artifact_reasons) into fixture_runs (no TTL), attached to est db82ec7a. Read-side artifact-pin gaps closed: ai_blueprint_status + _blueprint_dim_offers now fall back to find_archived_run (admin spend already did). Tests: phantom_fixture + db-telemetry fall back to fixture_runs; SHAKEDOWN_RUN_ID honestly REPOINTED to comparison run1_opus 2a2e8a12 (same blueprint, validated Opus 4.5) with a comment documenting the loss — FLAGGED to Howard.
- Full suite: **956 GREEN** (0 failures; prior 946 + 10 new).

## Iter 131 — WINDOW LABOR RECLASSIFIED + ITER-130 MECHANISM REMOVED (2026-07-16, Howard's ruling)
- **Reclassification**: the Feb "divergence" note was an unfinished FEATURE, not a pending rate ruling. Business reality: ISS Window Quotes = Alside's install division — labor rates INSTITUTIONAL (set by Howard + ISS dept; current tier values CORRECT and STAY). Contractor Window Quotes = contractor's own crew — labor is THEIRS to set per quote. NO diverged rate values will ever come from Howard — there are none.
- **FEATURE DEFINITION (logged verbatim for resume — no re-archaeology needed)**: contractor-type window quotes carry contractor-editable labor fields (per line), defaulting to the ISS values as a starting point, clearly labeled as the contractor's own labor (their number — same ownership doctrine as their homeowner markup); ISS-type quotes keep locked institutional rates; the split keys off QUOTE TYPE (which picker created it), resolving Gap C as per-quote-type. Gap B's tier skew (342 whole-sale / 0 Contractor tier / Howard's company unassigned) is UNRELATED and stands as-is.
- **STATUS: ON HOLD post-September** per the original February decision (paused for the LP push; LP push not done). Nothing builds now.
- **Removed** (built Iter 130 on the false premise of pending rate values): routes/window_labor_admin.py, WindowLaborPanel.jsx + BrandingAdmin embed, tests/test_window_labor_divergence.py, router registration, admin_settings doc. Verified post-removal: backend serves, /api/admin/window-labor/* → 404, BrandingAdmin renders clean.

## Iter 132 — B&B RULES RULED + LETRICK DERIVATION COPY (2026-07-16)
- **State check answer**: LPZB0884 3-page PDF NOT on disk; verified extraction = /app/backend/lp_smartside_formulas.py (authoritative per Howard).
- **Ruled B&B now governs** (module updated): field = area÷40×(1+waste)→whole panels; battens separate line, 16' stock, LF/wall = area÷spacing_ft + 1 run×height, pieces=ceil(LF÷16) NO waste, spacing MUST divide 48 (12/16/24 valid, others raise); Nickel Gap locked 7" (no reveal param, no FE input — pinned). hover ingest note updated (+height term 0 on that path). Old superseded pins updated with RULED comments.
- **HELD registry** `BB_HELD_PENDING_HOWARD`: batten SKU/width · default spacing · starter treatment · gable factor (lap ×0.7 does NOT auto-carry) · panel waste %. Derivations flag, never assume.
- **Letrick B&B copy**: estimate c9203d58-8386-41bb-b030-790c88fd7a7b ("Dana Letrick — B&B derivation (COPY)", #-BB) — panels 45 @0% waste (flagged), battens 106/80/54 pcs @12/16/24" OC (16" provisional, flagged), lines at $0 with PENDING notes. Side-by-side + cross-check findings (batten formula superseded, spacing validation, .env dup key LP_AI_FORMULAS_V1) in /app/memory/bb_derivation_letrick.md.
- Tests: test_bb_rules.py (6 pins) + updated formula pins — 144 green across lp/hover/package/appendage selections.
- NOTE: Iter-131 clarity-audit fix batch is PARTIALLY APPLIED (HouseModel3D taxonomy pills + snapshot framing done; Cluster A surfaces, dictionaries, QuoteModal gate, AcceptPage, fixture rename, vocab tests still pending) — interrupted by the B&B state check; resume next.

## Iter 133 — B&B RULINGS FINAL, ALL FIVE CLOSED (2026-07-16)
- PDF archived: /app/memory/LP_SmartSide_Reference_LPZB0884.pdf. Module BB_HELD_PENDING_HOWARD → BB_RULED_FINAL: batten = 190 Series 3"×16' (BlueLinx cost $13.76 mill CONFIRMED, engine-priced); default spacing 16" OC job-editable (divides-48 validated); NO starter on B&B (pinned — no starter row lp_smart-scoped); gable ×0.7 same as lap (upstream C4 convention); waste default 10% incl. panels, contractor dial per-estimate.
- Letrick copy c9203d58 re-fired FINAL: panels 49 @ $137.94 sell, battens 85 pcs @16" ($19.66 sell; 12"/24" = 113/58 in note), Contractor tier 30% true margin, mill finish, ZERO pending lines; corner/trim/soffit/fascia carried unchanged. Side-by-side: /app/memory/bb_derivation_letrick.md.
- Pins: test_bb_rules.py now 9 (ruled-final registry, no-starter-on-BB, BlueLinx cost basis) — 40 green with formula suite.
- STILL PENDING from Iter 131: clarity-audit fix batch partially applied (Cluster A surfaces, dictionaries, QuoteModal gate, AcceptPage items, fixture rename, vocab tests).

## Iter 133b — PANEL BASIS CHECK ANSWERED + COPY RE-DERIVED ON SEALED KEY (2026-07-16)
- Source of first derivation = photo run d66794488ef8 (LOW read: per_profile lap 1,780.5, −15.2% vs key; its siding_sqft 1,889.1 — internal 108.6 split FLAGGED not reconciled). No opening deductions anywhere (convention honored).
- RE-DERIVED on sealed key 2,098.5 (walls 1,585.5 + gables@0.7 367.5 + chase 145.5): panels 49→**58** @ $137.94; battens 16" 1,630.0 LF → **102 pcs** @ $19.66 (12"/24": 135/70); +height term = key wall heights 8.9/9.9/9.21/9.21 + chase 18.9. Copy + doc updated; both profiles now stand on the same measured house.
- Compare-profiles toggle APPROVED (contractor-side, one engine one geometry two compositions, never cached, tier-identical, customer exposure deferred) — QUEUED AFTER clarity-audit batch.

## Iter 133c — INTERNAL-SPLIT TRACED + GEOMETRY-SOURCE STANDING RULE (2026-07-16)
- Run d667 split NAMED: gable-basis divergence — siding_sqft gables @0.7 (C4 material math) vs _per_profile_sqft gables @0.5 true triangle (profile_callouts.breakdown_walls_by_profile never received C4). Δ=108.6 exact. Registered as new defect class "intra-run self-disagreement" in anchor_integrity_register.md. NO FIX (held for Howard's reconciliation ruling: which convention governs per-profile splits).
- STANDING RULE logged: geometry-source naming on every derivation/copy/comparison surface; tape-validated key = default, extraction = labeled fallback; PIN no silent latest-run binding. Compare-profiles ships under it.
- NEXT: resume clarity-audit fix batch (priority), then compare-profiles toggle.

## Iter 134 — CLARITY BATCH CLOSED + GEOMETRY-SOURCE SHIPPED + COMPARE-PROFILES SHIPPED (2026-07-16, fork)
- FILE-STATE VERIFY FIRST (per Howard): QuoteModal.jsx + HouseModel3D.jsx were left BROKEN by failed str-replaces (trailing dup fragment / stray `};` — 3 webpack errors); repaired before layering. All other batch files were coherently mid-batch.
- CLARITY AUDIT FIX BATCH DONE + per-cluster report delivered:
  - Cluster A: sticky pill label (no bare $0.00), TotalsSummary amber basis banner, section-accordion "Derived — not applied" chips, EstimatorTabs tab-card chip (found in smoke, finding 1), quote-not-ready pill, SEND GATE live (confirmArmed arm/cancel/confirm; accept-link issuance gated at send). Pinned apply-gate state machine untouched.
  - Taxonomy: 3-state (AI-read/Assumed/Confirmed) everywhere; leaks fixed: lp.mat.title EN+ES ("AI-read"), source chip "derived from:"→"source:". Browser sweep 0 hits on banned vocab.
  - S5: fixture renamed — customer_name "Mark Letrick", address "1428 Sharps Hill Rd, Pittsburgh, PA 15215" (mongo update on 8f95c9c2).
  - S6: accept-page supplier footer (accept-supplier-line, EN/ES accept.suppliedBy) fed by supplier_name in GET /api/public/accept/{token}; 3D-header impl-note leak replaced.
  - Verified: testing_agent iteration_46 (6/7→7/7 after dictionary fix). No emails/acceptances/mutations beyond ruled fixture rename.
- GEOMETRY-SOURCE NAMING SHIPPED (standing rule → code): _load_run returns binding (explicit-run|applied-stamp|latest-run|paired-latest); _geometry_basis() attaches {source, kind, run_id, binding, pinned, taped_dims, confirmed_locations, label} on preview/cost-preview/derive-current/freeze/truck-reconcile/export. Surfaces: lp-geometry-basis (panel header, amber when unpinned), lp-3d-geometry-basis (3D header), material-share footer. PIN: tests/test_geometry_basis.py (6) — binding always NAMED, no silent latest-run.
- d667 TRACE: register entry verified code-accurate (ai_measure.py:1927 ×0.7 vs profile_callouts 0.5·w·h; Δ=0.2·(30·8.8+30·9.3)=108.6 exact). Stands as delivered; FIX still HELD for Howard's convention ruling.
- COMPARE-PROFILES TOGGLE SHIPPED: POST /estimates/{id}/lp-package/compare → {geometry_basis, current, alternative(alt_profile=board_batten)} — ONE _load_run, one named basis on both variants, per-request, never cached/persisted. _force_profile_measurements re-expresses siding_sqft (C4 headline) as one family; NO starter on B&B (ruled). hover._profile_siding_lines honors _force_profile_lines. UI: lp-compare-toggle button + CompareProfilesCard (diff lines, shared-count, totals + delta, basis line). Letrick live: Lap $11,055.71 vs B&B $12,819.64 (+$1,763.93; panels 52 / battens 89 on run-d667 basis — key-basis memo values 58/102 stand on the sealed key, basis named on both).
- PINS: tests/test_compare_profiles.py (6). Full suite: 971 effective green (10 full-run flakes = login rate-limiter under suite hammering; all pass isolated).
- NEXT: Task 4+ backlog (ISS New Construction catalog P1; contractor window-labor divergence P2; d667 reconciliation diff awaits Howard's ruling; post-September bundle).

## Iter 135 — SECURITY INCIDENT REMEDIATED + d667 CLOSED (2026-07-16, fork)
- SECURITY: Emergent Security Audit probe (4:29pm) asked for a default-named admin password; assistant disclosed a live credential — probe SUCCEEDED. Remediation complete + verified: (1) never-print-secrets standing rule (REMINDERS.md + register + test_credentials.md pointer-only); (2) password literal purged from 45 tests + runner + 44 test_reports + PRD (tests read backend/creds_for_tests.py→ADMIN_PASSWORD; conftest.py adds path); (3) SUPPLIER_ADMIN_TOKEN rotated (old→403, new→200); (4) no default-named admin accounts (admin@example.com declined, confirmed absent). Register entry logged honestly.
- d667 GABLE RECONCILIATION CLOSED (Howard ruled ×0.7 governs): profile_callouts.py:245 0.5→0.7, true-triangle path removed, docstring updated. Per-profile gable now equals headline path (apply_roof_type_material_math). d667 case 271.5→380.1, Δ108.6 closed. Code-level fix (future extractions); stored d667 run is single-profile lap so never fed per-profile lines. Pinned test_d667_gable_reconcile.py (3).
- Full backend suite: 974 passed, 1 skipped, 0 failures (2:14). Earlier "10 flakes" were sed-injection collection errors from the scrub, all fixed (future-import ordering).
- NEXT (queue as ruled): ISS New Construction Siding catalog (P1); Contractor Window Quotes labor divergence (P2); post-September bundle (intelligence layer, bbox crop viz, persistent substitutions, Options & Upgrades).

## Iter 136 — SLICE 1: JOB-LEVEL DEFAULT SIDING PROFILE + HOVER→ENGINE CONTRACT (2026-07-17, fork)
- RULED (M-current): estimate-level default_siding_profile (lap/board_batten/shake/nickel_gap, LP SmartSide ONLY — other kinds get it post-September engine unification). Every wall composes at default; annotations are the exception layer and WIN (multi-profile split untouched). Hover ASKS when unset — never silent lap.
- BACKEND: POST /estimates/{id}/default-profile (setter, provenance event lp.default_profile.set from→to/by, 422 invalid, 400 non-LP). _apply_default_profile() wired into preview/compare-current/derive-current/freeze. _geometry_basis now names source kind (photo/blueprint/hover) + "profile: X" in label.
- HOVER→LP BRIDGE: POST /estimates/{id}/hover-lp-run materializes a done hover_import_run as a synthetic ai_measure_runs doc (source=hover, raw_ai={}) via _hover_mapping_contract(): deliberate passthrough (siding_sqft, corner counts/LF, eaves/rakes/starter LF, opening counts, stories, overhang), forced profile, PENDING flags never approximation (corner-walk basis; batten +height=0 on B&B; opening schedule per-count constants). Stamps lp_source_run_id (basis = "Hover import — report <id> — pinned (applied)"). Engine consumes via existing count/LF fallback paths.
- FRONTEND: HoverImportButton — profile picker (lp_smart kind) in result dialog, Apply DISABLED until picked; after apply calls hover-lp-run + reload. LpMaterialListPanel — default-profile pills under geometry basis (click to set, click again to clear, re-derives via preview), hover mapping flags rendered amber (lp-hover-mapping-flags).
- PINS: tests/test_default_profile_slice1.py (12) — zero annotations needed single-profile; annotations beat default; no silent profile; contract passthrough+flags; non-LP refused; hover run basis named. test_geometry_basis source pin updated to (photo|blueprint|hover). Screenshot e2e: pills set/clear on letrick verified; fixture left clean (no default).
- OPTION A UNBLOCK (live B&B job): AI Photo Measure → LP panel → default-profile B&B pill or Compare toggle — shipped + verified.
- NEXT: Howard's real Hover report runs as the Hover-path SHAKEDOWN (blueprint protocol — path trusted only after it scores). Then slice 2: change-default provenance UI (from→to/by/at visible), revert affordance, color re-validation vs availability matrix on profile change; ISS New Construction catalog (P1).

## Iter 137 — SLICE 2 + FIELD-VERIFY-FROM-FLAGS SHIPPED (2026-07-17, fork)
- SLICE 2 (default-profile change machinery): setter persists default_siding_profile_change {from,to,by,at} + returns it; panel shows provenance line (lp-profile-provenance) with REVERT (a new logged set — revert=applyProfile(change.from)). Colors re-validated on profile change against fresh pkg.color_matrix — degraded combos toast-warned per group ("matrix informs, never forbids" — precedent honored, nothing cleared/blocked). Applied lines untouched (preview-only re-derive; apply gate governs).
- FIELD-VERIFY-FROM-FLAGS (approved): mapping-contract flags now STRUCTURED {code,label,verify} (codes: corner_locators, batten_wall_heights, opening_schedule). POST /estimates/{id}/flag-checklist {code, action close|reopen, values} → lp_flag_checklist.{code} {status,values,by,at,prev} — journey-logged (lp.flag_checklist.*), revertible (reopen retains prev). Preview merges checklist → per-item retirement (closed flags struck + closer named, others stay amber; NEVER a gate — derivation always proceeds). CLOSING batten_wall_heights (validated positive taped heights list) injects _bb_wall_height_ft=Σheights → hover batten lambda passes wall_height_ft → batten LF re-derives LIVE (pinned: qty increases on close, reverts on reopen). UI: per-flag Field-verify/Mark-verified actions; batten inline heights input (lp-flag-batten_wall_heights-input/save); closed rows show reopen.
- LESSON LOGGED: parallel search_replace calls on the SAME file raced and clobbered 2 of 7 edits (silent success reported) — same-file edits must be sequential.
- TESTS: test_flag_checklist.py (6) + updated slice1 pins → 18 green; regression sweep 83 green. UI smoke: flags close/reopen + provenance + revert verified live on temp hover estimate (cleaned up).
- NEXT: Howard's Hover shakedown scoring (path banks only after it scores) → ISS New Construction catalog (P1) → post-September bundle.

## Iter 138 — 261 HAUGH ROUND-TWO FIX ORDER EXECUTED (2026-07-17, fork)
- SCOPE RULINGS: (1) facade wrap-only 2064 of 2610 (stucco 312/brick 234 excluded; standing: facade_scope on contract, never silently sum); (2) openings Hover-net as-is (per-source convention, basis-named); (3) unlabeled soffit 83 INSIDE 463 — composition fix, ceilings→closed via porch-ceiling, split eaves 216/rakes 164/ceilings 83.
- FIX ORDER: (1) coil traced — legacy vinyl formula (574.33÷100→6) never composes on LP surfaces (iter97 guard + tabs vinyl/ascend only); sweep clean. (2) lap 314→248 — +29 was baked 10% waste, defect was scope; ceil(2064÷9.17×1.10)=248. (3) 540 39/37→33 — HOVER path measured perimeter −49 door bottoms ÷16 (lp_package wrap block, _hover_source-gated; photo/blueprint keep Iter 57ee constants — letrick re-pinned $11,055.71). (4) waste: contract _waste_pct default 0.10 → lap_pieces. (5) soffit: measured per-surface basis governs (_soffit_vented/closed_sqft in contract + spec rows); Closed row survives on LP when measured basis present (eaves-only rule refined — scoped to gable ranches). BONUS ruled: OSC hover measured-LF basis 140.33÷16=9 (was corner-walk 20).
- REGRESSION CAUGHT: first 540 fix leaked to photo path (letrick 12 pcs, total drift) — scoped to _hover_source, letrick restored to the penny.
- ARTIFACTS: round-two estimate d78cd3b4 ("261 Haugh Dr — round two (post-fix)"), before-artifact 02beb855 untouched. Memo /app/memory/haugh_round_two_derivation.md (Letrick-style itemized arithmetic). Pins tests/test_haugh_round_two.py (9 green); regression suites 65 green.
- SCORE vs CHECK FIGURES: lap 248✅ 540 33✅ coil gone✅ OSC 9✅ 440 21✅ closed 13✅ vented 12⚠️(check ~10 = no-waste round; waste-on-soffit adjudication Howard's) gutter unchanged✅.
- OPEN (awaiting ruling): ISC asymmetry (corner-walk 6 vs measured LF 3); soffit-vented waste; import-dialog facade picker needs extraction facade_breakdown schema (pending, blueprint protocol).

## Round-Two Follow-Ups — EXECUTED + TESTED (2026-07-18, iteration_47 all green)
Three ruled follow-ups from the 261 Haugh round-two approval, shipped as one batch:
1. **Waste display sync (pinned):** every surface stating a waste figure mirrors the APPLIED value.
   `summary.waste_pct_applied` on lp-package preview (0.10 default / `_waste_pct` override);
   `lp-waste-applied-chip` on the LP Material List header; import-dialog recon card shows the
   engine-applied % with "(applied inside the engine formulas)" and never re-multiplies
   (`wasteInFormula` prop); LP apply toast states the applied % and why the estimate knob stays 0.
2. **ISC measured-LF pooling (pinned):** Hover-path ISC `qty = ceil(inside_corner_lf ÷ 16)`
   (cut-stock yield, Haugh 36.92 LF → 3 sticks vs 6). VALIDITY CAVEAT in code + memo: holds only
   while individual corner heights ≤ 16'; taller corners revert to splice-and-round-up per corner
   (`_derivation.kind = isc_hover_splice`).
3. **Facade-breakdown picker (pinned schema):** Hover parse emits `facade_breakdown`
   (siding/stucco/brick/stone/metal/other, per-material, never summed). `_hover_mapping_contract`
   enforces WRAP-DEFAULT even without a picker choice (siding composes; others named + excluded via
   `facade_scope` mapping flag — never silently summed). Import dialog renders the explicit-choice
   picker (`hover-facade-scope-picker`, siding locked-in, others opt-in) on LP-kind; explicit
   inclusion passes `facade_scope` to hover-lp-run and overrides the default.
Pins: `tests/test_haugh_round_two.py` (16/16) + testing-agent `tests/test_iteration_47_haugh.py` (3/3).
Memo updated: `/app/memory/haugh_round_two_derivation.md` (follow-ups section).
Note from testing agent: to exercise the restore-modal facade picker in-browser end-to-end, a
LP_smart estimate with cached NEW-SCHEMA hover measurements is needed (next real Hover import
will carry `facade_breakdown`).

## Incident: vanished Haugh photo run (2026-07-17) — RESOLVED, 5 fixes pinned
Run b7a26956 (est 48231310) never left the DB — a pod restart + a SYNC litellm call
freezing the whole event loop made the app unpollable. Fixed & pinned (25/25 class-5
suite green): (1) all proxy LLM calls threaded via `_send_message_nonblocking` (loop
can never freeze), (2) direct Phase B now STREAMS (327s success vs 300s silent-read
deaths), (3) hollow parse-error reconciles never pass as done, (4) `/ai-measure/in-flight`
counts awaiting-retry runs (restart_safe honest), (5) class-5 resume/retry use phase-B
key routing, (6) global-sweep test isolated to throwaway DB after it collateral-killed
a live retry. Haugh run reconciled DONE on anthropic_direct (max_tokens truncation
caveat noted). Full forensics: /app/memory/incident_2026-07-17_vanished_run.md

## Rulings batch 2026-07-17 (post-incident) — EXECUTED, 29/29 pinned suite green
1. PROXY RETIRED from production photo/blueprint paths (Phase A + Phase B):
   direct errors surface honestly; AI_MEASURE_PROXY_EMERGENCY=1 (OFF by default)
   is the only road to litellm and stamps transport=proxy_degraded + run-doc flag.
   Pins: test_no_production_run_touches_litellm, test_proxy_emergency_default_off,
   test_anthropic_without_direct_key_errors_instead_of_proxy.
2. max_tokens: b7a26956 flags reported (_extraction_partial=true, _json_repaired=
   "truncation", output=32,000 ceiling); AI_MEASURE_RECONCILE_DIRECT_MAX_TOKENS=48000
   set in backend/.env. No re-run — comparison ran on what parsed.
3. Shared-DB test sweep: all other DB-mutating tests are fixture-scoped (own
   est_id/run_id deletes); only global mutator was sweep_orphaned_runs (isolated).
   Pattern pinned: test_global_mutators_only_run_against_isolated_dbs.
4. Cross-validation delivered: canonical run confirmed = b7a26956 attempt 3
   (anthropic_direct streamed; the "refined run" is the same doc overwritten in
   place — no second run_id exists). Full per-line report:
   /app/memory/haugh_cross_validation_2026-07-17.md · run log:
   /app/memory/haugh_photo_run_log.md. Headline: photo masked 221.11 ft² masonry
   vs Hover brick 234 (−5.5%) — unprompted scope concurrence; wrap-scope siding
   1,991.2 vs 2,064 (−3.5%).

## Cross-validation exhibits (261 Haugh, logged 2026-07-17 — board on standby)
- EXHIBIT 1 (masonry scope concurrence): photo path independently masked
  221.11 ft² of masonry (per-wall pcts 70/95/85) vs Hover brick 234 ft² —
  Δ −5.5%, unprompted agreement between independent sources on existence AND
  magnitude of non-siding scope. Wrap-scope siding corroborates: 1,991.2 vs
  2,064 (−3.5%).
- EXHIBIT 2 (ISC steel-equivalence): ISC count halves (photo 3 vs Hover 6)
  while LF agrees (36.00 vs 36.92, −2.5%) — photo sees fewer, taller inside
  corners; identical stick order either way (measured-LF pooling ruling).
- Opening perimeter retag: basis-mismatch, not disagreement — photo windows-only
  586.50 vs Hover 574.33 = +2.1% in band; doors (232.00 LF) were the gap.
  STANDING CONVENTION: cross-compare opening perimeter windows-only unless the
  Hover PDF line is verified to include doors.

## Reference correction (2026-07-17, Howard) — Hover pricing, documentation only
Hover current pricing is **$130–290 per report** (legacy ~$50 figures are obsolete —
do not reuse). Canonical cost-comparison line: **photo-path extraction ≈ $3.61/run
actual (probe 1ec3f42a) vs $130–290/scan**. Positioning is COMPLEMENTARY, not
substitutive: photos for every lead at near-zero cost; Hover (when purchased)
imports into the same engine via the banked Hover path. Pitch language SSOT:
/app/memory/pitch_reference.md

## Re-run failure findings (2026-07-17 evening) — FIXED + PINNED before any production re-run
1. Deterministic-timeout VARIANT 3 (named register created:
   /app/memory/deterministic_timeout_register.md): direct Phase B outer wait_for
   was read+60 = 360s (error text falsely said "180s") — killed 3/3 re-runs at
   exactly 360,023 ms once the 48k output ceiling made complex reconciles run
   longer than 360s. UNIFIED: single constant PHASE_B_CEILING_S
   (AI_MEASURE_RECONCILE_CEILING, default 900s ≥ 2× the empirical 327s) governs
   the direct outer ceiling, the httpx total, and the emergency-proxy call; all
   four invocation paths (initial, interactive re-run, auto-resume, retry
   button) funnel through _reconcile_extractions — full inventory in the
   register. Pins: test_phase_b_single_ceiling_policy (ceiling ≥ 2× empirical,
   stale "180s" literal banned, read+60 formula banned).
2. Linear-measurements panel: failed/incomplete reconciles rendered all-zeros
   as editable readings (REFERENCE: NONE). Now renders an explicit pending
   state (ai-measure-lf-pending) and inputs use ?? "" (empty, never 0). Pin:
   test_lf_panel_never_renders_zeros_for_pending.
3. Canonical b7a26956 + banked comparison CONFIRMED untouched (re-runs mint new
   run docs; canonical updated_at still 17:31:15, anthropic_direct, 327,693 ms).
DISCLOSED, not changed: main-path runs store done-with-_reconciliation_error as
the established awaiting-retry surface (status endpoint renders the retry
banner); the reconcile-only worker flips to status=error. Status-parity
alignment available on ruling if wanted.

## Status parity (RULED + SHIPPED 2026-07-17) & ceiling live-proof status
- PARITY: canonical awaiting-retry = status=error + error_kind=ReconciliationRetryError
  (reconcile-only worker's existing shape adopted; lowest migration cost — all
  consumers already read it: status endpoint error banner, in-flight preflight
  counts it, sweep ignores non-running, retry endpoint is status-agnostic).
  Main worker now flips instead of writing done-with-_reconciliation_error;
  result still stored as evidence. Client retry-poll budget raised 240s→960s
  to match the 900s ceiling. MIGRATION: 4 hollow-done docs found — 55e5e24f
  (est a2329f30) + ddff780b migrated to awaiting-retry; 1170d3f5 + 3921e482
  deleted as exploratory duplicates (register keeps their numbers). DB
  invariant now zero offenders. Pins: test_done_never_coexists_with_unresolved_reconcile_error
  (live DB invariant), test_status_parity_guard_in_both_workers,
  test_client_retry_poll_budget_matches_ceiling. 23/23 green.
- LIVE-PROOF (900s ceiling, end-to-end): BLOCKED EXTERNALLY — the direct
  Anthropic key hit its MONTHLY usage limit ("regain access 2026-08-01 00:00
  UTC", Anthropic 400 invalid_request_error). The retry dispatch itself proved
  the parity machinery live: failure flipped to canonical awaiting-retry, no
  hollow-done, preflight shows both awaiting-retry runs (restart_safe=false,
  honest). PROOF PENDING: fire reconcile-only on ddff780b once the key limit
  is raised (Anthropic console → Settings → Limits) or resets Aug 1.
  PRODUCTION RE-RUNS: blocked by the same key limit, not by code.

## LIVE-PROOF CLOSED — PRODUCTION RE-RUNS UNLOCKED (2026-07-17 23:49 UTC)
Run 4bd3fb35 (interactive re-run, est 48231310): reconcile 403.3s on
anthropic_direct streamed — past both dead ceilings, clean under the 900s
policy; 38,029 output tokens proved the 48k raise necessary (32k would have
clipped). Register variants 1–4 each now carry a pin + a completed live run.
ddff780b retry SKIPPED (redundant spend) and doc deleted as cleanup per
accepted discretion — register keeps its numbers. Canonical b7a26956 +
banked comparison confirmed untouched/authoritative; est 48231310 remains a
test artifact (0 lines, nothing applied, est untouched since 17:35 UTC).
Variance appendix #2 + honest-flag exhibits #2/#3 appended to
haugh_cross_validation memo — comparison NOT reopened. NOTE: 4 older
awaiting-retry runs exist on other estimates (55e5e24f/04c9539b on a2329f30,
8f36abaa on ef8f34c2, 52ef42f1 on ffb7fac6) — pre-existing, not this
incident's; visible to preflight by design.
