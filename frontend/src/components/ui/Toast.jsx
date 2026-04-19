import { X, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "../../lib/cn.js";

const ICON = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
};

const COLOR = {
  success: "text-accent",
  error: "text-danger",
  info: "text-accent-alt",
};

export function Toast({ toast, onDismiss }) {
  const Icon = ICON[toast.type] ?? Info;
  return (
    <div
      role="status"
      className="fixed top-4 right-4 z-50 animate-slide-in"
    >
      <div className="flex items-start gap-3 bg-surface border border-border rounded-lg shadow-xl px-4 py-3 min-w-[280px] max-w-sm">
        <Icon className={cn("w-4 h-4 mt-0.5 shrink-0", COLOR[toast.type])} />
        <div className="flex-1 min-w-0">
          <div className="text-sm text-text font-medium">{toast.title}</div>
          {toast.description && (
            <div className="text-xs text-text-muted mt-0.5">
              {toast.description}
            </div>
          )}
        </div>
        <button
          onClick={onDismiss}
          className="text-text-muted hover:text-text transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
