import { cn } from "../../lib/cn.js";

export function Card({ className, children, ...rest }) {
  return (
    <div
      className={cn(
        "bg-surface border border-border rounded-lg",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, right, className }) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 px-5 pt-4 pb-3 border-b border-border",
        className
      )}
    >
      <div>
        {title && (
          <h3 className="text-text font-medium text-sm tracking-tight">
            {title}
          </h3>
        )}
        {subtitle && (
          <p className="text-text-muted text-xs mt-0.5">{subtitle}</p>
        )}
      </div>
      {right}
    </div>
  );
}

export function CardBody({ className, children }) {
  return <div className={cn("px-5 py-4", className)}>{children}</div>;
}
