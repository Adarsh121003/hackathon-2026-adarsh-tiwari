import { Link } from "react-router-dom";
import {
  Radio,
  Wrench,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Circle,
} from "lucide-react";
import { useSentinelStore } from "../../stores/useSentinelStore.js";
import { Card, CardHeader, CardBody } from "../ui/Card.jsx";
import { EmptyState } from "../ui/EmptyState.jsx";
import { cn } from "../../lib/cn.js";
import { formatDate, formatRelative } from "../../lib/formatters.js";
import { Button } from "../ui/Button.jsx";

const TYPE_STYLE = {
  tool_call: { icon: Wrench, color: "text-accent-alt", label: "Tool call" },
  triage: { icon: Circle, color: "text-info", label: "Triage" },
  resolve: { icon: CheckCircle2, color: "text-accent", label: "Resolve" },
  resolved: { icon: CheckCircle2, color: "text-accent", label: "Resolved" },
  escalate: { icon: ShieldAlert, color: "text-warn", label: "Escalate" },
  escalated: { icon: ShieldAlert, color: "text-warn", label: "Escalated" },
  error: { icon: AlertTriangle, color: "text-danger", label: "Error" },
  complete: { icon: CheckCircle2, color: "text-accent", label: "Complete" },
  start: { icon: Circle, color: "text-text-muted", label: "Start" },
};

function eventDescription(ev) {
  const p = ev.payload ?? {};
  if (p.tool_name) return p.tool_name + (p.success === false ? " — failed" : "");
  if (p.status) return `status → ${p.status}`;
  if (p.stage) return p.stage;
  if (p.message) return p.message;
  return ev.type;
}

export function LiveFeed({ compact = false }) {
  const events = useSentinelStore((s) => s.events);
  const clear = useSentinelStore((s) => s.clearEvents);

  const items = events.slice(0, compact ? 12 : 30);

  return (
    <Card>
      <CardHeader
        title="Live Feed"
        subtitle="Streaming agent activity via Server-Sent Events"
        right={
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs text-text-muted">
              <Radio className="w-3 h-3" />
              <span>{events.length}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={clear} disabled={!events.length}>
              Clear
            </Button>
          </div>
        }
      />
      <CardBody className="p-0">
        {items.length === 0 ? (
          <EmptyState
            icon={Radio}
            title="Waiting for live events"
            description="Trigger ingestion from the Tickets page to see the agent work in real time."
          />
        ) : (
          <ul className="divide-y divide-border">
            {items.map((ev, idx) => {
              const style = TYPE_STYLE[ev.type] ?? TYPE_STYLE.start;
              const Icon = style.icon;
              return (
                <li
                  key={`${ev.ticket_id}-${ev._receivedAt}-${idx}`}
                  className="px-5 py-3 flex items-center gap-3 hover:bg-surface-2 transition-colors duration-150 animate-slide-in"
                >
                  <Icon className={cn("w-3.5 h-3.5 shrink-0", style.color)} />
                  <div className="flex-1 min-w-0 flex items-baseline gap-3">
                    <span
                      className={cn(
                        "font-mono text-xs shrink-0",
                        style.color
                      )}
                    >
                      {style.label}
                    </span>
                    {ev.ticket_id && (
                      <Link
                        to={`/tickets/${ev.ticket_id}`}
                        className="font-mono text-xs text-text hover:underline shrink-0"
                      >
                        {ev.ticket_id}
                      </Link>
                    )}
                    <span className="text-xs text-text-dim truncate">
                      {eventDescription(ev)}
                    </span>
                  </div>
                  <time
                    className="text-[10px] text-text-muted tabular-nums font-mono shrink-0"
                    title={formatDate(ev.timestamp)}
                  >
                    {formatRelative(ev.timestamp)}
                  </time>
                </li>
              );
            })}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
