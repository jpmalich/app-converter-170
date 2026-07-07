# UX & Accessibility Audit — Blueprint Estimator (Editor + Dashboard)

**Date:** 2026-07-06
**Scope:** The two screens shipped in the Blueprint Instrument redesign — `pages/EstimateEditor.jsx` (+ everything under `components/estimate/`) and `pages/Dashboard.jsx` — plus their shared shell (`components/Layout.jsx`) and the modals they launch.
**Method:** Heuristic evaluation (Nielsen) + WCAG 2.2 AA checks, combining **live instrumentation** of the running app (focus visibility, target sizes, reflow, contrast, landmarks/headings, accessible-name coverage — measured via scripted DOM probes at 1200px and 375px) with a **code survey** of state handling, async guards, and semantics (file:line evidence throughout).

This audit is deliberately grounded in the actual shipped code and rendered DOM — every finding carries measured values or a file:line reference. It is a findings document, not a change set.

---

## Executive summary

The redesign and the accessibility pass that shipped with it **hold up well**: keyboard focus is visible everywhere, the dense editor reflows cleanly to mobile with no horizontal scroll, every interactive control has an accessible name, error handling is consistent (toast + `formatApiError`), and the destructive-action confirmations, ARIA tablist, and label associations from the prior pass are correctly in place.

The gaps that remain cluster around **three themes**: (1) *system status* — a silent autosave path that can lose a contractor's work without any signal; (2) *document semantics* — a long, dense estimate with only a single heading, so there is no structural navigation for screen-reader or keyboard users; and (3) *consistency debt* — a handful of async buttons and native `window.confirm`/`prompt` dialogs that the redesign didn't reach (mostly in the AI/Blueprint measure sub-features).

### Top 5 to fix first
1. **Silent autosave failure** — persistent save errors are swallowed to `console.warn`; the user believes edits are saved when they are not. *(Critical — data loss)*
2. **No heading structure** — ~10 major sections are non-semantic `<div>`s; the estimate body has zero heading navigation after the `h1`. *(High)*
3. **Unguarded async buttons** — Dashboard create/duplicate/export and Editor Quote/Materials/Export can double-submit. *(High)*
4. **Unlabeled controls the label pass missed** — `tax-rate`, `margin-pct`, `margin-slider`, and the Dashboard search input. *(High)*
5. **Native `window.confirm`/`prompt` in AI/Blueprint measure** — inconsistent with the styled `ConfirmDialog`, and one gates a consequential Apply. *(High)*

---

## Severity overview

| # | Finding | Severity | Effort |
|---|---|---|---|
| 1 | Silent autosave failure — no user feedback on save error | **Critical** | M |
| 2 | Section titles are non-semantic divs — no `h2/h3`, no SR navigation | **High** | M |
| 3 | Unguarded async buttons (double-submit) — create/duplicate/export/quote | **High** | S–M |
| 4 | Unlabeled controls: tax/margin/slider + Dashboard search | **High** | S |
| 5 | `window.confirm`/`prompt` in AI Measure Apply + Blueprint waste factor | **High** | M |
| 6 | Draft stamp text fails AA contrast (~3.1:1 @ 10px) | **Medium** | S |
| 7 | No positive autosave affordance ("Saving…/Saved") | **Medium** | S |
| 8 | Small touch targets (tax-toggle 13px, back 20px, sub-24px toggles) | **Medium** | S |
| 9 | Dashboard list load = plain text, layout shift (no skeleton) | **Medium** | S |
| 10 | Load-failure bounces home via `nav()` in render — no error/retry screen | **Medium** | M |
| 11 | Hardcoded English "Saved" toast in an i18n app | **Low** | S |
| 12 | Dimension-line blue 4.64:1 — passes AA but tight at 11px | **Low** | S |
| 13 | No "nothing added yet" hint on an empty tab; no recommended-field cue | **Low** | S |
| 14 | Two stacked sticky top bars on the editor | **Low** | S |

*Effort: S = under an hour · M = a few hours · L = larger.*

---

## Verified strengths (no action needed)

These were measured/confirmed and are working — worth protecting in future changes:

- **Focus visibility:** 0 of 40 sampled interactive elements were missing a focus indicator (outline or box-shadow present throughout).
- **Responsive reflow:** at 375px the editor has no horizontal scroll and no element overflows the viewport.
- **Accessible names:** 0 unnamed buttons/links on either screen; 0 images missing `alt`.
- **Landmarks:** `header` + `nav` (from `Layout.jsx:36,47`) and a per-screen `main` (`Dashboard.jsx:177`, `EstimateEditor.jsx:311`).
- **Consistent error surfacing:** API failures route through `formatApiError` + `toast.error` (Dashboard 68/90/113/207, EstimateEditor 211/258/471, useEstimate 138/478, PhotosPanel 22).
- **Async guards where they matter most:** QuoteModal send/PDF (`sending`), CatalogSyncBanner apply (`busy`), HOVER/Blueprint imports (`busy`) all disable + show progress.
- **Input semantics:** correct `type`/`inputMode` for phone (`tel`), email, numeric, ZIP; inline validation with `aria-invalid` + `aria-describedby` + `role="alert"`.
- **Prior a11y pass intact:** ARIA tablist keyboard nav, Radix confirm/modal dialogs, color-select + Vero/Mezzo label associations, dimension lines, status stamps — all rendering correctly.

