import React, { useState } from "react";
import { HelpCircle } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useLang } from "@/lib/i18n";
import { canonicalItemName } from "@/lib/catalogTranslations";
import { getItemDescription, hasItemDescription } from "@/lib/itemDescriptions";

/**
 * Iter 57aa — Per-row help icon.
 *
 * Renders a small "?" next to a catalog item name. On click, pops a
 * popover with the description from `itemDescriptions.js` in the user's
 * active language. Returns null when no description exists so empty
 * popovers don't appear.
 */
export default function ItemHelpButton({ itemName }) {
  const lang = useLang();
  const [open, setOpen] = useState(false);
  // Iter 57cc — Always resolve via the canonical (post-rename) name so
  // legacy estimates (e.g. lines saved as "RainDrop" before the
  // rename) still get the right popover entry under the new key
  // ("RainDrop House Wrap").
  const resolved = canonicalItemName(itemName);
  if (!hasItemDescription(resolved)) return null;
  const text = getItemDescription(resolved, lang);
  if (!text) return null;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setOpen((v) => !v);
          }}
          className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-[#71717A] hover:text-[#3B82F6] hover:bg-[#EFF6FF] focus:outline-none focus:ring-1 focus:ring-[#3B82F6] transition-colors"
          aria-label={`Help — ${itemName}`}
          data-testid={`item-help-${itemName}`}
        >
          <HelpCircle className="w-3.5 h-3.5" strokeWidth={2} />
        </button>
      </PopoverTrigger>
      <PopoverContent
        side="top"
        align="start"
        className="w-80 max-w-[90vw] p-3 text-xs leading-relaxed text-[#27272A] bg-white border border-[#3B82F6] shadow-lg"
        onClick={(e) => e.stopPropagation()}
        data-testid={`item-help-popover-${itemName}`}
      >
        <div className="font-bold text-[11px] uppercase tracking-wider text-[#3B82F6] mb-1.5">
          {resolved}
        </div>
        <div className="whitespace-pre-line">
          {/* Iter 78z++++ — Highlight the "Packaging:" / "Empaque:"
              label in the same blue as the item title so the carton
              info pops out from the spec paragraph. We split once,
              keep the rest of the sentence in normal copy. */}
          {(() => {
            const labels = ["Packaging:", "Empaque:"];
            for (const lbl of labels) {
              const idx = text.indexOf(lbl);
              if (idx !== -1) {
                return (
                  <>
                    {text.slice(0, idx)}
                    <span className="font-bold text-[#3B82F6]">{lbl}</span>
                    {text.slice(idx + lbl.length)}
                  </>
                );
              }
            }
            return text;
          })()}
        </div>
      </PopoverContent>
    </Popover>
  );
}
