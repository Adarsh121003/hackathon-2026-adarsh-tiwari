import { useState } from "react";
import { CheckCircle2, AlertTriangle, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "../../lib/cn.js";
import { formatDate, formatLatency } from "../../lib/formatters.js";
import { EmptyState } from "../ui/EmptyState.jsx";
import { Wrench } from "lucide-react";

function ToolCallItem({ call }) {
  const [open, setOpen] = useState(false);
  const ok = !!call.success;
  return (
    <div className="relative">
      <div
        className={cn(
          "absolute left-[11px] top-6 bottom-0 w-px",
          "bg-border"
        )}
        aria-hidden
      />
      <div className="relative flex items-start gap-3 py-3">
        <div
          className={cn(
            "w-6 h-6 rounded-full border flex items-center justify-center shrink-0 z-10 bg-surface",
            ok ? "border-accent/40" : "border-danger/40"
          )}
        >
          {ok ? (
            <CheckCircle2 className="w-3 h-3 text-accent" />
          ) : (
            <AlertTriangle className="w-3 h-3 text-danger" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <button
            onClick={() => setOpen((v) => !v)}
            className="w-full flex items-center justify-between gap-2 group"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-mono text-xs text-text-muted tabular-nums">
                #{call.sequence}
              </span>
              <span className="font-mono text-sm text-text truncate">
                {call.tool_name}
              </span>
              {call.attempt > 1 && (
                <span className="text-[10px] text-warn">
                  retry {call.attempt}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-[11px] text-text-muted font-mono tabular-nums">
                {formatLatency(call.latency_ms)}
              </span>
              {open ? (
                <ChevronDown className="w-3.5 h-3.5 text-text-muted group-hover:text-text" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-text-muted group-hover:text-text" />
              )}
            </div>
          </button>
          {open && (
            <div className="mt-2 space-y-2">
              <KeyValue label="Arguments" value={call.arguments} />
              {call.result != null && (
                <KeyValue label="Result" value={call.result} />
              )}
              {call.error && (
                <div className="bg-danger/5 border border-danger/20 rounded-md p-2">
                  <div className="text-[10px] uppercase tracking-wider text-danger/80 mb-0.5">
                    Error
                  </div>
                  <div className="text-xs text-danger font-mono break-all">
                    {call.error}
                  </div>
                </div>
              )}
              <div className="text-[10px] text-text-muted font-mono">
                {formatDate(call.timestamp)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KeyValue({ label, value }) {
  return (
    <div className="bg-surface-2 border border-border rounded-md p-2">
      <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">
        {label}
      </div>
      <pre className="text-xs text-text-dim font-mono whitespace-pre-wrap break-all max-h-48 overflow-auto leading-relaxed">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

export function ToolCallTimeline({ calls }) {
  if (!calls || calls.length === 0) {
    return (
      <EmptyState
        icon={Wrench}
        title="No tool calls"
        description="The agent resolved without executing any tools."
      />
    );
  }
  return (
    <div className="px-5 py-2">
      {calls.map((c) => (
        <ToolCallItem key={`${c.sequence}-${c.timestamp}`} call={c} />
      ))}
    </div>
  );
}
