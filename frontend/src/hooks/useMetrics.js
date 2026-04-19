import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api.js";

export function useMetrics() {
  return useQuery({
    queryKey: ["metrics"],
    queryFn: api.metrics,
    staleTime: 10_000,
  });
}

export function useAuditLog() {
  return useQuery({
    queryKey: ["audit-log"],
    queryFn: api.auditLog,
    staleTime: 30_000,
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 15_000,
    retry: 0,
  });
}
