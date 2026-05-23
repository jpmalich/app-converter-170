import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/lib/auth";
import { BrandingProvider } from "@/lib/branding";
import { CompanyProvider } from "@/lib/company";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import EstimateEditor from "@/pages/EstimateEditor";
import Catalog from "@/pages/Catalog";
import Team from "@/pages/Team";
import BrandingAdmin from "@/pages/BrandingAdmin";
import Layout from "@/components/Layout";

function Protected({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null)
    return (
      <div className="flex items-center justify-center h-screen text-[#52525B]" data-testid="loading-state">
        Loading…
      </div>
    );
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrandingProvider>
          <CompanyProvider>
            <BrowserRouter>
              <Toaster position="top-right" theme="light" />
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/branding-admin" element={<BrandingAdmin />} />
                <Route
                  element={
                    <Protected>
                      <Layout />
                    </Protected>
                  }
                >
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/estimate/:id" element={<EstimateEditor />} />
                  <Route path="/catalog" element={<Catalog />} />
                  <Route path="/team" element={<Team />} />
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </CompanyProvider>
        </BrandingProvider>
      </AuthProvider>
    </div>
  );
}

export default App;
