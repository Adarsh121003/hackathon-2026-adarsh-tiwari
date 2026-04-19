"""Groq LLM client.

Groq uses OpenAI-compatible tool-calling schema, so the response shape
is nearly identical.  We normalize it to the LLMClient contract so
resolver.py never knows which backend is active.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable

import groq as groq_lib
from groq import AsyncGroq

from backend.core.config import settings
from backend.core.exceptions import LLMInvalidResponseError, LLMRateLimitError
from backend.llm.base import LLMClient

logger = logging.getLogger(__name__)

_WAIT_RE = re.compile(r"Please try again in ([\d.]+)s")
_MAX_RATE_LIMIT_RETRIES = 3


class GroqClient(LLMClient):
    """Async Groq client wrapping the official SDK."""

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        full_messages = self._prepend_system(messages, system)

        async def _call() -> str:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return resp.choices[0].message.content or ""

        return await self._invoke_with_rate_limit_retry(_call)

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        max_tokens: int = 2048,
        tool_choice: str = "auto",
    ) -> dict:
        full_messages = self._prepend_system(messages, system)

        async def _call() -> Any:
            return await self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                tools=tools,
                tool_choice=tool_choice,
                max_tokens=max_tokens,
                temperature=0.1,
            )

        resp = await self._invoke_with_rate_limit_retry(_call)

        choice = resp.choices[0]
        msg = choice.message
        stop_reason = choice.finish_reason  # "tool_calls" | "stop"

        tool_calls: list[dict] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError as exc:
                    raise LLMInvalidResponseError(
                        "groq", f"tool args not valid JSON: {exc}"
                    ) from exc
                tool_calls.append(
                    {"id": tc.id, "name": tc.function.name, "arguments": args}
                )

        return {
            "content": msg.content,
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if stop_reason == "tool_calls" else "end_turn",
            "raw_usage": {
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _invoke_with_rate_limit_retry(self, callable: Callable) -> Any:
        """Call callable(), retrying up to 3 times on Groq 429 rate-limit errors.

        Catches groq.RateLimitError directly (not just by string matching) so
        we never miss a rate-limit and waste a retry on the wrong exception type.
        Parses the suggested wait time from the error body when available.
        """
        for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return await callable()
            except groq_lib.RateLimitError as exc:
                if attempt >= _MAX_RATE_LIMIT_RETRIES:
                    # All internal retries exhausted — bubble up as Sentinel error
                    raise LLMRateLimitError("groq") from exc
                msg = str(exc)
                m = _WAIT_RE.search(msg)
                wait = float(m.group(1)) + 1.0 if m else 62.0
                logger.info(
                    "Groq 429 rate-limit — sleeping %.1fs then retrying "
                    "(internal attempt %d/%d)",
                    wait,
                    attempt,
                    _MAX_RATE_LIMIT_RETRIES,
                )
                await asyncio.sleep(wait)
            except Exception as exc:
                # Non-rate-limit errors: no retry, normalise and raise immediately
                self._handle_error(exc)

    @staticmethod
    def _prepend_system(messages: list[dict], system: str) -> list[dict]:
        if not system:
            return messages
        return [{"role": "system", "content": system}] + messages

    def _handle_error(self, exc: Exception) -> None:
        """Re-raise provider errors as Sentinel errors."""
        msg = str(exc).lower()
        if "rate limit" in msg or "429" in msg or "rate_limit_exceeded" in msg:
            raise LLMRateLimitError("groq") from exc
        raise LLMInvalidResponseError("groq", str(exc)) from exc
