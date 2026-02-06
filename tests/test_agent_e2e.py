"""
End-to-end Agent test script.
端到端 Agent 测试脚本

Tests the complete Agent workflow: Planner → Actor → Reflector → Adjuster
测试完整的 Agent 工作流
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Windows console encoding fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def print_header(title: str) -> None:
    """Print section header."""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = "") -> None:
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status} - {name}")
    if message:
        print(f"       {message}")


async def test_rag_knowledge_base() -> bool:
    """Test RAG knowledge base is loaded."""
    print_header("Step 1: RAG 知识库验证")
    
    from app.rag.retriever import retrieve_context
    
    try:
        context = await retrieve_context("碳循环饮食原理", top_k=2)
        
        if context and len(context) > 100:
            print_result("知识库检索", True, f"检索到 {len(context)} 字符知识")
            print(f"\n  Preview: {context[:200]}...")
            return True
        else:
            print_result("知识库检索", False, "知识库为空或检索失败")
            return False
            
    except Exception as e:
        print_result("知识库检索", False, str(e))
        return False


async def test_planner_with_rag() -> dict:
    """Test Planner node with RAG integration."""
    print_header("Step 2: Planner + RAG 集成测试")
    
    from app.agent.nodes.planner import plan_node
    from app.agent.state import AgentState
    
    # Create test user context
    test_state: AgentState = {
        "run_id": "test_e2e_001",
        "trigger": "new_user",
        "user": {
            "user_id": "test_user_001",
            "name": "测试用户",
            "gender": "male",
            "age": 28,
            "height_cm": 175,
            "weight_kg": 78,
            "target_weight_kg": 72,
            "goal": "fat_loss",
            "activity_level": "moderate",
            "training_days": 4,
            "tdee": 2200,
            "dietary_preferences": "无特殊限制",
        },
        "plan": {
            "cycle_length": 7,
        },
        "logs": [],
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "planner_output": None,
        "actor_output": None,
        "reflection": None,
        "adjustment": None,
        "final_output": None,
        "error": None,
        "should_adjust": False,
        "iteration": 0,
        "max_iterations": 10,
        "messages": [],
    }
    
    print(f"  用户: {test_state['user']['name']}")
    print(f"  目标: {test_state['user']['goal']}")
    print(f"  TDEE: {test_state['user']['tdee']} kcal")
    print()
    
    try:
        result = await plan_node(test_state)
        
        planner_output = result.get("planner_output", {})
        status = planner_output.get("status")
        knowledge_used = planner_output.get("knowledge_used", False)
        raw_response = planner_output.get("raw_response", "")
        
        if status == "success" and raw_response:
            print_result("Planner 执行", True, f"生成 {len(raw_response)} 字符响应")
            print_result("RAG 知识注入", knowledge_used, "知识已注入" if knowledge_used else "未使用知识")
            
            # Check if response contains expected structure
            has_json = "```json" in raw_response or '"days"' in raw_response
            print_result("JSON 格式输出", has_json, "包含结构化数据" if has_json else "纯文本响应")
            
            print(f"\n  响应预览:\n  {raw_response[:500]}...")
            
            return {"success": True, "state": {**test_state, **result}}
        else:
            print_result("Planner 执行", False, planner_output.get("error", "未知错误"))
            return {"success": False, "state": test_state}
            
    except Exception as e:
        print_result("Planner 执行", False, str(e))
        return {"success": False, "state": test_state}


async def test_actor_node(state: dict) -> dict:
    """Test Actor node with diet logs."""
    print_header("Step 3: Actor 节点测试")
    
    from app.agent.nodes.actor import act_node
    
    # Add sample diet logs
    state["logs"] = [
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "actual_calories": 2100,
            "actual_protein": 140,
            "actual_carbs": 220,
            "actual_fat": 65,
            "training_completed": True,
            "meal_count": 4,
        }
    ]
    
    print(f"  模拟日志: 热量={state['logs'][0]['actual_calories']}kcal")
    
    try:
        result = await act_node(state)
        
        actor_output = result.get("actor_output", {})
        status = actor_output.get("status")
        
        if status == "success":
            intake = actor_output.get("actual_intake", {})
            print_result("Actor 解析", True, 
                        f"热量={intake.get('calories')}kcal, 蛋白质={intake.get('protein')}g")
            return {"success": True, "state": {**state, **result}}
        else:
            print_result("Actor 解析", False, actor_output.get("summary", "无数据"))
            return {"success": False, "state": state}
            
    except Exception as e:
        print_result("Actor 执行", False, str(e))
        return {"success": False, "state": state}


async def test_reflector_node(state: dict) -> dict:
    """Test Reflector node with trend analysis."""
    print_header("Step 4: Reflector 节点测试 (增强)")
    
    from app.agent.nodes.reflector import reflect_node
    
    # Set plan targets for comparison
    state["plan"] = {
        **state.get("plan", {}),
        "target_calories": 2200,
        "target_protein": 150,
        "target_carbs": 200,
        "target_fat": 70,
        "day_type": "high_carb",
    }
    
    # Add multi-day logs for trend analysis
    state["logs"] = [
        {"date": "2026-01-29", "actual_calories": 2300, "actual_protein": 145, "training_completed": True, "target_calories": 2200, "target_protein": 150},
        {"date": "2026-01-30", "actual_calories": 2250, "actual_protein": 140, "training_completed": True, "target_calories": 2200, "target_protein": 150},
        {"date": "2026-01-31", "actual_calories": 2100, "actual_protein": 135, "training_completed": False, "target_calories": 2200, "target_protein": 150},
        {"date": "2026-02-01", "actual_calories": 2100, "actual_protein": 140, "actual_carbs": 220, "actual_fat": 65, "training_completed": True, "meal_count": 4},
    ]
    
    try:
        result = await reflect_node(state)
        
        reflection = result.get("reflection", {})
        severity = reflection.get("severity", "unknown")
        needs_adjust = reflection.get("needs_adjustment", False)
        
        print_result("Reflector 分析", True, 
                    f"严重程度={severity}, 需要调整={needs_adjust}")
        
        if reflection.get("calorie_deviation_pct") is not None:
            print(f"       热量偏差: {reflection['calorie_deviation_pct']:.1f}%")
        
        # Check new features
        trends = result.get("trends", {})
        if trends:
            print_result("趋势分析", True, 
                        f"方向={trends.get('trend_direction')}, 分析{trends.get('days_analyzed')}天")
        
        summary = result.get("reflection_summary", "")
        if summary:
            print_result("LLM 总结生成", True, f"{len(summary)} 字符")
            print(f"       总结: {summary[:100]}...")
        
        return {"success": True, "state": {**state, **result}}
        
    except Exception as e:
        import traceback
        print_result("Reflector 执行", False, str(e))
        traceback.print_exc()
        return {"success": False, "state": state}


async def test_full_agent_run() -> bool:
    """Test complete agent run with run_agent function."""
    print_header("Step 5: 完整 Agent 流程测试")
    
    from app.agent.graph import run_agent
    
    try:
        result = await run_agent(
            user_id="test_full_001",
            trigger="daily_check",
            user_context={
                "user_id": "test_full_001",
                "name": "完整测试用户",
                "goal": "fat_loss",
                "weight_kg": 75,
                "tdee": 2100,
            },
            plan_context={
                "target_calories": 2000,
                "target_protein": 140,
                "day_type": "medium_carb",
            },
            logs=[
                {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "actual_calories": 1850,
                    "actual_protein": 130,
                    "actual_carbs": 180,
                    "actual_fat": 55,
                    "training_completed": True,
                    "meal_count": 3,
                }
            ],
        )
        
        status = result.get("status")
        run_id = result.get("run_id")
        
        if status == "success":
            print_result("完整流程", True, f"run_id={run_id}")
            
            # Check outputs
            if result.get("planner_output"):
                print_result("Planner 输出", True)
            if result.get("reflection"):
                print_result("Reflector 输出", True)
            if result.get("adjustment"):
                print_result("Adjuster 输出", True)
            
            return True
        else:
            print_result("完整流程", False, result.get("error", "未知错误"))
            return False
            
    except Exception as e:
        print_result("完整流程", False, str(e))
        return False


async def main():
    """Run all E2E tests."""
    print("\n" + "🧪 CarbonCycle-FitAgent E2E 测试" + "\n")
    
    results = []
    
    # Test 1: RAG Knowledge Base
    rag_ok = await test_rag_knowledge_base()
    results.append(("RAG 知识库", rag_ok))
    
    # Test 2: Planner + RAG
    planner_result = await test_planner_with_rag()
    results.append(("Planner + RAG", planner_result["success"]))
    
    # Test 3: Actor
    if planner_result["success"]:
        actor_result = await test_actor_node(planner_result["state"])
        results.append(("Actor 节点", actor_result["success"]))
        
        # Test 4: Reflector
        if actor_result["success"]:
            reflector_result = await test_reflector_node(actor_result["state"])
            results.append(("Reflector 节点", reflector_result["success"]))
    
    # Test 5: Full Agent Run
    full_ok = await test_full_agent_run()
    results.append(("完整 Agent 流程", full_ok))
    
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
        print("🎉 所有 E2E 测试通过！Agent 已就绪。")
    else:
        print("⚠️ 部分测试失败，请检查日志。")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
