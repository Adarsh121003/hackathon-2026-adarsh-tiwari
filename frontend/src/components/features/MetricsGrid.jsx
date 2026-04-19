import { Inbox, CheckCircle2, Activity, Gauge } from "lucide-react";
import { Card } from "../ui/Card.jsx";
import { Skeleton } from "../ui/Skeleton.jsx";
import { ConfidenceGauge } from "../ui/ConfidenceGauge.jsx";
import {
  formatNumber,
  formatPercent,
} from "../../lib/formatters.js";

function Kpi({ icon: Icon, label, value, sub, accent = "text-text-dim", loading }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[11px] uppercase tracking-wider text-text-muted">
          {label}
        </div>
        <div className="w-7 h-7 rounded-md bg-surface-2 border border-border flex items-center justify-center">
          <Icon className={`w-3.5 h-3.5 ${accent}`} />
        </div>
      </div>
      {loading ? (
        <Skeleton className="h-8 w-24" />
      ) : (
        <div className="text-2xl font-semibold text-text tabular-nums">
          {value}
        </div>
      )}
      {sub && !loading && (
        <div className="text-xs text-text-muted mt-1">{sub}</div>
      )}
    </Card>
  );
}

export function MetricsGrid({ metrics, loading }) {
  const total = metrics?.total_tickets ?? 0;
  const rate = metrics?.resolution_rate ?? 0;
  const resolved = metrics?.status_breakdown?.resolved ?? 0;
  const avgTools = metrics?.avg_tool_calls ?? 0;
  const avgConf = metrics?.avg_confidence ?? 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Kpi
        icon={Inbox}
        label="Total Tickets"
        value={total}
        sub={total ? `${resolved} resolved` : "No tickets yet"}
        accent="text-accent-alt"
        loading={loading}
      />
      <Kpi
        icon={CheckCircle2}
        label="Resolution Rate"
        value={formatPercent(rate, 1)}
        sub={total ? `${resolved}/${total} tickets` : "—"}
        accent="text-accent"
        loading={loading}
      />
      <Kpi
        icon={Activity}
        label="Avg Tool Calls"
        value={formatNumber(avgTools, 1)}
        sub="per ticket"
        accent="text-info"
        loading={loading}
      />
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="text-[11px] uppercase tracking-wider text-text-muted">
            Avg Confidence
          </div>
          <div className="w-7 h-7 rounded-md bg-surface-2 border border-border flex items-center justify-center">
            <Gauge className="w-3.5 h-3.5 text-warn" />
          </div>
        </div>
        {loading ? (
          <Skeleton className="h-10 w-24" />
        ) : (
          <div className="flex items-center gap-3">
            <ConfidenceGauge value={avgConf} size={68} label={false} />
            <div>
              <div className="text-2xl font-semibold text-text tabular-nums">
                {formatNumber(avgConf, 2)}
              </div>
              <div className="text-xs text-text-muted">calibrated</div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
