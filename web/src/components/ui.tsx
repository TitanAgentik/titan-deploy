import type { CSSProperties, ReactNode } from "react";
import clsx from "clsx";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {actions ? <div style={{ display: "flex", gap: 8 }}>{actions}</div> : null}
    </div>
  );
}

export function Card({
  title,
  action,
  children,
  className,
  style,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div className={clsx("card", className)} style={style}>
      {title ? (
        <div className="card-title">
          <span>{title}</span>
          {action}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function Metric({
  label,
  value,
  delta,
  deltaDir,
}: {
  label: string;
  value: string;
  delta?: string;
  deltaDir?: "up" | "down";
}) {
  return (
    <div className="card metric">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {delta ? <span className={clsx("delta", deltaDir)}>{delta}</span> : null}
    </div>
  );
}

export function Tag({
  kind,
  children,
}: {
  kind: "healthy" | "bleeding" | "watch" | "info" | "neutral";
  children: ReactNode;
}) {
  return <span className={clsx("tag", kind)}>{children}</span>;
}

export function Btn({
  children,
  variant = "default",
  onClick,
  disabled,
  type = "button",
}: {
  children: ReactNode;
  variant?: "default" | "primary" | "danger" | "ghost";
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      className={clsx("btn", variant !== "default" && variant)}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
