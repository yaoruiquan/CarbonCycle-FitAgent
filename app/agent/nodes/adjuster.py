"""
Adjuster agent node.
调整者智能体节点

Generates plan adjustments based on reflection analysis.
根据反思分析生成计划调整建议

Enhanced with RAG knowledge retrieval and LLM-powered suggestions.
增强了 RAG 知识检索和 LLM 驱动的建议生成
"""

from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from app.agent.state import AgentState, AdjustmentResult
from app.agent.trace import append_trace, duration_ms, make_step_trace, start_timer
from app.core.logging import get_logger, log_agent_decision
from app.harness.safety_policy import NutritionSafetyPolicy
from app.llm.client import get_llm_client
from app.rag.retriever import retrieve_context

logger = get_logger(__name__)


def _target_calories(plan: dict[str, Any]) -> float:
    """Return the current plan calorie target from explicit or macro fields."""
    if plan.get("target_calories"):
        return float(plan["target_calories"])
    protein = float(plan.get("target_protein", 0) or 0)
    carbs = float(plan.get("target_carbs", 0) or 0)
    fat = float(plan.get("target_fat", 0) or 0)
    return protein * 4 + carbs * 4 + fat * 9


def _build_plan_diff(
    plan: dict[str, Any],
    calorie_adjustment: float,
    patterns: list[str],
) -> list[dict[str, Any]]:
    """Build structured, approval-ready plan changes."""
    current_calories = _target_calories(plan)
    if not current_calories or abs(calorie_adjustment) < 1:
        return []

    next_calories = round(max(1200, current_calories + calorie_adjustment), 0)
    diff: list[dict[str, Any]] = [
        {
            "field": "target_calories",
            "label": "明日目标热量",
            "before": round(current_calories, 0),
            "after": next_calories,
            "delta": round(next_calories - current_calories, 0),
            "reason": "根据今日执行偏差做小幅补偿，避免一次性大改计划。",
            "requires_confirmation": True,
        }
    ]

    if "蛋白质摄入不足" in patterns and plan.get("target_protein"):
        before = float(plan["target_protein"])
        diff.append(
            {
                "field": "target_protein",
                "label": "明日蛋白质目标",
                "before": round(before, 0),
                "after": round(before + 15, 0),
                "delta": 15,
                "reason": "蛋白质偏低时优先补足恢复和饱腹感。",
                "requires_confirmation": True,
            }
        )

    if calorie_adjustment < 0 and plan.get("target_carbs"):
        before = float(plan["target_carbs"])
        diff.append(
            {
                "field": "target_carbs",
                "label": "明日碳水目标",
                "before": round(before, 0),
                "after": round(max(60, before + calorie_adjustment / 4), 0),
                "delta": round(calorie_adjustment / 4, 0),
                "reason": "热量超标时优先从碳水做温和回调。",
                "requires_confirmation": True,
            }
        )

    return diff


def _build_safety_warnings(
    user: dict[str, Any],
    plan: dict[str, Any],
    plan_diff: list[dict[str, Any]],
    reflection: dict[str, Any],
) -> list[dict[str, str]]:
    """Apply nutrition guardrails to proposed changes."""
    return NutritionSafetyPolicy().warnings(
        user=user,
        plan=plan,
        plan_diff=plan_diff,
        reflection=reflection,
    )


