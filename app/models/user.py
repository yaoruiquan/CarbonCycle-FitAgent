"""
User profile and goal models.
用户画像和目标模型

Defines user-related data structures for the carbon cycle planning system.
定义碳循环规划系统的用户相关数据结构
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class UserGoal(str, Enum):
    """User fitness goal categories."""
    
    MUSCLE_GAIN = "muscle_gain"      # 增肌
    FAT_LOSS = "fat_loss"            # 减脂
    MAINTENANCE = "maintenance"       # 维持
    RECOMPOSITION = "recomposition"  # 重塑（同时减脂增肌）


class ActivityLevel(str, Enum):
    """Physical activity level multipliers for TDEE calculation."""
    
    SEDENTARY = "sedentary"          # 久坐 (1.2)
    LIGHT = "light"                  # 轻度活动 (1.375)
    MODERATE = "moderate"            # 中度活动 (1.55)
    ACTIVE = "active"                # 高度活动 (1.725)
    VERY_ACTIVE = "very_active"      # 极高活动 (1.9)


class Gender(str, Enum):
    """Biological gender for BMR calculation."""
    
    MALE = "male"
    FEMALE = "female"


class UserProfile(BaseModel):
    """
    Complete user profile for carbon cycle planning.
    
    Attributes:
        id: Unique user identifier.
        name: User display name.
        gender: Biological gender for BMR calculation.
        birth_date: Date of birth for age calculation.
        height_cm: Height in centimeters.
        weight_kg: Current weight in kilograms.
        target_weight_kg: Goal weight in kilograms.
        goal: Primary fitness goal.
        activity_level: Base activity level.
        training_days_per_week: Number of training sessions per week.
        dietary_preferences: Food preferences or restrictions.
        created_at: Profile creation timestamp.
        updated_at: Last update timestamp.
    """
    
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    hashed_password: str = Field(...)
    gender: Gender
    birth_date: date
    height_cm: float = Field(..., gt=100, lt=250)
    weight_kg: float = Field(..., gt=30, lt=300)
    target_weight_kg: Optional[float] = Field(None, gt=30, lt=300)
    goal: UserGoal
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    training_days_per_week: int = Field(default=4, ge=0, le=7)
    dietary_preferences: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator("target_weight_kg", mode="before")
    @classmethod
    def validate_target_weight(cls, v: Optional[float], info) -> Optional[float]:
        """Validate target weight is reasonable given current weight."""
        if v is None:
            return v
        return v
    
    def calculate_age(self) -> int:
        """
        Calculate user's current age.
        
        Returns:
            int: Age in years.
        """
        today = date.today()
        age = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1
        return age
    
    def calculate_bmr(self) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.
        
        Returns:
            float: BMR in kcal/day.
        """
        age = self.calculate_age()
        
        if self.gender == Gender.MALE:
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * age + 5
        else:
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * age - 161
        
        return round(bmr, 1)
    
    def calculate_tdee(self) -> float:
        """
        Calculate Total Daily Energy Expenditure.
        
        Returns:
            float: TDEE in kcal/day.
        """
        activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.VERY_ACTIVE: 1.9,
        }
        
        bmr = self.calculate_bmr()
        multiplier = activity_multipliers[self.activity_level]
        
        return round(bmr * multiplier, 1)


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    
    id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    gender: Gender
    birth_date: date
    height_cm: float = Field(..., gt=100, lt=250)
    weight_kg: float = Field(..., gt=30, lt=300)
    target_weight_kg: Optional[float] = Field(None, gt=30, lt=300)
    goal: UserGoal
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    training_days_per_week: int = Field(default=4, ge=0, le=7)
    dietary_preferences: list[str] = Field(default_factory=list)


class UserLogin(BaseModel):
    """Schema for user login."""
    
    email: str
    password: str


class Token(BaseModel):
    """Schema for authentication token."""
    
    access_token: str
    token_type: str = "bearer"
    user_id: str
    user_name: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    weight_kg: Optional[float] = Field(None, gt=30, lt=300)
    target_weight_kg: Optional[float] = Field(None, gt=30, lt=300)
    goal: Optional[UserGoal] = None
    activity_level: Optional[ActivityLevel] = None
    training_days_per_week: Optional[int] = Field(None, ge=0, le=7)
    dietary_preferences: Optional[list[str]] = None
