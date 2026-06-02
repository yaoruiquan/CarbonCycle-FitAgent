import pytest

from app.services.agent_observability import AgentObservabilityService


@pytest.mark.asyncio
async def test_persist_run_stores_trace_and_proposed_missions(db):
    service = AgentObservabilityService(db)
    result = {
        "run_id": "run-1",
        "status": "success",
        "latency_ms": 123,
        "trace": [
            {
                "node": "planner",
                "title": "计划生成",
                "status": "success",
                "decision": "generate_plan",
                "reasoning": "test",
                "input_summary": {"goal": "fat_loss"},
                "output_summary": {"knowledge_used": True},
                "confidence": 0.8,
                "duration_ms": 10,
            }
        ],
        "tool_trace": [
            {
                "tool_name": "get_user_history",
                "arguments": {"user_id": "user-1"},
                "result": {"period_days": 7},
                "status": "success",
                "duration_ms": 5,
            }
        ],
        "missions": [
            {
                "id": "mission-1",
                "title": "补足蛋白",
                "description": "每餐补充优质蛋白",
                "due_date": "2026-06-03",
                "next_action": "记录下一餐",
                "evidence": ["餐食记录"],
            }
        ],
        "plan_diff": [{"field": "target_calories", "before": 2000, "after": 1900}],
        "safety_warnings": [],
        "action_cards": [],
        "memory_context": {"recent_preferred_foods": ["鸡胸肉"]},
        "evaluation_summary": {"artifact_count": 1},
    }

    persisted = await service.persist_run("user-1", "manual", result)
    missions = await service.list_missions("user-1")

    assert persisted["run_id"] == "run-1"
    assert persisted["trace"][0]["node"] == "planner"
    assert persisted["tool_trace"][0]["tool_name"] == "get_user_history"
    assert persisted["plan_diff"][0]["field"] == "target_calories"
    assert missions[0]["status"] == "proposed"


@pytest.mark.asyncio
async def test_build_memory_context_includes_stored_memories(db):
    service = AgentObservabilityService(db)
    await service.upsert_memory(
        user_id="user-1",
        category="food_preference",
        key="oats",
        value={"food": "oats"},
        confidence=0.7,
        source="test",
    )

    memory = await service.build_memory_context("user-1")

    assert memory["memory_count"] == 1
    assert memory["memories"][0]["category"] == "food_preference"
