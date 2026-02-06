"""
Actor agent node.
执行者智能体节点

Parses and processes user execution data (diet logs).
解析和处理用户执行数据（饮食记录）
"""

from typing import Any

from app.agent.state import AgentState, LogContext
from app.core.logging import get_logger, log_agent_decision

logger = get_logger(__name__)


def _parse_log_data(logs: list[LogContext]) -> dict[str, Any]:
    """Parse log data for analysis."""
    if not logs:
        return {"status": "no_data", "summary": "没有饮食记录"}
    
    latest = logs[-1]
    return {
        "status": "success",
        "date": latest.get("date"),
        "actual_intake": {
            "calories": latest.get("actual_calories", 0),
            "protein": latest.get("actual_protein", 0),
            "carbs": latest.get("actual_carbs", 0),
            "fat": latest.get("actual_fat", 0),
        },
        "training_completed": latest.get("training_completed", False),
        "meal_count": latest.get("meal_count", 0),
    }


async def act_node(state: AgentState) -> dict[str, Any]:
    """
    Actor node: processes user execution data.
    
    Args:
        state: Current agent state.
        
    Returns:
        Updated state with actor_output.
    """
    logger.info(f"Actor node executing for run {state.get('run_id')}")
    
    logs = state.get("logs", [])
    parsed = _parse_log_data(logs)
    
    log_agent_decision(
        logger,
        node="actor",
        decision="parse_execution",
        reasoning=f"解析了{len(logs)}条饮食记录",
        context={"meal_count": parsed.get("meal_count", 0)},
    )
    
    return {
        "actor_output": parsed,
    }
