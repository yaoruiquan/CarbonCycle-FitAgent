"""
Scheduled task management.
定时任务管理

Uses APScheduler for periodic tasks like weekly report generation.
使用 APScheduler 执行周期性任务如周报生成
"""

from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logging import get_logger

logger = get_logger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None

# Task type alias
ScheduledTask = Callable[[], Coroutine[Any, Any, None]]


def get_scheduler() -> AsyncIOScheduler:
    """
    Get or create the global scheduler instance.
    
    Returns:
        AsyncIOScheduler: The scheduler instance.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def add_weekly_task(
    task_id: str,
    func: ScheduledTask,
    day_of_week: str = "sun",
    hour: int = 9,
    minute: int = 0,
) -> None:
    """
    Add a weekly scheduled task.
    
    Args:
        task_id: Unique identifier for the task.
        func: Async function to execute.
        day_of_week: Day to run (mon, tue, wed, thu, fri, sat, sun).
        hour: Hour to run (0-23).
        minute: Minute to run (0-59).
    
    Example:
        add_weekly_task(
            "weekly_report",
            generate_weekly_reports,
            day_of_week="sun",
            hour=9,
        )
    """
    scheduler = get_scheduler()
    
    trigger = CronTrigger(
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
    )
    
    scheduler.add_job(
        func,
        trigger=trigger,
        id=task_id,
        name=f"Weekly task: {task_id}",
        replace_existing=True,
    )
    
    logger.info(
        f"Scheduled weekly task: {task_id} "
        f"at {day_of_week} {hour:02d}:{minute:02d}"
    )


def add_daily_task(
    task_id: str,
    func: ScheduledTask,
    hour: int = 0,
    minute: int = 0,
) -> None:
    """
    Add a daily scheduled task.
    
    Args:
        task_id: Unique identifier for the task.
        func: Async function to execute.
        hour: Hour to run (0-23).
        minute: Minute to run (0-59).
    """
    scheduler = get_scheduler()
    
    trigger = CronTrigger(hour=hour, minute=minute)
    
    scheduler.add_job(
        func,
        trigger=trigger,
        id=task_id,
        name=f"Daily task: {task_id}",
        replace_existing=True,
    )
    
    logger.info(f"Scheduled daily task: {task_id} at {hour:02d}:{minute:02d}")


def start_scheduler() -> None:
    """
    Start the scheduler.
    
    Should be called during application startup.
    """
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler() -> None:
    """
    Stop the scheduler gracefully.
    
    Should be called during application shutdown.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
        _scheduler = None


def get_next_run_time(task_id: str) -> Optional[datetime]:
    """
    Get the next scheduled run time for a task.
    
    Args:
        task_id: The task identifier.
        
    Returns:
        Next run datetime or None if task not found.
    """
    scheduler = get_scheduler()
    job = scheduler.get_job(task_id)
    if job:
        return job.next_run_time
    return None
