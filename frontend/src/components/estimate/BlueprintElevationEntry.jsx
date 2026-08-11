// BLUEPRINT ELEVATION ENTRY (Howard ruled 2026-08-11 send-3).
//
// Persistent, always-mounted entry point to the four blueprint elevation
// sheets (EL-1..EL-4). Renders on TWO surfaces — the Blueprint tile on
// the estimate page (before any read has been graded) AND inside the
// Takeoff Preview (while grading a read) — the two moments when the
// contractor wants the drawing beside the numbers.
//
// The rule this replaces: sheets used to require an applied run + an
// open run dialog to reach a link. That inverted grading — the drawing
// exists to help GRADE a read, and you cannot see it until you have
// ACCEPTED that read. Ruled reversed: the sheet renders from any
// completed read, applied or not.
//
// SurfaceAccessChip contract: this component is NEVER invisible. If no
// completed run exists yet, it renders a chip that names the state and
// the way out (see memory/entry_link_surface_audit_2026-08-11.md).
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import SurfaceAccessChip from "@/components/estimate/SurfaceAccessChip";

const WALLS = ["front", "right", "back", "left"];

export default function BlueprintElevationEntry({
  estId,
  where, // "blueprint-tile" | "takeoff-preview" — testid prefix
  compact = false,
}) {
  const [status, setStatus] = useState({ loading: true });
  useEffect(() => {
    let dead = false;
    if (!estId) return undefined;
    api
      .get(`/estimates/${estId}/blueprint-latest-run`)
      .then((r) => {
        if (!dead) setStatus({ loading: false, ...r.data });
      })
      .catch(() => {
        if (!dead) setStatus({ loading: false, available: false, state: "error" });
      });
    return () => {
      dead = true;
    };
  }, [estId]);

  const prefix = `bp-el-entry-${where}`;

  if (status.loading) {
    return (
      <SurfaceAccessChip
        state="Loading elevation sheets"
        wayOut=""
        testid={`${prefix}-loading`}
      />
    );
  }
  if (!status.available) {
    // Chip must speak: name the state and the way out.
    const map = {
      "no_run": {
        state: "Elevation sheets — needs a completed blueprint read",
        wayOut: "start a read from the Blueprints tile to enable EL-1..EL-4",
      },
      "running": {
        state: "Elevation sheets — blueprint read in progress",
        wayOut: "sheets appear once the read completes",
      },
      "queued": {
        state: "Elevation sheets — blueprint read queued",
        wayOut: "sheets appear once the read completes",
      },
      "error": {
        state: "Elevation sheets — last blueprint read errored",
        wayOut: "re-run from the Blueprints tile to enable EL-1..EL-4",
      },
    };
    const msg = map[status.state] || {
      state: `Elevation sheets — ${status.state || "unavailable"}`,
      wayOut: status.message || "start a read from the Blueprints tile",
    };
    return (
      <SurfaceAccessChip
        state={msg.state}
        wayOut={msg.wayOut}
        testid={`${prefix}-chip`}
      />
    );
  }

  // Available — render the four links. Walls carried by the run are
  // active; missing walls speak (the run didn't carry a wall for that
  // side — the sheet still renders as "no wall" per Phase 1 doctrine
  // but we mark the link so the contractor knows what he'll see).
  const carried = new Set(status.walls || []);
  return (
    <div
      className="flex items-center gap-2 flex-wrap"
      data-testid={`${prefix}`}
    >
      <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
        Elevation sheets
      </span>
      {WALLS.map((w, i) => {
        const has = carried.has(w);
        const testid = `${prefix}-link-${w}`;
        return (
          <React.Fragment key={w}>
            <Link
              to={`/estimate/${estId}/blueprint-elevation/${w}`}
              className={`text-[11px] underline font-bold uppercase tracking-wider ${
                has ? "text-[var(--ai)]" : "text-[var(--muted)]"
              }`}
              data-testid={testid}
              title={
                has
                  ? `EL-${i + 1} ${w} — carried by run ${String(status.run_id || "").slice(0, 8)}`
                  : `EL-${i + 1} ${w} — no wall in run; sheet renders NEEDS-YOUR-TAPE`
              }
            >
              EL-{i + 1} {w}
              {!has ? " ⚠" : ""}
            </Link>
            {i < WALLS.length - 1 && (
              <span className="text-[10px] text-[var(--muted)]">·</span>
            )}
          </React.Fragment>
        );
      })}
      {!compact && (
        <span
          className="text-[9px] text-[var(--muted)] ml-1"
          data-testid={`${prefix}-source`}
        >
          run {String(status.run_id || "").slice(0, 8)}
          {status.applied ? " · applied" : " · not applied"}
        </span>
      )}
    </div>
  );
}
