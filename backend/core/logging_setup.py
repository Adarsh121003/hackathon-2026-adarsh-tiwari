"""Structured logging with per-ticket correlation.

The ContextVar current_ticket_id is set by the worker before processing each
ticket, so every log line emitted anywhere in that async task automatically
includes the ticket ID.  This is critical for debugging concurrent runs where
multiple tickets are in-flight simultaneously.
"""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

# ---------------------------------------------------------------------------
# Correlation context
# ---------------------------------------------------------------------------

current_ticket_id: ContextVar[str] = ContextVar("current_ticket_id", default="-")


# ---------------------------------------------------------------------------
# Log filter that injects ticket_id into every record
# ---------------------------------------------------------------------------


class TicketFilter(logging.Filter):
    """Injects the active ticket_id into each LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.ticket_id = current_ticket_id.get("-")  # type: ignore[attr-defined]
        return True


# ---------------------------------------------------------------------------
# Public setup function
# ---------------------------------------------------------------------------

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-7s | ticket=%(ticket_id)s | %(name)s | %(message)s"
)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with ticket correlation; silence noisy third-party libs."""
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid adding duplicate handlers on repeated calls (e.g. during tests)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        handler.addFilter(TicketFilter())
        root.addHandler(handler)
    else:
        # Ensure the filter is attached to existing handlers
        for h in root.handlers:
            if not any(isinstance(f, TicketFilter) for f in h.filters):
                h.addFilter(TicketFilter())

    # Silence noisy third-party loggers so they don't pollute audit output
    for noisy in ("httpx", "httpcore", "anthropic", "groq", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
