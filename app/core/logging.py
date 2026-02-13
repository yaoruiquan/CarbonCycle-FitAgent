"""
Structured logging configuration.
结构化日志配置

Provides JSON-formatted logs with context support for Agent decision auditing.
提供支持上下文的 JSON 格式日志，用于智能体决策审计
"""

import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import get_settings

# Context variables for request/agent tracing
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
agent_run_id_var: ContextVar[Optional[str]] = ContextVar("agent_run_id", default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON-style structured log formatter.
    
    Includes timestamp, level, message, and context variables.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured string.
        
        Args:
            record: Log record to format.
            
        Returns:
            Formatted log string with context.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_data = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context variables if present
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
            
        agent_run_id = agent_run_id_var.get()
        if agent_run_id:
            log_data["agent_run_id"] = agent_run_id
        
        # Add extra fields from record
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # Format as key=value pairs for readability
        parts = [f"{k}={v}" for k, v in log_data.items()]
        return " | ".join(parts)


def setup_logging() -> None:
    """
    Configure application-wide logging.
    
    Sets up structured formatting and appropriate log levels.
    """
    settings = get_settings()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name, typically __name__ of the module.
        
    Returns:
        Logger: Configured logger instance.
    """
    return logging.getLogger(name)


def log_agent_decision(
    logger: logging.Logger,
    node: str,
    decision: str,
    reasoning: str,
    context: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log an Agent decision for auditing purposes.
    
    Args:
        logger: Logger instance to use.
        node: Agent node name (planner, actor, reflector, adjuster).
        decision: The decision made.
        reasoning: Explanation of why this decision was made.
        context: Additional context data.
    
    Example:
        log_agent_decision(
            logger,
            node="planner",
            decision="generate_high_carb_day",
            reasoning="User has training scheduled, needs glycogen replenishment",
            context={"training_type": "strength", "intensity": "high"}
        )
    """
    extra_data = {
        "node": node,
        "decision": decision,
        "reasoning": reasoning,
    }
    if context:
        extra_data["context"] = context
    
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        f"Agent decision: {decision}",
        None,
        None,
    )
    record.extra_data = extra_data
    logger.handle(record)
