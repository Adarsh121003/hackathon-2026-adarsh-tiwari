import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from "recharts";
import { Card, CardHeader, CardBody } from "../ui/Card.jsx";
import { EmptyState } from "../ui/EmptyState.jsx";
import { BarChart2 } from "lucide-react";
import { titleCase } from "../../lib/formatters.js";

const CATEGORY_COLOR = "var(--accent-alt)";

export function CategoryChart({ tickets, loading }) {
  const counts = {};
  (tickets ?? []).forEach((t) => {
    const c = t.category ?? "other";
    counts[c] = (counts[c] ?? 0) + 1;
  });
  const data = Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <Card className="h-full">
      <CardHeader title="By Category" subtitle="Tickets grouped by classification" />
      <CardBody>
        {loading ? (
          <div className="h-64 bg-surface-2 rounded animate-pulse" />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart2}
            title="No tickets processed"
            description="Classification breakdown will appear here."
          />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="name"
                  tickFormatter={(v) => titleCase(v)}
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={{ stroke: "var(--border)" }}
                  tickLine={false}
                  interval={0}
                  angle={-30}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                  axisLine={{ stroke: "var(--border)" }}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<BarTooltip />} cursor={{ fill: "var(--surface-2)" }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {data.map((_, i) => (
                    <Cell key={i} fill={CATEGORY_COLOR} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function BarTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0].payload;
  return (
    <div className="bg-surface border border-border rounded-md px-2.5 py-1.5 shadow-lg">
      <div className="text-xs text-text-dim">{titleCase(name)}</div>
      <div className="text-sm text-text font-medium tabular-nums">{value}</div>
    </div>
  );
}
