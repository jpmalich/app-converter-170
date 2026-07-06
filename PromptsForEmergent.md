# Prompts for Emergent

Copy-pasteable prompts for the Emergent AI tool (https://app.emergent.sh) that replicate
changes made in this repository into the Emergent-hosted version of the app.

**How to use:** open the Emergent project chat and paste the prompt block of any entry not
yet applied there, oldest first. Each prompt is self-contained — it describes the change by
rule and intent so the Emergent agent can implement it without seeing this repo's diffs.

**Maintenance rule:** every time a feature or change is completed in this repo, a new entry
is appended here (newest at the bottom) — date, summary, and the ready-to-paste prompt.
**When later work changes something an existing entry covers, that entry's prompt is updated
in place and its revision is bumped** — never silently. Each entry carries a `Revision` line
and a `Change log` naming what caused each update, so you can tell whether a prompt you
already applied in Emergent needs to be re-run.

**Sync status table** — check the box when you apply an entry in Emergent and note the
revision you applied. If the table's *current* revision is newer than the one you applied,
re-run that entry's prompt (they are written to be safely re-applied in full).

| # | Entry | Current rev | Last updated | Applied in Emergent? (you fill in) |
|---|---|---|---|---|
| 1 | WCAG accessibility pass + icon cleanup | r2 | 2026-07-04 | ☐ rev: ____ date: ____ |
| 2 | Theme picker (tokens + six themes) | r1 | 2026-07-03 | ☐ rev: ____ date: ____ |
| 3 | Customer contact & company fields | r3 | 2026-07-03 | ☐ rev: ____ date: ____ |
| 4 | Auto-populate estimate fields at creation | r1 | 2026-07-03 | ☐ rev: ____ date: ____ |
| 5 | Soft input validation + format tips | r2 | 2026-07-03 | ☐ rev: ____ date: ____ |
| 6 | Post-merge adaptations (2026-07-04 code merge) | r1 | 2026-07-04 | ☐ rev: ____ date: ____ |

**Excluded by design:** anything related to decoupling this repo from the Emergent platform
(the direct-Anthropic LLM client, Docker self-hosting, removal of Emergent branding/telemetry,
dependency swaps). Those changes are intentionally NOT for replication into Emergent.

---

## 1 — WCAG AA accessibility pass + emoji-to-SVG icon cleanup (2026-07-02)

**Revision:** r2 · last updated 2026-07-04
**Change log:**
- r1 (2026-07-02) — initial
- r2 (2026-07-04) — after merging your iters 79j.15–.34 into this repo, one NEW emoji UI
  icon exists that r1's list predates: the "🔁 Re-run" button on the AI Measure preview →
  replace with a lucide <RefreshCw> inline icon + "Re-run" text (aria-hidden, w-3). Also
  note: RULES 1–3 apply equally to the newer AI components (AIMeasureButton additions,
  BlueprintMeasureButton 3D tab, HouseModel3D UI chrome) — re-sweep those files.

**If you applied r1 in Emergent:** only the r2 additions above are new — apply them
directly; no need to redo the full pass.

**What changed here:** ~410 context-sensitive contrast fixes across 63 frontend files, emoji
UI icons replaced with lucide SVGs, reduced-motion support, and the rules codified in
`design_guidelines.json`.

**Prompt for Emergent:**

```
Apply a WCAG AA accessibility pass to the entire React frontend. Keep the existing
Swiss/industrial brand (safety orange #F97316 on white/concrete grays) — change only the
tokens below, judging each occurrence by the effective background behind it (walk up the
JSX tree; modal headers and the sticky sell-bar are often black #09090B while bodies are
white).

RULE 1 — muted gray text #A1A1AA (2.56:1 on white — fails WCAG):
- As TEXT or ICON color on a light background (white, #FAFAFA, #F4F4F5 — the app default):
  replace #A1A1AA with #71717A (4.83:1).
- On a dark background (bg-[#09090B], bg-black, dark overlays/headers): KEEP #A1A1AA
  (7.76:1 on black — changing it there would be a regression).
- As a BORDER color or canvas/SVG drawing color (measurement lines drawn over photos):
  leave unchanged.

RULE 2 — brand orange as text, text-[#F97316] (2.80:1 on white — fails):
- On a light background: replace with text-[#C2410C] (5.18:1).
- On a dark background (sticky sell-bar active tab/sell price, black modal headers,
  dark logo boxes): KEEP text-[#F97316] (7.10:1 on black).
- bg-[#F97316] fills, border-[#F97316] accents, focus rings, canvas colors: leave unchanged.
- Inline-style JS constants that feed style={{color}} on light rows count as text colors —
  darken those too.

RULE 3 — orange buttons with white labels (2.80:1 — fails):
- Any element whose className contains BOTH bg-[#F97316] AND text-white: change text-white
  to text-[#09090B]. Black-on-safety-orange is 7.10:1 and fits the industrial brand.
  This includes .btn-primary in index.css, orange modal/submodal headers, count badges,
  and orange CTA links in the generated email HTML (lib/emailQuote.js) and print documents
  (lib/printTakeoff.js, lib/materialList.js — their standalone HTML is white-backed, so
  Rule 1 and 2 apply there as well).

RULE 4 — global CSS (src/index.css):
- :root --muted becomes #71717A; add --brand-text: #C2410C.
- .input:focus border-color uses #C2410C (focus indicators need 3:1 against white; #F97316
  is only 2.80:1).
- Add a prefers-reduced-motion block that zeroes animation/transition durations:
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after {
    animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important; scroll-behavior: auto !important; } }

RULE 5 — replace emoji glyphs used as UI icons with lucide-react SVG icons (the library is
already installed). Known instances and their replacements:
- "🔍 Deep Verify" (HoverImportButton, both occurrences) → <ScanSearch> inline icon + text
- "⚡ Fast Track" (GuidedCaptureWizard toggle) → <Zap>
- "💡 Gable ft² …" hint and both "🔍 …" labels in AIMeasureButton → <Lightbulb> / <ScanSearch>
- "✏️ Precision · Pencil" chip (PhotoAnnotateModal) → <Pencil>
- Guided step titles in PhotoAnnotateModal: 🎯→<Crosshair>, 📏→<Ruler>, 🪟→<AppWindow>,
  🧱→<BrickWall>, 🏠→<Home>
- "✨ Auto-detect" (ProfileAnnotator) → <Sparkles>
- 💡 feedback-banner glyph (Dashboard) → <Lightbulb>
Give each icon aria-hidden="true" and a small inline size (w-3/w-4). Do NOT touch the
ASCII/pictograph positioning diagrams in GuidedCaptureWizard ("🏠 ← YOU (25-30 ft)" etc.) —
those are instructional content, not UI icons.

RULE 6 — small component fixes:
- EmailPipeline: the shared Stage badge applies one literal text-white over four fill
  colors; add a per-stage textColor prop (default text-white) and pass text-[#09090B] for
  the light gray "Sent" and orange "Clicked" stages.
- SectionAccordion "commonly needed" rows: keep the yellow tint + Lightbulb icon pairing
  (non-color cue), bump the icon to text-yellow-700, and use #C2410C for the
  orange-outline badges' text.
- InstallBanner: the Smartphone icon inside the orange tile gets text-[#09090B].

Finally, record these rules in design_guidelines.json: set colors.text.muted to #71717A,
add colors.brand.primary_text_on_light #C2410C, set borders.focus to #C2410C, change the
primary_button spec to black label text, set icons_strategy to lucide-react with a
"never use emoji as UI icons" note, and add an "accessibility" section stating: text on
light >= 4.5:1; orange text on light uses #C2410C; orange buttons use black labels;
#A1A1AA only on dark; focus indicators >= 3:1; reduced motion honored; never rely on
color alone.

Verify when done: no text-[#A1A1AA] remains on light surfaces, no className combines
bg-[#F97316] with text-white, no emoji UI icons remain, and the app builds.
```

---

## 2 — Theme picker: semantic tokens + six WCAG-validated themes (2026-07-03)

**Revision:** r1 · last updated 2026-07-03
**Change log:**
- r1 (2026-07-03) — initial

**What changed here:** all hardcoded Tailwind hex classes migrated to CSS-variable tokens
(~2,100 replacements), six themes defined in `index.css`, a ThemePicker component added to
the header and Team page, FOUC guard in `index.html`, and a contrast-gate validator script.
*Prerequisite: the accessibility pass in entry 1 must already be applied.*

**Prompt for Emergent:**

```
Implement a user-selectable theme system for the React frontend. It restyles ONLY the
contractor's working UI — customer-facing surfaces (QuoteModal, AcceptPage, and the
generated HTML in lib/emailQuote.js, lib/materialList.js, lib/printTakeoff.js) keep the
neutral document style and must be EXCLUDED from every step below.

STEP 1 — tokens (src/index.css). Extend :root with this semantic token set (values = the
current Safety Orange look): --bg-app #F4F4F5, --surface #FFFFFF, --surface-muted #FAFAFA,
--table-header #E4E4E7, --ink #09090B, --ink-2 #52525B, --muted #71717A, --border #E4E4E7,
--border-strong #09090B, --edge #09090B, --focus #C2410C, --brand #F97316, --brand-hover
#EA580C, --brand-text #C2410C, --on-brand #09090B, --bar-bg #09090B, --bar-ink #FFFFFF,
--bar-muted #A1A1AA, --ai #7C3AED, --ai-soft #F5F3FF, --profit #059669, --success #16A34A,
--warning-text #92400E, --danger #EF4444, --danger-text #DC2626, --danger-soft #FEF2F2,
--hint-bg #FEFCE8, --hint-bg-2 #FEF9C3, --hint-line #FACC15, --hint-ink #A16207,
--hint-ink-2 #713F12. Rewrite the component classes (.btn-primary/.btn-secondary/
.btn-ghost/.btn-danger/.input/.label/.card/.section-tag/.sell-bar and body) to use these
variables — e.g. .btn-primary is bg var(--brand), color var(--on-brand), border+hard-shadow
var(--edge); .sell-bar is background var(--bar-bg), border-bottom 2px var(--brand).

STEP 2 — theme blocks. Add [data-theme="…"] blocks overriding only what differs:
- blueprint: --bg-app #F2F4F8, --ink #0C1220, --ink-2 #475569, --muted #64748B, --border
  #DBE1EA, --border-strong/--edge/--bar-bg #0C1220, --focus #1D4ED8, --brand #2563EB,
  --brand-hover #1D4ED8, --brand-text #1D4ED8, --on-brand #FFFFFF
- forest: --bg-app #F1F5F1, --ink #0A0F0B, --ink-2 #44554A, --muted #5F6F65, --border
  #DDE4DE, --border-strong/--edge/--bar-bg #0A0F0B, --focus #166534, --brand #15803D,
  --brand-hover #166534, --brand-text #166534, --on-brand #FFFFFF
- steel: --bg-app #F2F4F6, --ink #0B0F14, --ink-2 #475569, --muted #64748B, --border
  #DDE2E8, --border-strong/--edge/--bar-bg #0B0F14, --focus #334155, --brand #334155,
  --brand-hover #1E293B, --brand-text #334155, --on-brand #FFFFFF
- highvis: --focus #854D0E, --brand #FACC15, --brand-hover #EAB308, --brand-text #854D0E,
  --on-brand #09090B
- dark: --bg-app #0B0B0D, --surface #18181B, --surface-muted #1F1F23, --table-header
  #27272A, --ink #FAFAFA, --ink-2 #D4D4D8, --muted #A1A1AA, --border #2E2E33,
  --border-strong #FAFAFA, --edge #000000, --focus #FB923C, --brand #F97316, --brand-hover
  #FB923C, --brand-text #FB923C, --on-brand #09090B, --bar-bg #27272A, --bar-ink #FAFAFA,
  --ai #A78BFA, --ai-soft #2A2440, --profit #34D399, --success #4ADE80, --warning-text
  #FBBF24, --danger #F87171, --danger-text #F87171, --danger-soft #3A1A1A, --hint-bg
  #2A2415, --hint-bg-2 #332B15, --hint-line #854D0E, --hint-ink #FACC15, --hint-ink-2 #FDE68A

STEP 3 — codemod every .jsx/.js under src (EXCEPT the excluded customer files and
components/ui/), rewriting ONLY bracketed utility classes and plain bg-white — never inline
styles or JS color strings (canvas/SVG drawing colors must stay literal). Ordered rules:
(a) on lines containing bg-[#F97316]: text-[#09090B] → text-[var(--on-brand)]
(b) focus:border/ring/outline-[#F97316] → …[var(--focus)]
(c) #F97316 → var(--brand) (bg/text/border/accent/decoration/ring);
    #EA580C → var(--brand-hover); bg-[#C2410C] → var(--brand-hover);
    text/border-[#C2410C] → var(--brand-text)
(d) bg-[#09090B] → bg-[var(--bar-bg)]; text-[#09090B] → text-[var(--ink)];
    border-[#09090B] → border-[var(--border-strong)]
(e) #52525B → var(--ink-2); #71717A → var(--muted);
    text-[#A1A1AA] → text-[var(--bar-muted)]; border/bg-[#A1A1AA] → var(--muted)
(f) bg-white → bg-[var(--surface)] (word-boundary — do NOT touch bg-white/50 opacity
    variants); bg-[#F4F4F5] → bg-[var(--bg-app)]; bg-[#FAFAFA] → bg-[var(--surface-muted)];
    bg-[#E4E4E7] → bg-[var(--table-header)]; border-[#E4E4E7] → border-[var(--border)];
    border-[#F4F4F5] → border-[var(--bg-app)]
(g) #7C3AED → var(--ai); bg-[#F5F3FF]/bg-[#EDE9FE] → bg-[var(--ai-soft)]
(h) text-[#DC2626] → var(--danger-text); #EF4444 → var(--danger); bg-[#FEF2F2] →
    var(--danger-soft); #16A34A/#10B981 → var(--success); text-[#059669] → var(--profit);
    text-[#92400E]/text-[#B45309] → var(--warning-text)
(i) bg-yellow-50 → bg-[var(--hint-bg)]; bg-yellow-100 → bg-[var(--hint-bg-2)];
    border-yellow-400 → border-[var(--hint-line)]; text-yellow-700 → text-[var(--hint-ink)];
    text-yellow-900 → text-[var(--hint-ink-2)]
Leave soft pastel banner colors (#FEF3C7, #FFF7ED, #F0F9FF, sky #0EA5E9, deep purple
#6D28D9, gradients) literal.

STEP 4 — picker. Create src/lib/themes.js: THEMES registry (auto / orange / blueprint /
forest / steel / highvis / dark) with 3-color swatch chips, localStorage key "ui-theme-v1",
applyTheme() sets/removes data-theme on <html> ("orange" clears it; "auto" resolves
prefers-color-scheme dark→dark else orange), setTheme(), watchSystemTheme(). Create
src/components/ThemePicker.jsx: palette-icon button (btn-ghost) opening a Radix Popover
(components/ui/popover) with a role="radiogroup" list — each row = 3-dot swatch chip +
theme name + check on active, aria-checked, instant apply on click, aria-live status.
An `inline` prop renders the list without the popover. Mount <ThemePicker /> in the Layout
header next to <LangToggle />, and an inline card on the Team page ("does not affect
customer quotes" blurb). Bilingual labels via the i18n dictionaries (theme.toggle.aria
Theme/Tema, theme.auto, theme.orange "Safety Orange", theme.blueprint "Blueprint Blue",
theme.forest "Forest Green", theme.steel "Steel", theme.highvis "High-Vis Yellow",
theme.dark "Jobsite Dark", theme.status "Theme: {name}", theme.blurb). Apply the stored
theme at boot in src/index.js and watch the OS scheme.

STEP 5 — FOUC guard + SW. Add an inline <script> to public/index.html <head> that reads
localStorage "ui-theme-v1" (default auto), resolves auto via prefers-color-scheme, and sets
data-theme before first paint. Bump the service-worker cache name in public/sw.js so the
cached shell refreshes.

Verify: the app builds; switching themes restyles the whole UI instantly including the
sticky sell-bar accent; Jobsite Dark shows dark surfaces with readable text everywhere;
the quote preview/accept page stay unthemed; reload preserves the chosen theme without a
flash of the default.
```

---

## 3 — Customer contact & company fields on estimates (2026-07-03)

**Revision:** r3 · last updated 2026-07-03
**Change log:**
- r1 (2026-07-03) — initial: 10 contact/company/lead fields, Contact & Lead block, email
  sync, quote/CSV integration
- r2 (2026-07-03) — Job Information form reorganized into four logical groups
  (Customer / Contact & Lead / Job & Billing Address / Estimate); STEP 3 layout rewritten
- r3 (2026-07-03) — addresses broken into structured Street/City/State/ZIP parts with a
  composed-string sync + legacy parse (STEP 1 schema + STEP 3 address group rewritten);
  added STEP 6b browser-autofill handling

**If you applied r1 or r2 in Emergent:** re-run the full prompt below — it supersedes the
earlier revisions and is safe to apply over them.

**What changed here:** 10 new customer fields on the estimate (email, cell + secondary
phone, fax, preferred contact method, company + contact title, billing address, lead
source + detail), a "Contact & Lead" block in the Job Information panel, two-way email
sync with the send-quote dialog, and the fields flowing into the quote document and CSVs.

**Prompt for Emergent:**

```
Add customer contact/company fields to estimates. Everything is optional — nothing blocks
drafting or autosave; email is only needed to send a quote.

STEP 1 — backend/models.py, class EstimateIn (after `notes`): add ten fields, each
`Optional[str] = None` (NOT ""), so the PUT handler's model_dump(exclude_none=True) means
partial payloads never clobber stored values: customer_email, customer_phone (cell),
customer_phone_alt (landline), customer_fax, customer_contact_method (slug
cell|landline|email|text|""), customer_company, customer_contact_title, billing_address
(empty string means "same as job address" — no boolean flag), lead_source (slug),
lead_source_detail (free text). ALSO add structured address parts (the composed `address`
and `billing_address` strings stay canonical — every consumer keeps reading them):
address_street, address_city, address_state, address_zip, billing_street, billing_city,
billing_state, billing_zip.

STEP 2 — frontend/src/lib/useEstimate.js buildPayload (the explicit whitelist): add one
line per field after `notes`; .trim() the email/phone/fax values; plain `|| ""` for the
rest. Loading needs no change (initial load spreads the API doc).

STEP 3 — JobInfoPanel.jsx: reorganize the whole Job Information form grid into FOUR
logically grouped sections, each introduced by the small uppercase mini-header pattern
(same style as the Material Colors header):
1. "Customer" — Customer name (cust-name) · Company (cust-company) · Contact Title
   (cust-contact-title).
2. "Contact & Lead" — Row 1: Cell Phone (type=tel, cust-phone) · Secondary Phone
   (cust-phone-alt) · Fax (cust-fax). Row 2: Email (type=email, cust-email) · Preferred
   Contact select (cust-contact-method: — /Cell/Landline/Email/Text) · Lead Source select
   (lead-source) with presets referral, repeat_customer, web, social, yard_sign,
   truck_wrap, home_show, supplier, door_knock, other (slug values persist; labels via
   i18n); when the value is "other" or "referral", reveal a small text input
   lead-source-detail in the same cell.
3. "Job & Billing Address" — the job address is FOUR fields on one row: Street
   (cust-street, half width) · City (cust-city) · State (cust-state, a select of the 50
   US state + DC abbreviations) · ZIP (cust-zip, inputMode numeric, maxLength 10). On any
   part change, also recompose the canonical single-line `address` string
   ("street, city, ST zip") so quote docs/CSVs/geocoding keep working. When the
   structured parts are all empty but a legacy `address` string exists, best-effort
   parse it (zip regex at end, 2-letter state token, first comma segment = street) for
   display only — persist parts on first edit. Below it, a full-width checkbox "Billing
   address same as job address" (billing-same-checkbox), CHECKED when billing_address is
   empty; unchecking copies the job parts into billing_street/city/state/zip +
   billing_address and reveals the same four-field grid (billing-street/-city/-state/
   -zip); re-checking clears all five billing fields.
4. "Estimate" — Estimate # (est-num) · Date (est-date) · Estimator (estimator-name), then
   the full-width Scope of Work textarea (notes-input).
Every label gets htmlFor/id.
Header: when customer_email is empty, show the standard lightbulb hint badge (hint tokens
+ Lightbulb icon) reading "Add email to send quotes" (testid contact-hint), visible even
when the panel is collapsed. Collapsed summary line: append customer_company after the
name and one contact chip (customer_phone || customer_email).

STEP 4 — two-way email sync. QuoteModal: initialize the recipient input from
estimate.customer_email || estimate.recipient_email; when the estimate has no
customer_email, show a small note "This email will be saved to the estimate." In
EstimateEditor's onEmail success path: if the sent address differs from
est.customer_email, call update({ customer_email: recipient_email }) so autosave persists
it; ALSO replace the `Object.assign(est, data)` post-send refresh with a proper state
update (the mutation never re-renders). Same write-back in ISSEstimateEditor's onEmail via
its updateField.

STEP 5 — ISS editor customer grid: add Email (iss-customer-email, type=email) and Cell
Phone (iss-customer-phone, type=tel) inputs. Its payload spreads the whole estimate, so no
payload change is needed.

STEP 6 — displays/exports. Quote "Prepared For" block in BOTH QuoteModal's printable area
and lib/emailQuote.js buildEmailHtml: company name (bold) above the customer name; a small
"phone · email" line under the address; a "Billing: …" line when billing_address is set.
NEVER print lead_source, fax, or contact method on customer documents.
backend/routes/estimates.py: all-estimates CSV gains Email, Phone, Company, Lead Source
columns after Address; the single-estimate CSV gains rows for all ten fields.
Dashboard search filter: also match customer_email, customer_phone, customer_company.
AcceptPage, material list, print takeoff, measurement report: unchanged.

STEP 6b — browser autofill: these are the CUSTOMER's details, not the signed-in user's,
so give every contact/address input autoComplete="off"; and since Chrome may autofill
anyway, add a CSS override so autofilled inputs keep the theme colors instead of Chrome's
pale-blue fill: .input:-webkit-autofill (+ :hover/:focus and select.input variant) with
-webkit-box-shadow: 0 0 0 1000px var(--surface) inset; -webkit-text-fill-color: var(--ink);
caret-color: var(--ink); and a very long background-color transition.

STEP 7 — i18n: add EN + ES keys for every new label (est.contactInfo "Contact & Lead"/
"Contacto y Origen", est.email, est.phoneCell, est.phoneAlt, est.fax, est.contactMethod +
.cell/.landline/.email/.text, est.company, est.contactTitle, est.billingSame,
est.billingAddress, est.leadSource + the ten preset keys, est.leadSourceDetail,
est.contactHint, quote.emailWillSave).

Verify: PUT an estimate with the new fields then GET returns them; a PUT omitting them
does not clobber; fill the fields in the editor, reload, they persist; the billing
checkbox round-trips; QuoteModal prefills from the saved email and sending to a new
address updates the estimate; both CSVs include the new columns; the hint badge
disappears once an email is entered; Spanish labels render.
```

---

## 4 — Auto-populate estimate fields at creation (2026-07-03)

**Revision:** r1 · last updated 2026-07-03
**Change log:**
- r1 (2026-07-03) — initial

**What changed here:** new estimates pre-fill the Estimator (logged-in user's name), the
Date (today, local), and the job State (company's last-used state). Fill-if-empty only —
client-provided values always win. *Depends on entry 3 (the address_state field).*

**Prompt for Emergent:**

```
Auto-populate estimate fields the app already knows at creation time. Fill-if-empty ONLY —
never override a value the client sent, and the contractor can edit everything afterward.

BACKEND — in the POST /api/estimates create handler (routes/estimates.py), after building
the doc from the request body:
- if `estimator` is empty, set it to the creating user's name (user.get("name") or "").
- if `estimate_date` is empty, set it to today's date (YYYY-MM-DD from the same UTC `now`
  timestamp already used for created_at) as a server-side fallback.
- if `address_state` is empty, look up the company's most recently updated estimate that
  has a non-empty address_state (find_one filtered by company_id and
  address_state $nin [None, ""], sorted by updated_at descending) and copy its
  address_state — most jobs are local, so the last-used state is an excellent default.

FRONTEND — Dashboard's createEstimate already sends estimate_date, but it uses
new Date().toISOString().slice(0,10), which is the UTC date — an estimate created in the
evening US-time gets dated tomorrow. Change it to the LOCAL date:
new Date().toLocaleDateString("en-CA") (yields YYYY-MM-DD in local time).

Verify: create an estimate from the dashboard while logged in — the editor opens with
Estimator = your name, Date = today (local), and State pre-selected to the state used on
the company's previous estimate; creating via API with explicit estimator/date/state
keeps the provided values untouched.
```

---

## 5 — Soft input validation + format tips on contact fields (2026-07-03)

**Revision:** r2 · last updated 2026-07-03
**Change log:**
- r1 (2026-07-03) — initial
- r2 (2026-07-03) — format examples looked like populated data at first glance; placeholders
  are now globally styled as hints (dimmed 55% + italic via .input::placeholder) and all
  example placeholders carry an "e.g. " prefix ("e.g. (412) 555-0100"), EN + ES

**If you applied r1 in Emergent:** re-run the full prompt below — it supersedes r1 and is
safe to apply over it.

**What changed here:** format placeholders + warn-don't-block validation on the customer
contact fields (email/phone/fax/ZIP), phone auto-formatting on blur, and an invalid-email
gate on the quote Send button. *Depends on entry 3 (the contact fields).*

**Prompt for Emergent:**

```
Add soft input validation to the customer contact fields. Policy: WARN, don't block —
empty values are always allowed (requiredness is handled at the action that needs the
field); warnings appear only after the user first leaves a field (blur) and clear live
once the value is fixed.

STEP 1 — create src/lib/validate.js with four helpers, each treating EMPTY as valid:
isValidEmail (basic something@something.tld regex), isValidPhone (strip non-digits; valid
if exactly 10 digits, or 11 starting with 1), isValidZip (/^\d{5}(-\d{4})?$/), and
formatPhoneUS (if the digits are cleanly 10 — or 11 with a leading 1 — return
"(AAA) BBB-CCCC"; otherwise return the input untouched, so extensions/international
numbers are never mangled).

STEP 2 — JobInfoPanel: track a per-field `touched` state set on blur. Add a global
placeholder style so format examples can never be mistaken for populated values:
.input::placeholder { color: var(--muted); opacity: .55; font-style: italic; }. For Email
(placeholder "e.g. name@example.com"), Cell Phone, Secondary Phone, Fax (placeholder
"e.g. (412) 555-0100"), and both job + billing ZIP (placeholder "e.g. 15222") — the
"e.g." prefix is part of the fix and needs EN ("e.g.") + ES ("p. ej.") variants: when touched AND
non-empty AND invalid, render a small warning line under the field using the theme's
--warning-text token ("Doesn't look like a valid email address" / "…phone number —
expected 10 digits, e.g. (412) 555-0100" / "ZIP should be 5 digits, or ZIP+4"), and set
aria-invalid + aria-describedby pointing at the warning element's id. On blur of the
three phone-ish fields, also run formatPhoneUS and write the normalized value back if it
changed. Add EN + ES dictionary keys for the three messages.

STEP 3 — ISS editor: same treatment (placeholder + blur warning + phone auto-format) on
its Email and Cell Phone inputs.

STEP 4 — QuoteModal (send dialog): compute emailInvalid = non-empty AND !isValidEmail.
When invalid, show a bold inline warning next to the recipient input and DISABLE the
Send button (this is the required-at-send gate — the backend's EmailStr validation would
reject it with an ugly 422 anyway; fail helpfully in the UI instead). The "will be saved
to the estimate" note shows only when the email is not invalid.

Verify: type "sdasdsf.com" in the estimate's Email field and tab away — warning appears
and aria-invalid=true; fix it — warning clears live. Type 4125550100 in Cell Phone and
tab away — it becomes (412) 555-0100. In the send-quote dialog, a malformed recipient
email shows the warning and keeps Send disabled.
```

---

## 6 — Post-merge adaptations from the 2026-07-04 code merge

**Revision:** r1 · last updated 2026-07-04
**Change log:**
- r1 (2026-07-04) — initial

**What changed here:** we merged your Emergent build's iters 79j.15–.34 (3D house model,
model A/B suite, waste-baking, prompt overhaul, bug fixes) into this repo. Most of that
work is already in your Emergent project — but the merge produced a few improvements on
our side that Emergent does NOT have, plus follow-ups so earlier entries cover the new
files. **Deliberately NOT replicated:** our trim of the model registry/dropdown to
Claude-only — that is decoupling-related; Emergent's universal key should keep offering
Gemini/GPT.

**Prompt for Emergent:**

```
Three small follow-ups to the AI Measure feature set:

1. ISS estimates: the ISS editor renders <AIMeasureButton> but does not pass the
   estimate prop that JobInfoPanel passes (used by HouseModel3D for the Alside
   color-name fallback when AI color sampling is weak). In pages/ISSEstimateEditor.jsx,
   add estimate={est} to the <AIMeasureButton …> invocation so ISS runs get the same
   3D color fallback as siding/windows estimates.

2. Replace the "🔁 Re-run" emoji on the AI Measure preview's Re-run button with a
   lucide-react <RefreshCw className="w-3 h-3 inline mr-1" aria-hidden="true" /> icon
   followed by the text "Re-run" (consistent with the no-emoji-icons rule).

3. Re-apply the accessibility + theming rule sets to the files added/changed since they
   were first applied: AIMeasureButton.jsx additions (model select, comparison panel,
   error banner, photos-lost banner), BlueprintMeasureButton.jsx 3D tab, and
   HouseModel3D.jsx UI chrome. Concretely: run entry 1's RULES 1–3 (muted gray #A1A1AA →
   #71717A on light, orange text → #C2410C on light, black labels on orange buttons) and
   entry 2's STEP 3 codemod (hardcoded hex classes → the semantic var(--token) utilities)
   over those files. Do NOT touch HouseModel3D's Three.js material colors (they are 3D
   scene colors, not UI classes) — only its className strings.

Verify: ISS estimate's AI Measure modal renders the 3D tab with palette-fallback colors;
the Re-run button shows an SVG icon; no hardcoded hex classes remain in the three files'
UI chrome; the app builds.
```

---
