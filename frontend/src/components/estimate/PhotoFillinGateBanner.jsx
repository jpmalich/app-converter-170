// PHOTO FILL-IN GATE BANNER (Howard ruled 2026-08-02): the quote blocker
// shows at the TOP of the estimate page so the contractor sees it before
// he reaches for the quote button — not as a 409 after. Reads the SAME
// server gate (/gates → photo_fillin_unset) that hard-blocks email/PDF,
// so the banner can never disagree with the block (one set/unset copy,
// measure_staging.photo_fillins_unset).
import React, { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import api from "@/lib/api";

export default function PhotoFillinGateBanner({ est }) {
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
  return (
    <div
      className="mb-4 border border-[#F59E0B] bg-[#FEF3C7] px-4 py-3 flex items-start gap-3"
      data-testid="photo-fillin-gate-banner"
    >
      <AlertTriangle className="w-5 h-5 text-[#B45309] mt-0.5 shrink-0" />
      <div>
        <div className="text-[11px] font-bold uppercase tracking-wider text-[#92400E]">
          Photo fill-ins block this quote
        </div>
        <p className="text-sm text-[#92400E] mt-0.5">{item.label}</p>
        <p className="text-[10px] uppercase tracking-wider text-[#B45309] mt-1">
          Fill the boxes under Trade specs below — email, PDF and quote
          surfaces stay blocked until scope is set.
        </p>
      </div>
    </div>
  );
}