---

## Findings

### 1. Silent autosave failure — no user feedback *(Critical · data loss)*
**Evidence:** `lib/useEstimate.js:494-514` — autosave is silent by design and on failure only `console.warn("[autosave] swallowed:", …)` (509). The unmount/`pagehide` flush paths swallow the same way (551, 578). No "saving/saved/failed" affordance exists.
**Impact:** On a persistent failure (network drop, expired session/401), the contractor keeps editing believing the quote is saved. On reload the work is gone — with no prior signal. This is the single highest-risk gap: it's invisible until data is already lost.
**Recommendation:** Surface autosave state. Minimum: on autosave failure show a non-blocking persistent banner ("Couldn't save your changes — retrying" / "Offline — changes not saved") and a retry, rather than a one-shot toast. Pair with finding #7 (a positive "All changes saved" affordance) so the *absence* of "saved" becomes meaningful. Consider a dirty-state guard on navigation/`beforeunload`.

### 2. Section titles are non-semantic divs — no heading navigation *(High)*
**Evidence:** Live probe: the editor renders **1 `h1`, 0 `h2`–`h6`**. All section titles are `<div className="section-tag">` — e.g. `TotalsSummary.jsx:20`, `PhotosPanel.jsx:29`, `SettingsRow.jsx:56/158/183`, `JobInfoPanel.jsx:190`, `VeroPanel.jsx:422`, `MezzoPanel.jsx:376`, `SectionAccordion.jsx:445`; sub-group labels (`SubHeader`) are also plain divs (`JobInfoPanel.jsx:135-143`). The design system already has an `h2` primitive (`DrawingLabel`, `blueprint/index.jsx:67`) that these screens don't use.
**Impact:** A screen-reader user lands on the customer-name `h1` and then has **no heading navigation** through a very long estimate (JobInfo → Settings → Photos → tabs → N accordions → Totals). This is also the root of the orientation issue in finding #15 — structure is purely visual.
**Recommendation:** Promote the ~10 section titles to real headings (`h2`), sub-groups to `h3`. Cleanest path: give `section-tag`/`DrawingLabel` an `as`/`level` prop and render the correct tag, so the visual style is unchanged but semantics land. Verify sequential levels (no skips).

### 3. Unguarded async buttons — double-submit *(High)*
**Evidence:** `Dashboard.jsx:78-93` `createEstimate` (buttons 215-217, 350-352) and `107-115` `duplicate` (button 455-466) have no in-flight guard — double-click creates two estimates / two duplicates. Export-all CSV (`196-211`) and Editor `handleOpenQuote`/`handleOpenMaterials`/`handleExportCsv` (`269-285`, `201-213`) `await` save+PDF+network but their `TotalsSummary` buttons (`TotalsSummary.jsx:41/44/50`) have no `disabled` prop (only Save at 38 is guarded).
**Impact:** Duplicate records, duplicate PDF POSTs, duplicate saves. On a slow connection (contractor in the field) this is easy to trigger.
**Recommendation:** Add an in-flight state to each async handler and disable the button while pending (mirror the pattern QuoteModal already uses with `sending`). A small `useAsyncAction` hook would DRY this across both screens.

### 4. Unlabeled controls the label pass missed *(High)*
**Evidence:** Live probe found 6/32 editor controls and 1/1 dashboard control with no accessible name: `tax-rate` (number), `margin-pct` (number), `margin-slider` (range) in `SettingsRow.jsx`; the **Dashboard search input** (`Dashboard.jsx:209` — placeholder only, which is not a name); and the two hidden file inputs (`hover-import-input`, `blueprint-import-input` — lower priority since a labeled button triggers them).
**Impact:** The margin/tax controls (which set the *sell price*) and search are announced by role only ("edit text", "slider") with no name. The range slider additionally announces no value text.
**Recommendation:** Add `htmlFor`/`id` (or `aria-label`) to tax-rate, margin-pct, and the search input; give margin-slider an `aria-label` + `aria-valuetext` (e.g. "38%"). Quick, mechanical — same pattern as the shipped label pass.

### 5. Native `window.confirm`/`prompt` in AI/Blueprint measure *(High)*
**Evidence:** `AIMeasureButton.jsx:1652` — `window.confirm(...)` gates **Apply** (writes extrapolated/unmeasured wall dimensions into a customer-facing quote). `BlueprintMeasureButton.jsx:602-605` and `677-680` — `window.prompt(...)` to capture Waste Factor % (no validation, unstyled, not i18n). (`BrandingAdmin.jsx:778` has another `window.prompt` outside these two screens.)
**Impact:** Inconsistent with the styled, focus-trapped `ConfirmDialog`/`Modal` used everywhere else; the Apply case is *consequential* (it commits estimated numbers to a quote) yet uses the weakest, unstyled confirmation. Native `prompt` also can't validate the waste %.
**Recommendation:** Replace the `window.confirm` with the existing `ConfirmDialog` (destructive/consequential variant, clear description of what "Apply" writes). Replace the two `window.prompt` waste-factor calls with a small numeric `Modal` field with validation. This finishes retiring the `window.*` dialog debt.

