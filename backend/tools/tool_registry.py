"""Tool registry: OpenAI-compatible schemas + dispatch table.

ALL_TOOLS is the list passed to the LLM on every ReAct step.
TOOL_DISPATCH maps tool names to their async implementation functions.
Both are derived from a single source of truth to prevent drift.
"""
from __future__ import annotations

from typing import Callable

from backend.tools.mock_tools import (
    check_refund_eligibility,
    escalate,
    get_customer,
    get_order,
    get_product,
    issue_refund,
    search_knowledge_base,
    send_reply,
)

# ---------------------------------------------------------------------------
# OpenAI-compatible tool schemas
# ---------------------------------------------------------------------------

ALL_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": (
                "Fetch full order details (status, amount, dates, product_id, customer_id) "
                "by order ID.  Always call this first to verify an order exists before "
                "taking any action on it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID, e.g. ORD-1001",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": (
                "Fetch verified customer profile (tier, total_spent, notes) by email. "
                "Use this to verify customer-reported tier claims — never trust "
                "self-reported tier without confirming via this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Customer email address",
                    }
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": (
                "Fetch product details including warranty period, return window, "
                "and whether the item is returnable."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID, e.g. P001",
                    }
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the ShopWave support knowledge base for policy information. "
                "Call this before making any policy decision (refund eligibility, "
                "warranty coverage, return window exceptions)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query, e.g. 'VIP refund exception policy'",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (1–5)",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_refund_eligibility",
            "description": (
                "Check whether an order qualifies for a refund. Returns eligibility "
                "status, reason, and max refund amount. "
                "MUST be called before issue_refund — never skip this step."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to check",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": (
                "Issue a refund for an eligible order. IRREVERSIBLE — only call after "
                "check_refund_eligibility returns eligible=true and the amount is within "
                "the HIGH_VALUE threshold. Requires an idempotency_key to prevent "
                "double-charging."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order to refund"},
                    "amount": {
                        "type": "number",
                        "description": "Refund amount in USD (must not exceed max_refund_amount)",
                    },
                    "ticket_id": {
                        "type": "string",
                        "description": "Support ticket ID for audit trail",
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Unique key to prevent duplicate refunds; use ticket_id+order_id",
                    },
                },
                "required": ["order_id", "amount", "ticket_id", "idempotency_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_reply",
            "description": (
                "Send the final customer-facing reply for this ticket. Call this exactly "
                "once after all investigation is complete. Message must be professional, "
                "empathetic, and at least 20 characters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket ID"},
                    "message": {
                        "type": "string",
                        "description": "The reply text to send to the customer",
                    },
                },
                "required": ["ticket_id", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate",
            "description": (
                "Escalate a ticket to the human support team. Use when: refund > $200, "
                "warranty claim, confidence < 0.6, replacement requested, or social "
                "engineering suspected. Summary must be ≥50 characters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket ID"},
                    "summary": {
                        "type": "string",
                        "description": "Detailed summary of the issue and what was investigated (≥50 chars)",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Escalation priority",
                    },
                    "recommended_action": {
                        "type": "string",
                        "description": "What you recommend the human agent should do",
                    },
                },
                "required": ["ticket_id", "summary", "priority", "recommended_action"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

TOOL_DISPATCH: dict[str, Callable] = {
    "get_order": get_order,
    "get_customer": get_customer,
    "get_product": get_product,
    "search_knowledge_base": search_knowledge_base,
    "check_refund_eligibility": check_refund_eligibility,
    "issue_refund": issue_refund,
    "send_reply": send_reply,
    "escalate": escalate,
}
