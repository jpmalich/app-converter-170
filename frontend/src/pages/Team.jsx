import React, { useRef, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { useCompany } from "@/lib/company";
import { toast } from "sonner";
import { Copy, Building2, Upload, X, Image as ImageIcon } from "lucide-react";

export default function Team() {
  const { company, refresh, update } = useCompany();
  const [renameVal, setRenameVal] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef();

  if (!company) return <div className="p-10 text-center text-[#52525B]">Loading…</div>;

  const copyInvite = () => {
    try {
      navigator.clipboard.writeText(company.invite_code);
      toast.success("Invite code copied");
    } catch {
      toast.error("Clipboard blocked — select and copy manually");
    }
  };

  const uploadLogo = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data: up } = await api.post("/uploads", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await update({ logo_url: up.url });
      toast.success("Logo updated");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const removeLogo = async () => {
    setBusy(true);
    try {
      await update({ logo_url: "" });
      toast.success("Logo removed");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const saveName = async () => {
    if (!renameVal.trim()) return;
    setBusy(true);
    try {
      await update({ name: renameVal.trim() });
      toast.success("Company renamed");
      setRenameVal("");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const logoFullUrl = company.logo_url
    ? `${process.env.REACT_APP_BACKEND_URL}${company.logo_url}`
    : null;

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="team-page">
      <div className="text-xs uppercase tracking-[0.2em] text-[#A1A1AA] mb-1">Settings</div>
      <h1 className="font-heading text-4xl text-[#09090B] mb-8">Company &amp; Team</h1>

      {/* Company info + rename */}
      <div className="card p-6 mb-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-4">
          <Building2 className="w-5 h-5 text-[#F97316]" />
          <div className="section-tag">Company</div>
        </div>
        <div className="text-2xl font-heading text-[#09090B] mb-1" data-testid="company-name">
          {company.name}
        </div>
        <div className="text-xs text-[#A1A1AA] mb-4">
          Created {new Date(company.created_at).toLocaleDateString()}
        </div>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="Rename company…"
            value={renameVal}
            onChange={(e) => setRenameVal(e.target.value)}
            data-testid="rename-company-input"
          />
          <button
            className="btn-secondary"
            onClick={saveName}
            disabled={busy || !renameVal.trim()}
            data-testid="rename-company-btn"
          >
            Save
          </button>
        </div>
      </div>

      {/* Logo upload */}
      <div className="card p-6 mb-6 max-w-2xl" data-testid="logo-panel">
        <div className="flex items-center gap-3 mb-4">
          <ImageIcon className="w-5 h-5 text-[#F97316]" />
          <div className="section-tag">Company Logo</div>
        </div>
        <p className="text-sm text-[#52525B] mb-4">
          Used in the top navigation and on every customer quote. Square images work best (PNG, JPG, or WebP).
        </p>
        <div className="flex items-center gap-5">
          <div className="w-24 h-24 border-2 border-[#E4E4E7] bg-[#09090B] flex items-center justify-center overflow-hidden">
            {logoFullUrl ? (
              <img
                src={logoFullUrl}
                alt="Company logo"
                className="w-full h-full object-contain"
                data-testid="logo-preview"
              />
            ) : (
              <div className="font-heading text-[#F97316] text-4xl" data-testid="logo-placeholder">
                {(company.name || "W").charAt(0).toUpperCase()}
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              hidden
              onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0])}
              data-testid="logo-file-input"
            />
            <button
              className="btn-primary"
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              data-testid="upload-logo-btn"
            >
              <Upload className="w-4 h-4" /> {logoFullUrl ? "Replace" : "Upload"} Logo
            </button>
            {logoFullUrl && (
              <button
                className="btn-ghost text-[#EF4444] hover:text-[#EF4444]"
                onClick={removeLogo}
                disabled={busy}
                data-testid="remove-logo-btn"
              >
                <X className="w-4 h-4" /> Remove
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Invite teammates */}
      <div className="card p-6 max-w-2xl">
        <div className="section-tag mb-3">Invite a teammate</div>
        <p className="text-sm text-[#52525B] mb-4">
          Share this code so a teammate can join your company. They&apos;ll see the same estimates and price catalog as you.
        </p>
        <div className="flex items-stretch gap-2">
          <div
            className="flex-1 bg-[#09090B] text-[#F97316] font-mono-num text-2xl tracking-[0.3em] px-5 flex items-center"
            data-testid="invite-code-display"
          >
            {company.invite_code}
          </div>
          <button className="btn-primary" onClick={copyInvite} data-testid="copy-invite-btn">
            <Copy className="w-4 h-4" /> Copy
          </button>
        </div>
        <p className="text-xs text-[#A1A1AA] mt-3 uppercase tracking-wider">
          Teammate registers at <span className="font-mono-num text-[#52525B]">/login → Register → Join with code</span>
        </p>
      </div>
    </main>
  );
}
