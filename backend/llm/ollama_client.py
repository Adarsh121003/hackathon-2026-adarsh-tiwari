"""Ollama local LLM client (optional fallback).

Uses httpx to call the Ollama REST API directly.  Newer Ollama versions
support OpenAI-compatible tool calling; we use that format.
"""
from __future__ import annotations

import json
import logging

import httpx

from backend.core.config import settings
from backend.core.exceptions import LLMInvalidResponseError
from backend.llm.base import LLMClient

logger = logging.getLogger(__name__)

_TIMEOUT = 60.0  # Ollama can be slow on CPU


class OllamaClient(LLMClient):
    """Async Ollama client via httpx."""

    def __init__(self) -> None:
        self._base = settings.ollama_host.rstrip("/")
        self._model = settings.ollama_model

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        full_messages = self._prepend_system(messages, system)
        payload = {
            "model": self._model,
            "messages": full_messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.1},
        }
        resp = await self._post("/api/chat", payload)
        return resp.get("message", {}).get("content", "")

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        max_tokens: int = 2048,
        tool_choice: str = "auto",
    ) -> dict:
        full_messages = self._prepend_system(messages, system)
        payload = {
            "model": self._model,
            "messages": full_messages,
            "tools": tools,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.1},
        }
        resp = await self._post("/api/chat", payload)
        msg = resp.get("message", {})

        tool_calls: list[dict] = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(
                {"id": tc.get("id", ""), "name": fn.get("name", ""), "arguments": args}
            )

        stop = resp.get("done_reason", "stop")
        return {
            "content": msg.get("content"),
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if tool_calls else "end_turn",
            "raw_usage": {},
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _prepend_system(messages: list[dict], system: str) -> list[dict]:
        if not system:
            return messages
        return [{"role": "system", "content": system}] + messages

    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                r = await client.post(f"{self._base}{path}", json=payload)
                r.raise_for_status()
                return r.json()
            except Exception as exc:
                raise LLMInvalidResponseError("ollama", str(exc)) from exc
