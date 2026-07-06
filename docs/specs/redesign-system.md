# Blueprint Instrument — Design System Specification

*Companion to [`theme-picker.md`](./theme-picker.md). Sign-off doc for the P2 "Full app
redesign" TODO. Interactive mockup: [`redesign-mockup.html`](./redesign-mockup.html)
([hosted](https://claude.ai/code/artifact/715bd989-d070-4356-8b9b-fc4043f118fb)). Rev 2,
2026-07-06.*

## 1. Summary

**Blueprint Instrument** is a distinctive, ground-up visual identity for Pro-Quote —
**a replacement for the flat industrial look, not an evolution of it.** The app presents as
a working **drafting sheet**: a drawing frame with a title block, a faint graph-paper
substrate, measurements rendered as **dimension lines**, tabular-mono numerals as the hero of
every surface, and safety orange used only as **redline markup**. The classic **cyanotype**
(white-on-navy) is the dark theme, not an inversion.

This is a **decision + spec** document; it does not change code. Rev 1 recommended *evolving*
the existing Swiss/industrial system; that was overridden by the direction to build something
unique — this rev supersedes it.

## 2. Why this direction

- **It belongs to the subject.** The product's whole world is *measurement* — takeoffs,
  squares, linear feet, elevations, HOVER sheets, waste %. A drafting/blueprint language makes
  the tool read as a precision instrument a tradesperson already trusts, instead of a generic
  SaaS dashboard. The domain, not a template, generated the identity.
- **It is logically functional.** Numbers and dimensions are the content; the design promotes
  them to the hero rather than decorating around them. Summary reads before detail; state is
  encoded in *form* (stamps, redlines, gauges), not only color.
- **It is genuinely differentiated.** It deliberately avoids the current AI-generic looks
  (cream+serif, purple gradient, near-black+acid-green, Inter-everywhere). The one aesthetic
  risk — the drawing-board metaphor taken literally (graph paper, dimension lines, stamps) —
  is spent in one place; everything else stays quiet.
- **Brand fit.** Alside's safety orange survives as the **redline/markup** color (scarce, high
  signal). Blueprint blue becomes the primary accent — which doubles as the per-company brand
  hook (§8).

## 3. Design language — "the app is a drawing"

| Device | Meaning |
|---|---|
| **Drawing frame** | Every screen sits inside a double-rule sheet border — you're working *on a sheet*. |
| **Title block** | Architect's corner block (sheet / rev / scale) as the app header & card headers. |
| **Graph-paper substrate** | Two-scale faint grid behind the sheet; everything aligns to it. |
| **Dimension lines** | Measurements drawn (`⊢—— 24.0 SQ ——⊣`), not just typed. |
| **Drawing labels** | Sections coded like sheets (`A-01`, `01 · Vinyl Siding`). |
| **Stamps** | Status (Won/Sent/Draft) and profit rendered as rubber-stamp marks. |
| **Redline** | Safety orange = a reviewer's markup pen; flags, deltas, "verify…" notes only. |

## 4. Color tokens

Two themes ship at launch; both are first-class (not inverts). All components style through
tokens — never hardcode hex (retires the StickyBar inline-hex audit finding).

**Whiteprint (light) — default**
| Token | Hex | Role |
|---|---|---|
| `--desk` | `#E4E7EC` | canvas behind the sheet |
| `--paper` | `#F7F8FA` | sheet ground |
| `--sheet` | `#FFFFFF` | card/panel surface |
| `--ink` | `#0B1F3A` | blueprint-navy text / frame |
| `--ink-2` | `#47566B` | secondary text |
| `--muted` | `#8493A8` | labels, meta |
| `--line` | `#1E6FEB` | **primary accent** — dimension lines, rules, focus, CTAs |
| `--line-2` | `#A9C4F5` | inner frame, soft rules |
| `--grid` / `--grid-2` | `rgba(30,111,235,.07 / .14)` | minor / major graph grid |
| `--border` | `#D3DBE6` | panel borders |
| `--mark` | `#F26419` | **redline** — markup only, scarce |
| `--pos` | `#0E7C66` | profit / positive stamp |
| `--neg` | `#C63B3B` | loss / redline negative |

**Blueprint (dark) — cyanotype**
| Token | Hex |
|---|---|
| `--desk` `#05070D` · `--paper` `#081327` · `--sheet` `#0B1F3A` |
| `--ink` `#EAF1FF` · `--ink-2` `#A7BEDE` · `--muted` `#6E86A8` |
| `--line` `#5B9BFF` · `--border` `#1C3355` · `--mark` `#FF9247` |
| `--pos` `#34D399` · `--neg` `#FF6B6B` |

Theme selection: `prefers-color-scheme` default + explicit `data-theme` override (same
mechanism as the existing theme picker). Semantic color (`pos`/`neg`/`mark`) is **separate
from the accent** and never the sole signal.

## 5. Typography

- **Display / UI:** a technical grotesque (International/Swiss lineage — e.g. a licensed
  Aeonik/Basis-grotesque; the mockup approximates with Helvetica/Arial). Headings tight
  (`-0.02em`); labels uppercase, wide-tracked (`.12–.16em`) like drafting annotations.
- **Numerals & measurements — the hero:** **JetBrains Mono**, `tabular-nums`, on *every*
  dollar amount, quantity, and dimension. This is the single most identity-defining type rule.
- Keep body line-length ≈ 65ch; type scale fixed; `text-wrap: balance` on headings.

## 6. Spacing, grid, frame

- **8px base grid** (`4 / 8 / 12 / 16 / 24 / 32 / 48`) — literally the graph-paper module.
- **Drawing frame:** 1.5px `--line` outer + 1px `--line-2` inner offset (the classic sheet
  border). Panels are square-cornered (drafting has no rounding) — *radius is intentionally 0*,
  which is the opposite call from Rev 1 and correct for this identity.
- Wide content (register table, line-item grid) scrolls inside its own `overflow-x:auto`.

## 7. Signature components (all on Radix primitives)

Building these on the installed `components/ui/*` Radix primitives is also how the redesign
**retires the open UI/UX audit debt**:

| Component | Spec | Retires |
|---|---|---|
| **Title block** | Header + card headers as bordered metadata cells (sheet/rev/scale). | — (new) |
| **Dimension line** | `rule–value–rule` with tick ends; renders any measurement. | — (new) |
| **Instrument KPI** | Label + big mono value + delta + mini tick-gauge. | — (new) |
| **Stamp status** | Outlined uppercase mark; profit = rotated stamp. | status-as-text |
| **Dialog / AlertDialog** | Radix `Dialog` for all modals; `AlertDialog` for every destructive action, styled as a "revision / confirm" stamp. | ~22 hand-rolled modals; `window.confirm`/`alert` |
| **Tabs (layers)** | Radix `Tabs` for product lines, styled as drawing layers. | `EstimatorTabs` keyboard nav |
| **Accordion** | Radix `Accordion` for sections (`aria-expanded`). | accordion semantics |
| **Inputs** | Mono, right-aligned, `label`+`id`, `inputmode`; focus = `--line` ring. | unnamed grid/color/Vero inputs |
| **Buttons** | Square, uppercase; rest/hover/focus-visible/disabled/**loading**. | double-submit guards |
| **Feedback** | Skeletons on load; inline error near field + toast for API; redline for flags. | skeletons; autosave surfacing |
| **Z-index** | Token scale (`--z-header/sticky/modal/popover/toast`). | ad-hoc z literals |

## 8. Per-company branding

The identity is built to rebrand per contractor from **one brand color**:

- The **primary accent lives in a single token** (`--line`). A company theme regenerates
  `--line` (+ its focus/hover derivations) from the company's brand color — the drawing stays
  a drawing; only the ink color of the lines changes.
- **Precedence:** `user pick > company theme > supplier default > app default`.
- **Contrast gate:** company colors are validated (build `frontend/scripts/validate-themes.py`,
  referenced by CLAUDE.md but not yet created) so no contractor can pick an accent that fails
  the §9 gates against `--paper` and `--sheet`, light and dark.
- Company logo (already on the company record) slots into the title block.

## 9. Accessibility gates (non-negotiable)

Every theme (built-in or company) and component must pass:
- Text contrast ≥ 4.5:1 (headings ≥ 3:1); `--line` and `--mark` legible on `--paper`/`--sheet`
  in both themes.
- Visible `focus-visible` ring on all interactive elements.
- Color never the sole signal — stamps carry a label, redlines carry text, profit carries sign.
- `prefers-reduced-motion` honored (the sheet's entrance + hovers disable).
- No horizontal page scroll at 375 / 768 / 1024 / 1440; dense tables scroll within their panel.

## 10. Delivery plan

1. **This spec + mockup** → Howard sign-off on the Blueprint Instrument direction.
2. **Foundation PR:** the token sets (§4), spacing/frame, `--line`/`--mark`/`--pos`/`--neg`,
   z-index tokens, mono-numeral rule. Ship the two themes behind the existing theme system.
3. **Primitive components:** title block, dimension line, stamp, instrument KPI, totals gauge
   — as reusable components in `components/ui/`.
4. **Screen conversions (retire audit debt), one per PR:** Dashboard → Estimate Editor →
   Catalog → Admin → Auth, swapping in Radix Dialog/Tabs/Accordion + labeled inputs + skeletons
   as each screen is redrawn.
5. **Per-company theming:** build `validate-themes.py` gate → `--line` generator → precedence
   chain → admin UI.
6. **Sweep:** remaining audit low-impact items (skip-to-content, `cn()` adoption, dead-weight
   cleanup, bilingual `aria-label` gaps).

## 11. Open questions

- **Metaphor dial:** full drafting treatment on every screen, or reserve the heaviest devices
  (graph paper, dimension lines) for the estimate/measure surfaces and keep Dashboard/Admin
  calmer?
- **Redline scope:** markup orange for flags/deltas only, or also for primary destructive
  actions (delete)?
- **Company accent:** does a company brand color replace blueprint-blue entirely, or tint
  toward it so every tenant still reads as "a blueprint"? (Lean: constrain toward blueprint so
  the identity survives rebrand.)
- **Type budget:** license a distinctive grotesque, or ship with a high-quality system stack +
  JetBrains Mono to start?

## 12. Next step

On sign-off, begin the **Foundation PR** (§10.2): land the two token themes and the
mono-numeral + frame primitives, with no behavior change — the substrate every screen
conversion builds on.
