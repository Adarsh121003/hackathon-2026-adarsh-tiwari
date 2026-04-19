import { cn } from "../../lib/cn.js";

export function EmptyState({ icon: Icon, title, description, action, className }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center py-10 px-6",
        className
      )}
    >
      {Icon && (
        <div className="w-10 h-10 rounded-lg bg-surface-2 border border-border flex items-center justify-center mb-3">
          <Icon className="w-5 h-5 text-text-muted" aria-hidden />
        </div>
      )}
      {title && (
        <h4 className="text-text text-sm font-medium">{title}</h4>
      )}
      {description && (
        <p className="text-text-muted text-xs mt-1 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
