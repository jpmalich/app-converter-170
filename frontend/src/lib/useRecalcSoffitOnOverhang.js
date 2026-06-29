import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { porchCeilingTotalSqft } from "@/components/estimate/PorchCeilingsCard";

// Iter 78ai/78aj — Auto-recalculate soffit material qty when the
// contractor changes the Eave Overhang field OR edits any porch
// ceiling dimension (length / width / add / remove). Soffit pieces
// are computed at import time using the overhang value of the moment;
// without this hook, editing overhang or adding porches later leaves
// the original soffit qty stale.
//
// Behaviour:
//   • Fires only when overhang OR porch-ceiling-total actually changes.
//   • Recomputes qty for the 3 soffit rows (Charter Oak + LP Vented + LP Closed)
//     using `eaves_lf` + `rakes_lf` cached on `est.hover_measurements`
//     AND the porch ceiling total sqft (live-summed from est.porch_ceilings).
//   • If there's neither HOVER measurement data NOR porches, no-op toast.
//   • Always overwrites existing qty — Howard's call (Iter 78ai).
//   • Single toast summarising what was recalculated.

const CHARTER_OAK_SOFFIT = "Charter Oak Soffit Standard color";
const LP_VENTED = "38 Series Soffit 16 x 16 Vented";
const LP_CLOSED = "38 Series Soffit 16 x 16 Closed";

// PDF coverage rates — must mirror `backend/lp_smartside_formulas.py`
// and the legacy Vinyl/Ascend formulas in `backend/routes/hover.py`.
const LP_SOFFIT_SQFT_PER_PC = 21.3;     // 16" Soffit panel (Howard's default)
const LP_WASTE = 1.10;                   // 10% waste + ceil
const CHARTER_OAK_SQFT_PER_PC = 10.0;    // 10" exposure × 12' panel

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

export default function useRecalcSoffitOnOverhang(est, update) {
  // Track previous (overhang, porchTotal) tuple so we know when either
  // changed and can decide what to mention in the toast.
  const prevRef = useRef(undefined);

  const porchTotal = porchCeilingTotalSqft(est?.porch_ceilings);

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
      // Build a short descriptor for what changed so the toast is useful
      const changes = [];
      if (prev.overhang !== current) changes.push(`overhang ${prev.overhang}" → ${current}"`);
      if (prev.porchTotal !== porchTotal)
        changes.push(`porch ceilings ${prev.porchTotal} → ${porchTotal} sqft`);
      toast.info(
        `Updated ${changes.join(" + ")} — no measurements or porches yet, soffit qty will fill on next import.`
      );
      return;
    }

    // Porch ceilings sit under eaves (Vented) by convention — front
    // porch / breezeway covered ceiling all vent into the soffit on
    // the eave side of the house.
    const targets = {
      [CHARTER_OAK_SOFFIT]: charterOakSoffitPcs(current, eavesLf, rakesLf, porchTotal),
      [LP_VENTED]: lpSoffitPcs(current, eavesLf, porchTotal),
      [LP_CLOSED]: lpSoffitPcs(current, rakesLf),
    };

    let changed = 0;
    const newLines = (est.lines || []).map((l) => {
      if (!(l.name in targets)) return l;
      const newQty = targets[l.name];
      if (l.qty === newQty) return l;
      changed += 1;
      return { ...l, qty: newQty };
    });

    // Compose toast message describing what triggered the recalc
    const reasons = [];
    if (prev.overhang !== current) reasons.push(`overhang ${prev.overhang}" → ${current}"`);
    if (prev.porchTotal !== porchTotal)
      reasons.push(`porch ceilings ${prev.porchTotal} → ${porchTotal} sqft`);

    if (changed === 0) {
      toast.info(
        `Updated ${reasons.join(" + ")}. No soffit rows in this estimate to recalc — they'll pick up the new value on the next HOVER/AI import.`
      );
      return;
    }

    update({ lines: newLines });
    toast.success(
      `${reasons.join(" + ")} — recalculated ${changed} soffit row${changed === 1 ? "" : "s"}`
    );
    // ESLint disable next line — we intentionally only react to overhang
    // or porch_total changes; including the full `est` would re-run on
    // every keystroke in an unrelated field.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [est?.overhang_in, porchTotal]);
}
