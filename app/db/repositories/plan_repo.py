"""
Plan repository.
计划仓库

Handles database operations for carbon cycle plans.
处理碳循环计划的数据库操作
"""

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PlanModel, DayPlanModel
from app.models.plan import CarbonCyclePlan, DayPlan, MacroNutrients, DayType


class PlanRepository:
    """Repository for plan database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, plan: CarbonCyclePlan) -> CarbonCyclePlan:
        """Create a new plan with days."""
        # Create plan
        db_plan = PlanModel(
            id=str(plan.id),
            user_id=str(plan.user_id),
            name=plan.name,
            start_date=plan.start_date,
            end_date=plan.end_date,
            cycle_length_days=plan.cycle_length_days,
            base_calories=plan.base_calories,
            goal_deficit=plan.goal_deficit,
            is_active=plan.is_active,
        )
        self.session.add(db_plan)
        
        # Create day plans
        for day in plan.days:
            db_day = DayPlanModel(
                plan_id=str(plan.id),
                date=day.date,
                day_type=day.day_type.value if hasattr(day.day_type, 'value') else day.day_type,
                protein_g=day.macros.protein_g,
                carbs_g=day.macros.carbs_g,
                fat_g=day.macros.fat_g,
                fiber_g=day.macros.fiber_g,
                training_scheduled=day.training_scheduled,
                training_type=day.training_type,
                notes=day.notes,
            )
            self.session.add(db_day)
        
        await self.session.flush()
        return plan
    
    async def get_by_id(self, plan_id: UUID | str) -> Optional[CarbonCyclePlan]:
        """Get plan by ID with days."""
        result = await self.session.execute(
            select(PlanModel)
            .options(selectinload(PlanModel.days))
            .where(PlanModel.id == str(plan_id))
        )
        db_plan = result.scalar_one_or_none()
        return self._to_pydantic(db_plan) if db_plan else None
    
    async def get_user_plans(self, user_id: UUID | str) -> list[CarbonCyclePlan]:
        """Get all plans for a user."""
        result = await self.session.execute(
            select(PlanModel)
            .options(selectinload(PlanModel.days))
            .where(PlanModel.user_id == str(user_id))
        )
        return [self._to_pydantic(p) for p in result.scalars().all()]
    
    async def get_active_plan(self, user_id: UUID | str) -> Optional[CarbonCyclePlan]:
        """Get active plan for a user."""
        result = await self.session.execute(
            select(PlanModel)
            .options(selectinload(PlanModel.days))
            .where(PlanModel.user_id == str(user_id), PlanModel.is_active == True)
        )
        db_plan = result.scalar_one_or_none()
        return self._to_pydantic(db_plan) if db_plan else None
    
    async def deactivate_user_plans(self, user_id: UUID | str) -> None:
        """Deactivate all plans for a user."""
        await self.session.execute(
            update(PlanModel)
            .where(PlanModel.user_id == str(user_id))
            .values(is_active=False)
        )
    
    async def delete(self, plan_id: UUID | str) -> bool:
        """Delete a plan."""
        result = await self.session.execute(
            select(PlanModel).where(PlanModel.id == str(plan_id))
        )
        db_plan = result.scalar_one_or_none()
        if not db_plan:
            return False
        
        await self.session.delete(db_plan)
        await self.session.flush()
        return True
    
    async def update(self, plan_id: UUID | str, **updates) -> Optional[CarbonCyclePlan]:
        """Update a plan and its days."""
        result = await self.session.execute(
            select(PlanModel).options(selectinload(PlanModel.days)).where(PlanModel.id == str(plan_id))
        )
        db_plan = result.scalar_one_or_none()
        if not db_plan:
            return None
        
        # Handle days separately
        if "days" in updates:
            new_days = updates.pop("days")
            # Delete old days
            from sqlalchemy import delete
            await self.session.execute(delete(DayPlanModel).where(DayPlanModel.plan_id == str(plan_id)))
            # Add new days
            for i, day in enumerate(new_days):
                # day can be a Pydantic model or a dict
                day_data = day.model_dump() if hasattr(day, "model_dump") else day
                db_day = DayPlanModel(
                    plan_id=str(plan_id),
                    date=day_data["date"],
                    day_type=day_data["day_type"].value if hasattr(day_data["day_type"], "value") else day_data["day_type"],
                    protein_g=day_data["macros"]["protein_g"] if isinstance(day_data["macros"], dict) else day_data["macros"].protein_g,
                    carbs_g=day_data["macros"]["carbs_g"] if isinstance(day_data["macros"], dict) else day_data["macros"].carbs_g,
                    fat_g=day_data["macros"]["fat_g"] if isinstance(day_data["macros"], dict) else day_data["macros"].fat_g,
                    fiber_g=day_data["macros"]["fiber_g"] if isinstance(day_data["macros"], dict) else day_data["macros"].fiber_g,
                    training_scheduled=day_data["training_scheduled"],
                    training_type=day_data["training_type"],
                    notes=day_data.get("notes"),
                )
                self.session.add(db_day)

        # Update other fields
        for key, value in updates.items():
            if hasattr(db_plan, key):
                setattr(db_plan, key, value)
        
        await self.session.flush()
        # Refresh to get the new days
        await self.session.refresh(db_plan)
        return self._to_pydantic(db_plan)

    def _to_pydantic(self, db_plan: PlanModel) -> CarbonCyclePlan:
        """Convert DB model to Pydantic."""
        days = [
            DayPlan(
                date=d.date,
                day_type=DayType(d.day_type),
                macros=MacroNutrients(
                    protein_g=d.protein_g,
                    carbs_g=d.carbs_g,
                    fat_g=d.fat_g,
                    fiber_g=d.fiber_g,
                ),
                training_scheduled=d.training_scheduled,
                training_type=d.training_type,
                notes=d.notes,
            )
            for d in sorted(db_plan.days, key=lambda x: x.date)
        ]
        
        return CarbonCyclePlan(
            id=db_plan.id,
            user_id=db_plan.user_id,
            name=db_plan.name,
            start_date=db_plan.start_date,
            end_date=db_plan.end_date,
            cycle_length_days=db_plan.cycle_length_days,
            days=days,
            base_calories=db_plan.base_calories,
            goal_deficit=db_plan.goal_deficit,
            is_active=db_plan.is_active,
            created_at=db_plan.created_at,
            updated_at=db_plan.updated_at,
        )
