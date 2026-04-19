import { useMemo } from "react";
import { Activity, Radio, Zap } from "lucide-react";
import { useHealth, useMetrics } from "../../hooks/useMetrics.js";
import { useSentinelStore } from "../../stores/useSentinelStore.js";
import { cn } from "../../lib/cn.js";
import { formatLatency } from "../../lib/formatters.js";

const STATUS_STYLE = {
  open: { color: "bg-accent", label: "Live" },
  connecting: { color: "bg-warn animate-pulse", label: "Connecting" },
  error: { color: "bg-danger", label: "Reconnecting" },
  failed: { color: "bg-danger", label: "Offline" },
  idle: { color: "bg-text-muted", label: "Idle" },
};

export function Topbar() {
  const health = useHealth();
  const metrics = useMetrics();
  const streamStatus = useSentinelStore((s) => s.streamStatus);

  const provider = useMemo(() => {
    // Backend doesn't expose provider on /health — infer from env if mirrored, else label as LLM
    return import.meta.env.VITE_LLM_PROVIDER || "LLM";
  }, []);

  const backendUp = health.data?.status === "ok";
  const stream = STATUS_STYLE[streamStatus] ?? STATUS_STYLE.idle;

  return (
    <header className="h-14 border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-10">
      <div className="h-full px-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                backendUp ? "bg-accent" : "bg-danger"
              )}
              aria-hidden
            />
            <span className="text-xs text-text-dim">
              Backend {backendUp ? "online" : "offline"}
            </span>
          </div>
          <span className="w-px h-4 bg-border" />
          <div className="flex items-center gap-2 text-xs text-text-dim">
            <Radio className="w-3.5 h-3.5" />
            <span className={cn("w-1.5 h-1.5 rounded-full", stream.color)} />
            <span>SSE {stream.label}</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-text-dim">
            <Activity className="w-3.5 h-3.5" />
            <span>
              Avg latency:{" "}
              <span className="text-text tabular-nums">
                {formatLatency(metrics.data?.avg_latency_ms)}
              </span>
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface-2 border border-border">
            <Zap className="w-3 h-3 text-accent" />
            <span className="text-[10px] uppercase tracking-wider text-text-dim">
              {provider}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
