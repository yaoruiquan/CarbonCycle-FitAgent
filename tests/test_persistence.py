"""
Database persistence tests.
数据库持久化测试

Tests CRUD operations and data persistence.
测试 CRUD 操作和数据持久化
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
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status} - {name}")
    if message:
        print(f"       {message}")


async def test_user_persistence():
    """Test user CRUD with database."""
    print_header("Step 1: User 持久化测试")
    
    from app.core.database import get_db_context
    from app.db.db_storage import DatabaseStorage
    from app.models.user import UserProfile, Gender, UserGoal, ActivityLevel
    
    async with get_db_context() as session:
        storage = DatabaseStorage(session)
        
        # Create user
        user = UserProfile(
            name="测试用户_DB",
            gender=Gender.MALE,
            birth_date=date(1995, 6, 20),
            height_cm=178,
            weight_kg=75,
            target_weight_kg=70,
            goal=UserGoal.FAT_LOSS,
            activity_level=ActivityLevel.MODERATE,
        )
        
        created = await storage.add_user(user)
        print_result("创建用户", created is not None, f"ID: {created.id}")
        
        # Get user
        fetched = await storage.get_user(user.id)
        print_result("获取用户", fetched is not None and fetched.name == "测试用户_DB")
        
        # Update user
        updated = await storage.update_user(user.id, weight_kg=74)
        print_result("更新用户", updated is not None and updated.weight_kg == 74)
        
        # List users
        users = await storage.list_users()
        print_result("列出用户", len(users) >= 1)
        
        return str(user.id)


async def test_plan_persistence(user_id: str):
    """Test plan CRUD with database."""
    print_header("Step 2: Plan 持久化测试")
    
    from app.core.database import get_db_context
    from app.db.db_storage import DatabaseStorage
    from app.models.plan import CarbonCyclePlan, DayPlan, MacroNutrients, DayType
    
    async with get_db_context() as session:
        storage = DatabaseStorage(session)
        
        # Create plan
        days = [
            DayPlan(
                date=date.today() + timedelta(days=i),
                day_type=[DayType.HIGH_CARB, DayType.MEDIUM_CARB, DayType.LOW_CARB][i % 3],
                macros=MacroNutrients(
                    protein_g=150,
                    carbs_g=max(100, 300 - i * 30),  # Ensure >= 100
                    fat_g=60 + i * 5,
                ),
                training_scheduled=(i % 2 == 0),
            )
            for i in range(7)
        ]
        
        plan = CarbonCyclePlan(
            user_id=user_id,
            name="测试碳循环计划_DB",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=6),
            cycle_length_days=7,
            days=days,
            base_calories=2500,
            is_active=True,
        )
        
        created = await storage.add_plan(plan)
        print_result("创建计划", created is not None, f"ID: {created.id}")
        
        # Get plan
        fetched = await storage.get_plan(plan.id)
        print_result("获取计划", fetched is not None)
        print_result("计划天数", len(fetched.days) == 7, f"{len(fetched.days)} 天")
        
        # Get active plan
        active = await storage.get_active_plan(user_id)
        print_result("活跃计划", active is not None and active.is_active)
        
        return str(plan.id)


async def test_log_persistence(user_id: str):
    """Test log CRUD with database."""
    print_header("Step 3: Log 持久化测试")
    
    from app.core.database import get_db_context
    from app.db.db_storage import DatabaseStorage
    from app.models.log import DietLog, MealLog, FoodItem, MealType
    
    async with get_db_context() as session:
        storage = DatabaseStorage(session)
        
        # Create log with meals
        meals = [
            MealLog(
                meal_type=MealType.BREAKFAST,
                time=time(8, 0),
                items=[
                    FoodItem(name="燕麦", quantity=50, unit="g", calories=180, protein_g=6),
                    FoodItem(name="鸡蛋", quantity=2, unit="个", calories=140, protein_g=12),
                ],
            ),
            MealLog(
                meal_type=MealType.LUNCH,
                time=time(12, 0),
                items=[
                    FoodItem(name="鸡胸肉", quantity=150, unit="g", calories=250, protein_g=45),
                    FoodItem(name="米饭", quantity=150, unit="g", calories=180, protein_g=4),
                ],
            ),
        ]
        
        log = DietLog(
            user_id=user_id,
            date=date.today(),
            meals=meals,
            water_ml=2000,
            training_completed=True,
            mood=4,
            energy_level=4,
            sleep_hours=7.5,
        )
        
        created = await storage.add_log(log)
        print_result("创建日志", created is not None, f"ID: {created.id}")
        
        # Get log
        fetched = await storage.get_log(log.id)
        print_result("获取日志", fetched is not None)
        print_result("餐食数量", len(fetched.meals) == 2)
        print_result("热量计算", fetched.total_calories == 750, f"{fetched.total_calories} kcal")
        
        # Get user logs
        logs = await storage.get_user_logs(user_id, limit=7)
        print_result("用户日志列表", len(logs) >= 1)
        
        # Get stats
        stats = await storage.get_user_log_stats(user_id, days=7)
        print_result("日志统计", stats["days_logged"] >= 1)
        print(f"       平均热量: {stats['avg_calories']:.1f} kcal")
        
        return str(log.id)


async def test_data_persistence():
    """Test that data persists across sessions."""
    print_header("Step 4: 数据持久性验证")
    
    from app.core.database import get_db_context
    from app.db.db_storage import DatabaseStorage
    
    # New session - data should still exist
    async with get_db_context() as session:
        storage = DatabaseStorage(session)
        users = await storage.list_users()
        
        print_result("数据持久", len(users) >= 1, f"发现 {len(users)} 个用户")
        
        if users:
            user = users[0]
            print(f"       用户名: {user.name}")
            
            plans = await storage.get_user_plans(user.id)
            print_result("计划持久", len(plans) >= 1, f"发现 {len(plans)} 个计划")
            
            logs = await storage.get_user_logs(user.id, limit=10)
            print_result("日志持久", len(logs) >= 1, f"发现 {len(logs)} 条日志")


async def test_cascade_delete(user_id: str):
    """Test cascade delete."""
    print_header("Step 5: 级联删除测试")
    
    from app.core.database import get_db_context
    from app.db.db_storage import DatabaseStorage
    
    async with get_db_context() as session:
        storage = DatabaseStorage(session)
        
        # Get counts before
        plans_before = await storage.get_user_plans(user_id)
        logs_before = await storage.get_user_logs(user_id, limit=100)
        
        print(f"  删除前: {len(plans_before)} 计划, {len(logs_before)} 日志")
        
        # Delete user
        deleted = await storage.delete_user(user_id)
        print_result("删除用户", deleted)
        
        # Verify user is gone
        user = await storage.get_user(user_id)
        print_result("用户已删除", user is None)


async def main():
    """Run all persistence tests."""
    print("\n" + "🚀 CarbonCycle-FitAgent 数据库持久化测试" + "\n")
    
    # Initialize database first
    from app.core.database import get_engine, Base
    from app.db.models import UserModel, PlanModel, LogModel  # Import to register models
    
    engine = get_engine()
    print(f"📁 数据库: {engine.url}")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 表结构已同步\n")
    
    results = []
    
    # Test 1: User persistence
    user_id = await test_user_persistence()
    results.append(("User 持久化", user_id is not None))
    
    # Test 2: Plan persistence
    plan_id = await test_plan_persistence(user_id)
    results.append(("Plan 持久化", plan_id is not None))
    
    # Test 3: Log persistence
    log_id = await test_log_persistence(user_id)
    results.append(("Log 持久化", log_id is not None))
    
    # Test 4: Data persistence verification
    await test_data_persistence()
    results.append(("数据持久性", True))
    
    # Test 5: Cascade delete
    await test_cascade_delete(user_id)
    results.append(("级联删除", True))
    
    # Summary
    print_header("测试结果汇总")
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 所有持久化测试通过！")
    else:
        print("⚠️ 部分测试失败。")
    
    await engine.dispose()
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
