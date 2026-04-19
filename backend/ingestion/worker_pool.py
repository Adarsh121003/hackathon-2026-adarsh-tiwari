"""Semaphore-bounded concurrent worker pool.

asyncio.Semaphore limits simultaneous LLM calls to MAX_CONCURRENT_TICKETS
to avoid rate-limit exhaustion.  Each worker runs the full triage → resolve
→ audit pipeline, and any failure goes to the dead letter queue rather than
bubbling up as an unhandled exception.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from backend.agent.resolver import ResolverAgent
from backend.agent.triage import TriageAgent
from backend.audit.logger import audit_logger
from backend.core.config import settings
from backend.core.exceptions import LLMRateLimitError
from backend.core.logging_setup import current_ticket_id
from backend.core.models import Resolution, ResolutionStatus, Ticket, TicketCategory, Urgency
from backend.ingestion.dead_letter import dead_letter

logger = logging.getLogger(__name__)

_triage_agent = TriageAgent()
_resolver_agent = ResolverAgent()

_WORKER_RATE_LIMIT_RETRIES = 2
_WORKER_RATE_LIMIT_SLEEP = 65.0  # Groq TPM window is 60s; +5s buffer


async def _process_one(
    ticket: Ticket,
    sem: asyncio.Semaphore,
    on_progress: Callable[[str, dict], None] | None = None,
    stagger_delay: float = 0.0,
) -> Resolution:
    """Process a single ticket under the semaphore.

    LLMRateLimitError gets up to 2 worker-level retries with a 65s backoff
    (one full Groq TPM window) before being sent to the dead-letter queue.
    All other exceptions go to dead-letter immediately — we don't retry on
    logic errors.  stagger_delay spreads concurrent starts to avoid bursting
    all tokens at the same instant.
    """
    if stagger_delay > 0:
        await asyncio.sleep(stagger_delay)
    async with sem:
        token = current_ticket_id.set(ticket.ticket_id)
        try:
            return await _process_with_rate_limit_retry(ticket, on_progress)
        finally:
            current_ticket_id.reset(token)


async def _process_with_rate_limit_retry(
    ticket: Ticket,
    on_progress: Callable[[str, dict], None] | None,
) -> Resolution:
    """Run triage+resolve, retrying up to 2 times on LLMRateLimitError."""
    last_exc: Exception | None = None

    for attempt in range(1, _WORKER_RATE_LIMIT_RETRIES + 2):  # 1, 2, 3
        try:
            logger.info("Worker starting: ticket=%s (attempt %d)", ticket.ticket_id, attempt)
            return await _run_pipeline(ticket, on_progress)

        except LLMRateLimitError as exc:
            last_exc = exc
            if attempt <= _WORKER_RATE_LIMIT_RETRIES:
                logger.warning(
                    "Worker retrying ticket %s after rate limit (worker attempt %d/%d)",
                    ticket.ticket_id,
                    attempt,
                    _WORKER_RATE_LIMIT_RETRIES,
                )
                await asyncio.sleep(_WORKER_RATE_LIMIT_SLEEP)
                continue
            # All retries exhausted — fall through to dead-letter

        except Exception as exc:
            # Non-rate-limit errors: dead-letter immediately, no retry
            last_exc = exc
            break

    # Reached here only on exhausted retries or non-retryable exception
    logger.exception("Worker failed for ticket %s: %s", ticket.ticket_id, last_exc)
    await dead_letter.record(
        ticket_id=ticket.ticket_id,
        reason="unhandled_exception",
        last_error=str(last_exc),
    )
    await audit_logger.log_event(
        "resolution_failed",
        ticket.ticket_id,
        {"error": str(last_exc)},
    )
    from datetime import datetime, timezone
    return Resolution(
        ticket_id=ticket.ticket_id,
        status=ResolutionStatus.failed,
        category=TicketCategory.other,
        urgency=Urgency.medium,
        confidence=0.0,
        flags=[f"Fatal error: {last_exc}"],
        started_at=datetime.now(timezone.utc),
    )


async def _run_pipeline(
    ticket: Ticket,
    on_progress: Callable[[str, dict], None] | None,
) -> Resolution:
    """Core triage → resolve → audit pipeline (no retry logic here)."""
    # ── Triage ──────────────────────────────────────────────────────
    triage = await _triage_agent.classify(ticket)
    await audit_logger.log_event(
        "triage_completed",
        ticket.ticket_id,
        {
            "category": triage.category,
            "urgency": triage.urgency,
            "auto_resolvable": triage.auto_resolvable,
            "confidence": triage.confidence,
        },
    )

    if on_progress:
        on_progress(
            ticket.ticket_id,
            {"stage": "triage_complete", "category": str(triage.category), "urgency": str(triage.urgency)},
        )

    # ── Resolve ──────────────────────────────────────────────────────
    resolution = await _resolver_agent.resolve(ticket, triage)

    await audit_logger.log_event(
        "resolution_completed",
        ticket.ticket_id,
        {
            "status": resolution.status,
            "confidence": resolution.confidence,
            "tool_calls": len(resolution.tool_calls),
            "total_latency_ms": resolution.total_latency_ms,
        },
    )

    if on_progress:
        on_progress(
            ticket.ticket_id,
            {
                "stage": "resolution_complete",
                "status": str(resolution.status),
                "confidence": resolution.confidence,
            },
        )

    logger.info(
        "Worker done: ticket=%s status=%s confidence=%.2f latency=%.0fms",
        ticket.ticket_id,
        resolution.status,
        resolution.confidence,
        resolution.total_latency_ms,
    )
    return resolution


async def run_worker_pool(
    tickets: list[Ticket],
    concurrency: int | None = None,
    on_progress: Callable[[str, dict], None] | None = None,
) -> list[Resolution]:
    """Process all tickets concurrently, respecting the concurrency limit.

    Returns all resolutions (including failures) in the same order as input.
    """
    limit = concurrency or settings.max_concurrent_tickets
    sem = asyncio.Semaphore(limit)
    logger.info("Worker pool started: %d tickets, concurrency=%d", len(tickets), limit)

    # Stagger starts by 3s per ticket so concurrent workers don't burst tokens simultaneously
    tasks = [
        _process_one(ticket, sem, on_progress, stagger_delay=i * 3.0)
        for i, ticket in enumerate(tickets)
    ]
    resolutions: list[Resolution] = await asyncio.gather(*tasks, return_exceptions=False)

    resolved = sum(1 for r in resolutions if r.status == ResolutionStatus.resolved)
    escalated = sum(1 for r in resolutions if r.status == ResolutionStatus.escalated)
    failed = sum(1 for r in resolutions if r.status == ResolutionStatus.failed)
    logger.info(
        "Worker pool done: resolved=%d escalated=%d failed=%d",
        resolved, escalated, failed,
    )
    return list(resolutions)
