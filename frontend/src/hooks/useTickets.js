import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api.js";

export function useTickets() {
  return useQuery({
    queryKey: ["tickets"],
    queryFn: api.listTickets,
    staleTime: 30_000,
  });
}

export function useTicket(id) {
  return useQuery({
    queryKey: ["ticket", id],
    queryFn: () => api.getTicket(id),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useIngestTickets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.ingest,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}
