# Failure Modes & Recovery Playbook

**Sentinel — Autonomous Support Resolution Agent · Ksolves Hackathon 2026**

Real support systems fail constantly: APIs time out, LLMs hallucinate tool
arguments, agents loop on ambiguous tickets, guardrails catch unsafe actions.
A scoring agent that pretends these don't happen is a toy. This document
enumerates the seven failure modes Sentinel is hardened against, how each is
detected, and what the system does when it fires — every behavior below is
backed by code that runs in the demo.

The guiding principle: **no failure is silent**. Every failure produces an
audit record, a recovery attempt, or a human escalation — never a dropped
ticket.

---

## 1. Tool Timeout

**Scenario.** A downstream tool (mock API) hangs past `TOOL_TIMEOUT_SECONDS`
(default 5s). In production this maps to an unresponsive CRM, payment
processor, or knowledge base.

**How it's simulated.** `backend/tools/mock_tools.py` injects latency at a
`MOCK_TIMEOUT_RATE` (default 5%) — judges can see real retries during the
demo, not just theoretical ones.

**Detection.** `backend/tools/resilience.py:57` wraps every tool invocation
in `asyncio.wait_for(...)`. A `TimeoutError` is caught and wrapped in a
domain-specific `ToolTimeoutError`.

**Recovery.**
- Exponential backoff with jitter: `base_delay * 2^(attempt-1) + U(0, 0.05)`.
- Up to `MAX_TOOL_RETRIES + 1` attempts (default 3 total).
- Every attempt — success or failure — produces its own `ToolCallRecord`
  in the audit trail, so the retry history is fully visible post-hoc.

**Final fallback.** If all retries fail, `execute_tool()` returns an
`{"error": "tool_failed", ...}` dict to the ReAct loop rather than raising.
The LLM then sees the failure in its conversation history and can adapt —
e.g. switch to a different lookup tool or escalate to a human with the
timeout as context. This is the "never black-box the agent" principle:
the LLM is a first-class failure handler.

**Evidence.** The latest run shows **13 tickets with `attempt > 1`** in
`audit_log.json` — the retry path is exercised, not theoretical.

---

## 2. Malformed Tool Response

**Scenario.** A tool returns structurally-invalid data: wrong keys, garbled
JSON, or a response shape the agent cannot reason over. Production analog:
a vendor API ships a breaking change mid-deploy.

**How it's simulated.** `MOCK_MALFORMED_RATE` (default 3%) in
`mock_tools.py` randomly corrupts tool output.

**Detection.** The tool itself raises `MalformedResponseError`, caught
explicitly at `resilience.py:78`. Unlike timeouts, malformed errors are
not counted as transient by default — they indicate the tool is broken,
not busy.

**Recovery.** The retry loop still runs for `MAX_TOOL_RETRIES` attempts
(the mock may succeed on retry), but each failure is logged with
`error_msg` so post-mortem review is possible.

**Final fallback.** Same as timeout — the error dict is surfaced to the
LLM, which is explicitly prompted to reason about failed tool output
rather than trust it.

---

## 3. ReAct Loop Exhaustion (Max Steps Exceeded)

**Scenario.** The agent can't converge on a resolution within its step
budget — it keeps looking up more data, second-guessing, or chasing edge
cases. Classic failure mode of open-ended agents.

**Detection.** The for-loop in `backend/agent/resolver.py:145` is bounded
by `MAX_AGENT_STEPS` (default 16). If the loop exits without the LLM
emitting a terminal action (`send_reply` or `escalate`), control falls
through to the `else` branch at resolver.py:265.

**Recovery.** Rather than dropping the ticket or raising, Sentinel
injects a system-role message telling the LLM: *"You've reached the step
limit. Set status='escalated' in your final JSON — this needs human
review."* A final synthesis call then produces a valid `Resolution` with
full reasoning trace and whatever partial context was gathered. The
ticket is **always** delivered to a human with structured context — it is
never discarded.

**Why this matters.** A naive agent that crashes on step exhaustion loses
all the work it did in steps 1–15. Sentinel preserves every tool call and
every reasoning step in the escalation summary so the human picks up
where the agent left off.

---

## 4. Tool-Call Looping (Redundant Queries)

**Scenario.** The agent calls the same tool with the same arguments in
consecutive steps — typically when confused by ambiguous ticket wording.
Left unchecked, this burns the step budget and the token budget.

