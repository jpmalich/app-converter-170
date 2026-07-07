import * as React from "react";
import * as AlertDialog from "@radix-ui/react-alert-dialog";

/**
 * One reusable confirmation dialog for the whole app, built on the Radix
 * AlertDialog primitive (focus trap, Esc, aria-modal, restore-focus for free) —
 * the replacement for `window.confirm`/`window.alert` throughout the estimator.
 *
 * Styled with the app's semantic tokens so it works in every theme and adopts
 * the Blueprint palette wherever the token bridge is active.
 *
 * Usage (trigger form):
 *   <ConfirmDialog
 *     trigger={<button>Delete</button>}
 *     title="Delete estimate?"
 *     description="This can't be undone."
 *     confirmLabel="Delete"
 *     destructive
 *     onConfirm={doDelete}
 *   />
 */
export default function ConfirmDialog({
  trigger,
  title,
  description,
  confirmLabel = "Continue",
  cancelLabel = "Cancel",
  onConfirm,
  destructive = false,
}) {
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>{trigger}</AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay
          className="fixed inset-0"
          style={{ zIndex: 70, background: "rgba(9,9,11,.55)" }}
        />
        <AlertDialog.Content
          className="fixed left-1/2 top-1/2 w-[92vw] max-w-md -translate-x-1/2 -translate-y-1/2 border p-5 shadow-xl outline-none"
          style={{
            zIndex: 71,
            background: "var(--surface)",
            borderColor: "var(--border-strong, var(--ink))",
            color: "var(--ink)",
          }}
        >
          <AlertDialog.Title className="text-base font-bold" style={{ letterSpacing: "-.01em" }}>
            {title}
          </AlertDialog.Title>
          {description ? (
            <AlertDialog.Description
              className="mt-2 text-sm"
              style={{ color: "var(--ink-2)", whiteSpace: "pre-line" }}
            >
              {description}
            </AlertDialog.Description>
          ) : null}
          <div className="mt-5 flex justify-end gap-2">
            <AlertDialog.Cancel
              className="px-4 py-2 text-xs font-bold uppercase tracking-wider border transition-colors"
              style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--ink)" }}
            >
              {cancelLabel}
            </AlertDialog.Cancel>
            <AlertDialog.Action
              onClick={onConfirm}
              className="px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors"
              style={
                destructive
                  ? { background: "var(--danger)", color: "#FFFFFF" }
                  : { background: "var(--brand)", color: "var(--on-brand)" }
              }
            >
              {confirmLabel}
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
