import { cn } from "../../lib/cn.js";

const VARIANTS = {
  resolved: "bg-accent/10 text-accent border-accent/20",
  escalated: "bg-warn/10 text-warn border-warn/20",
  info_requested: "bg-info/10 text-info border-info/20",
  failed: "bg-danger/10 text-danger border-danger/20",
  neutral: "bg-surface-2 text-text-dim border-border",
  accent: "bg-accent-alt/10 text-accent-alt border-accent-alt/20",
};

const LABELS = {
  resolved: "Resolved",
  escalated: "Escalated",
  info_requested: "Info Requested",
  failed: "Failed",
};

export function Badge({ variant = "neutral", children, className, dot = false, ...rest }) {
  const cls = VARIANTS[variant] ?? VARIANTS.neutral;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border whitespace-nowrap",
        cls,
        className
      )}
      {...rest}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
      {children ?? LABELS[variant] ?? variant}
    </span>
  );
}

export function StatusBadge({ status, className }) {
  const variant =
    status === "resolved"
      ? "resolved"
      : status === "escalated"
      ? "escalated"
      : status === "info_requested"
      ? "info_requested"
      : status === "failed"
      ? "failed"
      : "neutral";
  return <Badge variant={variant} dot className={className} />;
}
