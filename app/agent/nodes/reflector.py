"""
Reflector agent node.
反思者智能体节点

Analyzes execution deviations and identifies patterns.
分析执行偏差并识别模式

Enhanced with multi-day trend analysis and LLM insights.
增强了多日趋势分析和 LLM 洞察
"""

from typing import Any, Optional

from app.agent.state import AgentState, ReflectionResult
from app.core.logging import get_logger, log_agent_decision
from app.llm.client import get_llm_client

logger = get_logger(__name__)


def _calculate_deviation(target: float, actual: float) -> float:
    """Calculate percentage deviation."""
    if target == 0:
        return 0
    return ((actual - target) / target) * 100


def _determine_severity(deviation_pct: float) -> str:
    """Determine deviation severity."""
    abs_dev = abs(deviation_pct)
    if abs_dev <= 10:
        return "minor"
    elif abs_dev <= 20:
        return "moderate"
    return "significant"


def _analyze_trends(logs: list[Any]) -> dict[str, Any]:
    """
    Analyze multi-day trends from logs.
    分析多日日志的趋势
    
    Args:
        logs: List of diet log entries.
        
    Returns:
        Trend analysis dict.
    """
    if not logs or len(logs) < 2:
        return {
            "has_trend": False,
            "days_analyzed": len(logs) if logs else 0,
            "trend_direction": "insufficient_data",
        }
    
    # Calculate average deviations over time
    cal_deviations = []
    protein_deviations = []
    training_rate = 0
    training_count = 0
    
    for log in logs[-7:]:  # Analyze last 7 days max
        actual_cal = log.get("actual_calories", 0)
        target_cal = log.get("target_calories", 2000)  # Fallback
        cal_dev = _calculate_deviation(target_cal, actual_cal)
        cal_deviations.append(cal_dev)
        
        actual_protein = log.get("actual_protein", 0)
        target_protein = log.get("target_protein", 150)
        protein_dev = _calculate_deviation(target_protein, actual_protein)
        protein_deviations.append(protein_dev)
        
        if log.get("training_completed"):
            training_count += 1
    
    training_rate = training_count / len(logs[-7:]) * 100 if logs else 0
    
    # Determine trend direction
    if len(cal_deviations) >= 3:
        recent_avg = sum(cal_deviations[-3:]) / 3
        earlier_avg = sum(cal_deviations[:-3]) / max(len(cal_deviations) - 3, 1) if len(cal_deviations) > 3 else recent_avg
        
        if recent_avg > earlier_avg + 5:
            trend_direction = "worsening"
        elif recent_avg < earlier_avg - 5:
            trend_direction = "improving"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "insufficient_data"
    
    return {
        "has_trend": len(logs) >= 3,
        "days_analyzed": len(logs[-7:]),
        "avg_calorie_deviation": round(sum(cal_deviations) / len(cal_deviations), 1) if cal_deviations else 0,
        "avg_protein_deviation": round(sum(protein_deviations) / len(protein_deviations), 1) if protein_deviations else 0,
        "trend_direction": trend_direction,
        "training_completion_rate": round(training_rate, 1),
        "calorie_deviations": cal_deviations,
    }


async def _generate_reflection_summary(
    reflection: ReflectionResult,
    trends: Optional[dict[str, Any]],
    plan: dict[str, Any],
) -> str:
    """
    Use LLM to generate natural language reflection summary.
    使用 LLM 生成自然语言反思总结
    """
    if reflection.get("severity") == "none":
        return "没有足够的执行数据进行反思分析。"
    
    # Defensive null check for trends
    if trends is None:
        trends = {"days_analyzed": 0, "trend_direction": "unknown", "avg_calorie_deviation": 0, "training_completion_rate": 0}
    
    # Build context for LLM
    context = f"""
用户今日执行情况：
- 热量偏差: {reflection.get('calorie_deviation_pct', 0):.1f}%
- 蛋白质偏差: {reflection.get('protein_deviation_pct', 0):.1f}%
- 严重程度: {reflection.get('severity')}
- 识别的模式: {', '.join(reflection.get('patterns', [])) or '无'}

趋势分析 (近{trends.get('days_analyzed', 0)}天):
- 趋势方向: {trends.get('trend_direction', '未知')}
- 平均热量偏差: {trends.get('avg_calorie_deviation', 0):.1f}%
- 训练完成率: {trends.get('training_completion_rate', 0):.1f}%

计划类型: {plan.get('day_type', '未知')}
"""
    
    llm = get_llm_client()
    
    messages = [
        {
            "role": "system",
            "content": "你是一个专业的健身营养顾问。请用简洁、鼓励性的语气总结用户的执行情况，指出亮点和需要改进的地方。回复控制在100字以内。"
        },
        {"role": "user", "content": context},
    ]
    
    try:
        response = await llm.chat(messages, temperature=0.5)
        return response.get("content", "执行分析生成失败。")
    except Exception as e:
        logger.warning(f"LLM reflection summary failed: {e}")
        # Fallback to rule-based summary
        if reflection.get("severity") == "minor":
            return f"执行良好！热量偏差仅{abs(reflection.get('calorie_deviation_pct', 0)):.1f}%，继续保持。"
        elif reflection.get("severity") == "moderate":
            return f"执行有一定偏差，热量偏差{reflection.get('calorie_deviation_pct', 0):.1f}%，建议关注。"
        else:
            return f"执行偏差较大，需要调整策略。热量偏差{reflection.get('calorie_deviation_pct', 0):.1f}%。"


