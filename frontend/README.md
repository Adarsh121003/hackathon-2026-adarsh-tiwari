# Sentinel Frontend

Production-grade React dashboard for the Sentinel autonomous support agent.

## Stack

- Vite + React 18 (SWC)
- Tailwind CSS v3
- TanStack Query (data fetching + cache)
- Zustand (live events + filters)
- React Router v6
- Recharts, lucide-react
- Dark-mode UI designed for judges on a projector.

## Run

```bash
cd frontend
npm install
npm run dev
```

Opens on [http://localhost:5173](http://localhost:5173).

The Vite dev server proxies `/api/*` to the FastAPI backend on
`http://localhost:8000`, so start the backend in parallel:

```bash
# from the repo root
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

To point the frontend at a non-default backend, copy `.env.example` to `.env`
and set `VITE_API_BASE_URL`. When set, the proxy is bypassed.

## Pages

| Route | Purpose |
|---|---|
| `/` | Dashboard — KPIs, status donut, category chart, live feed |
| `/tickets` | Filterable/sortable list of resolved tickets |
| `/tickets/:id` | Deep view: reasoning, tool timeline, raw resolution |
| `/audit` | Raw audit JSONL with search + download |
| `/about` | Architecture for judges |

## Architecture notes

- **State split.** Server data lives in TanStack Query (tickets, metrics, audit log).
  Live events + ephemeral filter state live in a single Zustand store
  (`stores/useSentinelStore.js`). No `localStorage` — all in-memory.
- **Live updates.** `hooks/useLiveStream.js` subscribes to `/api/stream` via
  `EventSource`. On `complete`/`resolved` events it invalidates the relevant
  query keys so cached views stay fresh without polling.
- **Resilience.** `lib/sse.js` auto-reconnects up to 5 times with a 3s backoff
  and surfaces status through the topbar.
- **Typography.** Inter + JetBrains Mono via `rsms.me/inter` and tailwind
  `font-mono` utility on numerics.
