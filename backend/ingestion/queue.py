"""Priority-aware async ticket queue.

Urgent tickets are processed first by mapping urgency to numeric priority.
The asyncio.PriorityQueue ensures the worker pool always picks the highest-
priority waiting ticket when a worker slot becomes free.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from backend.core.models import Ticket, Triage, Urgency

logger = logging.getLogger(__name__)

_URGENCY_PRIORITY: dict[str, int] = {
    Urgency.urgent: 0,
    Urgency.high: 1,
    Urgency.medium: 2,
    Urgency.low: 3,
}


@dataclass(order=True)
class PrioritisedTicket:
    priority: int
    ticket: Ticket = field(compare=False)


class TicketQueue:
    """Asyncio-backed priority queue for support tickets."""

    def __init__(self) -> None:
        self._q: asyncio.PriorityQueue[PrioritisedTicket] = asyncio.PriorityQueue()

    async def put(self, ticket: Ticket, triage: Optional[Triage] = None) -> None:
        priority = _URGENCY_PRIORITY.get(
            triage.urgency if triage else Urgency.medium, 2
        )
        await self._q.put(PrioritisedTicket(priority=priority, ticket=ticket))
        logger.debug("Queued ticket %s priority=%d", ticket.ticket_id, priority)

    async def get(self) -> Ticket:
        item = await self._q.get()
        return item.ticket

    def task_done(self) -> None:
        self._q.task_done()

    def qsize(self) -> int:
        return self._q.qsize()

    async def join(self) -> None:
        await self._q.join()
