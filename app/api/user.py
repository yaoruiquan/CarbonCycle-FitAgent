"""
User profile API endpoints.
用户画像 API 端点
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.db_storage import DatabaseStorage
from app.models.user import UserCreate, UserProfile, UserUpdate

router = APIRouter()


@router.post("/", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> UserProfile:
    """
    Create a new user profile.
    创建新用户档案
    """
    storage = DatabaseStorage(db)
    # Note: For creation, we might want to use the auth register endpoint instead if it involves password.
    # But keeping this for general profile creation/testing.
    user = UserProfile(**user_data.model_dump())
    return await storage.add_user(user)


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)) -> UserProfile:
    """
    Get user profile by ID.
    根据 ID 获取用户档案
    """
    storage = DatabaseStorage(db)
    user = await storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserProfile)
async def update_user(user_id: str, update_data: UserUpdate, db: AsyncSession = Depends(get_db)) -> UserProfile:
    """
    Update user profile.
    更新用户档案
    """
    storage = DatabaseStorage(db)
    update_dict = update_data.model_dump(exclude_unset=True)
    user = await storage.update_user(user_id, **update_dict)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete user and all associated data.
    删除用户及其所有关联数据
    """
    storage = DatabaseStorage(db)
    if not await storage.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/", response_model=list[UserProfile])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[UserProfile]:
    """
    List all users.
    列出所有用户
    """
    storage = DatabaseStorage(db)
    return await storage.list_users()