async def reflect_node(state: AgentState) -> dict[str, Any]:
    """
    Reflector node: analyzes execution deviation.
    
    Enhanced with:
    - Multi-day trend analysis
    - LLM-generated insights
    - Visualization data points
    
    Args:
        state: Current agent state.
        
    Returns:
        Updated state with reflection result.
    """
    logger.info(f"Reflector node executing for run {state.get('run_id')}")
    
    plan = state.get("plan") or {}
    actor_output = state.get("actor_output") or {}
    logs = state.get("logs") or []
    
    # Early return for no data scenario
    if not actor_output or actor_output.get("status") != "success":
        # Still analyze trends if logs available
        trends = _analyze_trends(list(logs)) if logs else {
            "has_trend": False,
            "days_analyzed": 0,
            "trend_direction": "insufficient_data",
        }
        
        return {
            "reflection": ReflectionResult(
                severity="none",
                deviation_type="no_data",
                calorie_deviation_pct=0,
                protein_deviation_pct=0,
                needs_adjustment=False,
                patterns=[],
            ),
            "should_adjust": False,
            "reflection_summary": "没有足够的执行数据进行反思分析。",
            "trends": trends,
        }
    
    intake = actor_output.get("actual_intake") or {}
    
    # Current day deviation
    target_cal = plan.get("target_calories", 2000) if plan else 2000
    target_protein = plan.get("target_protein", 150) if plan else 150
    
    cal_dev = _calculate_deviation(
        target_cal,
        intake.get("calories", 0),
    )
    protein_dev = _calculate_deviation(
        target_protein,
        intake.get("protein", 0),
    )
    
    severity = _determine_severity(cal_dev)
    needs_adjustment = severity in ("moderate", "significant")
    
    # Pattern detection
    patterns = []
    if cal_dev > 15:
        patterns.append("持续热量超标")
    if cal_dev < -15:
        patterns.append("热量摄入不足")
    if protein_dev < -15:
        patterns.append("蛋白质摄入不足")
    if not actor_output.get("training_completed", True):
        patterns.append("训练计划执行率低")
    
    deviation_type = "calorie_excess" if cal_dev > 0 else "calorie_deficit"
    if abs(protein_dev) > abs(cal_dev):
        deviation_type = "protein_low" if protein_dev < 0 else "macro_imbalance"
    
    # Multi-day trend analysis - convert to list of dicts for type safety
    logs_as_dicts = [dict(log) for log in logs] if logs else []
    trends = _analyze_trends(logs_as_dicts)
    
    # Adjust decision based on trends
    if trends and trends.get("trend_direction") == "worsening" and severity == "minor":
        needs_adjustment = True
        patterns.append("趋势恶化")
    
    reflection = ReflectionResult(
        severity=severity,
        deviation_type=deviation_type,
        calorie_deviation_pct=round(cal_dev, 1),
        protein_deviation_pct=round(protein_dev, 1),
        needs_adjustment=needs_adjustment,
        patterns=patterns,
    )
    
    # Generate LLM summary
    plan_dict = dict(plan) if plan else {}
    summary = await _generate_reflection_summary(reflection, trends, plan_dict)
    
    log_agent_decision(
        logger,
        node="reflector",
        decision=f"severity_{severity}",
        reasoning=f"热量偏差{cal_dev:.1f}%，趋势: {trends.get('trend_direction', '未知') if trends else '未知'}",
        context={"patterns": patterns, "trends": trends},
    )
    
    return {
        "reflection": reflection,
        "should_adjust": needs_adjustment,
        "reflection_summary": summary,
        "trends": trends,
    }
