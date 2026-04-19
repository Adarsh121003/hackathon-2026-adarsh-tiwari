import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Clock,
  Wrench,
  Brain,
  FileJson,
  MessageSquare,
  Flag,
  AlertCircle,
} from "lucide-react";
import { useTicket } from "../hooks/useTickets.js";
import { Card, CardHeader, CardBody } from "../components/ui/Card.jsx";
import { StatusBadge, Badge } from "../components/ui/Badge.jsx";
import { ConfidenceGauge } from "../components/ui/ConfidenceGauge.jsx";
import { Tabs } from "../components/ui/Tabs.jsx";
import { Skeleton } from "../components/ui/Skeleton.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { Button } from "../components/ui/Button.jsx";
import { ToolCallTimeline } from "../components/features/ToolCallTimeline.jsx";
import { ReasoningTrace } from "../components/features/ReasoningTrace.jsx";
import {
  formatDate,
  formatLatency,
  titleCase,
} from "../lib/formatters.js";

const TABS = [
  { value: "summary", label: "Summary" },
  { value: "reasoning", label: "Reasoning" },
  { value: "tools", label: "Tool Calls" },
  { value: "raw", label: "Raw JSON" },
];

export function TicketDetail() {
  const { id } = useParams();
  const { data, isLoading, error, refetch } = useTicket(id);
  const [tab, setTab] = useState("summary");

  if (isLoading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-36" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <EmptyState
          icon={AlertCircle}
          title="Could not load ticket"
          description={error.message}
          action={
            <Button variant="secondary" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      </Card>
    );
  }

  if (!data) return null;

  const tabsWithCounts = TABS.map((t) => ({
    ...t,
    count:
      t.value === "tools"
        ? data.tool_calls?.length ?? 0
        : t.value === "reasoning"
        ? data.reasoning_trace?.length ?? 0
        : undefined,
  }));

  return (
    <div className="space-y-5 animate-fade-in">
      <Link
        to="/tickets"
        className="inline-flex items-center gap-1 text-xs text-text-muted hover:text-text transition-colors"
      >
        <ArrowLeft className="w-3 h-3" />
        All tickets
      </Link>

      <Card>
        <div className="p-5 flex items-start justify-between gap-6 flex-wrap">
          <div className="flex items-center gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-semibold text-text font-mono">
                  {data.ticket_id}
                </h1>
                <StatusBadge status={data.status} />
              </div>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <Badge variant="accent">{titleCase(data.category)}</Badge>
                <Badge variant="neutral">{titleCase(data.urgency)} urgency</Badge>
                {(data.flags ?? []).map((f, i) => (
                  <Badge key={i} variant="neutral" className="text-text-dim">
                    <Flag className="w-2.5 h-2.5" />
                    {f.slice(0, 40)}
                    {f.length > 40 ? "…" : ""}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
          <ConfidenceGauge value={data.confidence} size={110} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border border-t border-border">
          <MetaCell label="Tool Calls" value={data.tool_calls?.length ?? 0} />
          <MetaCell
            label="Latency"
            value={formatLatency(data.total_latency_ms)}
            mono
          />
          <MetaCell label="Started" value={formatDate(data.started_at)} mono small />
          <MetaCell label="Completed" value={formatDate(data.completed_at)} mono small />
        </div>
      </Card>

      <Tabs tabs={tabsWithCounts} active={tab} onChange={setTab} />

      {tab === "summary" && <SummaryPanel data={data} />}
      {tab === "reasoning" && (
        <Card>
          <CardHeader title="Reasoning Trace" subtitle="Key decision points recorded by the agent" />
          <ReasoningTrace steps={data.reasoning_trace} />
        </Card>
      )}
      {tab === "tools" && (
        <Card>
          <CardHeader
            title="Tool Call Timeline"
            subtitle="Sequential tool invocations with retries and latencies"
          />
          <ToolCallTimeline calls={data.tool_calls} />
        </Card>
      )}
      {tab === "raw" && (
        <Card>
          <CardHeader title="Raw Resolution" subtitle="Full Resolution object" />
          <CardBody>
            <pre className="text-xs text-text-dim font-mono whitespace-pre-wrap break-all bg-surface-2 border border-border rounded-md p-3 max-h-[560px] overflow-auto leading-relaxed">
              {JSON.stringify(data, null, 2)}
            </pre>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function MetaCell({ label, value, mono = false, small = false }) {
  return (
    <div className="bg-surface px-5 py-3">
      <div className="text-[10px] uppercase tracking-wider text-text-muted">
        {label}
      </div>
      <div
        className={`mt-1 text-text tabular-nums ${
          mono ? "font-mono" : ""
        } ${small ? "text-xs" : "text-sm"}`}
      >
        {value}
      </div>
    </div>
  );
}

function SummaryPanel({ data }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="lg:col-span-2">
        <CardHeader
          title={
            data.status === "escalated"
              ? "Escalation Summary"
              : "Customer Reply"
          }
          subtitle={
            data.status === "escalated"
              ? "Context passed to the human reviewer"
              : "Final message sent to the customer"
          }
          right={
            <MessageSquare className="w-3.5 h-3.5 text-text-muted" />
          }
        />
        <CardBody>
          {data.status === "escalated" ? (
            data.escalation_summary ? (
              <p className="text-sm text-text-dim leading-relaxed whitespace-pre-wrap">
                {data.escalation_summary}
              </p>
            ) : (
              <EmptyState
                icon={MessageSquare}
                title="No summary recorded"
                description="Agent did not produce an escalation summary."
              />
            )
          ) : data.final_customer_message ? (
            <p className="text-sm text-text-dim leading-relaxed whitespace-pre-wrap">
              {data.final_customer_message}
            </p>
          ) : (
            <EmptyState
              icon={MessageSquare}
              title="No reply drafted"
              description="Ticket closed without a customer-facing response."
            />
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Actions Taken" subtitle="What the agent did" />
        <CardBody>
          {!data.actions_taken || data.actions_taken.length === 0 ? (
            <EmptyState
              icon={Wrench}
              title="No actions"
              description="The agent did not take any actions."
            />
          ) : (
            <ul className="space-y-2">
              {data.actions_taken.map((a, i) => (
                <li key={i} className="flex gap-2 text-sm text-text-dim">
                  <span className="w-4 h-4 rounded-sm bg-accent/10 border border-accent/30 text-accent text-[10px] flex items-center justify-center mt-0.5 shrink-0">
                    {i + 1}
                  </span>
                  <span className="leading-relaxed">{a}</span>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
