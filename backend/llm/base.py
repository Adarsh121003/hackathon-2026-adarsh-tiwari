"""Abstract LLM client interface.

All provider implementations return the same normalized dict shape so the
ReAct loop in resolver.py never needs to branch on which LLM is active.
This is the classic Adapter pattern — swap providers without touching agent
logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Provider-agnostic async LLM interface."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """Send a plain chat request and return the text response."""

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        max_tokens: int = 2048,
        tool_choice: str = "auto",
    ) -> dict:
        """Send a chat request with tool-calling capability.

        Returns a normalized dict:
        {
            "content": str | None,          # text part of the response
            "tool_calls": [                 # may be empty list
                {"id": str, "name": str, "arguments": dict}
            ],
            "stop_reason": str,             # "tool_use" | "end_turn" | "stop" | etc.
            "raw_usage": dict,              # token counts from provider
        }
        """
