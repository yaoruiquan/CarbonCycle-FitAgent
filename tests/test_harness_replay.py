import pytest

from app.harness import replay


class FakeObservability:
    def __init__(self, run):
        self.run = run

    async def get_run(self, run_id):
        return self.run


@pytest.mark.asyncio
async def test_replay_missing_run_returns_not_found():
    result = await replay.replay_agent_run(
        run_id="missing",
        observability=FakeObservability(None),
    )

    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_replay_missing_episode_returns_error():
    result = await replay.replay_agent_run(
        run_id="run-1",
        observability=FakeObservability({"run_id": "run-1"}),
    )

    assert result["status"] == "missing_episode"


@pytest.mark.asyncio
async def test_replay_compares_runs(monkeypatch):
    original = {
        "run_id": "run-1",
        "user_id": "user-1",
        "trigger": "manual",
        "trace": [{"node": "planner"}],
        "tool_trace": [],
        "plan_diff": [],
        "safety_warnings": [{"rule": "old_rule"}],
        "harness_score": 80,
        "harness_episode": {
            "input_snapshot": {
                "user_context": {"user_id": "user-1"},
                "plan_context": {},
                "logs": [],
                "memory_context": {},
            }
        },
    }

    async def fake_run_agent(**kwargs):
        return {
            "run_id": "run-2",
            "trace": [{"node": "planner"}, {"node": "verifier"}],
            "tool_trace": [{"tool_name": "x"}],
            "plan_diff": [{"field": "target_calories"}],
            "safety_warnings": [{"rule": "new_rule"}],
            "harness_score": 90,
        }

    monkeypatch.setattr(replay.agent_graph, "run_agent", fake_run_agent)

    result = await replay.replay_agent_run(
        run_id="run-1",
        observability=FakeObservability(original),
    )

    assert result["status"] == "success"
    assert result["comparison"]["tool_call_delta"] == 1
    assert result["comparison"]["warning_rules_added"] == ["new_rule"]
    assert result["comparison"]["harness_score_delta"] == 10
    assert result["comparison"]["score_delta_by_dimension"] == {}
    assert result["comparison"]["regression"] is False


def test_compare_runs_reports_dimension_regression():
    comparison = replay.compare_runs(
        {
            "passed": True,
            "harness_score": 92,
            "dimension_scores": {"safety_score": 100, "task_success_score": 95},
        },
        {
            "passed": False,
            "harness_score": 70,
            "dimension_scores": {"safety_score": 70, "task_success_score": 85},
        },
    )

    assert comparison["harness_score_delta"] == -22
    assert comparison["score_delta_by_dimension"] == {
        "safety_score": -30,
        "task_success_score": -10,
    }
    assert comparison["regression"] is True
