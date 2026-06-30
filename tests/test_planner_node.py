from unittest.mock import AsyncMock, Mock

import pytest

from app.agent.nodes import planner


@pytest.mark.asyncio
async def test_planner_runtime_error_is_not_reported_as_provider_failure(monkeypatch):
    monkeypatch.setattr(planner, "retrieve_context", AsyncMock(return_value=""))
    mock_llm = Mock()
    mock_llm.plan = AsyncMock(side_effect=ValueError("bad planner state"))
    monkeypatch.setattr(planner, "get_llm_client", lambda: mock_llm)

    result = await planner.plan_node({
        "run_id": "run-1",
        "user": {"user_id": "user-1", "name": "Test"},
        "plan": {"cycle_length": 7},
        "messages": [],
        "trace": [],
    })

    assert result["error"] == "bad planner state"
    assert "model_status" not in result
    assert result["planner_output"]["status"] == "error"
    assert result["trace"][0]["output_summary"]["code"] == "planner_runtime_error"
