"""
Carbon cycle plan models.
碳循环计划模型

Defines data structures for carb cycling meal plans.
定义碳水循环饮食计划的数据结构
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DayType(str, Enum):
    """Carbon cycle day type categories."""
    
    HIGH_CARB = "high_carb"      # 高碳日 (训练日)
    MEDIUM_CARB = "medium_carb"  # 中碳日 (轻量训练)
    LOW_CARB = "low_carb"        # 低碳日 (休息日)
    REFEED = "refeed"            # 再喂食日 (代谢恢复)


class MacroNutrients(BaseModel):
    """
    Macronutrient targets in grams.
    """
    
    protein_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    fiber_g: float = Field(default=25.0, ge=0)
    
    @property
    def total_calories(self) -> float:
        """Calculate total calories from macros."""
        return self.protein_g * 4 + self.carbs_g * 4 + self.fat_g * 9


class DayPlan(BaseModel):
    """
    Single day plan within a carbon cycle.
    """
    
    date: date
    day_type: DayType
    macros: MacroNutrients
    training_scheduled: bool = False
    training_type: Optional[str] = None
    notes: Optional[str] = None
    
    @property
    def target_calories(self) -> float:
        """Get target calories for the day."""
        return self.macros.total_calories


class CarbonCyclePlan(BaseModel):
    """
    Complete carbon cycle plan spanning multiple days.
    """
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str = Field(default="Carbon Cycle Plan")
    start_date: date
    end_date: date
    cycle_length_days: int = Field(default=7, ge=3, le=14)
    days: list[DayPlan] = Field(default_factory=list)
    base_calories: float = Field(..., gt=1000, lt=10000)
    goal_deficit: float = Field(default=0, ge=-1500, le=1000)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    notes: Optional[str] = Field(default=None, description="AI生成的计划建议")
    
    @property
    def total_days(self) -> int:
        return (self.end_date - self.start_date).days + 1
    
    @property
    def average_daily_calories(self) -> float:
        if not self.days:
            return self.base_calories
        total = sum(day.target_calories for day in self.days)
        return round(total / len(self.days), 1)
    
    def get_day_plan(self, target_date: date) -> Optional[DayPlan]:
        for day in self.days:
            if day.date == target_date:
                return day
        return None
    
    def count_day_types(self) -> dict[DayType, int]:
        counts = {day_type: 0 for day_type in DayType}
        for day in self.days:
            counts[day.day_type] += 1
        return counts


class PlanCreate(BaseModel):
    """Schema for creating a new carbon cycle plan."""
    
    user_id: UUID
    name: str = Field(default="Carbon Cycle Plan")
    start_date: date
    cycle_length_days: int = Field(default=7, ge=3, le=14)
    num_cycles: int = Field(default=4, ge=1, le=12)
    goal_deficit: float = Field(default=0, ge=-1500, le=1000)
    
    high_carb_days: int = Field(default=2, ge=0, le=7)
    medium_carb_days: int = Field(default=2, ge=0, le=7)
    low_carb_days: int = Field(default=3, ge=0, le=7)


class PlanUpdate(BaseModel):
    """Schema for updating an existing plan."""
    days: Optional[list[DayPlan]] = None
    is_active: Optional[bool] = None
    name: Optional[str] = None


class PlanSummary(BaseModel):
    """Summary view of a carbon cycle plan."""
    
    id: UUID
    name: str
    start_date: date
    end_date: date
    is_active: bool
    average_daily_calories: float
    day_type_counts: dict[str, int]
