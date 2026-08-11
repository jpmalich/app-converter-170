// WRITE-THROUGH (Howard ruled 2026-08-11 send-4).
//
// "A WRITE THAT IS REFUSED MUST SAY SO. No optimistic local state
// survives a non-2xx response. Roll it back and surface the refusal
// in words — 'this estimate is protected; nothing was saved' — same
// contract as the SurfaceAccessChip: name the state and the way out."
//
// One code path for every optimistic UI write. Any component that
// mutates local state before an API write must route through this
// helper; the optimistic-write detector (backend/tests/test_optimistic_
// write_detector_2026_08_11.py) fails the build otherwise.
//
// Contract:
//   1. Apply optimistic patch (optional — pass null to opt out).
//   2. Fire API call.
//   3. On 2xx: keep the patch (or reconcile from `reconcileFrom(resp)`).
//   4. On non-2xx: run `rollback()`. Then render a persistent refusal
//      surface (toast + setRefusal() so the caller can paint a chip
//      that speaks state + way out).
//   5. On network error: same as non-2xx, but the message names the
//      network state so the contractor knows to retry.
//
// See memory/optimistic_ui_audit_2026-08-11.md §3 for the contract in
// prose and §1 for the census of sites this helper is retiring.
import { toast } from "sonner";

/**
 * @template TResp
 * @param {object} opts
 * @param {(() => void)|null} opts.applyOptimistic - Local state patch to run before the API call.
 * @param {() => void} opts.rollback - The inverse of applyOptimistic (mandatory when applyOptimistic is set).
 * @param {() => Promise<{data: TResp, status: number}>} opts.apiCall - The API call.
 * @param {((resp: {data: TResp, status: number}) => void)|null} [opts.reconcileFrom] - Post-2xx reconcile (usually update({...data})).
 * @param {(err: any) => string} [opts.refusalMessage] - Custom refusal message. Default extracts err.response.data.detail.
 * @param {((chip: {state: string, wayOut: string, testid: string} | null) => void)|null} [opts.setRefusal] - Callback to paint a persistent refusal chip.
 * @param {string} [opts.refusalTestid] - The testid the chip renders with.
 * @returns {Promise<{ok: boolean, data?: TResp, error?: any}>}
 */
export default async function writeThrough({
  applyOptimistic = null,
  rollback,
  apiCall,
  reconcileFrom = null,
  refusalMessage = null,
  setRefusal = null,
  refusalTestid = "write-refusal-chip",
}) {
  if (typeof apiCall !== "function") {
    throw new Error("writeThrough: apiCall is required");
  }
  if (applyOptimistic && typeof rollback !== "function") {
    throw new Error(
      "writeThrough: rollback is REQUIRED whenever applyOptimistic runs — the whole point of this helper is that a refused write cannot leave optimistic state behind"
    );
  }
  // Clear any prior refusal chip when we try again.
  if (typeof setRefusal === "function") setRefusal(null);
  if (typeof applyOptimistic === "function") applyOptimistic();
  try {
    const resp = await apiCall();
    if (typeof reconcileFrom === "function") reconcileFrom(resp);
    return { ok: true, data: resp?.data };
  } catch (err) {
    if (typeof rollback === "function") {
      try { rollback(); } catch (rollErr) {
        // Rollback failed — surface it loudly.
        console.error("writeThrough: rollback threw", rollErr);
      }
    }
    // Extract the server's refusal words. Never a canned string —
    // PURITY, per the audit doc §7.
    const status = err?.response?.status;
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      (status ? `Server refused (HTTP ${status})` : "Network error");
    const chip = {
      state: (typeof refusalMessage === "function"
        ? refusalMessage(err) : detail),
      wayOut: status === 423
        ? "This estimate is protected — nothing was saved. Rulings above the freeze happen out-of-band."
        : status === 409
        ? "The server is in a state that refuses this write. Check the banner above for the gate."
        : status && status >= 400 && status < 500
        ? "Fix the input and try again — the server explained why above."
        : "Retry when the network settles; nothing was saved.",
      testid: refusalTestid,
    };
    if (typeof setRefusal === "function") setRefusal(chip);
    // Toast is the ephemeral surface; the chip is the persistent one.
    toast.error(chip.state);
    return { ok: false, error: err };
  }
}
