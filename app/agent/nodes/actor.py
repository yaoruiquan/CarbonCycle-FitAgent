"""
Actor agent node.
执行者智能体节点

Parses and processes user execution data (diet logs).
Enhanced with function calling support for tool execution.
解析和处理用户执行数据（饮食记录），增强了工具函数调用支持
"""

import json
from typing import Any, Optional

from app.agent.state import AgentState, LogContext
from app.core.logging import get_logger, log_agent_decision
from app.llm.client import get_llm_client, ModelType
from app.llm.tools import get_tool_definitions

logger = get_logger(__name__)

# Max iterations for tool calling loop to prevent infinite loops
MAX_TOOL_ITERATIONS = 5


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


async def _run_tool_calling_loop(
    messages: list[dict[str, Any]],
    db_session: Any,
    tool_names: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Run a function calling loop with the LLM.
    执行 LLM 工具调用循环

    1. Send messages + tool definitions to LLM
    2. If LLM returns tool_calls, execute them via ToolExecutor
    3. Append tool results as 'tool' role messages
    4. Repeat until LLM returns a text response (no tool_calls)

    Args:
        messages: Conversation messages.
        db_session: Database session for tool execution.
        tool_names: Specific tools to make available.

    Returns:
        Final LLM response dict.
    """
    from app.llm.tool_executor import ToolExecutor

    llm = get_llm_client()
    tools = get_tool_definitions(tool_names)
    executor = ToolExecutor(db_session)

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = await llm.chat(
            messages=messages,
            model_type=ModelType.BRAIN,
            tools=tools,
            temperature=0.3,
        )

        tool_calls = response.get("tool_calls")
        if not tool_calls:
            # LLM returned a text response — done
            return response

        logger.info(
            f"Tool calling iteration {iteration + 1}: "
            f"{len(tool_calls)} tool(s) called"
        )

        # Append assistant message with tool_calls
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.get("content") or ""}
        assistant_msg["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": tc["function"],
            }
            for tc in tool_calls
        ]
        messages.append(assistant_msg)

        # Execute each tool and append result
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                func_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                func_args = {}

            logger.info(f"Executing tool: {func_name}({json.dumps(func_args, ensure_ascii=False)[:200]})")
            result = await executor.execute(func_name, func_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    # If we exhaust iterations, return the last response
    logger.warning(f"Tool calling loop exhausted after {MAX_TOOL_ITERATIONS} iterations")
    return response


async def act_node(state: AgentState) -> dict[str, Any]:
    """
    Actor node: processes user execution data.
    
    When a db_session is present in state, the actor can use
    function calling to invoke tools for richer analysis.
    
    Args:
        state: Current agent state.
        
    Returns:
        Updated state with actor_output.
    """
    logger.info(f"Actor node executing for run {state.get('run_id')}")
    
    logs = state.get("logs", [])
    parsed = _parse_log_data(logs)
    
    # If we have a db session, try function calling for enhanced analysis
    db_session = state.get("db_session")
    tool_analysis = None

    if db_session and state.get("user"):
        user = state["user"]
        plan = state.get("plan")

        system_msg = (
            "你是碳循环饮食健身规划 Agent 的执行分析模块。"
            "你可以使用工具来获取数据、分析偏差、查询食物营养信息。"
            "根据用户的执行数据进行分析，必要时调用工具获取更多信息。"
        )

        user_msg = (
            f"用户 {user.get('name', '')} 的最新执行数据：\n"
            f"{json.dumps(parsed, ensure_ascii=False, indent=2)}\n\n"
        )
        if plan:
            user_msg += (
                f"当前计划：{plan.get('day_type', '未知')} 日，"
                f"目标热量 {plan.get('target_calories', 0)} kcal\n"
            )
        user_msg += "\n请分析执行情况，如果需要可以调用工具获取更多信息。"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            response = await _run_tool_calling_loop(messages, db_session)
            tool_analysis = response.get("content")
            logger.info("Actor tool calling analysis completed")
        except Exception as e:
            logger.warning(f"Tool calling analysis failed, using basic parsing: {e}")

    log_agent_decision(
        logger,
        node="actor",
        decision="parse_execution",
        reasoning=f"解析了{len(logs)}条饮食记录" + (" + 工具增强分析" if tool_analysis else ""),
        context={"meal_count": parsed.get("meal_count", 0)},
    )
    
    result = {"actor_output": parsed}
    if tool_analysis:
        result["actor_output"]["tool_analysis"] = tool_analysis

    return result
