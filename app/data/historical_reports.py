"""
Historical data seeder for weekly reports.
历史数据生成器

Generates realistic historical weekly report data for demo and testing purposes.
生成用于演示和测试的真实历史周报数据
"""

from datetime import date, datetime, timedelta
from uuid import uuid4
import random

# Generate 8 weeks of historical data
def generate_weekly_reports(user_id: str = "demo") -> list[dict]:
    """Generate 8 weeks of historical weekly report data."""
    reports = []
    today = date.today()
    
    # Start from 8 weeks ago
    for week_offset in range(8, 0, -1):
        week_end = today - timedelta(days=week_offset * 7)
        week_start = week_end - timedelta(days=6)
        
        # Generate realistic varying metrics
        # Simulate improvement over time with some variance
        base_calorie_rate = 70 + (8 - week_offset) * 2.5 + random.uniform(-5, 5)
        base_training_rate = 60 + (8 - week_offset) * 3 + random.uniform(-10, 10)
        
        calorie_rate = min(100, max(50, base_calorie_rate))
        training_rate = min(100, max(40, base_training_rate))
        
        # Weight change (slight loss trend with variance)
        weight_change = round(-0.3 + random.uniform(-0.2, 0.3), 1)
        
        # Macros
        avg_protein = round(135 + random.uniform(-10, 15), 0)
        avg_carbs = round(210 + random.uniform(-20, 30), 0)
        avg_fat = round(62 + random.uniform(-8, 8), 0)
        
        # Determine trend based on metrics
        if calorie_rate >= 85 and training_rate >= 80:
            trend = "improving"
        elif calorie_rate < 70 or training_rate < 60:
            trend = "declining"
        else:
            trend = "stable"
        
        # Generate summary based on performance
        if calorie_rate >= 85:
            summary = f"本周热量控制良好，达成率{calorie_rate:.0f}%。"
        elif calorie_rate >= 70:
            summary = f"本周执行稳定，热量控制在可接受范围内（{calorie_rate:.0f}%）。"
        else:
            summary = f"本周执行有所松懈，热量达成率仅{calorie_rate:.0f}%，需要加强。"
        
        if training_rate >= 80:
            summary += f"训练完成率{training_rate:.0f}%，表现优秀！"
        elif training_rate >= 60:
            summary += f"训练完成率{training_rate:.0f}%，建议提高训练规律性。"
        else:
            summary += f"训练完成率偏低（{training_rate:.0f}%），需调整时间安排。"
        
        # Generate recommendations
        recommendations = []
        if calorie_rate < 80:
            recommendations.append("加强饮食记录习惯，每餐拍照记录")
        if training_rate < 80:
            recommendations.append("调整训练时间，确保规律执行")
        if avg_protein < 140:
            recommendations.append(f"增加蛋白质摄入，目标每日150g，当前平均{avg_protein:.0f}g")
        if weight_change > 0:
            recommendations.append("注意热量缺口，适当减少碳水摄入")
        
        if not recommendations:
            recommendations = ["保持当前节奏", "可适当增加训练强度"]
        
        report = {
            "id": str(week_offset),
            "user_id": user_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "calorie_rate": round(calorie_rate, 1),
            "training_rate": round(training_rate, 1),
            "weight_change": weight_change,
            "avg_protein": avg_protein,
            "avg_carbs": avg_carbs,
            "avg_fat": avg_fat,
            "overall_adherence": round((calorie_rate + training_rate) / 2, 1),
            "trend": trend,
            "summary": summary,
            "recommendations": recommendations,
            "created_at": (week_end + timedelta(hours=20)).isoformat(),
        }
        reports.append(report)
    
    return reports


