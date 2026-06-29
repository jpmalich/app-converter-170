import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { porchCeilingTotalSqft } from "@/components/estimate/PorchCeilingsCard";

// Iter 78ai/78aj/78ak — Auto-recalculate soffit material qty + Porch
// Ceiling labor rows when the contractor changes the Eave Overhang
// field OR edits any porch ceiling dimension.
//
// Behaviour:
//   • Fires only when overhang OR porch-ceiling-total actually changes.
//   • Recomputes qty for 3 soffit rows (Charter Oak + LP Vented + LP
//     Closed) using `eaves_lf` + `rakes_lf` cached on
//     `est.hover_measurements` PLUS the live porch ceiling total.
//   • Recomputes qty for 2 Porch Ceiling section rows:
//       - "With or without siding Charter Oak"  (sqft)
//       - "Wrap porch beam"  (LF = sum of length + 2 × width per porch)
//     Lines are AUTO-ADDED to est.lines using catalog mat/lab when
//     they don't exist yet and porchTotalSqft > 0. When porchTotal
//     goes back to 0, qty is set to 0 (line stays so contractor can
//     manually re-edit if they want).
//   • If there's neither HOVER measurement data NOR porches, no-op.
//   • Single toast summarising what was recalculated.

const CHARTER_OAK_SOFFIT = "Charter Oak Soffit Standard color";
const LP_VENTED = "38 Series Soffit 16 x 16 Vented";
const LP_CLOSED = "38 Series Soffit 16 x 16 Closed";

// Iter 78ak — Porch Ceiling catalog row names (exact strings from
// catalog_seed.py).
const PORCH_CHARTER = "With or without siding Charter Oak";
const PORCH_BEAM = "Wrap porch beam";
const PORCH_SECTION = "Porch Ceiling";

// PDF coverage rates — must mirror `backend/lp_smartside_formulas.py`
// and the legacy Vinyl/Ascend formulas in `backend/routes/hover.py`.
const LP_SOFFIT_SQFT_PER_PC = 21.3;     // 16" Soffit panel (Howard's default)
const LP_WASTE = 1.10;                   // 10% waste + ceil
const CHARTER_OAK_SQFT_PER_PC = 10.0;    // 10" exposure × 12' panel

// Iter 78ak — Beam wrap LF per porch. Convention: porch is rectangular
// with the long side abutting the house wall (no beam), so beam wrap
// covers the front edge (length) + the two short sides (2 × width).
// Howard's typical 22'×10' porch → 22 + 2×10 = 42 LF of beam wrap.
function porchBeamWrapLF(porches) {
  if (!Array.isArray(porches)) return 0;
  return porches.reduce((s, p) => {
    const L = Number(p.length_ft) || 0;
    const W = Number(p.width_ft) || 0;
    if (L <= 0 || W <= 0) return s;
    return s + L + 2 * W;
  }, 0);
}

// Look up a catalog item's price + unit so we can hydrate a new line.
function findCatalogItem(catalog, sectionTitle, itemName) {
  for (const sec of catalog || []) {
    if (sec.title === sectionTitle || sec.section === sectionTitle) {
      const items = sec.items || [];
      return items.find((it) => it.name === itemName) || null;
    }
  }
  return null;
}

function lpSoffitPcs(overhangIn, lf, extraSqft = 0) {
  const area = (overhangIn / 12.0) * (lf || 0) + (extraSqft || 0);
  if (area <= 0) return 0;
  return Math.max(0, Math.ceil(area / LP_SOFFIT_SQFT_PER_PC * LP_WASTE));
}

function charterOakSoffitPcs(overhangIn, eavesLf, rakesLf, extraSqft = 0) {
  const totalLf = (eavesLf || 0) + (rakesLf || 0);
  const area = (overhangIn / 12.0) * totalLf + (extraSqft || 0);
  if (area <= 0) return 0;
  return Math.max(0, Math.ceil(area / CHARTER_OAK_SQFT_PER_PC));
}

