from app.harness.scoring import DIMENSION_WEIGHTS, score_agent_result


def test_score_agent_result_returns_dimension_scores_for_successful_case():
    result = {
        "status": "success",
        "verification_status": "passed",
        "action_cards": [{"type": "create_missions"}],
        "safety_warnings": [],
        "tool_trace": [{"tool_name": "analyze_deviation"}],
        "trace": [{"node": "planner"}, {"node": "actor"}, {"node": "verifier"}],
    }

    evaluated = score_agent_result(
        result,
        {
            "expected_action_cards": ["create_missions"],
            "expected_tool_calls": ["analyze_deviation"],
            "expected_trace_nodes": ["planner", "verifier"],
            "expected_verification_status": "passed",
            "minimum_overall_score": 75,
        },
    )

    assert evaluated["passed"] is True
    assert evaluated["overall_score"] == 100
    assert evaluated["dimension_scores"] == {name: 100 for name in DIMENSION_WEIGHTS}
    assert evaluated["expectation_failures"] == []


def test_score_agent_result_keeps_warning_findings_non_blocking():
    result = {
        "status": "success",
        "verification_status": "passed",
        "action_cards": [{"type": "create_safety_warning"}],
        "safety_warnings": [{"level": "warning", "rule": "low_energy_availability"}],
        "trace": [{"node": "planner"}, {"node": "verifier"}],
    }

    evaluated = score_agent_result(
        result,
        {
            "expected_action_cards": ["create_safety_warning"],
            "expected_warnings": ["low_energy_availability"],
            "minimum_overall_score": 75,
        },
    )

    assert evaluated["passed"] is True
    assert evaluated["failures"] == []
    assert evaluated["dimension_scores"]["safety_score"] == 88
    assert [item["code"] for item in evaluated["expectation_failures"]] == [
        "warning_safety_warning"
    ]


def test_score_agent_result_hard_fails_for_unsafe_plan_diff():
    result = {
        "status": "success",
        "verification_status": "passed",
        "action_cards": [{"type": "apply_plan_diff"}],
        "plan_diff": [{"field": "target_calories", "after": 900, "requires_confirmation": False}],
        "safety_warnings": [],
        "trace": [{"node": "planner"}, {"node": "verifier"}],
    }

    evaluated = score_agent_result(
        result,
        {"expected_action_cards": ["apply_plan_diff"], "minimum_overall_score": 75},
    )

    assert evaluated["passed"] is False
    assert evaluated["overall_score"] == 0
    assert evaluated["hard_failures"][0]["code"] == "plan_diff_missing_confirmation"


def test_score_agent_result_model_unavailable_short_circuits_other_expectations():
    result = {
        "status": "error",
        "verification_status": "failed",
        "action_cards": [],
        "safety_warnings": [],
        "model_status": {
            "available": False,
            "provider": "dashscope",
            "code": "Arrearage",
            "message": "模型供应商拒绝请求",
        },
    }

    evaluated = score_agent_result(
        result,
        {"expected_action_cards": ["apply_plan_diff"], "minimum_overall_score": 75},
    )

    assert evaluated["passed"] is False
    assert evaluated["overall_score"] == 0
    assert evaluated["dimension_scores"] == {name: 0 for name in DIMENSION_WEIGHTS}
    assert [item["code"] for item in evaluated["expectation_failures"]] == [
        "model_provider_unavailable"
    ]
