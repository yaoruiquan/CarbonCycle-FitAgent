"""
Adjustment engine service.
调整引擎服务

Generates dynamic plan adjustments based on deviation analysis.
基于偏差分析生成动态计划调整
"""

from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger
from app.models.user import UserGoal
from app.services.execution_analysis import (
    DailyAnalysis,
    DeviationSeverity,
    DeviationType,
)

logger = get_logger(__name__)

MAX_CALORIE_ADJUSTMENT_PCT = 0.15


@dataclass
class AdjustmentRecommendation:
    """Single adjustment recommendation."""
    action: str
    reasoning: str
    priority: str

    def to_dict(self) -> dict:
        return {"action": self.action, "reasoning": self.reasoning, "priority": self.priority}


@dataclass 
class PlanModification:
    """Plan modification details."""
    calorie_adjustment: float
    protein_adjustment: float
    carbs_adjustment: float
    fat_adjustment: float
    day_type_changes: list[dict]

    def to_dict(self) -> dict:
        return {
            "calorie_adjustment": self.calorie_adjustment,
            "macro_adjustments": {
                "protein_g": self.protein_adjustment,
                "carbs_g": self.carbs_adjustment,
                "fat_g": self.fat_adjustment,
            },
            "day_type_changes": self.day_type_changes,
        }


@dataclass
class AdjustmentPlan:
    """Complete adjustment plan."""
    adjustment_type: str
    immediate_actions: list[AdjustmentRecommendation]
    plan_modifications: PlanModification
    behavioral_suggestions: list[dict]
    prevention_strategies: list[str]
    expected_outcome: str
    confidence: float
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "adjustment_type": self.adjustment_type,
            "immediate_actions": [a.to_dict() for a in self.immediate_actions],
            "plan_modifications": self.plan_modifications.to_dict(),
            "behavioral_suggestions": self.behavioral_suggestions,
            "prevention_strategies": self.prevention_strategies,
            "expected_outcome": self.expected_outcome,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class AdjustmentEngine:
    """Engine for generating dynamic plan adjustments."""

    def __init__(self, max_adjustment_pct: float = MAX_CALORIE_ADJUSTMENT_PCT) -> None:
        self.max_adjustment_pct = max_adjustment_pct

    def _calculate_calorie_adjustment(self, analyses: list[DailyAnalysis], goal: UserGoal) -> float:
        if not analyses:
            return 0
        avg_deviation = sum(a.calories.absolute_diff for a in analyses) / len(analyses)
        adjustment = -avg_deviation * 0.5
        return max(-200, min(200, adjustment))

    def _generate_immediate_actions(self, analysis: DailyAnalysis) -> list[AdjustmentRecommendation]:
        actions = []
        dev_type = analysis.primary_deviation_type
        
        if dev_type == DeviationType.CALORIE_EXCESS:
            actions.append(AdjustmentRecommendation(
                action="增加明天活动量，目标额外消耗200千卡",
                reasoning="弥补热量超标",
                priority="high",
            ))
        elif dev_type == DeviationType.PROTEIN_LOW:
            actions.append(AdjustmentRecommendation(
                action="每餐增加一份蛋白质来源",
                reasoning="蛋白质不足影响恢复",
                priority="high",
            ))
        elif dev_type == DeviationType.TRAINING_SKIPPED:
            actions.append(AdjustmentRecommendation(
                action="安排补训或降低碳水摄入",
                reasoning="没有训练消耗不需要额外碳水",
                priority="medium",
            ))
        return actions

    def _generate_behavioral_suggestions(self, patterns: list[str]) -> list[dict]:
        suggestions = []
        if "持续热量超标" in patterns:
            suggestions.append({"suggestion": "使用更小餐盘", "implementation": "自然减少摄入"})
        if "蛋白质摄入不足" in patterns:
            suggestions.append({"suggestion": "提前准备蛋白质零食", "implementation": "随身携带"})
        if "周末执行率下降" in patterns:
            suggestions.append({"suggestion": "周末提前规划餐食", "implementation": "周五制定计划"})
        return suggestions

    def _generate_prevention_strategies(self, patterns: list[str]) -> list[str]:
        strategies = []
        if "持续热量超标" in patterns:
            strategies.append("限制高热量食物购买")
        if "训练计划执行率低" in patterns:
            strategies.append("寻找训练伙伴")
        return strategies

    def generate_adjustment_plan(
        self,
        analyses: list[DailyAnalysis],
        patterns: list[str],
        goal: UserGoal,
    ) -> AdjustmentPlan:
        """Generate comprehensive adjustment plan."""
        if not analyses:
            return AdjustmentPlan(
                adjustment_type="none",
                immediate_actions=[],
                plan_modifications=PlanModification(0, 0, 0, 0, []),
                behavioral_suggestions=[],
                prevention_strategies=[],
                expected_outcome="无需调整",
                confidence=1.0,
                reasoning="数据不足",
            )

        recent = analyses[-1]
        severity = recent.severity
        adj_type = "minor" if severity == DeviationSeverity.MINOR else (
            "moderate" if severity == DeviationSeverity.MODERATE else "significant"
        )

        calorie_adj = self._calculate_calorie_adjustment(analyses, goal)
        plan_mods = PlanModification(
            calorie_adjustment=round(calorie_adj, 0),
            protein_adjustment=0,
            carbs_adjustment=round(calorie_adj * 0.6 / 4, 1),
            fat_adjustment=round(calorie_adj * 0.4 / 9, 1),
            day_type_changes=[],
        )

        outcome = f"预期通过调整每日热量{abs(calorie_adj):.0f}千卡，2周内回到目标轨道"
        
        return AdjustmentPlan(
            adjustment_type=adj_type,
            immediate_actions=self._generate_immediate_actions(recent),
            plan_modifications=plan_mods,
            behavioral_suggestions=self._generate_behavioral_suggestions(patterns),
            prevention_strategies=self._generate_prevention_strategies(patterns),
            expected_outcome=outcome,
            confidence=min(0.9, 0.5 + 0.1 * len(analyses)),
            reasoning=f"基于{len(analyses)}天数据，主要问题：{', '.join(patterns) or '无'}",
        )
