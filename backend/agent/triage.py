"""Triage agent — fast, single-call ticket classification.

Uses a cheap LLM call to classify the ticket before the expensive ReAct loop.
This pre-flight check lets the worker_pool prioritise urgent tickets and
skip the multi-step resolver for obvious policy questions.
"""
from __future__ import annotations

import json
import logging
import re

from backend.agent.prompts import TRIAGE_SYSTEM_PROMPT
from backend.core.models import Ticket, Triage, TicketCategory, Urgency
from backend.llm.factory import get_llm_client

logger = logging.getLogger(__name__)

# Semantic aliases: LLMs sometimes return near-synonyms for valid category names.
# Mapping here prevents Pydantic validation failures on otherwise-correct responses.
_CATEGORY_ALIASES: dict[str, str] = {
    "defective": "damaged",
    "broken": "damaged",
    "faulty": "damaged",
    "malfunction": "damaged",
    "cancel": "cancellation",
    "cancel_order": "cancellation",
    "complaint": "other",
    "inquiry": "policy_question",
    "question": "policy_question",
    "info": "policy_question",
    "information": "policy_question",
    "status": "shipping",
    "tracking": "shipping",
    "delivery": "shipping",
}

# Set of valid TicketCategory values for fast membership check
_VALID_CATEGORIES: set[str] = {c.value for c in TicketCategory}


def _extract_json(text: str) -> str:
    """Strip markdown fences and extract the first JSON object."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def _normalise_category(raw: str) -> str:
    """Map raw LLM category string to a valid TicketCategory value.

    Checks the valid set first, then aliases, then falls back to 'other'.
    The 'return' category is special: the enum value is 'return_' but the
    JSON string should be 'return'.
    """
    cleaned = raw.strip().lower()
    # Direct match (covers all enum values including 'return')
    if cleaned in _VALID_CATEGORIES:
        return cleaned
    # Enum member named 'return_' has value 'return' — already covered above
    # Alias lookup
    if cleaned in _CATEGORY_ALIASES:
        mapped = _CATEGORY_ALIASES[cleaned]
        logger.info("Triage category aliased: '%s' -> '%s'", cleaned, mapped)
        return mapped
    logger.warning("Unknown triage category '%s', falling back to 'other'", cleaned)
    return "other"


class TriageAgent:
    """Classifies a ticket in a single LLM call."""

    async def classify(self, ticket: Ticket) -> Triage:
        """Return a validated Triage for the given ticket."""
        llm = get_llm_client()

        user_message = (
            f"Ticket ID: {ticket.ticket_id}\n"
            f"From: {ticket.customer_email}\n"
            f"Subject: {ticket.subject}\n"
            f"Body:\n{ticket.body}"
        )

        logger.info("Triaging ticket %s", ticket.ticket_id)
        raw = await llm.chat(
            messages=[{"role": "user", "content": user_message}],
            system=TRIAGE_SYSTEM_PROMPT,
            max_tokens=512,
        )

        try:
            data = json.loads(_extract_json(raw))

            # Normalise category before Pydantic sees it
            if "category" in data:
                data["category"] = _normalise_category(str(data["category"]))

            triage = Triage.model_validate(data)
            logger.info(
                "Triage complete: category=%s urgency=%s auto_resolvable=%s confidence=%.2f",
                triage.category,
                triage.urgency,
                triage.auto_resolvable,
                triage.confidence,
            )
            return triage
        except Exception as exc:
            logger.warning("Triage parse failed (%s), using fallback", exc)
            return Triage(
                category=TicketCategory.ambiguous,
                urgency=Urgency.medium,
                auto_resolvable=False,
                reasoning=f"Classification failed: {exc}. Using safe defaults.",
                confidence=0.3,
            )
