"""
Proactive agent jobs.
主动式 Agent 任务
"""

from app.agent import run_agent
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.db.db_storage import DatabaseStorage
from app.services.agent_observability import AgentObservabilityService

logger = get_logger(__name__)


async def run_daily_agent_checkins() -> None:
    """Run a lightweight daily agent check-in for every user."""
    async with get_db_context() as db:
        storage = DatabaseStorage(db)
        observability = AgentObservabilityService(db)
        users = await storage.list_users()
        logger.info(f"Running proactive daily agent check-ins for {len(users)} users")

        for user in users:
            try:
                user_id = str(user.id)
                plan = await storage.get_active_plan(user_id)
                logs = await storage.get_user_logs(user_id, limit=7)
                memory_context = await observability.build_memory_context(user_id)
                evaluation_summary = await observability.get_evaluation_summary()

                result = await run_agent(
                    user_id=user_id,
                    trigger="daily_checkin",
                    user_context={
                        "user_id": user_id,
                        "name": user.name,
                        "gender": user.gender.value if hasattr(user.gender, "value") else user.gender,
                        "age": user.calculate_age(),
                        "height_cm": user.height_cm,
                        "weight_kg": user.weight_kg,
                        "target_weight_kg": user.target_weight_kg or user.weight_kg,
                        "goal": user.goal.value if hasattr(user.goal, "value") else user.goal,
                        "activity_level": user.activity_level.value if hasattr(user.activity_level, "value") else user.activity_level,
                        "training_days": user.training_days_per_week,
                        "tdee": user.calculate_tdee(),
                        "dietary_preferences": ", ".join(user.dietary_preferences or []) or "无特殊限制",
                    },
                    plan_context={
                        "plan_id": str(plan.id) if plan else "",
                        "start_date": plan.start_date.isoformat() if plan else "",
                        "cycle_length": len(plan.days) if plan else 7,
                    },
                    logs=[
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
                    ],
                    db_session=db,
                    memory_context=memory_context,
                    evaluation_summary=evaluation_summary,
                )
                await observability.persist_run(user_id, "daily_checkin", result)
            except Exception as exc:
                logger.warning(f"Daily agent check-in failed for user {getattr(user, 'id', 'unknown')}: {exc}")
