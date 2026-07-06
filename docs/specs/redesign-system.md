# Full App Redesign — Design System Specification

*Companion to [`theme-picker.md`](./theme-picker.md). Sign-off doc for the P2 "Full app
redesign" TODO. Written 2026-07-06.*

## 1. Summary

The redesign **evolves the existing Swiss/industrial system rather than replacing it.** The
current black (`#09090B`) + safety-orange (`#F97316`) language is already the *correct*
design direction for a professional construction tool — the goal is to modernize its
elevation, spacing, density, and component states, retire the open UI/UX audit debt in the
same pass, and add per-company branding on top of the semantic-token foundation.

This is a **decision + spec** document. It does not change code. The next deliverable is
before/after mockups of the Dashboard and Estimate Editor for Howard's sign-off.

## 2. Why evolve, not replace (the evidence)

A design-intelligence pass (`ui-ux-pro-max`) was run for this product profile (B2B SaaS
estimator, professional trade tool, field-use). The matched guidance **validates the current
direction**:

- **Style — "Swiss Modernism 2.0"**: grid system, `#000/#FFF/#F5F5F5` + *a single vibrant
  accent*, mathematical spacing, **WCAG AAA**, Tailwind fit 10/10. This is essentially what
  the app already is. The sibling **"Data-Dense Dashboard"** style (KPI cards, minimal
  padding, space-efficient tables) matches the estimate grid.
- **Color — "Construction/Architecture" palette**: explicitly pairs grey + **orange as the
  safety/CTA accent (`#F97316`)** + blueprint blue. The app's brand orange *is* the
  domain-correct accent — not something to swap for generic SaaS blue.
- **Typography — "Dashboard Data"**: mono for numbers, sans for labels. The app already does
  this (JetBrains Mono numerals + Archivo/IBM Plex Sans).

**Rejected option:** the generator's default "Flat + professional blue (`#0369A1`)" SaaS
look. It's competent but generic and would discard Alside's brand identity and the
domain-appropriate safety-orange signal. We keep orange.

**What "modernize" means concretely** (the "bland widgets" note from the Howie call): softer,
consistent elevation instead of flat/hard edges; a real spacing scale; refined interactive
states (hover/focus/active/disabled/loading); skeletons over bare spinners; and adopting the
installed Radix primitives so dialogs/tabs/accordions feel first-class.

## 3. Goals & non-goals

**Goals**
- One coherent, modern visual language across **every** page (editor, dashboard, catalog,
  admin, auth).
- Keep the semantic-token architecture; the redesign is mostly *token + component* work, not
  a rewrite.
- Fold in the open UI/UX audit items (Radix dialogs/tabs/accordions, skeletons, input
  labels, section rollups, z-index scale) so the redesign **retires** that debt.
- Add **per-company branding inside the app** (not just on quotes), derived from one brand
  color and accessibility-validated.

**Non-goals**
- No blue rebrand; no consumer-flashy gradients/glow.
- No change to business logic, calc, or data model.
- Not a Tailwind→other-framework migration.

## 4. Design language

| Axis | Decision |
|---|---|
| **System** | Swiss Modernism 2.0, evolved — 12-col grid, mathematical spacing, high contrast, one accent per view. |
| **Density** | Data-Dense Dashboard for the estimate grid / totals; comfortable density for forms & marketing/auth. |
| **Accent** | Safety orange `--brand` stays the single primary accent. Blueprint blue reserved as an optional **data/secondary** accent (charts, informational chips) — not a second brand color. |
| **Elevation** | Move from hard brutalist shadow to a **3-step soft elevation scale** (see §6). Keep one deliberate "industrial" hard-edge treatment for the sticky sell-bar only. |
| **Motion** | 150–200ms, `transform`/`opacity` only, `prefers-reduced-motion` honored (already global). |
| **Icons** | SVG only (Lucide, already in use). No emoji icons. |

## 5. Color system

Keep the existing semantic tokens (`index.css :root`). Refinements:

- **Primary accent:** `--brand #F97316` / `--brand-hover #EA580C` / `--brand-text #C2410C` /
  `--on-brand #09090B` — unchanged (domain-correct safety orange).
- **Neutrals:** keep the zinc ramp (`--ink #09090B`, `--ink-2 #52525B`, `--muted #71717A`,
  `--border #E4E4E7`, `--bg-app #F4F4F5`).
- **Add semantic profit/loss tokens** `--pos` / `--neg` and retire the inline hex
  (`#10B981`/`#F87171`) in `StickyBar.jsx:104–106` (audit finding).
- **Blueprint blue** as `--data` (informational only), so it can't be confused with the brand
  CTA. Revisit whether the AI-feature purple (`--ai #7C3AED`) stays a sanctioned accent or
  folds into `--data` (open UI/UX item "Purple AI-feature styling").
- **Six shipped themes stay:** default orange + `blueprint`, `dark`, `forest`, `highvis`,
  `steel`. Every theme continues to pass the accessibility gate (§8).

## 6. Elevation, spacing, radius (the modernization levers)

