"""
Harness episode snapshots.

An episode captures the inputs, runtime configuration, and observable output
summary for one agent run. It is intentionally stored as JSON-compatible data
so it can be persisted inside existing run payloads.
"""

from typing import Any


GRAPH_VERSION = "planner-actor-reflector-adjuster-verifier:v1"
PROMPT_VERSION = "prompts:v1"
TOOL_POLICY_VERSION = "tool-policy:v1"
SAFETY_POLICY_VERSION = "nutrition-safety:v1"


def build_harness_episode(
    *,
    run_id: str,
    trigger: str,
    user_context: dict[str, Any],
    plan_context: dict[str, Any],
    logs: list[dict[str, Any]],
    memory_context: dict[str, Any],
    evaluation_summary: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build a compact, replayable episode snapshot for one agent run."""
    trace = result.get("trace") or []
    tool_trace = result.get("tool_trace") or []
    plan_diff = result.get("plan_diff") or []
    safety_warnings = result.get("safety_warnings") or []
    action_cards = result.get("action_cards") or []
    missions = result.get("missions") or []
    dimension_scores = result.get("dimension_scores") or {}

    return {
        "episode_id": run_id,
        "trigger": trigger,
        "input_snapshot": {
            "user_context": user_context,
            "plan_context": plan_context,
            "logs": logs,
            "memory_context": memory_context or {},
            "evaluation_summary": evaluation_summary or {},
        },
        "runtime_config": {
            "model_provider": "configured_llm_client",
            "graph_version": GRAPH_VERSION,
            "prompt_version": PROMPT_VERSION,
            "tool_policy_version": TOOL_POLICY_VERSION,
            "safety_policy_version": SAFETY_POLICY_VERSION,
        },
        "output_summary": {
            "status": result.get("status"),
            "latency_ms": result.get("latency_ms"),
            "trace_count": len(trace),
            "tool_call_count": len(tool_trace),
            "plan_diff_count": len(plan_diff),
            "warning_count": len(safety_warnings),
            "action_card_count": len(action_cards),
            "mission_count": len(missions),
            "verification_status": result.get("verification_status"),
            "harness_score": result.get("harness_score"),
            "dimension_scores": dimension_scores,
            "expectation_failures": result.get("expectation_failures") or [],
            "trace_nodes": [item.get("node") for item in trace],
            "tool_names": [item.get("tool_name") for item in tool_trace],
            "action_types": [item.get("type") for item in action_cards],
        },
    }
