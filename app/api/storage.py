"""
Unified in-memory storage for API layer.
统一的内存存储层，用于 API 数据管理

Provides a centralized storage that can be easily replaced with a database later.
提供集中式存储，便于后续迁移到数据库
"""

from datetime import date
from typing import Optional
from uuid import UUID

from app.models.log import DietLog
from app.models.plan import CarbonCyclePlan
from app.models.user import UserProfile
from app.core.logging import get_logger

logger = get_logger(__name__)


class InMemoryStorage:
    """
    Centralized in-memory storage for all entities.
    集中式内存存储
    
    This class provides a single source of truth for all data,
    making it easy to migrate to a database later.
    """
    
    def __init__(self):
        self._users: dict[UUID, UserProfile] = {}
        self._plans: dict[UUID, CarbonCyclePlan] = {}
        self._logs: dict[UUID, DietLog] = {}
    
    # ========== User Operations ==========
    
    def add_user(self, user: UserProfile) -> UserProfile:
        """Add a user to storage."""
        self._users[user.id] = user
        logger.debug(f"Added user {user.id}")
        return user
    
    def get_user(self, user_id: UUID) -> Optional[UserProfile]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    def update_user(self, user_id: UUID, **updates) -> Optional[UserProfile]:
        """Update user fields."""
        user = self._users.get(user_id)
        if user:
            for field, value in updates.items():
                if hasattr(user, field):
                    setattr(user, field, value)
        return user
    
    def delete_user(self, user_id: UUID) -> bool:
        """Delete user and associated data."""
        if user_id in self._users:
            del self._users[user_id]
            # Also delete associated plans and logs
            self._plans = {k: v for k, v in self._plans.items() if v.user_id != user_id}
            self._logs = {k: v for k, v in self._logs.items() if v.user_id != user_id}
            logger.info(f"Deleted user {user_id} and associated data")
            return True
        return False
    
    def list_users(self) -> list[UserProfile]:
        """List all users."""
        return list(self._users.values())
    
    # ========== Plan Operations ==========
    
    def add_plan(self, plan: CarbonCyclePlan) -> CarbonCyclePlan:
        """Add a plan to storage."""
        self._plans[plan.id] = plan
        logger.debug(f"Added plan {plan.id} for user {plan.user_id}")
        return plan
    
    def get_plan(self, plan_id: UUID) -> Optional[CarbonCyclePlan]:
        """Get plan by ID."""
        return self._plans.get(plan_id)
    
    def get_user_plans(self, user_id: UUID) -> list[CarbonCyclePlan]:
        """Get all plans for a user."""
        return [p for p in self._plans.values() if p.user_id == user_id]
    
    def get_active_plan(self, user_id: UUID) -> Optional[CarbonCyclePlan]:
        """Get active plan for a user."""
        for plan in self._plans.values():
            if plan.user_id == user_id and plan.is_active:
                return plan
        return None
    
    def delete_plan(self, plan_id: UUID) -> bool:
        """Delete a plan."""
        if plan_id in self._plans:
            del self._plans[plan_id]
            return True
        return False
    
    # ========== Log Operations ==========
    
    def add_log(self, log: DietLog) -> DietLog:
        """Add a diet log."""
        self._logs[log.id] = log
        logger.debug(f"Added log {log.id} for user {log.user_id}")
        return log
    
    def get_log(self, log_id: UUID) -> Optional[DietLog]:
        """Get log by ID."""
        return self._logs.get(log_id)
    
    def get_user_logs(self, user_id: UUID, limit: int = 7) -> list[DietLog]:
        """Get recent logs for a user."""
        user_logs = [l for l in self._logs.values() if l.user_id == user_id]
        user_logs.sort(key=lambda x: x.date, reverse=True)
        return user_logs[:limit]
    
    def get_log_by_date(self, user_id: UUID, log_date: date) -> Optional[DietLog]:
        """Get log for a specific date."""
        for log in self._logs.values():
            if log.user_id == user_id and log.date == log_date:
                return log
        return None
    
    def update_log(self, log_id: UUID, **updates) -> Optional[DietLog]:
        """Update log fields."""
        log = self._logs.get(log_id)
        if log:
            for field, value in updates.items():
                if hasattr(log, field):
                    setattr(log, field, value)
        return log
    
    def delete_log(self, log_id: UUID) -> bool:
        """Delete a log."""
        if log_id in self._logs:
            del self._logs[log_id]
            return True
        return False
    
    def get_user_log_stats(self, user_id: UUID, days: int = 7) -> dict:
        """
        Get log statistics for a user.
        获取用户的日志统计
        """
        logs = self.get_user_logs(user_id, limit=days)
        
        if not logs:
            return {
                "days_logged": 0,
                "avg_calories": 0,
                "avg_protein": 0,
                "avg_carbs": 0,
                "avg_fat": 0,
                "training_completion_rate": 0,
            }
        
        total_cal = sum(l.total_calories or 0 for l in logs)
        total_protein = sum(l.total_protein or 0 for l in logs)
        total_carbs = sum(l.total_carbs or 0 for l in logs)
        total_fat = sum(l.total_fat or 0 for l in logs)
        training_completed = sum(1 for l in logs if l.training_completed)
        
        n = len(logs)
        return {
            "days_logged": n,
            "avg_calories": round(total_cal / n, 1),
            "avg_protein": round(total_protein / n, 1),
            "avg_carbs": round(total_carbs / n, 1),
            "avg_fat": round(total_fat / n, 1),
            "training_completion_rate": round(training_completed / n * 100, 1),
        }
    
    # ========== Utility ==========
    
    def clear_all(self):
        """Clear all data (for testing)."""
        self._users.clear()
        self._plans.clear()
        self._logs.clear()
        logger.info("Cleared all storage data")


# Singleton instance
_storage: Optional[InMemoryStorage] = None


def get_storage() -> InMemoryStorage:
    """Get the singleton storage instance."""
    global _storage
    if _storage is None:
        _storage = InMemoryStorage()
    return _storage
