import { API_BASE } from "./api.js";

const MAX_RETRIES = 5;
const RETRY_MS = 3000;

export function subscribeToStream({ onEvent, onStatus } = {}) {
  let source = null;
  let retries = 0;
  let closed = false;
  let retryTimer = null;

  const connect = () => {
    if (closed) return;
    onStatus?.("connecting");
    source = new EventSource(`${API_BASE}/api/stream`);
    source.onopen = () => {
      retries = 0;
      onStatus?.("open");
    };
    source.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data);
        onEvent?.(parsed);
      } catch {
        // malformed; ignore
      }
    };
    source.onerror = () => {
      onStatus?.("error");
      source?.close();
      source = null;
      if (closed) return;
      if (retries >= MAX_RETRIES) {
        onStatus?.("failed");
        return;
      }
      retries += 1;
      retryTimer = setTimeout(connect, RETRY_MS);
    };
  };

  connect();

  return () => {
    closed = true;
    if (retryTimer) clearTimeout(retryTimer);
    source?.close();
    source = null;
  };
}
