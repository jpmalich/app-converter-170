// PLAIN-LANGUAGE GATE MESSAGES (Howard ruled 2026-08-06): no contractor
// knows what a 409 is. Every user-facing block message says WHAT is wrong
// and WHAT TO DO in plain words — the status code and gate name stay in
// the console for debugging, never on screen.
export async function gateBlockMessage(res, t) {
  let msg = t("err.pdf.generic");
  try {
    const err = await res.json();
    const d = err?.detail;
    // developers keep the code; the human gets the meaning
    console.warn("[pdf blocked]", res.status, d?.gate, d?.blocking || d);
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
        ? ` · ${t("err.gate.more", { n: items.length - 3 })}`
        : "";
      const intro = d.gate === "material_list"
        ? t("err.gate.materials")
        : d.gate === "order"
        ? t("err.gate.order")
        : t("err.gate.quote");
      msg = `${intro} ${names}${more}. ${t("err.gate.action")}`;
    } else if (d?.gate) {
      msg = `${t("err.gate.quote")} ${t("err.gate.action")}`;
    }
  } catch {
    /* non-JSON body — keep the plain generic message */
  }
  return msg;
}
