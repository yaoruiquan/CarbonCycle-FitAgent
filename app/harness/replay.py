"""
Replay and compare historical Harness episodes.
"""

from typing import Any

from app.agent import graph as agent_graph
from app.services.agent_observability import AgentObservabilityService


async def replay_agent_run(
    *,
    run_id: str,
    observability: AgentObservabilityService,
    db_session: Any = None,
) -> dict[str, Any]:
    """Replay a persisted run from its harness episode input snapshot."""
    original = await observability.get_run(run_id)
    if not original:
        return {"status": "not_found", "message": "Agent run not found"}

    episode = original.get("harness_episode") or (original.get("evaluation_summary") or {}).get("harness_episode")
    if not episode:
        return {"status": "missing_episode", "message": "Agent run does not contain a harness episode"}

    snapshot = episode.get("input_snapshot") or {}
    replayed = await agent_graph.run_agent(
        user_id=str(snapshot.get("user_context", {}).get("user_id", original.get("user_id", ""))),
        trigger=f"replay:{original.get('trigger', 'unknown')}",
        user_context=snapshot.get("user_context") or {},
        plan_context=snapshot.get("plan_context") or {},
        logs=snapshot.get("logs") or [],
        db_session=db_session,
        memory_context=snapshot.get("memory_context") or {},
        evaluation_summary={"source": "harness_replay", "original_run_id": run_id},
    )

    return {
        "status": "success",
        "original_run_id": run_id,
        "replay_run_id": replayed.get("run_id"),
        "comparison": compare_runs(original, replayed),
        "replayed": replayed,
    }


def compare_runs(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    """Compare high-signal Harness run outputs."""
    original_nodes = [step.get("node") for step in original.get("trace") or []]
    replay_nodes = [step.get("node") for step in replayed.get("trace") or []]
    original_warnings = [item.get("rule") for item in original.get("safety_warnings") or []]
    replay_warnings = [item.get("rule") for item in replayed.get("safety_warnings") or []]
    return {
        "trace_nodes_match": original_nodes == replay_nodes,
        "original_trace_nodes": original_nodes,
        "replay_trace_nodes": replay_nodes,
        "tool_call_delta": len(replayed.get("tool_trace") or []) - len(original.get("tool_trace") or []),
        "plan_diff_delta": len(replayed.get("plan_diff") or []) - len(original.get("plan_diff") or []),
        "warning_rules_added": sorted(set(replay_warnings) - set(original_warnings)),
        "warning_rules_removed": sorted(set(original_warnings) - set(replay_warnings)),
        "harness_score_delta": int(replayed.get("harness_score") or 0) - int(original.get("harness_score") or 0),
        "score_delta_by_dimension": _score_delta_by_dimension(original, replayed),
        "regression": _is_regression(original, replayed),
    }


def _score_delta_by_dimension(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, int]:
    original_scores = original.get("dimension_scores") or {}
    replay_scores = replayed.get("dimension_scores") or {}
    if not original_scores:
        original_scores = ((original.get("harness_episode") or {}).get("output_summary") or {}).get("dimension_scores") or {}
    dimensions = sorted(set(original_scores) | set(replay_scores))
    return {
        dimension: int(replay_scores.get(dimension, 0)) - int(original_scores.get(dimension, 0))
        for dimension in dimensions
    }


def _is_regression(original: dict[str, Any], replayed: dict[str, Any]) -> bool:
    original_passed = original.get("passed")
    replay_passed = replayed.get("passed")
    if original_passed is True and replay_passed is False:
        return True
    score_delta = int(replayed.get("harness_score") or 0) - int(original.get("harness_score") or 0)
    return score_delta < -10
