
import asyncio
import os
import sys
from datetime import date
from uuid import uuid4

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.plan_enrichment import PlanEnrichmentService
from app.models.plan import CarbonCyclePlan, DayPlan, DayType, MacroNutrients
from app.models.user import UserProfile, Gender, UserGoal, ActivityLevel

async def test_enrichment():
    """
    Test PlanEnrichmentService with LLM.
    """
    print("🚀 Starting Plan Enrichment Test...")
    print("-" * 50)
    
    # 1. Mock User
    user = UserProfile(
        id=uuid4(),
        email="test@example.com",
        name="Test Athlete",
        hashed_password="mock_password_hash",
        gender=Gender.MALE,
        birth_date=date(1995, 1, 1),
        height_cm=180,
        weight_kg=80,
        target_weight_kg=75,
        goal=UserGoal.FAT_LOSS,
        activity_level=ActivityLevel.MODERATE,
        training_days_per_week=4
    )
    
    # 2. Mock Plan (1 Day)
    day = DayPlan(
        date=date.today(),
        day_type=DayType.HIGH_CARB,
        macros=MacroNutrients(protein_g=160, carbs_g=300, fat_g=60),
        training_scheduled=True,
        training_type="力量训练 (Placeholder)",  # This should be replaced
        notes="碳水集中在训练后 (Placeholder)"      # This should be replaced
    )
    
    plan = CarbonCyclePlan(
        user_id=user.id,
        start_date=date.today(),
        end_date=date.today(),
        days=[day],
        base_calories=2500,
        goal_deficit=-300
    )
    
    print(f"Original Training: {day.training_type}")
    print(f"Original Notes: {day.notes}")
    
    # 3. Run Enrichment
    print("\n🔮 Calling LLM for enrichment...")
    
    service = PlanEnrichmentService()
    try:
        enriched_plan = await service.enrich_plan(plan, user)
        
        enriched_day = enriched_plan.days[0]
        print("-" * 50)
        print("✅ Enrichment Complete!")
        print(f"New Training: {enriched_day.training_type}")
        print(f"New Notes: {enriched_day.notes}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_enrichment())
