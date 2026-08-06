// GATE-BLOCK MESSAGES (Howard, 2026-08-06): when a gate 409s a surface,
// the message must NAME the blockers — never a raw status code. The
// backend already ships {gate, blocking:[{code,label}]} in the 409 body;
// this helper turns it into a human line. Read-only display.
export async function gateBlockMessage(res, t) {
  let msg = `PDF render failed: ${res.status}`;
  try {
    const err = await res.json();
    const d = err?.detail;
    if (d?.gate && Array.isArray(d.blocking) && d.blocking.length) {
      const seen = new Set();
      const items = d.blocking.filter((b) => {
        const k = b.code || b.label;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      });
      const names = items.slice(0, 3).map((b) => b.label || b.code).join(" · ");
      const more = items.length > 3
        ? ` · ${t("ml.gate.more", { n: items.length - 3 })}`
        : "";
      msg = t("ml.gate.blocked", { gate: d.gate.toUpperCase() }) + ` ${names}${more}`;
    } else if (d?.gate) {
      msg = t("ml.gate.blocked", { gate: d.gate.toUpperCase() });
    }
  } catch {
    /* non-JSON body — keep the status fallback */
  }
  return msg;
}
