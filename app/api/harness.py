from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.harness.case_runner import list_harness_cases, run_harness_cases
from app.harness.replay import replay_agent_run
from app.services.agent_observability import AgentObservabilityService

router = APIRouter()


class HarnessRunRequest(BaseModel):
    case_ids: Optional[list[str]] = None


@router.get("/cases")
async def get_harness_cases() -> dict[str, Any]:
    """List available domain Harness cases."""
    return {"cases": list_harness_cases()}


@router.post("/run")
async def run_harness_suite(
    request: HarnessRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run selected Harness cases."""
    return await run_harness_cases(case_ids=request.case_ids, db_session=db)


@router.get("/runs/{run_id}")
async def get_harness_run(run_id: str) -> dict[str, Any]:
    """Read a persisted Harness report from evaluation_results."""
    from pathlib import Path
    import json

    for path in Path("evaluation_results").glob("harness_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("run_id") == run_id:
            return data
    raise HTTPException(status_code=404, detail="Harness run not found")


@router.post("/replay/{run_id}")
async def replay_harness_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Replay a persisted agent run from its episode snapshot."""
    result = await replay_agent_run(
        run_id=run_id,
        observability=AgentObservabilityService(db),
        db_session=db,
    )
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    if result["status"] == "missing_episode":
        raise HTTPException(status_code=400, detail=result["message"])
    return result
