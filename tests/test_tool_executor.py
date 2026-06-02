"""
Tests for the Tool Executor.

Tests tool dispatch and execution logic without requiring LLM calls.
"""

import json

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.llm.tool_executor import ToolExecutor
from app.llm.tools import (
    TOOL_CALCULATE_MACROS,
    TOOL_QUERY_FOOD,
    TOOL_ANALYZE_DEVIATION,
    TOOL_GET_USER_HISTORY,
    TOOL_SUGGEST_ADJUSTMENT,
)


@pytest.fixture
def mock_db():
    """Create a mock DB session."""
    return AsyncMock()


@pytest.fixture
def executor(mock_db):
    """Create a ToolExecutor with a mocked DB session."""
    return ToolExecutor(mock_db)


# ---------- calculate_macros ----------

@pytest.mark.asyncio
async def test_calculate_macros_high_carb(executor):
    """Test macro calculation for high carb day."""
    with patch.object(executor.storage, 'get_user', new_callable=AsyncMock) as mock_user:
        mock_user.return_value = MagicMock(weight_kg=75.0)

        result_str = await executor.execute(TOOL_CALCULATE_MACROS, {
            "user_id": "user-1",
            "day_type": "high_carb",
            "target_calories": 2400,
        })

    result = json.loads(result_str)
    assert result["day_type"] == "high_carb"
    assert result["target_calories"] == 2400
    assert result["macros"]["protein_g"] == 150.0  # 2400 * 0.25 / 4
    assert result["macros"]["carbs_g"] == 300.0    # 2400 * 0.50 / 4
    assert result["macros"]["fat_g"] == pytest.approx(66.7, abs=0.1)  # 2400 * 0.25 / 9


@pytest.mark.asyncio
async def test_calculate_macros_low_carb(executor):
    """Test macro calculation for low carb day."""
    with patch.object(executor.storage, 'get_user', new_callable=AsyncMock) as mock_user:
        mock_user.return_value = MagicMock(weight_kg=70.0)

        result_str = await executor.execute(TOOL_CALCULATE_MACROS, {
            "user_id": "user-1",
            "day_type": "low_carb",
            "target_calories": 2000,
        })

    result = json.loads(result_str)
    assert result["macros"]["protein_g"] == 200.0   # 2000 * 0.40 / 4
    assert result["macros"]["carbs_g"] == 100.0      # 2000 * 0.20 / 4
    assert result["macros"]["fat_g"] == pytest.approx(88.9, abs=0.1)  # 2000 * 0.40 / 9


# ---------- query_food ----------

@pytest.mark.asyncio
async def test_query_food_success(executor):
    """Test food nutrition query with mocked LLM."""
    mock_response = {
        "content": '{"carbs_g": 25, "protein_g": 30, "fat_g": 8, "fiber_g": 2}'
    }
    with patch("app.llm.tool_executor.get_llm_client") as mock_llm:
        mock_llm.return_value.chat = AsyncMock(return_value=mock_response)
        result_str = await executor.execute(TOOL_QUERY_FOOD, {
            "food_name": "鸡胸肉",
            "quantity_g": 200,
        })

    result = json.loads(result_str)
    assert result["food_name"] == "鸡胸肉"
    assert result["quantity_g"] == 200
    assert result["protein_g"] == 30
    assert result["carbs_g"] == 25
    assert result["calories"] == 25 * 4 + 30 * 4 + 8 * 9  # 292


@pytest.mark.asyncio
async def test_query_food_fallback(executor):
    """Test food query falls back gracefully on LLM failure."""
    with patch("app.llm.tool_executor.get_llm_client") as mock_llm:
        mock_llm.return_value.chat = AsyncMock(side_effect=Exception("LLM error"))
        result_str = await executor.execute(TOOL_QUERY_FOOD, {
            "food_name": "unknown",
            "quantity_g": 100,
        })

    result = json.loads(result_str)
    assert result["food_name"] == "unknown"
    # Should use fallback ratios
    assert result["carbs_g"] == 15.0    # 100 * 0.15
    assert result["protein_g"] == 10.0  # 100 * 0.10
    assert result["fat_g"] == 5.0       # 100 * 0.05


# ---------- suggest_adjustment ----------

@pytest.mark.asyncio
async def test_suggest_adjustment_calorie_excess(executor):
    """Test adjustment suggestion for calorie excess."""
    result_str = await executor.execute(TOOL_SUGGEST_ADJUSTMENT, {
        "user_id": "user-1",
        "deviation_type": "calorie_excess",
        "severity": "moderate",
    })

    result = json.loads(result_str)
    assert result["deviation_type"] == "calorie_excess"
    assert result["severity"] == "moderate"
    assert result["calorie_adjustment"] == -200
    assert len(result["recommended_actions"]) > 0


@pytest.mark.asyncio
async def test_suggest_adjustment_training_skip(executor):
    """Test adjustment suggestion for training skip."""
    result_str = await executor.execute(TOOL_SUGGEST_ADJUSTMENT, {
        "user_id": "user-1",
        "deviation_type": "training_skip",
        "severity": "minor",
    })

    result = json.loads(result_str)
    assert result["calorie_adjustment"] == -50
    assert "快速训练" in result["recommended_actions"][0]


# ---------- Unknown tool ----------

@pytest.mark.asyncio
async def test_unknown_tool(executor):
    """Test handling of unknown tool name."""
    result_str = await executor.execute("nonexistent_tool", {})
    result = json.loads(result_str)
    assert "error" in result
    assert "Unknown tool" in result["error"]


# ---------- analyze_deviation ----------

@pytest.mark.asyncio
async def test_analyze_deviation_no_plan(executor):
    """Test analyze deviation when user has no active plan."""
    with patch.object(executor.storage, 'get_active_plan', new_callable=AsyncMock) as mock_plan, \
         patch.object(executor.storage, 'get_log_by_date', new_callable=AsyncMock) as mock_log:
        mock_plan.return_value = None
        mock_log.return_value = None
        result_str = await executor.execute(TOOL_ANALYZE_DEVIATION, {
            "user_id": "user-1",
            "date": "2024-01-15",
        })

    result = json.loads(result_str)
    assert result["error"] == "no_active_plan"


# ---------- get_user_history ----------

@pytest.mark.asyncio
async def test_get_user_history(executor):
    """Test user history retrieval with mocked storage."""
    with patch.object(executor.storage, 'get_user_logs', new_callable=AsyncMock) as mock_logs, \
         patch.object(executor.storage, 'get_user_weight_logs', new_callable=AsyncMock) as mock_weights, \
         patch.object(executor.storage, 'get_user_log_stats', new_callable=AsyncMock) as mock_stats:

        mock_logs.return_value = []
        mock_weights.return_value = []
        mock_stats.return_value = {"avg_calories": 2000}

        result_str = await executor.execute(TOOL_GET_USER_HISTORY, {
            "user_id": "user-1",
            "days": 7,
        })

    result = json.loads(result_str)
    assert result["user_id"] == "user-1"
    assert result["period_days"] == 7
    assert result["diet_logs"] == []
    assert result["weight_logs"] == []
