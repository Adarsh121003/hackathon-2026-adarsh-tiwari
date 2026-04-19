"""Pre-execution guardrails for tool calls.

Guardrails are a separate concern from tool logic — they enforce business
rules at the orchestration layer, where the agent has full context.
A tool blocked by a guardrail is reported back to the LLM so it can adapt
its reasoning (e.g. "refund blocked, escalating instead").
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from backend.core.config import settings

logger = logging.getLogger(__name__)


class GuardrailCheck(BaseModel):
    allowed: bool
    reason: str
    severity: str  # "info" | "warning" | "block"


class Guardrails:
    """Stateless rule evaluator for tool calls within a ticket resolution context."""

    def check(
        self,
        tool_name: str,
        arguments: dict,
        context: dict,
    ) -> GuardrailCheck:
        """Evaluate all applicable rules for the given tool call.

        context keys used:
          - tool_calls_made: list[str] of tool names already called this ticket
          - eligibility_results: dict[order_id, eligibility_dict]
          - issued_refund_ids: set[str] of order_ids already refunded
          - ticket_id: str
        """
        handler = getattr(self, f"_check_{tool_name}", None)
        if handler is None:
            return GuardrailCheck(allowed=True, reason="No guardrail for this tool", severity="info")
        return handler(arguments, context)

    # ------------------------------------------------------------------
    # Per-tool rules
    # ------------------------------------------------------------------

    def _check_issue_refund(self, arguments: dict, context: dict) -> GuardrailCheck:
        order_id = arguments.get("order_id", "")
        amount = float(arguments.get("amount", 0))

        # Rule 1: Must have prior eligibility check for this order
        eligibility_results: dict = context.get("eligibility_results", {})
        if order_id not in eligibility_results:
            return GuardrailCheck(
                allowed=False,
                reason=(
                    f"issue_refund blocked: check_refund_eligibility has not been called "
                    f"for order {order_id!r} in this session. Call it first."
                ),
                severity="block",
            )

        elig = eligibility_results[order_id]
        if not elig.get("eligible"):
            return GuardrailCheck(
                allowed=False,
                reason=f"issue_refund blocked: eligibility check returned not-eligible: {elig.get('reason')}",
                severity="block",
            )

        # Rule 2: High-value refund → escalate instead
        if amount > settings.high_value_refund_threshold:
            return GuardrailCheck(
                allowed=False,
                reason=(
                    f"issue_refund blocked: amount ${amount:.2f} exceeds "
                    f"HIGH_VALUE threshold ${settings.high_value_refund_threshold:.2f}. "
                    "Escalate to human agent."
                ),
                severity="block",
            )

        # Rule 3: Duplicate refund guard
        issued_ids: set = context.get("issued_refund_ids", set())
        if order_id in issued_ids:
            return GuardrailCheck(
                allowed=False,
                reason=f"issue_refund blocked: refund already issued for order {order_id!r} in this session",
                severity="block",
            )

        return GuardrailCheck(allowed=True, reason="All refund guardrails passed", severity="info")

    def _check_send_reply(self, arguments: dict, context: dict) -> GuardrailCheck:
        # Rule: Must have made at least one lookup tool call before replying
        tool_calls_made: list[str] = context.get("tool_calls_made", [])
        lookup_tools = {"get_order", "get_customer", "get_product", "search_knowledge_base", "check_refund_eligibility"}
        if not any(t in lookup_tools for t in tool_calls_made):
            return GuardrailCheck(
                allowed=False,
                reason="send_reply blocked: no lookup tool has been called yet. Gather information first.",
                severity="warning",
            )
        return GuardrailCheck(allowed=True, reason="send_reply guardrail passed", severity="info")

    def _check_escalate(self, arguments: dict, context: dict) -> GuardrailCheck:
        summary = arguments.get("summary", "")
        if len(summary.strip()) < 50:
            return GuardrailCheck(
                allowed=False,
                reason=f"escalate blocked: summary too short ({len(summary)} chars). Minimum 50 required.",
                severity="block",
            )
        return GuardrailCheck(allowed=True, reason="escalate guardrail passed", severity="info")
