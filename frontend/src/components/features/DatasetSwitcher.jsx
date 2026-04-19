import { useRef, useState } from "react";
import { Database, Upload, Check, X, AlertTriangle, Loader2 } from "lucide-react";
import {
  useDatasets,
  useSwitchDataset,
  useUploadDataset,
} from "../../hooks/useDatasets.js";
import { Card, CardHeader, CardBody } from "../ui/Card.jsx";
import { Button } from "../ui/Button.jsx";
import { Badge } from "../ui/Badge.jsx";
import { Skeleton } from "../ui/Skeleton.jsx";
import { useSentinelStore } from "../../stores/useSentinelStore.js";
import { cn } from "../../lib/cn.js";

function TagBadge({ tag }) {
  const variant =
    tag === "official" ? "accent" : tag === "custom" ? "resolved" : "neutral";
  return (
    <Badge variant={variant} className="text-[10px] uppercase tracking-wider">
      {tag}
    </Badge>
  );
}

export function DatasetSwitcher({ compact = false }) {
  const datasets = useDatasets();
  const switcher = useSwitchDataset();
  const uploader = useUploadDataset();
  const showToast = useSentinelStore((s) => s.showToast);

  const [selected, setSelected] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  const active = datasets.data?.available?.find(
    (d) => d.id === datasets.data.active
  );
  const pending = selected
    ? datasets.data?.available?.find((d) => d.id === selected)
    : null;

  if (datasets.isLoading) {
    return (
      <Card>
        <CardBody>
          <Skeleton className="h-20 w-full" />
        </CardBody>
      </Card>
    );
  }

  if (datasets.error || !datasets.data) {
    return (
      <Card>
        <CardBody>
          <div className="flex items-center gap-2 text-sm text-danger">
            <AlertTriangle className="w-4 h-4" />
            Could not load datasets: {datasets.error?.message}
          </div>
        </CardBody>
      </Card>
    );
  }

  const confirmSwitch = async () => {
    if (!pending) return;
    try {
      await switcher.mutateAsync(pending.id);
      showToast({
        type: "success",
        title: `Switched to ${pending.name}`,
        description: `Cleared prior run. Ready to process ${pending.count} tickets.`,
      });
      setSelected(null);
      setConfirming(false);
    } catch (err) {
      showToast({
        type: "error",
        title: "Switch failed",
        description: err.message,
      });
    }
  };

  // Compact view for Dashboard
  if (compact) {
    return (
      <Card>
        <CardBody>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-md bg-accent-alt/10 border border-accent-alt/20 flex items-center justify-center shrink-0">
                <Database className="w-4 h-4 text-accent-alt" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-text font-medium truncate">
                    {active?.name ?? "No dataset"}
                  </span>
                  {active && <TagBadge tag={active.tag} />}
                </div>
                <div className="text-xs text-text-muted mt-0.5 font-mono tabular-nums">
                  {active?.count ?? 0} tickets · id={" "}
                  <span className="text-text-dim">{active?.id}</span>
                </div>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
    );
  }

  // Full view for Tickets page
  return (
    <>
      <Card>
        <CardHeader
          title="Dataset"
          subtitle="Choose what the agent will process"
          right={
            <Button
              variant="secondary"
              size="sm"
              icon={Upload}
              onClick={() => setUploadOpen(true)}
            >
              Upload custom
            </Button>
          }
        />
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {datasets.data.available.map((d) => {
              const isActive = d.id === datasets.data.active;
              const isSelected = selected === d.id;
              return (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => {
                    if (isActive) return;
                    setSelected(d.id);
                  }}
                  className={cn(
                    "text-left rounded-lg p-3 border transition-colors",
                    isActive
                      ? "border-accent bg-accent/5 cursor-default"
                      : isSelected
                      ? "border-accent-alt bg-accent-alt/5"
                      : "border-border bg-surface-2 hover:border-text-muted"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-sm text-text font-medium truncate">
                        {d.name}
                      </span>
                      <TagBadge tag={d.tag} />
                    </div>
                    {isActive ? (
                      <span className="inline-flex items-center gap-1 text-[10px] text-accent uppercase tracking-wider font-medium shrink-0">
                        <Check className="w-3 h-3" />
                        Active
                      </span>
                    ) : isSelected ? (
                      <span className="text-[10px] text-accent-alt uppercase tracking-wider font-medium shrink-0">
                        Pending
                      </span>
                    ) : null}
                  </div>
                  <p className="text-xs text-text-muted mt-1.5 leading-relaxed">
                    {d.description}
                  </p>
                  <div className="text-[11px] text-text-dim font-mono tabular-nums mt-2">
                    {d.count} tickets
                  </div>
                </button>
              );
            })}
          </div>

          {selected && pending && (
            <div className="mt-4 flex items-center justify-between gap-3 p-3 bg-warn/5 border border-warn/20 rounded-md flex-wrap">
              <div className="flex items-start gap-2 min-w-0">
                <AlertTriangle className="w-4 h-4 text-warn shrink-0 mt-0.5" />
                <div className="text-xs text-text-dim leading-relaxed">
                  Switching will{" "}
                  <span className="text-text font-medium">clear the current run</span>{" "}
                  (metrics, tickets, audit log) and make{" "}
                  <span className="text-text font-medium">{pending.name}</span> active.
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelected(null)}
                  disabled={switcher.isPending}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={confirmSwitch}
                  disabled={switcher.isPending}
                  icon={switcher.isPending ? Loader2 : Check}
                >
                  {switcher.isPending ? "Switching…" : "Switch & Clear"}
                </Button>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          uploader={uploader}
          onSuccess={(entry) =>
            showToast({
              type: "success",
              title: `Uploaded ${entry.name}`,
              description: `Activated ${entry.count} tickets. Click Process Tickets to run.`,
            })
          }
          onError={(err) =>
            showToast({
              type: "error",
              title: "Upload failed",
              description: err.message,
            })
          }
        />
      )}
    </>
  );
}

