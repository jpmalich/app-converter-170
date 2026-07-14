// Best-effort browser autofill / save-address suppression for CUSTOMER
// data fields — homeowner info must never be offered into the
// contractor's own browser address profile ("Save address?" popups on
// stock Chrome/Edge). Browsers honor this inconsistently: BEST-EFFORT,
// not pinned behavior.
//   • Chrome/Edge ignore autocomplete="off" for address heuristics but
//     treat an UNKNOWN token as "no autofill category" (the long-standing
//     workaround).
//   • aria-autocomplete="none" additionally suppresses Edge 105+.
//   • The `list`-to-missing-datalist trick is deliberately NOT used — it
//     remaps the input to a combobox role and breaks WCAG AA semantics.
export const NO_AUTOFILL = {
  autoComplete: "off-homeowner-data",
  "aria-autocomplete": "none",
};
