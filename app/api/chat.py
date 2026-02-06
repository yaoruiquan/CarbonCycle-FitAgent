"""
Chat API endpoints for AI Coach.
AI 私教聊天 API 端点

Provides endpoints for chat sessions and AI-powered conversations.
提供聊天会话和 AI 驱动对话的端点
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.db.models import ChatSessionModel, ChatMessageModel, UserModel, PlanModel, LogModel
from app.models.chat import (
    ChatMessage, ChatRole, ChatIntent, ActionCard, ActionType,
    ChatMessageCreate, ChatMessageResponse, ChatSession,
    ChatSessionSummary, ChatHistoryResponse,
)
from app.llm import get_llm_client
from app.agent import run_agent

logger = get_logger(__name__)
router = APIRouter()


# ============ Intent Classification ============

INTENT_CLASSIFICATION_PROMPT = """你是健身教练助手的意图分类器。分析用户消息，判断用户意图。

用户消息: {message}

可选意图及说明：
- query_plan: 询问今天/这周的计划安排
- query_progress: 询问执行进度、完成情况
- query_nutrition: 营养饮食相关咨询
- adjust_plan: 请求修改或调整计划
- add_food: 想要记录饮食
- log_training: 想要记录训练
- analyze_week: 请求周报告或周分析
- get_suggestions: 请求改进建议
- greeting: 打招呼、闲聊
- general_qa: 通用健身/减脂/增肌问题

仅返回 JSON，格式: {{"intent": "<类型>", "confidence": <0-1>}}"""


async def classify_intent(message: str, llm) -> tuple[ChatIntent, float]:
    """Classify user intent using LLM."""
    try:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message)
        response = await llm.chat([{"role": "user", "content": prompt}])
        content = response.get("content", "{}")
        
        # Parse JSON response
        import re
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            data = json.loads(json_match.group())
            intent_str = data.get("intent", "general_qa")
            confidence = float(data.get("confidence", 0.5))
            
            try:
                intent = ChatIntent(intent_str)
            except ValueError:
                intent = ChatIntent.GENERAL_QA
            
            return intent, confidence
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")
    
    return ChatIntent.GENERAL_QA, 0.5


# ============ Context Retrieval ============

async def retrieve_context(
    intent: ChatIntent,
    user_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Retrieve context based on intent."""
    context: dict[str, Any] = {}
    
    # Get user
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        context["user"] = {
            "name": user.name,
            "goal": user.goal,
            "weight_kg": user.weight_kg,
            "target_weight_kg": user.target_weight_kg,
        }
    
    # Get active plan
    result = await db.execute(
        select(PlanModel)
        .where(PlanModel.user_id == user_id, PlanModel.is_active == True)
        .options(selectinload(PlanModel.days))
    )
    plan = result.scalar_one_or_none()
    if plan:
        from datetime import date
        today = date.today()
        today_day = next((d for d in plan.days if d.date == today), None)
        
        context["plan"] = {
            "start_date": plan.start_date.isoformat(),
            "today_type": today_day.day_type if today_day else "unknown",
            "today_macros": {
                "protein_g": today_day.protein_g if today_day else 0,
                "carbs_g": today_day.carbs_g if today_day else 0,
                "fat_g": today_day.fat_g if today_day else 0,
            } if today_day else None,
            "training_scheduled": today_day.training_scheduled if today_day else False,
        }
    
    # Get recent logs for progress queries
    if intent in [ChatIntent.QUERY_PROGRESS, ChatIntent.ANALYZE_WEEK, ChatIntent.GET_SUGGESTIONS]:
        result = await db.execute(
            select(LogModel)
            .where(LogModel.user_id == user_id)
            .order_by(desc(LogModel.date))
            .limit(7)
        )
        logs = result.scalars().all()
        context["logs"] = [
            {
                "date": log.date.isoformat(),
                "training_completed": log.training_completed,
            }
            for log in logs
        ]
    
    return context


# ============ Response Generation ============

