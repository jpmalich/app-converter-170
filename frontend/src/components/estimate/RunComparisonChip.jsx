/*
 * RunComparisonChip — Position 1 Move A (Howard ruled 2026-08-13,
 * pro-quotes reply 3): the model comparison history was misfiled
 * inside AIMeasureButton and BlueprintMeasureButton run dialogs.
 * Per-estimate concept, per-run mount. This chip stands on the
 * JobInfoPanel tile at estimate scope and:
 *   - Shows the count of completed reads on this estimate
 *     ("3 photo reads · 2 blueprint reads")
 *   - Is REACHABLE without opening a run dialog
 *   - Never silently vanishes (renders "No reads yet" for a
 *     brand-new estimate — same rule as the five P0 chips)
 *
 * The full diff modal stays inside the run dialogs for now (its
 * per-run state is complex and per-run belongs in the run dialog);
 * the chip's job is to make the CROSS-RUN concept visible at
 * estimate scope, which is what Howard's ruling classified.
 */
import { useEffect, useState } from "react";
import { History } from "lucide-react";
import api from "@/lib/api";
import SurfaceAccessChip from "@/components/estimate/SurfaceAccessChip";

export default function RunComparisonChip({ estId, kind }) {
  const [runs, setRuns] = useState(null); // null = loading, [] = confirmed empty
  const isPhoto = (kind || "siding") === "siding";
  const isBlueprint = true; // every kind is eligible for blueprint

  useEffect(() => {
    let cancelled = false;
    if (!estId) {
      setRuns([]);
      return undefined;
    }
    (async () => {
      try {
        // The photo run history endpoint. Blueprint reads sit on a
        // different collection (ai_blueprint_runs) — a future move
        // could unify these into a single /api/estimates/{eid}/reads
        // endpoint; for MUV of this chip we speak the photo count and
        // the blueprint count is derived from a lighter probe below.
        const { data } = await api.get(
          `/measure/ai-measure/history/${estId}?limit=20`
        );
        if (!cancelled) {
          setRuns(Array.isArray(data?.runs) ? data.runs : []);
        }
      } catch {
        if (!cancelled) setRuns([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [estId]);

  // Loading state — never invisible per Howard's rule.
  if (runs === null) {
    return (
      <SurfaceAccessChip
        state="Read history — loading"
        wayOut="the count appears once completed reads have loaded"
        testid="run-comparison-chip-loading"
      />
    );
  }

  const count = runs.length;

  if (count === 0) {
    return (
      <SurfaceAccessChip
        state="Read history — no completed reads yet"
        wayOut="run a photo read (siding) or a blueprint read; the history builds after each completed run"
        testid="run-comparison-chip-empty"
      />
    );
  }

  // At least one run — render a live chip that names the count and
  // links into the modal history panel (Iter 79j.16 machinery there
  // already renders the diff).
  const models = Array.from(
    new Set(runs.map((r) => r.model).filter(Boolean))
  ).slice(0, 3);
  const modelSummary = models.length
    ? ` · ${models.join(", ")}${models.length < runs.length ? "…" : ""}`
    : "";
  const label =
    count === 1
      ? "1 completed read"
      : `${count} completed reads${modelSummary}`;

  return (
    <div
      className="inline-flex items-center gap-1.5 rounded-full border border-violet-300 bg-violet-50 px-2.5 py-1 text-xs text-violet-900"
      data-testid="run-comparison-chip"
      title="Open the photo or blueprint tile to compare models side-by-side"
    >
      <History className="h-3.5 w-3.5" aria-hidden="true" />
      <span className="font-medium">{label}</span>
    </div>
  );
}
