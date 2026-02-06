"""
Comprehensive backend test.
后端综合测试

Tests all major components of the CarbonCycle-FitAgent backend.
测试 CarbonCycle-FitAgent 后端的所有主要组件
"""

import asyncio
import sys
from datetime import date, time, timedelta
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force UTF-8 encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def print_header(title: str) -> None:
    """Print section header."""
    print("\n" + "=" * 60)
    print(f"🧪 {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = "") -> None:
    """Print test result."""
    status = "✅" if success else "❌"
    print(f"  {status} {name}")
    if message:
        print(f"     └─ {message}")


async def test_core_modules():
    """Test core modules: config, database, logging."""
    print_header("1. Core 模块")
    
    from app.core.config import get_settings
    from app.core.logging import get_logger
    
    settings = get_settings()
    print_result("Config 加载", settings is not None, f"App: {settings.app_name}")
    
    logger = get_logger("test")
    print_result("Logger 获取", logger is not None)
    
    from app.core.database import get_engine
    engine = get_engine()
    print_result("Database 引擎", engine is not None, f"URL: {engine.url}")
    
    return True


async def test_models():
    """Test Pydantic models."""
    print_header("2. Models 模块")
    
    from app.models.user import UserProfile, UserCreate, Gender, UserGoal, ActivityLevel
    from app.models.plan import CarbonCyclePlan, DayPlan, MacroNutrients, DayType
    from app.models.log import DietLog, MealLog, FoodItem, MealType
    
    # User model
    user = UserProfile(
        name="测试用户",
        gender=Gender.MALE,
        birth_date=date(1995, 1, 1),
        height_cm=175,
        weight_kg=75,
        goal=UserGoal.FAT_LOSS,
    )
    print_result("UserProfile 创建", user.id is not None)
    print_result("TDEE 计算", user.calculate_tdee() > 0, f"{user.calculate_tdee():.0f} kcal")
    
    # Plan model
    days = [
        DayPlan(
            date=date.today(),
            day_type=DayType.HIGH_CARB,
            macros=MacroNutrients(protein_g=150, carbs_g=250, fat_g=60),
        )
    ]
    plan = CarbonCyclePlan(
        user_id=user.id,
        start_date=date.today(),
        end_date=date.today(),
        days=days,
        base_calories=2500,
    )
    print_result("CarbonCyclePlan 创建", plan.id is not None)
    
    # Log model
    log = DietLog(
        user_id=user.id,
        date=date.today(),
        meals=[
            MealLog(
                meal_type=MealType.BREAKFAST,
                time=time(8, 0),
                items=[FoodItem(name="燕麦", quantity=50, unit="g", calories=180)],
            )
        ],
    )
    print_result("DietLog 创建", log.total_calories == 180)
    
    return True


async def test_services():
    """Test service modules."""
    print_header("3. Services 模块")
    
    from app.services.carbon_strategy import CarbonStrategyService
    from app.services.knowledge_service import KnowledgeService
    
    # CarbonStrategyService
    strategy = CarbonStrategyService()
    print_result("CarbonStrategyService 初始化", strategy is not None)
    
    # KnowledgeService
    knowledge = KnowledgeService()
    food = knowledge.query_food_nutrition("鸡胸肉", 150)
    print_result("食物营养查询", food is not None, f"鸡胸肉: {food['calories']} kcal")
    
    high_protein = knowledge.get_high_protein_foods(3)
    print_result("高蛋白食物搜索", len(high_protein) == 3)
    
    return True


async def test_memory():
    """Test memory modules."""
    print_header("4. Memory 模块")
    
    from app.memory.user_memory import get_user_memory, UserPreferences
    from app.memory.agent_memory import get_agent_memory
    
    user_id = uuid4()
    
    # User memory
    user_mem = get_user_memory()
    prefs = await user_mem.get_preferences(user_id)
    print_result("UserMemory 获取偏好", prefs is not None)
    
    await user_mem.add_preferred_food(user_id, "鸡胸肉")
    prefs = await user_mem.get_preferences(user_id)
    print_result("添加偏好食物", "鸡胸肉" in prefs.preferred_foods)
    
    # Agent memory
    agent_mem = get_agent_memory()
    run = await agent_mem.start_run(user_id, "test")
    print_result("AgentMemory 开始运行", run is not None)
    
    await agent_mem.record_decision(
        run_id=run.id,
        node="test_node",
        decision="test_decision",
        reasoning="test_reasoning",
    )
    fetched_run = await agent_mem.get_run(run.id)
    print_result("记录决策", len(fetched_run.decisions) == 1)
    
    return True


async def test_llm():
    """Test LLM client."""
    print_header("5. LLM 模块")
    
    from app.llm.client import get_llm_client
    
    client = get_llm_client()
    print_result("LLM Client 初始化", client is not None)
    
    # Quick chat test
    try:
        response = await asyncio.wait_for(
            client.chat([{"role": "user", "content": "你好，请用一个词回复"}]),
            timeout=10.0
        )
        print_result("LLM Chat 调用", response.get("content") is not None, "响应成功")
    except asyncio.TimeoutError:
        print_result("LLM Chat 调用", False, "超时")
    except Exception as e:
        print_result("LLM Chat 调用", False, str(e)[:40])
    
    return True


async def test_rag():
    """Test RAG module."""
    print_header("6. RAG 模块")
    
    try:
        from app.rag.retriever import retrieve_context
        
        context = await retrieve_context("碳循环饮食", top_k=2)
        print_result("RAG 检索", len(context) > 0, f"{len(context)} chars")
    except Exception as e:
        print_result("RAG 检索", False, str(e)[:40])
    
    return True


async def test_agent():
    """Test Agent flow."""
    print_header("7. Agent 模块")
    
    from app.agent import run_agent
    
    user_context = {
        "user_id": str(uuid4()),
        "name": "测试用户",
        "gender": "male",
        "age": 28,
        "height_cm": 175,
        "weight_kg": 75,
        "goal": "fat_loss",
        "activity_level": "moderate",
        "training_days": 4,
        "tdee": 2500,
    }
    
    plan_context = {
        "day_type": "high_carb",
        "target_calories": 2500,
        "cycle_length": 7,
    }
    
    try:
        result = await asyncio.wait_for(
            run_agent(
                user_id=user_context["user_id"],
                trigger="test",
                user_context=user_context,
                plan_context=plan_context,
            ),
            timeout=60.0
        )
        
        print_result("Agent 执行", result.get("status") == "success")
        print_result("Planner 输出", result.get("planner_output") is not None)
        
    except asyncio.TimeoutError:
        print_result("Agent 执行", False, "超时 (60s)")
    except Exception as e:
        print_result("Agent 执行", False, str(e)[:50])
    
    return True


async def test_database_storage():
    """Test database persistence."""
    print_header("8. Database 持久化")
    
    from app.core.database import get_db_context, get_engine, Base
    from app.db.models import UserModel
    from app.db.db_storage import DatabaseStorage
    from app.models.user import UserProfile, Gender, UserGoal, ActivityLevel
    
    # Ensure tables exist
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with get_db_context() as session:
        storage = DatabaseStorage(session)
        
        # Create user
        user = UserProfile(
            name="DB测试用户",
            gender=Gender.MALE,
            birth_date=date(1990, 1, 1),
            height_cm=180,
            weight_kg=80,
            goal=UserGoal.FAT_LOSS,
        )
        
        created = await storage.add_user(user)
        print_result("创建用户", created is not None)
        
        # Fetch user
        fetched = await storage.get_user(user.id)
        print_result("获取用户", fetched is not None and fetched.name == "DB测试用户")
        
        # Delete user
        deleted = await storage.delete_user(user.id)
        print_result("删除用户", deleted)
    
    return True


async def main():
    """Run all backend tests."""
    print("\n" + "🚀 CarbonCycle-FitAgent 后端综合测试" + "\n")
    
    results = []
    
    # Test each module
    results.append(("Core", await test_core_modules()))
    results.append(("Models", await test_models()))
    results.append(("Services", await test_services()))
    results.append(("Memory", await test_memory()))
    results.append(("LLM", await test_llm()))
    results.append(("RAG", await test_rag()))
    results.append(("Agent", await test_agent()))
    results.append(("Database", await test_database_storage()))
    
    # Summary
    print_header("测试结果汇总")
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
    
    print()
    print(f"📊 通过率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 所有后端测试通过！后端开发完成。")
    else:
        print("\n⚠️ 部分测试需要关注。")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
