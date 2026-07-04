/* Dispatches /estimate/:id to the correct editor based on the
   estimate's `kind` field. ISS estimates use a separate, simpler page
   with one combined Price column; everything else uses the standard
   multi-tab EstimateEditor. */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import api from "@/lib/api";
import EstimateEditor from "./EstimateEditor";
import ISSEstimateEditor from "./ISSEstimateEditor";

export default function EstimateRouter() {
  const { id } = useParams();
  const [kind, setKind] = useState(null);

  useEffect(() => {
    let alive = true;
    api
      .get(`/estimates/${id}`)
      .then((res) => alive && setKind(res.data?.kind || "siding"))
      .catch(() => alive && setKind("siding"));
    return () => {
      alive = false;
    };
  }, [id]);

  if (kind === null) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-[#FAFAFA]">
        <Loader2 className="w-6 h-6 animate-spin text-[#C2410C]" />
      </main>
    );
  }
  if (kind === "iss") return <ISSEstimateEditor />;
  return <EstimateEditor />;
}
