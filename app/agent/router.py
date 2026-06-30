"""
Conditional routing logic for agent graph.
智能体状态图的条件路由逻辑

Determines transitions between agent nodes based on state.
根据状态决定智能体节点之间的转换
"""

from typing import Literal

from app.agent.state import AgentState
from app.core.logging import get_logger

logger = get_logger(__name__)


def should_continue_to_reflect(state: AgentState) -> Literal["reflect", "verify"]:
    """
    Determine if we should proceed to reflection.
    
    Args:
        state: Current agent state.
        
    Returns:
        "reflect" to continue, "verify" if error or no data.
    """
    if state.get("error"):
        logger.info("Routing to verifier due to error")
        return "verify"
    
    actor_output = state.get("actor_output") or {}
    if actor_output.get("status") == "no_data":
        logger.info("Routing to verifier due to no data")
        return "verify"
    
    return "reflect"


def should_adjust(state: AgentState) -> Literal["adjust", "verify"]:
    """
    Determine if adjustment is needed.
    
    Args:
        state: Current agent state.
        
    Returns:
        "adjust" if adjustment needed, "verify" otherwise.
    """
    if state.get("error"):
        return "verify"
    
    if state.get("should_adjust", False):
        logger.info("Routing to adjust based on reflection")
        return "adjust"
    
    logger.info("No adjustment needed, routing to verifier")
    return "verify"


def check_iteration_limit(state: AgentState) -> Literal["continue", "end"]:
    """
    Check if iteration limit reached.
    
    Args:
        state: Current agent state.
        
    Returns:
        "continue" if under limit, "end" if reached.
    """
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 10)
    
    if iteration >= max_iter:
        logger.warning(f"Max iterations ({max_iter}) reached")
        return "end"
    
    return "continue"


def should_skip_after_planner(state: AgentState) -> Literal["skip", "continue"]:
    """
    Determine if we should skip Actor/Reflector/Adjuster after Planner.
    
    For create_plan and plan_only triggers, we only need Planner output.
    创建计划时只需要 Planner 节点的输出，跳过后续节点。
    
    Args:
        state: Current agent state.
        
    Returns:
        "skip" to end after planner, "continue" to proceed to actor.
    """
    trigger = state.get("trigger", "")

    if state.get("error"):
        logger.info("Skipping downstream nodes because planner returned an error")
        return "skip"
    
    # Triggers that only need planner output
    planner_only_triggers = {"create_plan", "plan_only", "generate_plan"}
    
    if trigger in planner_only_triggers:
        logger.info(f"Skipping to end for trigger: {trigger}")
        return "skip"
    
    return "continue"
