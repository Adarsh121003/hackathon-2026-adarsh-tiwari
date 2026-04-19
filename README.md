# Sentinel — Autonomous Support Resolution Agent

> Production-grade agentic AI system for ShopWave e-commerce support ticket resolution.
> Built for the Ksolves Agentic AI Hackathon 2026 by **Adarsh Tiwari**.

![Stack](https://img.shields.io/badge/python-3.11-blue) ![Node](https://img.shields.io/badge/node-20_LTS-green) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-teal) ![React](https://img.shields.io/badge/React-18-61dafb) ![Status](https://img.shields.io/badge/status-submission--ready-brightgreen)

Sentinel ingests customer support tickets, routes each one through a custom ReAct
reasoning loop, invokes domain tools to read state and take action, and produces
either an auto-resolution or a human-ready escalation — with a full, replayable audit
trail for every step.

---
## Video
https://drive.google.com/file/d/13zc1BgwW-mJLE-sRHfSG2MVEAUXNSFq4/view?usp=drive_link
## Overview

Sentinel is a two-agent support automation pipeline:

- **Triage Agent** — a single cheap LLM call tags each ticket with category,
  urgency, and whether the request is auto-resolvable.
- **Resolver Agent** — a multi-step ReAct loop equipped with 8 domain tools
  (order lookup, refund eligibility, refund issuance, customer reply, KB search,
  escalation, etc.), hardened by a canonical-JSON loop guard, idempotency keys,
  a guardrail layer, and chaos-tolerant retries.
- **Audit Layer** — every decision is written to JSONL (stream), SQLite (query),
  and a final `audit_log.json` submission artifact.

A React dashboard streams events live via Server-Sent Events, and a dataset
switcher lets judges swap between the Ksolves 20 sample and a 50-ticket synthetic
stress test (or upload their own).

### Key Numbers (tuned run)

| Metric                              | Ksolves 20       | Synthetic 50     |
|-------------------------------------|------------------|------------------|
| Resolved                            | 9 / 20 (45%)     | 17 / 50 (34%)    |
| Correctly escalated per policy      | 11               | 33               |
| Avg tool calls per ticket           | 6.1              | 6.0              |
| Avg confidence                      | 0.78             | 0.76             |
| Crashes / uncaught exceptions       | 0                | 0                |

> Remaining tickets are **policy-mandated escalations** (warranty claims,
> social-engineering attempts, replacement requests, threats of chargeback) —
> not failures. See `benchmarks/` for before/after artifacts.

---

## Architecture

A complete write-up with diagrams is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
(PDF at [`docs/ARCHITECTURE.pdf`](docs/ARCHITECTURE.pdf)). At a glance:

```
Ticket Source (JSON)
        ↓
   Ingest Queue  ──►  [Triage Agent]  ──►  category / urgency / auto_resolvable
        ↓                                          ↓
   Worker Pool (asyncio.Semaphore)          [Resolver Agent — ReAct loop]
        ↓                                   ├─ 8 Tools (read + action)
   Dead-letter queue                        ├─ Loop guard (canonical JSON cache)
                                            ├─ Guardrails (idempotency, ceilings)
                                            └─ Confidence calibration
                                                   ↓
                                        resolved / escalated / info_requested
                                                   ↓
                              Audit → JSONL + SQLite + audit_log.json
```

---

## Quick Start

### Prerequisites

- Python **3.11** (a `.python-version` file pins this for `pyenv`)
- Node.js **20 LTS** + npm 10
- One LLM provider key: **OpenAI** (recommended, `$5` covers ~100 full runs),
  Anthropic, Groq, or a local Ollama

### 5-minute setup

```bash
git clone <repo-url> sentinel && cd sentinel

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Env
cp .env.example .env
# edit .env — set LLM_PROVIDER=openai and OPENAI_API_KEY=sk-...

# Frontend
cd frontend && npm install && cd ..
```

### Run it

**Option A — CLI demo (fastest, produces the submission artifact):**

```bash
source venv/bin/activate
python -m backend.run_demo
```

Outputs a rich terminal summary plus `audit_log.json` (submission artifact),
`logs/audit_log.jsonl`, and `logs/sentinel.db`.

**Option B — Full dashboard (recommended for the demo):**

Terminal 1 (backend):
```bash
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend && npm run dev
```

Open <http://localhost:5173>, pick a dataset, hit **Process Tickets**.

---

````md
## Docker Run (Recommended)

Run the complete Sentinel stack (FastAPI backend + React frontend) using Docker.

### Prerequisites

- Docker 27+
- Docker Compose v2

Verify:

```bash
docker --version
docker compose version
````

---

### 1. Clone Repository

```bash
git clone <repo-url>
cd to-project
```

---

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

(Anthropic / Groq / Ollama also supported.)

---

### 3. Start Full Application

```bash
docker compose up --build
```

This launches:

* Backend (FastAPI) → `8000`
* Frontend (React + Vite) → `5173`

---

### 4. Open Application

Frontend Dashboard:

http://localhost:5173

Backend API:

http://localhost:8000

Swagger Docs:

http://localhost:8000/docs

---

### 5. Stop Application

```bash
docker compose down
```

---

### 6. Run in Background

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f
```

Stop background mode:

```bash
docker compose down
```

---

### 7. Rebuild After Code Changes

```bash
docker compose up --build
```

---

### 8. Cleanup (Optional)

Remove unused Docker data:

```bash
docker system prune -a -f
```

---

### Notes

* Frontend automatically proxies `/api/*` requests to backend.
* Local development mode also works without Docker.
* Logs and generated files remain inside project folders.

```
```


## Features

### Agent
- Two-stage pipeline (triage + resolver) — ~40% fewer tokens than monolithic
- Multi-step ReAct loop, 16-step ceiling with graceful escalation on exhaustion
- Canonical-JSON loop detection prevents LLM from re-calling identical tools
- Idempotency keys — a refund cannot fire twice for the same ticket
- Guardrail layer: refund requires eligibility check, escalation requires ≥50-char
  summary, high-value refunds capped at `$200` auto-approval
- Confidence calibration blending LLM self-report, tool-success ratio, and
  guardrail events
- Multi-provider LLM abstraction — swap OpenAI / Anthropic / Groq / Ollama with
  a single env var

### Resilience
- Chaos injection on tool layer (`5%` timeout, `3%` malformed by default) to prove
  the retry / escalation path is exercised
- Exponential backoff with 3 attempts per tool
- Dead-letter queue for workers that exhaust retries
- OpenAI rate-limit handling with `Retry-After` parsing

### Dashboard
- Real-time SSE live feed of agent activity
- Per-ticket tool-call timeline with expandable arguments/results
- Reasoning trace viewer
- Metrics dashboard (KPI grid, status donut, category bar chart)
- Audit log explorer with full-text search + JSON download
- **Dataset switcher** — swap Ksolves 20 / Synthetic 50 / upload custom JSON
- Architecture explainer page

### Audit
- Triple-storage: JSONL (`logs/audit_log.jsonl`), SQLite (`logs/sentinel.db`),
  submission JSON (`audit_log.json`)
- Every tool call records `sequence, tool_name, arguments, result, latency,
  attempt, timestamp, success`
- Structured reasoning trace per ticket

---

## Configuration

All settings are read from `.env` (gitignored). Highlights:

| Variable                     | Default                      | Description                                         |
|------------------------------|------------------------------|-----------------------------------------------------|
| `LLM_PROVIDER`               | `groq`                       | `openai` / `anthropic` / `groq` / `ollama`          |
| `OPENAI_MODEL`               | `gpt-4o-mini`                | OpenAI model name                                   |
| `ANTHROPIC_MODEL`            | `claude-sonnet-4-5-20250929` | Anthropic model name                                |
| `MAX_CONCURRENT_TICKETS`     | `2`                          | asyncio semaphore capacity                          |
| `MAX_AGENT_STEPS`            | `16`                         | ReAct loop ceiling per ticket                       |
| `CONFIDENCE_THRESHOLD`       | `0.6`                        | Below this, auto-escalate                           |
| `HIGH_VALUE_REFUND_THRESHOLD`| `200.0`                      | USD ceiling for automatic refund                    |
| `MOCK_TIMEOUT_RATE`          | `0.12`                       | Chaos: tool timeout probability                     |
| `MOCK_MALFORMED_RATE`        | `0.08`                       | Chaos: tool malformed-response probability          |
| `TOOL_TIMEOUT_SECONDS`       | `5.0`                        | Hard per-tool timeout                               |
| `MAX_TOOL_RETRIES`           | `2`                          | Retry budget per tool call                          |
| `ACTIVE_DATASET`             | _manifest_                   | Override active dataset at boot (optional)          |

---

## Project Structure

```
hackathon2026-adarsh-tiwari/
├── backend/
│   ├── agent/          # Triage + Resolver + Guardrails + Confidence
│   ├── api/            # FastAPI routes + SSE streams + CORS
│   ├── audit/          # JSONL logger + SQLite store + JSON exporter
│   ├── core/           # Pydantic models + config + logging
│   ├── ingestion/      # Queue + worker pool + dead-letter
│   ├── llm/            # Multi-provider abstraction (factory pattern)
│   └── tools/          # 8 mock tools + resilience wrapper + KB search
├── frontend/           # React + Vite + Tailwind dashboard
├── data/               # JSON datasets (tickets, customers, orders, products, KB)
│   ├── dataset_manifest.json
│   ├── tickets_ksolves_20.json
│   └── tickets_combined_50.json
├── benchmarks/         # Baseline vs tuned comparison artifacts
├── docs/               # ARCHITECTURE.{md,pdf} + FAILURE_MODES.md
├── logs/               # Runtime JSONL + SQLite (gitignored)
├── audit_log.json      # Submission artifact (generated by run_demo)
├── requirements.txt
└── .env.example
```

---

## Benchmarks

| Dataset          | Baseline        | Tuned           | Δ      |
|------------------|-----------------|-----------------|--------|
| Ksolves 20       | 7 / 20 (35%)    | 9 / 20 (45%)    | +10%   |
| Synthetic 50     | 13 / 50 (26%)   | 17 / 50 (34%)   | +8%    |

Tuning changes were **infrastructural, not ticket-specific**: chaos-rate
calibration, enum `__str__` overrides, canonical-JSON loop guard, convergence-bias
prompt additions, and `MAX_AGENT_STEPS` lifted from 12 → 16. See
`benchmarks/BASELINE_v1.md` for methodology.

---

## Technology Decisions

| Decision                         | Rationale                                                                 |
|----------------------------------|---------------------------------------------------------------------------|
| Custom ReAct loop (no LangGraph) | Explainability and tight control over step budget + loop detection        |
| Two-stage pipeline               | Cheap triage fails-fast on irrelevant tickets; ~40% token reduction       |
| Pydantic v2 everywhere           | Schema contract at every boundary; frozen models catch malformed data     |
| asyncio + `Semaphore`            | Right tool for I/O-bound LLM workloads                                    |
| Provider factory                 | Zero vendor lock-in — one env var swap between OpenAI/Anthropic/Groq      |
| Idempotency keys                 | Prevents double-refund under retries (Stripe pattern)                     |
| Canonical-JSON loop cache        | Stops pathological LLM repetition before it burns the step budget         |
| Dead-letter queue                | No silent failures; ops can replay                                        |
| JSONL + SQLite dual store        | `grep`-friendly stream + indexed query                                    |
| React + TanStack Query + SSE     | Live UI without polling, server-authoritative cache                       |

See `docs/FAILURE_MODES.md` for the detailed failure-handling playbook.

---

## Development

Run the CLI demo:
```bash
python -m backend.run_demo
```

Endpoints (backend running on `:8000`):
```
GET  /api/health
POST /api/ingest                  # kicks off a run; returns run_id
GET  /api/tickets
GET  /api/tickets/{ticket_id}
GET  /api/metrics
GET  /api/audit/log
GET  /api/stream                  # Server-Sent Events
GET  /api/datasets
POST /api/datasets/switch         # body: {"dataset_id": "..."}
POST /api/datasets/upload         # multipart file upload
```

---

## Submission

- **Event:** Ksolves Agentic AI Hackathon 2026
- **Participant:** Adarsh Tiwari <adarshtiwari.110044@gmail.com>
- **Deadline:** 2026-04-19, 9 PM IST
- **Submission artifact:** `audit_log.json` (regenerated on every `run_demo`)

---