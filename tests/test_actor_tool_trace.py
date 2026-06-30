import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.nodes.actor import _run_tool_calling_loop
from app.agent.nodes.actor import act_node
from app.llm.errors import LLMProviderError


@pytest.mark.asyncio
async def test_tool_calling_loop_returns_observable_tool_trace():
    llm_responses = [
        {
            "content": "",
            "tool_calls": [
                {
                    "id": "call-1",
                    "function": {
                        "name": "calculate_macros",
                        "arguments": json.dumps({
                            "user_id": "user-1",
                            "day_type": "high_carb",
                            "target_calories": 2400,
                        }),
                    },
                }
            ],
        },
        {"content": "分析完成"},
    ]

    with patch("app.agent.nodes.actor.get_llm_client") as mock_llm, \
         patch("app.llm.tool_executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_execute:
        mock_llm.return_value.chat = AsyncMock(side_effect=llm_responses)
        mock_execute.return_value = json.dumps({"macros": {"carbs_g": 300}})

        response, traces = await _run_tool_calling_loop(
            messages=[{"role": "user", "content": "analyze"}],
            db_session=AsyncMock(),
            tool_names=["calculate_macros"],
        )

    assert response["content"] == "分析完成"
    assert traces[0]["tool_name"] == "calculate_macros"
    assert traces[0]["status"] == "success"
    assert traces[0]["result"]["macros"]["carbs_g"] == 300


@pytest.mark.asyncio
async def test_actor_tool_calling_failure_falls_back_without_global_model_failure():
    state = {
        "run_id": "run-1",
        "user": {"user_id": "user-1", "name": "Test"},
        "plan": {"target_calories": 2000, "day_type": "medium_carb"},
        "logs": [],
        "db_session": AsyncMock(),
        "trace": [],
        "tool_trace": [],
        "model_status": {"available": True, "provider": "gemini"},
    }

    with patch(
        "app.agent.nodes.actor._run_tool_calling_loop",
        side_effect=LLMProviderError(
            message="tool calling unavailable",
            code="provider_error",
            provider="gemini",
        ),
    ):
        result = await act_node(state)

    assert "model_status" not in result
    assert result["tool_trace"][0]["tool_name"] == "actor_tool_loop"
    assert result["tool_trace"][0]["status"] == "error"