function UploadModal({ onClose, uploader, onSuccess, onError }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [errors, setErrors] = useState([]);

  const submit = async () => {
    if (!file) return;
    setErrors([]);
    try {
      const res = await uploader.mutateAsync(file);
      onSuccess?.(res.active);
      onClose();
    } catch (err) {
      const body = err.body;
      if (body?.detail?.errors?.length) {
        setErrors(body.detail.errors);
      } else {
        setErrors([err.message]);
      }
      onError?.(err);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-lg w-full max-w-lg shadow-2xl animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            <h3 className="text-sm font-medium text-text">Upload dataset</h3>
            <p className="text-xs text-text-muted mt-0.5">
              JSON array of tickets. Validated against the Ticket schema.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-5 space-y-4">
          <div>
            <input
              ref={fileRef}
              type="file"
              accept="application/json,.json"
              onChange={(e) => {
                setErrors([]);
                setFile(e.target.files?.[0] ?? null);
              }}
              className="block w-full text-xs text-text-dim file:mr-3 file:px-3 file:py-1.5 file:rounded-md file:border file:border-border file:bg-surface-2 file:text-text file:text-xs file:font-medium file:cursor-pointer hover:file:bg-border"
            />
            {file && (
              <div className="mt-2 text-xs text-text-muted">
                Selected: <span className="text-text">{file.name}</span> (
                {(file.size / 1024).toFixed(1)} KB)
              </div>
            )}
          </div>

          <div className="bg-surface-2 border border-border rounded-md p-3 text-[11px] text-text-dim leading-relaxed">
            <div className="text-text font-medium mb-1">Required fields per ticket:</div>
            <code className="font-mono block">
              ticket_id, customer_email, subject, body, created_at
            </code>
            <div className="mt-2">Max 200 tickets · all ticket_ids must be unique.</div>
          </div>

          {errors.length > 0 && (
            <div className="bg-danger/5 border border-danger/20 rounded-md p-3 max-h-40 overflow-auto">
              <div className="flex items-center gap-1.5 text-xs text-danger font-medium mb-1.5">
                <AlertTriangle className="w-3 h-3" />
                Validation failed
              </div>
              <ul className="text-[11px] text-text-dim space-y-1 font-mono">
                {errors.map((e, i) => (
                  <li key={i} className="break-all">
                    · {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border bg-surface-2/50 rounded-b-lg">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={submit}
            disabled={!file || uploader.isPending}
            icon={uploader.isPending ? Loader2 : Upload}
          >
            {uploader.isPending ? "Uploading…" : "Upload & Activate"}
          </Button>
        </div>
      </div>
    </div>
  );
}
