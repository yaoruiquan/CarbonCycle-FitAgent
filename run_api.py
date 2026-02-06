"""
Startup script for FastAPI Backend API.
FastAPI 后端接口启动脚本
"""

import os
import sys
import uvicorn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings

if __name__ == "__main__":
    from app.core.database import get_engine, Base
    import asyncio
    
    # Initialize DB (Ensures tables exist)
    async def init():
        print("Initializing database...")
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database ready.")
    
    asyncio.run(init())
    
    # Run API
    settings = get_settings()
    print(f"Starting FastAPI Backend on http://0.0.0.0:8000")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
