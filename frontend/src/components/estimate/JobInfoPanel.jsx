import React from "react";
import DOMPurify from "dompurify";
import { useT, useLang } from "@/lib/i18n";
import { tColor, tColorGroup } from "@/lib/catalogTranslations";
import { vinylSidingColorGroupsForEstimate, accessoryColorGroupsForEstimate, ASCEND_COLORS, SHAKE_COLOR_GROUPS, BOARD_BATTEN_COLOR_GROUPS, SOFFIT_COLOR_GROUPS, GUTTER_COLORS, WINDOW_WRAP_COLORS, LP_SMARTSIDE_COLORS, MEZZO_EXTERIOR_COLOR_GROUPS, MEZZO_INTERIOR_COLOR_GROUPS, VERO_EXTERIOR_COLOR_GROUPS, VERO_INTERIOR_COLOR_GROUPS, VERO_LAMINATE_NAMES } from "@/lib/colorOptions";
import HoverImportButton from "@/components/estimate/HoverImportButton";
import AIMeasureButton from "@/components/estimate/AIMeasureButton";
// Iter 79j.19 — bake current waste_pct into AI-generated cut-prone
// lines on Apply, same as HOVER Import does.
import { bakeWasteIntoLines } from "@/lib/wasteLogic";
import BlueprintMeasureButton from "@/components/estimate/BlueprintMeasureButton";
import PairToLpButton from "@/components/estimate/PairToLpButton";
// Iter 78u — Compare Drawings modal trigger
import { useState } from "react";
import { Upload, FileText, Sparkles, Layers, ChevronDown, ChevronUp, MoreHorizontal, Lightbulb } from "lucide-react";
import ElevationCompareModal, { countSources } from "@/components/estimate/ElevationCompareModal";
import { isValidEmail, isValidPhone, isValidZip, formatPhoneUS } from "@/lib/validate";
import { NO_AUTOFILL } from "@/lib/noAutofill";

// Iter 79j.47 — US-state select options for the structured address grid.
// Includes DC per USPS. Kept as [code] pairs — labels use the same
// abbreviation in EN and ES (they're state codes, not names).
const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
];

// Iter 79j.47 — Lead-source presets (slug values are persisted, labels
// come from the i18n dict so ES translations swap in automatically).
const LEAD_SOURCE_SLUGS = [
  "referral","repeat_customer","web","social","yard_sign","truck_wrap","home_show","supplier","door_knock","other",
];

// Iter 79j.47 — Compose the canonical single-line `address` string
// from the 4 structured parts. Every downstream consumer (quote docs,
// CSVs, geocoding) keeps reading `address`, so this MUST stay in
// sync with whatever the grid inputs hold. Empty parts collapse
// gracefully ("Street, City, ST 12345" → "Street" if only street).
function composeAddress(street, city, state, zip) {
  const s = (street || "").trim();
  const c = (city || "").trim();
  const st = (state || "").trim().toUpperCase();
  const z = (zip || "").trim();
  const cityStateZip = [c, [st, z].filter(Boolean).join(" ")]
    .filter(Boolean)
    .join(", ");
  return [s, cityStateZip].filter(Boolean).join(", ");
}

// Iter 79j.47 — Best-effort parse of a legacy single-line address into
// parts for display. Runs ONLY when all structured parts are empty
// and a legacy `address` string exists (unmigrated draft). Never
// persists silently — the panel writes parts back to state on first
// user edit. Heuristic: trailing token = ZIP if it matches 5(-4) or
// starts with a digit; token before it = 2-letter state; first
// comma-separated segment = street; anything in between = city.
function parseLegacyAddress(addr) {
  const out = { street: "", city: "", state: "", zip: "" };
  if (!addr || typeof addr !== "string") return out;
  const clean = addr.trim();
  if (!clean) return out;
  // Zip regex — 5-digit or 5+4 at the end of the string.
  const zipMatch = clean.match(/(\d{5}(?:-\d{4})?)\s*$/);
  let rest = clean;
  if (zipMatch) {
    out.zip = zipMatch[1];
    rest = clean.slice(0, zipMatch.index).replace(/[,\s]+$/, "");
  }
  // State regex — 2-letter uppercase token at the end.
  const stMatch = rest.match(/\b([A-Z]{2})\s*$/);
  if (stMatch) {
    out.state = stMatch[1];
    rest = rest.slice(0, stMatch.index).replace(/[,\s]+$/, "");
  }
  // Remaining rest splits by commas: first segment = street, last = city.
  const segs = rest.split(",").map((s) => s.trim()).filter(Boolean);
  if (segs.length >= 2) {
    out.street = segs[0];
    out.city = segs.slice(1).join(", ");
  } else if (segs.length === 1) {
    out.street = segs[0];
  }
  return out;
}