COACH_SYSTEM_PROMPT = """你是一位专业的健身私教和营养师，名叫"Carbon Coach"。

用户信息：
{user_context}

当前计划：
{plan_context}

你的职责：
1. 根据用户的目标和当前计划，提供个性化的建议
2. 用友好、鼓励的语气回答问题
3. 回答要简洁实用，避免过长的理论解释
4. 如果用户问的问题需要调整计划，建议他们使用"调整计划"功能

回答格式要求：
- 使用 Markdown 格式
- 重要数字用粗体标注
- 适当使用 emoji 增加亲和力"""


async def generate_response(
    intent: ChatIntent,
    context: dict[str, Any],
    messages: list[ChatMessage],
    llm,
) -> tuple[str, list[ActionCard]]:
    """Generate AI response based on intent and context."""
    
    # Build system prompt
    user_context = json.dumps(context.get("user", {}), ensure_ascii=False, indent=2)
    plan_context = json.dumps(context.get("plan", {}), ensure_ascii=False, indent=2)
    
    system_prompt = COACH_SYSTEM_PROMPT.format(
        user_context=user_context,
        plan_context=plan_context,
    )
    
    # Build message history
    llm_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages[-5:]:  # Last 5 messages for context
        llm_messages.append({
            "role": msg.role.value,
            "content": msg.content,
        })
    
    # Generate response
    response = await llm.chat(llm_messages)
    content = response.get("content", "抱歉，我暂时无法回答这个问题。")
    
    # Generate action suggestions based on intent
    actions = []
    if intent == ChatIntent.QUERY_PLAN:
        actions.append(ActionCard(
            type=ActionType.VIEW_PLAN,
            title="查看完整计划",
            description="打开碳循环策略页面",
            data={"route": "/strategy"},
        ))
    elif intent == ChatIntent.ADD_FOOD:
        actions.append(ActionCard(
            type=ActionType.LOG_FOOD,
            title="记录饮食",
            description="打开饮食记录弹窗",
            data={"action": "open_food_modal"},
        ))
    elif intent == ChatIntent.LOG_TRAINING:
        actions.append(ActionCard(
            type=ActionType.LOG_TRAINING,
            title="记录训练",
            description="标记今日训练完成",
            data={"action": "log_training"},
        ))
    elif intent == ChatIntent.ANALYZE_WEEK:
        actions.append(ActionCard(
            type=ActionType.VIEW_REPORT,
            title="查看报告",
            description="打开周报告页面",
            data={"route": "/report"},
        ))
    
    return content, actions


