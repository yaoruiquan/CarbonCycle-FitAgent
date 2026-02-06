"""
User repository.
用户仓库

Handles database operations for users.
处理用户的数据库操作
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserModel
from app.models.user import UserProfile


class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user: UserProfile) -> UserProfile:
        """Create a new user."""
        db_user = UserModel.from_pydantic(user)
        self.session.add(db_user)
        await self.session.flush()
        return db_user.to_pydantic()
    
    async def get_by_id(self, user_id: UUID | str) -> Optional[UserProfile]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        db_user = result.scalar_one_or_none()
        return db_user.to_pydantic() if db_user else None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        db_user = result.scalar_one_or_none()
        return db_user.to_pydantic() if db_user else None
    
    async def update(self, user_id: UUID | str, **updates) -> Optional[UserProfile]:
        """Update user fields."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None
        
        for field, value in updates.items():
            if hasattr(db_user, field) and value is not None:
                # Handle enum values
                if hasattr(value, 'value'):
                    value = value.value
                setattr(db_user, field, value)
        
        await self.session.flush()
        return db_user.to_pydantic()
    
    async def delete(self, user_id: UUID | str) -> bool:
        """Delete user and cascade to related data."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        db_user = result.scalar_one_or_none()
        if not db_user:
            return False
        
        await self.session.delete(db_user)
        await self.session.flush()
        return True
    
    async def list_all(self) -> list[UserProfile]:
        """List all users."""
        result = await self.session.execute(select(UserModel))
        return [u.to_pydantic() for u in result.scalars().all()]
