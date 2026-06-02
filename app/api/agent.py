from datetime import date
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent import run_agent
from app.core.database import get_db
from app.db.db_storage import DatabaseStorage
from app.db.models import AgentMissionModel, PlanModel
from app.core.logging import get_logger
from app.services.agent_observability import AgentObservabilityService

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
    latency_ms: Optional[int] = None
    planner_output: Optional[dict[str, Any]] = None
    actor_output: Optional[dict[str, Any]] = None
    reflection: Optional[dict[str, Any]] = None
    adjustment: Optional[dict[str, Any]] = None
    reflection_summary: Optional[str] = None
    motivation: Optional[str] = None
    trends: Optional[dict[str, Any]] = None
    trace: list[dict[str, Any]] = []
    tool_trace: list[dict[str, Any]] = []
    plan_diff: list[dict[str, Any]] = []
    safety_warnings: list[dict[str, Any]] = []
    missions: list[dict[str, Any]] = []
    action_cards: list[dict[str, Any]] = []
    memory_context: dict[str, Any] = {}
    evaluation_summary: dict[str, Any] = {}
    error: Optional[str] = None


class AgentActionRequest(BaseModel):
    """Request to execute an action card."""
    user_id: str
    action_type: str
    data: dict[str, Any] = {}


class AgentActionResponse(BaseModel):
    """Result from executing an action card."""
    status: str
    message: str
    result: dict[str, Any] = {}


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


def _result_response(result: dict[str, Any]) -> AgentResultResponse:
    """Build API response from an agent result dict."""
    return AgentResultResponse(
        run_id=result.get("run_id", ""),
        status=result.get("status", "unknown"),
        latency_ms=result.get("latency_ms"),
        planner_output=result.get("planner_output"),
        actor_output=result.get("actor_output"),
        reflection=result.get("reflection"),
        adjustment=result.get("adjustment"),
        reflection_summary=result.get("reflection_summary"),
        motivation=result.get("motivation"),
        trends=result.get("trends"),
        trace=result.get("trace") or [],
        tool_trace=result.get("tool_trace") or [],
        plan_diff=result.get("plan_diff") or [],
        safety_warnings=result.get("safety_warnings") or [],
        missions=result.get("missions") or [],
        action_cards=result.get("action_cards") or [],
        memory_context=result.get("memory_context") or {},
        evaluation_summary=result.get("evaluation_summary") or {},
        error=result.get("error"),
    )


@router.post("/run", response_model=AgentResultResponse)
async def run_agent_sync(request: AgentTriggerRequest, db: AsyncSession = Depends(get_db)) -> AgentResultResponse:
    """
    Run agent synchronously with real user data.
    同步运行 Agent，使用真实用户数据
    """
    storage = DatabaseStorage(db)
    observability = AgentObservabilityService(db)
    
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
    memory_context = await observability.build_memory_context(str(request.user_id))
    evaluation_summary = await observability.get_evaluation_summary()
    
    logger.info(f"Running agent for user {request.user_id} with {len(logs)} logs")
    
    result = await run_agent(
        user_id=str(request.user_id),
        trigger=request.trigger,
        user_context=user_context,
        plan_context=plan_context,
        logs=logs_context,
        db_session=db,
        memory_context=memory_context,
        evaluation_summary=evaluation_summary,
    )
    persisted = await observability.persist_run(str(request.user_id), request.trigger, result)
    return _result_response(persisted)


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
                observability = AgentObservabilityService(session)
                memory_context = await observability.build_memory_context(str(request.user_id))
                evaluation_summary = await observability.get_evaluation_summary()
                
                result = await run_agent(
                    user_id=str(request.user_id),
                    trigger=request.trigger,
                    user_context=_build_user_context(user),
                    plan_context=_build_plan_context(plan),
                    logs=_build_logs_context(logs),
                    db_session=session,
                    memory_context=memory_context,
                    evaluation_summary=evaluation_summary,
                )
                result["run_id"] = run_id
                persisted = await observability.persist_run(str(request.user_id), request.trigger, result)
                await session.commit()
                _agent_results[run_id] = persisted
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
async def get_agent_status(run_id: str, db: AsyncSession = Depends(get_db)) -> AgentResultResponse:
    """
    Get status of an agent run.
    获取 Agent 运行状态
    """
    observability = AgentObservabilityService(db)
    persisted = await observability.get_run(run_id)
    if persisted:
        return _result_response(persisted)

    if run_id not in _agent_results:
        return AgentResultResponse(run_id=run_id, status="not_found")
    
    result = _agent_results[run_id]
    return _result_response({"run_id": run_id, **result})


