"""
Verifier agent node.

The verifier is the Harness gate after adjustment. It checks that proposed
actions are auditable, confirmation-gated, and safe enough to show to users.
"""

from typing import Any

from app.agent.state import AgentState
from app.agent.trace import append_trace, duration_ms, make_step_trace, start_timer
from app.core.logging import get_logger

logger = get_logger(__name__)


def verify_agent_state(state: AgentState) -> dict[str, Any]:
    """Return verifier status, findings, and a compact harness score."""
    findings: list[dict[str, Any]] = []
    plan_diff = state.get("plan_diff") or []
    safety_warnings = state.get("safety_warnings") or []
    action_cards = state.get("action_cards") or []
    trace = state.get("trace") or []
    model_status = state.get("model_status") or {}
    nodes = {step.get("node") for step in trace}

    if model_status.get("available") is False:
        findings.append({
            "level": "error",
            "code": "model_provider_unavailable",
            "message": model_status.get("message") or "模型供应商当前不可用。",
            "evidence": {
                "provider": model_status.get("provider"),
                "status_code": model_status.get("status_code"),
                "provider_code": model_status.get("code"),
                "request_id": model_status.get("request_id"),
            },
        })
    elif state.get("error"):
        findings.append({
            "level": "error",
            "code": "agent_error",
            "message": state.get("error") or "Agent 运行失败。",
            "evidence": {},
        })

    for warning in safety_warnings:
        if warning.get("level") == "danger":
            findings.append({
                "level": "danger",
                "code": "danger_safety_warning",
                "message": "存在 danger 级安全警告，需要人工确认。",
                "evidence": {"rule": warning.get("rule")},
            })

    for item in plan_diff:
        if item.get("requires_confirmation") is not True:
            findings.append({
                "level": "error",
                "code": "plan_diff_missing_confirmation",
                "message": "计划变更缺少 requires_confirmation=true。",
                "evidence": {"field": item.get("field")},
            })

    if plan_diff and not any(card.get("type") == "apply_plan_diff" for card in action_cards):
        findings.append({
            "level": "error",
            "code": "missing_apply_plan_diff_action",
            "message": "存在计划变更，但缺少应用计划变更的 action card。",
            "evidence": {"plan_diff_count": len(plan_diff)},
        })

    if "planner" not in nodes:
        findings.append({
            "level": "warning",
            "code": "missing_planner_trace",
            "message": "运行轨迹缺少 planner 节点。",
            "evidence": {"nodes": sorted(node for node in nodes if node)},
        })

    if any(item["level"] == "error" for item in findings):
        status = "failed"
    elif plan_diff or any(item["level"] == "danger" for item in findings):
        status = "needs_user_confirmation"
    else:
        status = "passed"

    score = 100
    for finding in findings:
        if finding["level"] == "error":
            score -= 30
        elif finding["level"] == "danger":
            score -= 20
        elif finding["level"] == "warning":
            score -= 10
    score = max(0, score)
    if model_status.get("available") is False:
        score = 0

    return {
        "verification_status": status,
        "verification_findings": findings,
        "harness_score": score,
    }


async def verify_node(state: AgentState) -> dict[str, Any]:
    """Verify the current agent run before returning it to the user."""
    logger.info(f"Verifier node executing for run {state.get('run_id')}")
    started_at, started = start_timer()
    verification = verify_agent_state(state)
    return {
        **verification,
        "trace": append_trace(
            state,
            make_step_trace(
                node="verifier",
                title="Harness 验证",
                status=verification["verification_status"],
                decision=verification["verification_status"],
                reasoning="检查计划变更、安全警告、动作卡片和运行轨迹是否满足 Harness 约束。",
                input_summary={
                    "plan_diff": len(state.get("plan_diff") or []),
                    "safety_warnings": len(state.get("safety_warnings") or []),
                    "action_cards": len(state.get("action_cards") or []),
                },
                output_summary={
                    "findings": len(verification["verification_findings"]),
                    "harness_score": verification["harness_score"],
                },
                confidence=0.9,
                started_at=started_at,
                elapsed_ms=duration_ms(started),
            ),
        ),
    }
