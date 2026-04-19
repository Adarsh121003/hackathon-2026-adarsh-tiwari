import { cn } from "../../lib/cn.js";

export function Tabs({ tabs, active, onChange, className }) {
  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex items-center gap-1 p-1 bg-surface border border-border rounded-lg",
        className
      )}
    >
      {tabs.map((t) => {
        const isActive = t.value === active;
        return (
          <button
            key={t.value}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(t.value)}
            className={cn(
              "px-3 h-7 rounded-md text-xs font-medium transition-colors duration-150",
              isActive
                ? "bg-surface-2 text-text"
                : "text-text-muted hover:text-text"
            )}
          >
            {t.label}
            {t.count != null && (
              <span
                className={cn(
                  "ml-1.5 text-[10px]",
                  isActive ? "text-text-dim" : "text-text-muted"
                )}
              >
                {t.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
