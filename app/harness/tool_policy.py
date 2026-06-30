"""
Tool permission policy for agent tool calls.
"""

from enum import Enum
from typing import Any, Optional, Union

from app.llm.tools import (
    TOOL_ANALYZE_DEVIATION,
    TOOL_CALCULATE_MACROS,
    TOOL_GET_USER_HISTORY,
    TOOL_QUERY_FOOD,
    TOOL_SUGGEST_ADJUSTMENT,
)


class ToolPermission(str, Enum):
    """Supported tool permissions."""

    AUTO = "auto"
    CONFIRM = "confirm"
    DRY_RUN = "dry_run"
    BLOCKED = "blocked"


class ToolPolicy:
    """Resolve whether an agent tool call is allowed to execute."""

    version = "tool-policy:v1"

    DEFAULT_PERMISSIONS: dict[str, ToolPermission] = {
        TOOL_CALCULATE_MACROS: ToolPermission.AUTO,
        TOOL_QUERY_FOOD: ToolPermission.AUTO,
        TOOL_ANALYZE_DEVIATION: ToolPermission.AUTO,
        TOOL_GET_USER_HISTORY: ToolPermission.AUTO,
        TOOL_SUGGEST_ADJUSTMENT: ToolPermission.AUTO,
    }

    def __init__(self, permissions: Optional[dict[str, Union[ToolPermission, str]]] = None):
        merged: dict[str, Union[ToolPermission, str]] = dict(self.DEFAULT_PERMISSIONS)
        if permissions:
            merged.update(permissions)
        self.permissions = {
            name: permission if isinstance(permission, ToolPermission) else ToolPermission(permission)
            for name, permission in merged.items()
        }

    def decide(self, tool_name: str, arguments: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Return the policy decision for a proposed tool call."""
        permission = self.permissions.get(tool_name, ToolPermission.BLOCKED)
        if permission == ToolPermission.BLOCKED:
            decision = "blocked"
            reason = "Tool is not registered in the active harness policy."
        elif permission == ToolPermission.CONFIRM:
            decision = "requires_confirmation"
            reason = "Tool requires human confirmation before execution."
        elif permission == ToolPermission.DRY_RUN:
            decision = "dry_run"
            reason = "Tool will be simulated without changing state."
        else:
            decision = "allowed"
            reason = "Tool is allowed to execute automatically."

        return {
            "tool_name": tool_name,
            "permission": permission.value,
            "policy_decision": decision,
            "policy_version": self.version,
            "reason": reason,
            "arguments": arguments or {},
        }
