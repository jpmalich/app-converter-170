// SURFACE-ACCESS CHIP (Howard ruled 2026-08-11 send-3):
// "A surface that is invisible teaches me nothing; a surface that says
// what it is waiting for teaches me the shape of the gate."
//
// Contract:
//   1. NEVER invisible. If the surface it guards cannot render its output,
//      the chip renders in its place. Disabled is acceptable; hidden is not.
//   2. Names the STATE ("needs an applied run" / "photo door only" /
//      "needs a completed measurement" / etc.) so the contractor sees
//      what the surface is waiting for.
//   3. Names the WAY OUT so he knows what to do — start a run, switch
//      doors, upload a photo, tape the wall.
//   4. testid is caller-supplied and required — this chip is a load-bearing
//      instrument; a chip without a testid is a chip nobody can pin.
//
// See memory/entry_link_surface_audit_2026-08-11.md for the four
// instances that motivated this component.
import React from "react";
import { Lock } from "lucide-react";

export default function SurfaceAccessChip({ state, wayOut, testid, className = "" }) {
  return (
    <div
      data-testid={testid}
      data-surface-state={state}
      className={`inline-flex items-start gap-1.5 border border-[var(--border)] bg-[var(--surface-muted)] px-2 py-1 text-[11px] leading-snug text-[var(--muted)] ${className}`}
    >
      <Lock aria-hidden="true" className="w-3 h-3 mt-[2px] shrink-0" />
      <span>
        <span className="font-bold uppercase tracking-wider text-[10px] text-[var(--ink-2)]">
          {state}
        </span>
        {wayOut ? (
          <>
            {" · "}
            <span>{wayOut}</span>
          </>
        ) : null}
      </span>
    </div>
  );
}
