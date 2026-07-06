// Dev/design preview for the Blueprint Instrument foundation.
// Public route: /design/blueprint — renders the primitives + both themes so the
// design system can be reviewed live before any screen is converted. Not linked
// from app navigation; safe to leave in place during the redesign.

import React, { useState } from "react";
import {
  BlueprintScope,
  DrawingSheet,
  TitleBlock,
  DrawingLabel,
  DimensionLine,
  InstrumentKpi,
  Stamp,
} from "@/components/ui/blueprint";

export default function BlueprintPreview() {
  const [theme, setTheme] = useState("light");

  return (
    <BlueprintScope
      theme={theme}
      style={{ background: "var(--bp-desk)", minHeight: "100vh", padding: "clamp(14px,3vw,40px)" }}
    >
      <div style={{ maxWidth: 1160, margin: "0 auto" }}>
        <DrawingSheet>
          <TitleBlock
            title="Pro-Quote · Estimating Sheet"
            subtitle="Blueprint Instrument — foundation preview"
            cells={[
              { k: "Sheet", v: "A-00" },
              { k: "Rev", v: "02" },
              { k: "Scale", v: "1:1" },
            ]}
            right={
              <div style={{ display: "flex" }}>
                <button
                  className="bp-btn"
                  style={{ borderTop: "none", borderBottom: "none", borderRight: "none" }}
                  aria-pressed={theme === "light"}
                  onClick={() => setTheme("light")}
                >
                  Whiteprint
                </button>
                <button
                  className="bp-btn"
                  style={{ borderTop: "none", borderBottom: "none", borderRight: "none" }}
                  aria-pressed={theme === "dark"}
                  onClick={() => setTheme("dark")}
                >
                  Blueprint
                </button>
              </div>
            }
          />

          <DrawingLabel code="A-01" title="Instrument readouts" note="30-day window" />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
            <InstrumentKpi label="Quoted" value="$184,200" delta="▲ 12.4%" direction="up" />
            <InstrumentKpi label="Won" value="$92,600" delta="▲ 8.1%" direction="up" />
            <InstrumentKpi label="Open" value="14" delta={<span className="bp-markup">◆ 3 flagged</span>} />
            <InstrumentKpi label="Close rate" value="38%" delta="▼ 2.0%" direction="down" />
          </div>

          <DrawingLabel code="A-02" title="Primitives" note="dimension · stamp · input" />
          <div className="bp-panel" style={{ padding: 18, display: "grid", gap: 16 }}>
            <div style={{ maxWidth: 220 }}>
              <DimensionLine value="24.0 SQ · 10% waste" />
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <Stamp variant="won">Won</Stamp>
              <Stamp variant="sent">Sent</Stamp>
              <Stamp variant="draft">Draft</Stamp>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
              <label style={{ display: "grid", gap: 4, fontSize: 9, letterSpacing: ".12em", textTransform: "uppercase", color: "var(--bp-muted)", fontWeight: 700 }}>
                Qty
                <input className="bp-input" defaultValue="24" aria-label="Sample quantity" style={{ width: 90 }} />
              </label>
              <button className="bp-btn bp-btn--go">Customer Quote →</button>
              <button className="bp-btn">Material List ▤</button>
            </div>
            <div className="bp-markup">◆ redline: verify soffit LF against HOVER sheet</div>
          </div>
        </DrawingSheet>
      </div>
    </BlueprintScope>
  );
}
