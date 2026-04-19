import { cn } from "../../lib/cn.js";

export function Skeleton({ className }) {
  return (
    <div
      className={cn(
        "bg-surface-2 rounded animate-pulse",
        className
      )}
      aria-hidden
    />
  );
}

export function SkeletonRow({ cols = 6 }) {
  return (
    <div className="flex items-center gap-4 py-2">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className="h-3 flex-1" />
      ))}
    </div>
  );
}
