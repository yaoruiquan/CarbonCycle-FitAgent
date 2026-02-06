"""
Adjuster agent node.
调整者智能体节点

Generates plan adjustments based on reflection analysis.
根据反思分析生成计划调整建议

Enhanced with RAG knowledge retrieval and LLM-powered suggestions.
增强了 RAG 知识检索和 LLM 驱动的建议生成
"""

from typing import Any

from app.agent.state import AgentState, AdjustmentResult
from app.core.logging import get_logger, log_agent_decision
from app.llm.client import get_llm_client
from app.rag.retriever import retrieve_context

logger = get_logger(__name__)


async def _generate_smart_suggestions(
    reflection: dict,
    trends: dict,
    user: dict,
) -> list[dict[str, str]]:
    """
    Use LLM + RAG to generate intelligent adjustment suggestions.
    使用 LLM + RAG 生成智能调整建议
    
    Args:
        reflection: Current reflection result.
        trends: Trend analysis data.
        user: User context.
        
    Returns:
        List of smart suggestions.
    """
    # Retrieve relevant knowledge
    goal = user.get("goal", "fat_loss")
    deviation_type = reflection.get("deviation_type", "calorie_excess")
    
    try:
        knowledge = await retrieve_context(
            f"碳循环饮食 {deviation_type} 调整策略 {goal}",
            top_k=2
        )
    except Exception as e:
        logger.warning(f"RAG retrieval for adjuster failed: {e}")
        knowledge = ""
    
    # Build context for LLM
    context = f"""
用户情况:
- 目标: {goal}
- 当前体重: {user.get('weight_kg', 70)}kg
- 热量偏差: {reflection.get('calorie_deviation_pct', 0):.1f}%
- 蛋白质偏差: {reflection.get('protein_deviation_pct', 0):.1f}%
- 识别的问题: {', '.join(reflection.get('patterns', [])) or '无'}
- 趋势方向: {trends.get('trend_direction', '未知')}
- 训练完成率: {trends.get('training_completion_rate', 0):.1f}%

{f'专业知识参考:{chr(10)}{knowledge}' if knowledge else ''}

请针对以上情况，生成2-3条具体、可执行的调整建议。每条建议包含:
1. 具体动作
2. 实施细节
3. 预期效果

以JSON数组格式输出：
[{{"action": "...", "implementation": "...", "expected_effect": "..."}}]
"""
    
    llm = get_llm_client()
    
    messages = [
        {
            "role": "system",
            "content": "你是一个专业的健身营养顾问。请根据用户情况生成个性化的调整建议。"
        },
        {"role": "user", "content": context},
    ]
    
    try:
        response = await llm.chat(messages, temperature=0.5)
        content = response.get("content", "")
        
        # Try to parse JSON from response
        import json
        import re
        
        # Extract JSON array from response
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            suggestions = json.loads(json_match.group())
            return suggestions[:3]  # Max 3 suggestions
        
    except Exception as e:
        logger.warning(f"LLM smart suggestions failed: {e}")
    
    # Fallback to rule-based suggestions
    return []


async def adjust_node(state: AgentState) -> dict[str, Any]:
    """
    Adjuster node: generates plan adjustments.
    
    Enhanced with:
    - RAG knowledge integration
    - LLM-powered smart suggestions
    - Behavioral insights
    - Motivational messages
    
    Args:
        state: Current agent state.
        
    Returns:
        Updated state with adjustment result.
    """
    logger.info(f"Adjuster node executing for run {state.get('run_id')}")
    
    reflection = state.get("reflection")
    trends = state.get("trends", {})
    user = state.get("user", {})
    
    if not reflection or not reflection.get("needs_adjustment"):
        return {
            "adjustment": AdjustmentResult(
                adjustment_type="none",
                calorie_adjustment=0,
                immediate_actions=[],
                behavioral_suggestions=[],
            ),
            "motivation": "继续保持！你做得很好。💪",
        }
    
    severity = reflection.get("severity", "minor")
    cal_dev = reflection.get("calorie_deviation_pct", 0)
    patterns = reflection.get("patterns", [])
    
    # Calculate adjustment
    if severity == "significant":
        adj_type = "significant"
        cal_adj = -cal_dev * 0.5  # Correct 50% of deviation
    elif severity == "moderate":
        adj_type = "moderate"
        cal_adj = -cal_dev * 0.3
    else:
        adj_type = "minor"
        cal_adj = -cal_dev * 0.2
    
    cal_adj = max(-200, min(200, cal_adj * 20))  # Scale and cap
    
    # Generate rule-based immediate actions
    actions = []
    if cal_dev > 15:
        actions.append({
            "action": "明天降低碳水摄入10%",
            "reasoning": "平衡周平均热量",
        })
    if cal_dev < -15:
        actions.append({
            "action": "增加健康碳水来源",
            "reasoning": "避免代谢下降",
        })
    if "蛋白质摄入不足" in patterns:
        actions.append({
            "action": "每餐增加蛋白质来源(鸡蛋/鸡胸/豆腐)",
            "reasoning": "确保肌肉恢复和饱腹感",
        })
    if "训练计划执行率低" in patterns:
        actions.append({
            "action": "安排10分钟快速训练",
            "reasoning": "保持运动习惯",
        })
    if "热量摄入不足" in patterns:
        actions.append({
            "action": "添加健康加餐",
            "reasoning": "防止代谢适应",
        })
    
    # Generate LLM-powered smart suggestions
    smart_suggestions = await _generate_smart_suggestions(reflection, trends, user)
    
    # Merge rule-based and LLM suggestions
    behavioral_suggestions = []
    
    # Add rule-based patterns
    if "持续热量超标" in patterns:
        behavioral_suggestions.append({
            "suggestion": "使用较小餐具",
            "implementation": "心理学显示小盘子可减少20%摄入",
        })
    if trends.get("trend_direction") == "worsening":
        behavioral_suggestions.append({
            "suggestion": "记录饮食日记",
            "implementation": "提高意识是改变的第一步",
        })
    
    # Add smart suggestions
    for sugg in smart_suggestions:
        behavioral_suggestions.append({
            "suggestion": sugg.get("action", ""),
            "implementation": sugg.get("implementation", ""),
        })
    
    adjustment = AdjustmentResult(
        adjustment_type=adj_type,
        calorie_adjustment=round(cal_adj, 0),
        immediate_actions=actions,
        behavioral_suggestions=behavioral_suggestions[:5],  # Limit to 5
    )
    
    # Generate motivational message
    motivations = {
        "minor": "小的偏差是正常的，继续保持大方向！👍",
        "moderate": "今天有些挑战，但明天是新的开始！💪",
        "significant": "这是一个调整的机会。进步不是直线，而是螺旋上升的！🌟",
    }
    motivation = motivations.get(severity, "加油！")
    
    log_agent_decision(
        logger,
        node="adjuster",
        decision=f"adjust_{adj_type}",
        reasoning=f"建议调整热量{cal_adj:.0f}千卡，生成{len(behavioral_suggestions)}条建议",
        context={
            "actions_count": len(actions),
            "smart_suggestions_count": len(smart_suggestions),
        },
    )
    
    return {
        "adjustment": adjustment,
        "motivation": motivation,
    }
