import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { StatusBadge } from "../ui/Badge.jsx";
import {
  formatConfidence,
  formatLatency,
  titleCase,
} from "../../lib/formatters.js";
import { cn } from "../../lib/cn.js";

export function TicketRow({ ticket }) {
  const conf = ticket.confidence ?? 0;
  const confColor =
    conf >= 0.8
      ? "text-accent"
      : conf >= 0.6
      ? "text-accent-alt"
      : conf >= 0.4
      ? "text-warn"
      : "text-danger";
  return (
    <Link
      to={`/tickets/${ticket.ticket_id}`}
      className="group grid grid-cols-[140px_160px_160px_120px_100px_100px_32px] gap-4 items-center px-4 h-12 border-t border-border hover:bg-surface-2 transition-colors duration-150"
    >
      <span className="font-mono text-xs text-text tabular-nums">
        {ticket.ticket_id}
      </span>
      <span className="text-xs text-text-dim truncate">
        {titleCase(ticket.category)}
      </span>
      <StatusBadge status={ticket.status} />
      <span className={cn("text-xs tabular-nums", confColor)}>
        {formatConfidence(conf)}
      </span>
      <span className="text-xs text-text-dim tabular-nums">
        {ticket.tool_call_cnt ?? 0}
      </span>
      <span className="text-xs text-text-dim tabular-nums font-mono">
        {formatLatency(ticket.latency_ms)}
      </span>
      <ChevronRight className="w-3.5 h-3.5 text-text-muted group-hover:text-text transition-colors" />
    </Link>
  );
}

export function TicketHeaderRow() {
  return (
    <div className="grid grid-cols-[140px_160px_160px_120px_100px_100px_32px] gap-4 items-center px-4 h-9 text-[10px] uppercase tracking-wider text-text-muted font-medium">
      <span>Ticket ID</span>
      <span>Category</span>
      <span>Status</span>
      <span>Confidence</span>
      <span>Tool Calls</span>
      <span>Latency</span>
      <span />
    </div>
  );
}
