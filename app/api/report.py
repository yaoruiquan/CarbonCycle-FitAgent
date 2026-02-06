"""
Weekly Report API.
周报告 API

Generates weekly statistics and AI-powered analysis reports using Agent and Memory.
使用 Agent 和 Memory 生成周统计数据和 AI 分析报告。
"""

from datetime import date
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.agent import run_agent
from app.db.db_storage import DatabaseStorage

logger = get_logger(__name__)

router = APIRouter()


class WeeklyStats(BaseModel):
    """Weekly statistics for report generation."""
    calorieTarget: float
    calorieActual: float
    calorieRate: float
    trainingCompleted: int
    trainingTotal: int
    trainingRate: float
    avgProtein: float
    avgCarbs: float
    avgFat: float
    weightStart: Optional[float] = None
    weightEnd: Optional[float] = None
    weightChange: Optional[float] = None


class WeeklyReportRequest(BaseModel):
    """Request body for weekly report generation."""
    user_id: str
    stats: WeeklyStats
    plan_id: Optional[str] = None


class WeeklyReportResponse(BaseModel):
    """Response model for weekly report."""
    report: str
    generated_at: str
    agent_used: bool = False
    latency_ms: Optional[int] = None


def _build_user_context(user: Any) -> dict[str, Any]:
    """Build user context from UserProfile."""
    return {
        "user_id": str(user.id),
        "name": user.name,
        "gender": user.gender.value if hasattr(user.gender, 'value') else user.gender,
        "age": user.calculate_age() if hasattr(user, 'calculate_age') else 30,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "target_weight_kg": getattr(user, 'target_weight_kg', user.weight_kg - 5) or user.weight_kg - 5,
        "goal": user.goal.value if hasattr(user.goal, 'value') else user.goal,
        "activity_level": user.activity_level.value if hasattr(user.activity_level, 'value') else user.activity_level,
    }


