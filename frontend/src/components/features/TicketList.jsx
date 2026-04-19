import { useMemo } from "react";
import { Search, Filter, Inbox } from "lucide-react";
import { Card } from "../ui/Card.jsx";
import { EmptyState } from "../ui/EmptyState.jsx";
import { TicketHeaderRow, TicketRow } from "./TicketRow.jsx";
import { SkeletonRow } from "../ui/Skeleton.jsx";
import { Button } from "../ui/Button.jsx";
import { useSentinelStore } from "../../stores/useSentinelStore.js";

const STATUSES = [
  { value: "all", label: "All statuses" },
  { value: "resolved", label: "Resolved" },
  { value: "escalated", label: "Escalated" },
  { value: "info_requested", label: "Info Requested" },
  { value: "failed", label: "Failed" },
];

export function TicketList({ tickets, loading, onIngest, ingesting }) {
  const filters = useSentinelStore((s) => s.ticketFilters);
  const setFilter = useSentinelStore((s) => s.setTicketFilter);

  const categories = useMemo(() => {
    const seen = new Set();
    (tickets ?? []).forEach((t) => t.category && seen.add(t.category));
    return ["all", ...Array.from(seen).sort()];
  }, [tickets]);

  const filtered = useMemo(() => {
    const { search, status, category } = filters;
    const q = search.trim().toLowerCase();
    return (tickets ?? []).filter((t) => {
      if (status !== "all" && t.status !== status) return false;
      if (category !== "all" && t.category !== category) return false;
      if (q && !t.ticket_id.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [tickets, filters]);

  return (
    <Card>
      <div className="flex items-center gap-3 p-4 border-b border-border flex-wrap">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search ticket ID…"
            value={filters.search}
            onChange={(e) => setFilter("search", e.target.value)}
            className="w-full h-8 pl-8 pr-3 bg-surface-2 border border-border rounded-md text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent-alt transition-colors"
          />
        </div>
        <SelectField
          icon={Filter}
          value={filters.status}
          onChange={(v) => setFilter("status", v)}
          options={STATUSES}
        />
        <SelectField
          value={filters.category}
          onChange={(v) => setFilter("category", v)}
          options={categories.map((c) => ({
            value: c,
            label: c === "all" ? "All categories" : c.replace(/_/g, " "),
          }))}
        />
        <div className="flex-1 flex justify-end">
          <Button
            variant="primary"
            size="md"
            onClick={onIngest}
            disabled={ingesting}
          >
            {ingesting ? "Processing…" : "Process Tickets"}
          </Button>
        </div>
      </div>
      <TicketHeaderRow />
      {loading ? (
        <div className="divide-y divide-border">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="px-4">
              <SkeletonRow />
            </div>
          ))}
        </div>
      ) : !tickets || tickets.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="No tickets processed yet"
          description="Trigger the agent to ingest and resolve the tickets fixture."
          action={
            <Button variant="primary" onClick={onIngest} disabled={ingesting}>
              {ingesting ? "Processing…" : "Process Tickets"}
            </Button>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Filter}
          title="No matches"
          description="Adjust filters to see more tickets."
        />
      ) : (
        <div>
          {filtered.map((t) => (
            <TicketRow key={t.ticket_id} ticket={t} />
          ))}
          <div className="h-9 px-4 flex items-center border-t border-border text-[11px] text-text-muted">
            Showing {filtered.length} of {tickets.length}
          </div>
        </div>
      )}
    </Card>
  );
}

function SelectField({ icon: Icon, value, onChange, options }) {
  return (
    <div className="relative">
      {Icon && (
        <Icon className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`h-8 ${
          Icon ? "pl-8" : "pl-3"
        } pr-8 bg-surface-2 border border-border rounded-md text-sm text-text focus:outline-none focus:border-accent-alt appearance-none cursor-pointer`}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <svg
        className="w-3 h-3 text-text-muted absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
        viewBox="0 0 12 12"
        fill="none"
      >
        <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    </div>
  );
}
