"""
Agent flow integration tests.
"""

import pytest
from uuid import uuid4

from app.agent.state import AgentState
from app.agent.nodes.planner import plan_node
from app.agent.nodes.actor import act_node
from app.agent.nodes.reflector import reflect_node
from app.agent.nodes.adjuster import adjust_node
from app.agent.router import should_adjust, should_continue_to_reflect


class TestAgentNodes:
    """Test individual agent nodes."""

    @pytest.fixture
    def base_state(self) -> AgentState:
        """Create base agent state for testing."""
        return AgentState(
            run_id=str(uuid4()),
            trigger="test",
            user={
                "user_id": str(uuid4()),
                "name": "测试用户",
                "goal": "fat_loss",
                "weight_kg": 75,
                "tdee": 2200,
            },
            plan={
                "plan_id": str(uuid4()),
                "start_date": "2024-01-01",
                "current_day": 1,
                "day_type": "high_carb",
                "target_calories": 2400,
                "target_protein": 150,
                "target_carbs": 300,
                "target_fat": 67,
            },
            logs=[
                {
                    "date": "2024-01-01",
                    "actual_calories": 2600,
                    "actual_protein": 140,
                    "actual_carbs": 350,
                    "actual_fat": 70,
                    "training_completed": True,
                    "meal_count": 5,
                }
            ],
            current_date="2024-01-01",
            iteration=0,
            max_iterations=10,
            messages=[],
        )

    @pytest.mark.asyncio
    async def test_actor_node_parses_logs(self, base_state):
        """Test actor node correctly parses log data."""
        result = await act_node(base_state)
        
        assert "actor_output" in result
        assert result["actor_output"]["status"] == "success"
        assert result["actor_output"]["actual_intake"]["calories"] == 2600

    @pytest.mark.asyncio
    async def test_actor_node_handles_no_data(self, base_state):
        """Test actor node handles empty logs."""
        base_state["logs"] = []
        result = await act_node(base_state)
        
        assert result["actor_output"]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_reflector_calculates_deviation(self, base_state):
        """Test reflector calculates correct deviation."""
        base_state["actor_output"] = {
            "status": "success",
            "actual_intake": {
                "calories": 2600,
                "protein": 140,
                "carbs": 350,
                "fat": 70,
            },
            "training_completed": True,
        }
        
        result = await reflect_node(base_state)
        
        assert "reflection" in result
        assert result["reflection"]["calorie_deviation_pct"] > 0  # Exceeded

    @pytest.mark.asyncio
    async def test_adjuster_generates_actions(self, base_state):
        """Test adjuster generates adjustment actions."""
        base_state["reflection"] = {
            "severity": "moderate",
            "deviation_type": "calorie_excess",
            "calorie_deviation_pct": 15.0,
            "protein_deviation_pct": -5.0,
            "needs_adjustment": True,
            "patterns": ["持续热量超标"],
        }
        
        result = await adjust_node(base_state)
        
        assert "adjustment" in result
        assert result["adjustment"]["adjustment_type"] != "none"


class TestAgentRouter:
    """Test routing logic."""

    def test_should_continue_on_success(self):
        """Test routing continues after successful actor."""
        state = AgentState(
            actor_output={"status": "success"},
        )
        assert should_continue_to_reflect(state) == "reflect"

    def test_should_end_on_error(self):
        """Test routing ends on error."""
        state = AgentState(
            error="Test error",
        )
        assert should_continue_to_reflect(state) == "end"

    def test_should_adjust_when_needed(self):
        """Test routing to adjuster when adjustment needed."""
        state = AgentState(
            should_adjust=True,
        )
        assert should_adjust(state) == "adjust"

    def test_should_end_when_no_adjustment(self):
        """Test routing ends when no adjustment needed."""
        state = AgentState(
            should_adjust=False,
        )
        assert should_adjust(state) == "end"
