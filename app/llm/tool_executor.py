"""
Tool executor for agent function calling.
Agent 工具执行器

Implements the execution logic for each tool defined in tools.py.
实现 tools.py 中定义的每个工具的执行逻辑
"""

import json
import re
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.db_storage import DatabaseStorage
from app.llm.client import get_llm_client
from app.llm.tools import (
    TOOL_CALCULATE_MACROS,
    TOOL_QUERY_FOOD,
    TOOL_ANALYZE_DEVIATION,
    TOOL_GET_USER_HISTORY,
    TOOL_SUGGEST_ADJUSTMENT,
)

logger = get_logger(__name__)


class ToolExecutor:
    """
    Executes agent tools by dispatching to service layer.
    通过分派到服务层来执行 Agent 工具

    Each tool maps to an existing service or LLM call.
    每个工具映射到现有服务或 LLM 调用
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = DatabaseStorage(db)
        self._dispatch = {
            TOOL_CALCULATE_MACROS: self._execute_calculate_macros,
            TOOL_QUERY_FOOD: self._execute_query_food,
            TOOL_ANALYZE_DEVIATION: self._execute_analyze_deviation,
            TOOL_GET_USER_HISTORY: self._execute_get_user_history,
            TOOL_SUGGEST_ADJUSTMENT: self._execute_suggest_adjustment,
        }

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        Execute a tool by name and return JSON string result.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments as a dict.

        Returns:
            JSON-encoded result string.
        """
        handler = self._dispatch.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)

        try:
            result = await handler(arguments)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return json.dumps(
                {"error": f"Tool execution failed: {str(e)}"},
                ensure_ascii=False,
            )

    # ============ Tool Implementations ============

    async def _execute_calculate_macros(self, args: dict[str, Any]) -> dict:
        """
        Calculate macros based on user profile, goal, and day type.
        根据碳循环日类型计算宏量营养素分配
        """
        user_id = args["user_id"]
        day_type = args["day_type"]
        target_calories = float(args["target_calories"])

        # Macro ratios by day type (protein/carbs/fat percentages)
        MACRO_RATIOS = {
            "high_carb": {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
            "medium_carb": {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
            "low_carb": {"protein": 0.40, "carbs": 0.20, "fat": 0.40},
            "refeed": {"protein": 0.20, "carbs": 0.55, "fat": 0.25},
        }

        ratios = MACRO_RATIOS.get(day_type, MACRO_RATIOS["medium_carb"])

        # protein/carbs: 4 kcal/g, fat: 9 kcal/g
        protein_g = round(target_calories * ratios["protein"] / 4, 1)
        carbs_g = round(target_calories * ratios["carbs"] / 4, 1)
        fat_g = round(target_calories * ratios["fat"] / 9, 1)

        # Fetch user for context
        user = await self.storage.get_user(user_id)
        user_weight = user.weight_kg if user else 70

        return {
            "day_type": day_type,
            "target_calories": target_calories,
            "macros": {
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
            },
            "ratios": ratios,
            "protein_per_kg": round(protein_g / user_weight, 2) if user_weight else None,
            "note": f"{day_type} 日宏量分配完成",
        }

    async def _execute_query_food(self, args: dict[str, Any]) -> dict:
        """
        Query nutrition info for a food item via LLM estimation.
        通过 LLM 估算食物营养信息
        """
        food_name = args["food_name"]
        quantity_g = float(args.get("quantity_g", 100))

        llm = get_llm_client()

        prompt = f"""作为营养师，请估算以下食物的宏量营养素：

食物名称：{food_name}
重量：{quantity_g}克

请以JSON格式返回：
{{
    "carbs_g": <碳水化合物克数>,
    "protein_g": <蛋白质克数>,
    "fat_g": <脂肪克数>,
    "fiber_g": <膳食纤维克数>
}}

只返回JSON，不要有其他文字"""

        try:
            response = await llm.chat([{"role": "user", "content": prompt}])
            response_text = response.get("content", "") or ""

            json_match = re.search(r"\{[^}]+\}", response_text, re.DOTALL)
            if json_match:
                nutrition = json.loads(json_match.group())
                carbs_g = float(nutrition.get("carbs_g", 0))
                protein_g = float(nutrition.get("protein_g", 0))
                fat_g = float(nutrition.get("fat_g", 0))
                fiber_g = float(nutrition.get("fiber_g", 0))
            else:
                # Fallback
                carbs_g = quantity_g * 0.15
                protein_g = quantity_g * 0.10
                fat_g = quantity_g * 0.05
                fiber_g = quantity_g * 0.02
        except Exception as e:
            logger.warning(f"LLM food query failed: {e}")
            carbs_g = quantity_g * 0.15
            protein_g = quantity_g * 0.10
            fat_g = quantity_g * 0.05
            fiber_g = quantity_g * 0.02

        calories = carbs_g * 4 + protein_g * 4 + fat_g * 9

        return {
            "food_name": food_name,
            "quantity_g": quantity_g,
            "calories": round(calories, 1),
            "protein_g": round(protein_g, 1),
            "carbs_g": round(carbs_g, 1),
            "fat_g": round(fat_g, 1),
            "fiber_g": round(fiber_g, 1),
        }

    async def _execute_analyze_deviation(self, args: dict[str, Any]) -> dict:
        """
        Analyze deviation between planned and actual intake for a given day.
        分析某日计划与实际摄入之间的偏差
        """
        from app.services.execution_analysis import ExecutionAnalysisService

        user_id = args["user_id"]
        analysis_date = date.fromisoformat(args["date"])

        # Get plan and log
        plan = await self.storage.get_active_plan(user_id)
        log = await self.storage.get_log_by_date(user_id, analysis_date)

        if not plan:
            return {"error": "no_active_plan", "message": "用户没有活跃的碳循环计划"}
        if not log:
            return {"error": "no_log", "message": f"{analysis_date} 没有饮食记录"}

        # Find the day plan for this date
        day_plan = None
        for dp in plan.days:
            if str(dp.date) == str(analysis_date):
                day_plan = dp
                break

        if not day_plan:
            return {"error": "no_day_plan", "message": f"计划中没有 {analysis_date} 的安排"}

        service = ExecutionAnalysisService()
        analysis = service.analyze_day(day_plan, log)

        return analysis.to_dict()

    async def _execute_get_user_history(self, args: dict[str, Any]) -> dict:
        """
        Get user's historical diet logs and weight data.
        获取用户历史饮食记录和体重数据
        """
        user_id = args["user_id"]
        days = int(args.get("days", 7))
        include_reports = args.get("include_reports", False)

        # Get diet logs
        logs = await self.storage.get_user_logs(user_id, limit=days)
        log_summaries = []
        for log in logs:
            log_summaries.append({
                "date": str(log.date),
                "calories": log.total_calories,
                "protein": log.total_protein,
                "carbs": log.total_carbs,
                "fat": log.total_fat,
                "meal_count": len(log.meals),
                "training_completed": log.training_completed,
            })

        # Get weight history
        weight_logs = await self.storage.get_user_weight_logs(user_id, limit=days)
        weight_summaries = [
            {"date": str(w.date), "weight_kg": w.weight_kg, "body_fat_pct": w.body_fat_pct}
            for w in weight_logs
        ]

        # Get user stats
        stats = await self.storage.get_user_log_stats(user_id, days=days)

        return {
            "user_id": user_id,
            "period_days": days,
            "diet_logs": log_summaries,
            "weight_logs": weight_summaries,
            "statistics": stats,
        }

    async def _execute_suggest_adjustment(self, args: dict[str, Any]) -> dict:
        """
        Generate adjustment suggestions based on deviation analysis.
        根据偏差分析生成调整建议
        """
        user_id = args["user_id"]
        deviation_type = args["deviation_type"]
        severity = args["severity"]

        # Rule-based adjustment suggestions
        ADJUSTMENTS = {
            "calorie_excess": {
                "minor": {
                    "calorie_change": -100,
                    "actions": ["下一餐减少主食量10%", "增加蔬菜占比"],
                },
                "moderate": {
                    "calorie_change": -200,
                    "actions": ["明天切换到低碳日", "减少零食和加工食品", "增加步行量"],
                },
                "significant": {
                    "calorie_change": -300,
                    "actions": ["未来两天切换到低碳日", "暂停加餐", "增加有氧运动30分钟"],
                },
            },
            "calorie_deficit": {
                "minor": {
                    "calorie_change": 100,
                    "actions": ["加一份健康零食（坚果/酸奶）"],
                },
                "moderate": {
                    "calorie_change": 200,
                    "actions": ["增加一餐健康加餐", "确保主餐碳水充足"],
                },
                "significant": {
                    "calorie_change": 300,
                    "actions": ["增加主餐份量", "添加两份健康加餐", "检查是否有饮食障碍倾向"],
                },
            },
            "macro_imbalance": {
                "minor": {
                    "calorie_change": 0,
                    "actions": ["调整蛋白质来源，确保每餐有优质蛋白"],
                },
                "moderate": {
                    "calorie_change": 0,
                    "actions": ["重新分配三大营养素比例", "增加蛋白质摄入（鸡胸/鱼/豆腐）"],
                },
                "significant": {
                    "calorie_change": 0,
                    "actions": ["严格按照计划的宏量比例准备餐食", "考虑使用蛋白粉补充", "咨询营养师"],
                },
            },
            "training_skip": {
                "minor": {
                    "calorie_change": -50,
                    "actions": ["安排一次10分钟快速训练"],
                },
                "moderate": {
                    "calorie_change": -100,
                    "actions": ["补一次训练", "相应减少碳水摄入"],
                },
                "significant": {
                    "calorie_change": -150,
                    "actions": ["重新评估训练计划的可行性", "切换到低碳日", "考虑减少训练强度但保持频率"],
                },
            },
        }

        adjustment = ADJUSTMENTS.get(deviation_type, {}).get(severity, {
            "calorie_change": 0,
            "actions": ["保持当前计划"],
        })

        return {
            "user_id": user_id,
            "deviation_type": deviation_type,
            "severity": severity,
            "calorie_adjustment": adjustment["calorie_change"],
            "recommended_actions": adjustment["actions"],
            "note": f"基于{severity}程度的{deviation_type}偏差生成的调整建议",
        }