**Detection.** `resolver.py:257` caches every successful tool call keyed
by `(tool_name, arguments)`. A duplicate call with identical args is
short-circuited: the cached result is returned without hitting the tool
again.

**Recovery.** The agent sees the cached result and (in practice) stops
repeating. Failed tool calls are *not* cached — those can legitimately
be reissued by the agent as a retry strategy.

**Observability.** The full unique-vs-duplicate ratio is visible in the
audit trail because every call — including cache hits — is recorded.

---

## 5. Guardrail Block on Unsafe Action

**Scenario.** The LLM proposes an action that violates a business rule:
issuing a refund without eligibility verification, refunding above
threshold, replying with no context, or escalating with a one-line
summary.

**Detection.** `backend/agent/guardrails.py` runs pre-execution checks
on the sensitive tools:
- **`issue_refund`** — blocked unless `check_refund_eligibility` was
  called first and returned `eligible=true`, amount ≤
  `HIGH_VALUE_REFUND_THRESHOLD`, and the order has not already been
  refunded in this session.
- **`send_reply`** — blocked if no lookup tool has been called yet
  (prevents replying before gathering context).
- **`escalate`** — blocked if summary < 50 characters (prevents
  low-quality human handoffs).

**Recovery.** The block reason is surfaced to the LLM as a tool result
(e.g. *"issue_refund blocked: amount $450 exceeds threshold $200.
Escalate to human agent."*). The agent then adapts — almost always
switching to `escalate` with the block reason included in its summary.

**Why this is safer than post-hoc review.** Guardrails run *before* the
irreversible action executes. An escalation never results in the refund
actually being issued.

---

## 6. LLM Output Parse Failure

**Scenario.** The model returns a tool call with malformed JSON args,
references a nonexistent tool, or produces a final response that doesn't
match the expected schema.

**Detection.**
- Unknown tool names are caught at `resolver.py:243` and returned as an
  `{"error": "unknown_tool"}` result — no crash, the agent sees the
  mistake in history.
- Argument parsing errors surface as `ToolExecutionError` through
  `resilience.py:84`.
- Final synthesis is schema-validated via `Resolution` (Pydantic model);
  a malformed final response is caught and the ticket falls back to
  "escalated" with the parse error preserved.

**Recovery.** In every case the LLM gets to see what went wrong — either
via a tool-result message or via a correction prompt on the next synthesis
attempt. No silent data loss.

---

## 7. Unrecoverable Ticket (Dead Letter)

**Scenario.** A ticket fails in a way none of the above paths can
recover — e.g. the LLM API itself is down, or the ticket payload is
corrupt at ingestion.

**Detection.** Exceptions bubbling past the `Resolver.resolve()` boundary
are caught by the worker pool in `backend/ingestion/worker_pool.py`.

**Recovery.** The ticket is written to
`backend/ingestion/dead_letter.py` → `logs/dead_letter.jsonl` with:
- original ticket id
- failure reason
- last error message
- attempt count
- UTC timestamp

This gives operations a single, tailable file to triage pipeline-level
failures — distinct from per-ticket escalations, which go to human
support.

**Current demo state.** `logs/dead_letter.jsonl` is 0 bytes after the
latest 20-ticket run — zero pipeline-level failures, 100% of tickets
produced a structured resolution.

---

## Summary Matrix

| Failure                   | Detected in                        | Recovery strategy                          | Ticket still delivered? |
|---------------------------|------------------------------------|--------------------------------------------|-------------------------|
| Tool timeout              | `resilience.py:57` (asyncio)       | Retry w/ exponential backoff + jitter      | ✅ (LLM sees error)     |
| Malformed tool response   | `resilience.py:78`                 | Retry, then surface as error to LLM        | ✅ (LLM adapts)         |
| Max agent steps exceeded  | `resolver.py:265`                  | Force-escalate with full reasoning trace   | ✅ (human escalation)   |
| Repeated tool calls       | `resolver.py:257` (seen_calls)     | Return cached result                       | ✅                      |
| Guardrail block           | `guardrails.py`                    | Surface block reason → agent adapts        | ✅                      |
| LLM output parse failure  | `resolver.py:243` / Pydantic       | Return error to LLM; fallback to escalated | ✅                      |
| Unrecoverable exception   | `worker_pool.py` → `dead_letter`   | Persist to `logs/dead_letter.jsonl`        | ✅ (operator visibility)|

Every row ends in "yes". That is the design invariant.
