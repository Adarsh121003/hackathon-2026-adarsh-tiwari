"""In-memory DataStore backed by the fixture JSON files.

Single source of truth for all runtime data.  Using asyncio.Lock on mutations
prevents race conditions when multiple tickets are processed concurrently.
The idempotency registry ensures we never double-refund even if an agent
retries a tool call.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from backend.core.config import settings
from backend.core.models import Customer, Order, Product

logger = logging.getLogger(__name__)


class DataStore:
    """Loads and indexes all fixture data; tracks performed actions for idempotency."""

    def __init__(self) -> None:
        self._customers: list[Customer] = []
        self._orders: list[Order] = []
        self._products: list[Product] = []
        self._kb_text: str = ""

        # Indexed for O(1) lookups
        self._customers_by_email: dict[str, Customer] = {}
        self._customers_by_id: dict[str, Customer] = {}
        self._orders_by_id: dict[str, Order] = {}
        self._products_by_id: dict[str, Product] = {}

        # Mutable order state (refund_status, order_status)
        self._order_overrides: dict[str, dict] = {}

        # Idempotency registry: ticket_id → set of action_keys already performed
        self._performed_actions: dict[str, set[str]] = {}

        self._lock = asyncio.Lock()
        self._loaded = False

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Parse all fixture files.  Fails fast on schema violations."""
        data_dir: Path = settings.data_dir
        logger.info("Loading datastore from %s", data_dir)

        raw_customers = json.loads((data_dir / "customers.json").read_text())
        self._customers = [Customer.model_validate(c) for c in raw_customers]

        raw_orders = json.loads((data_dir / "orders.json").read_text())
        self._orders = [Order.model_validate(o) for o in raw_orders]

        raw_products = json.loads((data_dir / "products.json").read_text())
        self._products = [Product.model_validate(p) for p in raw_products]

        self._kb_text = (data_dir / "knowledge-base.md").read_text()

        # Build indexes
        self._customers_by_email = {c.email: c for c in self._customers}
        self._customers_by_id = {c.customer_id: c for c in self._customers}
        self._orders_by_id = {o.order_id: o for o in self._orders}
        self._products_by_id = {p.product_id: p for p in self._products}

        self._loaded = True
        logger.info(
            "DataStore loaded: %d customers, %d orders, %d products",
            len(self._customers),
            len(self._orders),
            len(self._products),
        )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        return self._customers_by_email.get(email)

    def get_customer_by_id(self, customer_id: str) -> Optional[Customer]:
        return self._customers_by_id.get(customer_id)

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders_by_id.get(order_id)

    def get_product(self, product_id: str) -> Optional[Product]:
        return self._products_by_id.get(product_id)

    def find_orders_by_email(self, email: str) -> list[Order]:
        """Return all orders belonging to the customer with the given email."""
        customer = self._customers_by_email.get(email)
        if not customer:
            return []
        return [o for o in self._orders if o.customer_id == customer.customer_id]

    def get_effective_order(self, order_id: str) -> Optional[dict]:
        """Return order as dict, merging any runtime overrides."""
        order = self._orders_by_id.get(order_id)
        if not order:
            return None
        base = order.model_dump()
        base.update(self._order_overrides.get(order_id, {}))
        return base

    @property
    def kb_text(self) -> str:
        return self._kb_text

    # ------------------------------------------------------------------
    # Mutating ops (async + lock)
    # ------------------------------------------------------------------

    async def update_order_status(self, order_id: str, status: str) -> None:
        async with self._lock:
            self._order_overrides.setdefault(order_id, {})["status"] = status

    async def mark_refunded(self, order_id: str, refund_id: str) -> None:
        async with self._lock:
            self._order_overrides.setdefault(order_id, {}).update(
                {"refund_status": "refunded", "refund_id": refund_id}
            )

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def mark_performed(self, ticket_id: str, action_key: str) -> bool:
        """Record that action_key was performed for ticket_id.

        Returns True if this is the first time (action should proceed),
        False if already performed (caller should skip / return cached result).
        """
        bucket = self._performed_actions.setdefault(ticket_id, set())
        if action_key in bucket:
            return False
        bucket.add(action_key)
        return True


# Module-level singleton
store = DataStore()


# ---------------------------------------------------------------------------
# Dataset manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    """Read the dataset manifest from disk."""
    path = settings.dataset_manifest_path
    if not path.exists():
        raise FileNotFoundError(f"dataset_manifest.json not found at {path}")
    return json.loads(path.read_text())


def write_manifest(manifest: dict) -> None:
    """Persist the dataset manifest."""
    settings.dataset_manifest_path.write_text(json.dumps(manifest, indent=2))


def _resolve_dataset_entry(manifest: dict, dataset_id: str) -> dict:
    for entry in manifest.get("available", []):
        if entry["id"] == dataset_id:
            return entry
    raise KeyError(f"Unknown dataset id: {dataset_id}")


def get_active_dataset() -> dict:
    """Return the active dataset entry. Honours ACTIVE_DATASET env override once."""
    manifest = load_manifest()
    override = (settings.active_dataset or "").strip()
    active_id = override or manifest.get("active")
    if not active_id:
        active_id = manifest["available"][0]["id"]
    try:
        return _resolve_dataset_entry(manifest, active_id)
    except KeyError:
        logger.warning(
            "Active dataset %r not found in manifest; falling back to first entry",
            active_id,
        )
        return manifest["available"][0]


def get_active_tickets_path() -> Path:
    entry = get_active_dataset()
    return settings.data_dir / entry["file"]


def switch_dataset(dataset_id: str) -> dict:
    """Update the manifest 'active' pointer. Returns the new entry."""
    manifest = load_manifest()
    entry = _resolve_dataset_entry(manifest, dataset_id)
    manifest["active"] = dataset_id
    write_manifest(manifest)
    logger.info("Dataset switched to %s (%d tickets)", dataset_id, entry["count"])
    return entry


def register_uploaded_dataset(
    tickets: list[dict],
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict:
    """Persist an uploaded dataset to disk and register it in the manifest.

    Returns the new manifest entry. Caller is responsible for switching to it.
    """
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"tickets_custom_{stamp}.json"
    path = settings.data_dir / filename
    path.write_text(json.dumps(tickets, indent=2, default=str))

    dataset_id = f"custom_{stamp}"
    entry = {
        "id": dataset_id,
        "name": name or f"Custom upload {stamp}",
        "description": description or f"User-uploaded dataset ({len(tickets)} tickets)",
        "file": filename,
        "count": len(tickets),
        "tag": "custom",
    }
    manifest = load_manifest()
    manifest["available"].append(entry)
    write_manifest(manifest)
    logger.info("Registered uploaded dataset %s (%d tickets)", dataset_id, len(tickets))
    return entry
