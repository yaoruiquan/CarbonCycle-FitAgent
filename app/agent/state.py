"""
Agent state schema definition.
智能体状态模式定义

Defines the state structure passed between agent nodes.
定义在智能体节点之间传递的状态结构
"""

from datetime import date
from typing import Any, Optional, TypedDict
from uuid import UUID


class UserContext(TypedDict, total=False):
    """User context within agent state."""
    user_id: str
    name: str
    gender: str
    age: int
    height_cm: float
    goal: str
    weight_kg: float
    target_weight_kg: float
    activity_level: str
    training_days: int
    tdee: float
    dietary_preferences: str


class PlanContext(TypedDict, total=False):
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


class AgentStepTrace(TypedDict, total=False):
    """Observable trace entry for one agent node."""
    node: str
    title: str
    status: str
    decision: str
    reasoning: str
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    confidence: float
    started_at: str
    completed_at: str
    duration_ms: int


class ToolTrace(TypedDict, total=False):
    """Trace entry for one tool call."""
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    status: str
    duration_ms: int
    error: Optional[str]


class PlanDiffItem(TypedDict, total=False):
    """Structured plan change proposed by the agent."""
    field: str
    label: str
    before: Any
    after: Any
    delta: Any
    reason: str
    requires_confirmation: bool


class SafetyWarning(TypedDict):
    """Safety guardrail warning."""
    level: str
    message: str
    rule: str


class AgentMission(TypedDict, total=False):
    """Goal-oriented task proposed by the agent."""
    id: str
    title: str
    description: str
    status: str
    due_date: str
    next_action: str
    evidence: list[str]


class AgentActionCard(TypedDict, total=False):
    """Executable action shown to the user."""
    type: str
    title: str
    description: str
    data: dict[str, Any]
    confirmation_required: bool


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

    # Observable agent capabilities
    trace: list[AgentStepTrace]
    tool_trace: list[ToolTrace]
    plan_diff: list[PlanDiffItem]
    safety_warnings: list[SafetyWarning]
    missions: list[AgentMission]
    action_cards: list[AgentActionCard]
    memory_context: dict[str, Any]
    evaluation_summary: dict[str, Any]
