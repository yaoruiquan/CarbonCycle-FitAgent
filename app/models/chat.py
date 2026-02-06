"""
Chat models for AI Coach conversation.
AI 私教对话模型

Defines data structures for chat sessions and messages.
定义聊天会话和消息的数据结构
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    """Chat message role."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatIntent(str, Enum):
    """Classified intent of user message."""
    
    # Query intents
    QUERY_PLAN = "query_plan"           # 查询计划信息
    QUERY_PROGRESS = "query_progress"   # 查询进度
    QUERY_NUTRITION = "query_nutrition" # 营养咨询
    
    # Action intents
    ADJUST_PLAN = "adjust_plan"         # 调整计划
    ADD_FOOD = "add_food"               # 记录饮食
    LOG_TRAINING = "log_training"       # 记录训练
    
    # Analysis intents
    ANALYZE_WEEK = "analyze_week"       # 周分析
    GET_SUGGESTIONS = "get_suggestions" # 获取建议
    
    # General intents
    GREETING = "greeting"               # 打招呼
    GENERAL_QA = "general_qa"           # 通用健身问题
    UNKNOWN = "unknown"                 # 未知意图


class ActionType(str, Enum):
    """Types of suggested actions."""
    
    ADJUST_PLAN = "adjust_plan"
    LOG_FOOD = "log_food"
    LOG_TRAINING = "log_training"
    VIEW_REPORT = "view_report"
    VIEW_PLAN = "view_plan"


class ChatMessage(BaseModel):
    """
    Single chat message in a conversation.
    
    Attributes:
        id: Unique message identifier.
        role: Message sender role (user/assistant/system).
        content: Message text content.
        intent: Classified intent (for user messages).
        metadata: Additional data (context used, actions suggested, etc).
        timestamp: When the message was created.
    """
    
    id: UUID = Field(default_factory=uuid4)
    role: ChatRole
    content: str
    intent: Optional[ChatIntent] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ActionCard(BaseModel):
    """
    Suggested action card in assistant response.
    
    Attributes:
        type: Type of action.
        title: Display title.
        description: Action description.
        data: Action-specific data.
    """
    
    type: ActionType
    title: str
    description: str
    data: dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    """
    Complete chat session with message history.
    
    Attributes:
        id: Unique session identifier.
        user_id: Owner of this session.
        title: Session title (auto-generated from first message).
        messages: List of messages in this session.
        is_active: Whether session is currently active.
        created_at: Session creation timestamp.
        updated_at: Last update timestamp.
    """
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    title: str = "新对话"
    messages: list[ChatMessage] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to this session."""
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # Update title from first user message
        if len(self.messages) == 1 and message.role == ChatRole.USER:
            self.title = message.content[:30] + ("..." if len(message.content) > 30 else "")
    
    def get_recent_messages(self, limit: int = 10) -> list[ChatMessage]:
        """Get recent messages for context."""
        return self.messages[-limit:]


# ============ API Request/Response Models ============

class ChatMessageCreate(BaseModel):
    """Request to send a new chat message."""
    
    session_id: Optional[UUID] = None  # None creates new session
    content: str = Field(..., min_length=1, max_length=2000)


class ChatMessageResponse(BaseModel):
    """Response from chat message endpoint."""
    
    session_id: UUID
    message: ChatMessage
    actions: list[ActionCard] = Field(default_factory=list)


class ChatSessionSummary(BaseModel):
    """Summary of a chat session for list view."""
    
    id: UUID
    title: str
    message_count: int
    last_message: Optional[str] = None
    updated_at: datetime


class ChatHistoryResponse(BaseModel):
    """Response containing session history."""
    
    session: ChatSession
    total_messages: int
