"""
Data package for CarbonCycle-FitAgent.
数据模块
"""

from app.data.historical_reports import HISTORICAL_REPORTS, WEIGHT_HISTORY, generate_weekly_reports

__all__ = ["HISTORICAL_REPORTS", "WEIGHT_HISTORY", "generate_weekly_reports"]