@router.post("/weekly", response_model=WeeklyReportResponse)
async def generate_weekly_report(
    request: WeeklyReportRequest,
    db: AsyncSession = Depends(get_db),
) -> WeeklyReportResponse:
    """
    Generate AI-powered weekly report with analysis and suggestions using Agent.
    使用 Agent 生成周报告，包含分析和建议。
    """
    stats = request.stats
    storage = DatabaseStorage(db)
    
    # Get user data
    try:
        user = await storage.get_user(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_context = _build_user_context(user)
    except Exception as e:
        logger.warning(f"Failed to get user context: {e}")
        user_context = {"user_id": request.user_id}
    
    # Get active plan for context
    try:
        plan = await storage.get_active_plan(request.user_id)
    except Exception:
        plan = None
    
    # Build trigger message with weekly stats
    trigger_message = f"""
周复盘分析请求：
- 热量达标率: {stats.calorieRate:.0f}%
- 目标热量: {stats.calorieTarget:.0f} kcal/天
- 实际热量: {stats.calorieActual:.0f} kcal/天
- 训练完成: {stats.trainingCompleted}/{stats.trainingTotal} 次 ({stats.trainingRate:.0f}%)
- 日均碳水: {stats.avgCarbs:.0f}g
- 日均蛋白: {stats.avgProtein:.0f}g
- 日均脂肪: {stats.avgFat:.0f}g
{f"- 体重变化: {stats.weightChange:+.1f}kg" if stats.weightChange is not None else ""}

请分析本周执行情况并给出改进建议。
"""
    
    # Get recent logs for memory
    try:
        db_logs = await storage.get_user_logs(request.user_id, limit=7)
        logs_context = [
            {
                "date": log.date.isoformat(),
                "actual_calories": log.total_calories,
                "actual_protein": log.total_protein,
                "actual_carbs": log.total_carbs,
                "actual_fat": log.total_fat,
                "training_completed": log.training_completed,
                "meal_count": len(log.meals)
            }
            for log in db_logs
        ]
    except Exception as e:
        logger.warning(f"Failed to fetch logs for user {request.user_id}: {e}")
        logs_context = []

    try:
        # Call the Agent with memory integration
        result = await run_agent(
            user_id=request.user_id,
            trigger=f"weekly_report: {trigger_message}",
            user_context=user_context,
            plan_context={
                "plan_id": str(plan.id) if plan else None,
                "target_calories": stats.calorieTarget,
                "target_protein": stats.avgProtein,
                "target_carbs": stats.avgCarbs,
                "target_fat": stats.avgFat
            },
            logs=logs_context,
        )
        
        # Extract report from agent result
        if result.get("status") == "success":
            # Capture latency from agent
            latency_ms = result.get("latency_ms")
            
            # Try to get structured output
            reflection = result.get("reflection", {})
            adjustment = result.get("adjustment", {})
            reflection_summary = result.get("reflection_summary")
            trends = result.get("trends", {})
            
            # Final output might contain the summary
            final_output = result.get("planner_output", {}) # In some versions it's in planner_output
            motivation = final_output.get("motivation", "") if isinstance(final_output, dict) else ""
            
            # Build comprehensive report
            report_parts = ["## AI 深度复盘分析\n"]
            
            # Reflection summary
            if reflection_summary:
                report_parts.append(f"### 📊 执行情况反馈\n{reflection_summary}\n")
            elif reflection:
                summary = reflection.get("summary", "")
                adherence = reflection.get("adherence_score", stats.calorieRate)
                report_parts.append(f"### 📊 执行对比分析\n{summary}\n")
                if adherence:
                    report_parts.append(f"- 综合评分: **{adherence}**\n")
            else:
                report_parts.append(f"### 📊 本周执行回顾\n")
                report_parts.append(f"- 热量达成率: {stats.calorieRate:.0f}%\n")
                report_parts.append(f"- 训练完成率: {stats.trainingRate:.0f}%\n")
            
            # Trends analysis
            if trends and trends.get("has_trend"):
                report_parts.append("\n### 📈 趋势分析\n")
                report_parts.append(f"- 执行趋势: **{trends.get('trend_direction', '稳定')}**\n")
                report_parts.append(f"- 近7日平均热量偏差: {trends.get('avg_calorie_deviation', 0):.1f}%\n")
                report_parts.append(f"- 近7日训练完成率: {trends.get('training_completion_rate', 0):.1f}%\n")
            
            # Adjustment suggestions
            if adjustment:
                suggestions = adjustment.get("suggestions", []) or adjustment.get("adjustments", [])
                if suggestions:
                    report_parts.append("\n### 💡 针对性改进建议\n")
                    for i, adj in enumerate(suggestions[:3], 1):
                        report_parts.append(f"{i}. {adj}\n")
            
            # Motivation
            if motivation:
                report_parts.append(f"\n### 🎯 Coach 寄语\n{motivation}\n")
            
            report = "".join(report_parts)
            agent_used = True
            
        else:
            # Agent failed or returned error, use fallback
            latency_ms = result.get("latency_ms")
            error_msg = result.get("error", "Unknown agent error")
            logger.error(f"Agent returned error: {error_msg}")
            raise Exception(error_msg)
            
    except Exception as e:
        logger.error(f"Agent failed, using fallback: {e}")
        latency_ms = None  # No latency for fallback
        
        # Fallback report without agent
        report = f"""
## 本周复盘

### 📊 执行情况
- 热量控制：达成率 **{stats.calorieRate:.0f}%**
- 训练完成：{stats.trainingCompleted}/{stats.trainingTotal} 次 ({stats.trainingRate:.0f}%)
{f"- 体重变化：{stats.weightChange:+.1f}kg" if stats.weightChange is not None else ""}

### 💡 改进建议
1. {"热量控制良好，继续保持！" if stats.calorieRate >= 80 else "热量摄入需要更精确记录"}
2. {"训练全勤，非常棒！" if stats.trainingRate >= 100 else "部分训练未完成，建议调整时间安排"}
3. 确保蛋白质摄入达到每日 {stats.avgProtein:.0f}g 目标

### 🎯 下周目标
- 保持碳水循环节奏
- 每餐坚持拍照记录
        """.strip()
        agent_used = False
    
    return WeeklyReportResponse(
        report=report,
        generated_at=date.today().isoformat(),
        agent_used=agent_used,
        latency_ms=latency_ms,
    )



# ============ Historical Report Endpoints ============

class ReportSummaryResponse(BaseModel):
    """Summary of a historical report for list view."""
    id: str
    week_start: str
    week_end: str
    overall_adherence: float
    weight_change: Optional[float] = None
    trend: str
    created_at: str


class ReportDetailResponse(BaseModel):
    """Full historical report detail."""
    id: str
    user_id: str
    week_start: str
    week_end: str
    calorie_rate: float
    training_rate: float
    weight_change: Optional[float] = None
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    summary: Optional[str] = None
    recommendations: list[str] = []
    created_at: str


# In-memory storage for generated reports (would be DB in production)
_report_cache: dict[str, dict] = {}


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report_by_id(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    """
    Get a historical weekly report by ID.
    获取历史周报详情
    """
    # Import historical data
    from app.data.historical_reports import HISTORICAL_REPORTS
    
    # Check cache first
    if report_id in _report_cache:
        cached = _report_cache[report_id]
        return ReportDetailResponse(**cached)
    
    # Find report by ID from historical data
    for report in HISTORICAL_REPORTS:
        if report["id"] == report_id:
            return ReportDetailResponse(**report)
    
    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/user/{user_id}", response_model=list[ReportSummaryResponse])
async def list_user_reports(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ReportSummaryResponse]:
    """
    List all historical reports for a user.
    列出用户的所有历史周报
    """
    from app.data.historical_reports import HISTORICAL_REPORTS
    
    # Convert to summary format
    summaries = [
        ReportSummaryResponse(
            id=r["id"],
            week_start=r["week_start"],
            week_end=r["week_end"],
            overall_adherence=r["overall_adherence"],
            weight_change=r["weight_change"],
            trend=r["trend"],
            created_at=r["created_at"],
        )
        for r in HISTORICAL_REPORTS
    ]
    
    return summaries


@router.get("/user/{user_id}/weights")
async def get_user_weight_history(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Get weight history for a user (for charts).
    获取用户体重历史（用于图表）
    """
    from app.data.historical_reports import WEIGHT_HISTORY
    
    return WEIGHT_HISTORY