# ============ API Endpoints ============

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageCreate,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """
    Send a message and get AI response.
    发送消息并获取 AI 回复
    """
    llm = get_llm_client()
    
    # Get or create session
    session_id = request.session_id
    if session_id:
        result = await db.execute(
            select(ChatSessionModel)
            .where(ChatSessionModel.id == str(session_id))
            .options(selectinload(ChatSessionModel.messages))
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create new session
        session = ChatSessionModel(
            id=str(uuid4()),
            user_id=user_id,
            title=request.content[:30] + ("..." if len(request.content) > 30 else ""),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(session)
        await db.flush()
    
    # Classify intent
    intent, confidence = await classify_intent(request.content, llm)
    logger.info(f"Classified intent: {intent.value} (confidence: {confidence:.2f})")
    
    # Save user message
    user_msg = ChatMessageModel(
        id=str(uuid4()),
        session_id=str(session.id),
        role=ChatRole.USER.value,
        content=request.content,
        intent=intent.value,
        metadata_json={"confidence": confidence},
        timestamp=datetime.now(),
    )
    db.add(user_msg)
    
    # Retrieve context
    context = await retrieve_context(intent, user_id, db)
    
    # Get existing messages for context
    existing_messages = []
    if "messages" in session.__dict__:
        existing_messages = [msg.to_pydantic() for msg in session.messages]
    existing_messages.append(user_msg.to_pydantic())
    
    # Generate response
    response_content, actions = await generate_response(
        intent, context, existing_messages, llm
    )
    
    # Save assistant message
    assistant_msg = ChatMessageModel(
        id=str(uuid4()),
        session_id=str(session.id),
        role=ChatRole.ASSISTANT.value,
        content=response_content,
        metadata_json={"actions": [a.model_dump() for a in actions]},
        timestamp=datetime.now(),
    )
    db.add(assistant_msg)
    
    await db.commit()
    
    return ChatMessageResponse(
        session_id=UUID(str(session.id)),
        message=assistant_msg.to_pydantic(),
        actions=actions,
    )


@router.post("/stream")
async def stream_message(
    request: ChatMessageCreate,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream AI response using Server-Sent Events.
    使用 SSE 流式返回 AI 回复
    """
    llm = get_llm_client()
    
    # Get or create session
    session_id = request.session_id
    if session_id:
        result = await db.execute(
            select(ChatSessionModel)
            .where(ChatSessionModel.id == str(session_id))
            .options(selectinload(ChatSessionModel.messages))
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSessionModel(
            id=str(uuid4()),
            user_id=user_id,
            title=request.content[:30] + ("..." if len(request.content) > 30 else ""),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(session)
        await db.flush()
    
    # Classify intent
    intent, confidence = await classify_intent(request.content, llm)
    
    # Save user message
    user_msg = ChatMessageModel(
        id=str(uuid4()),
        session_id=str(session.id),
        role=ChatRole.USER.value,
        content=request.content,
        intent=intent.value,
        metadata_json={"confidence": confidence},
    )
    db.add(user_msg)
    await db.flush()
    
    # Retrieve context
    context = await retrieve_context(intent, user_id, db)
    
    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE stream."""
        # Send session ID first
        yield f"data: {json.dumps({'type': 'session', 'session_id': str(session.id)})}\n\n"
        
        # Build messages for LLM
        user_context = json.dumps(context.get("user", {}), ensure_ascii=False)
        plan_context = json.dumps(context.get("plan", {}), ensure_ascii=False)
        system_prompt = COACH_SYSTEM_PROMPT.format(
            user_context=user_context,
            plan_context=plan_context,
        )
        
        llm_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.content},
        ]
        
        # Stream response
        full_content = ""
        try:
            async for chunk in llm.stream_chat(llm_messages):
                if chunk:
                    full_content += chunk
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            full_content = "抱歉，生成回复时出现错误。"
            yield f"data: {json.dumps({'type': 'content', 'content': full_content})}\n\n"
        
        # Save assistant message
        assistant_msg = ChatMessageModel(
            id=str(uuid4()),
            session_id=str(session.id),
            role=ChatRole.ASSISTANT.value,
            content=full_content,
            metadata_json={},
            timestamp=datetime.now(),
        )
        db.add(assistant_msg)
        await db.commit()
        
        # Send completion
        yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_msg.id)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/sessions", response_model=list[ChatSessionSummary])
async def list_sessions(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ChatSessionSummary]:
    """
    List user's chat sessions.
    获取用户的聊天会话列表
    """
    result = await db.execute(
        select(ChatSessionModel)
        .where(ChatSessionModel.user_id == user_id)
        .order_by(desc(ChatSessionModel.updated_at))
        .limit(limit)
        .options(selectinload(ChatSessionModel.messages))
    )
    sessions = result.scalars().all()
    
    return [
        ChatSessionSummary(
            id=UUID(str(s.id)),
            title=str(s.title or "新对话"),
            message_count=len(s.messages),
            last_message=s.messages[-1].content[:50] if s.messages else None,
            updated_at=s.updated_at,  # type: ignore
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    """
    Get chat session with full history.
    获取完整的聊天会话历史
    """
    result = await db.execute(
        select(ChatSessionModel)
        .where(ChatSessionModel.id == session_id)
        .options(selectinload(ChatSessionModel.messages))
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return ChatHistoryResponse(
        session=session.to_pydantic(),
        total_messages=len(session.messages),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a chat session.
    删除聊天会话
    """
    result = await db.execute(
        select(ChatSessionModel).where(ChatSessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.delete(session)
    await db.commit()
    
    return {"status": "deleted", "session_id": session_id}