- **Spacing scale (8pt):** `4 / 8 / 12 / 16 / 24 / 32 / 48`. Audit `w-N h-N` squares →
  `size-N`; adopt `cn()` for the ~137 template-literal classNames.
- **Radius:** introduce a small consistent radius token (`--radius: 6px`) for cards, inputs,
  buttons, dialogs — replacing today's sharp 0px corners on most surfaces (keep 0px only for
  the intentional industrial sell-bar).
- **Elevation:** `--e1` (resting card), `--e2` (raised/hover), `--e3` (dialog/popover) — soft,
  low-spread shadows tuned per light/dark theme. Replaces the flat hard-edge look that read as
  "bland."

## 7. Component language (all on Radix primitives)

Every interactive component uses the installed `components/ui/*` Radix primitives — this is
also how the redesign retires the audit's a11y debt:

| Component | Spec | Retires audit item |
|---|---|---|
| **Dialog / AlertDialog** | Radix `Dialog` for all modals (focus trap, Esc, `aria-modal`); `AlertDialog` for every destructive action. | ~22 hand-rolled modals; `window.confirm`/`alert`; unguarded photo/opening removes |
| **Tabs** | Radix `Tabs` for the product-line strip (arrow-key nav, roving tabindex). | `EstimatorTabs` keyboard nav |
| **Accordion** | Radix `Accordion` for `SectionAccordion` (`aria-expanded`/`aria-controls`). | Accordion semantics |
| **Inputs** | Always `label htmlFor`/`id`; `inputmode`/`type=number`; right-aligned `.input.num` tabular. | Unnamed grid/color/Vero inputs |
| **Buttons** | States: rest / hover (color-opacity) / focus-visible ring / active / disabled / **loading** (disable during async). | Double-submit guards on Totals actions |
| **Feedback** | Skeletons (`ui/skeleton.jsx`) for loads; inline error text near the field + toast for API; persistent saved/saving/error chip near the sell-bar. | Skeletons; autosave-failure surfacing |
| **Touch** | ≥44×44px targets (photo-remove X, reset ↺, adder qty). | Sub-44px targets |
| **Z-index** | Token scale: `--z-header/sticky/modal/popover/toast` — no ad-hoc `z-[70]` literals. | z-index scale |

## 8. Per-company branding

Each contractor company gets in-app branding, built on the token system (not a fork):

- A **company theme is a generated `data-theme` block** derived from one brand color:
  `brand → brand-hover / brand-text / on-brand` computed and **validated for contrast**
  before it can be saved (build `frontend/scripts/validate-themes.py`, referenced by CLAUDE.md
  but not yet created — this is a prerequisite, like Phase 1 was for the theme picker).
- **Precedence chain:** `user pick > company theme > supplier default > app default`.
  Overlaps with theme-picker Phase 3 (supplier-pinned default); design them together.
- Company logo already lives on the company record and shows on quotes/nav — extend it to the
  in-app header.
- Contractors **cannot pick an inaccessible combo** — the validator is the gate (same AAA/AA
  discipline as the six built-in themes).

## 9. Accessibility gates (unchanged, non-negotiable)

Every theme (built-in or company-generated) and every component must pass:
- Text contrast ≥ 4.5:1 (headings 3:1); `--brand`-on-`--on-brand` legible in all six themes.
- Visible `focus-visible` ring on all interactive elements.
- Color never the sole signal (profit/loss also carries sign/label).
- `prefers-reduced-motion` respected (already global).
- Responsive with no horizontal scroll at 375 / 768 / 1024 / 1440; tables → horizontal-scroll
  or card layout on mobile.

## 10. Delivery plan

1. **This spec** → Howard sign-off on *evolve-not-replace + orange stays*.
2. **Before/after mockups** of Dashboard + Estimate Editor (interactive HTML, theme-switchable)
   — the visual proof before any code.
3. **Foundation PR:** spacing/radius/elevation tokens, `--pos`/`--neg`/`--data`, z-index
   tokens, `radius`. No visual regression beyond intended.
4. **Component PRs (retire audit debt):** Radix Dialog/AlertDialog → Tabs → Accordion →
   inputs/labels → skeletons/loading states. One family per PR, screen-by-screen.
5. **Per-company theming:** build `validate-themes.py` gate → company-theme generator →
   precedence chain → admin UI.
6. **Sweep:** remaining audit low-impact items (skip-to-content, `cn()` adoption, dead-weight
   cleanup, bilingual `aria-label` gaps).

## 11. Open questions

- Does the AI-feature purple stay a sanctioned accent, or fold into `--data` (blueprint blue)?
- Radius: 6px everywhere, or keep some surfaces sharp for industrial character?
- Company theme: single brand color (derive the rest) or a small guided palette per company?
- Typography: keep Archivo/IBM Plex/JetBrains, or evaluate the "Dashboard Data" (Fira) pairing
  the generator surfaced? (Lean: keep — the current stack already satisfies the intent.)

## 12. Next step

Build the **interactive before/after mockup** of Dashboard + Estimate Editor (theme-switchable
HTML artifact) so Howard can see the evolved system on real screens before committing to the
foundation PR.
