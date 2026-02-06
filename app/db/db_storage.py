"""
Database storage layer.
数据库存储层

Provides persistent storage using SQLAlchemy with the same interface as InMemoryStorage.
使用 SQLAlchemy 提供持久化存储，与 InMemoryStorage 具有相同接口
"""

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user_repo import UserRepository
from app.db.repositories.plan_repo import PlanRepository
from app.db.repositories.log_repo import LogRepository
from app.models.user import UserProfile
from app.models.plan import CarbonCyclePlan
from app.models.log import DietLog


class DatabaseStorage:
    """
    Persistent database storage.
    数据库持久化存储
    
    Uses the same interface as InMemoryStorage for easy swapping.
    与 InMemoryStorage 使用相同的接口，便于切换
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._user_repo = UserRepository(session)
        self._plan_repo = PlanRepository(session)
        self._log_repo = LogRepository(session)
    
    # ============ User Operations ============
    
    async def add_user(self, user: UserProfile) -> UserProfile:
        """Add a new user."""
        return await self._user_repo.create(user)
    
    async def get_user(self, user_id: UUID | str) -> Optional[UserProfile]:
        """Get user by ID."""
        return await self._user_repo.get_by_id(user_id)
    
    async def update_user(self, user_id: UUID | str, **updates) -> Optional[UserProfile]:
        """Update user fields."""
        return await self._user_repo.update(user_id, **updates)
    
    async def delete_user(self, user_id: UUID | str) -> bool:
        """Delete user and cascade."""
        return await self._user_repo.delete(user_id)
    
    async def list_users(self) -> list[UserProfile]:
        """List all users."""
        return await self._user_repo.list_all()
    
    # ============ Plan Operations ============
    
    async def add_plan(self, plan: CarbonCyclePlan) -> CarbonCyclePlan:
        """Add a new plan."""
        # Deactivate existing plans for this user
        if plan.is_active:
            await self._plan_repo.deactivate_user_plans(plan.user_id)
        return await self._plan_repo.create(plan)
    
    async def get_plan(self, plan_id: UUID | str) -> Optional[CarbonCyclePlan]:
        """Get plan by ID."""
        return await self._plan_repo.get_by_id(plan_id)
    
    async def get_user_plans(self, user_id: UUID | str) -> list[CarbonCyclePlan]:
        """Get all plans for a user."""
        return await self._plan_repo.get_user_plans(user_id)
    
    async def get_active_plan(self, user_id: UUID | str) -> Optional[CarbonCyclePlan]:
        """Get active plan for a user."""
        return await self._plan_repo.get_active_plan(user_id)
    
    async def update_plan(self, plan_id: UUID | str, **updates) -> Optional[CarbonCyclePlan]:
        """Update plan fields."""
        return await self._plan_repo.update(plan_id, **updates)
    
    async def delete_plan(self, plan_id: UUID | str) -> bool:
        """Delete a plan."""
        return await self._plan_repo.delete(plan_id)
    
    # ============ Log Operations ============
    
    async def add_log(self, log: DietLog) -> DietLog:
        """Add a new log."""
        return await self._log_repo.create(log)
    
    async def get_log(self, log_id: UUID | str) -> Optional[DietLog]:
        """Get log by ID."""
        return await self._log_repo.get_by_id(log_id)
    
    async def get_user_logs(self, user_id: UUID | str, limit: int = 7) -> list[DietLog]:
        """Get recent logs for a user."""
        return await self._log_repo.get_user_logs(user_id, limit=limit)
    
    async def get_log_by_date(self, user_id: UUID | str, log_date: date) -> Optional[DietLog]:
        """Get log for a specific date."""
        return await self._log_repo.get_by_date(user_id, log_date)
    
    async def update_log(self, log_id: UUID | str, **updates) -> Optional[DietLog]:
        """Update log fields."""
        return await self._log_repo.update(log_id, **updates)
    
    async def delete_log(self, log_id: UUID | str) -> bool:
        """Delete a log."""
        return await self._log_repo.delete(log_id)
    
    async def get_user_log_stats(self, user_id: UUID | str, days: int = 7) -> dict:
        """Get log statistics for a user."""
        return await self._log_repo.get_stats(user_id, days=days)
