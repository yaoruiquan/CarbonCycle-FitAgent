"""
Report generation service.
报告生成服务

Aggregates weekly data and generates summary reports.
汇总周数据并生成摘要报告
"""

from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.models.log import DietLog
from app.models.plan import CarbonCyclePlan
from app.models.report import DailyStats, WeeklyReport
from app.services.execution_analysis import DailyAnalysis

logger = get_logger(__name__)


class ReportService:
    """Service for generating weekly and periodic reports."""

    def build_daily_stats(self, analysis: DailyAnalysis) -> DailyStats:
        """Convert daily analysis to stats."""
        return DailyStats(
            date=analysis.date,
            target_calories=analysis.calories.target,
            actual_calories=analysis.calories.actual,
            target_protein=analysis.protein.target,
            actual_protein=analysis.protein.actual,
            target_carbs=analysis.carbs.target,
            actual_carbs=analysis.carbs.actual,
            target_fat=analysis.fat.target,
            actual_fat=analysis.fat.actual,
            training_planned=not analysis.training_deviation or True,
            training_completed=not analysis.training_deviation,
            adherence_score=analysis.adherence_score,
        )

    def generate_weekly_report(
        self,
        user_id: UUID,
        plan: CarbonCyclePlan,
        analyses: list[DailyAnalysis],
        week_start: date,
        weight_start: Optional[float] = None,
        weight_end: Optional[float] = None,
    ) -> WeeklyReport:
        """Generate weekly summary report."""
        week_end = week_start + timedelta(days=6)
        
        daily_stats = [self.build_daily_stats(a) for a in analyses]
        
        if daily_stats:
            avg_cal = sum(s.actual_calories for s in daily_stats) / len(daily_stats)
            avg_protein = sum(s.actual_protein for s in daily_stats) / len(daily_stats)
            avg_carbs = sum(s.actual_carbs for s in daily_stats) / len(daily_stats)
            avg_fat = sum(s.actual_fat for s in daily_stats) / len(daily_stats)
            training_done = sum(1 for s in daily_stats if s.training_completed)
            training_planned = sum(1 for s in daily_stats if s.training_planned)
            diet_adherence = sum(s.adherence_score for s in daily_stats) / len(daily_stats)
        else:
            avg_cal = avg_protein = avg_carbs = avg_fat = 0
            training_done = training_planned = 0
            diet_adherence = 0

        training_adherence = (training_done / training_planned * 100) if training_planned else 100

        report = WeeklyReport(
            user_id=user_id,
            plan_id=plan.id,
            week_start=week_start,
            week_end=week_end,
            daily_stats=daily_stats,
            average_calories=round(avg_cal, 1),
            average_protein=round(avg_protein, 1),
            average_carbs=round(avg_carbs, 1),
            average_fat=round(avg_fat, 1),
            total_training_sessions=training_done,
            planned_training_sessions=training_planned,
            training_adherence=round(training_adherence, 1),
            diet_adherence=round(diet_adherence, 1),
            weight_start_kg=weight_start,
            weight_end_kg=weight_end,
        )

        logger.info(f"Generated weekly report for user {user_id}: adherence={diet_adherence:.1f}%")
        return report
