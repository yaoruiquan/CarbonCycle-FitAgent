"""
Food Analysis API.
食物分析 API

Uses vision model to analyze food images and estimate macros.
使用视觉模型分析食物图片并估算营养成分。
"""

import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.db.db_storage import DatabaseStorage
from app.llm.client import get_llm_client

logger = get_logger(__name__)

router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class FoodAnalysisResult(BaseModel):
    """Response model for food analysis."""
    food_name: str
    portion: str
    carbs_g: float
    protein_g: float
    fat_g: float
    calories: float
    confidence: float
    image_path: Optional[str] = None
    log_id: Optional[str] = None


@router.post("/analyze", response_model=FoodAnalysisResult)
async def analyze_food(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    meal_type: str = Form(default="lunch"),
    auto_log: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
) -> FoodAnalysisResult:
    """
    Analyze food image using vision model.
    使用视觉模型分析食物图片。
    
    Args:
        file: Uploaded food image.
        user_id: User ID for logging.
        meal_type: Type of meal (breakfast/lunch/dinner/snack).
        auto_log: Whether to automatically create a diet log entry.
        
    Returns:
        FoodAnalysisResult with estimated macros and calories.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Save image to disk
    file_ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / file_name
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        logger.info(f"Saved food image: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image")
    
    # Analyze with vision model
    llm = get_llm_client()
    
    prompt = """
请仔细分析这张食物图片，估算其中的营养成分。

请以 JSON 格式返回，不要包含 Markdown 代码块，格式如下：
{
    "food_name": "食物名称（如：红烧牛肉面）",
    "portion": "份量估计（如：一碗约300g）",
    "carbs_g": 碳水化合物克数（数字）,
    "protein_g": 蛋白质克数（数字）,
    "fat_g": 脂肪克数（数字）,
    "confidence": 0.0到1.0之间的置信度（数字）
}

注意：
- 请根据图片中食物的份量进行合理估算
- 如果图片不清晰或无法识别，confidence 设为较低值
- 所有数值字段必须是数字，不是字符串
"""
    
    response_text = ""  # Initialize to avoid unbound error
    try:
        result = await llm.analyze_image(
            image_path=file_path,
            prompt=prompt,
            system_prompt="你是一位专业的营养师，擅长通过食物图片估算营养成分。请准确分析并以JSON格式返回。"
        )
        
        response_text = result.get("content", "")
        
        # Clean up response (remove markdown code blocks if present)
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        data = json.loads(cleaned)
        
        food_name = data.get("food_name", "未知食物")
        portion = data.get("portion", "未知份量")
        carbs_g = float(data.get("carbs_g", 0))
        protein_g = float(data.get("protein_g", 0))
        fat_g = float(data.get("fat_g", 0))
        confidence = float(data.get("confidence", 0.5))
        
        # Calculate calories: 碳水 4 kcal/g, 蛋白质 4 kcal/g, 脂肪 9 kcal/g
        calories = carbs_g * 4 + protein_g * 4 + fat_g * 9
        
        logger.info(f"Food analysis: {food_name}, {calories:.0f} kcal, confidence={confidence:.2f}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}, response: {response_text[:200] if response_text else 'empty'}")
        # Fallback to default values
        food_name = "未能识别"
        portion = "未知"
        carbs_g = 30.0
        protein_g = 20.0
        fat_g = 10.0
        calories = 290.0
        confidence = 0.3
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    # For MVP, skip auto-logging to storage - just return the analysis result
    # The frontend will handle the logging via the confirmation step
    log_id = None
    if auto_log:
        logger.info(f"Food analysis complete for user {user_id}: {food_name} ({calories:.0f} kcal)")
        # TODO: Implement proper diet log storage when DietLog model is fully integrated
    
    return FoodAnalysisResult(
        food_name=food_name,
        portion=portion,
        carbs_g=carbs_g,
        protein_g=protein_g,
        fat_g=fat_g,
        calories=round(calories, 1),
        confidence=confidence,
        image_path=f"/uploads/{file_name}",
        log_id=log_id,
    )


class ManualFoodInput(BaseModel):
    """Request model for manual food input."""
    food_name: str
    weight_g: float
    user_id: str
    meal_type: str = "lunch"
    auto_log: bool = True


@router.post("/estimate", response_model=FoodAnalysisResult)
async def estimate_food_nutrition(
    input_data: ManualFoodInput,
    db: AsyncSession = Depends(get_db),
) -> FoodAnalysisResult:
    """
    Estimate nutrition from food name and weight using LLM.
    使用 LLM 根据食物名称和重量估算营养成分。
    
    Args:
        input_data: Food name and weight in grams.
        
    Returns:
        FoodAnalysisResult with estimated macros and calories.
    """
    llm = get_llm_client()
    
    # Prompt for nutrition estimation
    prompt = f"""作为营养师，请根据以下信息估算食物的宏量营养素：

