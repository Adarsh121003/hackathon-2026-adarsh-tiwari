const RAW_BASE = import.meta.env.VITE_API_BASE_URL;
// With Vite proxy, we can leave base empty and let "/api" requests be proxied.
// When the env var is set, absolute URL is used (for prod or non-proxy dev).
export const API_BASE = RAW_BASE && RAW_BASE.length > 0 ? RAW_BASE : "";

export class APIError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  let res;
  try {
    res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (err) {
    throw new APIError(`Network error: ${err.message}`, 0, null);
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail = data?.detail || res.statusText || "Request failed";
    throw new APIError(detail, res.status, data);
  }
  return data;
}

async function uploadFile(path, file) {
  const url = `${API_BASE}${path}`;
  const form = new FormData();
  form.append("file", file);
  let res;
  try {
    res = await fetch(url, { method: "POST", body: form });
  } catch (err) {
    throw new APIError(`Network error: ${err.message}`, 0, null);
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail = data?.detail || res.statusText || "Upload failed";
    throw new APIError(
      typeof detail === "string" ? detail : detail.message || "Upload failed",
      res.status,
      data
    );
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),
  ingest: () => request("/api/ingest", { method: "POST" }),
  listTickets: () => request("/api/tickets"),
  getTicket: (id) => request(`/api/tickets/${id}`),
  metrics: () => request("/api/metrics"),
  auditLog: () => request("/api/audit/log"),
  listDatasets: () => request("/api/datasets"),
  switchDataset: (dataset_id) =>
    request("/api/datasets/switch", {
      method: "POST",
      body: JSON.stringify({ dataset_id }),
    }),
  uploadDataset: (file) => uploadFile("/api/datasets/upload", file),
};
