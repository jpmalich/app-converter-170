import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// COLD-START RESILIENCE (Howard's bug report 2026-08-24): the preview pod
// restarts between sessions; while it boots, EVERY /api route answers 404
// from the ingress. The panels used to read that burst as "no data" and
// print "NEEDS A COMPLETED BLUEPRINT READ" over reads that were DONE — a
// 404 wearing "no run"'s clothes (the SEND-115 lesson, client side).
// RULE: a failure only retries when the /api/version probe confirms the
// WHOLE TREE is down (then the original request never reached the app, so
// a retry can never double-fire a write). A real 404 from a live backend
// passes through untouched.
const RETRY_DELAYS_MS = [2000, 4000, 8000, 12000, 15000];
let _wakingBroadcast = false;

function _broadcast(down) {
  if (down === _wakingBroadcast) return;
  _wakingBroadcast = down;
  window.dispatchEvent(new CustomEvent(down ? "pq:backend-down" : "pq:backend-up"));
}

async function _backendIsDown() {
  try {
    // bare axios — never route the probe through this interceptor
    const r = await axios.get(`${API}/version`, { timeout: 6000, withCredentials: true });
    return !(r && r.status === 200);
  } catch {
    return true;
  }
}

const _sleep = (ms) => new Promise((res) => setTimeout(res, ms));

api.interceptors.response.use(
  (resp) => {
    _broadcast(false);
    return resp;
  },
  async (error) => {
    const cfg = error?.config || {};
    const status = error?.response?.status;
    const transportish = !error?.response || [404, 502, 503, 504].includes(status);
    if (!transportish || cfg.__noRetry) throw error;
    let attempt = cfg.__wakeAttempt || 0;
    while (attempt < RETRY_DELAYS_MS.length) {
      if (!(await _backendIsDown())) {
        if (attempt === 0) throw error; // backend is up — the answer is real
        break; // recovered mid-wait — replay the request
      }
      _broadcast(true);
      await _sleep(RETRY_DELAYS_MS[attempt]);
      attempt += 1;
    }
    _broadcast(false);
    if (attempt >= RETRY_DELAYS_MS.length) throw error;
    return api.request({ ...cfg, __wakeAttempt: attempt });
  }
);

export default api;

export function formatApiError(detail) {
  if (detail == null) return "That didn't go through — check your connection and try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const fmt = (n) =>
  Number(n || 0).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
