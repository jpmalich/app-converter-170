import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import BuildMismatchBanner from "@/components/BuildMismatchBanner";
import ServerWakingBanner from "@/components/ServerWakingBanner";
import { AuthProvider, useAuth } from "@/lib/auth";
import { BrandingProvider } from "@/lib/branding";
import { CompanyProvider } from "@/lib/company";
import { LangProvider } from "@/lib/i18n";
import Login from "@/pages/Login";
import HomePicker from "@/pages/HomePicker";
import IssPicker from "@/pages/IssPicker";
import ContractorPicker from "@/pages/ContractorPicker";
import Dashboard from "@/pages/Dashboard";
import EstimateRouter from "@/pages/EstimateRouter";
// SEND-131A — the photo-elevation pages are NO LONGER ROUTED (see the
// route block below). Their files stay; the imports go, so nothing in
// the contractor bundle points at them.
import BlueprintElevationSheet from "@/pages/BlueprintElevationSheet";
import FieldSheetPrint from "@/pages/FieldSheetPrint";
import SourceSheets from "@/pages/SourceSheets";
import Catalog from "@/pages/Catalog";
import Team from "@/pages/Team";
import BrandingAdmin from "@/pages/BrandingAdmin";
import LpFormulaPreview from "@/pages/LpFormulaPreview";
import AcceptPage from "@/pages/AcceptPage";
import MaterialListShare from "@/pages/MaterialListShare";
import AccuracyReportShare from "@/pages/AccuracyReportShare";
import Terms from "@/pages/Terms";
import Privacy from "@/pages/Privacy";
import Layout from "@/components/Layout";

function Protected({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null)
    return (
      <div className="flex items-center justify-center h-screen text-[var(--ink-2)]" data-testid="loading-state">
        Loading…
      </div>
    );
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}

function App() {
  return (
    <div className="App">
      <LangProvider>
        <AuthProvider>
          <BrandingProvider>
            <CompanyProvider>
              <BrowserRouter>
                <Toaster position="top-right" theme="light" />
                {/* STALE PAGE DETECTION (ruled 2026-08-09): a page older
                    than the deployed build says so — on every route. */}
                <BuildMismatchBanner />
                {/* COLD-START HONESTY (2026-08-24): while the pod boots,
                    the client retries and SAYS SO — never an empty state
                    posing as "no data". */}
                <ServerWakingBanner />
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/branding-admin" element={<BrandingAdmin />} />
                  <Route path="/lp-formula-preview" element={<LpFormulaPreview />} />
                  <Route path="/accept/:token" element={<AcceptPage />} />
                  <Route path="/m/:token" element={<MaterialListShare />} />
                  <Route path="/r/:token" element={<AccuracyReportShare />} />
                  <Route path="/terms" element={<Terms />} />
                  <Route path="/privacy" element={<Privacy />} />
                  <Route
                    element={
                      <Protected>
                        <Layout />
                      </Protected>
                    }
                  >
                    <Route path="/" element={<HomePicker />} />
                    <Route path="/picker/iss" element={<IssPicker />} />
                    <Route path="/picker/contractor" element={<ContractorPicker />} />
                    <Route path="/dashboard/siding" element={<Dashboard kind="siding" />} />
                    <Route path="/dashboard/lp_smart" element={<Dashboard kind="lp_smart" />} />
                    <Route path="/dashboard/windows" element={<Dashboard kind="windows" />} />
                    <Route path="/dashboard/iss" element={<Dashboard kind="iss" />} />
                    {/* Back-compat: old bookmarks pointing to /dashboard hit
                        the siding workspace (legacy default). */}
                    <Route path="/dashboard" element={<Navigate to="/dashboard/siding" replace />} />
                    {/* PHOTO-GENERATED ELEVATIONS ARE OUT OF THE
                        CONTRACTOR UI (Howard ruled 2026-08-26, SEND-131A):
                        the contractor works on the PHOTOS, not on renders
                        made from them. The two photo-elevation print
                        routes are unreachable from here; the page
                        components (`ElevationSheet`, `ElevationSheetsPrint`)
                        and the backend `/elevation-sheet/{which}` route
                        with all its pins stay in place, untouched.
                        BLUEPRINT elevation sheets are a different route
                        and are not affected. */}
                    <Route path="/estimate/:id/field-sheet" element={<FieldSheetPrint />} />
                    <Route path="/estimate/:id/blueprint-elevation/:which" element={<BlueprintElevationSheet />} />
                    {/* Source-view (generalized 2026-07-20): one surface for every
                        intake door — photos / blueprints / hover reference. The
                        original blueprint URL stays as an alias (accepted surface
                        never moves). Direct route + the Field Verify card link. */}
                    <Route path="/estimate/:id/source-view" element={<SourceSheets />} />
                    <Route path="/estimate/:id/source-sheets" element={<SourceSheets />} />
                    <Route path="/estimate/:id" element={<EstimateRouter />} />
                    <Route path="/catalog" element={<Catalog />} />
                    <Route path="/team" element={<Team />} />
                  </Route>
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </BrowserRouter>
            </CompanyProvider>
          </BrandingProvider>
        </AuthProvider>
      </LangProvider>
    </div>
  );
}

export default App;
