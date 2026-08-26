# SEND-131A — PHOTO TAKEOFF PHASE 1: BUILT, PINNED, GREEN (2026-08-26)

Stamp (full local suite, run twice — second run clean first-time):
`2026-08-26 · CLEAN · 2919 passed, 9 skipped, 7 warnings in 445.49s`
· census `census pin GREEN — 6 baselined reads, 0 PENDING_CONVERSION`
· ingress smoke `4 passed in 1.82s`
(2891 → 2919 = the 28 new SEND-131A pins.)

## THE RULING EXECUTED
The contractor works on the PHOTOS. Not on renders made from them.

1. **THE ROUTE WAS DEAD ON ARRIVAL.** `routes/photo_takeoff.py` existed
   from the previous session but was **never mounted** — zero endpoints
   were live and nothing pinned it. Registered in `routes/__init__.py`;
   a pin now fails the suite if the router is ever unmounted (a route
   file nobody mounts is a route file that does nothing).

2. **PHASE 1 BACKEND** — `/api/estimates/{id}/photo-takeoff`
   (GET · scale PUT · marks POST/PATCH/DELETE · import-annotations POST
   · apply POST). `photo_key` is the photo FILENAME — the same key
   `photoAnnotations` already uses, so imports line up by construction.
   Marks live in the photo's NATURAL PIXELS in `photo_takeoff_marks`;
   scale in `photo_takeoff_scale`.

3. **THE DISCIPLINE, CARRIED VERBATIM FROM THE BLUEPRINT LANE:**
   - a mark lands **PROVISIONAL** and carries NO quantity; the
     unconfirmed marks are counted and NAMED on the surface;
   - **THE TAPE WINS** over the two-tap anchor on the same span; the
     anchor figure is kept and the label says which governs;
   - **no anchor and no tape → no quantity and a NAMED refusal**; a
     tape with no span is refused 400 ("the tape describes THAT span");
   - **a lane with no confirmed mark of its kind reports None, NEVER 0**
     (a zero reads as "measured and empty");
   - **adjusting a confirmed mark returns it to PROVISIONAL** — a
     confirmation cannot outlive the figure it was given for;
   - a **phase-2 kind** (outside/inside corner, J-channel, starter,
     soffit, fascia, finish trim) is **refused and named**, never
     silently stored as an area mark;
   - **423 on protected estimates** for `apply` (a derived write).

4. **AN OPENING TAP CARRIES A COUNT, NOT AN AREA.** The annotator's
   tagged windows are TAPS, not boxes: they import as POINT openings —
   a count with **no ft², named** (`openings_without_extent_note`),
   never a silent 0. Box one here to give it an area.

5. **OPENINGS REPORT SEPARATELY — NO DEDUCTION IN PHASE 1** (ruled).
   `openings_deducted: false` rides every quantity payload and the
   right rail prints it. The blueprint lane's deduction ruling does
   NOT carry here; deduction gets its own ruling once both numbers are
   visible.

6. **APPLY WRITES A SEPARATE PHOTO LANE, QUANTITY ONLY.** Four keys at
   the estimate's top level (`photo_siding_sqft`,
   `photo_non_siding_sqft`, `photo_opening_sqft`,
   `photo_opening_count`) plus the full `photo_takeoff` record. They do
   **NOT** enter `hover_measurements` or any blueprint/derived total
   (pinned). They sit outside `EstimateIn`, so no client save can
   carry, alter or strip them — **the silent-strip class cannot reach
   this lane by construction**. A structural pin fails on any price /
   money / `lines` token appearing in the module.

7. **THE EDITOR** — `PhotoTakeoffEditor.jsx`, full-screen, one photo at
   a time, shaped after `PdfOverlayEditor`: same snap conventions, the
   overlay editor's siding blue + the annotator's own material colours
   (no new colour system), floating cursor-anchored zoom, **pinch-zoom
   on a phone**, and vertex drag on WINDOW pointer events normalised
   against the rendered rect exactly once — **tracks the finger 1:1 at
   any zoom** (the blueprint editor's SEND-50 fix, same invariant).
   Right rail: scale (two-tap + typed tape, label states which
   governs), live quantities with every refusal named, marks list with
   **Confirm / Refuse / Adjust / Delete** per mark, "pull in what I
   already drew", and Apply.

8. **ENTRY POINT** — a per-photo **Photo Takeoff** button in the AI
   Photo Measure grid, **beside** `Annotate`. Annotate stays the pre-AI
   annotator; Photo Takeoff is where quantity is made. Neither replaces
   the other (pinned).

9. **PHOTO-GENERATED ELEVATIONS ARE OUT OF THE CONTRACTOR VIEW.** One
   named flag `PHOTO_ELEVATIONS_ENABLED = false` (stop-loss doctrine,
   same shape as `RENDER_3D_ENABLED`): the panel mount, the FieldVerify
   sheet links, and both frontend print routes are gone from the
   contractor UI. **NOTHING DELETED** — `ElevationSheet.jsx`,
   `ElevationSheetsPrint.jsx`, `ElevationSheetsPanel.jsx` and the
   backend `/elevation-sheet/{which}` route with all its pins stay
   intact. **BLUEPRINT elevation sheets are a different route and are
   untouched** (pinned both ways).
   **TWO NAMED PIN UPDATES** (stale by the ruling, never silently
   flipped): `test_inline_elevation_sheets.py::test_editor_mounts_the_section`
   now asserts the FLAG GATE, and
   `test_print_package_pins.py::test_route_registered` now asserts the
   RETIREMENT and names why. One baseline entry added to the surface
   census with its reason (four VALUE-HELPER null returns in the
   editor — null IS the answer, and the surface prints the refusal).

## VERIFICATION
- 28 pins: `tests/test_send131a_photo_takeoff_2026_08_26.py` (live HTTP
  on a disposable estimate + structural).
- Full suite green twice; census GREEN; ingress smoke 4 passed.
- Browser end-to-end (testing agent, `test_reports/iteration_58.json`):
  all 8 photo cards carry BOTH buttons; provisional carries `—` not 0;
  anchor 10 ft → 37.35 ft², a 20 ft TAPE → 149.38 ft² (×4 on a doubled
  span — quadratic, exactly right) with the label flipping to TAPE
  GOVERNS; refuse empties the lane; vertex drag moved 80 px in one
  drag and returned the mark to provisional with the re-confirm reason;
  brick zone 30.86 ft² landed in the per-category chip; a confirmed
  opening (count 1, 11.11 ft²) did NOT reduce siding; second import
  press imported nothing; no `elevation-sheets-section` anywhere and
  both photo-elevation routes fall through while
  `blueprint-elevation/front` still renders. **Zero defects.**
- Test residue cleaned: the browser pass left 2 marks + 1 scale on the
  real Letrick estimate; both collections purged for that id (no test
  residue on a real estimate).

## PHASE 2 — NOT BUILT, NAMED
Linear trim runs: outside corners · inside corners · J-channel ·
starter · soffit · fascia · finish trim. The kinds are declared and
refused today; a pin fails if the phase boundary goes silent.

## OPEN / AWAITING HOWARD
- **The deduction ruling** for photo openings (report-only today).
- Where the photo lane's ft² should meet the existing measurement
  lanes, if ever (it is deliberately separate right now).
- Whether the photo takeoff needs a run-pollution tripwire of its own
  (the conftest tripwire covers measure-run docs, not takeoff marks —
  today's residue was cleaned by hand).
- Blueprint work stays **PARKED**: symbols placement, foreign-drafter
  generality lifts, the material-card confirm write path (423), the
  walkout manual-entry surface.

