"""CLI demo runner — the single command that produces all submission artifacts.

Usage:
    python -m backend.run_demo

Flow:
  1. Validate config and load data
  2. Process all 20 tickets concurrently via worker_pool
  3. Persist results to SQLite
  4. Export audit_log.json to repo root
  5. Print rich summary table + metrics
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import box

from backend.audit import exporters, store as audit_store
from backend.audit.store import init_db
from backend.core.config import settings
from backend.core.logging_setup import setup_logging
from backend.core.models import ResolutionStatus, Ticket
from backend.ingestion.worker_pool import run_worker_pool
from backend.tools import datastore as ds_module
from backend.tools import kb_search

console = Console()
setup_logging(logging.WARNING)  # suppress routine logs in demo; keep ERRORs


def _load_tickets() -> list[Ticket]:
    """Load the currently-active dataset declared in dataset_manifest.json."""
    path = ds_module.get_active_tickets_path()
    raw = json.loads(path.read_text())
    return [Ticket.model_validate(t) for t in raw]


def _status_color(status: str) -> str:
    return {
        "resolved": "green",
        "escalated": "yellow",
        "info_requested": "cyan",
        "failed": "red",
    }.get(status, "white")


async def _main() -> int:
    # ── Banner ─────────────────────────────────────────────────────────
    console.print(
        Panel.fit(
            "[bold cyan]SENTINEL[/bold cyan]  ·  Autonomous Support Agent\n"
            f"[dim]Provider:[/dim] [bold]{settings.llm_provider.upper()}[/bold]  "
            f"[dim]Model:[/dim] [bold]{ {'groq': settings.groq_model, 'anthropic': settings.anthropic_model, 'openai': settings.openai_model}.get(settings.llm_provider, settings.groq_model) }[/bold]\n"
            f"[dim]Concurrency:[/dim] {settings.max_concurrent_tickets}  "
            f"[dim]Max Steps:[/dim] {settings.max_agent_steps}  "
            f"[dim]Confidence Threshold:[/dim] {settings.confidence_threshold}",
            title="ShopWave Demo",
            border_style="cyan",
        )
    )

    # ── Startup ────────────────────────────────────────────────────────
    try:
        settings.validate()
    except ValueError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        return 1

    ds_module.store.load()
    kb_search.build_index(ds_module.store.kb_text)
    await init_db()

    tickets = _load_tickets()
    console.print(f"\n[bold]Loaded {len(tickets)} tickets.[/bold] Processing now...\n")

    # ── Process ────────────────────────────────────────────────────────
    completed_events: list[str] = []

    def on_progress(ticket_id: str, payload: dict) -> None:
        if payload.get("stage") == "resolution_complete":
            status = payload.get("status", "?")
            color = _status_color(status)
            completed_events.append(
                f"[dim]{ticket_id}[/dim] → [{color}]{status}[/{color}]"
            )

    wall_start = time.monotonic()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Processing tickets...", total=None)
        resolutions = await run_worker_pool(tickets, on_progress=on_progress)
        progress.update(task, completed=len(resolutions))

    total_wall = time.monotonic() - wall_start

    # ── Persist ────────────────────────────────────────────────────────
    for r in resolutions:
        await audit_store.save_resolution(r)

    # ── Summary Table ──────────────────────────────────────────────────
    table = Table(
        title="Resolution Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Ticket ID", style="dim", width=12)
    table.add_column("Category", width=18)
    table.add_column("Status", width=14)
    table.add_column("Confidence", justify="right", width=10)
    table.add_column("Tool Calls", justify="right", width=10)
    table.add_column("Latency ms", justify="right", width=11)

    for r in sorted(resolutions, key=lambda x: x.ticket_id):
        color = _status_color(str(r.status))
        table.add_row(
            r.ticket_id,
            str(r.category).replace("TicketCategory.", ""),
            f"[{color}]{str(r.status).replace('ResolutionStatus.', '')}[/{color}]",
            f"{r.confidence:.2f}",
            str(len(r.tool_calls)),
            f"{r.total_latency_ms:.0f}",
        )

    console.print(table)

    # ── Metrics ────────────────────────────────────────────────────────
    metrics = await audit_store.get_metrics()
    resolved = sum(1 for r in resolutions if r.status == ResolutionStatus.resolved)
    escalated = sum(1 for r in resolutions if r.status == ResolutionStatus.escalated)
    failed = sum(1 for r in resolutions if r.status == ResolutionStatus.failed)
    avg_tools = (
        sum(len(r.tool_calls) for r in resolutions) / len(resolutions)
        if resolutions else 0
    )

    console.print(
        Panel(
            f"[bold green]Resolved:[/bold green]  {resolved}/{len(resolutions)}  "
            f"({100*resolved//len(resolutions) if resolutions else 0}%)\n"
            f"[bold yellow]Escalated:[/bold yellow] {escalated}\n"
            f"[bold red]Failed:[/bold red]    {failed}\n"
            f"[bold]Avg Tool Calls:[/bold] {avg_tools:.1f}\n"
            f"[bold]Avg Confidence:[/bold] {metrics.get('avg_confidence', 0):.3f}\n"
            f"[bold]Wall Time:[/bold] {total_wall:.1f}s",
            title="Metrics",
            border_style="magenta",
        )
    )

    # ── Export audit log ───────────────────────────────────────────────
    out_path = await exporters.export_submission_audit_log()
    console.print(
        f"\n[bold green]✓[/bold green] Submission artifact: [underline]{out_path}[/underline]"
    )
    console.print(
        f"[bold green]✓[/bold green] Audit JSONL: [underline]{settings.logs_dir / 'audit_log.jsonl'}[/underline]"
    )
    console.print(
        f"[bold green]✓[/bold green] SQLite DB:   [underline]{settings.db_path}[/underline]\n"
    )

    return 0 if failed == 0 else 1


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
