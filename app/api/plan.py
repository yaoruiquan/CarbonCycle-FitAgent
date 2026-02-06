from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.db_storage import DatabaseStorage
from app.models.plan import CarbonCyclePlan, PlanCreate, PlanSummary, PlanUpdate
from app.services.carbon_strategy import CarbonStrategyService

router = APIRouter()

strategy_service = CarbonStrategyService()


@router.post("/", response_model=CarbonCyclePlan, status_code=status.HTTP_201_CREATED)
async def create_plan(plan_data: PlanCreate, db: AsyncSession = Depends(get_db)) -> CarbonCyclePlan:
    """
    Create a new carbon cycle plan with Agent enhancement.
    创建新的碳循环计划（使用 Agent 增强）
    
    Calls Agent's Planner node for personalized suggestions.
    """
    storage = DatabaseStorage(db)
    
    user = await storage.get_user(plan_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use Agent-enhanced plan generation
    new_plan = await strategy_service.generate_plan_with_agent(user, plan_data)
    return await storage.add_plan(new_plan)


@router.get("/{plan_id}", response_model=CarbonCyclePlan)
async def get_plan(plan_id: str, db: AsyncSession = Depends(get_db)) -> CarbonCyclePlan:
    """
    Get plan by ID.
    根据 ID 获取计划
    """
    storage = DatabaseStorage(db)
    plan = await storage.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.patch("/{plan_id}", response_model=CarbonCyclePlan)
async def update_plan(plan_id: str, plan_update: PlanUpdate, db: AsyncSession = Depends(get_db)) -> CarbonCyclePlan:
    """
    Update a plan.
    更新计划 (支持更新 days 列表)
    """
    storage = DatabaseStorage(db)
    
    # Extract updates from the Pydantic model
    updates = plan_update.model_dump(exclude_unset=True)
    
    updated_plan = await storage.update_plan(plan_id, **updates)
    if not updated_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    return updated_plan


@router.get("/user/{user_id}", response_model=list[PlanSummary])
async def get_user_plans(user_id: str, db: AsyncSession = Depends(get_db)) -> list[PlanSummary]:
    """
    Get all plans for a user.
    获取用户的所有计划
    """
    storage = DatabaseStorage(db)
    if not await storage.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    user_plans = await storage.get_user_plans(user_id)
    return [
        PlanSummary(
            id=p.id,
            name=p.name,
            start_date=p.start_date,
            end_date=p.end_date,
            is_active=p.is_active,
            average_daily_calories=p.average_daily_calories,
            day_type_counts={k.value: v for k, v in p.count_day_types().items()},
        )
        for p in user_plans
    ]


@router.get("/user/{user_id}/active", response_model=CarbonCyclePlan)
async def get_active_plan(user_id: str, db: AsyncSession = Depends(get_db)) -> CarbonCyclePlan:
    """
    Get active plan for a user.
    获取用户的当前活跃计划
    """
    storage = DatabaseStorage(db)
    plan = await storage.get_active_plan(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found")
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a plan.
    删除计划
    """
    storage = DatabaseStorage(db)
    if not await storage.delete_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")


@router.patch("/{plan_id}/deactivate", response_model=CarbonCyclePlan)
async def deactivate_plan(plan_id: str, db: AsyncSession = Depends(get_db)) -> CarbonCyclePlan:
    """
    Deactivate a plan.
    停用计划
    """
    storage = DatabaseStorage(db)
    plan = await storage.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan.is_active = False
    # Persist change
    return plan


@router.post("/{plan_id}/days/{day_date}/regenerate")
async def regenerate_day(
    plan_id: str,
    day_date: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate training and diet plan for a specific day using LLM.
    使用 LLM 重新生成某一天的训练和饮食计划
    """
    from app.services.plan_enrichment import PlanEnrichmentService
    
    storage = DatabaseStorage(db)
    plan = await storage.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    user = await storage.get_user(str(plan.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Find the target day
    target_day = None
    target_index = -1
    for i, day in enumerate(plan.days):
        if str(day.date) == day_date:
            target_day = day
            target_index = i
            break
    
    if target_day is None:
        raise HTTPException(status_code=404, detail="Day not found in plan")
    
    # Use enrichment service to regenerate this day
    enrichment_service = PlanEnrichmentService()
    await enrichment_service._enrich_day(target_day, user)
    
    # Update the plan in storage
    plan.days[target_index] = target_day
    await storage.update_plan(plan_id, days=plan.days)
    
    # Return the regenerated day as a dict
    return {
        "date": str(target_day.date),
        "day_type": target_day.day_type.value if hasattr(target_day.day_type, 'value') else str(target_day.day_type),
        "target_calories": target_day.target_calories,
        "macros": {
            "protein_g": target_day.macros.protein_g,
            "carbs_g": target_day.macros.carbs_g,
            "fat_g": target_day.macros.fat_g,
            "fiber_g": target_day.macros.fiber_g,
        },
        "training_scheduled": target_day.training_scheduled,
        "training_type": target_day.training_type,
        "notes": target_day.notes,
    }

