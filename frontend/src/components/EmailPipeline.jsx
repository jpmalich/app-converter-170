// Compact email-tracking timeline shown on each Dashboard row.
// Shows 4 stages: Sent → Opened → Clicked → Accepted.
// A filled dot means that stage happened; gray means not yet.
// Hovering a filled dot shows the timestamp via title attr.
import React from "react";
import { Send, Eye, MousePointerClick, Check, AlertTriangle } from "lucide-react";

function Stage({ Icon, label, ts, color, textColor = "text-white", testId }) {
  const filled = !!ts;
  const tip = filled ? `${label}: ${new Date(ts).toLocaleString()}` : `${label}: not yet`;
  return (
    <span
      title={tip}
      className={`inline-flex items-center justify-center w-5 h-5 rounded-sm border ${
        filled
          ? `${color} border-transparent ${textColor}`
          : "bg-white border-[#E4E4E7] text-[#D4D4D8]"
      }`}
      data-testid={testId}
      aria-label={tip}
    >
      <Icon className="w-3 h-3" strokeWidth={filled ? 2.5 : 1.5} />
    </span>
  );
}

export default function EmailPipeline({ est }) {
  // Bounce/complaint take precedence — show a single red flag instead of the chain.
  if (est?.last_bounced_at || est?.last_complained_at) {
    const ts = est.last_bounced_at || est.last_complained_at;
    const label = est.last_bounced_at ? "Bounced" : "Marked as spam";
    return (
      <span
        title={`${label}: ${new Date(ts).toLocaleString()}`}
        className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-[#FEE2E2] text-[#B91C1C] border border-[#FCA5A5] rounded-sm"
        data-testid={`status-bounced-${est.id}`}
      >
        <AlertTriangle className="w-3 h-3" />
        {label}
      </span>
    );
  }
  // Drafts that haven't been sent: no chain to show
  if (!est?.last_sent_at) return null;
  return (
    <span className="inline-flex items-center gap-1" data-testid={`pipeline-${est.id}`}>
      <Stage Icon={Send} label="Sent" ts={est.last_sent_at} color="bg-[#A1A1AA]" textColor="text-[#09090B]" testId={`stage-sent-${est.id}`} />
      <Stage Icon={Eye} label="Opened" ts={est.last_opened_at} color="bg-[#3B82F6]" testId={`stage-opened-${est.id}`} />
      <Stage Icon={MousePointerClick} label="Clicked" ts={est.last_clicked_at} color="bg-[#F97316]" textColor="text-[#09090B]" testId={`stage-clicked-${est.id}`} />
      <Stage Icon={Check} label="Accepted" ts={est.accepted_at} color="bg-[#16A34A]" testId={`stage-accepted-${est.id}`} />
    </span>
  );
}