# Pre-generated data for immediate use (deterministic for consistency)
HISTORICAL_REPORTS = [
    {
        "id": "1",
        "user_id": "demo",
        "week_start": "2026-01-27",
        "week_end": "2026-02-02",
        "calorie_rate": 92.0,
        "training_rate": 100.0,
        "weight_change": -0.2,
        "avg_protein": 150.0,
        "avg_carbs": 210.0,
        "avg_fat": 60.0,
        "overall_adherence": 96.0,
        "trend": "improving",
        "summary": "本周热量控制良好，达成率92%。训练完成率100%，表现优秀！",
        "recommendations": ["保持当前节奏", "可适当增加训练强度"],
        "created_at": "2026-02-02T20:00:00",
    },
    {
        "id": "2",
        "user_id": "demo",
        "week_start": "2026-01-20",
        "week_end": "2026-01-26",
        "calorie_rate": 78.0,
        "training_rate": 60.0,
        "weight_change": 0.1,
        "avg_protein": 130.0,
        "avg_carbs": 250.0,
        "avg_fat": 70.0,
        "overall_adherence": 69.0,
        "trend": "declining",
        "summary": "本周执行有所松懈，热量达成率仅78%，需要加强。训练完成率偏低（60%），需调整时间安排。",
        "recommendations": ["加强饮食记录习惯，每餐拍照记录", "调整训练时间，确保规律执行", "增加蛋白质摄入，目标每日150g，当前平均130g"],
        "created_at": "2026-01-26T20:00:00",
    },
    {
        "id": "3",
        "user_id": "demo",
        "week_start": "2026-01-13",
        "week_end": "2026-01-19",
        "calorie_rate": 88.0,
        "training_rate": 80.0,
        "weight_change": -0.3,
        "avg_protein": 142.0,
        "avg_carbs": 215.0,
        "avg_fat": 62.0,
        "overall_adherence": 84.0,
        "trend": "stable",
        "summary": "本周热量控制良好，达成率88%。训练完成率80%，表现优秀！",
        "recommendations": ["保持当前节奏", "注意睡眠质量"],
        "created_at": "2026-01-19T20:00:00",
    },
    {
        "id": "4",
        "user_id": "demo",
        "week_start": "2026-01-06",
        "week_end": "2026-01-12",
        "calorie_rate": 75.0,
        "training_rate": 60.0,
        "weight_change": 0.2,
        "avg_protein": 128.0,
        "avg_carbs": 240.0,
        "avg_fat": 68.0,
        "overall_adherence": 67.5,
        "trend": "declining",
        "summary": "本周执行稳定，热量控制在可接受范围内（75%）。训练完成率偏低（60%），需调整时间安排。",
        "recommendations": ["加强饮食记录习惯", "调整训练时间", "减少外食频率"],
        "created_at": "2026-01-12T20:00:00",
    },
    {
        "id": "5",
        "user_id": "demo",
        "week_start": "2025-12-30",
        "week_end": "2026-01-05",
        "calorie_rate": 82.0,
        "training_rate": 80.0,
        "weight_change": -0.1,
        "avg_protein": 138.0,
        "avg_carbs": 225.0,
        "avg_fat": 65.0,
        "overall_adherence": 81.0,
        "trend": "stable",
        "summary": "本周执行稳定，热量控制在可接受范围内（82%）。训练完成率80%，表现优秀！",
        "recommendations": ["继续保持", "增加蛋白质摄入"],
        "created_at": "2026-01-05T20:00:00",
    },
    {
        "id": "6",
        "user_id": "demo",
        "week_start": "2025-12-23",
        "week_end": "2025-12-29",
        "calorie_rate": 65.0,
        "training_rate": 40.0,
        "weight_change": 0.5,
        "avg_protein": 115.0,
        "avg_carbs": 280.0,
        "avg_fat": 75.0,
        "overall_adherence": 52.5,
        "trend": "declining",
        "summary": "本周执行有所松懈（节日期间），热量达成率仅65%。训练完成率偏低（40%），下周需恢复节奏。",
        "recommendations": ["节后恢复正常饮食", "重新开始规律训练", "减少聚餐应酬"],
        "created_at": "2025-12-29T20:00:00",
    },
    {
        "id": "7",
        "user_id": "demo",
        "week_start": "2025-12-16",
        "week_end": "2025-12-22",
        "calorie_rate": 85.0,
        "training_rate": 80.0,
        "weight_change": -0.2,
        "avg_protein": 145.0,
        "avg_carbs": 218.0,
        "avg_fat": 63.0,
        "overall_adherence": 82.5,
        "trend": "stable",
        "summary": "本周热量控制良好，达成率85%。训练完成率80%，表现优秀！",
        "recommendations": ["保持当前节奏", "注意节日期间饮食控制"],
        "created_at": "2025-12-22T20:00:00",
    },
    {
        "id": "8",
        "user_id": "demo",
        "week_start": "2025-12-09",
        "week_end": "2025-12-15",
        "calorie_rate": 80.0,
        "training_rate": 60.0,
        "weight_change": 0.0,
        "avg_protein": 135.0,
        "avg_carbs": 230.0,
        "avg_fat": 66.0,
        "overall_adherence": 70.0,
        "trend": "stable",
        "summary": "本周执行稳定，热量控制在可接受范围内（80%）。训练完成率60%，建议提高训练规律性。",
        "recommendations": ["提高训练频率", "增加蛋白质摄入"],
        "created_at": "2025-12-15T20:00:00",
    },
]

# Weight history for chart (daily data for past 8 weeks)
WEIGHT_HISTORY = []
base_weight = 76.2
current_date = date.today() - timedelta(days=56)
for i in range(57):
    # Slight downward trend with daily variance
    weight = base_weight - (i * 0.02) + random.uniform(-0.3, 0.3)
    WEIGHT_HISTORY.append({
        "date": current_date.isoformat(),
        "value": round(weight, 1),
    })
    current_date += timedelta(days=1)

# Regenerate with fixed seed for consistency
random.seed(42)
WEIGHT_HISTORY = []
base_weight = 76.2
current_date = date.today() - timedelta(days=56)
for i in range(57):
    weight = base_weight - (i * 0.02) + (0.3 if i % 3 == 0 else -0.2 if i % 4 == 0 else 0.1)
    WEIGHT_HISTORY.append({
        "date": current_date.isoformat(),
        "value": round(weight, 1),
    })
    current_date += timedelta(days=1)


if __name__ == "__main__":
    # Test generation
    import json
    reports = generate_weekly_reports()
    print(json.dumps(reports, indent=2, ensure_ascii=False))
