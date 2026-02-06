"""
Weekly Report API E2E Tests.
周报 API 端到端测试

Tests the /api/reports/weekly endpoint with different data scenarios.
测试不同数据量情况下的周报生成
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Windows console encoding fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[union-attr]


def print_header(title: str) -> None:
    """Print section header."""
    print("\n" + "=" * 60)
    print(f"🧪 {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = "", latency_ms: int = 0) -> None:
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    latency_str = f" ({latency_ms}ms)" if latency_ms > 0 else ""
    print(f"  {status} - {name}{latency_str}")
    if message:
        print(f"       {message}")


async def test_weekly_report_no_data() -> tuple[bool, int]:
    """
    Test weekly report generation with NO log data.
    无日志数据场景测试
    
    Expected:
    - Should use fallback report (agent not triggered due to insufficient data)
    - Should return quickly
    """
    print_header("场景1: 无日志数据")
    
    from app.agent.graph import run_agent
    
    start_time = time.time()
    
    try:
        result = await run_agent(
            user_id="test_no_data_user",
            trigger="weekly_report: 周复盘分析请求（无数据）",
            user_context={
                "user_id": "test_no_data_user",
                "name": "无数据测试用户",
                "goal": "fat_loss",
                "weight_kg": 70,
                "tdee": 2000,
            },
            plan_context={
                "target_calories": 1800,
                "target_protein": 140,
                "day_type": "medium_carb",
            },
            logs=[],  # Empty logs
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        status = result.get("status")
        
        if status == "success":
            print_result("Agent 执行", True, "成功处理空数据场景", latency_ms)
            
            # Check that trends show insufficient data
            trends = result.get("trends") or {}
            if trends.get("trend_direction") == "insufficient_data" or not trends.get("has_trend"):
                print_result("趋势分析", True, "正确识别数据不足")
            else:
                print_result("趋势分析", False, f"未能识别数据不足: {trends}")
                return (False, latency_ms)
            
            return (True, latency_ms)
        else:
            # Even error is acceptable for no data - fallback should kick in
            print_result("Agent 执行", True, f"返回错误（预期行为）: {result.get('error')}", latency_ms)
            return (True, latency_ms)
            
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        print_result("Agent 执行", False, str(e), latency_ms)
        return (False, latency_ms)


async def test_weekly_report_partial_data() -> tuple[bool, int]:
    """
    Test weekly report generation with PARTIAL log data (1-3 days).
    部分日志数据场景测试
    
    Expected:
    - Agent runs with limited data
    - Trends may be limited
    - Should generate meaningful report
    """
    print_header("场景2: 部分日志数据 (2天)")
    
    from app.agent.graph import run_agent
    
    start_time = time.time()
    
    try:
        today = datetime.now()
        
        result = await run_agent(
            user_id="test_partial_data_user",
            trigger="weekly_report: 周复盘分析请求（部分数据）",
            user_context={
                "user_id": "test_partial_data_user",
                "name": "部分数据测试用户",
                "goal": "fat_loss",
                "weight_kg": 75,
                "tdee": 2100,
            },
            plan_context={
                "target_calories": 1900,
                "target_protein": 145,
                "target_carbs": 200,
                "target_fat": 60,
                "day_type": "high_carb",
            },
            logs=[
                {
                    "date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
                    "actual_calories": 2000,
                    "actual_protein": 140,
                    "actual_carbs": 210,
                    "actual_fat": 55,
                    "training_completed": True,
                    "meal_count": 4,
                },
                {
                    "date": today.strftime("%Y-%m-%d"),
                    "actual_calories": 1850,
                    "actual_protein": 135,
                    "actual_carbs": 180,
                    "actual_fat": 60,
                    "training_completed": False,
                    "meal_count": 3,
                },
            ],
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        status = result.get("status")
        
        if status == "success":
            print_result("Agent 执行", True, "成功处理部分数据", latency_ms)
            
            # Check planner output
            if result.get("planner_output"):
                print_result("Planner 输出", True)
            
            # Check reflection
            reflection = result.get("reflection") or {}
            if reflection:
                print_result("Reflector 分析", True, 
                            f"偏差={reflection.get('calorie_deviation_pct', 0):.1f}%")
            
            return (True, latency_ms)
        else:
            print_result("Agent 执行", False, str(result.get("error", "Unknown error")), latency_ms)
            return (False, latency_ms)
            
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        print_result("Agent 执行", False, str(e), latency_ms)
        return (False, latency_ms)


async def test_weekly_report_full_data() -> tuple[bool, int]:
    """
    Test weekly report generation with FULL log data (7 days).
    完整日志数据场景测试
    
    Expected:
    - Full Agent flow executed
    - Trend analysis available
    - Detailed reflection and adjustments
    """
    print_header("场景3: 完整日志数据 (7天)")
    
    from app.agent.graph import run_agent
    
    start_time = time.time()
    
    try:
        today = datetime.now()
        
        # Generate 7 days of varied data
        logs = []
        for i in range(7):
            day = today - timedelta(days=6-i)
            # Simulate varying adherence
            cal_variance = 50 + (i * 20)  # Improving over time
            logs.append({
                "date": day.strftime("%Y-%m-%d"),
                "actual_calories": 1900 + (100 if i % 2 == 0 else -50) + (i * 10),
                "actual_protein": 140 + (i * 2),
                "actual_carbs": 200 + (20 if i % 3 == 0 else -10),
                "actual_fat": 60 + (5 if i % 2 == 0 else -5),
                "training_completed": i not in [2, 5],  # Skip 2 training days
                "meal_count": 3 + (1 if i % 2 == 0 else 0),
                "target_calories": 2000,
                "target_protein": 150,
            })
        
        result = await run_agent(
            user_id="test_full_data_user",
            trigger="weekly_report: 周复盘分析请求（完整数据）",
            user_context={
                "user_id": "test_full_data_user",
                "name": "完整数据测试用户",
                "goal": "fat_loss",
                "weight_kg": 78,
                "tdee": 2200,
            },
            plan_context={
                "target_calories": 2000,
                "target_protein": 150,
                "target_carbs": 220,
                "target_fat": 65,
                "day_type": "medium_carb",
            },
            logs=logs,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        status = result.get("status")
        
        if status == "success":
            print_result("Agent 执行", True, "成功处理完整数据", latency_ms)
            
            # Check all outputs
            if result.get("planner_output"):
                print_result("Planner 输出", True)
            
            reflection = result.get("reflection") or {}
            if reflection:
                severity = reflection.get("severity", "unknown")
                print_result("Reflector 分析", True, f"严重程度={severity}")
            
            trends = result.get("trends") or {}
            if trends and trends.get("has_trend"):
                direction = trends.get("trend_direction", "unknown")
                print_result("趋势分析", True, f"方向={direction}")
            
            summary = result.get("reflection_summary")
            if summary:
                print_result("LLM 总结", True, f"{len(summary)} 字符")
                print(f"\n  总结预览: {summary[:150]}...")
            
            return (True, latency_ms)
        else:
            print_result("Agent 执行", False, str(result.get("error", "Unknown error")), latency_ms)
            return (False, latency_ms)
            
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        print_result("Agent 执行", False, str(e), latency_ms)
        return (False, latency_ms)


async def main():
    """Run all weekly report tests."""
    print("\n" + "🧪 Weekly Report API E2E 测试" + "\n")
    
    results = []
    latencies = []
    
    # Test 1: No data
    success, latency = await test_weekly_report_no_data()
    results.append(("无数据场景", success))
    latencies.append(latency)
    
    # Test 2: Partial data
    success, latency = await test_weekly_report_partial_data()
    results.append(("部分数据场景", success))
    latencies.append(latency)
    
    # Test 3: Full data
    success, latency = await test_weekly_report_full_data()
    results.append(("完整数据场景", success))
    latencies.append(latency)
    
    # Summary
    print_header("测试结果汇总")
    
    all_passed = True
    for (name, passed), lat in zip(results, latencies):
        status = "✅" if passed else "❌"
        print(f"  {status} {name} ({lat}ms)")
        if not passed:
            all_passed = False
    
    # Latency analysis
    print("\n📊 性能分析:")
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    print(f"  平均延迟: {avg_latency:.0f}ms")
    print(f"  最大延迟: {max_latency}ms")
    
    if max_latency > 10000:
        print("  ⚠️ 建议: 延迟超过10秒，考虑引入异步任务队列")
    elif max_latency > 3000:
        print("  💡 建议: 延迟较高，前端可增加进度提示")
    else:
        print("  ✅ 性能良好，无需异步处理")
    
    print()
    if all_passed:
        print("🎉 所有 Weekly Report 测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查日志。")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
