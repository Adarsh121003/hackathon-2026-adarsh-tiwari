import { useMetrics } from "../hooks/useMetrics.js";
import { useTickets, useIngestTickets } from "../hooks/useTickets.js";
import { MetricsGrid } from "../components/features/MetricsGrid.jsx";
import { StatusDonut } from "../components/features/StatusDonut.jsx";
import { CategoryChart } from "../components/features/CategoryChart.jsx";
import { LiveFeed } from "../components/features/LiveFeed.jsx";
import { DatasetSwitcher } from "../components/features/DatasetSwitcher.jsx";
import { Button } from "../components/ui/Button.jsx";
import { useSentinelStore } from "../stores/useSentinelStore.js";
import { Play } from "lucide-react";

export function Dashboard() {
  const metrics = useMetrics();
  const tickets = useTickets();
  const ingest = useIngestTickets();
  const showToast = useSentinelStore((s) => s.showToast);

  const handleIngest = async () => {
    try {
      const res = await ingest.mutateAsync();
      showToast({
        type: "success",
        title: "Ingestion started",
        description: `Processing ${res.total_tickets} tickets · run ${res.run_id}`,
      });
    } catch (err) {
      showToast({
        type: "error",
        title: "Failed to start",
        description: err.message,
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-text tracking-tight">
            Overview
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Autonomous support agent for ShopWave — live resolution metrics.
          </p>
        </div>
        <Button
          variant="primary"
          icon={Play}
          onClick={handleIngest}
          disabled={ingest.isPending}
        >
          {ingest.isPending ? "Starting…" : "Process Tickets"}
        </Button>
      </div>

      <DatasetSwitcher compact />

      <MetricsGrid metrics={metrics.data} loading={metrics.isLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <StatusDonut metrics={metrics.data} loading={metrics.isLoading} />
        <CategoryChart tickets={tickets.data} loading={tickets.isLoading} />
      </div>

      <LiveFeed />
    </div>
  );
}
