"""
Data models package.
数据模型包

Contains Pydantic models for API validation and ORM models for persistence.
包含用于 API 验证的 Pydantic 模型和用于持久化的 ORM 模型
"""

from app.models.user import UserProfile, UserGoal, UserCreate, UserUpdate
from app.models.plan import CarbonCyclePlan, DayType, DayPlan, PlanCreate
from app.models.log import DietLog, MealType, LogCreate
from app.models.report import WeeklyReport, ReportSummary
from app.models.chat import (
    ChatSession, ChatMessage, ChatRole, ChatIntent,
    ActionCard, ActionType, ChatMessageCreate, ChatMessageResponse,
    ChatSessionSummary, ChatHistoryResponse,
)

__all__ = [
    # User models
    "UserProfile",
    "UserGoal",
    "UserCreate",
    "UserUpdate",
    # Plan models
    "CarbonCyclePlan",
    "DayType",
    "DayPlan",
    "PlanCreate",
    # Log models
    "DietLog",
    "MealType",
    "LogCreate",
    # Report models
    "WeeklyReport",
    "ReportSummary",
    # Chat models
    "ChatSession",
    "ChatMessage",
    "ChatRole",
    "ChatIntent",
    "ActionCard",
    "ActionType",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatSessionSummary",
    "ChatHistoryResponse",
]