// Iter 78z+++ — Cleaner job-info header. Three equal-width "tool tiles"
// for the measurement importers (HOVER · Blueprints · AI Photo), each
// with a short label so contractors don't have to read button text to
// tell them apart. PairToLp + Compare Drawings tuck into a "More tools"
// row below the tiles since they're contextual / rare. Form fields
// collapse to a 1-line summary once customer + address are filled so
// the page stops scrolling past data the contractor doesn't need to
// re-touch.
function ToolTile({ icon: Icon, label, sub, children, testid, accent = "#7C3AED" }) {
  return (
    <div
      className="border border-[var(--border)] bg-[var(--surface)] p-3 flex flex-col gap-2 min-w-0"
      data-testid={testid}
    >
      <div className="flex items-center gap-1.5">
        <Icon className="w-3.5 h-3.5" style={{ color: accent }} />
        <div className="text-[10px] uppercase tracking-wider font-bold text-[var(--ink-2)] truncate">
          {label}
        </div>
        {sub && (
          <span className="text-[9px] text-[var(--muted)] uppercase tracking-wider truncate ml-auto">
            {sub}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5 items-start">{children}</div>
    </div>
  );
}

// Iter 79j.49 — Small warning line under an input. Rendered ONLY when
// (touched && non-empty && invalid). Uses the theme's --warning-text
// so it inherits every color palette. The id lets aria-describedby
// on the input point at it for screen-reader announcements.
function FieldWarning({ id, children }) {
  return (
    <div
      id={id}
      role="alert"
      className="text-[11px] leading-tight mt-1 text-[var(--warning-text)]"
      data-testid={id}
    >
      {children}
    </div>
  );
}

// Iter 79j.47 — Sub-section mini-header (same visual pattern as the
// "Material Colors" title) shared by the 4 groups of the new form.
// Defined at module scope so React doesn't destroy/recreate the
// subtree on every JobInfoPanel render (react/no-unstable-nested-components).
function SubHeader({ children, testid }) {
  return (
    <div
      className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)] font-bold mb-2 sm:col-span-2 lg:col-span-3"
      data-testid={testid}
    >
      {children}
    </div>
  );
}

