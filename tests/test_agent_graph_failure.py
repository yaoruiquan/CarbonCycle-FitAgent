import pytest

from app.agent import graph as agent_graph


class FakeGraph:
    async def ainvoke(self, initial_state):
        return {
            **initial_state,
            "error": "模型供应商拒绝请求",
            "model_status": {
                "available": False,
                "provider": "dashscope",
                "code": "Arrearage",
                "message": "模型供应商拒绝请求",
            },
            "trace": [{"node": "planner", "status": "error"}],
        }


@pytest.mark.asyncio
async def test_run_agent_error_result_is_verified(monkeypatch):
    monkeypatch.setattr(agent_graph, "get_agent_graph", lambda: FakeGraph())

    result = await agent_graph.run_agent(
        user_id="user-1",
        trigger="manual",
        user_context={"user_id": "user-1", "name": "Test"},
        plan_context={},
        logs=[],
    )

    assert result["status"] == "error"
    assert result["verification_status"] == "failed"
    assert result["harness_score"] == 0
    assert result["model_status"]["code"] == "Arrearage"
    assert any(
        item["code"] == "model_provider_unavailable"
        for item in result["verification_findings"]
    )
