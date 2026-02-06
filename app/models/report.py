"""
Report models.
报告模型

Defines data structures for weekly summaries and trend analysis.
定义周报和趋势分析的数据结构
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DailyStats(BaseModel):
    """
    Statistics for a single day.
    
    Attributes:
        date: The date of the stats.
        target_calories: Planned calorie target.
        actual_calories: Actual calories consumed.
        target_protein: Planned protein target.
        actual_protein: Actual protein consumed.
        target_carbs: Planned carb target.
        actual_carbs: Actual carbs consumed.
        target_fat: Planned fat target.
        actual_fat: Actual fat consumed.
        training_planned: Whether training was planned.
        training_completed: Whether training was done.
        adherence_score: Overall adherence (0-100).
    """
    
    date: date
    target_calories: float = 0
    actual_calories: float = 0
    target_protein: float = 0
    actual_protein: float = 0
    target_carbs: float = 0
    actual_carbs: float = 0
    target_fat: float = 0
    actual_fat: float = 0
    training_planned: bool = False
    training_completed: bool = False
    adherence_score: float = Field(default=0, ge=0, le=100)
    
    @property
    def calorie_deviation(self) -> float:
        """Calculate calorie deviation percentage."""
        if self.target_calories == 0:
            return 0
        return ((self.actual_calories - self.target_calories) 
                / self.target_calories * 100)
    
    @property
    def is_within_target(self) -> bool:
        """Check if daily intake is within acceptable range (±10%)."""
        return abs(self.calorie_deviation) <= 10


class WeeklyReport(BaseModel):
    """
    Weekly summary report.
    
    Attributes:
        id: Unique report identifier.
        user_id: Associated user identifier.
        plan_id: Associated plan identifier.
        week_start: First day of the report week.
        week_end: Last day of the report week.
        daily_stats: Stats for each day of the week.
        average_calories: Average daily calorie intake.
        average_protein: Average daily protein intake.
        average_carbs: Average daily carb intake.
        average_fat: Average daily fat intake.
        total_training_sessions: Number of training sessions completed.
        training_adherence: Training plan adherence percentage.
        diet_adherence: Diet plan adherence percentage.
        weight_change_kg: Weight change over the week.
        summary: AI-generated summary text.
        recommendations: AI-generated recommendations.
        created_at: Report creation timestamp.
    """
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    plan_id: Optional[UUID] = None
    week_start: date
    week_end: date
    daily_stats: list[DailyStats] = Field(default_factory=list)
    average_calories: float = 0
    average_protein: float = 0
    average_carbs: float = 0
    average_fat: float = 0
    total_training_sessions: int = 0
    planned_training_sessions: int = 0
    training_adherence: float = Field(default=0, ge=0, le=100)
    diet_adherence: float = Field(default=0, ge=0, le=100)
    weight_start_kg: Optional[float] = None
    weight_end_kg: Optional[float] = None
    summary: Optional[str] = None
    recommendations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def weight_change_kg(self) -> Optional[float]:
        """Calculate weight change over the week."""
        if self.weight_start_kg is None or self.weight_end_kg is None:
            return None
        return round(self.weight_end_kg - self.weight_start_kg, 2)
    
    @property
    def days_logged(self) -> int:
        """Count number of days with data."""
        return len(self.daily_stats)
    
    @property
    def overall_adherence(self) -> float:
        """Calculate overall adherence score."""
        if not self.daily_stats:
            return 0
        total = sum(day.adherence_score for day in self.daily_stats)
        return round(total / len(self.daily_stats), 1)
    
    def get_trend(self) -> str:
        """
        Analyze weekly trend.
        
        Returns:
            str: 'improving', 'stable', or 'declining'.
        """
        if len(self.daily_stats) < 3:
            return "stable"
        
        first_half = self.daily_stats[:len(self.daily_stats)//2]
        second_half = self.daily_stats[len(self.daily_stats)//2:]
        
        first_avg = sum(d.adherence_score for d in first_half) / len(first_half)
        second_avg = sum(d.adherence_score for d in second_half) / len(second_half)
        
        diff = second_avg - first_avg
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        return "stable"


class ReportSummary(BaseModel):
    """Summary view of a weekly report."""
    
    id: UUID
    week_start: date
    week_end: date
    overall_adherence: float
    weight_change_kg: Optional[float]
    trend: str
    created_at: datetime


class TrendAnalysis(BaseModel):
    """
    Multi-week trend analysis.
    
    Attributes:
        user_id: Associated user identifier.
        analysis_period_weeks: Number of weeks analyzed.
        weight_trend: Overall weight trend direction.
        adherence_trend: Overall adherence trend.
        average_weekly_weight_change: Average weight change per week.
        best_performing_day_type: Day type with highest adherence.
        areas_for_improvement: Identified weak points.
        generated_at: Analysis timestamp.
    """
    
    user_id: UUID
    analysis_period_weeks: int
    weight_trend: str  # 'losing', 'gaining', 'stable'
    adherence_trend: str  # 'improving', 'stable', 'declining'
    average_weekly_weight_change: Optional[float] = None
    best_performing_day_type: Optional[str] = None
    worst_performing_day_type: Optional[str] = None
    areas_for_improvement: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
