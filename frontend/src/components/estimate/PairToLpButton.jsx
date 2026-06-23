import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link2 } from "lucide-react";
import { toast } from "sonner";

/**
 * "Pair to LP" — Iter 74.
 *
 * One-click spawn of an LP-kind paired estimate from a siding draft.
 * Mirrors the siding↔windows pair pattern (Iter 41) but uses the
 * independent `paired_lp_estimate_id` field so a single siding draft can
 * fan out to BOTH a windows-pair AND an LP-pair without collision.
 *
 * UX:
 *   - Visible only on siding-kind estimates (vinyl + ascend). Hidden on
 *     LP/Windows/ISS kinds since they're not the source side.
 *   - If the source already has a paired LP, the button reads "Open LP
 *     Pair" instead of "Pair to LP" and just navigates.
 *   - On success, navigates to the new LP estimate immediately so the
 *     contractor can start adding LP lines.
 */
export default function PairToLpButton({ est }) {
  const nav = useNavigate();
  const [loading, setLoading] = useState(false);
  if (!est?.id) return null;
  // Only siding-kind estimates can fan out to LP (per Iter 73 split).
  // ISS, Windows, and LP-kind estimates skip the button.
  const kind = est.kind || "siding";
  if (kind !== "siding") return null;

  const alreadyPaired = !!est.paired_lp_estimate_id;
  const label = alreadyPaired ? "Open LP Pair" : "Pair to LP";

  const onClick = async () => {
    if (loading) return;
    if (alreadyPaired) {
      nav(`/estimate/${est.paired_lp_estimate_id}`);
      return;
    }
    setLoading(true);
    try {
      const API = process.env.REACT_APP_BACKEND_URL;
      const r = await fetch(`${API}/api/estimates/${est.id}/pair-lp`, {
        method: "POST",
        credentials: "include",
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        toast.error(err.detail || "Failed to pair LP estimate");
        return;
      }
      const data = await r.json();
      toast.success(`LP pair created${data.estimate_number ? ` · ${data.estimate_number}` : ""}`);
      nav(`/estimate/${data.id}`);
    } catch (e) {
      toast.error(e.message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-bold uppercase tracking-wider border border-[#E4E4E7] bg-white text-[#09090B] hover:border-[#F97316] hover:text-[#F97316] disabled:opacity-50"
      title={alreadyPaired ? "Open the LP estimate paired with this draft" : "Spawn an LP estimate carrying customer info + HOVER measurements"}
      data-testid="pair-to-lp-btn"
    >
      <Link2 className="w-3.5 h-3.5" />
      {loading ? "..." : label}
    </button>
  );
}
