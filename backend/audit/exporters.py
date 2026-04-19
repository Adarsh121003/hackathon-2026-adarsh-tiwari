"""Submission artifact exporter.

Produces audit_log.json — the file submitted to judges — covering all
processed tickets with: classification, tool call chain, reasoning trace,
and final resolution.  Output is deterministically ordered by ticket_id.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import aiosqlite

from backend.core.config import settings

logger = logging.getLogger(__name__)

_DB_PATH = settings.db_path


async def export_submission_audit_log(
    output_path: Path | None = None,
) -> Path:
    """Read all resolved tickets from SQLite and write audit_log.json.

    Returns the path of the written file.
    """
    if output_path is None:
        output_path = Path(__file__).resolve().parent.parent.parent / "audit_log.json"

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT full_json FROM resolutions ORDER BY ticket_id"
        ) as cur:
            rows = await cur.fetchall()

    resolutions = []
    for row in rows:
        try:
            r = json.loads(row["full_json"])
            resolutions.append(_flatten_for_submission(r))
        except Exception as exc:
            logger.warning("Could not parse row: %s", exc)

    output = {
        "sentinel_version": "1.0.0",
        "export_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "total_tickets": len(resolutions),
        "resolutions": resolutions,
    }

    output_path.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Audit log exported: %s (%d tickets)", output_path, len(resolutions))
    return output_path


def _flatten_for_submission(r: dict) -> dict:
    """Project a Resolution dict into the submission-friendly shape."""
    return {
        "ticket_id": r.get("ticket_id"),
        "status": r.get("status"),
        "category": r.get("category"),
        "urgency": r.get("urgency"),
        "confidence": r.get("confidence"),
        "actions_taken": r.get("actions_taken", []),
        "tool_call_count": len(r.get("tool_calls", [])),
        "tool_calls": [
            {
                "sequence": tc.get("sequence"),
                "tool_name": tc.get("tool_name"),
                "success": tc.get("success"),
                "latency_ms": tc.get("latency_ms"),
                "attempt": tc.get("attempt"),
            }
            for tc in r.get("tool_calls", [])
        ],
        "reasoning_trace": r.get("reasoning_trace", []),
        "final_customer_message": r.get("final_customer_message", ""),
        "escalation_summary": r.get("escalation_summary"),
        "flags": r.get("flags", []),
        "total_latency_ms": r.get("total_latency_ms"),
        "started_at": r.get("started_at"),
        "completed_at": r.get("completed_at"),
    }
