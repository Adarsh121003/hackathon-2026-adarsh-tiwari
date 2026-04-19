"""Exception hierarchy for Sentinel.

All custom exceptions inherit from SentinelError so callers can catch at
any specificity level without accidentally swallowing unrelated errors.
The three top-level families (Tool, Agent, LLM) map cleanly to the three
subsystems judges will ask about.
"""
from __future__ import annotations


class SentinelError(Exception):
    """Base for all Sentinel-specific exceptions."""


# ---------------------------------------------------------------------------
# Tool errors
# ---------------------------------------------------------------------------


class ToolError(SentinelError):
    """A tool invocation failed."""


class ToolTimeoutError(ToolError):
    """Tool did not respond within the configured timeout window."""

    def __init__(self, tool_name: str, timeout_s: float) -> None:
        self.tool_name = tool_name
        self.timeout_s = timeout_s
        super().__init__(f"{tool_name!r} timed out after {timeout_s}s")


class MalformedResponseError(ToolError):
    """Tool returned a structurally invalid response."""

    def __init__(self, tool_name: str, detail: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"{tool_name!r} malformed response: {detail}")


class ToolExecutionError(ToolError):
    """Tool raised an unexpected exception during execution."""

    def __init__(self, tool_name: str, cause: Exception) -> None:
        self.tool_name = tool_name
        self.cause = cause
        super().__init__(f"{tool_name!r} execution error: {cause}")


# ---------------------------------------------------------------------------
# Agent errors
# ---------------------------------------------------------------------------


class AgentError(SentinelError):
    """Error in the agent's reasoning/orchestration layer."""


class MaxStepsExceededError(AgentError):
    """ReAct loop reached MAX_AGENT_STEPS without producing a resolution."""

    def __init__(self, steps: int) -> None:
        super().__init__(f"Agent exceeded max steps ({steps}) without resolving")


class InvalidToolCallError(AgentError):
    """LLM produced a tool call that references an unknown tool or bad args."""

    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Invalid tool call {tool_name!r}: {reason}")


# ---------------------------------------------------------------------------
# LLM errors
# ---------------------------------------------------------------------------


class LLMError(SentinelError):
    """Error communicating with the underlying language model."""


class LLMRateLimitError(LLMError):
    """Provider returned a 429 / rate-limit response."""

    def __init__(self, provider: str, retry_after: float | None = None) -> None:
        self.provider = provider
        self.retry_after = retry_after
        msg = f"{provider} rate limit hit"
        if retry_after:
            msg += f"; retry after {retry_after}s"
        super().__init__(msg)


class LLMInvalidResponseError(LLMError):
    """Provider returned a response that couldn't be parsed."""

    def __init__(self, provider: str, detail: str) -> None:
        self.provider = provider
        super().__init__(f"{provider} invalid response: {detail}")
