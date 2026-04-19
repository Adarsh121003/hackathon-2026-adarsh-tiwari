"""REST API routes for Sentinel.

Endpoints cover the full lifecycle: ingest → query tickets → metrics → export.
All responses are JSON.  The /ingest endpoint triggers async background
processing so it returns immediately with a run_id.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, UploadFile, File
from pydantic import ValidationError

from backend.audit import exporters, store as audit_store
from backend.api.streams import push_event
from backend.core.models import Ticket
from backend.ingestion.worker_pool import run_worker_pool
from backend.tools import datastore as ds_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

MAX_UPLOAD_TICKETS = 200

# Shared state for in-progress/completed runs
_runs: dict[str, dict] = {}


def _load_tickets() -> list[Ticket]:
    path = ds_module.get_active_tickets_path()
    if not path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Active dataset file missing: {path.name}",
        )
    raw = json.loads(path.read_text())
    return [Ticket.model_validate(t) for t in raw]


@router.get("/health")
async def health():
    """Liveness check."""
    return {"status": "ok", "service": "sentinel"}


@router.post("/ingest")
async def ingest_tickets(background_tasks: BackgroundTasks):
    """Trigger processing of all tickets from tickets.json."""
    import uuid

    run_id = str(uuid.uuid4())[:8]
    tickets = _load_tickets()
    _runs[run_id] = {"status": "running", "total": len(tickets), "completed": 0}

    async def _run():
        resolutions = await run_worker_pool(tickets, on_progress=push_event)
        for r in resolutions:
            await audit_store.save_resolution(r)
        _runs[run_id]["status"] = "done"
        _runs[run_id]["completed"] = len(resolutions)
        logger.info("Ingest run %s complete: %d resolutions", run_id, len(resolutions))

    background_tasks.add_task(_run)
    return {"run_id": run_id, "total_tickets": len(tickets), "status": "running"}


@router.get("/ingest/{run_id}")
async def ingest_status(run_id: str):
    """Check status of a processing run."""
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/tickets")
async def list_tickets():
    """List all processed tickets with summary fields."""
    return await audit_store.list_resolutions()


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get full resolution trace for a single ticket."""
    data = await audit_store.get_resolution(ticket_id)
    if not data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return data


@router.get("/metrics")
async def metrics():
    """Aggregate metrics: resolution rate, avg tool calls, latency, confidence."""
    return await audit_store.get_metrics()


@router.get("/audit/log")
async def audit_log():
    """Export the full audit JSONL as a JSON array."""
    from backend.core.config import settings

    path: Path = settings.logs_dir / "audit_log.jsonl"
    if not path.exists():
        return []
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return lines


@router.post("/export")
async def export_audit():
    """Generate and return the path of the submission audit_log.json."""
    out_path = await exporters.export_submission_audit_log()
    return {"path": str(out_path), "status": "exported"}


# ---------------------------------------------------------------------------
# Dataset management
# ---------------------------------------------------------------------------

@router.get("/datasets")
async def list_datasets():
    """Return the dataset manifest (available datasets + active pointer)."""
    try:
        return ds_module.load_manifest()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/datasets/switch")
async def switch_dataset(payload: dict = Body(...)):
    """Switch the active dataset and clear the prior run's audit store.

    Body: {"dataset_id": "ksolves_20"}
    """
    dataset_id = (payload or {}).get("dataset_id")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")
    try:
        entry = ds_module.switch_dataset(dataset_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await audit_store.clear_all()
    return {"active": entry, "cleared": True}


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a custom ticket dataset (JSON array).

    Validates each ticket against the Ticket schema, enforces id uniqueness,
    caps at MAX_UPLOAD_TICKETS, then registers + activates the dataset.
    """
    raw_bytes = await file.read()
    try:
        tickets_raw = json.loads(raw_bytes)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e.msg}")

    if not isinstance(tickets_raw, list):
        raise HTTPException(status_code=400, detail="Top-level JSON must be an array")
    if not tickets_raw:
        raise HTTPException(status_code=400, detail="Ticket array is empty")
    if len(tickets_raw) > MAX_UPLOAD_TICKETS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many tickets ({len(tickets_raw)}); max {MAX_UPLOAD_TICKETS}",
        )

    seen_ids: set[str] = set()
    errors: list[str] = []
    for idx, item in enumerate(tickets_raw):
        try:
            t = Ticket.model_validate(item)
        except ValidationError as e:
            errors.append(f"ticket[{idx}]: {e.errors()[0]['msg']}")
            continue
        if t.ticket_id in seen_ids:
            errors.append(f"ticket[{idx}]: duplicate ticket_id {t.ticket_id!r}")
        seen_ids.add(t.ticket_id)

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Validation failed", "errors": errors[:20]},
        )

    display_name = Path(file.filename or "custom").stem[:40] or "custom"
    entry = ds_module.register_uploaded_dataset(
        tickets_raw,
        name=f"Custom: {display_name}",
        description=f"Uploaded via UI ({len(tickets_raw)} tickets)",
    )
    ds_module.switch_dataset(entry["id"])
    await audit_store.clear_all()
    return {"active": entry, "count": len(tickets_raw), "cleared": True}
