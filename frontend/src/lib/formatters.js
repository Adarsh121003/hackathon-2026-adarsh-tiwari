export function formatLatency(ms) {
  if (ms == null || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatPercent(n, digits = 0) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatNumber(n, digits = 1) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

export function formatConfidence(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toFixed(2);
}

export function formatDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function formatRelative(iso) {
  if (!iso) return "—";
  const d = new Date(iso).getTime();
  const now = Date.now();
  const diff = (now - d) / 1000;
  if (diff < 5) return "just now";
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

export function titleCase(s) {
  if (!s) return "";
  return s
    .replace(/_/g, " ")
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function truncate(s, n = 80) {
  if (!s) return "";
  return s.length > n ? `${s.slice(0, n)}…` : s;
}
