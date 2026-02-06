"""
User memory storage.
用户记忆存储

Manages persistent storage of user preferences, history, and state.
管理用户偏好、历史记录和状态的持久存储
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Protocol
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class MemoryStore(Protocol):
    """Protocol for memory storage backends."""
    
    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve value by key."""
        ...
    
    async def set(self, key: str, value: dict[str, Any], ttl: Optional[int] = None) -> None:
        """Store value with optional TTL."""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete value by key."""
        ...


class UserPreferences(BaseModel):
    """
    User preferences learned over time.
    
    Attributes:
        preferred_foods: Foods the user frequently logs.
        avoided_foods: Foods the user avoids.
        preferred_meal_times: Typical meal schedule.
        training_preferences: Training style preferences.
        notes: Additional learned preferences.
    """
    
    preferred_foods: list[str] = Field(default_factory=list)
    avoided_foods: list[str] = Field(default_factory=list)
    preferred_meal_times: dict[str, str] = Field(default_factory=dict)
    training_preferences: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class UserState(BaseModel):
    """
    Current user state snapshot.
    
    Attributes:
        user_id: User identifier.
        current_weight_kg: Most recent weight.
        current_plan_id: Active plan identifier.
        streak_days: Consecutive days of logging.
        last_log_date: Most recent log date.
        average_adherence: Recent adherence average.
        updated_at: State update timestamp.
    """
    
    user_id: UUID
    current_weight_kg: Optional[float] = None
    current_plan_id: Optional[UUID] = None
    streak_days: int = 0
    last_log_date: Optional[datetime] = None
    average_adherence: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.now)


class InMemoryStore:
    """Simple in-memory storage implementation."""
    
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
    
    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve value by key."""
        return self._store.get(key)
    
    async def set(
        self, 
        key: str, 
        value: dict[str, Any], 
        ttl: Optional[int] = None,
    ) -> None:
        """Store value (TTL not implemented in memory store)."""
        self._store[key] = value
    
    async def delete(self, key: str) -> None:
        """Delete value by key."""
        self._store.pop(key, None)


class UserMemory:
    """
    Manages user-related memory storage and retrieval.
    
    Provides methods to store and retrieve user preferences,
    state, and historical patterns.
    """
    
    def __init__(self, store: MemoryStore) -> None:
        """
        Initialize user memory with storage backend.
        
        Args:
            store: Storage backend implementing MemoryStore protocol.
        """
        self._store = store
    
    def _preferences_key(self, user_id: UUID) -> str:
        """Generate storage key for user preferences."""
        return f"user:{user_id}:preferences"
    
    def _state_key(self, user_id: UUID) -> str:
        """Generate storage key for user state."""
        return f"user:{user_id}:state"
    
    async def get_preferences(self, user_id: UUID) -> UserPreferences:
        """
        Get user preferences.
        
        Args:
            user_id: User identifier.
            
        Returns:
            UserPreferences object (empty if not found).
        """
        data = await self._store.get(self._preferences_key(user_id))
        if data:
            return UserPreferences.model_validate(data)
        return UserPreferences()
    
    async def update_preferences(
        self,
        user_id: UUID,
        preferences: UserPreferences,
    ) -> None:
        """
        Update user preferences.
        
        Args:
            user_id: User identifier.
            preferences: Updated preferences.
        """
        await self._store.set(
            self._preferences_key(user_id),
            preferences.model_dump(),
        )
        logger.debug(f"Updated preferences for user {user_id}")
    
    async def add_preferred_food(self, user_id: UUID, food: str) -> None:
        """
        Add a food to user's preferred list.
        
        Args:
            user_id: User identifier.
            food: Food name to add.
        """
        prefs = await self.get_preferences(user_id)
        if food not in prefs.preferred_foods:
            prefs.preferred_foods.append(food)
            await self.update_preferences(user_id, prefs)
    
    async def get_state(self, user_id: UUID) -> Optional[UserState]:
        """
        Get current user state.
        
        Args:
            user_id: User identifier.
            
        Returns:
            UserState if found, None otherwise.
        """
        data = await self._store.get(self._state_key(user_id))
        if data:
            return UserState.model_validate(data)
        return None
    
    async def update_state(self, user_id: UUID, state: UserState) -> None:
        """
        Update user state.
        
        Args:
            user_id: User identifier.
            state: Updated state.
        """
        state.updated_at = datetime.now()
        await self._store.set(
            self._state_key(user_id),
            state.model_dump(mode="json"),
        )
        logger.debug(f"Updated state for user {user_id}")


# Singleton instance
_user_memory: Optional[UserMemory] = None


def get_user_memory() -> UserMemory:
    """
    Get or create the singleton user memory instance.
    
    Returns:
        UserMemory: Configured memory instance.
    """
    global _user_memory
    if _user_memory is None:
        # Default to in-memory store; replace with Redis/DB in production
        store = InMemoryStore()
        _user_memory = UserMemory(store)
    return _user_memory
