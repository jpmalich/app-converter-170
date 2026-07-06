# Theme Picker — Design Specification

*Status: proposed · Author: UI/UX design pass, 2026-07-02 · Origin: Howie call — "I give like
8 to 10 different styles… just by a click of a button, it can change the way the whole thing
looks."*

## 1. Summary

A user-selectable theme system for the Pro-Quote UI: six WCAG-AA-validated color themes,
switchable instantly from a picker in the app header, persisted per device (later per user).
Themes restyle **the contractor's working UI only** — never customer-facing documents.

## 2. Goals & non-goals

**Goals**
- One-click switching between professionally designed, accessibility-validated looks.
- Zero contrast regressions: every theme ships pre-validated against the same WCAG gates
  codified in `design_guidelines.json`.
- Architecture that makes future themes a ~20-line token file, not a redesign.

**Non-goals (v1)**
- **No font switching.** Typography (Archivo / IBM Plex Sans / JetBrains Mono) is part of the
  product's voice and font swaps cause layout shift and load cost. Revisit only if demand is real.
- **No customer-facing changes.** Quote modal print area, WeasyPrint PDF, email HTML
  (`emailQuote.js`), material list, print takeoff, and the public Accept page keep the neutral
  document style — a homeowner's quote reflects the contractor's brand, not the estimator's UI
  preference.
- No per-line-item or per-estimate theming.

## 3. The architectural prerequisite (Phase 1 is the real work)

The census: **2,254 hardcoded arbitrary hex classes** (`text-[#09090B]`, `bg-[#F97316]`, …)
across the frontend, but only ~12 hex values cover ~90% of them. Meanwhile
`tailwind.config.js` already supports CSS-variable colors (the shadcn block) and `index.css`
already defines `:root` tokens — they're just unused by app code.

Migration = extend the token set, map Tailwind utilities to the variables, then run a scripted
codemod over the 12 dominant hexes (same shape as the recent contrast sweep, agent-verifiable):

| Hex (count) | Semantic token | Tailwind utility |
|---|---|---|
| `#09090B` (429) | `--ink` / dark fixed surfaces (see below) | `text-ink`, `bg-bar` |
| `#71717A` (472) | `--muted` | `text-muted` |
| `#52525B` (250) | `--ink-2` | `text-ink-2` |
| `#E4E4E7` (346) | `--border` | `border-border` |
| `#F97316` (135) | `--brand` | `bg-brand`, `border-brand` |
| `#C2410C` (83) | `--brand-text` | `text-brand-text` |
| `#F4F4F5` (90) | `--bg-app` | `bg-app` |
| `#FAFAFA` (108) | `--surface-muted` | `bg-surface-muted` |
| `#7C3AED` (103) | `--ai` | `text-ai`, `bg-ai` |
| `#DC2626`/`#16A34A`/`#B45309`… | status tokens | `text-danger`, … |

**Context-sensitive mappings** (the 10% needing judgment, mirroring the contrast sweep):
- The sticky sell-bar and dark modal headers are **fixed dark surfaces in every light theme**
  (they're the brand's anchor). They get their own tokens (`--bar-bg`, `--bar-ink`,
  `--bar-muted`) rather than inheriting `--surface`/`--ink`, so light themes keep the black
  bar and Jobsite Dark can lift it one step (`#27272A`) for separation.
- `#A1A1AA` on dark surfaces → `--bar-muted` (not `--muted`).
- Canvas/SVG measurement drawing colors stay hardcoded — they render over photos, not themed
  surfaces.

## 4. Token set (per theme)

```
--bg-app, --surface, --surface-muted, --table-header
--ink, --ink-2, --muted, --inverse
--border, --border-strong, --focus
--brand, --brand-hover, --brand-text, --on-brand
--bar-bg, --bar-ink, --bar-muted            (fixed chrome: sell-bar, dark headers)
--ai, --ai-text                             (AI-feature accent)
--success, --success-text, --warning-text, --danger, --danger-text, --profit
```

