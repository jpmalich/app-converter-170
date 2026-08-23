// SEND-111 order item 4 — THE QR FIELD SHEET (printable crew page).
// One page for the house: what to tape per refusing face (the height
// cards), the refused rows, and QR links — the estimate itself (the
// tape nudge is right there on a phone) and the frozen material list
// share link if one exists. Instructions and links, never a quantity.
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Printer, Loader2 } from "lucide-react";
import api from "@/lib/api";

export default function FieldSheetPrint() {
  const { id } = useParams();
  const [sheet, setSheet] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api
      .get(`/estimates/${id}/pdf-overlay/field-sheet`, {
        params: { app_url: window.location.origin },
      })
      .then(({ data }) => setSheet(data))
      .catch((e) =>
        setErr(e?.response?.data?.detail || "Could not load the field sheet")
      );
  }, [id]);

  if (err)
    return (
      <div className="p-8 text-sm text-red-700" data-testid="field-sheet-error">
        {err}
      </div>
    );
  if (!sheet)
    return (
      <div className="p-8 flex items-center gap-2 text-sm" data-testid="field-sheet-loading">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading field sheet…
      </div>
    );

  return (
    <div className="max-w-3xl mx-auto p-6 bg-white text-[#1a1a1a]" data-testid="field-sheet">
      <div className="no-print flex justify-end mb-4">
        <button
          className="btn-secondary inline-flex items-center gap-2 border px-3 py-1.5 text-sm"
          onClick={() => window.print()}
          data-testid="field-sheet-print-btn"
        >
          <Printer className="w-4 h-4" /> Print
        </button>
      </div>

      <div className="border-b-2 border-black pb-3 mb-4">
        <div className="text-xl font-bold" data-testid="field-sheet-header">
          FIELD SHEET — {sheet.estimate_number || sheet.estimate_id}
        </div>
        <div className="text-sm mt-1">
          {sheet.customer_name}
          {sheet.address ? ` · ${sheet.address}` : ""}
        </div>
      </div>

      <div className="flex flex-wrap gap-8 mb-6" data-testid="field-sheet-qrs">
        {sheet.qr_estimate?.png && (
          <div className="text-center">
            <img src={sheet.qr_estimate.png} alt="Open estimate" className="w-36 h-36" />
            <div className="text-[11px] font-bold mt-1">OPEN THIS ESTIMATE</div>
            <div className="text-[10px] text-[#555]">tape entry lives here</div>
          </div>
        )}
        {sheet.qr_material_list?.png ? (
          <div className="text-center">
            <img src={sheet.qr_material_list.png} alt="Material list" className="w-36 h-36" />
            <div className="text-[11px] font-bold mt-1">MATERIAL LIST</div>
          </div>
        ) : (
          <div
            className="text-[11px] text-[#777] max-w-[180px] self-center"
            data-testid="field-sheet-no-ml"
          >
            {sheet.qr_material_list?.reason}
          </div>
        )}
      </div>

      {(sheet.cards || []).length > 0 && (
        <div className="mb-6">
          <div className="text-sm font-bold uppercase tracking-wide border-b border-black pb-1 mb-2">
            What to tape ({sheet.cards.length} face{sheet.cards.length === 1 ? "" : "s"})
          </div>
          {sheet.cards.map((c) => (
            <div key={c.face} className="border border-black p-3 mb-3" data-testid={`field-sheet-card-${c.face}`}>
              <div className="text-sm font-bold uppercase">
                {c.face} {c.page ? `(page ${c.page})` : ""}
              </div>
              <div className="text-[11px] text-[#555] mt-0.5">{c.refusal}</div>
              <div className="text-xs mt-2">{c.tape}</div>
              <div className="text-[11px] mt-1 font-semibold">{c.tape_points?.label}</div>
              {c.tape_entered ? (
                <div className="text-[11px] mt-1 text-emerald-800">
                  tape already entered: {c.tape_entered.value_ft} ft
                </div>
              ) : (
                <div className="mt-3 text-[11px]">
                  FIGURE: ______________ ft &nbsp;&nbsp; BY: ______________ &nbsp;&nbsp; DATE: __________
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {(sheet.refused_lines || []).length > 0 && (
        <div className="mb-6">
          <div className="text-sm font-bold uppercase tracking-wide border-b border-black pb-1 mb-2">
            Refused rows waiting on the tape
          </div>
          <ul className="text-xs space-y-1">
            {sheet.refused_lines.map((l, i) => (
              <li key={i} data-testid="field-sheet-refused-line">
                • {l.name} ({l.section}) — {l.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="text-[10px] text-[#777] border-t pt-2">{sheet.note}</div>
    </div>
  );
}
