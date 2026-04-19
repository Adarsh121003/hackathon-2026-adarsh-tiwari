import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api.js";

export function useDatasets() {
  return useQuery({
    queryKey: ["datasets"],
    queryFn: api.listDatasets,
    staleTime: 60_000,
  });
}

function invalidateRunData(qc) {
  qc.invalidateQueries({ queryKey: ["datasets"] });
  qc.invalidateQueries({ queryKey: ["tickets"] });
  qc.invalidateQueries({ queryKey: ["metrics"] });
  qc.invalidateQueries({ queryKey: ["auditLog"] });
}

export function useSwitchDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (datasetId) => api.switchDataset(datasetId),
    onSuccess: () => invalidateRunData(qc),
  });
}

export function useUploadDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file) => api.uploadDataset(file),
    onSuccess: () => invalidateRunData(qc),
  });
}
