import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardHeader, CardBody } from "../ui/Card.jsx";
import { EmptyState } from "../ui/EmptyState.jsx";
import { PieChart as PieIcon } from "lucide-react";
import { titleCase } from "../../lib/formatters.js";

const COLORS = {
  resolved: "var(--accent)",
  escalated: "var(--warn)",
  info_requested: "var(--info)",
  failed: "var(--danger)",
};

export function StatusDonut({ metrics, loading }) {
  const breakdown = metrics?.status_breakdown ?? {};
  const data = Object.entries(breakdown)
    .map(([name, value]) => ({ name, value }))
    .filter((d) => d.value > 0);

  const total = data.reduce((a, b) => a + b.value, 0);

  return (
    <Card className="h-full">
      <CardHeader title="Status Breakdown" subtitle="Resolution outcomes across tickets" />
      <CardBody>
        {loading ? (
          <div className="h-64 bg-surface-2 rounded animate-pulse" />
        ) : data.length === 0 ? (
          <EmptyState
            icon={PieIcon}
            title="No data yet"
            description="Trigger ingestion to populate metrics."
          />
        ) : (
          <div className="h-64 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={58}
                  outerRadius={88}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="var(--surface)"
                  strokeWidth={2}
                >
                  {data.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={COLORS[entry.name] ?? "var(--text-muted)"}
                    />
                  ))}
                </Pie>
                <Tooltip content={<DonutTooltip total={total} />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center">
                <div className="text-2xl font-semibold text-text tabular-nums">
                  {total}
                </div>
                <div className="text-[10px] uppercase tracking-wider text-text-muted">
                  tickets
                </div>
              </div>
            </div>
          </div>
        )}
        {data.length > 0 && (
          <div className="mt-4 grid grid-cols-2 gap-y-2 gap-x-3">
            {data.map((d) => (
              <div key={d.name} className="flex items-center gap-2 text-xs">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: COLORS[d.name] ?? "var(--text-muted)" }}
                />
                <span className="text-text-dim flex-1">
                  {titleCase(d.name)}
                </span>
                <span className="text-text font-medium tabular-nums">
                  {d.value}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function DonutTooltip({ active, payload, total }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0];
  const pct = total ? ((value / total) * 100).toFixed(1) : "0";
  return (
    <div className="bg-surface border border-border rounded-md px-2.5 py-1.5 shadow-lg">
      <div className="text-xs text-text-dim">{titleCase(name)}</div>
      <div className="text-sm text-text font-medium tabular-nums">
        {value} <span className="text-text-muted">({pct}%)</span>
      </div>
    </div>
  );
}
