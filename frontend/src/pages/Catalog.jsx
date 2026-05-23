import React, { useEffect, useState, useCallback } from "react";
import api, { fmt, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Save, RotateCcw, Lock } from "lucide-react";

export default function Catalog() {
  const [sections, setSections] = useState([]);
  const [tierName, setTierName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/catalog");
      setSections(data.sections || []);
      setTierName(data.tier_name || "");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updateItem = (si, ii, key, val) => {
    setSections((arr) => {
      const next = JSON.parse(JSON.stringify(arr));
      next[si].items[ii][key] = Number(val) || 0;
      const item = next[si].items[ii];
      if (key === "mat") item.mat_overridden = Number(val) !== Number(item.tier_mat);
      if (key === "lab") item.lab_overridden = Number(val) !== Number(item.tier_lab);
      return next;
    });
  };

  const resetItem = (si, ii) => {
    setSections((arr) => {
      const next = JSON.parse(JSON.stringify(arr));
      const it = next[si].items[ii];
      it.mat = it.tier_mat;
      it.lab = it.tier_lab;
      it.mat_overridden = false;
      it.lab_overridden = false;
      return next;
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      // Build overrides dict: only items that differ from tier defaults
      const overrides = {};
      sections.forEach((s) => {
        s.items.forEach((it) => {
          const ov = {};
          if (it.mat_overridden) ov.mat = it.mat;
          if (it.lab_overridden) ov.lab = it.lab;
          if (Object.keys(ov).length) overrides[`${s.title}::${it.name}`] = ov;
        });
      });
      await api.put("/catalog", { overrides });
      toast.success("Catalog saved");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const resetAll = async () => {
    if (!window.confirm("Clear all your custom overrides and use the tier defaults?")) return;
    const { data } = await api.post("/catalog/reset");
    setSections(data.sections);
    toast.success("Reset to tier defaults");
  };

  if (loading) return <div className="p-10 text-center text-[#52525B]">Loading…</div>;

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="catalog-page">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-[#A1A1AA] mb-1">Settings</div>
          <h1 className="font-heading text-4xl text-[#09090B]">Price Catalog</h1>
          <div className="flex items-center gap-3 mt-3">
            <span className="inline-flex items-center gap-2 bg-[#09090B] text-[#F97316] px-3 py-1 text-xs font-bold uppercase tracking-wider" data-testid="tier-badge">
              <Lock className="w-3 h-3" /> Tier: {tierName}
            </span>
            <span className="text-xs text-[#52525B]">
              Material prices set by your supplier. Labor is yours to set. You can also override
              material per-item — overrides only apply to your company.
            </span>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary" onClick={resetAll} data-testid="reset-catalog-btn">
            <RotateCcw className="w-4 h-4" /> Clear Overrides
          </button>
          <button className="btn-primary" onClick={save} disabled={saving} data-testid="save-catalog-btn">
            <Save className="w-4 h-4" /> {saving ? "Saving…" : "Save Catalog"}
          </button>
        </div>
      </div>

      <div className="space-y-8">
        {sections.map((s) => (
          <div key={s.title} className="card">
            <div className="px-5 py-3 border-b border-[#E4E4E7]">
              <div className="section-tag">{s.title}</div>
            </div>
            <div className="hidden md:grid grid-cols-12 gap-3 px-5 py-2 text-[10px] uppercase tracking-[0.18em] text-[#A1A1AA] font-bold border-b border-[#E4E4E7]">
              <div className="col-span-5">Item</div>
              <div className="col-span-1">Unit</div>
              <div className="col-span-2 text-right">Material $</div>
              <div className="col-span-2 text-right">Labor $</div>
              <div className="col-span-2"></div>
            </div>
            {s.items.map((it) => {
              const ii = s.items.indexOf(it);
              const si = sections.indexOf(s);
              return (
                <div key={it.name} className="grid grid-cols-12 gap-3 px-5 py-2 border-b border-[#E4E4E7] items-center">
                  <div className="col-span-12 md:col-span-5 text-sm text-[#09090B]">{it.name}</div>
                  <div className="col-span-3 md:col-span-1 text-xs text-[#A1A1AA] uppercase tracking-wider">
                    {it.unit}
                  </div>
                  <div className="col-span-4 md:col-span-2">
                    <input
                      className={`input num h-10 ${it.mat_overridden ? "border-[#F97316] bg-orange-50" : ""}`}
                      type="number"
                      step="0.01"
                      value={it.mat}
                      onChange={(e) => updateItem(si, ii, "mat", e.target.value)}
                      title={it.mat_overridden ? `Tier default: $${it.tier_mat}` : ""}
                    />
                  </div>
                  <div className="col-span-4 md:col-span-2">
                    <input
                      className={`input num h-10 ${it.lab_overridden ? "border-[#F97316] bg-orange-50" : ""}`}
                      type="number"
                      step="0.01"
                      value={it.lab}
                      onChange={(e) => updateItem(si, ii, "lab", e.target.value)}
                      title={it.lab_overridden ? `Tier default: $${it.tier_lab}` : ""}
                    />
                  </div>
                  <div className="col-span-1 md:col-span-2 text-right">
                    {(it.mat_overridden || it.lab_overridden) && (
                      <button
                        className="btn-ghost text-[#F97316]"
                        onClick={() => resetItem(si, ii)}
                        title="Reset to tier defaults"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </main>
  );
}
