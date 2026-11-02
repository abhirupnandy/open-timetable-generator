import { useEffect, useRef, type ReactNode } from "react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  small?: boolean;
  children: ReactNode;
  footer?: ReactNode;
  onSubmit?: () => void;
}

/** Modal built on the native <dialog> element (Esc and backdrop handled by the browser). */
export function Dialog({ open, onClose, title, small, children, footer, onSubmit }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    } else if (!open && dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }
  }, [open]);

  return (
    <dialog ref={ref} className={`dialog ${small ? "dialog-small" : ""}`} onClose={onClose} onCancel={onClose}>
      {open && (
        <form
          method="dialog"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit?.();
          }}
        >
          {title && (
            <header className="dialog-head">
              <h2>{title}</h2>
              <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
                ✕
              </button>
            </header>
          )}
          <div className="dialog-body">{children}</div>
          {footer && <footer className="dialog-foot">{footer}</footer>}
        </form>
      )}
    </dialog>
  );
}
