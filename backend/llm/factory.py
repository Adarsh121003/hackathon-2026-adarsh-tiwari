"""LLM client factory.

Returns the correct provider instance based on LLM_PROVIDER env var.
The lru_cache ensures we create at most one client per process — important
because each client holds an HTTP connection pool.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from backend.core.config import settings
from backend.llm.base import LLMClient

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """Return the singleton LLM client for the configured provider."""
    provider = settings.llm_provider.lower()
    logger.info("Initialising LLM client: provider=%s", provider)

    if provider == "groq":
        from backend.llm.groq_client import GroqClient

        return GroqClient()
    if provider == "anthropic":
        from backend.llm.anthropic_client import AnthropicClient

        return AnthropicClient()
    if provider == "ollama":
        from backend.llm.ollama_client import OllamaClient

        return OllamaClient()
    if provider == "openai":
        from backend.llm.openai_client import OpenAIClient

        return OpenAIClient()

    raise ValueError(f"Unknown LLM_PROVIDER={provider!r}")
