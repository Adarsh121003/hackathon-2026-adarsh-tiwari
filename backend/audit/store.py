"""SQLite-backed audit store for queryable resolution data.

The JSONL file is the canonical record; SQLite is derived from it for fast
API queries.  Using aiosqlite keeps us fully async throughout.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from backend.core.config import settings
from backend.core.models import Resolution

logger = logging.getLogger(__name__)

_DB_PATH: Path = settings.db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS resolutions (
    ticket_id     TEXT PRIMARY KEY,
    status        TEXT,
    category      TEXT,
    urgency       TEXT,
    confidence    REAL,
    tool_call_cnt INTEGER,
    latency_ms    REAL,
    started_at    TEXT,
    completed_at  TEXT,
    flags         TEXT,
    full_json     TEXT
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id    TEXT,
    sequence     INTEGER,
    tool_name    TEXT,
    success      INTEGER,
    latency_ms   REAL,
    attempt      INTEGER,
    timestamp    TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT,
    event_type   TEXT,
    ticket_id    TEXT,
    payload      TEXT
);
"""


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("Audit DB initialised at %s", _DB_PATH)


async def clear_all() -> None:
    """Truncate all audit tables and rotate the JSONL/dead-letter files.

    Called when switching datasets so metrics reflect only the new run.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(
            "DELETE FROM resolutions; DELETE FROM tool_calls; DELETE FROM audit_events;"
        )
        await db.commit()
    for name in ("audit_log.jsonl", "dead_letter.jsonl"):
        p = settings.logs_dir / name
        if p.exists():
            p.write_text("")
    logger.info("Audit store cleared")


async def save_resolution(resolution: Resolution) -> None:
    """Upsert a resolution into the SQLite store."""
    full_json = resolution.model_dump_json()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO resolutions
              (ticket_id, status, category, urgency, confidence,
               tool_call_cnt, latency_ms, started_at, completed_at, flags, full_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                resolution.ticket_id,
                str(resolution.status),
                str(resolution.category),
                str(resolution.urgency),
                resolution.confidence,
                len(resolution.tool_calls),
                resolution.total_latency_ms,
                resolution.started_at.isoformat() if resolution.started_at else None,
                resolution.completed_at.isoformat() if resolution.completed_at else None,
                json.dumps(resolution.flags),
                full_json,
            ),
        )
        for tc in resolution.tool_calls:
            await db.execute(
                """
                INSERT INTO tool_calls
                  (ticket_id, sequence, tool_name, success, latency_ms, attempt, timestamp)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    resolution.ticket_id,
                    tc.sequence,
                    tc.tool_name,
                    1 if tc.success else 0,
                    tc.latency_ms,
                    tc.attempt,
                    tc.timestamp.isoformat(),
                ),
            )
        await db.commit()


async def get_resolution(ticket_id: str) -> dict | None:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT full_json FROM resolutions WHERE ticket_id = ?", (ticket_id,)
        ) as cur:
            row = await cur.fetchone()
    if row:
        return json.loads(row["full_json"])
    return None


async def list_resolutions() -> list[dict]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT ticket_id, status, category, urgency, confidence, tool_call_cnt, latency_ms FROM resolutions ORDER BY ticket_id"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_metrics() -> dict:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT status, COUNT(*) as cnt FROM resolutions GROUP BY status"
        ) as cur:
            status_rows = await cur.fetchall()
        async with db.execute(
            "SELECT AVG(tool_call_cnt) as avg_tools, AVG(latency_ms) as avg_ms, AVG(confidence) as avg_conf FROM resolutions"
        ) as cur:
            agg = await cur.fetchone()
        async with db.execute("SELECT COUNT(*) as total FROM resolutions") as cur:
            total_row = await cur.fetchone()

    status_breakdown = {r["status"]: r["cnt"] for r in status_rows}
    total = total_row["total"] if total_row else 0
    resolved = status_breakdown.get("resolved", 0)

    return {
        "total_tickets": total,
        "resolution_rate": round(resolved / total, 3) if total else 0,
        "status_breakdown": status_breakdown,
        "avg_tool_calls": round(agg["avg_tools"] or 0, 2),
        "avg_latency_ms": round(agg["avg_ms"] or 0, 2),
        "avg_confidence": round(agg["avg_conf"] or 0, 3),
    }
