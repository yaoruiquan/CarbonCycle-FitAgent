"""
Health check endpoint.
健康检查端点
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        dict with status "healthy".
    """
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """
    Readiness check endpoint.
    
    Returns:
        dict with ready status.
    """
    return {"status": "ready"}
