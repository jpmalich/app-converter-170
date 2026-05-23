import React, { createContext, useContext, useEffect, useState } from "react";
import api from "./api";

const BrandingCtx = createContext({});

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState({
    supplier_name: "Loading…",
    supplier_tagline: "",
    supplier_logo_url: null,
  });

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/branding");
        setBranding(data);
      } catch {
        // Fall back to defaults
      }
    })();
  }, []);

  return <BrandingCtx.Provider value={branding}>{children}</BrandingCtx.Provider>;
}

export const useBranding = () => useContext(BrandingCtx);
