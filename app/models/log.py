"""
Diet log models.
饮食记录模型

Defines data structures for tracking meal intake and execution.
定义用于跟踪餐食摄入和执行的数据结构
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MealType(str, Enum):
    """Types of meals throughout the day."""
    
    BREAKFAST = "breakfast"      # 早餐
    MORNING_SNACK = "morning_snack"  # 上午加餐
    LUNCH = "lunch"              # 午餐
    AFTERNOON_SNACK = "afternoon_snack"  # 下午加餐
    DINNER = "dinner"            # 晚餐
    EVENING_SNACK = "evening_snack"  # 晚间加餐
    PRE_WORKOUT = "pre_workout"  # 训练前
    POST_WORKOUT = "post_workout"  # 训练后


class FoodItem(BaseModel):
    """
    Individual food item within a meal.
    
    Attributes:
        name: Food name/description.
        quantity: Amount consumed.
        unit: Unit of measurement (g, ml, piece, etc.).
        calories: Estimated calories.
        protein_g: Protein content in grams.
        carbs_g: Carbohydrate content in grams.
        fat_g: Fat content in grams.
        fiber_g: Fiber content in grams.
    """
    
    name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(..., gt=0)
    unit: str = Field(default="g", max_length=20)
    calories: float = Field(..., ge=0)
    protein_g: float = Field(default=0, ge=0)
    carbs_g: float = Field(default=0, ge=0)
    fat_g: float = Field(default=0, ge=0)
    fiber_g: float = Field(default=0, ge=0)


class MealLog(BaseModel):
    """
    Record of a single meal.
    
    Attributes:
        meal_type: Type of meal.
        time: Time the meal was consumed.
        items: List of food items in the meal.
        notes: Additional notes about the meal.
    """
    
    meal_type: MealType
    time: time
    items: list[FoodItem] = Field(default_factory=list)
    notes: Optional[str] = None
    
    @property
    def total_calories(self) -> float:
        """Calculate total calories for the meal."""
        return sum(item.calories for item in self.items)
    
    @property
    def total_protein(self) -> float:
        """Calculate total protein for the meal."""
        return sum(item.protein_g for item in self.items)
    
    @property
    def total_carbs(self) -> float:
        """Calculate total carbs for the meal."""
        return sum(item.carbs_g for item in self.items)
    
    @property
    def total_fat(self) -> float:
        """Calculate total fat for the meal."""
        return sum(item.fat_g for item in self.items)


class DietLog(BaseModel):
    """
    Complete daily diet log.
    
    Attributes:
        id: Unique log identifier.
        user_id: Associated user identifier.
        plan_id: Associated plan identifier.
        date: Date of the log.
        meals: List of meal records.
        water_ml: Water intake in milliliters.
        training_completed: Whether training was completed.
        training_notes: Notes about training session.
        mood: Overall mood (1-5 scale).
        energy_level: Energy level (1-5 scale).
        sleep_hours: Sleep duration previous night.
        created_at: Log creation timestamp.
        updated_at: Last update timestamp.
    """
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    plan_id: Optional[UUID] = None
    date: date
    meals: list[MealLog] = Field(default_factory=list)
    water_ml: float = Field(default=0, ge=0)
    training_completed: bool = False
    training_notes: Optional[str] = None
    mood: Optional[int] = Field(None, ge=1, le=5)
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def total_calories(self) -> float:
        """Calculate total daily calories."""
        return sum(meal.total_calories for meal in self.meals)
    
    @property
    def total_protein(self) -> float:
        """Calculate total daily protein in grams."""
        return sum(meal.total_protein for meal in self.meals)
    
    @property
    def total_carbs(self) -> float:
        """Calculate total daily carbs in grams."""
        return sum(meal.total_carbs for meal in self.meals)
    
    @property
    def total_fat(self) -> float:
        """Calculate total daily fat in grams."""
        return sum(meal.total_fat for meal in self.meals)
    
    @property
    def meal_count(self) -> int:
        """Get number of meals logged."""
        return len(self.meals)
    
    def get_macro_summary(self) -> dict[str, float]:
        """
        Get summary of macronutrient intake.
        
        Returns:
            dict with calories, protein, carbs, fat totals.
        """
        return {
            "calories": self.total_calories,
            "protein_g": self.total_protein,
            "carbs_g": self.total_carbs,
            "fat_g": self.total_fat,
        }


class LogCreate(BaseModel):
    """Schema for creating a new diet log."""
    
    user_id: UUID
    plan_id: Optional[UUID] = None
    date: date
    meals: list[MealLog] = Field(default_factory=list)
    water_ml: float = Field(default=0, ge=0)
    training_completed: bool = False
    training_notes: Optional[str] = None
    mood: Optional[int] = Field(None, ge=1, le=5)
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)


class LogUpdate(BaseModel):
    """Schema for updating a diet log."""
    
    meals: Optional[list[MealLog]] = None
    water_ml: Optional[float] = Field(None, ge=0)
    training_completed: Optional[bool] = None
    training_notes: Optional[str] = None
    mood: Optional[int] = Field(None, ge=1, le=5)
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
