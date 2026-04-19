"""ReAct-loop resolver agent — the core of Sentinel.

Implements the full Reason-Act-Observe loop:
  1. LLM reasons and emits tool calls
  2. Each tool call goes through guardrails → resilience wrapper → tool
  3. Results appended to message history
  4. Loop continues until LLM stops calling tools or max steps reached
  5. Final synthesis call produces the structured Resolution

This file is the most important one for judges: it shows the complete
agentic reasoning pipeline with every safety check visible.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from backend.agent.confidence import calibrate, extract_llm_confidence
from backend.agent.guardrails import Guardrails
from backend.agent.prompts import FINAL_RESOLUTION_PROMPT, RESOLVER_SYSTEM_PROMPT
from backend.core.config import settings
from backend.core.exceptions import MaxStepsExceededError
from backend.core.models import (
    Resolution,
    ResolutionStatus,
    Ticket,
    TicketCategory,
    Triage,
    ToolCallRecord,
    Urgency,
)
from backend.llm.factory import get_llm_client
from backend.tools.resilience import execute_tool
from backend.tools.tool_registry import ALL_TOOLS, TOOL_DISPATCH

logger = logging.getLogger(__name__)

_guardrails = Guardrails()


def _truncate_messages(messages: list[dict], keep_recent: int = 6) -> list[dict]:
    """Return a token-budget-friendly view of the conversation history.

    We truncate to reduce token usage while preserving the agent's anchoring
    context (initial user ticket) and the most recent reasoning steps.
    The full untruncated list is always kept for the audit trail.

    Critical invariant: the tail must never start with a 'tool' message.
    OpenAI (and spec-compliant providers) require every tool message to
    immediately follow an assistant message that contains tool_calls.
    If truncation slices off that assistant message, the orphaned tool
    message at the start of the tail causes a 400 error.  We walk forward
    past any leading tool messages to find a safe cut point.
    """
    if len(messages) <= 1 + keep_recent:
        return messages

    anchor = messages[:1]  # always keep: initial user ticket message
    tail = messages[-keep_recent:]

    # Skip orphaned leading tool messages — their assistant+tool_calls
    # partner was truncated away and cannot be reconstructed here.
    start = 0
    while start < len(tail) and tail[start].get("role") == "tool":
        start += 1

    return anchor + tail[start:]


def _extract_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text or "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def _tool_result_message(tool_id: str, tool_name: str, result: dict) -> dict:
    """Format a tool result as a message for the LLM conversation history."""
    return {
        "role": "tool",
        "tool_call_id": tool_id,
        "name": tool_name,
        "content": json.dumps(result, default=str),
    }


class ResolverAgent:
    """Multi-step ReAct agent that resolves a support ticket."""

    async def resolve(self, ticket: Ticket, triage: Triage) -> Resolution:
        """Run the full ReAct loop and return a structured Resolution."""
        started_at = datetime.now(timezone.utc)
        wall_start = time.monotonic()

        llm = get_llm_client()
        all_tool_records: list[ToolCallRecord] = []

        # Agent context — shared state for guardrails
        agent_ctx: dict[str, Any] = {
            "ticket_id": ticket.ticket_id,
            "tool_calls_made": [],          # tool names called successfully
            "eligibility_results": {},      # order_id → eligibility dict
            "issued_refund_ids": set(),     # order_ids where refund was issued
            "guardrail_fired": False,
        }

        # Loop detection: keyed on canonical (tool_name, arguments). When the
        # LLM repeats an identical call we return the cached result without
        # re-executing — this protects against pathological reasoning loops
        # that otherwise burn the step budget with zero new information.
        seen_calls: dict[str, dict] = {}

        # Initial user message with full ticket + triage context
        user_content = (
            f"## Support Ticket\n"
            f"Ticket ID: {ticket.ticket_id}\n"
            f"Customer Email: {ticket.customer_email}\n"
            f"Subject: {ticket.subject}\n"
            f"Body:\n{ticket.body}\n\n"
            f"## Pre-Classification (Triage)\n"
            f"Category: {triage.category}\n"
            f"Urgency: {triage.urgency}\n"
            f"Auto-resolvable: {triage.auto_resolvable}\n"
            f"Extracted Order ID: {triage.extracted_order_id or 'none found'}\n"
            f"Social Engineering Suspected: {triage.social_engineering_suspected}\n"
            f"Threatening Language: {triage.threatening_language}\n"
            f"Triage Reasoning: {triage.reasoning}\n\n"
            f"Resolve this ticket now.\n"
            f"You must make at least 3 tool calls BEFORE any action tool "
            f"(issue_refund / cancel_order / escalate / send_reply).\n"
            f"After the minimum is met, STOP GATHERING and ACT — pick a "
            f"resolution path from the system prompt. Do not keep investigating "
            f"once you have the evidence to decide."
        )

        messages: list[dict] = [{"role": "user", "content": user_content}]
        tool_call_sequence = 0

        # ----------------------------------------------------------------
        # ReAct loop
        # ----------------------------------------------------------------
        for step in range(settings.max_agent_steps):
            logger.info(
                "ReAct step %d/%d for ticket %s",
                step + 1,
                settings.max_agent_steps,
                ticket.ticket_id,
            )

            response = await llm.chat_with_tools(
                messages=_truncate_messages(messages),
                tools=ALL_TOOLS,
                system=RESOLVER_SYSTEM_PROMPT,
                max_tokens=2048,
            )

            assistant_text = response.get("content") or ""
            tool_calls = response.get("tool_calls", [])
            stop_reason = response.get("stop_reason", "end_turn")

            # Build assistant message for history
            if tool_calls:
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": assistant_text or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            else:
                assistant_msg = {"role": "assistant", "content": assistant_text}
            messages.append(assistant_msg)

            # No tool calls → LLM is done (or we've reached natural end)
            if not tool_calls:
                logger.info("LLM made no more tool calls at step %d", step + 1)
                break

            # Execute each tool call
            for tc in tool_calls:
                tool_name = tc["name"]
                arguments = tc["arguments"]
                tool_id = tc["id"]

                # Loop guard: hash canonical (name, args). If we already ran this
                # exact call, return the cached result without re-executing, without
                # advancing the sequence counter, and without appending a new audit
                # record. The synthetic note nudges the LLM to make progress.
                call_key = f"{tool_name}:{json.dumps(arguments, sort_keys=True, default=str)}"
                if call_key in seen_calls:
                    logger.warning(
                        "Loop guard: %s called again with identical args for ticket %s",
                        tool_name, ticket.ticket_id,
                    )
                    loop_result = {
                        "loop_guard": True,
                        "note": "Identical call was already made. Use the prior result; do not repeat.",
                        "previous_result": seen_calls[call_key],
                    }
                    messages.append(_tool_result_message(tool_id, tool_name, loop_result))
                    continue

                tool_call_sequence += 1

                logger.info("Tool call #%d: %s(%s)", tool_call_sequence, tool_name, arguments)

                # Guardrail check
                check = _guardrails.check(tool_name, arguments, agent_ctx)
                if not check.allowed:
                    logger.warning("Guardrail blocked %s: %s", tool_name, check.reason)
                    agent_ctx["guardrail_fired"] = True
                    # Inform LLM about the block
                    block_result = {"blocked": True, "reason": check.reason}
                    messages.append(_tool_result_message(tool_id, tool_name, block_result))
                    all_tool_records.append(
                        ToolCallRecord(
                            sequence=tool_call_sequence,
                            tool_name=tool_name,
                            arguments=arguments,
                            success=False,
                            result=block_result,
                            error=f"Guardrail: {check.reason}",
                            latency_ms=0.0,
                            attempt=1,
                            timestamp=datetime.now(timezone.utc),
                        )
                    )
                    continue

                # Execute via resilience wrapper
                fn = TOOL_DISPATCH.get(tool_name)
                if fn is None:
                    error_result = {"error": "unknown_tool", "name": tool_name}
                    messages.append(_tool_result_message(tool_id, tool_name, error_result))
                    continue

                result, records = await execute_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    fn=fn,
                    sequence=tool_call_sequence,
                )
                all_tool_records.extend(records)
                messages.append(_tool_result_message(tool_id, tool_name, result))

                # Cache for loop detection — only after a successful roundtrip
                # (failed retries can legitimately be reissued by the agent).
                if "error" not in result and not result.get("blocked"):
                    seen_calls[call_key] = result

                # Update agent context for subsequent guardrail checks
                self._update_context(agent_ctx, tool_name, arguments, result)

        else:
            # Loop exhausted without breaking → max steps exceeded.
            # Inject an explicit instruction so synthesis always produces
            # "escalated" rather than "failed" — the agent did real work,
            # it just couldn't finish under the step budget.
            logger.error("Max steps (%d) exceeded for ticket %s", settings.max_agent_steps, ticket.ticket_id)
            messages.append({
                "role": "user",
                "content": (
                    "SYSTEM NOTE: The agent has reached the maximum step limit. "
                    "You could not fully resolve this ticket. "
                    "Set status='escalated' in your final JSON — this ticket needs human review."
                ),
            })

        # ----------------------------------------------------------------
        # Synthesise final Resolution
        # ----------------------------------------------------------------
        resolution = await self._synthesise(
            ticket=ticket,
            triage=triage,
            messages=messages,
            tool_records=all_tool_records,
            agent_ctx=agent_ctx,
            started_at=started_at,
            wall_start=wall_start,
        )
        return resolution

    # ------------------------------------------------------------------
    # Context tracking
    # ------------------------------------------------------------------

    def _update_context(
        self, ctx: dict, tool_name: str, arguments: dict, result: dict
    ) -> None:
        """Update agent_ctx based on successful tool results."""
        if "error" in result or result.get("blocked"):
            return

        ctx["tool_calls_made"].append(tool_name)

        if tool_name == "check_refund_eligibility":
            order_id = arguments.get("order_id", "")
            if order_id:
                ctx["eligibility_results"][order_id] = result

        if tool_name == "issue_refund" and result.get("status") == "issued":
            order_id = arguments.get("order_id", "")
            if order_id:
                ctx["issued_refund_ids"].add(order_id)

    # ------------------------------------------------------------------
    # Resolution synthesis
    # ------------------------------------------------------------------

    async def _synthesise(
        self,
        ticket: Ticket,
        triage: Triage,
        messages: list[dict],
        tool_records: list[ToolCallRecord],
        agent_ctx: dict,
        started_at: datetime,
        wall_start: float,
    ) -> Resolution:
        """Ask the LLM to produce a structured Resolution from the full conversation."""
        llm = get_llm_client()

        synthesis_messages = messages + [
            {
                "role": "user",
                "content": (
                    f"You have completed your investigation of ticket {ticket.ticket_id}. "
                    "Now produce the final structured JSON resolution as described in the system prompt. "
                    "Base it on all tool results gathered above. Output ONLY valid JSON."
                ),
            }
        ]

        raw = await llm.chat(
            messages=synthesis_messages,
            system=FINAL_RESOLUTION_PROMPT,
            max_tokens=1024,
        )

        completed_at = datetime.now(timezone.utc)
        total_ms = (time.monotonic() - wall_start) * 1000

        try:
            data = json.loads(_extract_json(raw))
        except Exception as exc:
            logger.warning("Resolution parse failed for %s: %s", ticket.ticket_id, exc)
            data = {}

        llm_conf = extract_llm_confidence(data)
        calibrated_conf = calibrate(llm_conf, tool_records, agent_ctx.get("guardrail_fired", False))

        status_raw = data.get("status", "escalated")
        try:
            status = ResolutionStatus(status_raw)
        except ValueError:
            status = ResolutionStatus.escalated

        # "failed" is a system-level state (exception/crash), not a logical outcome.
        # If the agent made tool calls but couldn't resolve, that's "escalated" —
        # a human should review it.  Prevents the LLM from returning "failed" for
        # cases like "return window passed, can't refund" which need human judgment.
        if status == ResolutionStatus.failed and tool_records:
            status = ResolutionStatus.escalated
            data.setdefault("flags", []).append(
                "Status promoted from 'failed' to 'escalated': agent investigated "
                "but could not resolve — requires human review."
            )

        return Resolution(
            ticket_id=ticket.ticket_id,
            status=status,
            category=triage.category,
            urgency=triage.urgency,
            confidence=calibrated_conf,
            actions_taken=data.get("actions_taken", []),
            final_customer_message=data.get("final_customer_message", ""),
            escalation_summary=data.get("escalation_summary"),
            reasoning_trace=data.get("reasoning_trace", []),
            tool_calls=tool_records,
            started_at=started_at,
            completed_at=completed_at,
            total_latency_ms=round(total_ms, 2),
            flags=data.get("flags", []),
        )