export default function JobInfoPanel({ est, update, save, setInstallMethod, setHomePre1978 }) {
  const t = useT();
  const { lang } = useLang();
  // Iter 78u — Compare Drawings modal state
  const [showCompare, setShowCompare] = useState(false);
  const numDrawingSources = countSources(est);
  // Iter 78z+++ — collapse the form section once the contractor has
  // filled the basics. They can re-expand any time via the "Edit"
  // affordance in the summary row.
  const basicsFilled = !!(est?.customer_name && est?.address);
  const [collapsed, setCollapsed] = useState(false);
  // Auto-collapse when basics become filled on first render (but only
  // once — if the user expands manually we respect their choice).
  const [autoTouched, setAutoTouched] = useState(false);
  // Iter 79j.49 — Per-field "touched" set. Warnings appear only AFTER
  // the user first leaves a field (blur), so an empty draft doesn't
  // shout at the contractor mid-typing. Live-clears once fixed.
  const [touched, setTouched] = useState({});
  const markTouched = (name) => setTouched((prev) => (prev[name] ? prev : { ...prev, [name]: true }));
  if (!autoTouched && basicsFilled && !collapsed) {
    // schedule once to avoid setState during render
    setTimeout(() => {
      setCollapsed(true);
      setAutoTouched(true);
    }, 0);
  }
  // Brand-filtered vinyl siding color groups. Computed inline on every
  // render — cheap (an array filter over <30 items) and avoids the
  // hooks/preserve-manual-memoization lint complaint about useMemo +
  // optional chaining. Shared across siding / accessories / outside-corner
  // dropdowns so they all narrow to the active brand together.
  const vinylColorGroups = vinylSidingColorGroupsForEstimate(est?.lines || []);
  // Accessories + Outside Corner pickers also include Ascend so an
  // Ascend-quote contractor can match the corner posts without leaving
  // the field.
  const accessoryColorGroups = accessoryColorGroupsForEstimate(est?.lines || []);
  // Iter 77 — LP SmartSide estimates use the factory ExpertFinish 16-color
  // palette across every applicable color picker, with renamed labels
  // ("LP Siding Color", "Trim Color") and no Window Wrap dropdown.
  const isLp = est?.kind === "lp_smart";
  return (
    <section className="card p-5 sm:p-6 mb-6" data-testid="job-info">
      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="section-tag">{t("est.jobInfo")}</div>
          {/* Iter 79j.47 — Contact-hint badge. Shows any time
              customer_email is empty (drafting or otherwise) — visible
              even when the form is collapsed so the contractor knows
              why the "Send" flow will prompt them later. */}
          {!(est?.customer_email || "").trim() && (
            <span
              className="inline-flex items-center gap-1 px-2 py-1 text-[10px] uppercase tracking-wider font-bold bg-[var(--hint-bg)] border border-[var(--hint-line)] text-[var(--hint-ink)]"
              data-testid="contact-hint"
              title="Adds the customer's email so quote-send flows can prefill it."
            >
              <Lightbulb aria-hidden="true" className="w-3 h-3" />
              {t("est.contactHint")}
            </span>
          )}
          {collapsed && basicsFilled && (
            <div className="text-xs text-[var(--ink-2)] flex items-center gap-2 flex-wrap" data-testid="job-info-summary">
              <span className="font-bold text-[var(--ink)]">{est.customer_name}</span>
              {est.customer_company && (
                <>
                  <span className="text-[var(--muted)]">·</span>
                  <span data-testid="job-info-summary-company">{est.customer_company}</span>
                </>
              )}
              <span className="text-[var(--muted)]">·</span>
              <span>{est.address}</span>
              {(est.customer_phone || est.customer_email) && (
                <>
                  <span className="text-[var(--muted)]">·</span>
                  <span className="font-mono-num text-[var(--muted)]" data-testid="job-info-summary-contact">
                    {est.customer_phone || est.customer_email}
                  </span>
                </>
              )}
              {est.estimate_number && (
                <>
                  <span className="text-[var(--muted)]">·</span>
                  <span className="font-mono-num text-[var(--muted)]">{est.estimate_number}</span>
                </>
              )}
            </div>
          )}
        </div>
        {basicsFilled && (
          <button
            type="button"
            onClick={() => setCollapsed((c) => !c)}
            className="text-[10px] uppercase tracking-wider font-bold text-[var(--ai)] hover:text-[#5B21B6] flex items-center gap-1"
            data-testid="job-info-toggle"
          >
            {collapsed ? (
              <>
                <ChevronDown className="w-3 h-3" /> Edit
              </>
            ) : (
              <>
                <ChevronUp className="w-3 h-3" /> Collapse
              </>
            )}
          </button>
        )}
      </div>

      {/* Iter 78z+++ — Measurement tools tile row. Three equal-width
          tiles so HOVER / Blueprints / AI Photo Measure look like the
          parallel choices they actually are. Each tile is a launcher
          + its contextual sub-actions (Restore HOVER, Tag Profiles,
          waste-default caption, resume banner). */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3" data-testid="measurement-tools-row">
        <ToolTile icon={Upload} label="HOVER PDF" accent="#09090B" testid="tool-tile-hover">
          <HoverImportButton est={est} update={update} save={save} />
        </ToolTile>
        <ToolTile icon={FileText} label="Blueprints" accent="#7C3AED" testid="tool-tile-blueprint">
          <BlueprintMeasureButton est={est} update={update} save={save} />
        </ToolTile>
        <ToolTile icon={Sparkles} label="AI Photo Measure" accent="#7C3AED" testid="tool-tile-ai">
          <AIMeasureButton
            kind={est.kind || "siding"}
            address={est?.address}
            overhangIn={est?.overhang_in ?? 12}
            estimateId={est?.id}
            estimate={est}
            onApply={async ({ lines: aiLines, measurements }) => {
              // Iter 79j.19 — Apply the current estimate `waste_pct`
              // to cut-prone AI lines the same way HOVER Import does.
              // Without this, hitting Re-run (or the first Apply)
              // produced siding SQ counts equal to the raw ft²/100,
              // ignoring the contractor's waste setting entirely.
              // `bakeWasteIntoLines` walks each cut-prone line, stores
              // the raw in `raw_qty`, and bumps qty to `raw × (1 +
              // waste/100)` rounded up to the nearest 0.5 unit.
              // Non-cut-prone lines (gutter, downspouts, labor, etc.)
              // are untouched.
              const wastePct = Number(est?.waste_pct ?? 0);
              const srcKind = est.kind || "siding";
              // THE CUT (ruled 2026-07-14): lp_smart-kind estimates compose
              // through the LP engine — importers merge NO composition
              // lines (raw _build_lines output bypasses the composition
              // guard / per-system table / whole-piece rounding, and
              // waste_pct would stack on formulas already carrying ×1.10).
              if (srcKind === "lp_smart") {
                const patch = {};
                if (measurements?._photo_zones_summary) {
                  patch.photo_zones_summary = measurements._photo_zones_summary;
                  patch.photo_zones_deducted_sqft = measurements._photo_zones_deducted_sqft || 0;
                }
                if (Object.keys(patch).length) {
                  update(patch);
                  if (save) await save({ ...est, ...patch });
                }
                return;
              }
              const bakedLines = bakeWasteIntoLines(aiLines || [], wastePct);
              const existing = est.lines || [];
              const keyOf = (l) => `${l.tab || "vinyl"}::${l.section}::${l.name}`;
              const byKey = new Map(existing.map((l, i) => [keyOf(l), i]));
              const next = [...existing];
              // Iter 78z++++ — LP Smart has its own workspace; drop LP rows
              // from AI imports onto siding-kind estimates. lp_smart-kind
              // estimates never reach here (engine-owned, above).
              const SIDING_TABS = new Set(["vinyl", "ascend"]);
              const WINDOWS_TABS = new Set(["windows"]);
              for (const ln of bakedLines) {
                const isSiding = SIDING_TABS.has(ln.tab || "vinyl");
                const isWindows = WINDOWS_TABS.has(ln.tab || "vinyl");
                if (srcKind === "windows" ? !isWindows : !isSiding) continue;
                const key = keyOf(ln);
                const idx = byKey.get(key);
                if (idx == null) {
                  next.push({
                    tab: ln.tab || "vinyl",
                    section: ln.section,
                    name: ln.name,
                    unit: ln.unit,
                    qty: ln.qty,
                    raw_qty: ln.raw_qty,   // preserve raw so future waste-% changes recompute correctly
                    mat: 0,
                    lab: 0,
                  });
                } else {
                  next[idx] = {
                    ...next[idx],
                    qty: ln.qty,
                    // Only stamp raw_qty when the incoming AI line has
                    // one (cut-prone). Non-cut lines keep whatever
                    // raw_qty the existing row had (usually null).
                    ...(ln.raw_qty != null ? { raw_qty: ln.raw_qty } : {}),
                  };
                }
              }
              // Surface masked-out zones (brick, stone, garage, stucco) on
              // the estimate so the PDF / email can show "Materials
              // excluded: ..." under the siding row.
              const patch = { lines: next };
              if (measurements?._photo_zones_summary) {
                patch.photo_zones_summary = measurements._photo_zones_summary;
                patch.photo_zones_deducted_sqft = measurements._photo_zones_deducted_sqft || 0;
              }
              update(patch);
              if (save) await save({ ...est, ...patch });
            }}
          />
        </ToolTile>
      </div>

      {/* Iter 78z+++ — Workspace-level / contextual tools. Pair to LP
          is a workspace switcher, not a job-info action — it lives
          here in a low-emphasis row so it's reachable but doesn't
          compete with the importers. Compare Drawings only renders
          when 2+ measurement sources exist. */}
      {((est?.kind || "siding") === "siding" || numDrawingSources >= 2) && (
        <div className="flex flex-wrap gap-2 mb-4 justify-end" data-testid="job-info-more-tools">
          {numDrawingSources >= 2 && (
            <button
              type="button"
              onClick={() => setShowCompare(true)}
              className="px-2.5 py-1 text-[10px] uppercase tracking-wider font-bold text-[var(--muted)] hover:text-[var(--ai)] flex items-center gap-1"
              title="Side-by-side compare drawings across your measurement sources"
              data-testid="compare-drawings-btn"
            >
              <Layers className="w-3 h-3" />
              Compare ({numDrawingSources})
            </button>
          )}
          <PairToLpButton est={est} />
        </div>
      )}

      <div
        className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 ${collapsed ? "hidden" : ""}`}
        data-testid="job-info-form"
      >
        {/* Iter 79j.47 — 4 logically grouped sections. All fields
            optional; autosave debounces the whole payload. */}

        {/* --- 1. Customer --- */}
        <SubHeader testid="job-info-sub-customer">{t("est.customer")}</SubHeader>
        <div>
          <label className="label" htmlFor="cust-name">{t("est.customer")}</label>
          <input
            id="cust-name"
            className="input"
            value={est.customer_name || ""}
            onChange={(e) => update({ customer_name: e.target.value })}
            {...NO_AUTOFILL}
            data-testid="cust-name"
          />
        </div>
        <div>
          <label className="label" htmlFor="cust-company">{t("est.company")}</label>
          <input
            id="cust-company"
            className="input"
            value={est.customer_company || ""}
            onChange={(e) => update({ customer_company: e.target.value })}
            {...NO_AUTOFILL}
            data-testid="cust-company"
          />
        </div>
        <div>
          <label className="label" htmlFor="cust-contact-title">{t("est.contactTitle")}</label>
          <input
            id="cust-contact-title"
            className="input"
            value={est.customer_contact_title || ""}
            onChange={(e) => update({ customer_contact_title: e.target.value })}
            {...NO_AUTOFILL}
            data-testid="cust-contact-title"
          />
        </div>

        {/* --- 2. Contact & Lead --- */}
        <SubHeader testid="job-info-sub-contact">{t("est.contactInfo")}</SubHeader>
        <div>
          <label className="label" htmlFor="cust-phone">{t("est.phoneCell")}</label>
          <input
            id="cust-phone"
            className="input"
            type="tel"
            value={est.customer_phone || ""}
            onChange={(e) => update({ customer_phone: e.target.value })}
            onBlur={(e) => {
              markTouched("customer_phone");
              const norm = formatPhoneUS(e.target.value);
              if (norm !== (est.customer_phone || "")) update({ customer_phone: norm });
            }}
            placeholder={`${t("est.exampleLead")} (412) 555-0100`}
            aria-invalid={touched.customer_phone && !isValidPhone(est.customer_phone)}
            aria-describedby={touched.customer_phone && !isValidPhone(est.customer_phone) ? "cust-phone-warn" : undefined}
            {...NO_AUTOFILL}
            data-testid="cust-phone"
          />
          {touched.customer_phone && !isValidPhone(est.customer_phone) && (
            <FieldWarning id="cust-phone-warn">{t("est.warnPhone")}</FieldWarning>
          )}
        </div>
        <div>
          <label className="label" htmlFor="cust-phone-alt">{t("est.phoneAlt")}</label>
          <input
            id="cust-phone-alt"
            className="input"
            type="tel"
            value={est.customer_phone_alt || ""}
            onChange={(e) => update({ customer_phone_alt: e.target.value })}
            onBlur={(e) => {
              markTouched("customer_phone_alt");
              const norm = formatPhoneUS(e.target.value);
              if (norm !== (est.customer_phone_alt || "")) update({ customer_phone_alt: norm });
            }}
            placeholder={`${t("est.exampleLead")} (412) 555-0100`}
            aria-invalid={touched.customer_phone_alt && !isValidPhone(est.customer_phone_alt)}
            aria-describedby={touched.customer_phone_alt && !isValidPhone(est.customer_phone_alt) ? "cust-phone-alt-warn" : undefined}
            {...NO_AUTOFILL}
            data-testid="cust-phone-alt"
          />
          {touched.customer_phone_alt && !isValidPhone(est.customer_phone_alt) && (
            <FieldWarning id="cust-phone-alt-warn">{t("est.warnPhone")}</FieldWarning>
          )}
        </div>
        <div>
          <label className="label" htmlFor="cust-fax">{t("est.fax")}</label>
          <input
            id="cust-fax"
            className="input"
            type="tel"
            value={est.customer_fax || ""}
            onChange={(e) => update({ customer_fax: e.target.value })}
            onBlur={(e) => {
              markTouched("customer_fax");
              const norm = formatPhoneUS(e.target.value);
              if (norm !== (est.customer_fax || "")) update({ customer_fax: norm });
            }}
            placeholder={`${t("est.exampleLead")} (412) 555-0100`}
            aria-invalid={touched.customer_fax && !isValidPhone(est.customer_fax)}
            aria-describedby={touched.customer_fax && !isValidPhone(est.customer_fax) ? "cust-fax-warn" : undefined}
            {...NO_AUTOFILL}
            data-testid="cust-fax"
          />
          {touched.customer_fax && !isValidPhone(est.customer_fax) && (
            <FieldWarning id="cust-fax-warn">{t("est.warnPhone")}</FieldWarning>
          )}
        </div>
        <div>
          <label className="label" htmlFor="cust-email">{t("est.email")}</label>
          <input
            id="cust-email"
            className="input"
            type="email"
            value={est.customer_email || ""}
            onChange={(e) => update({ customer_email: e.target.value })}
            onBlur={() => markTouched("customer_email")}
            placeholder={`${t("est.exampleLead")} name@example.com`}
            aria-invalid={touched.customer_email && !isValidEmail(est.customer_email)}
            aria-describedby={touched.customer_email && !isValidEmail(est.customer_email) ? "cust-email-warn" : undefined}
            {...NO_AUTOFILL}
            data-testid="cust-email"
          />
          {touched.customer_email && !isValidEmail(est.customer_email) && (
            <FieldWarning id="cust-email-warn">{t("est.warnEmail")}</FieldWarning>
          )}
        </div>
        <div>
          <label className="label" htmlFor="cust-contact-method">{t("est.contactMethod")}</label>
          <select
            id="cust-contact-method"
            className="input"
            value={est.customer_contact_method || ""}
            onChange={(e) => update({ customer_contact_method: e.target.value })}
            data-testid="cust-contact-method"
          >
            <option value="">—</option>
            <option value="cell">{t("est.contactMethod.cell")}</option>
            <option value="landline">{t("est.contactMethod.landline")}</option>
            <option value="email">{t("est.contactMethod.email")}</option>
            <option value="text">{t("est.contactMethod.text")}</option>
          </select>
        </div>
        <div>
          <label className="label" htmlFor="lead-source">{t("est.leadSource")}</label>
          <select
            id="lead-source"
            className="input"
            value={est.lead_source || ""}
            onChange={(e) => {
              // Iter 79j.47 — Clear the detail field if the new slug
              // isn't one that reveals it, so stray detail text
              // doesn't survive a preset switch.
              const v = e.target.value;
              const patch = { lead_source: v };
              if (v !== "other" && v !== "referral") patch.lead_source_detail = "";
              update(patch);
            }}
            data-testid="lead-source"
          >
            <option value="">—</option>
            {LEAD_SOURCE_SLUGS.map((s) => (
              <option key={s} value={s}>{t(`est.leadSource.${s}`)}</option>
            ))}
          </select>
          {(est.lead_source === "other" || est.lead_source === "referral") && (
            <input
              className="input mt-2"
              placeholder={t("est.leadSourceDetail")}
              value={est.lead_source_detail || ""}
              onChange={(e) => update({ lead_source_detail: e.target.value })}
              {...NO_AUTOFILL}
              data-testid="lead-source-detail"
            />
          )}
        </div>

        {/* --- 3. Job & Billing Address --- */}
        <SubHeader testid="job-info-sub-address">{t("est.jobBilling")}</SubHeader>
        {/* Iter 79j.47 — Legacy-address fallback. If all structured
            parts are empty but a legacy `address` string exists,
            best-effort parse it for DISPLAY so the contractor sees
            their data. Actual parts are only persisted when they
            edit a field (writeAddress below). */}
        {(() => {
          const parts = {
            street: est.address_street ?? "",
            city: est.address_city ?? "",
            state: est.address_state ?? "",
            zip: est.address_zip ?? "",
          };
          const partsEmpty = !parts.street && !parts.city && !parts.state && !parts.zip;
          const legacy = partsEmpty ? parseLegacyAddress(est.address) : null;
          const disp = legacy || parts;
          const writeAddress = (patch) => {
            const next = { ...parts, ...(legacy || {}), ...patch };
            update({
              address_street: next.street,
              address_city: next.city,
              address_state: next.state,
              address_zip: next.zip,
              address: composeAddress(next.street, next.city, next.state, next.zip),
            });
          };
          return (
            <>
              <div className="sm:col-span-2 lg:col-span-2">
                <label className="label" htmlFor="cust-street">{t("est.street")}</label>
                <input
                  id="cust-street"
                  className="input"
                  value={disp.street || ""}
                  onChange={(e) => writeAddress({ street: e.target.value })}
                  {...NO_AUTOFILL}
                  data-testid="cust-street"
                />
              </div>
              <div>
                <label className="label" htmlFor="cust-city">{t("est.city")}</label>
                <input
                  id="cust-city"
                  className="input"
                  value={disp.city || ""}
                  onChange={(e) => writeAddress({ city: e.target.value })}
                  {...NO_AUTOFILL}
                  data-testid="cust-city"
                />
              </div>
              <div>
                <label className="label" htmlFor="cust-state">{t("est.state")}</label>
                <select
                  id="cust-state"
                  className="input"
                  value={disp.state || ""}
                  onChange={(e) => writeAddress({ state: e.target.value })}
                  data-testid="cust-state"
                >
                  <option value="">—</option>
                  {US_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="cust-zip">{t("est.zip")}</label>
                <input
                  id="cust-zip"
                  className="input"
                  inputMode="numeric"
                  maxLength={10}
                  value={disp.zip || ""}
                  onChange={(e) => writeAddress({ zip: e.target.value })}
                  onBlur={() => markTouched("address_zip")}
                  placeholder={`${t("est.exampleLead")} 15222`}
                  aria-invalid={touched.address_zip && !isValidZip(disp.zip)}
                  aria-describedby={touched.address_zip && !isValidZip(disp.zip) ? "cust-zip-warn" : undefined}
                  {...NO_AUTOFILL}
                  data-testid="cust-zip"
                />
                {touched.address_zip && !isValidZip(disp.zip) && (
                  <FieldWarning id="cust-zip-warn">{t("est.warnZip")}</FieldWarning>
                )}
              </div>
            </>
          );
        })()}
        {/* Billing = Job checkbox (billing_address === "" → checked) */}
        <div className="sm:col-span-2 lg:col-span-3">
          <label className="flex items-center gap-2 text-xs text-[var(--ink-2)] cursor-pointer">
            <input
              type="checkbox"
              className="w-4 h-4 accent-[var(--brand)]"
              checked={!(est.billing_address || "").trim()}
              onChange={(e) => {
                if (e.target.checked) {
                  // Re-check → clear all 5 billing fields.
                  update({
                    billing_address: "",
                    billing_street: "",
                    billing_city: "",
                    billing_state: "",
                    billing_zip: "",
                  });
                } else {
                  // Un-check → seed billing parts from the job address.
                  const s = est.address_street || "";
                  const c = est.address_city || "";
                  const st = est.address_state || "";
                  const z = est.address_zip || "";
                  update({
                    billing_street: s,
                    billing_city: c,
                    billing_state: st,
                    billing_zip: z,
                    billing_address: composeAddress(s, c, st, z) || (est.address || ""),
                  });
                }
              }}
              data-testid="billing-same-checkbox"
            />
            <span>{t("est.billingSame")}</span>
          </label>
        </div>
        {(est.billing_address || "").trim() !== "" && (() => {
          const writeBilling = (patch) => {
            const next = {
              street: est.billing_street ?? "",
              city: est.billing_city ?? "",
              state: est.billing_state ?? "",
              zip: est.billing_zip ?? "",
              ...patch,
            };
            update({
              billing_street: next.street,
              billing_city: next.city,
              billing_state: next.state,
              billing_zip: next.zip,
              billing_address: composeAddress(next.street, next.city, next.state, next.zip) || " ",
              // ↑ Non-empty sentinel so the checkbox stays un-checked
              // even before any field is filled in.
            });
          };
          return (
            <>
              <div className="sm:col-span-2 lg:col-span-2">
                <label className="label" htmlFor="billing-street">{t("est.billingAddress")} — {t("est.street")}</label>
                <input
                  id="billing-street"
                  className="input"
                  value={est.billing_street || ""}
                  onChange={(e) => writeBilling({ street: e.target.value })}
                  {...NO_AUTOFILL}
                  data-testid="billing-street"
                />
              </div>
              <div>
                <label className="label" htmlFor="billing-city">{t("est.city")}</label>
                <input
                  id="billing-city"
                  className="input"
                  value={est.billing_city || ""}
                  onChange={(e) => writeBilling({ city: e.target.value })}
                  {...NO_AUTOFILL}
                  data-testid="billing-city"
                />
              </div>
              <div>
                <label className="label" htmlFor="billing-state">{t("est.state")}</label>
                <select
                  id="billing-state"
                  className="input"
                  value={est.billing_state || ""}
                  onChange={(e) => writeBilling({ state: e.target.value })}
                  data-testid="billing-state"
                >
                  <option value="">—</option>
                  {US_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="billing-zip">{t("est.zip")}</label>
                <input
                  id="billing-zip"
                  className="input"
                  inputMode="numeric"
                  maxLength={10}
                  value={est.billing_zip || ""}
                  onChange={(e) => writeBilling({ zip: e.target.value })}
                  onBlur={() => markTouched("billing_zip")}
                  placeholder={`${t("est.exampleLead")} 15222`}
                  aria-invalid={touched.billing_zip && !isValidZip(est.billing_zip)}
                  aria-describedby={touched.billing_zip && !isValidZip(est.billing_zip) ? "billing-zip-warn" : undefined}
                  {...NO_AUTOFILL}
                  data-testid="billing-zip"
                />
                {touched.billing_zip && !isValidZip(est.billing_zip) && (
                  <FieldWarning id="billing-zip-warn">{t("est.warnZip")}</FieldWarning>
                )}
              </div>
            </>
          );
        })()}

        {/* --- 4. Estimate --- */}
        <SubHeader testid="job-info-sub-estimate">{t("est.estimateNum")}</SubHeader>
        <div>
          <label className="label" htmlFor="est-num">{t("est.estimateNum")}</label>
          <input
            id="est-num"
            className="input"
            value={est.estimate_number || ""}
            onChange={(e) => update({ estimate_number: e.target.value })}
            data-testid="est-num"
          />
        </div>
        <div>
          <label className="label" htmlFor="est-date">{t("est.date")}</label>
          <input
            id="est-date"
            className="input"
            type="date"
            value={est.estimate_date || ""}
            onChange={(e) => update({ estimate_date: e.target.value })}
            data-testid="est-date"
          />
        </div>
        <div>
          <label className="label" htmlFor="estimator-name">{t("est.estimator")}</label>
          <input
            id="estimator-name"
            className="input"
            value={est.estimator || ""}
            onChange={(e) => update({ estimator: e.target.value })}
            {...NO_AUTOFILL}
            data-testid="estimator-name"
          />
        </div>
        <div className="sm:col-span-2 lg:col-span-3">
          <label className="label" htmlFor="notes-input">{t("est.scope")}</label>
          <textarea
            id="notes-input"
            className="input"
            rows="3"
            value={est.notes || ""}
            onChange={(e) => update({ notes: e.target.value })}
            data-testid="notes-input"
          />
        </div>

        {/* Estimate-level colors — appear on the material list so the supplier
            pulls the right color stock for the whole job. Siding-kind only;
            window-only estimates show the Window Colors block below. */}
        {est.kind !== "windows" && (
        <div className="sm:col-span-2 lg:col-span-3 pt-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)] font-bold mb-2">
            {t("est.colors")}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
            <div>
              <label className="label">{isLp ? t("est.color.lpSiding") : t("est.color.siding")}</label>
              <select
                className="input"
                value={est.siding_color || ""}
                onChange={(e) => update({ siding_color: e.target.value })}
                data-testid="color-siding"
              >
                <option value="">— Select —</option>
                {isLp
                  ? LP_SMARTSIDE_COLORS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))
                  : vinylColorGroups.map((g) => (
                      <optgroup key={g.label} label={g.label}>
                        {g.colors.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </optgroup>
                    ))}
              </select>
            </div>
            {/* Iter 77 — LP SmartSiding doesn't use Ascend or Pelican Bay
                shake palettes; Howard asked to hide those two selectors on
                the LP workspace. Siding (vinyl/ascend) and ISS keep them. */}
            {est.kind !== "lp_smart" && (
            <div>
              <label className="label">{t("est.color.ascend")}</label>
              <select
                className="input"
                value={est.ascend_color || ""}
                onChange={(e) => update({ ascend_color: e.target.value })}
                data-testid="color-ascend"
              >
                <option value="">— Select —</option>
                {ASCEND_COLORS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            )}
            {est.kind !== "lp_smart" && (
            <div>
              <label className="label">{t("est.color.shake")}</label>
              <select
                className="input"
                value={est.shake_color || ""}
                onChange={(e) => update({ shake_color: e.target.value })}
                data-testid="color-shake"
              >
                <option value="">— Select —</option>
                {SHAKE_COLOR_GROUPS.map((g) => (
                  <optgroup key={g.label} label={g.label}>
                    {g.colors.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>
            )}
            <div>
              <label className="label">{t("est.color.boardBatten")}</label>
              <select
                className="input"
                value={est.board_batten_color || ""}
                onChange={(e) => update({ board_batten_color: e.target.value })}
                data-testid="color-board-batten"
              >
                <option value="">— Select —</option>
                {isLp
                  ? LP_SMARTSIDE_COLORS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))
                  : BOARD_BATTEN_COLOR_GROUPS.map((g) => (
                      <optgroup key={g.label} label={g.label}>
                        {g.colors.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </optgroup>
                    ))}
              </select>
            </div>
            <div>
              <label className="label">{isLp ? t("est.color.trim") : t("est.color.accessories")}</label>
              <select
                className="input"
                value={est.accessories_color || ""}
                onChange={(e) => update({ accessories_color: e.target.value })}
                data-testid="color-accessories"
              >
                <option value="">— Select —</option>
                {isLp
                  ? LP_SMARTSIDE_COLORS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))
                  : accessoryColorGroups.map((g) => (
                      <optgroup key={g.label} label={g.label}>
                        {g.colors.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </optgroup>
                    ))}
              </select>
            </div>
            <div>
              <label className="label">{t("est.color.outsideCorner")}</label>
              <select
                className="input"
                value={est.outside_corner_color || ""}
                onChange={(e) => update({ outside_corner_color: e.target.value })}
                data-testid="color-outside-corner"
              >
                <option value="">— Select —</option>
                {isLp
                  ? LP_SMARTSIDE_COLORS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))
                  : accessoryColorGroups.map((g) => (
                      <optgroup key={g.label} label={g.label}>
                        {g.colors.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </optgroup>
                    ))}
              </select>
            </div>
            <div>
              <label className="label">{t("est.color.soffitFascia")}</label>
              <select
                className="input"
                value={est.soffit_fascia_color || ""}
                onChange={(e) => update({ soffit_fascia_color: e.target.value })}
                data-testid="color-soffit-fascia"
              >
                <option value="">— Select —</option>
                {isLp
                  ? LP_SMARTSIDE_COLORS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))
                  : SOFFIT_COLOR_GROUPS.map((g) => (
                      <optgroup key={g.label} label={g.label}>
                        {g.colors.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </optgroup>
                    ))}
              </select>
            </div>
            {/* Iter 77 — LP SmartSide doesn't quote window wrap (factory
                trim handles window perimeters); hide the picker on LP. */}
            {!isLp && (
            <div>
              <label className="label">{t("est.color.windowWrap")}</label>
              <select
                className="input"
                value={est.window_wrap_color || ""}
                onChange={(e) => update({ window_wrap_color: e.target.value })}
                data-testid="color-window-wrap"
              >
                <option value="">— Select —</option>
                {WINDOW_WRAP_COLORS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            )}
            <div>
              <label className="label">{t("est.color.gutter")}</label>
              <select
                className="input"
                value={est.gutter_color || ""}
                onChange={(e) => update({ gutter_color: e.target.value })}
                data-testid="color-gutter"
              >
                <option value="">— Select —</option>
                {GUTTER_COLORS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
        )}

        {/* Window-product colors — Windows-kind estimates only. Siding
            estimates use the Window Wrap field above for capping color;
            frame / interior / exterior are window-product attributes. */}
        {est.kind === "windows" && (
        <div className="sm:col-span-2 lg:col-span-3 pt-2 space-y-5">
          {/* Iter 36: Install method + Lead-Safe — windows-job-level
              switches that auto-fill the matching install / lead-safe
              rows so contractors don't have to remember to add them. */}
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)] font-bold mb-2">
              Window Job Setup
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <label className="label">Default install method</label>
                <div className="grid grid-cols-2 gap-1.5" data-testid="install-method-toggle">
                  {[
                    { id: "pocket", label: "Pocket" },
                    { id: "full_fin", label: "Full Fin" },
                  ].map((opt) => {
                    const active = (est.install_method || "") === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        className={`px-3 py-2 text-xs font-bold uppercase tracking-wider border ${
                          active
                            ? "bg-[var(--bar-bg)] text-white border-[var(--border-strong)]"
                            : "bg-[var(--surface)] text-[var(--ink-2)] border-[var(--border)] hover:border-[var(--border-strong)]"
                        }`}
                        onClick={() =>
                          setInstallMethod && setInstallMethod(active ? "" : opt.id)
                        }
                        data-testid={`install-method-${opt.id}`}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
                <p className="text-[10px] text-[var(--muted)] mt-1.5 leading-snug">
                  Picks which install row the total window count flows into.
                  Override per-row anytime.
                </p>
              </div>
              <div>
                <label className="label">Lead-Safe RRP</label>
                <label
                  className={`flex items-start gap-2.5 px-3 py-2.5 border cursor-pointer ${
                    est.home_pre_1978
                      ? "bg-[#FEF3C7] border-[#F59E0B]"
                      : "bg-[var(--surface)] border-[var(--border)] hover:border-[var(--border-strong)]"
                  }`}
                  data-testid="pre-1978-toggle"
                >
                  <input
                    type="checkbox"
                    className="w-4 h-4 mt-0.5 accent-[var(--brand)] flex-shrink-0"
                    checked={!!est.home_pre_1978}
                    onChange={(ev) =>
                      setHomePre1978 && setHomePre1978(ev.target.checked)
                    }
                    data-testid="pre-1978-checkbox"
                  />
                  <div className="text-xs leading-snug">
                    <div className="font-bold text-[var(--ink)]">
                      Home built before 1978
                    </div>
                    <div className="text-[var(--muted)]">
                      Auto-adds Lead Safe Test Fee + Installation Practices for every window.
                    </div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--muted)] font-bold mb-3">
            {t("est.colors.windows")}
          </div>

          {/* VERO color block — hidden per user request (pricing TBD). White
              forced as the only color choice; the picker is suppressed until
              pricing for the other extruded / laminate / painted finishes is
              re-clarified. */}
          {false && (
          <div className="border border-[var(--border)] bg-[var(--surface)] p-4 mb-3">
            <div className="text-[11px] uppercase tracking-wider text-[var(--ink)] font-bold mb-3">
              Vero
              <span className="ml-2 text-[var(--muted)] font-normal normal-case tracking-normal">
                {t("win.colors.veroDesc")}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="label">{t("win.color.exterior")}</label>
                <select
                  className="input"
                  value={est.window_exterior_color || ""}
                  onChange={(e) => update({ window_exterior_color: e.target.value })}
                  data-testid="color-vero-exterior"
                >
                  <option value="">{t("win.color.select")}</option>
                  {VERO_EXTERIOR_COLOR_GROUPS.map((g) => (
                    <optgroup key={g.label} label={tColorGroup(g.label, lang)}>
                      {g.colors.map((c) => (
                        <option key={c} value={c}>{tColor(c, lang)}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">{t("win.color.interior")}</label>
                <select
                  className="input"
                  value={est.window_interior_color || ""}
                  onChange={(e) => update({ window_interior_color: e.target.value })}
                  data-testid="color-vero-interior"
                >
                  <option value="">{t("win.color.select")}</option>
                  {VERO_INTERIOR_COLOR_GROUPS.map((g) => (
                    <optgroup key={g.label} label={tColorGroup(g.label, lang)}>
                      {g.colors.map((c) => (
                        <option key={c} value={c}>{tColor(c, lang)}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
            </div>
            {/* Laminate ⇒ white base only. Warn if a tan extruded base is
                paired with a laminate exterior/interior. */}
            {(() => {
              const ext = est.window_exterior_color || "";
              const intr = est.window_interior_color || "";
              const hasLaminate = VERO_LAMINATE_NAMES.has(ext) || VERO_LAMINATE_NAMES.has(intr);
              const conflictsWithTan =
                (VERO_LAMINATE_NAMES.has(ext) && intr === "Tan") ||
                (VERO_LAMINATE_NAMES.has(intr) && ext === "Tan");
              if (conflictsWithTan) {
                return (
                  <div
                    className="mt-2 px-3 py-2 bg-[var(--danger-soft)] border-l-2 border-[#DC2626] text-[11px] text-[#991B1B]"
                    data-testid="vero-laminate-warning"
                    dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(t("win.color.laminateWarn")) }}
                  />
                );
              }
              if (hasLaminate) {
                return (
                  <div
                    className="mt-2 px-3 py-2 bg-[#F0F9FF] border-l-2 border-[#0284C7] text-[11px] text-[#075985]"
                    data-testid="vero-laminate-notice"
                    dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(t("win.color.laminateNotice")) }}
                  />
                );
              }
              return null;
            })()}
          </div>
          )}

          {/* MEZZO color block — solid extruded + FrameWorks / Woodgrain */}
          <div className="border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="text-[11px] uppercase tracking-wider text-[var(--ink)] font-bold mb-3">
              Mezzo
              <span className="ml-2 text-[var(--muted)] font-normal normal-case tracking-normal">
                {t("win.colors.mezzoDesc")}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="label">{t("win.color.exterior")}</label>
                <select
                  className="input"
                  value={est.mezzo_exterior_color || ""}
                  onChange={(e) => update({ mezzo_exterior_color: e.target.value })}
                  data-testid="color-mezzo-exterior"
                >
                  <option value="">{t("win.color.select")}</option>
                  {MEZZO_EXTERIOR_COLOR_GROUPS.map((g) => (
                    <optgroup key={g.label} label={tColorGroup(g.label, lang)}>
                      {g.colors.map((c) => (
                        <option key={c} value={c}>{tColor(c, lang)}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">{t("win.color.interior")}</label>
                <select
                  className="input"
                  value={est.mezzo_interior_color || ""}
                  onChange={(e) => update({ mezzo_interior_color: e.target.value })}
                  data-testid="color-mezzo-interior"
                >
                  <option value="">{t("win.color.select")}</option>
                  {MEZZO_INTERIOR_COLOR_GROUPS.map((g) => (
                    <optgroup key={g.label} label={tColorGroup(g.label, lang)}>
                      {g.colors.map((c) => (
                        <option key={c} value={c}>{tColor(c, lang)}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
            </div>
          </div>
          </div>
        </div>
        )}
      </div>
      <ElevationCompareModal
        est={est}
        open={showCompare}
        onClose={() => setShowCompare(false)}
      />
    </section>
  );
}
