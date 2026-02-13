"""
API routes package.
API 路由包

Contains all FastAPI route definitions.
包含所有 FastAPI 路由定义
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.user import router as user_router
from app.api.plan import router as plan_router
from app.api.log import router as log_router
from app.api.agent import router as agent_router
from app.api.report import router as report_router
from app.api.food import router as food_router
from app.api.chat import router as chat_router
from app.api.weight import router as weight_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(user_router, prefix="/users", tags=["users"])
api_router.include_router(plan_router, prefix="/plans", tags=["plans"])
api_router.include_router(log_router, prefix="/logs", tags=["logs"])
api_router.include_router(weight_router, prefix="/weights", tags=["weights"])
api_router.include_router(agent_router, prefix="/agent", tags=["agent"])
api_router.include_router(report_router, prefix="/reports", tags=["reports"])
api_router.include_router(food_router, prefix="/food", tags=["food"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])

__all__ = ["api_router"]


