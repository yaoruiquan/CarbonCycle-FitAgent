"""
Planner agent node.
计划者智能体节点

Generates carbon cycle diet plans based on user profile and goals.
根据用户画像和目标生成碳循环饮食计划

Enhanced with RAG knowledge retrieval for professional nutrition guidance.
增强了 RAG 知识检索，提供专业营养指导
"""

from pathlib import Path
from typing import Any

from app.agent.state import AgentState
from app.core.logging import get_logger, log_agent_decision
from app.llm.client import get_llm_client
from app.rag.retriever import retrieve_context

logger = get_logger(__name__)

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "planner.txt"


def _load_prompt_template() -> str:
    """Load planner prompt template."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return "Generate a carbon cycle plan for the user."


def _build_prompt(state: AgentState, knowledge_context: str = "") -> str:
    """
    Build prompt from template and state.
    
    Args:
        state: Agent state with user info.
        knowledge_context: RAG-retrieved knowledge to inject.
        
    Returns:
        Complete prompt string.
    """
    template = _load_prompt_template()
    user = state.get("user", {})
    plan = state.get("plan", {})
    
    base_prompt = template.format(
        user_name=user.get("name", "用户"),
        gender="男" if user.get("gender") == "male" else "女",
        age=user.get("age", 30),
        height_cm=user.get("height_cm", 175),
        weight_kg=user.get("weight_kg", 70),
        target_weight_kg=user.get("target_weight_kg", user.get("weight_kg", 70) - 5),
        goal=user.get("goal", "fat_loss"),
        activity_level=user.get("activity_level", "moderate"),
        training_days=user.get("training_days", 4),
        tdee=user.get("tdee", 2000),
        dietary_preferences=user.get("dietary_preferences", "无特殊限制"),
        cycle_length=plan.get("cycle_length", 7),
    )
    
    # Inject RAG knowledge if available
    if knowledge_context:
        knowledge_section = f"""
## 专业知识参考
以下是碳循环饮食的专业知识，请在制定计划时参考：

{knowledge_context}

---
"""
        # Insert knowledge before the task section
        base_prompt = base_prompt.replace("## 任务", knowledge_section + "## 任务")
    
    return base_prompt


async def plan_node(state: AgentState) -> dict[str, Any]:
    """
    Planner node: generates or updates carbon cycle plan.
    
    Uses RAG to retrieve professional nutrition knowledge.
    使用 RAG 检索专业营养知识
    
    Args:
        state: Current agent state.
        
    Returns:
        Updated state with planner_output.
    """
    logger.info(f"Planner node executing for run {state.get('run_id')}")
    
    user = state.get("user", {})
    goal = user.get("goal", "fat_loss")
    
    # RAG: Retrieve relevant knowledge based on user goal
    logger.info(f"Retrieving RAG knowledge for goal: {goal}")
    try:
        knowledge_context = await retrieve_context(
            f"碳循环饮食 {goal} 宏量营养素计算",
            top_k=3
        )
        logger.info(f"Retrieved {len(knowledge_context)} chars of knowledge")
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}, proceeding without knowledge")
        knowledge_context = ""
    
    llm = get_llm_client()
    prompt = _build_prompt(state, knowledge_context=knowledge_context)
    
    messages = [
        {"role": "system", "content": "你是一个专业的碳循环饮食规划师，具备丰富的营养学知识。"},
        {"role": "user", "content": prompt},
    ]
    
    try:
        response = await llm.plan(messages)
        content = response.get("content", "")
        
        log_agent_decision(
            logger,
            node="planner",
            decision="generate_plan",
            reasoning=f"基于用户档案和 RAG 知识生成碳循环计划 (知识: {len(knowledge_context)} chars)",
            context={"user_id": user.get("user_id"), "goal": goal},
        )
        
        return {
            "planner_output": {
                "raw_response": content,
                "status": "success",
                "knowledge_used": bool(knowledge_context),
            },
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": content}
            ],
        }
        
    except Exception as e:
        logger.error(f"Planner node error: {e}")
        return {
            "planner_output": {"status": "error", "error": str(e)},
            "error": str(e),
        }
