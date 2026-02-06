"""
LangGraph agent graph definition.
LangGraph 智能体状态图定义

Implements Planner → Actor → Reflector → Adjuster workflow.
实现 计划者 → 执行者 → 反思者 → 调整者 工作流
"""

from typing import Any, Optional
from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes import act_node, adjust_node, plan_node, reflect_node
from app.agent.router import should_adjust, should_continue_to_reflect, should_skip_after_planner
from app.agent.state import AgentState, UserContext, PlanContext, LogContext
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_agent_graph() -> CompiledStateGraph:
    """
    Create the agent state graph.
    
    Returns:
        Compiled StateGraph ready for execution.
    """
    # Create graph with state schema
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("planner", plan_node)
    graph.add_node("actor", act_node)
    graph.add_node("reflector", reflect_node)
    graph.add_node("adjuster", adjust_node)
    
    # Set entry point
    graph.set_entry_point("planner")
    
    # Conditional edge after planner: skip to END for create_plan trigger
    graph.add_conditional_edges(
        "planner",
        should_skip_after_planner,
        {
            "skip": END,
            "continue": "actor",
        },
    )
    
    # Conditional edge after actor
    graph.add_conditional_edges(
        "actor",
        should_continue_to_reflect,
        {
            "reflect": "reflector",
            "end": END,
        },
    )
    
    # Conditional edge after reflector
    graph.add_conditional_edges(
        "reflector",
        should_adjust,
        {
            "adjust": "adjuster",
            "end": END,
        },
    )
    
    # Adjuster leads to end
    graph.add_edge("adjuster", END)
    
    return graph.compile()


# Singleton graph instance
_agent_graph: Optional[CompiledStateGraph] = None


def get_agent_graph() -> CompiledStateGraph:
    """Get or create the singleton agent graph."""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = create_agent_graph()
    return _agent_graph


async def run_agent(
    user_id: str,
    trigger: str,
    user_context: dict[str, Any],
    plan_context: dict[str, Any],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run the agent with given context.
    
    Args:
        user_id: User identifier.
        trigger: What triggered this run.
        user_context: User data.
        plan_context: Current plan data.
        logs: Recent diet logs.
        
    Returns:
        Agent execution result with latency_ms.
    """
    import time
    start_time = time.time()
    
    run_id = str(uuid4())
    logger.info(f"Starting agent run {run_id} for user {user_id}")
    
    # Ensure context dictionaries match TypedDict schemas for type safety
    typed_user_context: UserContext = {
        "user_id": str(user_context.get("user_id", "")),
        "name": str(user_context.get("name", "User")),
        "goal": str(user_context.get("goal", "maintain")),
        "weight_kg": float(user_context.get("weight_kg", 70)),
        "tdee": float(user_context.get("tdee", 2000)),
    }
    
    typed_plan_context: PlanContext = {
        "plan_id": str(plan_context.get("plan_id", "")),
        "start_date": str(plan_context.get("start_date", "")),
        "current_day": int(plan_context.get("current_day", 1)),
        "day_type": str(plan_context.get("day_type", "medium_carb")),
        "target_calories": float(plan_context.get("target_calories", 2000)),
        "target_protein": float(plan_context.get("target_protein", 150)),
        "target_carbs": float(plan_context.get("target_carbs", 200)),
        "target_fat": float(plan_context.get("target_fat", 60)),
    }
    
    typed_logs: list[LogContext] = [
        {
            "date": str(l.get("date", "")),
            "actual_calories": float(l.get("actual_calories", 0)),
            "actual_protein": float(l.get("actual_protein", 0)),
            "actual_carbs": float(l.get("actual_carbs", 0)),
            "actual_fat": float(l.get("actual_fat", 0)),
            "training_completed": bool(l.get("training_completed", False)),
            "meal_count": int(l.get("meal_count", 0)),
        }
        for l in logs
    ]
    
    initial_state: AgentState = {
        "run_id": run_id,
        "trigger": trigger,
        "user": typed_user_context,
        "plan": typed_plan_context,
        "logs": typed_logs,
        "current_date": "",
        "planner_output": None,
        "actor_output": None,
        "reflection": None,
        "adjustment": None,
        "final_output": None,
        "error": None,
        "should_adjust": False,
        "iteration": 0,
        "max_iterations": 10,
        "messages": [],
    }
    
    graph = get_agent_graph()
    
    try:
        result = await graph.ainvoke(initial_state)
        
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Agent run {run_id} completed successfully in {latency_ms}ms")
        
        return {
            "run_id": run_id,
            "status": "success",
            "latency_ms": latency_ms,
            "planner_output": result.get("planner_output"),
            "reflection": result.get("reflection"),
            "adjustment": result.get("adjustment"),
            "reflection_summary": result.get("reflection_summary"),
            "trends": result.get("trends"),
        }
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Agent run {run_id} failed in {latency_ms}ms: {e}")
        return {
            "run_id": run_id,
            "status": "error",
            "latency_ms": latency_ms,
            "error": str(e),
        }
