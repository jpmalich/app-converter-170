import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";

/**
 * Reusable modal on the Radix Dialog primitive — the replacement for the
 * app's hand-rolled `fixed inset-0` overlays. Gives focus trap, Escape,
 * outside-click dismiss, aria-modal, and focus restore for free.
 *
 * Controlled: pass `open` + `onClose`. A `title` is REQUIRED (Radix needs a
 * Dialog.Title for screen readers); it renders visually hidden so callers keep
 * their own visible header markup in `children`.
 *
 * `contentClassName` / `contentStyle` style the dialog box itself — default is
 * a centered card; full-screen modals pass their own.
 */
export default function Modal({
  open,
  onClose,
  title,
  children,
  testid,
  contentClassName,
  contentStyle,
  overlayStyle,
}) {
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose?.();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay
          className="fixed inset-0"
          style={{ zIndex: 70, background: "rgba(9,9,11,.6)", ...overlayStyle }}
        />
        <Dialog.Content
          data-testid={testid}
          className={
            contentClassName ||
            "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[92vw] max-w-md outline-none"
          }
          style={{ zIndex: 71, ...contentStyle }}
        >
          <Dialog.Title className="sr-only">{title}</Dialog.Title>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
