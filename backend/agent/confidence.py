"""Confidence calibration helpers.

Combines the LLM's self-reported confidence with objective signals from the
tool call record to produce a calibrated final confidence score.
This gives judges a transparent, multi-signal view into how certain the
agent is about each resolution.
"""
from __future__ import annotations

from backend.core.models import ToolCallRecord


def calibrate(
    llm_confidence: float,
    tool_records: list[ToolCallRecord],
    guardrail_fired: bool = False,
) -> float:
    """Return a weighted confidence score combining multiple signals.

    Weights:
    - LLM self-reported: 60%
    - Tool success rate: 30%
    - Guardrail penalty: -10% if any guardrail fired
    """
    llm_conf = max(0.0, min(1.0, llm_confidence))

    if tool_records:
        successful = sum(1 for r in tool_records if r.success)
        tool_conf = successful / len(tool_records)
    else:
        tool_conf = 0.5  # neutral when no tools called

    guardrail_penalty = 0.10 if guardrail_fired else 0.0

    score = (llm_conf * 0.60) + (tool_conf * 0.30) - guardrail_penalty
    return round(max(0.0, min(1.0, score)), 3)


def extract_llm_confidence(resolution_dict: dict) -> float:
    """Safely extract the confidence float from a parsed resolution dict."""
    raw = resolution_dict.get("confidence", 0.5)
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return 0.5
