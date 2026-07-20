// Feature flags (Howard's rulings — flip only on a ruling).
//
// RENDER_3D_ENABLED (ruled 2026-07-20): 3D is OFF for ALL audiences —
// contractor mounts (LP panel / AI Measure / Blueprint previews), DEMO
// mode (inherits the contractor panels), the customer accept-page orbit
// view, and the static quote PNG. Code, tests and pins stay intact for
// re-entry (stop-loss doctrine). Asserted-absence pins enforce that no
// route, toggle, setting or URL renders a 3D while this is false.
export const RENDER_3D_ENABLED = false;
