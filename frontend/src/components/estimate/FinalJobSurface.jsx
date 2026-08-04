import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// FINAL-JOB SURFACE (Howard ruled 2026-07-29) — where the ORDER gate
// clears. QUOTE gate blocks customer surfaces (email / Accept / PDF /
// freeze / QR); ORDER gate blocks material release. Taped fields entered
// here SUPERSEDE derived values (14-vs-20 machinery, reversible).

const nums = (s) =>
  String(s || "")
    .split(/[,\s]+/)
    .map((x) => parseFloat(x))
    .filter((x) => isFinite(x) && x > 0);

function GateBadge({ blocked, gate }) {
  const t = useT();
  return (
    <span
      data-testid={`gate-badge-${gate}`}
      className={`px-2 py-0.5 text-xs font-bold tracking-wide ${
        blocked ? "bg-red-600/15 text-red-700" : "bg-emerald-600/15 text-emerald-700"
      }`}
    >
      {t(`gates.badge.${gate}`)} — {blocked ? t("gates.badge.blocked") : t("gates.badge.clear")}
    </span>
  );
}

function OrderFlagRow({ item, input, setInput, onAct }) {
  const code = item.code;
  const closed = item.status === "closed";
  const v = input[code] || {};
  const set = (k, val) => setInput((p) => ({ ...p, [code]: { ...(p[code] || {}), [k]: val } }));
  const values = () => {
    if (code === "batten_wall_heights") return { wall_heights_ft: nums(v.heights) };
    if (code === "corner_locators") {
      const out = {};
      if (v.osc) out.outside_corner_count = parseInt(v.osc, 10);
      if (v.isc) out.inside_corner_count = parseInt(v.isc, 10);
      const tall = nums(v.tall);
      if (tall.length) out.tall_corners_ft = tall;
      return out;
    }
    if (code === "opening_facade_attribution") {
      const out = {};
      for (const [k, key] of [["win", "window_count"], ["ent", "entry_door_count"],
        ["pat", "patio_door_count"], ["gar", "garage_door_count"]]) {
        if (v[k] !== undefined && v[k] !== "") out[key] = parseInt(v[k], 10);
      }
      return out;
    }
    return {};
  };
  return (
    <div className="border-t border-[var(--border)] py-2" data-testid={`order-flag-${code}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="text-xs leading-snug flex-1">
          <span className={`font-mono font-bold ${closed ? "line-through opacity-60" : ""}`}>
            {code}
          </span>
          {item.blocking && !closed && (
            <span className="ml-2 text-red-600 font-bold" data-testid={`order-flag-blocking-${code}`}>
              BLOCKS ORDER
            </span>
          )}
          <div className="opacity-80 mt-0.5">{item.label}</div>
          {closed && (
            <div className="text-emerald-700 mt-0.5" data-testid={`order-flag-closed-${code}`}>
              closed by {item.closed_by} — taped values supersede derived
            </div>
          )}
        </div>
        {closed ? (
          <Button size="sm" variant="outline" data-testid={`reopen-flag-${code}`}
            onClick={() => onAct(code, "reopen")}>
            Reopen
          </Button>
        ) : (
          <Button size="sm" data-testid={`close-flag-${code}`}
            onClick={() => onAct(code, "close", values())}>
            Close
          </Button>
        )}
      </div>
      {!closed && code === "batten_wall_heights" && (
        <Input className="mt-1 h-8 text-xs" placeholder="Taped wall heights ft, e.g. 9, 9, 18.5"
          data-testid="input-batten-wall-heights"
          value={v.heights || ""} onChange={(e) => set("heights", e.target.value)} />
      )}
      {!closed && code === "corner_locators" && (
        <div className="mt-1 flex gap-2">
          <Input className="h-8 text-xs" placeholder="OSC walked" data-testid="input-osc-count"
            value={v.osc || ""} onChange={(e) => set("osc", e.target.value)} />
          <Input className="h-8 text-xs" placeholder="ISC walked" data-testid="input-isc-count"
            value={v.isc || ""} onChange={(e) => set("isc", e.target.value)} />
          <Input className="h-8 text-xs" placeholder="Tall corners ft (>16')" data-testid="input-tall-corners"
            value={v.tall || ""} onChange={(e) => set("tall", e.target.value)} />
        </div>
      )}
      {!closed && code === "opening_facade_attribution" && (
        <div className="mt-1 flex gap-2">
          {[["win", "Windows"], ["ent", "Entry"], ["pat", "Patio"], ["gar", "Garage"]].map(([k, ph]) => (
            <Input key={k} className="h-8 text-xs" placeholder={`${ph} in-scope`}
              data-testid={`input-attr-${k}`}
              value={v[k] || ""} onChange={(e) => set(k, e.target.value)} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FinalJobSurface({ estId }) {
  const t2 = useT();
  const [gates, setGates] = useState(null);
  const [input, setInput] = useState({});
  const [releasing, setReleasing] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/estimates/${estId}/gates`);
      setGates(data);
    } catch {
      setGates(null);
    }
  }, [estId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const h = () => load();
    window.addEventListener("lp-flag-checklist-changed", h);
    return () => window.removeEventListener("lp-flag-checklist-changed", h);
  }, [load]);

  const act = async (code, action, values) => {
    try {
      await api.post(`/estimates/${estId}/flag-checklist`, { code, action, values });
      toast.success(action === "close" ? "Closed — taped values supersede derived" : "Reopened");
      window.dispatchEvent(new Event("lp-flag-checklist-changed"));
      await load();
    } catch (e) {
      toast.error(String(e?.response?.data?.detail || "Checklist update failed"));
    }
  };

  const release = async () => {
    setReleasing(true);
    try {
      const { data } = await api.post(`/estimates/${estId}/order-release`, {});
      toast.success("Materials released — order gate cleared");
      setGates((g) => ({ ...g, order_released: data.order_released }));
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(d?.message || "ORDER GATE blocked");
    } finally {
      setReleasing(false);
    }
  };

  if (!gates) return null;
  const q = gates.quote || {};
  const o = gates.order || {};
  return (
    <div className="mt-4 border border-[var(--border)] bg-[var(--surface-muted)] p-4"
      data-testid="final-job-surface">
      <div className="flex items-center justify-between mb-2">
        <div className="section-tag">{t2("gates.finalJob")}</div>
        <div className="flex gap-2">
          <GateBadge blocked={q.blocked} gate="quote" />
          <GateBadge blocked={o.blocked} gate="order" />
        </div>
      </div>

      {q.blocked && (
        <div className="mb-3" data-testid="quote-gate-blockers">
          <div className="text-xs font-bold text-red-700 mb-1">
            {t2("gates.quoteBlockers")}
          </div>
          {(q.blocking || []).map((i, idx) => (
            <div key={idx} className="text-xs opacity-90 py-0.5"
              data-testid={`quote-blocker-${i.code}`}>
              <span className="font-mono font-bold">{i.code}</span> — {i.label}
            </div>
          ))}
        </div>
      )}
      {(q.items || []).filter((i) => !i.blocking).map((i, idx) => (
        <div key={`qi-${idx}`} className="text-[11px] opacity-70 py-0.5"
          data-testid={`quote-info-${i.code}`}>
          {i.label}
        </div>
      ))}

      {(o.items || []).length > 0 && (
        <div data-testid="order-gate-items">
          <div className="text-xs font-bold mb-1">
            {t2("gates.orderItems")}
          </div>
          {o.items.map((item, idx) => (
            <OrderFlagRow key={`${item.code}-${idx}`} item={item}
              input={input} setInput={setInput} onAct={act} />
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between">
        {gates.order_released ? (
          <div className="text-xs text-emerald-700" data-testid="order-released-stamp">
            {t2("gates.releasedBy", { by: gates.order_released.by, at: gates.order_released.at })}
          </div>
        ) : (
          <Button size="sm" disabled={o.blocked || releasing}
            data-testid="release-materials-btn" onClick={release}>
            {o.blocked ? t2("gates.orderBlocked") : releasing ? t2("gates.releasing") : t2("gates.releaseMaterials")}
          </Button>
        )}
      </div>
    </div>
  );
}