export default function useRecalcSoffitOnOverhang(est, update, catalog = []) {
  // Track previous (overhang, porchTotal) tuple so we know when either
  // changed and can decide what to mention in the toast.
  const prevRef = useRef(undefined);

  const porchTotal = porchCeilingTotalSqft(est?.porch_ceilings);
  const beamWrapLF = porchBeamWrapLF(est?.porch_ceilings);

  useEffect(() => {
    if (!est) return;
    const current = Number(est.overhang_in ?? 12);
    const prev = prevRef.current;
    prevRef.current = { overhang: current, porchTotal };

    // Skip initial mount — only react to actual changes.
    if (prev === undefined) return;
    if (prev.overhang === current && prev.porchTotal === porchTotal) return;

    const m = est.hover_measurements;
    const eavesLf = Number(m?.eaves_lf) || 0;
    const rakesLf = Number(m?.rakes_lf) || 0;
    const hasLf = eavesLf > 0 || rakesLf > 0;
    const hasPorch = porchTotal > 0;

    if (!hasLf && !hasPorch) {
      const changes = [];
      if (prev.overhang !== current) changes.push(`overhang ${prev.overhang}" → ${current}"`);
      if (prev.porchTotal !== porchTotal)
        changes.push(`porch ceilings ${prev.porchTotal} → ${porchTotal} sqft`);
      toast.info(
        `Updated ${changes.join(" + ")} — no measurements or porches yet, soffit qty will fill on next import.`
      );
      return;
    }

    // Soffit qty targets — porches go to the Vented (eave) row by
    // convention since front porch ceilings sit under the main eave.
    const targets = {
      [CHARTER_OAK_SOFFIT]: charterOakSoffitPcs(current, eavesLf, rakesLf, porchTotal),
      [LP_VENTED]: lpSoffitPcs(current, eavesLf, porchTotal),
      [LP_CLOSED]: lpSoffitPcs(current, rakesLf),
      // Iter 78ak — Porch Ceiling labor rows (always in sync with
      // porch dimensions). qty=0 just means "no porches right now".
      [PORCH_CHARTER]: porchTotal,
      [PORCH_BEAM]: beamWrapLF,
    };

    let changed = 0;
    let lines = (est.lines || []).map((l) => {
      if (!(l.name in targets)) return l;
      const newQty = targets[l.name];
      if (l.qty === newQty) return l;
      changed += 1;
      return { ...l, qty: newQty };
    });

    // Iter 78ak — auto-add the 2 Porch Ceiling rows when porches just
    // got typed in for the first time and they're not yet in est.lines.
    const charterExists = lines.some(
      (l) => l.section === PORCH_SECTION && l.name === PORCH_CHARTER
    );
    const beamExists = lines.some(
      (l) => l.section === PORCH_SECTION && l.name === PORCH_BEAM
    );
    const tab = est.kind === "lp_smart" ? "lp_smart" : "vinyl";
    const newRows = [];
    if (!charterExists && porchTotal > 0) {
      const it = findCatalogItem(catalog, PORCH_SECTION, PORCH_CHARTER);
      if (it) {
        newRows.push({
          tab,
          section: PORCH_SECTION,
          name: PORCH_CHARTER,
          unit: it.unit || "SQ FT",
          mat: Number(it.mat || 0),
          lab: Number(it.lab || 0),
          qty: porchTotal,
        });
      }
    }
    if (!beamExists && beamWrapLF > 0) {
      const it = findCatalogItem(catalog, PORCH_SECTION, PORCH_BEAM);
      if (it) {
        newRows.push({
          tab,
          section: PORCH_SECTION,
          name: PORCH_BEAM,
          unit: it.unit || "LF",
          mat: Number(it.mat || 0),
          lab: Number(it.lab || 0),
          qty: beamWrapLF,
        });
      }
    }
    if (newRows.length > 0) {
      lines = [...lines, ...newRows];
      changed += newRows.length;
    }

    // Compose toast message describing what triggered the recalc
    const reasons = [];
    if (prev.overhang !== current) reasons.push(`overhang ${prev.overhang}" → ${current}"`);
    if (prev.porchTotal !== porchTotal)
      reasons.push(`porch ceilings ${prev.porchTotal} → ${porchTotal} sqft`);

    if (changed === 0) {
      toast.info(
        `Updated ${reasons.join(" + ")}. No matching rows to recalc — they'll fill on next HOVER/AI import.`
      );
      return;
    }

    update({ lines });
    toast.success(
      `${reasons.join(" + ")} — recalculated ${changed} row${changed === 1 ? "" : "s"}`
    );
    // ESLint disable next line — we intentionally only react to overhang
    // or porch_total changes; including the full `est` would re-run on
    // every keystroke in an unrelated field.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [est?.overhang_in, porchTotal, beamWrapLF]);
}
