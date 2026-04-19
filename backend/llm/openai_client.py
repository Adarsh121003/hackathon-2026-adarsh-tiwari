"""OpenAI LLM client.

OpenAI uses the same tool-calling schema format as Groq (both are OpenAI-
compatible), so the response normalisation logic mirrors groq_client.py
closely.  Rate-limit handling uses the retry-after header OpenAI provides
rather than parsing the error body.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable

import openai as openai_lib
from openai import AsyncOpenAI

from backend.core.config import settings
from backend.core.exceptions import LLMInvalidResponseError, LLMRateLimitError
from backend.llm.base import LLMClient

logger = logging.getLogger(__name__)

_MAX_RATE_LIMIT_RETRIES = 3
_DEFAULT_RATE_LIMIT_SLEEP = 15.0


class OpenAIClient(LLMClient):
    """Async OpenAI client wrapping the official SDK."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

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
                        "openai", f"tool args not valid JSON: {exc}"
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
        """Call callable(), retrying up to 3 times on OpenAI 429 rate-limit errors.

        Reads the retry-after header from the exception when present; falls back
        to a 15s default.  OpenAI's tier-1 rate-limit windows reset faster than
        Groq's free tier, so a shorter default is appropriate.
        """
        for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return await callable()
            except openai_lib.RateLimitError as exc:
                if attempt >= _MAX_RATE_LIMIT_RETRIES:
                    raise LLMRateLimitError("openai") from exc

                # OpenAI sets retry-after in the response headers
                wait = _DEFAULT_RATE_LIMIT_SLEEP
                if hasattr(exc, "response") and exc.response is not None:
                    retry_after = exc.response.headers.get("retry-after")
                    if retry_after:
                        try:
                            wait = float(retry_after) + 1.0
                        except (ValueError, TypeError):
                            pass

                logger.info(
                    "OpenAI rate limit — sleeping %.1fs (attempt %d/%d)",
                    wait,
                    attempt,
                    _MAX_RATE_LIMIT_RETRIES,
                )
                await asyncio.sleep(wait)
            except Exception as exc:
                self._handle_error(exc)

    @staticmethod
    def _prepend_system(messages: list[dict], system: str) -> list[dict]:
        if not system:
            return messages
        return [{"role": "system", "content": system}] + messages

    def _handle_error(self, exc: Exception) -> None:
        """Re-raise provider errors as Sentinel errors."""
        msg = str(exc).lower()
        if "rate limit" in msg or "429" in msg:
            raise LLMRateLimitError("openai") from exc
        raise LLMInvalidResponseError("openai", str(exc)) from exc
