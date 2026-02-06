"""
Knowledge service for carbon cycle information.
碳循环信息知识服务

Provides RAG-based knowledge retrieval for nutrition and fitness.
为营养和健身提供基于 RAG 的知识检索
"""

from typing import Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Basic nutrition knowledge base (placeholder for RAG)
FOOD_DATABASE = {
    "鸡胸肉": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "unit": "100g"},
    "糙米": {"calories": 111, "protein": 2.6, "carbs": 23, "fat": 0.9, "unit": "100g"},
    "西兰花": {"calories": 34, "protein": 2.8, "carbs": 7, "fat": 0.4, "unit": "100g"},
    "三文鱼": {"calories": 208, "protein": 20, "carbs": 0, "fat": 13, "unit": "100g"},
    "红薯": {"calories": 86, "protein": 1.6, "carbs": 20, "fat": 0.1, "unit": "100g"},
    "牛油果": {"calories": 160, "protein": 2, "carbs": 9, "fat": 15, "unit": "100g"},
    "希腊酸奶": {"calories": 59, "protein": 10, "carbs": 3.6, "fat": 0.7, "unit": "100g"},
    "鸡蛋": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11, "unit": "100g"},
    "燕麦": {"calories": 389, "protein": 17, "carbs": 66, "fat": 7, "unit": "100g"},
    "牛肉": {"calories": 250, "protein": 26, "carbs": 0, "fat": 15, "unit": "100g"},
}


class KnowledgeService:
    """Service for nutrition and fitness knowledge retrieval."""

    def __init__(self) -> None:
        self._food_db = FOOD_DATABASE

    def query_food_nutrition(
        self,
        food_name: str,
        quantity_g: float = 100,
    ) -> Optional[dict[str, Any]]:
        """
        Query nutritional information for a food item.

        Args:
            food_name: Name of the food.
            quantity_g: Quantity in grams.

        Returns:
            Nutrition dict or None if not found.
        """
        food = self._food_db.get(food_name)
        if not food:
            logger.debug(f"Food not found: {food_name}")
            return None

        ratio = quantity_g / 100
        return {
            "name": food_name,
            "quantity_g": quantity_g,
            "calories": round(food["calories"] * ratio, 1),
            "protein_g": round(food["protein"] * ratio, 1),
            "carbs_g": round(food["carbs"] * ratio, 1),
            "fat_g": round(food["fat"] * ratio, 1),
        }

    def search_foods(self, query: str, limit: int = 5) -> list[str]:
        """Search foods by partial name match."""
        results = [name for name in self._food_db if query in name]
        return results[:limit]

    def get_high_protein_foods(self, limit: int = 5) -> list[dict]:
        """Get foods sorted by protein content."""
        sorted_foods = sorted(
            self._food_db.items(),
            key=lambda x: x[1]["protein"],
            reverse=True,
        )
        return [{"name": k, **v} for k, v in sorted_foods[:limit]]

    def get_low_carb_foods(self, limit: int = 5) -> list[dict]:
        """Get foods with low carb content."""
        sorted_foods = sorted(
            self._food_db.items(),
            key=lambda x: x[1]["carbs"],
        )
        return [{"name": k, **v} for k, v in sorted_foods[:limit]]
