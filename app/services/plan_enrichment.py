"""
Plan Enrichment Service.
计划增强服务

Uses LLM to generate personalized training and diet details for calculated plans.
使用 LLM 为计算好的计划生成个性化的训练和饮食详情。
"""

import asyncio
import json
from datetime import date
from typing import Optional

from app.core.logging import get_logger
from app.llm.client import get_llm_client, ModelType
from app.models.plan import CarbonCyclePlan, DayPlan, DayType, MacroNutrients
from app.models.user import UserProfile, UserGoal

logger = get_logger(__name__)


class PlanEnrichmentService:
    """
    Enriches algorithmic plans with AI-generated content.
    """
    
    def __init__(self):
        self.llm = get_llm_client()
        
    async def enrich_plan(self, plan: CarbonCyclePlan, user: UserProfile) -> CarbonCyclePlan:
        """
        Enrich all days in the plan with description text.
        
        Args:
            plan: The base plan with calculated numbers.
            user: User profile for personalization.
            
        Returns:
            The plan with populated training_type and notes.
        """
        logger.info(f"Enriching plan {plan.id} for user {user.name}")
        
        # Prepare tasks for all days
        tasks = [
            self._enrich_day(day, user)
            for day in plan.days
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update plan days
        enriched_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to enrich day {plan.days[i].date}: {result}")
                # Fallback to default descriptions if LLM fails
                self._apply_fallback(plan.days[i])
            else:
                enriched_count += 1
                
        logger.info(f"Successfully enriched {enriched_count}/{len(plan.days)} days")
        return plan

    async def _enrich_day(self, day: DayPlan, user: UserProfile) -> DayPlan:
        """Generate content for a single day."""
        
        # Prompt Engineering
        # We need structured output mostly, but for now we'll parse simple text or use JSON mode if supported.
        # Let's simple format: return JSON.
        
        goal_text = {
            "fat_loss": "减脂",
            "muscle_gain": "增肌",
            "maintenance": "保持",
            "recomposition": "身体重组"
        }.get(str(user.goal), str(user.goal))
        
        day_type_text = {
            "high_carb": "高碳日 (训练日)",
            "medium_carb": "中碳日 (轻量训练)",
            "low_carb": "低碳日 (休息/有氧)",
            "refeed": "欺骗餐日"
        }.get(str(day.day_type), str(day.day_type))
        
        prompt = f"""
        你是一位专业的碳循环饮食教练。请为学员生成今天的【训练动作摘要】和【推荐食谱】。
        
        【学员档案】
        姓名: {user.name}
        目标: {goal_text}
        体重: {user.weight_kg}kg
        性别: {"男" if str(user.gender) == "male" else "女"}
        训练偏好: {user.training_days_per_week}练/周
        
        【今日数值】
        日期类型: {day_type_text}
        热量目标: {int(day.target_calories)} kcal
        宏量目标: 碳水 {int(day.macros.carbs_g)}g | 蛋白质 {int(day.macros.protein_g)}g | 脂肪 {int(day.macros.fat_g)}g
        需要训练: {"是" if day.training_scheduled else "否"}
        
        【要求】
        请直接以JSON格式返回，不要包含Markdown代码块，格式如下：
        {{
            "training": "一句话概括训练内容（例如：腿部重训：深蹲5x5...）",
            "diet": "一句话推荐食谱（例如：午餐红薯鸡胸肉，晚餐...）"
        }}
        内容必须简练（每项不超过50字），语气专业且鼓励。
        """
        
        try:
            response = await self.llm.generate_text(
                prompt=prompt,
                temperature=0.7,
                system_prompt="你是一个输出JSON的健身助手。"
            )
            
            # Clean up response (in case of markdown code blocks)
            cleaned_response = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_response)
            
            day.training_type = data.get("training", day.training_type)
            day.notes = data.get("diet", day.notes)
            
        except Exception as e:
            logger.error(f"LLM generation failed for day {day.date}: {e}")
            self._apply_fallback(day)
            
        return day

    def _apply_fallback(self, day: DayPlan):
        """Apply static fallback text if LLM fails."""
        if day.day_type == DayType.HIGH_CARB:
            day.training_type = "建议：在大肌群训练（腿/背）后安排高碳饮食"
            day.notes = "重点：碳水集中在训练前后摄入，早餐吃好"
        elif day.day_type == DayType.LOW_CARB:
            day.training_type = "建议：主动恢复，做瑜伽或慢走"
            day.notes = "重点：全天控碳，多吃绿叶蔬菜和优质脂肪"
        else:
            day.training_type = "建议：进行适度有氧或手臂/肩部训练"
            day.notes = "重点：保持血糖平稳，少食多餐"
