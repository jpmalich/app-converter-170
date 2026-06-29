import React from "react";
import { Plus, Trash2, Home } from "lucide-react";

// Iter 78aj — Porch Ceilings list editor.
// Howard's quoting flow: "Porch ceiling is 22' along house × 10' out
// from house". Multiple porches per house are common on nicer homes
// (front + back + side entry), so we keep an array rather than a
// single sqft field. Total sqft is computed live and routed into the
// soffit qty formula via `useRecalcSoffitOnOverhang`.

const round2 = (n) => Math.round(Number(n || 0) * 100) / 100;

export function porchCeilingTotalSqft(porches) {
  if (!Array.isArray(porches)) return 0;
  return porches.reduce(
    (s, p) => s + (Number(p.length_ft) || 0) * (Number(p.width_ft) || 0),
    0
  );
}

export default function PorchCeilingsCard({ value = [], onChange }) {
  const porches = Array.isArray(value) ? value : [];
  const total = porchCeilingTotalSqft(porches);

  const update = (idx, patch) => {
    const next = porches.map((p, i) => (i === idx ? { ...p, ...patch } : p));
    onChange(next);
  };

  const add = () => {
    onChange([
      ...porches,
      { label: porches.length === 0 ? "Front Porch" : "", length_ft: 0, width_ft: 0 },
    ]);
  };

  const remove = (idx) => {
    onChange(porches.filter((_, i) => i !== idx));
  };

  return (
    <div className="border border-[#E4E4E7] p-3 mt-2" data-testid="porch-ceilings-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <Home className="w-3.5 h-3.5 text-[#71717A]" />
          <span className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#71717A]">
            Porch Ceilings
          </span>
        </div>
        <div
          className="font-mono-num text-[11px] text-[#09090B] font-bold"
          data-testid="porch-ceilings-total"
        >
          Total: {round2(total)} sqft
        </div>
      </div>

      {porches.length === 0 && (
        <div className="text-[11px] text-[#71717A] italic mb-2 leading-snug">
          No porch ceilings yet. Add one if this job has a covered porch,
          breezeway, or soffited bay overhang — the sqft is rolled into the
          soffit qty automatically.
        </div>
      )}

      {porches.map((p, i) => {
        const area = round2((Number(p.length_ft) || 0) * (Number(p.width_ft) || 0));
        return (
          <div
            key={i}
            className="flex items-center gap-2 py-1.5 border-t border-[#F4F4F5] first-of-type:border-t-0"
            data-testid={`porch-row-${i}`}
          >
            <input
              type="text"
              className="input h-8 text-xs flex-1 min-w-0"
              placeholder="Front Porch / Side Entry / etc."
              value={p.label || ""}
              onChange={(e) => update(i, { label: e.target.value })}
              data-testid={`porch-label-${i}`}
            />
            <input
              type="number"
              step="0.5"
              min="0"
              className="input h-8 text-xs w-16 text-right font-mono-num"
              placeholder="L"
              value={p.length_ft || ""}
              onChange={(e) => update(i, { length_ft: Number(e.target.value) || 0 })}
              data-testid={`porch-length-${i}`}
            />
            <span className="text-[10px] text-[#A1A1AA]">ft ×</span>
            <input
              type="number"
              step="0.5"
              min="0"
              className="input h-8 text-xs w-16 text-right font-mono-num"
              placeholder="W"
              value={p.width_ft || ""}
              onChange={(e) => update(i, { width_ft: Number(e.target.value) || 0 })}
              data-testid={`porch-width-${i}`}
            />
            <span className="text-[10px] text-[#A1A1AA]">ft =</span>
            <span
              className="font-mono-num text-xs text-[#09090B] w-20 text-right tabular-nums"
              data-testid={`porch-area-${i}`}
            >
              {area} sqft
            </span>
            <button
              type="button"
              onClick={() => remove(i)}
              className="text-[#71717A] hover:text-[#DC2626] p-1"
              title="Remove porch"
              data-testid={`porch-remove-${i}`}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}

      <button
        type="button"
        onClick={add}
        className="mt-2 flex items-center gap-1 text-[10px] uppercase tracking-[0.18em] font-bold text-[#52525B] hover:text-[#09090B]"
        data-testid="porch-add"
      >
        <Plus className="w-3.5 h-3.5" />
        {porches.length === 0 ? "Add porch ceiling" : "Add another porch"}
      </button>
    </div>
  );
}
