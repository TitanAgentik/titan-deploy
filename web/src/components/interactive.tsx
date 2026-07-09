import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { X, ChevronDown, Check } from "lucide-react";
import clsx from "clsx";
import { Btn } from "./ui";

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  width = 560,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="modal-root" role="presentation" onMouseDown={onClose}>
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        style={{ maxWidth: width }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <h3>{title}</h3>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer ? <div className="modal-foot">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="drawer-root" role="presentation" onMouseDown={onClose}>
      <aside
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <h3>{title}</h3>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <div className="drawer-body">{children}</div>
        {footer ? <div className="modal-foot">{footer}</div> : null}
      </aside>
    </div>,
    document.body,
  );
}

export type MenuItem = {
  label: string;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
  hint?: string;
};

export function ActionMenu({
  label = "Actions",
  items,
  variant = "default",
}: {
  label?: ReactNode;
  items: MenuItem[];
  variant?: "default" | "primary" | "danger" | "ghost";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <div className="action-menu" ref={ref}>
      <Btn
        variant={variant}
        onClick={() => setOpen((v) => !v)}
      >
        {label}
        <ChevronDown size={14} />
      </Btn>
      {open ? (
        <div className="action-menu-pop">
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              className={clsx("action-menu-item", item.danger && "danger")}
              disabled={item.disabled}
              onClick={() => {
                setOpen(false);
                item.onClick();
              }}
            >
              <span>{item.label}</span>
              {item.hint ? <span className="hint">{item.hint}</span> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: { id: string; message: string; kind?: "ok" | "warn" | "danger" }[];
  onDismiss: (id: string) => void;
}) {
  if (!toasts.length) return null;
  return createPortal(
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className={clsx("toast", t.kind ?? "ok")}>
          <Check size={14} />
          <span>{t.message}</span>
          <button type="button" className="icon-btn" onClick={() => onDismiss(t.id)}>
            <X size={12} />
          </button>
        </div>
      ))}
    </div>,
    document.body,
  );
}

export function useToasts() {
  const [toasts, setToasts] = useState<
    { id: string; message: string; kind?: "ok" | "warn" | "danger" }[]
  >([]);
  const push = (message: string, kind?: "ok" | "warn" | "danger") => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((t) => [...t, { id, message, kind }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  };
  const dismiss = (id: string) => setToasts((t) => t.filter((x) => x.id !== id));
  return { toasts, push, dismiss };
}

export function DetailGrid({
  rows,
}: {
  rows: { label: string; value: ReactNode }[];
}) {
  return (
    <dl className="detail-grid">
      {rows.map((r) => (
        <div key={r.label} className="detail-row">
          <dt>{r.label}</dt>
          <dd>{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ClickableMetric({
  label,
  value,
  delta,
  deltaDir,
  onClick,
  style,
}: {
  label: string;
  value: string;
  delta?: string;
  deltaDir?: "up" | "down";
  onClick?: () => void;
  style?: CSSProperties;
}) {
  return (
    <button
      type="button"
      className={clsx("card metric metric-click")}
      style={style}
      onClick={onClick}
    >
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {delta ? <span className={clsx("delta", deltaDir)}>{delta}</span> : null}
      <span className="metric-hint">Click for details</span>
    </button>
  );
}

export function ConfirmBar({
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger,
  onConfirm,
  onCancel,
}: {
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="confirm-bar">
      <span>{message}</span>
      <div style={{ display: "flex", gap: 8 }}>
        <Btn variant="ghost" onClick={onCancel}>
          {cancelLabel}
        </Btn>
        <Btn variant={danger ? "danger" : "primary"} onClick={onConfirm}>
          {confirmLabel}
        </Btn>
      </div>
    </div>
  );
}
