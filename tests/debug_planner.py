"""Debug Planner node."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test():
    print("=== Testing Planner Node ===\n")
    
    from app.agent.nodes.planner import plan_node
    
    test_state = {
        "run_id": "debug_001",
        "trigger": "test",
        "user": {
            "user_id": "test_001",
            "name": "测试用户",
            "goal": "fat_loss",
            "weight_kg": 75,
            "tdee": 2100,
        },
        "plan": {"cycle_length": 7},
        "logs": [],
        "current_date": "2026-02-01",
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
    
    try:
        result = await plan_node(test_state)
        
        planner_output = result.get("planner_output", {})
        print(f"Status: {planner_output.get('status')}")
        print(f"Knowledge used: {planner_output.get('knowledge_used')}")
        print(f"Error: {planner_output.get('error')}")
        
        raw = planner_output.get("raw_response", "")
        print(f"\nResponse length: {len(raw)}")
        print(f"Response preview:\n{raw[:800]}")
        
    except Exception as e:
        import traceback
        print(f"Exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
