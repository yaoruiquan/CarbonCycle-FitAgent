"""
Log repository.
日志仓库

Handles database operations for diet logs.
处理饮食日志的数据库操作
"""

from datetime import date, time
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LogModel, MealModel, FoodItemModel
from app.models.log import DietLog, MealLog, FoodItem, MealType


class LogRepository:
    """Repository for log database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, log: DietLog) -> DietLog:
        """Create a new log with meals and food items."""
        # Create log
        db_log = LogModel(
            id=str(log.id),
            user_id=str(log.user_id),
            plan_id=str(log.plan_id) if log.plan_id else None,
            date=log.date,
            water_ml=log.water_ml,
            training_completed=log.training_completed,
            training_notes=log.training_notes,
            mood=log.mood,
            energy_level=log.energy_level,
            sleep_hours=log.sleep_hours,
        )
        self.session.add(db_log)
        
        # Create meals and items
        for meal in log.meals:
            db_meal = MealModel(
                log_id=str(log.id),
                meal_type=meal.meal_type.value if hasattr(meal.meal_type, 'value') else meal.meal_type,
                time=meal.time,
                notes=meal.notes,
            )
            self.session.add(db_meal)
            await self.session.flush()  # Get meal ID
            
            for item in meal.items:
                db_item = FoodItemModel(
                    meal_id=db_meal.id,
                    name=item.name,
                    quantity=item.quantity,
                    unit=item.unit,
                    calories=item.calories,
                    protein_g=item.protein_g,
                    carbs_g=item.carbs_g,
                    fat_g=item.fat_g,
                    fiber_g=item.fiber_g,
                )
                self.session.add(db_item)
        
        await self.session.flush()
        return log
    
    async def get_by_id(self, log_id: UUID | str) -> Optional[DietLog]:
        """Get log by ID with meals."""
        result = await self.session.execute(
            select(LogModel)
            .options(
                selectinload(LogModel.meals).selectinload(MealModel.items)
            )
            .where(LogModel.id == str(log_id))
        )
        db_log = result.scalar_one_or_none()
        return self._to_pydantic(db_log) if db_log else None
    
    async def get_user_logs(self, user_id: UUID | str, limit: int = 7) -> list[DietLog]:
        """Get recent logs for a user."""
        result = await self.session.execute(
            select(LogModel)
            .options(
                selectinload(LogModel.meals).selectinload(MealModel.items)
            )
            .where(LogModel.user_id == str(user_id))
            .order_by(LogModel.date.desc())
            .limit(limit)
        )
        return [self._to_pydantic(l) for l in result.scalars().all()]
    
    async def get_by_date(self, user_id: UUID | str, log_date: date) -> Optional[DietLog]:
        """Get log for a specific date."""
        result = await self.session.execute(
            select(LogModel)
            .options(
                selectinload(LogModel.meals).selectinload(MealModel.items)
            )
            .where(LogModel.user_id == str(user_id), LogModel.date == log_date)
        )
        db_log = result.scalar_one_or_none()
        return self._to_pydantic(db_log) if db_log else None
    
    async def update(self, log_id: UUID | str, **updates) -> Optional[DietLog]:
        """Update log fields."""
        result = await self.session.execute(
            select(LogModel).where(LogModel.id == str(log_id))
        )
        db_log = result.scalar_one_or_none()
        if not db_log:
            return None
        
        for field, value in updates.items():
            if hasattr(db_log, field) and value is not None:
                setattr(db_log, field, value)
        
        await self.session.flush()
        return await self.get_by_id(log_id)
    
    async def delete(self, log_id: UUID | str) -> bool:
        """Delete a log."""
        result = await self.session.execute(
            select(LogModel).where(LogModel.id == str(log_id))
        )
        db_log = result.scalar_one_or_none()
        if not db_log:
            return False
        
        await self.session.delete(db_log)
        await self.session.flush()
        return True
    
    async def get_stats(self, user_id: UUID | str, days: int = 7) -> dict:
        """Get log statistics for a user."""
        logs = await self.get_user_logs(user_id, limit=days)
        
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
    
    def _to_pydantic(self, db_log: LogModel) -> DietLog:
        """Convert DB model to Pydantic."""
        meals = [
            MealLog(
                meal_type=MealType(m.meal_type),
                time=m.time,
                items=[
                    FoodItem(
                        name=i.name,
                        quantity=i.quantity,
                        unit=i.unit,
                        calories=i.calories,
                        protein_g=i.protein_g,
                        carbs_g=i.carbs_g,
                        fat_g=i.fat_g,
                        fiber_g=i.fiber_g,
                    )
                    for i in m.items
                ],
                notes=m.notes,
            )
            for m in db_log.meals
        ]
        
        return DietLog(
            id=db_log.id,
            user_id=db_log.user_id,
            plan_id=db_log.plan_id,
            date=db_log.date,
            meals=meals,
            water_ml=db_log.water_ml,
            training_completed=db_log.training_completed,
            training_notes=db_log.training_notes,
            mood=db_log.mood,
            energy_level=db_log.energy_level,
            sleep_hours=db_log.sleep_hours,
            created_at=db_log.created_at,
            updated_at=db_log.updated_at,
        )