### 6. Draft stamp text fails AA contrast *(Medium)*
**Evidence:** Computed — draft stamp muted `#8493A8` on white sheet ≈ **3.11:1** at 10px/800-weight (not "large text", so AA needs 4.5:1). Sent (blue #1E6FEB ≈ 4.64:1) and Won (green) pass.
**Impact:** The most common status (draft) is the least legible. The outlined box gives a non-color cue, but the label itself is sub-threshold.
**Recommendation:** Darken the draft stamp text (use `--bp-ink-2` rather than `--bp-muted`, or a dedicated stamp-muted token ≥4.5:1). Small CSS change in `blueprint.css`.

### 7. No positive autosave affordance *(Medium)*
**Evidence:** The only saving indicator is the manual Save button label swap (`TotalsSummary.jsx:38-39`), disconnected from the autosave path (`useEstimate.js:494-514`).
**Impact:** Users have no confirmation their edits persist — trust gap, and (with #1) no way to notice a failure.
**Recommendation:** Add a lightweight "Saving… / All changes saved · HH:MM" status near the title block, driven by the autosave lifecycle. Complements #1.

### 8. Small touch targets *(Medium)*
**Evidence:** Measured sub-24px (WCAG 2.5.8) interactive elements: `tax-toggle` 13×13, `estimate-back-btn` 20×20, `billing-same`/`pre-1978`/`vero-package-quote` checkboxes 16×16, plus 14 controls in the 24–44px band (below the 44px comfort target).
**Impact:** The app is used by contractors, plausibly on tablets/in the field; 13px and 20px hit areas are hard to tap accurately.
**Recommendation:** Pad the smallest custom toggles/icon buttons to ≥24px (ideally 44px) hit area via padding (keep the visual size). Native checkboxes are lower priority if their `<label>` wraps and extends the click target — verify that.

### 9. Dashboard list load — no skeleton, layout shift *(Medium)*
**Evidence:** `Dashboard.jsx:343-344` renders plain `{t("common.loading")}` text in the table body; layout shifts when rows arrive. Editor load (`EstimateEditor.jsx:150-158`) is a centered spinner (adequate).
**Recommendation:** Render 3–5 skeleton rows matching the table grid to reserve space and reduce CLS.

### 10. Load-failure bounces home from inside render *(Medium)*
**Evidence:** `EstimateEditor.jsx:151-153` — on load failure the component calls `setTimeout(() => nav("/"), 0)` *during render* (a side-effect in render), with only the transient toast from `useEstimate.js:138`. No dedicated error screen or retry.
**Impact:** A failed/deleted/permission-denied estimate silently ejects the user to the picker; the side-effect-in-render is also a React anti-pattern (should be an effect).
**Recommendation:** Move the redirect into a `useEffect`, and prefer an inline error state ("Couldn't load this estimate" + Retry / Back) over an automatic bounce.

### 11–14. Low severity
- **11 · Hardcoded "Saved"** — `useEstimate.js:475` `toast.success("Saved")` is literal English while the app is i18n (the error path on the same function uses `formatApiError`). Use `t(...)`.
- **12 · Dimension-line contrast** — blue #1E6FEB on white measures 4.64:1; passes AA but tight for 11px. Fine as-is; nudge darker if the value ever shrinks.
- **13 · Missing guidance states** — a tab with catalog sections but no filled lines shows only collapsed `$0` accordions with no "nothing added yet" hint (`EstimatorTabs.jsx:40-44`); no "recommended" cue on `customer_name`/`estimate_number` (empty quotes render "—"). Both are by-design but reduce first-run clarity.
- **14 · Two stacked sticky bars** — Layout `<header>` (sticky, z-40) and `StickyBar` (`.sell-bar`) both pin to the top of the editor, eating vertical space on short viewports.

---

## Not findings (checked and OK)

- **`ConfirmDialog` newline handling** — `SettingsRow.jsx:32-41` builds a multi-paragraph `recomputeConfirmText`; `ConfirmDialog` sets `whiteSpace: pre-line` on the description, so the `\n\n` breaks render correctly (the survey flagged this as a risk; it's handled).
- **Focus indicators, reflow, accessible names, alt text, input types, inline validation** — all verified present (see Strengths).

---

## Suggested sequencing

- **Quick wins (S, do first):** #4 labels, #6 draft-stamp contrast, #11 i18n "Saved", #8 target padding, #9 skeleton. Mostly mechanical, mirror patterns already in the codebase.
- **This-milestone (M):** #1 autosave feedback + #7 saved affordance (do together), #2 heading semantics, #3 async guards (one small hook covers most), #5 finish the `window.*` dialog retirement.
- **When touching those areas (M):** #10 load-error screen.

Items #1, #3, #4, #5 also extend audit debt already retired elsewhere — folding them in keeps the a11y/status story consistent across the whole app.
