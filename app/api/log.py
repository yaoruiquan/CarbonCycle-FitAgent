from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.db_storage import DatabaseStorage
from app.models.log import DietLog, LogCreate, LogUpdate

router = APIRouter()


class LogStatsResponse(BaseModel):
    """Response model for log statistics."""
    days_logged: int
    avg_calories: float
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    training_completion_rate: float


@router.post("/", response_model=DietLog, status_code=status.HTTP_201_CREATED)
async def create_log(log_data: LogCreate, db: AsyncSession = Depends(get_db)) -> DietLog:
    """
    Create a new diet log.
    创建新饮食日志
    """
    storage = DatabaseStorage(db)
    
    # Verify user exists
    if not await storage.get_user(log_data.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    log = DietLog(**log_data.model_dump())
    return await storage.add_log(log)


@router.get("/{log_id}", response_model=DietLog)
async def get_log(log_id: str, db: AsyncSession = Depends(get_db)) -> DietLog:
    """
    Get log by ID.
    根据 ID 获取日志
    """
    storage = DatabaseStorage(db)
    log = await storage.get_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.get("/user/{user_id}", response_model=list[DietLog])
async def get_user_logs(
    user_id: str,
    limit: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
) -> list[DietLog]:
    """
    Get recent logs for a user.
    获取用户最近的日志
    """
    storage = DatabaseStorage(db)
    if not await storage.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return await storage.get_user_logs(user_id, limit=limit)


@router.get("/user/{user_id}/date/{log_date}", response_model=DietLog)
async def get_log_by_date(user_id: str, log_date: date, db: AsyncSession = Depends(get_db)) -> DietLog:
    """
    Get log for a specific date.
    获取特定日期的日志
    """
    storage = DatabaseStorage(db)
    log = await storage.get_log_by_date(user_id, log_date)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found for date")
    return log


@router.get("/user/{user_id}/stats", response_model=LogStatsResponse)
async def get_user_log_stats(
    user_id: str,
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
) -> LogStatsResponse:
    """
    Get log statistics for a user.
    获取用户的日志统计数据
    
    Returns average macros and training completion rate.
    """
    storage = DatabaseStorage(db)
    if not await storage.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    stats = await storage.get_user_log_stats(user_id, days=days)
    return LogStatsResponse(**stats)


@router.patch("/{log_id}", response_model=DietLog)
async def update_log(log_id: str, update_data: LogUpdate, db: AsyncSession = Depends(get_db)) -> DietLog:
    """
    Update a diet log.
    更新饮食日志
    """
    storage = DatabaseStorage(db)
    update_dict = update_data.model_dump(exclude_unset=True)
    log = await storage.update_log(log_id, **update_dict)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(log_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a diet log.
    删除饮食日志
    """
    storage = DatabaseStorage(db)
    if not await storage.delete_log(log_id):
        raise HTTPException(status_code=404, detail="Log not found")
