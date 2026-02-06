"""
Database initialization script.
数据库初始化脚本

Creates all tables defined in ORM models.
创建 ORM 模型中定义的所有表
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_engine, Base
from app.db.models import UserModel, PlanModel, DayPlanModel, LogModel, MealModel, FoodItemModel


async def init_database():
    """Initialize database schema."""
    print("=" * 50)
    print("🗄️ CarbonCycle-FitAgent 数据库初始化")
    print("=" * 50)
    
    engine = get_engine()
    
    print(f"\n📁 数据库: {engine.url}")
    print("\n⏳ 创建表结构...")
    
    async with engine.begin() as conn:
        # Drop all tables (for development)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("\n✅ 表创建成功:")
    for table in Base.metadata.tables.keys():
        print(f"   - {table}")
    
    await engine.dispose()
    print("\n🎉 数据库初始化完成！")


async def reset_database():
    """Reset database (drop and recreate all tables)."""
    print("=" * 50)
    print("⚠️ CarbonCycle-FitAgent 数据库重置")
    print("=" * 50)
    
    engine = get_engine()
    
    print(f"\n📁 数据库: {engine.url}")
    print("\n🗑️ 删除所有表...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("   表已删除")
        
        print("\n⏳ 重新创建表结构...")
        await conn.run_sync(Base.metadata.create_all)
    
    print("\n✅ 表重新创建成功")
    await engine.dispose()
    print("\n🎉 数据库重置完成！")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management")
    parser.add_argument("--reset", action="store_true", help="Reset database (drop all tables)")
    args = parser.parse_args()
    
    if args.reset:
        asyncio.run(reset_database())
    else:
        asyncio.run(init_database())
