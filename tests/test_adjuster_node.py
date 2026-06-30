from unittest.mock import AsyncMock

import pytest

from app.agent.nodes import adjuster


@pytest.mark.asyncio
async def test_adjuster_creates_missions_without_plan_diff_for_protein_only(monkeypatch):
    monkeypatch.setattr(adjuster, "_generate_smart_suggestions", AsyncMock(return_value=[]))

    result = await adjuster.adjust_node({
        "run_id": "run-1",
        "user": {"user_id": "user-1", "goal": "recomposition"},
        "plan": {"target_calories": 1850, "target_protein": 130},
        "reflection": {
            "severity": "minor",
            "deviation_type": "protein_low",
            "calorie_deviation_pct": -3.8,
            "protein_deviation_pct": -38.5,
            "needs_adjustment": True,
            "patterns": ["蛋白质摄入不足"],
        },
        "trends": {"training_completion_rate": 100},
        "trace": [],
    })

    action_types = [card["type"] for card in result["action_cards"]]
    assert "create_missions" in action_types
    assert "apply_plan_diff" not in action_types
    assert result["plan_diff"] == []
    assert result["adjustment"]["calorie_adjustment"] == 0


@pytest.mark.asyncio
async def test_adjuster_creates_missions_without_plan_diff_for_training_skip(monkeypatch):
    monkeypatch.setattr(adjuster, "_generate_smart_suggestions", AsyncMock(return_value=[]))

    result = await adjuster.adjust_node({
        "run_id": "run-1",
        "user": {"user_id": "user-1", "goal": "maintenance"},
        "plan": {"target_calories": 2500, "target_protein": 160},
        "reflection": {
            "severity": "minor",
            "deviation_type": "calorie_deficit",
            "calorie_deviation_pct": -0.8,
            "protein_deviation_pct": -3.1,
            "needs_adjustment": True,
            "patterns": ["训练计划执行率低"],
        },
        "trends": {"training_completion_rate": 0},
        "trace": [],
    })

    action_types = [card["type"] for card in result["action_cards"]]
    assert "create_missions" in action_types
    assert "apply_plan_diff" not in action_types
    assert result["plan_diff"] == []
    assert result["adjustment"]["calorie_adjustment"] == 0
