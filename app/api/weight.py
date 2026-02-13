"""
Weight log API endpoints.
体重记录 API 端点

Provides CRUD operations for user weight tracking.
提供用户体重记录的增删改查操作
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.db_storage import DatabaseStorage
from app.models.log import WeightLog, WeightLogCreate

router = APIRouter()


@router.post("/", response_model=WeightLog, status_code=status.HTTP_201_CREATED)
async def create_weight_log(
    data: WeightLogCreate,
    db: AsyncSession = Depends(get_db),
) -> WeightLog:
    """
    Record a new weight measurement.
    记录一条新的体重数据
    """
    storage = DatabaseStorage(db)
    
    if not await storage.get_user(data.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    weight_log = WeightLog(**data.model_dump())
    return await storage.add_weight_log(weight_log)


@router.get("/user/{user_id}", response_model=list[WeightLog])
async def get_user_weight_logs(
    user_id: str,
    limit: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[WeightLog]:
    """
    Get recent weight logs for a user.
    获取用户最近的体重记录
    """
    storage = DatabaseStorage(db)
    if not await storage.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return await storage.get_user_weight_logs(user_id, limit=limit)


@router.get("/user/{user_id}/latest", response_model=Optional[WeightLog])
async def get_latest_weight(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> Optional[WeightLog]:
    """
    Get the most recent weight log for a user.
    获取用户最新体重记录
    """
    storage = DatabaseStorage(db)
    if not await storage.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return await storage.get_latest_weight(user_id)


@router.get("/user/{user_id}/range", response_model=list[WeightLog])
async def get_weight_range(
    user_id: str,
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    db: AsyncSession = Depends(get_db),
) -> list[WeightLog]:
    """
    Get weight logs within a date range, ordered by date ascending.
    按日期范围查询体重记录（升序）
    """
    storage = DatabaseStorage(db)
    if not await storage.get_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if start > end:
        raise HTTPException(status_code=400, detail="start date must be <= end date")
    return await storage.get_weight_by_date_range(user_id, start, end)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a weight log.
    删除体重记录
    """
    storage = DatabaseStorage(db)
    if not await storage.delete_weight_log(log_id):
        raise HTTPException(status_code=404, detail="Weight log not found")
