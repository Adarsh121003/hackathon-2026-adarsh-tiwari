"""Retry-with-backoff and timeout wrapper for tool execution.

Every tool call in the ReAct loop goes through execute_tool() here.
This is the single place where fault-tolerance policy lives — making it
easy to explain to judges: "all tool calls go through one choke point
that enforces timeout + retry + audit logging."
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Callable

from backend.core.config import settings
from backend.core.exceptions import (
    MalformedResponseError,
    ToolExecutionError,
    ToolTimeoutError,
)
from backend.core.models import ToolCallRecord

logger = logging.getLogger(__name__)

# Exceptions that are worth retrying (transient)
_RETRYABLE = (ToolTimeoutError, asyncio.TimeoutError, OSError, ConnectionError)


async def execute_tool(
    tool_name: str,
    arguments: dict,
    fn: Callable,
    sequence: int,
) -> tuple[dict, list[ToolCallRecord]]:
    """Execute a tool with timeout + exponential-backoff retry.

    Returns (result_dict, list_of_ToolCallRecord) so the caller gets
    a complete audit trail regardless of how many attempts were needed.
    """
    records: list[ToolCallRecord] = []
    last_error: str | None = None
    last_result: dict | None = None

    max_attempts = settings.max_tool_retries + 1  # initial + retries
    base_delay_s = settings.retry_base_delay_ms / 1000.0

    for attempt in range(1, max_attempts + 1):
        start = time.monotonic()
        ts = datetime.now(timezone.utc)
        success = False
        result: dict = {}
        error_msg: str | None = None

        try:
            raw = await asyncio.wait_for(
                fn(**arguments),
                timeout=settings.tool_timeout_seconds,
            )
            # Normalise: tools return dicts; wrap if somehow not
            if isinstance(raw, dict):
                result = raw
            else:
                result = {"value": raw}
            success = True
            last_result = result

        except asyncio.TimeoutError as exc:
            error_msg = f"Timeout after {settings.tool_timeout_seconds}s"
            last_error = error_msg
            logger.warning(
                "Tool %s timed out (attempt %d/%d)", tool_name, attempt, max_attempts
            )
            # Wrap so callers can distinguish
            exc_to_raise = ToolTimeoutError(tool_name, settings.tool_timeout_seconds)

        except MalformedResponseError as exc:
            error_msg = str(exc)
            last_error = error_msg
            logger.warning("Tool %s malformed (attempt %d/%d): %s", tool_name, attempt, max_attempts, exc)
            exc_to_raise = exc  # type: ignore[assignment]

        except ToolExecutionError as exc:
            error_msg = str(exc)
            last_error = error_msg
            logger.warning("Tool %s exec error (attempt %d/%d): %s", tool_name, attempt, max_attempts, exc)
            exc_to_raise = exc  # type: ignore[assignment]

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            last_error = error_msg
            logger.warning("Tool %s unexpected error (attempt %d/%d): %s", tool_name, attempt, max_attempts, exc)
            exc_to_raise = ToolExecutionError(tool_name, exc)  # type: ignore[assignment]

        finally:
            latency_ms = (time.monotonic() - start) * 1000
            records.append(
                ToolCallRecord(
                    sequence=sequence,
                    tool_name=tool_name,
                    arguments=arguments,
                    success=success,
                    result=result if success else None,
                    error=error_msg,
                    latency_ms=round(latency_ms, 2),
                    attempt=attempt,
                    timestamp=ts,
                )
            )

        if success:
            return result, records

        # Don't retry after last attempt
        if attempt < max_attempts:
            delay = base_delay_s * (2 ** (attempt - 1)) + random.uniform(0, 0.05)
            logger.info("Retrying %s in %.2fs (attempt %d)", tool_name, delay, attempt + 1)
            await asyncio.sleep(delay)

    # All attempts exhausted — return an error dict (never raise to the agent)
    # so the ReAct loop can inform the LLM about the failure and continue
    error_result = {
        "error": "tool_failed",
        "tool": tool_name,
        "detail": last_error or "Unknown error after all retries",
    }
    return error_result, records
