import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "./api";
import { useAuth } from "./auth";

const CompanyCtx = createContext(null);

export function CompanyProvider({ children }) {
  const { user } = useAuth();
  const [company, setCompany] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/company");
      setCompany(data);
    } catch {
      setCompany(null);
    }
  }, []);

  useEffect(() => {
    if (user && user.id) refresh();
    else setCompany(null);
  }, [user, refresh]);

  const update = useCallback(async (patch) => {
    const { data } = await api.put("/company", patch);
    setCompany(data);
    return data;
  }, []);

  return (
    <CompanyCtx.Provider value={{ company, refresh, update }}>{children}</CompanyCtx.Provider>
  );
}

export const useCompany = () => useContext(CompanyCtx);
