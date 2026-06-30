from app.harness.episode import build_harness_episode


def test_build_harness_episode_captures_inputs_and_summary():
    result = {
        "status": "success",
        "latency_ms": 42,
        "trace": [{"node": "planner"}],
        "tool_trace": [{"tool_name": "calculate_macros"}],
        "plan_diff": [{"field": "target_calories"}],
        "safety_warnings": [{"rule": "deficit_cap"}],
        "action_cards": [{"type": "apply_plan_diff"}],
        "missions": [{"id": "mission-1"}],
        "verification_status": "needs_user_confirmation",
        "harness_score": 90,
    }

    episode = build_harness_episode(
        run_id="run-1",
        trigger="manual",
        user_context={"user_id": "u1"},
        plan_context={"plan_id": "p1"},
        logs=[{"date": "2026-06-19"}],
        memory_context={"memory_count": 1},
        evaluation_summary={},
        result=result,
    )

    assert episode["episode_id"] == "run-1"
    assert episode["input_snapshot"]["user_context"]["user_id"] == "u1"
    assert episode["runtime_config"]["graph_version"].endswith(":v1")
    assert episode["output_summary"]["trace_count"] == 1
    assert episode["output_summary"]["tool_call_count"] == 1
    assert episode["output_summary"]["harness_score"] == 90