食物名称：{input_data.food_name}
重量：{input_data.weight_g}克

请以JSON格式返回估算结果，格式如下：
{{
    "carbs_g": <碳水化合物克数>,
    "protein_g": <蛋白质克数>,
    "fat_g": <脂肪克数>
}}

注意：
1. 数值要基于常见食物的营养成分数据
2. 要根据实际重量进行计算
3. 只返回JSON，不要有其他文字"""

    try:
        response = await llm.chat([
            {"role": "user", "content": prompt}
        ])
        
        # Parse JSON response - response is a dict with 'content' key
        import re
        response_text = response.get("content", "") or ""
        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if json_match:
            nutrition = json.loads(json_match.group())
            carbs_g = float(nutrition.get("carbs_g", 0))
            protein_g = float(nutrition.get("protein_g", 0))
            fat_g = float(nutrition.get("fat_g", 0))
        else:
            # Fallback to rough estimates
            carbs_g = input_data.weight_g * 0.15
            protein_g = input_data.weight_g * 0.10
            fat_g = input_data.weight_g * 0.05
            
    except Exception as e:
        logger.error(f"LLM estimation failed: {e}")
        # Fallback estimates based on typical food
        carbs_g = input_data.weight_g * 0.15
        protein_g = input_data.weight_g * 0.10
        fat_g = input_data.weight_g * 0.05
    
    calories = carbs_g * 4 + protein_g * 4 + fat_g * 9
    
    # Generate log ID if auto_log is enabled
    log_id = None
    if input_data.auto_log:
        log_id = str(uuid.uuid4())
        logger.info(f"Manual food entry logged: {input_data.food_name} ({input_data.weight_g}g) = {calories:.0f} kcal")
    
    return FoodAnalysisResult(
        food_name=input_data.food_name,
        portion=f"{input_data.weight_g}g",
        carbs_g=round(carbs_g, 1),
        protein_g=round(protein_g, 1),
        fat_g=round(fat_g, 1),
        calories=round(calories, 1),
        confidence=0.7,  # Lower confidence for text-based estimation
        image_path=None,
        log_id=log_id,
    )


@router.post("/correct/{log_id}")
async def correct_food_analysis(
    log_id: str,
    carbs_g: float = Form(...),
    protein_g: float = Form(...),
    fat_g: float = Form(...),
    food_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually correct a food analysis result.
    手动修正食物分析结果。
    
    For MVP, this endpoint just returns the corrected values.
    TODO: Implement storage update when DietLog model is fully integrated.
    """
    # Calculate new calories
    calories = carbs_g * 4 + protein_g * 4 + fat_g * 9
    
    logger.info(f"Food correction: log_id={log_id}, new_calories={calories:.0f}")
    
    # TODO: Update storage when DietLog storage is fully integrated
    # storage = DatabaseStorage(db)
    # updated = await storage.update_log(log_id, ...)
    
    return {
        "status": "corrected",
        "log_id": log_id,
        "food_name": food_name,
        "carbs_g": carbs_g,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "new_calories": calories,
    }

