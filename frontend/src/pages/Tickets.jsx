import { useTickets, useIngestTickets } from "../hooks/useTickets.js";
import { TicketList } from "../components/features/TicketList.jsx";
import { DatasetSwitcher } from "../components/features/DatasetSwitcher.jsx";
import { useSentinelStore } from "../stores/useSentinelStore.js";

export function Tickets() {
  const { data, isLoading } = useTickets();
  const ingest = useIngestTickets();
  const showToast = useSentinelStore((s) => s.showToast);

  const onIngest = async () => {
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
        title: "Failed to ingest",
        description: err.message,
      });
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-text tracking-tight">
          Tickets
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Every ticket processed by the resolver, with audit metadata.
        </p>
      </div>
      <DatasetSwitcher />

      <TicketList
        tickets={data}
        loading={isLoading}
        onIngest={onIngest}
        ingesting={ingest.isPending}
      />
    </div>
  );
}
