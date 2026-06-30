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
from app.agent.nodes.verifier import verify_node
from app.agent.router import should_adjust, should_continue_to_reflect, should_skip_after_planner
from app.agent.state import AgentState, UserContext, PlanContext, LogContext
from app.core.config import get_settings
from app.core.logging import get_logger
from app.harness.episode import build_harness_episode
from app.llm.client import resolve_llm_provider_settings

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
    graph.add_node("verifier", verify_node)
    
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
            "verify": "verifier",
        },
    )
    
    # Conditional edge after reflector
    graph.add_conditional_edges(
        "reflector",
        should_adjust,
        {
            "adjust": "adjuster",
            "verify": "verifier",
        },
    )
    
    # Adjuster leads through harness verification before ending.
    graph.add_edge("adjuster", "verifier")
    graph.add_edge("verifier", END)
    
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
    db_session: Optional[Any] = None,
    memory_context: Optional[dict[str, Any]] = None,
    evaluation_summary: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Run the agent with given context.
    
    Args:
        user_id: User identifier.
        trigger: What triggered this run.
        user_context: User data.
        plan_context: Current plan data.
        logs: Recent diet logs.
        db_session: Optional database session for tool execution.
        memory_context: Optional durable user memory retrieved before the run.
        evaluation_summary: Optional latest local evaluation metrics.
        
    Returns:
        Agent execution result with latency_ms.
    """
    import time
    start_time = time.time()
    
    run_id = str(uuid4())
    provider_settings = resolve_llm_provider_settings(get_settings())
    logger.info(f"Starting agent run {run_id} for user {user_id}")
    
    # Ensure context dictionaries match TypedDict schemas for type safety
    typed_user_context: UserContext = {
        "user_id": str(user_context.get("user_id", "")),
        "name": str(user_context.get("name", "User")),
        "gender": str(user_context.get("gender", "")),
        "age": int(user_context.get("age", 30)),
        "height_cm": float(user_context.get("height_cm", 175)),
        "goal": str(user_context.get("goal", "maintain")),
        "weight_kg": float(user_context.get("weight_kg", 70)),
        "target_weight_kg": float(user_context.get("target_weight_kg", user_context.get("weight_kg", 70))),
        "activity_level": str(user_context.get("activity_level", "moderate")),
        "training_days": int(user_context.get("training_days", 4)),
        "tdee": float(user_context.get("tdee", 2000)),
        "dietary_preferences": str(user_context.get("dietary_preferences", "无特殊限制")),
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
        "cycle_length": int(plan_context.get("cycle_length", 7)),
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
        "db_session": db_session,
        "trace": [],
        "tool_trace": [],
        "plan_diff": [],
        "safety_warnings": [],
        "missions": [],
        "action_cards": [],
        "memory_context": memory_context or {},
        "evaluation_summary": evaluation_summary or {},
        "model_status": {"available": True, "provider": provider_settings["provider"]},
        "verification_status": "",
        "verification_findings": [],
        "harness_score": 0,
        "harness_episode": {},
    }
    
    graph = get_agent_graph()
    
    try:
        result = await graph.ainvoke(initial_state)
        if not result.get("verification_status"):
            result = {
                **result,
                **await verify_node(result),
            }
        
        latency_ms = int((time.time() - start_time) * 1000)
        status = "error" if result.get("error") else "success"
        logger.info(f"Agent run {run_id} completed with status={status} in {latency_ms}ms")
        
        response = {
            "run_id": run_id,
            "status": status,
            "latency_ms": latency_ms,
            "planner_output": result.get("planner_output"),
            "actor_output": result.get("actor_output"),
            "reflection": result.get("reflection"),
            "adjustment": result.get("adjustment"),
            "reflection_summary": result.get("reflection_summary"),
            "trends": result.get("trends"),
            "motivation": result.get("motivation"),
            "trace": result.get("trace", []),
            "tool_trace": result.get("tool_trace", []),
            "plan_diff": result.get("plan_diff", []),
            "safety_warnings": result.get("safety_warnings", []),
            "missions": result.get("missions", []),
            "action_cards": result.get("action_cards", []),
            "memory_context": result.get("memory_context", memory_context or {}),
            "evaluation_summary": result.get("evaluation_summary", evaluation_summary or {}),
            "model_status": result.get("model_status", {"available": True, "provider": provider_settings["provider"]}),
            "verification_status": result.get("verification_status"),
            "verification_findings": result.get("verification_findings", []),
            "harness_score": result.get("harness_score", 0),
            "error": result.get("error"),
        }
        response["harness_episode"] = build_harness_episode(
            run_id=run_id,
            trigger=trigger,
            user_context=typed_user_context,
            plan_context=typed_plan_context,
            logs=typed_logs,
            memory_context=memory_context or {},
            evaluation_summary=evaluation_summary or {},
            result=response,
        )
        response["evaluation_summary"] = {
            **(response.get("evaluation_summary") or {}),
            "harness_episode": response["harness_episode"],
        }
        return response
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Agent run {run_id} failed in {latency_ms}ms: {e}")
        return {
            "run_id": run_id,
            "status": "error",
            "latency_ms": latency_ms,
            "error": str(e),
            "model_status": {"available": False, "provider": "unknown", "message": str(e)},
            "verification_status": "failed",
            "verification_findings": [{
                "level": "error",
                "code": "agent_runtime_error",
                "message": str(e),
                "evidence": {},
            }],
            "harness_score": 0,
        }
