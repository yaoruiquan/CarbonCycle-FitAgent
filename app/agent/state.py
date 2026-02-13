"""
Agent state schema definition.
智能体状态模式定义

Defines the state structure passed between agent nodes.
定义在智能体节点之间传递的状态结构
"""

from datetime import date
from typing import Any, Optional, TypedDict
from uuid import UUID


class UserContext(TypedDict):
    """User context within agent state."""
    user_id: str
    name: str
    goal: str
    weight_kg: float
    tdee: float


class PlanContext(TypedDict):
    """Plan context within agent state."""
    plan_id: str
    start_date: str
    current_day: int
    day_type: str
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float


class LogContext(TypedDict):
    """Log context within agent state."""
    date: str
    actual_calories: float
    actual_protein: float
    actual_carbs: float
    actual_fat: float
    training_completed: bool
    meal_count: int


class ReflectionResult(TypedDict):
    """Result from reflection node."""
    severity: str
    deviation_type: str
    calorie_deviation_pct: float
    protein_deviation_pct: float
    needs_adjustment: bool
    patterns: list[str]


class AdjustmentResult(TypedDict):
    """Result from adjustment node."""
    adjustment_type: str
    calorie_adjustment: float
    immediate_actions: list[dict]
    behavioral_suggestions: list[dict]


class AgentState(TypedDict, total=False):
    """
    Complete agent state passed between nodes.
    
    Attributes:
        run_id: Unique identifier for this agent run.
        trigger: What triggered this agent run.
        user: User context information.
        plan: Current plan context.
        logs: Recent diet logs.
        current_date: Date being processed.
        planner_output: Output from planner node.
        actor_output: Output from actor node.
        reflection: Reflection analysis result.
        adjustment: Adjustment recommendations.
        final_output: Final agent output.
        error: Error message if failed.
        should_adjust: Whether adjustment is needed.
        iteration: Current iteration count.
        max_iterations: Maximum allowed iterations.
    """
    
    # Run metadata
    run_id: str
    trigger: str
    
    # Context
    user: UserContext
    plan: PlanContext
    logs: list[LogContext]
    current_date: str
    
    # Node outputs
    planner_output: Optional[dict[str, Any]]
    actor_output: Optional[dict[str, Any]]
    reflection: Optional[ReflectionResult]
    adjustment: Optional[AdjustmentResult]
    
    # Control flow
    final_output: Optional[dict[str, Any]]
    error: Optional[str]
    should_adjust: bool
    iteration: int
    max_iterations: int
    
    # Messages for LLM context
    messages: list[dict[str, str]]
    
    # Database session for tool execution
    db_session: Optional[Any]
