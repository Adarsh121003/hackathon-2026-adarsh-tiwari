"""Mock tool implementations with chaos injection.

Every tool simulates realistic network latency and two fault modes:
  - timeout_rate: the tool hangs (triggering the caller's asyncio timeout)
  - malformed_rate: the tool returns a structurally broken response

This is intentional: the resilience layer (resilience.py) must handle these
gracefully, and judges specifically look for fault-tolerance in the demo.

All tools return plain dicts (not Pydantic models) because the LLM receives
JSON-serialised tool results.
"""
from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import date

from backend.core.config import settings
from backend.core.exceptions import MalformedResponseError, ToolExecutionError
from backend.tools import datastore as ds_module
from backend.tools import kb_search

logger = logging.getLogger(__name__)


def _chaos(tool_name: str) -> None:
    """Inject faults at configured rates — called at the start of each tool."""
    r = random.random()
    if r < settings.mock_timeout_rate:
        logger.debug("chaos: injecting timeout into %s", tool_name)
        # This coroutine must be awaited by the caller; we raise instead since
        # we can't await here.  Resilience layer catches TimeoutError from
        # asyncio.wait_for wrapping the entire tool call.
        raise _PendingTimeout(tool_name)
    if r < settings.mock_timeout_rate + settings.mock_malformed_rate:
        logger.debug("chaos: injecting malformed response into %s", tool_name)
        raise MalformedResponseError(tool_name, "chaos-injected missing fields")


