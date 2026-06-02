import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.nodes.actor import _run_tool_calling_loop


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
