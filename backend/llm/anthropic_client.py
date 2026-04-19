"""Anthropic LLM client.

Anthropic's tool schema uses "input_schema" instead of OpenAI's "parameters",
and stop_reason is "tool_use" / "end_turn" (already matches our contract).
We convert inbound OpenAI-style tool dicts to Anthropic format internally.
"""
from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

from backend.core.config import settings
from backend.core.exceptions import LLMInvalidResponseError, LLMRateLimitError
from backend.llm.base import LLMClient

logger = logging.getLogger(__name__)


class AnthropicClient(LLMClient):
    """Async Anthropic client."""

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        try:
            resp = await self._client.messages.create(
                model=self._model,
                system=system or "",
                messages=messages,
                max_tokens=max_tokens,
            )
            return resp.content[0].text if resp.content else ""
        except Exception as exc:
            self._handle_error(exc)

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        max_tokens: int = 2048,
        tool_choice: str = "auto",
    ) -> dict:
        anthropic_tools = [self._convert_tool(t) for t in tools]
        try:
            resp = await self._client.messages.create(
                model=self._model,
                system=system or "",
                messages=messages,
                tools=anthropic_tools,
                max_tokens=max_tokens,
                temperature=0.1,
            )
        except Exception as exc:
            self._handle_error(exc)

        text_content: str | None = None
        tool_calls: list[dict] = []

        for block in resp.content:
            if block.type == "text":
                text_content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input,
                    }
                )

        return {
            "content": text_content,
            "tool_calls": tool_calls,
            "stop_reason": resp.stop_reason,  # already "tool_use" or "end_turn"
            "raw_usage": {
                "prompt_tokens": resp.usage.input_tokens,
                "completion_tokens": resp.usage.output_tokens,
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_tool(openai_tool: dict) -> dict:
        """Convert OpenAI tool schema to Anthropic format."""
        fn = openai_tool.get("function", openai_tool)
        return {
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        }

    def _handle_error(self, exc: Exception) -> None:
        msg = str(exc).lower()
        if "rate limit" in msg or "429" in msg or "overloaded" in msg:
            raise LLMRateLimitError("anthropic") from exc
        raise LLMInvalidResponseError("anthropic", str(exc)) from exc
