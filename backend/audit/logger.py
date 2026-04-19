"""Append-only JSONL audit logger.

Every significant event in the pipeline is logged here: triage, each tool
call, guardrail triggers, and final resolution.  The JSONL format means it
can be streamed, grepped, and imported into any analysis tool without
schema migration.

asyncio.Lock ensures file writes are atomic even when many tickets are
in-flight simultaneously.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.core.config import settings

logger = logging.getLogger(__name__)


class AuditLogger:
    """Thread-safe append-only audit logger."""

    def __init__(self) -> None:
        self._path: Path = settings.logs_dir / "audit_log.jsonl"
        self._lock = asyncio.Lock()

    async def log_event(
        self,
        event_type: str,
        ticket_id: str,
        payload: dict,
    ) -> None:
        """Append a single audit event as a JSONL line."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "ticket_id": ticket_id,
            **payload,
        }
        line = json.dumps(entry, default=str) + "\n"
        async with self._lock:
            with self._path.open("a") as fh:
                fh.write(line)


# Module-level singleton imported everywhere
audit_logger = AuditLogger()
