from unittest.mock import AsyncMock

import pytest

from app.agent.nodes import reflector


@pytest.mark.asyncio
async def test_reflector_routes_protein_deficit_to_adjuster(monkeypatch):
    monkeypatch.setattr(
        reflector,
        "_generate_reflection_summary",
        AsyncMock(return_value="蛋白质摄入不足，需要跟踪任务。"),
    )

    result = await reflector.reflect_node({
        "run_id": "run-1",
        "plan": {"target_calories": 1850, "target_protein": 130},
        "actor_output": {
            "status": "success",
            "actual_intake": {"calories": 1780, "protein": 80},
            "training_completed": True,
        },
        "logs": [{
            "date": "2026-06-19",
            "actual_calories": 1780,
            "actual_protein": 80,
            "actual_carbs": 210,
            "actual_fat": 58,
            "training_completed": True,
            "meal_count": 3,
        }],
        "trace": [],
    })

    assert result["should_adjust"] is True
    assert result["reflection"]["needs_adjustment"] is True
    assert "蛋白质摄入不足" in result["reflection"]["patterns"]


@pytest.mark.asyncio
async def test_reflector_routes_skipped_training_to_adjuster(monkeypatch):
    monkeypatch.setattr(
        reflector,
        "_generate_reflection_summary",
        AsyncMock(return_value="跳过训练，需要保底任务。"),
    )

    result = await reflector.reflect_node({
        "run_id": "run-1",
        "plan": {"target_calories": 2500, "target_protein": 160},
        "actor_output": {
            "status": "success",
            "actual_intake": {"calories": 2480, "protein": 155},
            "training_completed": False,
        },
        "logs": [{
            "date": "2026-06-19",
            "actual_calories": 2480,
            "actual_protein": 155,
            "actual_carbs": 300,
            "actual_fat": 72,
            "training_completed": False,
            "meal_count": 4,
        }],
        "trace": [],
    })

    assert result["should_adjust"] is True
    assert result["reflection"]["needs_adjustment"] is True
    assert "训练计划执行率低" in result["reflection"]["patterns"]
