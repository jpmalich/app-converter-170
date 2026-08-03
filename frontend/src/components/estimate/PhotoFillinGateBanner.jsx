// PHOTO FILL-IN GATE BANNER (Howard ruled 2026-08-02): the quote blocker
// shows at the TOP of the estimate page so the contractor sees it before
// he reaches for the quote button — not as a 409 after. Reads the SAME
// server gate (/gates → photo_fillin_unset) that hard-blocks email/PDF,
// so the banner can never disagree with the block (one set/unset copy,
// measure_staging.photo_fillins_unset).
// SPANISH (Howard ruled 2026-08-03): a Spanish-speaking contractor must
// never hit a block he cannot read — the banner composes its text from
// the gate's structured `unset` list through the dictionary, both langs.
import React, { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";

// server unset labels (canonical EN) → dictionary keys
const BOX_KEYS = {
  "soffit ft²": "gate.pf.box.soffit",
  "drip edge LF": "gate.pf.box.dripEdge",
  "total trim ft²": "gate.pf.box.totalTrim",
  "frieze yes/no": "gate.pf.box.frieze",
};

export default function PhotoFillinGateBanner({ est }) {
  const t = useT();
  const [item, setItem] = useState(null);
  const src = est?.hover_measurements?._source;

  useEffect(() => {
    let alive = true;
    if (!est?.id || src !== "photo") {
      setItem(null);
      return undefined;
    }
    (async () => {
      try {
        const { data } = await api.get(`/estimates/${est.id}/gates`);
        const hit = (data?.quote?.blocking || []).find(
          (i) => i.code === "photo_fillin_unset"
        );
        if (alive) setItem(hit || null);
      } catch {
        if (alive) setItem(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [
    est?.id,
    src,
    est?.photo_soffit_sqft,
    est?.photo_drip_edge_lf,
    est?.photo_total_trim_sqft,
    est?.photo_frieze_present,
  ]);

  if (!item) return null;
  const unset = item.unset || [];
  const body = unset.length
    ? t("gate.pf.body", {
        count: unset.length,
        boxes: unset.map((b) => (BOX_KEYS[b] ? t(BOX_KEYS[b]) : b)).join(", "),
      })
    : item.label; // fallback: server label verbatim
  return (
    <div
      className="mb-4 border border-[#F59E0B] bg-[#FEF3C7] px-4 py-3 flex items-start gap-3"
      data-testid="photo-fillin-gate-banner"
    >
      <AlertTriangle className="w-5 h-5 text-[#B45309] mt-0.5 shrink-0" />
      <div>
        <div className="text-[11px] font-bold uppercase tracking-wider text-[#92400E]">
          {t("gate.pf.title")}
        </div>
        <p className="text-sm text-[#92400E] mt-0.5">{body}</p>
        <p className="text-[10px] uppercase tracking-wider text-[#B45309] mt-1">
          {t("gate.pf.hint")}
        </p>
      </div>
    </div>
  );
}
