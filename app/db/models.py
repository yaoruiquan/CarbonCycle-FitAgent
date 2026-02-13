"""
SQLAlchemy ORM models.
SQLAlchemy ORM 模型

Maps Pydantic models to database tables.
将 Pydantic 模型映射到数据库表
"""

from datetime import date, datetime, time
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.user import Gender, UserGoal, ActivityLevel
from app.models.plan import DayType
from app.models.log import MealType


# Use String for SQLite compatibility, PGUUID for PostgreSQL
def uuid_column():
    """Create a UUID column compatible with SQLite and PostgreSQL."""
    return Column(String(36), primary_key=True, default=lambda: str(uuid4()))


class UserModel(Base):
    """SQLAlchemy model for users."""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    gender = Column(String(20), nullable=False)  # male/female
    birth_date = Column(Date, nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    target_weight_kg = Column(Float, nullable=True)
    goal = Column(String(50), nullable=False)  # muscle_gain/fat_loss/etc
    activity_level = Column(String(50), default="moderate")
    training_days_per_week = Column(Integer, default=4)
    dietary_preferences = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    plans = relationship("PlanModel", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("LogModel", back_populates="user", cascade="all, delete-orphan")
    weight_logs = relationship("WeightLogModel", back_populates="user", cascade="all, delete-orphan")
    
    def to_pydantic(self):
        """Convert to Pydantic model."""
        from app.models.user import UserProfile, Gender, UserGoal, ActivityLevel
        from uuid import UUID
        return UserProfile(
            id=UUID(str(self.id)), # type: ignore
            name=str(self.name), # type: ignore
            email=str(self.email), # type: ignore
            hashed_password=str(self.hashed_password), # type: ignore
            gender=Gender(str(self.gender)), # type: ignore
            birth_date=self.birth_date, # type: ignore
            height_cm=float(self.height_cm), # type: ignore
            weight_kg=float(self.weight_kg), # type: ignore
            target_weight_kg=float(self.target_weight_kg) if self.target_weight_kg is not None else None, # type: ignore
            goal=UserGoal(str(self.goal)), # type: ignore
            activity_level=ActivityLevel(str(self.activity_level)), # type: ignore
            training_days_per_week=int(self.training_days_per_week), # type: ignore
            dietary_preferences=list(self.dietary_preferences) if self.dietary_preferences else [], # type: ignore
            created_at=self.created_at, # type: ignore
            updated_at=self.updated_at, # type: ignore
        )
    
    @classmethod
    def from_pydantic(cls, user) -> "UserModel":
        """Create from Pydantic model."""
        return cls(
            id=str(user.id),
            name=user.name,
            email=getattr(user, 'email', None),
            hashed_password=getattr(user, 'hashed_password', None),
            gender=user.gender.value if hasattr(user.gender, 'value') else user.gender,
            birth_date=user.birth_date,
            height_cm=user.height_cm,
            weight_kg=user.weight_kg,
            target_weight_kg=user.target_weight_kg,
            goal=user.goal.value if hasattr(user.goal, 'value') else user.goal,
            activity_level=user.activity_level.value if hasattr(user.activity_level, 'value') else user.activity_level,
            training_days_per_week=user.training_days_per_week,
            dietary_preferences=user.dietary_preferences,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class PlanModel(Base):
    """SQLAlchemy model for carbon cycle plans."""
    
    __tablename__ = "plans"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), default="Carbon Cycle Plan")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    cycle_length_days = Column(Integer, default=7)
    base_calories = Column(Float, nullable=False)
    goal_deficit = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("UserModel", back_populates="plans")
    days = relationship("DayPlanModel", back_populates="plan", cascade="all, delete-orphan")


class DayPlanModel(Base):
    """SQLAlchemy model for daily plans within a cycle."""
    
    __tablename__ = "day_plans"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    day_type = Column(String(20), nullable=False)  # high_carb/medium_carb/low_carb
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    fiber_g = Column(Float, default=25)
    training_scheduled = Column(Boolean, default=False)
    training_type = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    plan = relationship("PlanModel", back_populates="days")


class LogModel(Base):
    """SQLAlchemy model for diet logs."""
    
    __tablename__ = "logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    date = Column(Date, nullable=False)
    water_ml = Column(Float, default=0)
    training_completed = Column(Boolean, default=False)
    training_notes = Column(Text, nullable=True)
    mood = Column(Integer, nullable=True)
    energy_level = Column(Integer, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("UserModel", back_populates="logs")
    meals = relationship("MealModel", back_populates="log", cascade="all, delete-orphan")


class MealModel(Base):
    """SQLAlchemy model for meals within a log."""
    
    __tablename__ = "meals"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    log_id = Column(String(36), ForeignKey("logs.id", ondelete="CASCADE"), nullable=False)
    meal_type = Column(String(50), nullable=False)
    time = Column(Time, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    log = relationship("LogModel", back_populates="meals")
    items = relationship("FoodItemModel", back_populates="meal", cascade="all, delete-orphan")


class FoodItemModel(Base):
    """SQLAlchemy model for food items within a meal."""
    
    __tablename__ = "food_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meal_id = Column(String(36), ForeignKey("meals.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), default="g")
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, default=0)
    carbs_g = Column(Float, default=0)
    fat_g = Column(Float, default=0)
    fiber_g = Column(Float, default=0)
    
    # Relationships
    meal = relationship("MealModel", back_populates="items")


class ChatSessionModel(Base):
    """SQLAlchemy model for chat sessions."""
    
    __tablename__ = "chat_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), default="新对话")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    messages = relationship("ChatMessageModel", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessageModel.timestamp")
    
    def to_pydantic(self):
        """Convert to Pydantic model."""
        from app.models.chat import ChatSession, ChatMessage, ChatRole, ChatIntent
        from uuid import UUID
        
        # Safely access messages only if they are loaded to avoid MissingGreenlet error
        messages = []
        try:
            # Check if relationship is loaded
            if "messages" in self.__dict__:
                messages = [msg.to_pydantic() for msg in self.messages]
        except Exception:
            pass

        return ChatSession(
            id=UUID(str(self.id)),
            user_id=UUID(str(self.user_id)),
            title=str(self.title or "新对话"),
            messages=messages,
            is_active=bool(self.is_active),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ChatMessageModel(Base):
    """SQLAlchemy model for chat messages."""
    
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user/assistant/system
    content = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)  # Classified intent
    metadata_json = Column(JSON, default=dict)  # Additional data
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationships
    session = relationship("ChatSessionModel", back_populates="messages")
    
    def to_pydantic(self):
        """Convert to Pydantic model."""
        from app.models.chat import ChatMessage, ChatRole, ChatIntent
        from uuid import UUID
        return ChatMessage(
            id=UUID(str(self.id)),
            role=ChatRole(str(self.role)),
            content=str(self.content),
            intent=ChatIntent(str(self.intent)) if self.intent else None,
            metadata=self.metadata_json or {},
            timestamp=self.timestamp,
        )


class WeightLogModel(Base):
    """SQLAlchemy model for weight logs. 体重记录 ORM 模型"""
    
    __tablename__ = "weight_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    weight_kg = Column(Float, nullable=False)
    body_fat_pct = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship("UserModel", back_populates="weight_logs")


