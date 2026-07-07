// Blueprint Instrument — reusable design-system primitives (Rev 2).
// Spec: docs/specs/redesign-system.md
//
// These are presentational primitives that render the Blueprint visual
// language. They rely on the scoped classes in `src/styles/blueprint.css` and
// only take effect inside a subtree carrying `data-design="blueprint"` — use
// <BlueprintScope> as the wrapper. Nothing here is wired into existing screens
// yet (screen conversion is a later PR).

import React from "react";

function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

// Opt-in wrapper. `theme="dark"` selects the cyanotype palette.
export function BlueprintScope({ theme = "light", className, style, children, ...rest }) {
  return (
    <div
      data-design="blueprint"
      data-bp-theme={theme === "dark" ? "dark" : "light"}
      className={className}
      style={style}
      {...rest}
    >
      {children}
    </div>
  );
}

// The drawing sheet: frame + graph-paper substrate.
export function DrawingSheet({ className, children, ...rest }) {
  return (
    <div className={cx("bp-sheet", className)} {...rest}>
      <div className="bp-sheet__pad">{children}</div>
    </div>
  );
}

// Architect's title block. `cells` = [{ k, v }]; `right` renders in a trailing slot.
export function TitleBlock({ mark = "PQ", title, subtitle, cells = [], right }) {
  return (
    <div className="bp-titleblock">
      <div className="bp-titleblock__brand">
        <div className="bp-titleblock__mark">{mark}</div>
        <div>
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </div>
      {cells.map((c) => (
        <div className="bp-titleblock__cell" key={c.k}>
          <span className="k">{c.k}</span>
          <span className="v">{c.v}</span>
        </div>
      ))}
      {right}
    </div>
  );
}

// Section eyebrow, coded like a drawing sheet.
export function DrawingLabel({ code, title, note }) {
  return (
    <div className="bp-dlabel">
      {code ? <span className="bp-dlabel__code">{code}</span> : null}
      <h2 className="bp-dlabel__title">{title}</h2>
      <span className="bp-dlabel__rule" />
      {note ? <span className="bp-dlabel__note">{note}</span> : null}
    </div>
  );
}

// A drawn measurement.
export function DimensionLine({ value, className }) {
  return (
    <div className={cx("bp-dim", className)}>
      <span className="bp-dim__rule" />
      <span className="bp-dim__val">{value}</span>
      <span className="bp-dim__rule" />
    </div>
  );
}

// Instrument-style KPI. `direction` = "up" | "down" | undefined.
export function InstrumentKpi({ label, value, delta, direction }) {
  const dirClass = direction === "up" ? "bp-up" : direction === "down" ? "bp-down" : "";
  return (
    <div className="bp-panel bp-kpi">
      <div className="bp-kpi__k">{label}</div>
      <div className="bp-kpi__v">{value}</div>
      {delta ? (
        <div className={cx("bp-kpi__foot", dirClass)}>{delta}</div>
      ) : null}
    </div>
  );
}

// Rubber-stamp status. `variant` = "won" | "sent" | "draft".
export function Stamp({ variant = "draft", children, className, ...rest }) {
  return (
    <span className={cx("bp-stamp", `bp-stamp--${variant}`, className)} {...rest}>
      {children}
    </span>
  );
}
