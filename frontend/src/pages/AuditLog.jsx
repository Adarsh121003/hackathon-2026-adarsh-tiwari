import { useMemo, useState } from "react";
import { Download, Search, FileText } from "lucide-react";
import { useAuditLog } from "../hooks/useMetrics.js";
import { Card, CardHeader, CardBody } from "../components/ui/Card.jsx";
import { EmptyState } from "../components/ui/EmptyState.jsx";
import { Skeleton } from "../components/ui/Skeleton.jsx";
import { Button } from "../components/ui/Button.jsx";

export function AuditLog() {
  const { data, isLoading, error, refetch } = useAuditLog();
  const [query, setQuery] = useState("");

  const lines = useMemo(() => {
    if (!Array.isArray(data)) return [];
    if (!query.trim()) return data;
    const q = query.trim().toLowerCase();
    return data.filter((entry) =>
      JSON.stringify(entry).toLowerCase().includes(q)
    );
  }, [data, query]);

  const download = () => {
    const blob = new Blob([JSON.stringify(data ?? [], null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audit_log.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-text tracking-tight">
          Audit Log
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Canonical JSONL record of every agent action for replay and review.
        </p>
      </div>

      <Card>
        <div className="flex items-center gap-3 p-4 border-b border-border flex-wrap">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by ticket ID, tool name, field…"
              className="w-full h-8 pl-8 pr-3 bg-surface-2 border border-border rounded-md text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent-alt"
            />
          </div>
          <div className="text-xs text-text-muted font-mono tabular-nums">
            {lines.length} / {data?.length ?? 0} lines
          </div>
          <Button
            variant="secondary"
            icon={Download}
            onClick={download}
            disabled={!data?.length}
          >
            Download
          </Button>
        </div>
        <CardBody className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          ) : error ? (
            <EmptyState
              icon={FileText}
              title="Could not load audit log"
              description={error.message}
              action={
                <Button variant="secondary" onClick={() => refetch()}>
                  Retry
                </Button>
              }
            />
          ) : lines.length === 0 ? (
            <EmptyState
              icon={FileText}
              title={data?.length ? "No matches" : "Audit log is empty"}
              description={
                data?.length
                  ? "Try a different search term."
                  : "Run ingestion to populate audit records."
              }
            />
          ) : (
            <pre className="font-mono text-[11px] text-text-dim leading-relaxed p-4 max-h-[640px] overflow-auto">
              {lines.map((entry, i) => (
                <div
                  key={i}
                  className="py-0.5 border-b border-border/50 last:border-0 whitespace-pre-wrap break-all"
                >
                  <span className="text-text-muted select-none mr-3">
                    {String(i + 1).padStart(4, " ")}
                  </span>
                  {JSON.stringify(entry)}
                </div>
              ))}
            </pre>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