class _PendingTimeout(Exception):
    """Signals that this call should sleep long enough to trigger the timeout."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name


async def _latency(tool_name: str) -> None:
    """Simulate real tool latency, or sleep forever to trigger timeout."""
    try:
        _chaos(tool_name)
    except _PendingTimeout:
        await asyncio.sleep(60)  # caller's wait_for will fire before this
    await asyncio.sleep(random.uniform(0.04, 0.35))


# ---------------------------------------------------------------------------
# READ TOOLS
# ---------------------------------------------------------------------------


async def get_order(order_id: str) -> dict:
    """Fetch order details by ID from the in-memory data store."""
    if not order_id or not order_id.strip():
        return {"error": "invalid_input", "detail": "order_id must be non-empty"}

    await _latency("get_order")

    store = ds_module.store
    data = store.get_effective_order(order_id.strip())
    if data is None:
        return {"error": "not_found", "order_id": order_id}

    # Ensure dates are JSON-serialisable strings
    for key in ("order_date", "delivery_date", "return_deadline"):
        if isinstance(data.get(key), date):
            data[key] = str(data[key])

    return data


async def get_customer(email: str) -> dict:
    """Fetch customer profile by email address."""
    if not email or not email.strip():
        return {"error": "invalid_input", "detail": "email must be non-empty"}

    await _latency("get_customer")

    store = ds_module.store
    customer = store.get_customer_by_email(email.strip().lower())
    if customer is None:
        return {"error": "not_found", "email": email}

    data = customer.model_dump()
    for key in ("member_since",):
        if isinstance(data.get(key), date):
            data[key] = str(data[key])
    if "address" in data and hasattr(data["address"], "model_dump"):
        data["address"] = data["address"].model_dump()

    return data


async def get_product(product_id: str) -> dict:
    """Fetch product details including warranty and return policy."""
    if not product_id or not product_id.strip():
        return {"error": "invalid_input", "detail": "product_id must be non-empty"}

    await _latency("get_product")

    store = ds_module.store
    product = store.get_product(product_id.strip())
    if product is None:
        return {"error": "not_found", "product_id": product_id}
    return product.model_dump()


async def search_knowledge_base(query: str, top_k: int = 3) -> dict:
    """Search the ShopWave knowledge base using TF-IDF relevance ranking."""
    if not query or not query.strip():
        return {"error": "invalid_input", "detail": "query must be non-empty"}

    await _latency("search_knowledge_base")

    results = kb_search.search(query.strip(), top_k=max(1, min(top_k, 10)))
    return {"query": query, "results": results}


# ---------------------------------------------------------------------------
# ACTION TOOLS
# ---------------------------------------------------------------------------


async def check_refund_eligibility(order_id: str) -> dict:
    """Determine whether an order is eligible for a refund based on policy rules."""
    if not order_id or not order_id.strip():
        return {"error": "invalid_input", "detail": "order_id must be non-empty"}

    await _latency("check_refund_eligibility")

    store = ds_module.store
    order_data = store.get_effective_order(order_id.strip())
    if order_data is None:
        return {"eligible": False, "reason": "Order not found", "max_refund_amount": 0.0, "policy_notes": []}

    product_id = order_data.get("product_id", "")
    product = store.get_product(product_id)

    today = date.today()
    policy_notes: list[str] = []

    # Gate: must be delivered
    if order_data.get("status") != "delivered":
        return {
            "eligible": False,
            "reason": f"Order is not in delivered status (current: {order_data.get('status')})",
            "max_refund_amount": 0.0,
            "policy_notes": ["Returns only accepted after delivery."],
        }

    # Gate: not already refunded
    if order_data.get("refund_status") == "refunded":
        return {
            "eligible": False,
            "reason": "Order has already been refunded",
            "max_refund_amount": 0.0,
            "policy_notes": ["Duplicate refund blocked by idempotency check."],
        }

    # Gate: product must be returnable
    if product and not product.returnable:
        return {
            "eligible": False,
            "reason": f"Product '{product.name}' is marked non-returnable",
            "max_refund_amount": 0.0,
            "policy_notes": ["Non-returnable items per product policy."],
        }

    # Gate: return deadline
    return_deadline_raw = order_data.get("return_deadline")
    if return_deadline_raw:
        if isinstance(return_deadline_raw, str):
            deadline = date.fromisoformat(return_deadline_raw)
        else:
            deadline = return_deadline_raw
        if today > deadline:
            policy_notes.append(
                f"Return window closed on {deadline}. VIP/Premium customers may have exceptions."
            )
            return {
                "eligible": False,
                "reason": f"Return deadline passed ({deadline})",
                "max_refund_amount": 0.0,
                "policy_notes": policy_notes,
            }
        else:
            days_left = (deadline - today).days
            policy_notes.append(f"{days_left} days remaining in return window.")

    max_amount = float(order_data.get("amount", 0))
    policy_notes.append("Refunds processed to original payment method in 5–7 business days.")

    return {
        "eligible": True,
        "reason": "All eligibility criteria met",
        "max_refund_amount": max_amount,
        "policy_notes": policy_notes,
    }


async def issue_refund(
    order_id: str,
    amount: float,
    ticket_id: str,
    idempotency_key: str,
) -> dict:
    """Issue a refund for an order.  Idempotent — safe to retry on network failures."""
    if not order_id or not ticket_id or not idempotency_key:
        return {"error": "invalid_input", "detail": "order_id, ticket_id, idempotency_key required"}
    if amount <= 0:
        return {"error": "invalid_input", "detail": "amount must be positive"}

    await _latency("issue_refund")

    store = ds_module.store

    # Idempotency guard — prevent double-refund across retries
    action_key = f"refund:{idempotency_key}"
    if not store.mark_performed(ticket_id, action_key):
        logger.info("Idempotency guard: refund already processed for %s", idempotency_key)
        return {
            "status": "already_processed",
            "order_id": order_id,
            "amount": amount,
            "detail": "Refund was already issued for this idempotency key",
        }

    # Double-check eligibility as safety net
    eligibility = await check_refund_eligibility(order_id)
    if not eligibility.get("eligible"):
        # Undo the mark_performed reservation since we didn't actually refund
        store._performed_actions.get(ticket_id, set()).discard(action_key)
        return {
            "status": "rejected",
            "reason": eligibility.get("reason", "Not eligible"),
            "order_id": order_id,
        }

    max_amount = eligibility.get("max_refund_amount", 0)
    actual_amount = min(float(amount), float(max_amount))

    refund_id = f"RFD-{uuid.uuid4().hex[:8].upper()}"
    await store.mark_refunded(order_id, refund_id)

    logger.info("Refund issued: %s amount=%.2f ticket=%s", refund_id, actual_amount, ticket_id)
    return {
        "status": "issued",
        "refund_id": refund_id,
        "order_id": order_id,
        "amount": actual_amount,
        "processing_days": "5–7 business days",
    }


async def send_reply(ticket_id: str, message: str) -> dict:
    """Send a customer-facing reply for a support ticket (one per ticket)."""
    if not ticket_id or not ticket_id.strip():
        return {"error": "invalid_input", "detail": "ticket_id required"}
    if not message or len(message.strip()) < 20:
        return {
            "error": "quality_guard",
            "detail": "Message must be at least 20 characters (quality guard)",
        }

    await _latency("send_reply")

    store = ds_module.store

    # One reply per ticket
    if not store.mark_performed(ticket_id, "send_reply"):
        return {
            "status": "already_sent",
            "ticket_id": ticket_id,
            "detail": "A reply has already been sent for this ticket",
        }

    message_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
    logger.info("Reply sent: %s for ticket=%s", message_id, ticket_id)
    return {
        "status": "sent",
        "ticket_id": ticket_id,
        "message_id": message_id,
        "chars": len(message),
    }


async def escalate(
    ticket_id: str,
    summary: str,
    priority: str,
    recommended_action: str,
) -> dict:
    """Escalate a ticket to the human support team with a structured summary."""
    if not ticket_id or not ticket_id.strip():
        return {"error": "invalid_input", "detail": "ticket_id required"}
    if not summary or len(summary.strip()) < 50:
        return {
            "error": "quality_guard",
            "detail": "Escalation summary must be at least 50 characters (quality guard)",
        }
    if priority not in {"low", "medium", "high", "urgent"}:
        return {
            "error": "invalid_input",
            "detail": f"priority must be one of: low, medium, high, urgent (got {priority!r})",
        }

    await _latency("escalate")

    store = ds_module.store

    # One escalation per ticket
    if not store.mark_performed(ticket_id, "escalate"):
        return {
            "status": "already_escalated",
            "ticket_id": ticket_id,
            "detail": "This ticket has already been escalated",
        }

    escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    logger.info(
        "Ticket escalated: %s priority=%s ticket=%s", escalation_id, priority, ticket_id
    )
    return {
        "status": "escalated",
        "escalation_id": escalation_id,
        "ticket_id": ticket_id,
        "priority": priority,
        "recommended_action": recommended_action,
    }
