"""
Function calling tool definitions.
函数调用工具定义

Defines tools available for LLM function calling.
定义可用于 LLM 函数调用的工具
Note: Tool implementations are in services layer, not here.
注意：工具实现在服务层，而非此处
"""

from typing import Any

# Tool name constants
TOOL_CALCULATE_MACROS = "calculate_macros"
TOOL_QUERY_FOOD = "query_food_nutrition"
TOOL_ANALYZE_DEVIATION = "analyze_deviation"
TOOL_GET_USER_HISTORY = "get_user_history"
TOOL_SUGGEST_ADJUSTMENT = "suggest_adjustment"


def _create_tool_definition(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    """
    Create OpenAI-compatible tool definition.
    
    Args:
        name: Tool function name.
        description: Tool description.
        parameters: Parameter schema.
        required: List of required parameter names.
        
    Returns:
        Tool definition dict.
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }


# Tool definitions
CALCULATE_MACROS_TOOL = _create_tool_definition(
    name=TOOL_CALCULATE_MACROS,
    description=(
        "Calculate macronutrient targets (protein, carbs, fat) based on "
        "user profile, goal, and day type in carbon cycle."
    ),
    parameters={
        "user_id": {
            "type": "string",
            "description": "User identifier",
        },
        "day_type": {
            "type": "string",
            "enum": ["high_carb", "medium_carb", "low_carb", "refeed"],
            "description": "Carbon cycle day type",
        },
        "target_calories": {
            "type": "number",
            "description": "Target calories for the day",
        },
    },
    required=["user_id", "day_type", "target_calories"],
)


QUERY_FOOD_TOOL = _create_tool_definition(
    name=TOOL_QUERY_FOOD,
    description=(
        "Query nutritional information for a food item. "
        "Returns calories, protein, carbs, and fat per 100g."
    ),
    parameters={
        "food_name": {
            "type": "string",
            "description": "Name of the food item",
        },
        "quantity_g": {
            "type": "number",
            "description": "Quantity in grams (optional, defaults to 100)",
        },
    },
    required=["food_name"],
)


ANALYZE_DEVIATION_TOOL = _create_tool_definition(
    name=TOOL_ANALYZE_DEVIATION,
    description=(
        "Analyze deviation between planned and actual intake. "
        "Returns deviation percentage and impact assessment."
    ),
    parameters={
        "user_id": {
            "type": "string",
            "description": "User identifier",
        },
        "date": {
            "type": "string",
            "format": "date",
            "description": "Date to analyze (YYYY-MM-DD)",
        },
    },
    required=["user_id", "date"],
)


GET_USER_HISTORY_TOOL = _create_tool_definition(
    name=TOOL_GET_USER_HISTORY,
    description=(
        "Get user's historical data including past plans, logs, and reports. "
        "Useful for understanding patterns and preferences."
    ),
    parameters={
        "user_id": {
            "type": "string",
            "description": "User identifier",
        },
        "days": {
            "type": "integer",
            "description": "Number of days of history to retrieve",
        },
        "include_reports": {
            "type": "boolean",
            "description": "Whether to include weekly reports",
        },
    },
    required=["user_id", "days"],
)


SUGGEST_ADJUSTMENT_TOOL = _create_tool_definition(
    name=TOOL_SUGGEST_ADJUSTMENT,
    description=(
        "Generate adjustment suggestions based on analysis results. "
        "Returns specific recommendations for plan modifications."
    ),
    parameters={
        "user_id": {
            "type": "string",
            "description": "User identifier",
        },
        "deviation_type": {
            "type": "string",
            "enum": ["calorie_excess", "calorie_deficit", "macro_imbalance", "training_skip"],
            "description": "Type of deviation detected",
        },
        "severity": {
            "type": "string",
            "enum": ["minor", "moderate", "significant"],
            "description": "Severity of the deviation",
        },
    },
    required=["user_id", "deviation_type", "severity"],
)


# Available tools collection
AVAILABLE_TOOLS = {
    TOOL_CALCULATE_MACROS: CALCULATE_MACROS_TOOL,
    TOOL_QUERY_FOOD: QUERY_FOOD_TOOL,
    TOOL_ANALYZE_DEVIATION: ANALYZE_DEVIATION_TOOL,
    TOOL_GET_USER_HISTORY: GET_USER_HISTORY_TOOL,
    TOOL_SUGGEST_ADJUSTMENT: SUGGEST_ADJUSTMENT_TOOL,
}


def get_tool_definitions(tool_names: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Get tool definitions for function calling.
    
    Args:
        tool_names: Specific tools to include. None means all tools.
        
    Returns:
        List of tool definition dicts.
    """
    if tool_names is None:
        return list(AVAILABLE_TOOLS.values())
    
    return [
        AVAILABLE_TOOLS[name]
        for name in tool_names
        if name in AVAILABLE_TOOLS
    ]
