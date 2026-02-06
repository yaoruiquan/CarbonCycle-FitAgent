"""
Execution deviation analysis service.
执行偏差分析服务

Compares actual intake against planned targets and identifies patterns.
对比实际摄入与计划目标并识别模式
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from app.core.logging import get_logger
from app.models.log import DietLog
from app.models.plan import DayPlan

logger = get_logger(__name__)


class DeviationSeverity(str, Enum):
    """Severity levels for plan deviations."""
    
    MINOR = "minor"           # <10% deviation
    MODERATE = "moderate"     # 10-20% deviation
    SIGNIFICANT = "significant"  # >20% deviation


class DeviationType(str, Enum):
    """Types of deviations from plan."""
    
    CALORIE_EXCESS = "calorie_excess"
    CALORIE_DEFICIT = "calorie_deficit"
    PROTEIN_LOW = "protein_low"
    CARBS_EXCESS = "carbs_excess"
    CARBS_DEFICIT = "carbs_deficit"
    FAT_EXCESS = "fat_excess"
    TRAINING_SKIPPED = "training_skipped"
    NO_DEVIATION = "no_deviation"


@dataclass
class MacroDeviation:
    """Deviation data for a single macronutrient."""
    
    target: float
    actual: float
    
    @property
    def absolute_diff(self) -> float:
        """Absolute difference between actual and target."""
        return self.actual - self.target
    
    @property
    def percentage_diff(self) -> float:
        """Percentage difference from target."""
        if self.target == 0:
            return 0
        return ((self.actual - self.target) / self.target) * 100


@dataclass
class DailyAnalysis:
    """Analysis result for a single day."""
    
    date: date
    calories: MacroDeviation
    protein: MacroDeviation
    carbs: MacroDeviation
    fat: MacroDeviation
    training_deviation: bool
    severity: DeviationSeverity
    primary_deviation_type: DeviationType
    adherence_score: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "date": self.date.isoformat(),
            "deviation_summary": {
                "calories": {
                    "absolute": round(self.calories.absolute_diff, 1),
                    "percentage": round(self.calories.percentage_diff, 1),
                },
                "protein": {
                    "absolute": round(self.protein.absolute_diff, 1),
                    "percentage": round(self.protein.percentage_diff, 1),
                },
                "carbs": {
                    "absolute": round(self.carbs.absolute_diff, 1),
                    "percentage": round(self.carbs.percentage_diff, 1),
                },
                "fat": {
                    "absolute": round(self.fat.absolute_diff, 1),
                    "percentage": round(self.fat.percentage_diff, 1),
                },
            },
            "training_skipped": self.training_deviation,
            "severity": self.severity.value,
            "primary_deviation_type": self.primary_deviation_type.value,
            "adherence_score": round(self.adherence_score, 1),
        }


class ExecutionAnalysisService:
    """
    Service for analyzing diet execution against plans.
    
    Computes deviations, identifies patterns, and assesses impact.
    """
    
    def __init__(
        self,
        minor_threshold: float = 0.10,
        moderate_threshold: float = 0.20,
    ) -> None:
        """
        Initialize analysis service.
        
        Args:
            minor_threshold: Max deviation for minor classification.
            moderate_threshold: Max deviation for moderate classification.
        """
        self.minor_threshold = minor_threshold
        self.moderate_threshold = moderate_threshold
    
    def _determine_severity(self, percentage: float) -> DeviationSeverity:
        """
        Determine severity based on percentage deviation.
        
        Args:
            percentage: Absolute percentage deviation.
            
        Returns:
            DeviationSeverity classification.
        """
        abs_pct = abs(percentage) / 100
        
        if abs_pct <= self.minor_threshold:
            return DeviationSeverity.MINOR
        elif abs_pct <= self.moderate_threshold:
            return DeviationSeverity.MODERATE
        else:
            return DeviationSeverity.SIGNIFICANT
    
    def _determine_primary_deviation(
        self,
        calories_dev: MacroDeviation,
        protein_dev: MacroDeviation,
        training_skipped: bool,
    ) -> DeviationType:
        """
        Determine the primary type of deviation.
        
        Args:
            calories_dev: Calorie deviation data.
            protein_dev: Protein deviation data.
            training_skipped: Whether training was skipped.
            
        Returns:
            Primary DeviationType.
        """
        if training_skipped:
            return DeviationType.TRAINING_SKIPPED
        
        cal_pct = calories_dev.percentage_diff
        protein_pct = protein_dev.percentage_diff
        
        # Check if within acceptable range
        if abs(cal_pct) <= 10 and abs(protein_pct) <= 10:
            return DeviationType.NO_DEVIATION
        
        # Prioritize calorie deviation
        if abs(cal_pct) > abs(protein_pct):
            if cal_pct > 0:
                return DeviationType.CALORIE_EXCESS
            else:
                return DeviationType.CALORIE_DEFICIT
        else:
            if protein_pct < -10:
                return DeviationType.PROTEIN_LOW
            return DeviationType.NO_DEVIATION
    
    def _calculate_adherence_score(
        self,
        calories_dev: MacroDeviation,
        protein_dev: MacroDeviation,
        training_deviation: bool,
    ) -> float:
        """
        Calculate overall adherence score (0-100).
        
        Args:
            calories_dev: Calorie deviation.
            protein_dev: Protein deviation.
            training_deviation: Whether training was skipped.
            
        Returns:
            Adherence score from 0 to 100.
        """
        # Base score of 100
        score = 100.0
        
        # Calorie deviation penalty (max 40 points)
        cal_penalty = min(40, abs(calories_dev.percentage_diff) * 2)
        score -= cal_penalty
        
        # Protein deviation penalty (max 30 points)
        protein_penalty = min(30, abs(protein_dev.percentage_diff) * 1.5)
        score -= protein_penalty
        
        # Training skip penalty (20 points)
        if training_deviation:
            score -= 20
        
        return max(0, min(100, score))
    
    def analyze_day(
        self,
        plan: DayPlan,
        log: DietLog,
    ) -> DailyAnalysis:
        """
        Analyze a single day's execution against plan.
        
        Args:
            plan: Planned targets for the day.
            log: Actual execution log.
            
        Returns:
            DailyAnalysis with deviation data.
        """
        # Calculate deviations
        calories_dev = MacroDeviation(
            target=plan.target_calories,
            actual=log.total_calories,
        )
        
        protein_dev = MacroDeviation(
            target=plan.macros.protein_g,
            actual=log.total_protein,
        )
        
        carbs_dev = MacroDeviation(
            target=plan.macros.carbs_g,
            actual=log.total_carbs,
        )
        
        fat_dev = MacroDeviation(
            target=plan.macros.fat_g,
            actual=log.total_fat,
        )
        
        # Check training deviation
        training_deviation = plan.training_scheduled and not log.training_completed
        
        # Determine severity
        severity = self._determine_severity(calories_dev.percentage_diff)
        
        # Determine primary deviation type
        primary_type = self._determine_primary_deviation(
            calories_dev, protein_dev, training_deviation
        )
        
        # Calculate adherence score
        adherence = self._calculate_adherence_score(
            calories_dev, protein_dev, training_deviation
        )
        
        analysis = DailyAnalysis(
            date=log.date,
            calories=calories_dev,
            protein=protein_dev,
            carbs=carbs_dev,
            fat=fat_dev,
            training_deviation=training_deviation,
            severity=severity,
            primary_deviation_type=primary_type,
            adherence_score=adherence,
        )
        
        logger.debug(
            f"Day analysis: date={log.date}, "
            f"severity={severity.value}, adherence={adherence:.1f}"
        )
        
        return analysis
    
    def analyze_week(
        self,
        plans: list[DayPlan],
        logs: list[DietLog],
    ) -> list[DailyAnalysis]:
        """
        Analyze a week's worth of execution.
        
        Args:
            plans: List of daily plans.
            logs: List of daily logs.
            
        Returns:
            List of DailyAnalysis for each matched day.
        """
        # Match plans and logs by date
        plan_map = {p.date: p for p in plans}
        
        analyses = []
        for log in logs:
            if log.date in plan_map:
                analysis = self.analyze_day(plan_map[log.date], log)
                analyses.append(analysis)
        
        return analyses
    
    def identify_patterns(
        self,
        analyses: list[DailyAnalysis],
    ) -> list[str]:
        """
        Identify recurring deviation patterns.
        
        Args:
            analyses: List of daily analyses.
            
        Returns:
            List of identified pattern descriptions.
        """
        if not analyses:
            return []
        
        patterns = []
        
        # Check for consistent calorie excess
        excess_days = sum(
            1 for a in analyses 
            if a.primary_deviation_type == DeviationType.CALORIE_EXCESS
        )
        if excess_days >= len(analyses) // 2:
            patterns.append("持续热量超标")
        
        # Check for protein deficiency
        protein_low_days = sum(
            1 for a in analyses 
            if a.protein.percentage_diff < -15
        )
        if protein_low_days >= len(analyses) // 2:
            patterns.append("蛋白质摄入不足")
        
        # Check for training skips
        training_skips = sum(1 for a in analyses if a.training_deviation)
        if training_skips >= 2:
            patterns.append("训练计划执行率低")
        
        # Check for weekend pattern
        if len(analyses) >= 7:
            weekend_adherence = [
                a.adherence_score for a in analyses 
                if a.date.weekday() >= 5
            ]
            weekday_adherence = [
                a.adherence_score for a in analyses 
                if a.date.weekday() < 5
            ]
            
            if weekend_adherence and weekday_adherence:
                if sum(weekend_adherence) / len(weekend_adherence) < \
                   sum(weekday_adherence) / len(weekday_adherence) - 15:
                    patterns.append("周末执行率下降")
        
        return patterns
