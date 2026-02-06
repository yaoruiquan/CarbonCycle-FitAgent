"""Quick verification of Phase 3 Agent enhancements."""
import asyncio
import sys
from pathlib import Path

# Force UTF-8 encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print("Phase 3 Agent Verification")
    print("=" * 50)
    
    # 1. Test Planner + RAG
    print("\n1. Planner + RAG Integration")
    from app.agent.nodes.planner import plan_node
    state = {
        "run_id": "verify_001",
        "trigger": "test",
        "user": {"name": "Test", "goal": "fat_loss", "weight_kg": 75, "tdee": 2100},
        "plan": {"cycle_length": 7},
        "logs": [],
        "messages": [],
    }
    result = await plan_node(state)
    planner_out = result.get("planner_output", {})
    print(f"   Status: {planner_out.get('status')}")
    print(f"   Knowledge used: {planner_out.get('knowledge_used')}")
    print(f"   Response length: {len(planner_out.get('raw_response', ''))}")
    
    # 2. Test Reflector with trends
    print("\n2. Reflector + Trend Analysis")
    from app.agent.nodes.reflector import reflect_node
    state["actor_output"] = {
        "status": "success",
        "actual_intake": {"calories": 2000, "protein": 130},
    }
    state["plan"] = {"target_calories": 2200, "target_protein": 150, "day_type": "high_carb"}
    state["logs"] = [
        {"actual_calories": 2300, "target_calories": 2200, "training_completed": True},
        {"actual_calories": 2250, "target_calories": 2200, "training_completed": True},
        {"actual_calories": 2000, "target_calories": 2200, "training_completed": False},
    ]
    result = await reflect_node(state)
    print(f"   Severity: {result.get('reflection', {}).get('severity')}")
    print(f"   Trend: {result.get('trends', {}).get('trend_direction')}")
    print(f"   Summary available: {bool(result.get('reflection_summary'))}")
    
    # 3. Test Adjuster with RAG
    print("\n3. Adjuster + Smart Suggestions")
    from app.agent.nodes.adjuster import adjust_node
    state["reflection"] = result.get("reflection")
    state["reflection"]["needs_adjustment"] = True
    state["trends"] = result.get("trends")
    result = await adjust_node(state)
    adj = result.get("adjustment", {})
    print(f"   Adjustment type: {adj.get('adjustment_type')}")
    print(f"   Calorie adj: {adj.get('calorie_adjustment')} kcal")
    print(f"   Actions: {len(adj.get('immediate_actions', []))}")
    print(f"   Suggestions: {len(adj.get('behavioral_suggestions', []))}")
    print(f"   Motivation: {result.get('motivation', '')[:50]}...")
    
    print("\n" + "=" * 50)
    print("Phase 3 verification complete!")
    

if __name__ == "__main__":
    asyncio.run(main())
