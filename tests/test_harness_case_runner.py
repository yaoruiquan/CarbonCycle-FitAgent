from pathlib import Path
from types import SimpleNamespace

import pytest

from app.harness import case_runner


def test_list_harness_cases_loads_default_cases():
    cases = case_runner.list_harness_cases()

    assert len(cases) >= 35
    assert {case["id"] for case in cases} >= {
        "calorie_overrun",
        "protein_deficit",
        "skipped_training",
        "under_eating_risk",
        "no_logs_checkin",
    }
    assert all(case["category"] for case in cases)
    assert all(case["difficulty"] for case in cases)
    assert all(isinstance(case["tags"], list) for case in cases)


def test_validate_harness_case_rejects_missing_fields():
    with pytest.raises(ValueError):
        case_runner.validate_harness_case({"id": "bad"})


def test_validate_harness_case_rejects_invalid_metadata():
    case = {
        "id": "bad-meta",
        "title": "Bad metadata",
        "category": "unknown",
        "difficulty": "regression",
        "tags": [],
        "trigger": "manual",
        "user_context": {},
        "plan_context": {},
        "logs": [],
        "expectations": {},
    }

    with pytest.raises(ValueError, match="invalid category"):
        case_runner.validate_harness_case(case)


def test_evaluate_expectations_reports_missing_action():
    result = {
        "status": "success",
        "verification_status": "passed",
        "harness_score": 100,
        "action_cards": [],
        "safety_warnings": [],
    }

    evaluated = case_runner.evaluate_expectations(
        result,
        {"expected_action_cards": ["apply_plan_diff"], "minimum_harness_score": 70},
    )

    assert evaluated["passed"] is False
    assert evaluated["failures"]
    assert evaluated["dimension_scores"]["actionability_score"] < 100


def test_evaluate_expectations_prioritizes_model_provider_error():
    result = {
        "status": "error",
        "verification_status": "failed",
        "harness_score": 0,
        "action_cards": [],
        "safety_warnings": [],
        "model_status": {
            "available": False,
            "provider": "dashscope",
            "code": "Arrearage",
            "message": "模型供应商拒绝请求",
        },
    }

    evaluated = case_runner.evaluate_expectations(
        result,
        {"expected_action_cards": ["apply_plan_diff"], "minimum_harness_score": 70},
    )

    assert evaluated["passed"] is False
    assert evaluated["failures"] == [
        "Model provider unavailable (Arrearage): 模型供应商拒绝请求"
    ]


@pytest.mark.asyncio
async def test_run_harness_cases_writes_summary(monkeypatch, tmp_path: Path):
    async def fake_run_agent(**kwargs):
        return {
            "run_id": "run-1",
            "status": "success",
            "trace": [{"node": "planner"}],
            "tool_trace": [],
            "safety_warnings": [],
            "action_cards": [{"type": "create_missions"}],
            "harness_score": 95,
            "verification_status": "passed",
        }

    monkeypatch.setattr(case_runner.agent_graph, "run_agent", fake_run_agent)

    summary = await case_runner.run_harness_cases(
        case_ids=["no_logs_checkin"],
        output_dir=tmp_path,
    )

    assert summary["total"] == 1
    assert summary["passed"] == 1
    assert summary["average_dimension_scores"]
    assert summary["category_summary"]["data_quality"]["total"] == 1
    assert summary["difficulty_summary"]["smoke"]["total"] == 1
    assert summary["results"][0]["category"] == "data_quality"
    assert summary["results"][0]["dimension_scores"]
    assert Path(summary["report_path"]).exists()


@pytest.mark.asyncio
async def test_run_harness_cases_retries_rate_limited_case(monkeypatch, tmp_path: Path):
    calls = 0
    sleeps = []

    monkeypatch.setattr(
        case_runner,
        "list_harness_cases",
        lambda: [{
            "id": "rate-limit-case",
            "title": "Rate limit case",
            "category": "data_quality",
            "difficulty": "smoke",
            "tags": [],
            "trigger": "manual",
            "user_context": {"user_id": "user-1"},
            "plan_context": {},
            "logs": [],
            "expectations": {
                "expected_trace_nodes": ["planner", "verifier"],
                "minimum_harness_score": 75,
            },
        }],
    )
    monkeypatch.setattr(
        case_runner,
        "get_settings",
        lambda: SimpleNamespace(
            harness_case_delay_seconds=0,
            harness_rate_limit_retry_count=1,
            harness_rate_limit_retry_delay_seconds=9,
        ),
    )

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    async def fake_run_agent(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "run_id": "run-1",
                "status": "error",
                "trace": [{"node": "planner"}, {"node": "verifier"}],
                "tool_trace": [],
                "safety_warnings": [],
                "action_cards": [],
                "harness_score": 0,
                "verification_status": "failed",
                "model_status": {
                    "available": False,
                    "provider": "gemini",
                    "status_code": 429,
                    "code": "rate_limited",
                    "retry_after_seconds": 3,
                    "message": "模型供应商限流",
                },
            }
        return {
            "run_id": "run-2",
            "status": "success",
            "trace": [{"node": "planner"}, {"node": "verifier"}],
            "tool_trace": [],
            "safety_warnings": [],
            "action_cards": [],
            "harness_score": 95,
            "verification_status": "passed",
            "model_status": {"available": True, "provider": "gemini"},
        }

    monkeypatch.setattr(case_runner.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(case_runner.agent_graph, "run_agent", fake_run_agent)

    summary = await case_runner.run_harness_cases(
        case_ids=["rate-limit-case"],
        output_dir=tmp_path,
    )

    assert calls == 2
    assert sleeps == [3]
    assert summary["passed"] == 1
    assert summary["results"][0]["retry_count"] == 1
