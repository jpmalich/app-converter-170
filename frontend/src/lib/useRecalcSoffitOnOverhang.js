import { useEffect, useRef } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { porchCeilingTotalSqft } from "@/components/estimate/PorchCeilingsCard";

// OVERHANG / PORCH RECALC — server-side (D4+D5 fixed, Howard ruled
// 2026-07-31). The hook's own derivation math is RETIRED: the hard-coded
// LP_WASTE = 1.10 was a second waste emitter and the qty writes ignored
// qty_src. Overhang/porch changes now call the ONE shared rebuild
// (POST /estimates/{id}/rederive) — the same emitter that serves import,
// spec saves and the manual button, every family. Human-typed quantities
// survive absolutely (server stamps derived_qty for the chip).
//
// The two Porch Ceiling labor rows (Charter Oak White + beam wrap) are
// NOT register-derived — they stay client-managed here, with the human
// guard applied.

const PORCH_CHARTER = "Charter Oak Soffit White";
const PORCH_BEAM = "Wrap porch beam";
const PORCH_SECTION = "Porch Ceiling";
const CHARTER_OAK_SQFT_PER_PC = 10.0;

function porchBeamWrapLF(porches) {
  if (!Array.isArray(porches)) return 0;
  return porches.reduce((s, p) => {
    const L = Number(p.length_ft) || 0;
    const W = Number(p.width_ft) || 0;
    if (L <= 0 || W <= 0) return s;
    return s + L + 2 * W;
  }, 0);
}

function findCatalogItem(catalog, sectionTitle, itemName) {
  for (const sec of catalog || []) {
    if (sec.title === sectionTitle || sec.section === sectionTitle) {
      const items = sec.items || [];
      return items.find((it) => it.name === itemName) || null;
    }
  }
  return null;
}

// Update/auto-add the two Porch Ceiling rows. Human-typed rows keep their
// qty and get derived_qty stamped instead (R6 — human qty is absolute).
function applyPorchRows(lines, targets, catalog, tab) {
  let changed = 0;
  let next = (lines || []).map((l) => {
    if (!(l.name in targets)) return l;
    const newQty = targets[l.name];
    if (l.qty_src === "human") {
      if (l.derived_qty === newQty) return l;
      changed += 1;
      return { ...l, derived_qty: newQty };
    }
    if (l.qty === newQty) return l;
    changed += 1;
    return { ...l, qty: newQty };
  });
  for (const name of [PORCH_CHARTER, PORCH_BEAM]) {
    const exists = next.some((l) => l.section === PORCH_SECTION && l.name === name);
    if (!exists && targets[name] > 0) {
      const it = findCatalogItem(catalog, PORCH_SECTION, name);
      if (it) {
        next = [...next, {
          tab,
          section: PORCH_SECTION,
          name,
          unit: it.unit || (name === PORCH_BEAM ? "LF" : "PCS"),
          mat: Number(it.mat || 0),
          lab: Number(it.lab || 0),
          qty: targets[name],
        }];
        changed += 1;
      }
    }
  }
  return { next, changed };
}

export default function useRecalcSoffitOnOverhang(est, update, catalog = []) {
  const prevRef = useRef(undefined);
  const porchTotal = porchCeilingTotalSqft(est?.porch_ceilings);
  const beamWrapLF = porchBeamWrapLF(est?.porch_ceilings);

  useEffect(() => {
    if (!est) return;
    const current = Number(est.overhang_in ?? 12);
    const prev = prevRef.current;
    prevRef.current = { overhang: current, porchTotal };

    if (prev === undefined) return;
    if (prev.overhang === current && prev.porchTotal === porchTotal) return;

    const reasons = [];
    if (prev.overhang !== current) reasons.push(`overhang ${prev.overhang}" → ${current}"`);
    if (prev.porchTotal !== porchTotal)
      reasons.push(`porch ceilings ${prev.porchTotal} → ${porchTotal} sqft`);

    const hasMeasurements =
      est.hover_measurements && Object.keys(est.hover_measurements).length > 0;
    const tab = est.kind === "lp_smart" ? "lp_smart" : "vinyl";
    const porchTargets = {
      [PORCH_CHARTER]: porchTotal > 0
        ? Math.ceil(porchTotal / CHARTER_OAK_SQFT_PER_PC - 1e-9) : 0,
      [PORCH_BEAM]: beamWrapLF,
    };

    const run = async () => {
      let baseLines = est.lines || [];
      let derived = 0;
      if (hasMeasurements) {
        try {
          const { data } = await api.post(`/estimates/${est.id}/rederive`, {
            trigger: "overhang-porch",
            overhang_in: current,
            porch_ceilings: est.porch_ceilings || [],
          });
          if (Array.isArray(data?.lines)) {
            baseLines = data.lines;
            derived = 1;
          }
        } catch (e) {
          toast.error(e?.response?.data?.detail || "Re-derive failed — soffit rows unchanged");
        }
      }
      const { next, changed } = applyPorchRows(baseLines, porchTargets, catalog, tab);
      if (!derived && changed === 0) {
        toast.info(
          `Updated ${reasons.join(" + ")} — no measurements or matching rows yet; qty fills on next import.`
        );
        return;
      }
      update({ lines: next });
      toast.success(
        `${reasons.join(" + ")} — re-derived server-side${changed ? ` + ${changed} porch row${changed === 1 ? "" : "s"}` : ""} (human-typed quantities preserved)`
      );
    };
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [est?.overhang_in, porchTotal, beamWrapLF]);
}