def _build_missions(
    patterns: list[str],
    trends: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create short goal-oriented tasks for follow-up."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    missions: list[dict[str, Any]] = []

    if "蛋白质摄入不足" in patterns:
        missions.append({
            "id": str(uuid4()),
            "title": "连续 3 餐补足优质蛋白",
            "description": "每餐至少加入一份鸡蛋、鱼、鸡胸、豆腐或酸奶。",
            "status": "pending",
            "due_date": tomorrow,
            "next_action": "在下一餐记录里确认蛋白质来源。",
            "evidence": ["餐食记录", "蛋白质克数"],
        })
    if "训练计划执行率低" in patterns or trends.get("training_completion_rate", 100) < 70:
        missions.append({
            "id": str(uuid4()),
            "title": "完成一次 10 分钟保底训练",
            "description": "用低门槛训练维持习惯连续性。",
            "status": "pending",
            "due_date": tomorrow,
            "next_action": "点击训练打卡并填写完成备注。",
            "evidence": ["训练完成状态", "训练备注"],
        })
    if not missions:
        missions.append({
            "id": str(uuid4()),
            "title": "明日按计划完成三餐记录",
            "description": "用完整记录帮助 Agent 判断是否需要继续调整。",
            "status": "pending",
            "due_date": tomorrow,
            "next_action": "晚餐后补齐当天饮食。",
            "evidence": ["餐次数量", "总热量", "宏量营养素"],
        })
    return missions[:3]


def _build_action_cards(
    plan_diff: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    warnings: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Build executable UI actions from agent decisions."""
    cards: list[dict[str, Any]] = []
    if plan_diff:
        cards.append({
            "type": "apply_plan_diff",
            "title": "审批并应用计划调整",
            "description": f"包含 {len(plan_diff)} 项明日计划变更，应用前需要确认。",
            "data": {"plan_diff": plan_diff, "safety_warnings": warnings},
            "confirmation_required": True,
        })
    if missions:
        cards.append({
            "type": "create_missions",
            "title": "创建本周 Agent 任务",
            "description": f"创建 {len(missions)} 个跟踪任务，Agent 后续会按任务复盘。",
            "data": {"missions": missions},
            "confirmation_required": True,
        })
    cards.append({
        "type": "open_agent_trace",
        "title": "查看 Agent 决策轨迹",
        "description": "展开 Planner、Actor、Reflector、Adjuster 的运行证据。",
        "data": {"panel": "trace"},
        "confirmation_required": False,
    })
    return cards


def _has_calorie_adjustment_pattern(patterns: list[str]) -> bool:
    """Return whether a reflection pattern justifies changing plan macros."""
    return any(
        pattern in {"持续热量超标", "热量摄入不足", "趋势恶化"}
        for pattern in patterns
    )


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
    started_at, started = start_timer()
    
    reflection = state.get("reflection")
    trends = state.get("trends", {})
    user = state.get("user", {})
    plan = state.get("plan", {})
    
    if not reflection or not reflection.get("needs_adjustment"):
        adjustment = AdjustmentResult(
            adjustment_type="none",
            calorie_adjustment=0,
            immediate_actions=[],
            behavioral_suggestions=[],
        )
        missions = _build_missions([], trends or {})
        return {
            "adjustment": adjustment,
            "motivation": "继续保持！你做得很好。💪",
            "missions": missions,
            "action_cards": _build_action_cards([], missions, []),
            "trace": append_trace(
                state,
                make_step_trace(
                    node="adjuster",
                    title="计划调整",
                    status="skipped",
                    decision="keep_current_plan",
                    reasoning="反思结果未达到调整阈值，保留当前计划并创建轻量跟踪任务。",
                    input_summary={"needs_adjustment": False},
                    output_summary={"missions": len(missions), "plan_diff": 0},
                    confidence=0.82,
                    started_at=started_at,
                    elapsed_ms=duration_ms(started),
                ),
            ),
        }
    
    severity = reflection.get("severity", "minor")
    cal_dev = reflection.get("calorie_deviation_pct", 0)
    patterns = reflection.get("patterns", [])
    has_calorie_adjustment = _has_calorie_adjustment_pattern(patterns)
    
    # Calculate adjustment
    if not has_calorie_adjustment:
        adj_type = "mission"
        cal_adj = 0
    elif severity == "significant":
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
    plan_diff = _build_plan_diff(plan, round(cal_adj, 0), patterns)
    safety_warnings = _build_safety_warnings(user, plan, plan_diff, reflection)
    missions = _build_missions(patterns, trends)
    action_cards = _build_action_cards(plan_diff, missions, safety_warnings)
    
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
        "plan_diff": plan_diff,
        "safety_warnings": safety_warnings,
        "missions": missions,
        "action_cards": action_cards,
        "trace": append_trace(
            state,
            make_step_trace(
                node="adjuster",
                title="计划调整",
                status="success",
                decision=f"adjust_{adj_type}",
                reasoning=f"建议调整热量{cal_adj:.0f}千卡，生成结构化计划 diff、任务和执行卡片。",
                input_summary={
                    "severity": severity,
                    "calorie_deviation_pct": cal_dev,
                    "patterns": patterns,
                },
                output_summary={
                    "plan_diff": len(plan_diff),
                    "safety_warnings": len(safety_warnings),
                    "missions": len(missions),
                    "action_cards": len(action_cards),
                },
                confidence=0.86 if smart_suggestions else 0.76,
                started_at=started_at,
                elapsed_ms=duration_ms(started),
            ),
        ),
    }
