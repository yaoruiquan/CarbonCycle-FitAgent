"""
Agent observability and persistence services.
Agent 可观察性与持久化服务
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AgentMissionModel,
    AgentRunModel,
    AgentStepModel,
    LogModel,
    MealModel,
    FoodItemModel,
    UserMemoryModel,
)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _model_to_dict(run: AgentRunModel) -> dict[str, Any]:
    """Serialize an AgentRunModel and related steps."""
    return {
        "run_id": run.id,
        "user_id": run.user_id,
        "trigger": run.trigger,
        "status": run.status,
        "latency_ms": run.latency_ms,
        "planner_output": run.planner_output or {},
        "actor_output": run.actor_output or {},
        "reflection": run.reflection or {},
        "adjustment": run.adjustment or {},
        "reflection_summary": run.reflection_summary,
        "motivation": run.motivation,
        "trends": run.trends or {},
        "trace": [
            {
                "node": step.node,
                "title": step.title,
                "status": step.status,
                "decision": step.decision,
                "reasoning": step.reasoning,
                "input_summary": step.input_summary or {},
                "output_summary": step.output_summary or {},
                "confidence": step.confidence,
                "duration_ms": step.duration_ms,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            }
            for step in run.steps
        ],
        "tool_trace": run.tool_trace or [],
        "plan_diff": run.plan_diff or [],
        "safety_warnings": run.safety_warnings or [],
        "action_cards": run.action_cards or [],
        "memory_context": run.memory_context or {},
        "evaluation_summary": run.evaluation_summary or {},
        "error": run.error,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


class AgentObservabilityService:
    """Persists and retrieves agent runs, traces, missions, and memory."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_memory_context(self, user_id: str) -> dict[str, Any]:
        """Build durable memory context from stored memories and recent behavior."""
        memory_rows = await self.db.execute(
            select(UserMemoryModel)
            .where(UserMemoryModel.user_id == user_id)
            .order_by(desc(UserMemoryModel.updated_at))
            .limit(20)
        )
        memories = memory_rows.scalars().all()

        recent_foods = await self.db.execute(
            select(FoodItemModel.name)
            .join(MealModel, FoodItemModel.meal_id == MealModel.id)
            .join(LogModel, MealModel.log_id == LogModel.id)
            .where(LogModel.user_id == user_id)
            .order_by(desc(LogModel.date))
            .limit(30)
        )
        food_names = [row[0] for row in recent_foods.all()]
        top_foods = sorted(set(food_names), key=food_names.count, reverse=True)[:8]

        return {
            "memories": [
                {
                    "category": row.category,
                    "key": row.key,
                    "value": row.value,
                    "confidence": row.confidence,
                    "source": row.source,
                }
                for row in memories
            ],
            "recent_preferred_foods": top_foods,
            "memory_count": len(memories),
        }

    async def learn_from_run(self, user_id: str, result: dict[str, Any]) -> None:
        """Persist lightweight memories inferred from agent output."""
        memory_context = result.get("memory_context") or {}
        for food in memory_context.get("recent_preferred_foods", [])[:5]:
            await self.upsert_memory(
                user_id=user_id,
                category="food_preference",
                key=str(food),
                value={"food": food, "reason": "recently_logged"},
                confidence=0.65,
                source="logs",
            )

        for warning in result.get("safety_warnings") or []:
            await self.upsert_memory(
                user_id=user_id,
                category="safety_pattern",
                key=warning.get("rule", "unknown"),
                value=warning,
                confidence=0.8,
                source="agent",
            )

    async def upsert_memory(
        self,
        *,
        user_id: str,
        category: str,
        key: str,
        value: dict[str, Any],
        confidence: float,
        source: str,
    ) -> None:
        """Create or update one user memory."""
        existing = await self.db.execute(
            select(UserMemoryModel).where(
                UserMemoryModel.user_id == user_id,
                UserMemoryModel.category == category,
                UserMemoryModel.key == key,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.value = value
            row.confidence = max(float(row.confidence or 0), confidence)
            row.source = source
            row.updated_at = datetime.now()
        else:
            self.db.add(
                UserMemoryModel(
                    user_id=user_id,
                    category=category,
                    key=key,
                    value=value,
                    confidence=confidence,
                    source=source,
                )
            )

    async def persist_run(self, user_id: str, trigger: str, result: dict[str, Any]) -> dict[str, Any]:
        """Persist an agent result and return the serialized run."""
        run_id = result.get("run_id") or str(uuid4())
        trace = result.get("trace") or []
        run = AgentRunModel(
            id=run_id,
            user_id=user_id,
            trigger=trigger,
            status=result.get("status", "unknown"),
            latency_ms=int(result.get("latency_ms") or 0),
            planner_output=result.get("planner_output") or {},
            actor_output=result.get("actor_output") or {},
            reflection=result.get("reflection") or {},
            adjustment=result.get("adjustment") or {},
            reflection_summary=result.get("reflection_summary"),
            motivation=result.get("motivation"),
            trends=result.get("trends") or {},
            tool_trace=result.get("tool_trace") or [],
            plan_diff=result.get("plan_diff") or [],
            safety_warnings=result.get("safety_warnings") or [],
            action_cards=result.get("action_cards") or [],
            memory_context=result.get("memory_context") or {},
            evaluation_summary=result.get("evaluation_summary") or {},
            error=result.get("error"),
            completed_at=datetime.now(),
        )
        self.db.add(run)
        await self.db.flush()

        for index, step in enumerate(trace):
            self.db.add(
                AgentStepModel(
                    run_id=run_id,
                    sequence=index,
                    node=step.get("node", "unknown"),
                    title=step.get("title", step.get("node", "unknown")),
                    status=step.get("status", "unknown"),
                    decision=step.get("decision"),
                    reasoning=step.get("reasoning"),
                    input_summary=step.get("input_summary") or {},
                    output_summary=step.get("output_summary") or {},
                    confidence=float(step.get("confidence") or 0),
                    duration_ms=int(step.get("duration_ms") or 0),
                    started_at=_parse_datetime(step.get("started_at")),
                    completed_at=_parse_datetime(step.get("completed_at")),
                )
            )

        for mission in result.get("missions") or []:
            self.db.add(
                AgentMissionModel(
                    id=mission.get("id") or str(uuid4()),
                    user_id=user_id,
                    run_id=run_id,
                    title=mission.get("title", "Agent 任务"),
                    description=mission.get("description"),
                    status="proposed",
                    due_date=_parse_date(mission.get("due_date")),
                    next_action=mission.get("next_action"),
                    evidence=mission.get("evidence") or [],
                )
            )

        await self.learn_from_run(user_id, result)
        await self.db.flush()
        return await self.get_run(run_id) or {**result, "run_id": run_id}

    async def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        """Return one persisted agent run."""
        result = await self.db.execute(
            select(AgentRunModel)
            .where(AgentRunModel.id == run_id)
            .options(selectinload(AgentRunModel.steps))
        )
        run = result.scalar_one_or_none()
        return _model_to_dict(run) if run else None

    async def list_runs(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent persisted agent runs for a user."""
        result = await self.db.execute(
            select(AgentRunModel)
            .where(AgentRunModel.user_id == user_id)
            .order_by(desc(AgentRunModel.created_at))
            .limit(limit)
            .options(selectinload(AgentRunModel.steps))
        )
        return [_model_to_dict(run) for run in result.scalars().all()]

    async def list_missions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent agent missions."""
        result = await self.db.execute(
            select(AgentMissionModel)
            .where(AgentMissionModel.user_id == user_id)
            .order_by(desc(AgentMissionModel.created_at))
            .limit(limit)
        )
        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "title": row.title,
                "description": row.description,
                "status": row.status,
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "next_action": row.next_action,
                "evidence": row.evidence or [],
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in result.scalars().all()
        ]

    async def get_evaluation_summary(self) -> dict[str, Any]:
        """Read local evaluation artifacts and summarize latest agent metrics."""
        eval_dir = Path("evaluation_results")
        files = sorted(eval_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        latest = []
        for path in files[:8]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            latest.append({
                "file": path.name,
                "benchmark": data.get("benchmark") or data.get("name") or path.stem.split("_")[0].upper(),
                "accuracy": data.get("accuracy") or data.get("score") or data.get("pass_rate"),
                "total": data.get("total") or data.get("total_samples") or data.get("num_samples"),
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            })
        return {
            "latest_runs": latest,
            "artifact_count": len(files),
            "report_path": "evaluation_results/evaluation_report.md"
            if (eval_dir / "evaluation_report.md").exists()
            else None,
        }
