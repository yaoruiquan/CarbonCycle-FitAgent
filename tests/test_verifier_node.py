import pytest

from app.agent.nodes.verifier import verify_agent_state, verify_node


def test_verifier_passes_clean_run():
    result = verify_agent_state({
        "trace": [{"node": "planner"}],
        "plan_diff": [],
        "safety_warnings": [],
        "action_cards": [],
    })

    assert result["verification_status"] == "passed"
    assert result["harness_score"] == 100


def test_verifier_requires_confirmation_for_plan_diff():
    result = verify_agent_state({
        "trace": [{"node": "planner"}],
        "plan_diff": [{"field": "target_calories", "requires_confirmation": True}],
        "safety_warnings": [],
        "action_cards": [{"type": "apply_plan_diff"}],
    })

    assert result["verification_status"] == "needs_user_confirmation"


def test_verifier_fails_missing_confirmation():
    result = verify_agent_state({
        "trace": [{"node": "planner"}],
        "plan_diff": [{"field": "target_calories"}],
        "safety_warnings": [],
        "action_cards": [{"type": "apply_plan_diff"}],
    })

    assert result["verification_status"] == "failed"
    assert any(item["code"] == "plan_diff_missing_confirmation" for item in result["verification_findings"])


def test_verifier_flags_danger_warning():
    result = verify_agent_state({
        "trace": [{"node": "planner"}],
        "plan_diff": [],
        "safety_warnings": [{"level": "danger", "rule": "minimum_calorie_floor"}],
        "action_cards": [],
    })

    assert result["verification_status"] == "needs_user_confirmation"
    assert any(item["code"] == "danger_safety_warning" for item in result["verification_findings"])


def test_verifier_fails_model_provider_unavailable():
    result = verify_agent_state({
        "trace": [{"node": "planner"}],
        "model_status": {
            "available": False,
            "provider": "dashscope",
            "code": "Arrearage",
            "message": "模型供应商拒绝请求",
        },
        "plan_diff": [],
        "safety_warnings": [],
        "action_cards": [],
    })

    assert result["verification_status"] == "failed"
    assert result["harness_score"] == 0
    assert any(item["code"] == "model_provider_unavailable" for item in result["verification_findings"])


@pytest.mark.asyncio
async def test_verify_node_appends_trace():
    result = await verify_node({
        "trace": [{"node": "planner"}],
        "plan_diff": [],
        "safety_warnings": [],
        "action_cards": [],
    })

    assert result["trace"][-1]["node"] == "verifier"
    assert result["verification_status"] == "passed"
