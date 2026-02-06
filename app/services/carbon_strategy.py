"""
Carbon cycle strategy generation service.
碳循环策略生成服务

Implements the core logic for calculating macros and creating cycle plans.
实现宏量营养素计算和创建循环计划的核心逻辑
"""

from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.models.plan import (
    CarbonCyclePlan,
    DayPlan,
    DayType,
    MacroNutrients,
    PlanCreate,
)
from app.models.user import UserGoal, UserProfile

logger = get_logger(__name__)

# Macro ratio constants by day type (protein%, carbs%, fat%)
MACRO_RATIOS = {
    DayType.HIGH_CARB: {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
    DayType.MEDIUM_CARB: {"protein": 0.30, "carbs": 0.35, "fat": 0.35},
    DayType.LOW_CARB: {"protein": 0.35, "carbs": 0.20, "fat": 0.45},
    DayType.REFEED: {"protein": 0.20, "carbs": 0.60, "fat": 0.20},
}

# Calorie adjustments by day type (relative to TDEE)
CALORIE_ADJUSTMENTS = {
    DayType.HIGH_CARB: 1.10,    # +10% on training days
    DayType.MEDIUM_CARB: 1.00,  # Maintenance
    DayType.LOW_CARB: 0.85,     # -15% on rest days
    DayType.REFEED: 1.20,       # +20% for metabolic boost
}

# Goal-based weekly deficit/surplus
GOAL_CALORIE_OFFSET = {
    UserGoal.FAT_LOSS: -350,       # ~0.3kg/week loss
    UserGoal.MUSCLE_GAIN: 250,     # ~0.2kg/week gain
    UserGoal.MAINTENANCE: 0,
    UserGoal.RECOMPOSITION: -100,  # Slight deficit
}


class CarbonStrategyService:
    """
    Service for generating carbon cycle diet strategies.
    
    Implements TDEE-based macro calculation and cycle planning.
    """
    
    def calculate_day_calories(
        self,
        base_tdee: float,
        day_type: DayType,
        goal: UserGoal,
    ) -> float:
        """
        Calculate target calories for a specific day type.
        
        Args:
            base_tdee: User's total daily energy expenditure.
            day_type: Carbon cycle day category.
            goal: User's fitness goal.
            
        Returns:
            Target calories for the day.
        """
        adjustment = CALORIE_ADJUSTMENTS[day_type]
        goal_offset = GOAL_CALORIE_OFFSET[goal] / 7  # Daily offset
        
        calories = base_tdee * adjustment + goal_offset
        return round(calories, 0)
    
    def calculate_macros(
        self,
        calories: float,
        day_type: DayType,
        weight_kg: float,
    ) -> MacroNutrients:
        """
        Calculate macronutrient targets for a day.
        
        Args:
            calories: Target total calories.
            day_type: Carbon cycle day category.
            weight_kg: User's current weight for protein calculation.
            
        Returns:
            MacroNutrients with gram targets.
        """
        ratios = MACRO_RATIOS[day_type]
        
        # Protein: prioritize by body weight (2g/kg)
        protein_g = weight_kg * 2.0
        protein_calories = protein_g * 4
        
        # Remaining calories for carbs and fat
        remaining_calories = calories - protein_calories
        
        # Adjust ratios for remaining macros
        carb_ratio = ratios["carbs"] / (ratios["carbs"] + ratios["fat"])
        fat_ratio = ratios["fat"] / (ratios["carbs"] + ratios["fat"])
        
        carbs_g = (remaining_calories * carb_ratio) / 4
        fat_g = (remaining_calories * fat_ratio) / 9
        
        # Ensure minimum fat intake (0.8g/kg)
        min_fat = weight_kg * 0.8
        if fat_g < min_fat:
            fat_g = min_fat
            fat_calories = fat_g * 9
            carbs_g = (remaining_calories - fat_calories) / 4
        
        return MacroNutrients(
            protein_g=round(protein_g, 1),
            carbs_g=round(max(carbs_g, 50), 1),  # Minimum 50g carbs
            fat_g=round(fat_g, 1),
            fiber_g=round(calories / 80, 1),  # ~12.5g per 1000kcal
        )
    
    def determine_day_sequence(
        self,
        training_days: int,
        cycle_length: int,
        goal: UserGoal,
    ) -> list[DayType]:
        """
        Determine the sequence of day types for a cycle.
        
        Args:
            training_days: Number of training days per week.
            cycle_length: Length of the cycle in days.
            goal: User's fitness goal.
            
        Returns:
            List of DayType for each day in the cycle.
        """
        sequence = []
        
        # Base distribution
        high_carb_count = training_days
        low_carb_count = cycle_length - training_days
        
        # Adjust for goal
        if goal == UserGoal.FAT_LOSS:
            # More low carb days
            medium_count = min(2, high_carb_count)
            high_carb_count = max(1, training_days - medium_count)
        elif goal == UserGoal.MUSCLE_GAIN:
            # More high carb days
            medium_count = 0
            high_carb_count = training_days
        else:
            medium_count = max(1, training_days // 2)
            high_carb_count = training_days - medium_count
        
        low_carb_count = cycle_length - high_carb_count - medium_count
        
        # Build sequence (training days first, then rest)
        sequence.extend([DayType.HIGH_CARB] * high_carb_count)
        sequence.extend([DayType.MEDIUM_CARB] * medium_count)
        sequence.extend([DayType.LOW_CARB] * low_carb_count)
        
        return sequence
    
    async def generate_plan(
        self,
        user: UserProfile,
        request: PlanCreate,
        use_agent: bool = True,
    ) -> CarbonCyclePlan:
        """
        Generate a complete carbon cycle plan.
        
        Args:
            user: User profile with physical stats and goals.
            request: Plan creation request with parameters.
            use_agent: Whether to use AI agent for enrichment.
            
        Returns:
            Complete CarbonCyclePlan with daily targets.
        """
        base_tdee = user.calculate_tdee()
        total_days = request.cycle_length_days * request.num_cycles
        end_date = request.start_date + timedelta(days=total_days - 1)
        
        # Get day type sequence for one cycle
        day_sequence = self.determine_day_sequence(
            training_days=user.training_days_per_week,
            cycle_length=request.cycle_length_days,
            goal=user.goal,
        )
        
        # Generate daily plans
        days: list[DayPlan] = []
        current_date = request.start_date
        
        for cycle in range(request.num_cycles):
            for day_idx, day_type in enumerate(day_sequence):
                calories = self.calculate_day_calories(
                    base_tdee=base_tdee,
                    day_type=day_type,
                    goal=user.goal,
                )
                
                macros = self.calculate_macros(
                    calories=calories,
                    day_type=day_type,
                    weight_kg=user.weight_kg,
                )
                
                # Training on high/medium carb days
                training_scheduled = day_type in (DayType.HIGH_CARB, DayType.MEDIUM_CARB)
                # Placeholder, will be enriched by Agent
                training_type = "力量训练" if training_scheduled else "休息/恢复"
                
                day_plan = DayPlan(
                    date=current_date,
                    day_type=day_type,
                    macros=macros,
                    training_scheduled=training_scheduled,
                    training_type=training_type,
                )
                days.append(day_plan)
                current_date += timedelta(days=1)
        
        plan = CarbonCyclePlan(
            user_id=request.user_id,
            name=request.name,
            start_date=request.start_date,
            end_date=end_date,
            cycle_length_days=request.cycle_length_days,
            days=days,
            base_calories=base_tdee,
            goal_deficit=GOAL_CALORIE_OFFSET[user.goal],
        )
        
        # AI Enrichment
        if use_agent:
            try:
                from app.services.plan_enrichment import PlanEnrichmentService
                enrichment_service = PlanEnrichmentService()
                plan = await enrichment_service.enrich_plan(plan, user)
            except Exception as e:
                logger.error(f"Plan enrichment failed: {e}")
                # Continue with base plan if agent fails
        
        logger.info(
            f"Generated plan for user {user.id}: "
            f"{len(days)} days, avg {plan.average_daily_calories}kcal"
        )
        
        return plan
    
    def adjust_plan(
        self,
        plan: CarbonCyclePlan,
        calorie_adjustment: float,
        start_from: Optional[date] = None,
    ) -> CarbonCyclePlan:
        """
        Adjust an existing plan's calorie targets.
        
        Args:
            plan: Existing plan to adjust.
            calorie_adjustment: Calories to add/subtract per day.
            start_from: Date to start adjustments (default: today).
            
        Returns:
            Adjusted plan.
        """
        start_from = start_from or date.today()
        
        for day in plan.days:
            if day.date >= start_from:
                new_calories = day.target_calories + calorie_adjustment
                
                # Recalculate macros for new calorie target
                new_macros = MacroNutrients(
                    protein_g=day.macros.protein_g,  # Keep protein stable
                    carbs_g=day.macros.carbs_g + (calorie_adjustment * 0.5 / 4),
                    fat_g=day.macros.fat_g + (calorie_adjustment * 0.5 / 9),
                    fiber_g=day.macros.fiber_g,
                )
                day.macros = new_macros
        
        logger.info(f"Adjusted plan {plan.id} by {calorie_adjustment}kcal/day")
        return plan
    
    async def generate_plan_with_agent(
        self,
        user: UserProfile,
        request: PlanCreate,
    ) -> CarbonCyclePlan:
        """
        Generate a carbon cycle plan with Agent enhancement.
        使用 Agent 增强的计划生成
        
        Calls the Agent's Planner node to get personalized suggestions
        based on RAG knowledge retrieval.
        调用 Agent 的 Planner 节点，基于 RAG 知识检索获取个性化建议
        
        Args:
            user: User profile with physical stats and goals.
            request: Plan creation request with parameters.
            
        Returns:
            Complete CarbonCyclePlan with AI-generated notes.
        """
        # Step 1: Generate base plan using rules (no enrichment yet)
        base_plan = await self.generate_plan(user, request, use_agent=False)
        
        # Step 2: Call Agent with create_plan trigger
        try:
            from app.agent import run_agent
            
            user_context = {
                "user_id": str(user.id),
                "name": user.name,
                "goal": user.goal.value if hasattr(user.goal, "value") else str(user.goal),
                "weight_kg": user.weight_kg,
                "height_cm": user.height_cm,
                "tdee": user.calculate_tdee(),
                "age": user.calculate_age(),
                "gender": user.gender.value if hasattr(user.gender, "value") else str(user.gender),
                "activity_level": user.activity_level.value if hasattr(user.activity_level, "value") else str(user.activity_level),
                "training_days": user.training_days_per_week,
            }
            
            plan_context = {
                "plan_id": str(base_plan.id),
                "start_date": str(base_plan.start_date),
                "cycle_length": request.cycle_length_days,
                "num_cycles": request.num_cycles,
                "base_calories": base_plan.base_calories,
                "day_count": len(base_plan.days),
            }
            
            logger.info(f"Calling Agent with trigger=create_plan for user {user.id}")
            
            result = await run_agent(
                user_id=str(user.id),
                trigger="create_plan",
                user_context=user_context,
                plan_context=plan_context,
                logs=[],  # No historical logs for new plan
            )
            
            # Step 3: Extract Planner output and merge into plan
            if result.get("status") == "success":
                planner_output = result.get("planner_output", {})
                raw_response = planner_output.get("raw_response", "")
                
                if raw_response:
                    base_plan.notes = f"## AI 建议\n\n{raw_response}"
                    logger.info(f"Agent enriched plan with {len(raw_response)} chars of suggestions")
                else:
                    logger.warning("Agent returned success but no raw_response")
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"Agent returned non-success status: {error_msg}")
                # Continue with base plan if agent fails
                
        except Exception as e:
            logger.error(f"Agent call failed: {e}")
            # Continue with base plan if agent call fails
        
        # Step 4: Use enrichment service for detailed day descriptions
        try:
            from app.services.plan_enrichment import PlanEnrichmentService
            enrichment_service = PlanEnrichmentService()
            base_plan = await enrichment_service.enrich_plan(base_plan, user)
        except Exception as e:
            logger.error(f"Plan enrichment failed: {e}")
        
        return base_plan
