"""
Weight log repository.
体重记录仓库

Handles database operations for weight tracking logs.
处理体重记录的数据库操作
"""

from datetime import date
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WeightLogModel
from app.models.log import WeightLog


class WeightRepository:
    """Repository for weight log database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, weight_log: WeightLog) -> WeightLog:
        """Create a new weight log."""
        db_log = WeightLogModel(
            id=str(weight_log.id),
            user_id=str(weight_log.user_id),
            date=weight_log.date,
            weight_kg=weight_log.weight_kg,
            body_fat_pct=weight_log.body_fat_pct,
            notes=weight_log.notes,
        )
        self.session.add(db_log)
        await self.session.flush()
        return weight_log
    
    async def get_by_id(self, log_id: Union[UUID, str]) -> Optional[WeightLog]:
        """Get weight log by ID."""
        result = await self.session.execute(
            select(WeightLogModel).where(WeightLogModel.id == str(log_id))
        )
        db_log = result.scalar_one_or_none()
        return self._to_pydantic(db_log) if db_log else None
    
    async def get_user_weights(
        self, user_id: Union[UUID, str], limit: int = 30
    ) -> list[WeightLog]:
        """Get recent weight logs for a user, ordered by date descending."""
        result = await self.session.execute(
            select(WeightLogModel)
            .where(WeightLogModel.user_id == str(user_id))
            .order_by(WeightLogModel.date.desc())
            .limit(limit)
        )
        return [self._to_pydantic(w) for w in result.scalars().all()]
    
    async def get_by_date_range(
        self,
        user_id: Union[UUID, str],
        start_date: date,
        end_date: date,
    ) -> list[WeightLog]:
        """Get weight logs within a date range, ordered by date ascending."""
        result = await self.session.execute(
            select(WeightLogModel)
            .where(
                WeightLogModel.user_id == str(user_id),
                WeightLogModel.date >= start_date,
                WeightLogModel.date <= end_date,
            )
            .order_by(WeightLogModel.date.asc())
        )
        return [self._to_pydantic(w) for w in result.scalars().all()]
    
    async def get_latest(self, user_id: Union[UUID, str]) -> Optional[WeightLog]:
        """Get the most recent weight log for a user."""
        result = await self.session.execute(
            select(WeightLogModel)
            .where(WeightLogModel.user_id == str(user_id))
            .order_by(WeightLogModel.date.desc())
            .limit(1)
        )
        db_log = result.scalar_one_or_none()
        return self._to_pydantic(db_log) if db_log else None
    
    async def delete(self, log_id: Union[UUID, str]) -> bool:
        """Delete a weight log."""
        result = await self.session.execute(
            select(WeightLogModel).where(WeightLogModel.id == str(log_id))
        )
        db_log = result.scalar_one_or_none()
        if not db_log:
            return False
        await self.session.delete(db_log)
        await self.session.flush()
        return True
    
    def _to_pydantic(self, db_log: WeightLogModel) -> WeightLog:
        """Convert DB model to Pydantic."""
        return WeightLog(
            id=db_log.id,
            user_id=db_log.user_id,
            date=db_log.date,
            weight_kg=db_log.weight_kg,
            body_fat_pct=db_log.body_fat_pct,
            notes=db_log.notes,
            created_at=db_log.created_at,
        )
