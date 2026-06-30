import pytest

from app.harness.tool_policy import ToolPermission, ToolPolicy
from app.llm.tools import TOOL_CALCULATE_MACROS


def test_registered_tools_default_to_auto():
    decision = ToolPolicy().decide(TOOL_CALCULATE_MACROS, {"user_id": "u1"})

    assert decision["permission"] == ToolPermission.AUTO.value
    assert decision["policy_decision"] == "allowed"


def test_unknown_tool_is_blocked():
    decision = ToolPolicy().decide("delete_database", {})

    assert decision["permission"] == ToolPermission.BLOCKED.value
    assert decision["policy_decision"] == "blocked"


def test_custom_policy_supports_dry_run():
    policy = ToolPolicy({TOOL_CALCULATE_MACROS: ToolPermission.DRY_RUN})

    decision = policy.decide(TOOL_CALCULATE_MACROS, {})

    assert decision["permission"] == ToolPermission.DRY_RUN.value
    assert decision["policy_decision"] == "dry_run"


def test_invalid_custom_permission_raises_value_error():
    with pytest.raises(ValueError):
        ToolPolicy({TOOL_CALCULATE_MACROS: "invalid"})
