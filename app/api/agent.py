from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import run_agent
from app.core.database import get_db
from app.db.db_storage import DatabaseStorage
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AgentTriggerRequest(BaseModel):
    """Request to trigger agent run."""
    user_id: str
    trigger: str = "manual"


class AgentRunResponse(BaseModel):
    """Response from agent run."""
    run_id: str
    status: str
    message: str


class AgentResultResponse(BaseModel):
    """Detailed agent result."""
    run_id: str
    status: str
    planner_output: Optional[dict[str, Any]] = None
    reflection: Optional[dict[str, Any]] = None
    adjustment: Optional[dict[str, Any]] = None
    reflection_summary: Optional[str] = None
    motivation: Optional[str] = None
    error: Optional[str] = None


# Store for async results
_agent_results: dict[str, dict[str, Any]] = {}


def _build_user_context(user) -> dict[str, Any]:
    """Build user context from UserProfile."""
    return {
        "user_id": str(user.id),
        "name": user.name,
        "gender": user.gender.value if hasattr(user.gender, 'value') else user.gender,
        "age": user.calculate_age() if hasattr(user, 'calculate_age') else 30,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "target_weight_kg": getattr(user, 'target_weight_kg', user.weight_kg - 5) or user.weight_kg - 5,
        "goal": user.goal.value if hasattr(user.goal, 'value') else user.goal,
        "activity_level": user.activity_level.value if hasattr(user.activity_level, 'value') else user.activity_level,
        "training_days": getattr(user, 'training_days_per_week', 4),
        "tdee": user.calculate_tdee() if hasattr(user, 'calculate_tdee') else 2000,
        "dietary_preferences": ", ".join(getattr(user, 'dietary_preferences', [])) or "无特殊限制",
    }


def _build_plan_context(plan) -> dict[str, Any]:
    """Build plan context from CarbonCyclePlan."""
    if not plan:
        return {}
    
    # Get today's plan day if available
    from datetime import date
    today = date.today()
    
    today_day = None
    for day in plan.days:
        if day.date == today:
            today_day = day
            break
    
    if today_day:
        return {
            "plan_id": str(plan.id),
            "start_date": plan.start_date.isoformat(),
            "current_day": (today - plan.start_date).days + 1,
            "day_type": today_day.day_type.value if hasattr(today_day.day_type, 'value') else today_day.day_type,
            "target_calories": today_day.target_calories,
            "target_protein": today_day.macros.protein_g,
            "target_carbs": today_day.macros.carbs_g,
            "target_fat": today_day.macros.fat_g,
            "cycle_length": len(plan.days),
        }
    
    return {
        "plan_id": str(plan.id),
        "start_date": plan.start_date.isoformat(),
        "target_calories": plan.average_daily_calories,
        "cycle_length": len(plan.days),
    }


def _build_logs_context(logs) -> list[dict[str, Any]]:
    """Build logs context from DietLog list."""
    return [
        {
            "date": log.date.isoformat(),
            "actual_calories": log.total_calories or 0,
            "actual_protein": log.total_protein or 0,
            "actual_carbs": log.total_carbs or 0,
            "actual_fat": log.total_fat or 0,
            "training_completed": log.training_completed or False,
            "meal_count": len(log.meals) if log.meals else 0,
        }
        for log in logs
    ]


@router.post("/run", response_model=AgentResultResponse)
async def run_agent_sync(request: AgentTriggerRequest, db: AsyncSession = Depends(get_db)) -> AgentResultResponse:
    """
    Run agent synchronously with real user data.
    同步运行 Agent，使用真实用户数据
    """
    storage = DatabaseStorage(db)
    
    # Get user
    user = await storage.get_user(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get active plan
    plan = await storage.get_active_plan(request.user_id)
    
    # Get recent logs
    logs = await storage.get_user_logs(request.user_id, limit=7)
    
    # Build contexts
    user_context = _build_user_context(user)
    plan_context = _build_plan_context(plan)
    logs_context = _build_logs_context(logs)
    
    logger.info(f"Running agent for user {request.user_id} with {len(logs)} logs")
    
    result = await run_agent(
        user_id=str(request.user_id),
        trigger=request.trigger,
        user_context=user_context,
        plan_context=plan_context,
        logs=logs_context,
    )
    
    return AgentResultResponse(
        run_id=result.get("run_id", ""),
        status=result.get("status", "unknown"),
        planner_output=result.get("planner_output"),
        reflection=result.get("reflection"),
        adjustment=result.get("adjustment"),
        reflection_summary=result.get("reflection_summary"),
        motivation=result.get("motivation"),
        error=result.get("error"),
    )


@router.post("/trigger", response_model=AgentRunResponse)
async def trigger_agent_async(
    request: AgentTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> AgentRunResponse:
    """
    Trigger agent run asynchronously.
    异步触发 Agent 运行
    """
    storage = DatabaseStorage(db)
    
    # Verify user exists
    if not await storage.get_user(request.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    run_id = str(uuid4())
    _agent_results[run_id] = {"status": "running"}
    
    async def run_in_background():
        # Note: Background tasks need their own DB session if they run after the request finishes.
        # But for now, we'll try using the injected session or a new one.
        # It's safer to use a new session in background tasks.
        from app.core.database import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            try:
                bg_storage = DatabaseStorage(session)
                user = await bg_storage.get_user(request.user_id)
                plan = await bg_storage.get_active_plan(request.user_id)
                logs = await bg_storage.get_user_logs(request.user_id, limit=7)
                
                result = await run_agent(
                    user_id=str(request.user_id),
                    trigger=request.trigger,
                    user_context=_build_user_context(user),
                    plan_context=_build_plan_context(plan),
                    logs=_build_logs_context(logs),
                )
                _agent_results[run_id] = result
            except Exception as e:
                logger.error(f"Background agent run failed: {e}")
                _agent_results[run_id] = {"status": "error", "error": str(e)}
    
    background_tasks.add_task(run_in_background)
    
    return AgentRunResponse(
        run_id=run_id,
        status="running",
        message="Agent run started",
    )


@router.get("/status/{run_id}", response_model=AgentResultResponse)
async def get_agent_status(run_id: str) -> AgentResultResponse:
    """
    Get status of an agent run.
    获取 Agent 运行状态
    """
    if run_id not in _agent_results:
        return AgentResultResponse(run_id=run_id, status="not_found")
    
    result = _agent_results[run_id]
    return AgentResultResponse(
        run_id=run_id,
        status=result.get("status", "unknown"),
        planner_output=result.get("planner_output"),
        reflection=result.get("reflection"),
        adjustment=result.get("adjustment"),
        reflection_summary=result.get("reflection_summary"),
        motivation=result.get("motivation"),
        error=result.get("error"),
    )