@router.get("/runs/{user_id}", response_model=list[AgentResultResponse])
async def list_agent_runs(
    user_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> list[AgentResultResponse]:
    """List recent persisted agent runs for a user."""
    observability = AgentObservabilityService(db)
    runs = await observability.list_runs(user_id, limit=limit)
    return [_result_response(run) for run in runs]


@router.get("/missions/{user_id}")
async def list_agent_missions(
    user_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List goal-oriented agent missions."""
    observability = AgentObservabilityService(db)
    return {"missions": await observability.list_missions(user_id, limit=limit)}


@router.get("/evaluations/summary")
async def get_evaluation_summary(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return local agent evaluation artifacts summary."""
    observability = AgentObservabilityService(db)
    return await observability.get_evaluation_summary()


@router.post("/actions/execute", response_model=AgentActionResponse)
async def execute_agent_action(
    request: AgentActionRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentActionResponse:
    """
    Execute an action card after user confirmation.
    执行用户确认后的 Agent 动作卡片
    """
    if request.action_type == "create_missions":
        missions = request.data.get("missions") or []
        created = 0
        activated = 0
        for mission in missions:
            mission_id = mission.get("id") or str(uuid4())
            existing = await db.execute(
                select(AgentMissionModel).where(AgentMissionModel.id == mission_id)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.status = "pending"
                activated += 1
                continue
            db.add(
                AgentMissionModel(
                    id=mission_id,
                    user_id=request.user_id,
                    title=mission.get("title", "Agent 任务"),
                    description=mission.get("description"),
                    status="pending",
                    due_date=date.fromisoformat(mission["due_date"]) if mission.get("due_date") else None,
                    next_action=mission.get("next_action"),
                    evidence=mission.get("evidence") or [],
                )
            )
            created += 1
        await db.flush()
        return AgentActionResponse(
            status="success",
            message=f"已激活 {created + activated} 个 Agent 跟踪任务",
            result={"created": created, "activated": activated},
        )

    if request.action_type == "apply_plan_diff":
        plan_diff = request.data.get("plan_diff") or []
        result = await db.execute(
            select(PlanModel)
            .where(PlanModel.user_id == request.user_id, PlanModel.is_active == True)
            .options(selectinload(PlanModel.days))
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Active plan not found")

        today = date.today()
        day = next((item for item in plan.days if item.date >= today), None)
        if not day:
            raise HTTPException(status_code=404, detail="No upcoming plan day found")

        applied: list[dict[str, Any]] = []
        for item in plan_diff:
            field = item.get("field")
            after = item.get("after")
            if after is None:
                continue
            if field == "target_protein":
                day.protein_g = float(after)
            elif field == "target_carbs":
                day.carbs_g = float(after)
            elif field == "target_fat":
                day.fat_g = float(after)
            elif field == "target_calories":
                day.notes = (day.notes or "") + f"\nAgent 建议目标热量调整为 {after} kcal。"
            else:
                continue
            applied.append(item)

        await db.flush()
        return AgentActionResponse(
            status="success",
            message=f"已应用 {len(applied)} 项计划调整",
            result={"applied": applied, "day_date": day.date.isoformat()},
        )

    if request.action_type == "open_agent_trace":
        return AgentActionResponse(
            status="success",
            message="该动作由前端打开 Agent 轨迹面板，无需后端变更。",
            result={"panel": "trace"},
        )

    raise HTTPException(status_code=400, detail=f"Unsupported action type: {request.action_type}")