Themes are applied as `<html data-theme="blueprint">`; each theme is one
`:root[data-theme=…] { … }` block in `index.css`. `--focus` must always hit ≥3:1 against
`--surface` (this is why Safety Orange's focus is `#C2410C`, not the 2.8:1 `#F97316`).

## 5. Theme catalog (v1 — all six validated)

Contrast validated 2026-07-02 (script method in `design_guidelines.json` accessibility rules).
"CTA" = `--on-brand` on `--brand` (button labels). All values below PASS their gate.

| Theme | `--brand` | `--brand-text` | `--on-brand` | Character | Key ratios |
|---|---|---|---|---|---|
| **Safety Orange** *(default — current look)* | `#F97316` | `#C2410C` | `#09090B` | The shipped industrial look | CTA 7.10 · brand-text 5.18 · muted 4.83 |
| **Blueprint Blue** | `#2563EB` | `#1D4ED8` | `#FFFFFF` | Architectural, trust-forward | CTA 5.17 · brand-text 6.70 |
| **Forest Green** | `#15803D` | `#166534` | `#FFFFFF` | The classic contractor green (retired look, by request) | CTA 5.02 · brand-text 7.13 |
| **Steel** | `#334155` | `#334155` | `#FFFFFF` | Monochrome slate, most conservative | CTA 10.35 |
| **High-Vis Yellow** | `#FACC15` | `#854D0E` | `#09090B` | OSHA vest energy | CTA 12.99 · brand-text 6.85 |
| **Jobsite Dark** | `#F97316` | `#FB923C` | `#09090B` | Dark surfaces (`--surface #18181B`, `--ink #FAFAFA`), truck-cab/evening use | ink 16.97 · muted (`#A1A1AA`) 6.91 · brand-text 7.83 |

Neutral ramps: light themes share the current zinc ramp; Blueprint/Steel use the slate ramp;
Forest uses a green-tinted neutral ramp. Jobsite Dark inverts surfaces and lifts status colors
one step lighter for dark-surface contrast.

## 6. Picker UX

**Entry point:** paintbrush/palette icon button in the `Layout` header (next to the EN/ES
toggle — same interaction family: a persistent personal preference), opening a Radix
`Popover`/`DropdownMenu`. Also mirrored as a card on the **Team** page for discoverability.

**Anatomy:** a `radiogroup` ("Theme") of six rows. Each row: theme name + a 3-dot swatch chip
(`--brand`, `--ink`, `--bg-app`) + a check on the active row. First row is
**Auto (match device)** → resolves `prefers-color-scheme` to Safety Orange / Jobsite Dark.

**Behavior:**
- Selection applies **instantly** (set `data-theme`, persist) — the app itself is the preview.
  No confirm step; switching back is one click. No transition animation on theme change (a
  root-wide color transition causes a smeary repaint; instant swap reads as intentional).
- Persist to `localStorage["ui-theme-v1"]` (v1). Phase 3: also persist to the user record
  (`PUT /api/auth/me { theme }`) so it follows login across devices; localStorage remains the
  fast path.
- **FOUC guard:** tiny inline script in `index.html` `<head>` applies `data-theme` from
  localStorage before first paint (standard dark-mode pattern).
- **A11y:** `role="radiogroup"` + `aria-checked`, arrow-key navigation (free with Radix
  RadioGroup/DropdownMenu), visible focus ring per theme's `--focus`, selection announced via
  an `aria-live="polite"` status ("Theme: Blueprint Blue"), EN/ES labels through `t()`.

## 7. Accessibility gates (every current and future theme)

1. `--ink`, `--ink-2`, `--muted`, `--brand-text`, all `*-text` status tokens ≥ 4.5:1 on
   `--surface` AND `--surface-muted`.
2. `--on-brand` ≥ 4.5:1 on `--brand` and `--brand-hover`.
3. `--focus` ≥ 3:1 against `--surface`; `--border-strong` ≥ 3:1.
4. `--bar-ink` ≥ 4.5:1 and `--bar-muted` ≥ 4.5:1 on `--bar-bg`.
5. Never rely on hue alone to distinguish themes' semantic states (status icons/text carry the
   meaning — already the house rule).

Add a `scripts/validate-themes.py` (the ratio script) run in CI/pre-commit so a new theme
cannot ship failing a gate.

## 8. Delivery plan

| Phase | Work | Size |
|---|---|---|
| **0 — Tokens** | Extend `index.css` token set (incl. `--bar-*`, `--ai`, status-text); map Tailwind utilities to vars in `tailwind.config.js` | small |
| **1 — Codemod** | Scripted migration of the 2,254 arbitrary hex classes → semantic utilities; context-sensitive pass for `--bar-*` surfaces; agent-verified like the contrast sweep; visual screenshot diff on key pages | the real work |
| **2 — Themes + picker** | Six `data-theme` blocks; picker in header + Team page; localStorage + FOUC guard; validator script | medium |
| **3 — Later** | Sync to user profile; per-company default theme (supplier-set); expand toward Howie's 8–10; optional auto-dark scheduling | opt-in |

**Emergent replication:** Phases 0–2 are app-affecting → each needs a `PromptsForEmergent.md`
entry on completion.

## 9. Open questions

1. Should the **supplier** be able to pin a company-wide default (contractor sees supplier's
   pick until they choose)? (Leaning yes, Phase 3 — it's a branding lever for Alside.)
2. Does the `--ai` purple accent stay constant across themes (recognizable "AI" signal) or
   re-map per theme? (v1: constant, slightly lightened on Jobsite Dark; also resolves the
   audit's "purple gradient" flag by tokenizing it.)
3. Names are placeholders — Howard may want supplier-flavored names ("Alside Orange").

## 10. Interactive mockup

A clickable HTML mockup of the picker + all six themes applied to a miniature estimate editor
accompanies this spec (Claude artifact, 2026-07-02). It demonstrates the exact token
architecture from §4 — each theme in the mockup is literally a `data-theme` CSS block.
