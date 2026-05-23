import React, { useEffect, useState, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Upload, Shield, Copy, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function BrandingAdmin() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [branding, setBranding] = useState(null);
  const [signupCode, setSignupCode] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [supplierTagline, setSupplierTagline] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef();

  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const [b, s] = await Promise.all([
          axios.get(`${API}/branding`),
          axios.get(`${API}/admin/signup-code?token=${encodeURIComponent(token)}`),
        ]);
        setBranding(b.data);
        setSupplierName(b.data.supplier_name || "");
        setSupplierTagline(b.data.supplier_tagline || "");
        setSignupCode(s.data.signup_code);
      } catch (e) {
        setError(
          e.response?.status === 403
            ? "Invalid admin token. Check your URL ?token=... and try again."
            : "Failed to load. " + (e.response?.data?.detail || e.message)
        );
      }
    })();
  }, [token]);

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F4F5]">
        <div className="card p-8 max-w-md w-full">
          <Shield className="w-10 h-10 text-[#F97316] mb-4" />
          <h1 className="font-heading text-2xl text-[#09090B] mb-2">Branding Admin</h1>
          <p className="text-sm text-[#52525B]">
            This URL requires an admin token. Append <code className="font-mono">?token=YOUR_TOKEN</code> to the URL. The token lives in <code className="font-mono">backend/.env</code> as <code className="font-mono">SUPPLIER_ADMIN_TOKEN</code>.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F4F5]">
        <div className="card p-8 max-w-md w-full">
          <h1 className="font-heading text-2xl text-[#EF4444] mb-2">Access denied</h1>
          <p className="text-sm text-[#52525B]">{error}</p>
        </div>
      </div>
    );
  }

  if (!branding) {
    return <div className="p-10 text-center text-[#52525B]">Loading…</div>;
  }

  const uploadLogo = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await axios.post(`${API}/admin/upload-logo?token=${encodeURIComponent(token)}`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setBranding({ ...branding, supplier_logo_url: data.url });
      toast.success("Supplier logo uploaded");
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const saveBranding = async () => {
    setBusy(true);
    try {
      const { data } = await axios.put(
        `${API}/admin/branding?token=${encodeURIComponent(token)}`,
        { supplier_name: supplierName, supplier_tagline: supplierTagline }
      );
      setBranding(data);
      toast.success("Branding saved");
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const logoUrl = branding.supplier_logo_url
    ? `${process.env.REACT_APP_BACKEND_URL}${branding.supplier_logo_url}`
    : null;

  return (
    <div className="min-h-screen bg-[#F4F4F5]">
      <header className="bg-[#09090B] text-white">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-[#F97316]" />
            <div>
              <div className="font-heading text-lg">Branding Admin</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/50">
                Supplier-only · do not share this URL
              </div>
            </div>
          </div>
          <Link to="/" className="text-white/70 hover:text-white text-sm">
            <ArrowLeft className="w-4 h-4 inline" /> Back to app
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        {/* Signup code */}
        <div className="card p-6" data-testid="signup-code-card">
          <div className="section-tag mb-3">Contractor Access Code</div>
          <p className="text-sm text-[#52525B] mb-3">
            Give this code to any contractor you want to grant access. They&apos;ll enter it when creating a new account.
          </p>
          <div className="flex items-stretch gap-2">
            <div className="flex-1 bg-[#09090B] text-[#F97316] font-mono-num text-2xl tracking-[0.3em] px-5 flex items-center">
              {signupCode}
            </div>
            <button
              className="btn-primary"
              onClick={() => {
                navigator.clipboard.writeText(signupCode);
                toast.success("Copied");
              }}
            >
              <Copy className="w-4 h-4" /> Copy
            </button>
          </div>
          <p className="text-[10px] uppercase tracking-wider text-[#A1A1AA] mt-3">
            To rotate: change SIGNUP_CODE in <span className="font-mono-num">backend/.env</span> &amp; restart backend.
          </p>
        </div>

        {/* Supplier brand */}
        <div className="card p-6">
          <div className="section-tag mb-3">Supplier Name &amp; Tagline</div>
          <div className="space-y-4">
            <div>
              <label className="label">Supplier name</label>
              <input
                className="input"
                value={supplierName}
                onChange={(e) => setSupplierName(e.target.value)}
                data-testid="supplier-name-input"
              />
            </div>
            <div>
              <label className="label">Tagline (sales contact / phone)</label>
              <input
                className="input"
                value={supplierTagline}
                onChange={(e) => setSupplierTagline(e.target.value)}
                data-testid="supplier-tagline-input"
              />
            </div>
            <button className="btn-primary" onClick={saveBranding} disabled={busy} data-testid="save-branding-btn">
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </div>

        {/* Supplier logo */}
        <div className="card p-6">
          <div className="section-tag mb-3">Supplier Logo</div>
          <p className="text-sm text-[#52525B] mb-4">
            Appears on the Login page and (optionally) in the quote footer.
          </p>
          <div className="flex items-center gap-5">
            <div className="w-28 h-28 border-2 border-[#E4E4E7] bg-[#09090B] flex items-center justify-center overflow-hidden">
              {logoUrl ? (
                <img src={logoUrl} alt="Supplier logo" className="w-full h-full object-contain" data-testid="supplier-logo-preview" />
              ) : (
                <div className="font-heading text-[#F97316] text-5xl">
                  {(supplierName || "A").charAt(0)}
                </div>
              )}
            </div>
            <div>
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/svg+xml"
                hidden
                onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0])}
              />
              <button className="btn-primary" onClick={() => fileRef.current?.click()} disabled={busy} data-testid="upload-supplier-logo-btn">
                <Upload className="w-4 h-4" /> {logoUrl ? "Replace" : "Upload"} Logo
              </button>
              {logoUrl && (
                <button
                  className="btn-ghost text-[#EF4444] mt-2"
                  onClick={async () => {
                    setBusy(true);
                    try {
                      const { data } = await axios.put(
                        `${API}/admin/branding?token=${encodeURIComponent(token)}`,
                        { supplier_logo_url: "" }
                      );
                      setBranding(data);
                      toast.success("Logo removed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="text-xs text-[#A1A1AA] text-center pt-4">
          Bookmark this URL — it&apos;s how you&apos;ll come back to update branding.
        </div>
      </main>
    </div>
  );
}
