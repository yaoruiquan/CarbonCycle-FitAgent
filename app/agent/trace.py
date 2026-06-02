"""
Agent trace helpers.
智能体轨迹辅助函数

Keeps node and tool observability payloads consistent across the graph.
"""

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Optional

from app.agent.state import AgentStepTrace, ToolTrace

def utc_now_iso() -> str:
    """Return a stable UTC timestamp for API payloads."""
    return datetime.now(timezone.utc).isoformat()


def start_timer() -> tuple[str, float]:
    """Return start timestamp and monotonic start time."""
    return utc_now_iso(), perf_counter()


def duration_ms(start: float) -> int:
    """Return elapsed milliseconds from a monotonic start time."""
    return int((perf_counter() - start) * 1000)


def make_step_trace(
    *,
    node: str,
    title: str,
    status: str,
    decision: str,
    reasoning: str,
    input_summary: Optional[dict[str, Any]] = None,
    output_summary: Optional[dict[str, Any]] = None,
    confidence: float = 0.8,
    started_at: Optional[str] = None,
    elapsed_ms: int = 0,
) -> AgentStepTrace:
    """Build an observable node trace entry."""
    return {
        "node": node,
        "title": title,
        "status": status,
        "decision": decision,
        "reasoning": reasoning,
        "input_summary": input_summary or {},
        "output_summary": output_summary or {},
        "confidence": max(0, min(1, confidence)),
        "started_at": started_at or utc_now_iso(),
        "completed_at": utc_now_iso(),
        "duration_ms": elapsed_ms,
    }


def make_tool_trace(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    result: Optional[dict[str, Any]] = None,
    status: str = "success",
    elapsed_ms: int = 0,
    error: Optional[str] = None,
) -> ToolTrace:
    """Build a trace entry for a function/tool call."""
    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result or {},
        "status": status,
        "duration_ms": elapsed_ms,
        "error": error,
    }


def append_trace(state: dict[str, Any], trace: AgentStepTrace) -> list[AgentStepTrace]:
    """Return a new trace list with the given trace appended."""
    return [*state.get("trace", []), trace]


def append_tool_trace(state: dict[str, Any], traces: list[ToolTrace]) -> list[ToolTrace]:
    """Return a new tool trace list with the given traces appended."""
    return [*state.get("tool_trace", []), *traces]
