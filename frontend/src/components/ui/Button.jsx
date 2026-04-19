import { cn } from "../../lib/cn.js";

const VARIANTS = {
  primary:
    "bg-accent text-black hover:bg-accent/90 disabled:bg-accent/50 disabled:cursor-not-allowed",
  secondary:
    "bg-surface-2 text-text border border-border hover:bg-border disabled:opacity-60",
  ghost:
    "bg-transparent text-text-dim hover:bg-surface-2 hover:text-text disabled:opacity-50",
  danger:
    "bg-danger/90 text-white hover:bg-danger disabled:bg-danger/40",
};

const SIZES = {
  sm: "h-7 px-2.5 text-xs",
  md: "h-8 px-3 text-sm",
  lg: "h-10 px-4 text-sm",
};

export function Button({
  variant = "secondary",
  size = "md",
  className,
  children,
  icon: Icon,
  ...rest
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors duration-150 disabled:cursor-not-allowed",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...rest}
    >
      {Icon && <Icon className="w-3.5 h-3.5" aria-hidden />}
      {children}
    </button>
  );
}
