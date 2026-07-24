# BLUEPRINT-CARD RESIDUE REPORT — EST-644081 "PREVIOUS READ · 2 PG · 21 MIN"
Report only, no code, nothing clicked. 2026-07-24.

## 1. What that RESTORE is offering — with receipts
A real `ai_blueprint_runs` document EXISTS for EST-644081:
  run faa6e978…, estimate_id ee077937… (EST-644081), user Howard,
  status done, page_count 2, created 2026-07-24 21:21:49 UTC,
  pages `bp_a8967979….jpg, bp_3390c1e1….jpg`.
Its creation time matches the 21:21 UTC handback suite run TO THE MINUTE
(stamp: `2026-07-24 21:21 UTC · 8cd195b · CLEAN`). The source is
`tests/test_blueprint_page_paths_http.py`: its `estimate_id` fixture
"reuses the FIRST EXISTING estimate" — `GET /api/estimates` items[0] — and
POSTs a synthesized two-page reportlab PDF ("Front Elevation Test Page 1"
/ "Back Elevation Test Page 2") against it. `GET /estimates` sorts
`updated_at DESC`, so items[0] is the MOST-RECENTLY-TOUCHED REAL JOB — at
21:21 that was EST-644081, which Howard was actively working. The 17 older
test runs in the collection all target the red-house fixture estimate,
which was items[0] until EST-644081 overtook it. So: the RESTORE was
offering a test artifact — the suite's throwaway synthetic PDF read.

## 2. Scoping verdict: the product mechanism is CLEAN — this is test-data pollution
The Restore banner is SERVER-side and correctly scoped: the modal calls
`GET /measure/ai-blueprint/latest-for-estimate/{est.id}` and the backend
filters `{user_id, estimate_id}` — no localStorage, no device-level state,
no cross-estimate read path (the archived-run fallback carries the same
two-key filter). A restore can never land on the wrong job THROUGH THE
PRODUCT. The defect is upstream: the TEST wrote a real run document onto a
real estimate. It is the leak/clobber defect CLASS, entering through the
test fixture instead of the app.

## 3. What clicking RESTORE would have done
`restoreResume` loads the run's result into the modal PREVIEW (no estimate
write) and adopts its `page_paths`, so TAG PROFILES would open over the two
synthetic test pages. Nothing touches the estimate unless APPLY is then
clicked — at which point the synthetic read's near-empty measurements would
graft onto EST-644081's lines (the clobber realized). Not another job's
pages — the test attached ITS OWN synthetic pages to THIS estimate — but
garbage-in all the same. Exposure window is small: the banner only surfaces
for runs younger than 30 minutes, so it appears only right after a suite
run touches the tests, and only on whichever real estimate was touched
most recently.

## 4. The other two tiles are standing UI, not residue
TAG PROFILES and DEFAULT WASTE 10% (change/clear) are the Blueprints
card's always-rendered affordances. Profile annotations on EST-644081 are
EMPTY (the annotations test resets `{}` after itself — verified in db), and
the waste control reads the estimate's own field. Only the PREVIOUS READ
banner was residue.

## 5. Fix size (when Howard opens it — nothing builds this month)
SMALL, test-side only, two files + one heal:
  a. `test_blueprint_page_paths_http.py` + `test_profile_annotations_http.py`:
     fixtures ALWAYS create a `TEST_`-prefixed throwaway estimate and
     delete it (and the blueprint run doc) on teardown — never reuse
     items[0]. (The annotations test already self-cleans its data but
     still WRITES to a real estimate mid-test; same fix applies.)
  b. Heal with receipts: delete run faa6e978… from `ai_blueprint_runs`
     (and optionally the 17 fixture-estimate test runs) — one query,
     logged in the register.
  c. Optional guard (test-suite doctrine): a conftest tripwire that fails
     any test POSTing measure runs at an estimate not created by the
     suite. Cheap insurance against the pattern recurring.
