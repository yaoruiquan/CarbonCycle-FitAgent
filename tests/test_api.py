"""
API integration tests.
API 集成测试

Tests the complete API workflow: User → Plan → Log → Agent
测试完整的 API 工作流
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

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


async def test_user_api():
    """Test User API endpoints."""
    print_header("Step 1: User API 测试")
    
    from app.api.storage import get_storage
    from app.models.user import UserCreate, UserProfile, UserUpdate, Gender, UserGoal, ActivityLevel
    from app.api.user import create_user, get_user, list_users, update_user, delete_user
    
    # Clear storage
    storage = get_storage()
    storage.clear_all()
    
    # Create user
    user_data = UserCreate(
        name="测试用户",
        gender=Gender.MALE,
        birth_date=date(1996, 5, 15),
        height_cm=175,
        weight_kg=78,
        target_weight_kg=72,
        goal=UserGoal.FAT_LOSS,
        activity_level=ActivityLevel.MODERATE,
        training_days_per_week=4,
    )
    
    user = await create_user(user_data)
    print_result("创建用户", user is not None, f"ID: {user.id}")
    print(f"       TDEE: {user.calculate_tdee()} kcal")
    
    # Get user
    fetched = await get_user(user.id)
    print_result("获取用户", fetched.name == "测试用户")
    
    # Update user
    updated = await update_user(user.id, UserUpdate(weight_kg=77))
    print_result("更新用户", updated.weight_kg == 77)
    
    # List users
    users = await list_users()
    print_result("列出用户", len(users) == 1)
    
    return user.id


async def test_plan_api(user_id: UUID):
    """Test Plan API endpoints."""
    print_header("Step 2: Plan API 测试")
    
    from app.models.plan import PlanCreate
    from app.api.plan import create_plan, get_plan, get_user_plans, get_active_plan
    
    # Create plan
    plan_data = PlanCreate(
        user_id=user_id,
        name="测试碳循环计划",
        start_date=date.today(),
        cycle_length_days=7,
        num_cycles=1,
    )
    
    plan = await create_plan(plan_data)
    print_result("创建计划", plan is not None, f"ID: {plan.id}")
    print_result("计划天数", len(plan.days) == 7, f"{len(plan.days)} 天")
    
    # Get plan
    fetched = await get_plan(plan.id)
    print_result("获取计划", fetched.id == plan.id)
    
    # Get user plans
    plans = await get_user_plans(user_id)
    print_result("用户计划列表", len(plans) == 1)
    
    # Get active plan
    active = await get_active_plan(user_id)
    print_result("活跃计划", active.is_active)
    
    return plan.id


async def test_log_api(user_id: UUID):
    """Test Log API endpoints."""
    print_header("Step 3: Log API 测试")
    
    from datetime import time
    from app.models.log import LogCreate, MealLog, FoodItem, MealType
    from app.api.log import create_log, get_user_logs, get_user_log_stats
    
    # Create multiple logs
    for i in range(3):
        # Create meal data with FoodItem
        meals = [
            MealLog(
                meal_type=MealType.BREAKFAST,
                time=time(8, 0),
                items=[
                    FoodItem(name="燕麦", quantity=50, unit="g", calories=180, protein_g=6, carbs_g=30, fat_g=3),
                    FoodItem(name="鸡蛋", quantity=2, unit="个", calories=140, protein_g=12, carbs_g=1, fat_g=10),
                ],
            ),
            MealLog(
                meal_type=MealType.LUNCH,
                time=time(12, 0),
                items=[
                    FoodItem(name="鸡胸肉", quantity=150, unit="g", calories=250, protein_g=45, carbs_g=0, fat_g=5),
                    FoodItem(name="米饭", quantity=150, unit="g", calories=180, protein_g=4, carbs_g=40, fat_g=0),
                    FoodItem(name="蔬菜", quantity=200, unit="g", calories=50, protein_g=2, carbs_g=8, fat_g=0),
                ],
            ),
            MealLog(
                meal_type=MealType.DINNER,
                time=time(18, 0),
                items=[
                    FoodItem(name="三文鱼", quantity=150, unit="g", calories=300, protein_g=35, carbs_g=0, fat_g=18),
                    FoodItem(name="红薯", quantity=150, unit="g", calories=130, protein_g=2, carbs_g=30, fat_g=0),
                ],
            ),
        ]
        
        log_data = LogCreate(
            user_id=user_id,
            date=date.today() - timedelta(days=i),
            meals=meals,
            water_ml=2000,
            training_completed=(i % 2 == 0),
            mood=4,
            energy_level=4,
            sleep_hours=7.5,
        )
        log = await create_log(log_data)
        print_result(f"创建日志 Day-{i}", log is not None)
    
    # Get user logs
    logs = await get_user_logs(user_id, limit=7)
    print_result("获取日志列表", len(logs) == 3)
    
    # Get log stats
    stats = await get_user_log_stats(user_id, days=7)
    print_result("日志统计", stats.days_logged == 3)
    print(f"       平均热量: {stats.avg_calories:.1f} kcal")
    print(f"       训练完成率: {stats.training_completion_rate:.1f}%")


async def test_agent_api(user_id: UUID):
    """Test Agent API endpoints."""
    print_header("Step 4: Agent API 测试")
    
    from app.api.agent import AgentTriggerRequest, run_agent_sync
    
    request = AgentTriggerRequest(user_id=user_id, trigger="api_test")
    
    try:
        result = await run_agent_sync(request)
        
        print_result("Agent 执行", result.status == "success", f"run_id: {result.run_id}")
        print_result("Planner 输出", result.planner_output is not None)
        
        if result.reflection:
            print_result("Reflection 输出", True, 
                        f"severity: {result.reflection.get('severity')}")
        
        if result.motivation:
            print(f"       激励: {result.motivation[:40]}...")
        
        return True
        
    except Exception as e:
        import traceback
        print_result("Agent 执行", False, str(e))
        traceback.print_exc()
        return False


async def test_delete_operations(user_id: UUID):
    """Test DELETE endpoints."""
    print_header("Step 5: DELETE 操作测试")
    
    from app.api.user import delete_user
    from app.api.storage import get_storage
    
    storage = get_storage()
    
    # Check data exists before delete
    logs_before = len(list(storage._logs.values()))
    plans_before = len(list(storage._plans.values()))
    
    print(f"  删除前: {logs_before} 日志, {plans_before} 计划")
    
    # Delete user (should cascade)
    await delete_user(user_id)
    
    # Check data is deleted
    users_after = len(storage.list_users())
    logs_after = len(list(storage._logs.values()))
    
    print_result("删除用户", users_after == 0)
    print_result("级联删除日志", logs_after == 0)


async def main():
    """Run all API tests."""
    print("\n" + "🚀 CarbonCycle-FitAgent API 测试" + "\n")
    
    results = []
    
    # Test 1: User API
    user_id = await test_user_api()
    results.append(("User API", user_id is not None))
    
    # Test 2: Plan API
    plan_id = await test_plan_api(user_id)
    results.append(("Plan API", plan_id is not None))
    
    # Test 3: Log API
    await test_log_api(user_id)
    results.append(("Log API", True))
    
    # Test 4: Agent API
    agent_ok = await test_agent_api(user_id)
    results.append(("Agent API", agent_ok))
    
    # Test 5: Delete operations
    await test_delete_operations(user_id)
    results.append(("Delete API", True))
    
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
        print("🎉 所有 API 测试通过！")
    else:
        print("⚠️ 部分测试失败。")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
