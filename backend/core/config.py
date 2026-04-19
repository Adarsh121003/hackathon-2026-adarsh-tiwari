"""Environment-driven configuration for Sentinel.

Using a frozen dataclass (not a mutable dict) makes it obvious at a glance
that configuration is set-once at startup.  validate() is called explicitly
at app boot so misconfiguration fails loudly with a helpful message instead
of producing a cryptic KeyError at runtime.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root is two levels above this file (backend/core/config.py → /)
_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Settings:
    # LLM routing
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq"))

    # Groq
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_model: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    )

    # Anthropic
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    anthropic_model: str = field(
        default_factory=lambda: os.getenv(
            "ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"
        )
    )

    # OpenAI
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    openai_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )

    # Ollama
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    )

    # Agent tuning
    max_agent_steps: int = field(
        default_factory=lambda: int(os.getenv("MAX_AGENT_STEPS", "16"))
    )
    confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
    )
    max_concurrent_tickets: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_TICKETS", "2"))
    )

    # Tool resilience
    tool_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("TOOL_TIMEOUT_SECONDS", "5.0"))
    )
    max_tool_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_TOOL_RETRIES", "2"))
    )
    retry_base_delay_ms: int = field(
        default_factory=lambda: int(os.getenv("RETRY_BASE_DELAY_MS", "150"))
    )

    # Chaos injection rates (0–1)
    mock_timeout_rate: float = field(
        default_factory=lambda: float(os.getenv("MOCK_TIMEOUT_RATE", "0.12"))
    )
    mock_malformed_rate: float = field(
        default_factory=lambda: float(os.getenv("MOCK_MALFORMED_RATE", "0.08"))
    )

    # Business rules
    high_value_refund_threshold: float = field(
        default_factory=lambda: float(
            os.getenv("HIGH_VALUE_REFUND_THRESHOLD", "200.0")
        )
    )

    # Dataset selection — manifest is source of truth; env can override at boot
    active_dataset: str = field(
        default_factory=lambda: os.getenv("ACTIVE_DATASET", "")
    )

    # API
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
    )

    # Derived paths (computed via property-like approach post-init is not
    # possible on frozen dataclasses, so we expose them as class-level helpers)
    @property
    def data_dir(self) -> Path:
        p = _ROOT / "data"
        return p

    @property
    def logs_dir(self) -> Path:
        p = _ROOT / "logs"
        p.mkdir(exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        return self.logs_dir / "sentinel.db"

    @property
    def dataset_manifest_path(self) -> Path:
        return self.data_dir / "dataset_manifest.json"

    def validate(self) -> None:
        """Raise ValueError if required keys are missing for the chosen provider."""
        provider = self.llm_provider.lower()
        if provider == "groq" and not self.groq_api_key:
            raise ValueError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set in environment"
            )
        if provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set in environment"
            )
        if provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set in environment"
            )
        if provider not in {"groq", "anthropic", "ollama", "openai"}:
            raise ValueError(
                f"Unknown LLM_PROVIDER={provider!r}. Choose groq | anthropic | ollama | openai"
            )


# Module-level singleton — import this everywhere
settings = Settings()
