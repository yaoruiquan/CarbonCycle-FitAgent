"""
Domain Harness case registry and runner.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from app.agent import graph as agent_graph
from app.core.config import get_settings
from app.harness.scoring import DIMENSION_WEIGHTS, score_agent_result

CASE_DIR = Path("harness/cases")
DEFAULT_RESULTS_DIR = Path("evaluation_results")
VALID_CATEGORIES = {
    "nutrition_deviation",
    "training_behavior",
    "safety_boundary",
    "data_quality",
    "tool_policy",
    "memory_context",
}
VALID_DIFFICULTIES = {"smoke", "regression", "adversarial"}


def list_harness_cases(case_dir: Path = CASE_DIR) -> list[dict[str, Any]]:
    """Load all harness case definitions."""
    cases = []
    for path in sorted(case_dir.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        validate_harness_case(case)
        cases.append(normalize_harness_case(case))
    return cases


def normalize_harness_case(case: dict[str, Any]) -> dict[str, Any]:
    """Return a case with v2 metadata defaults while preserving old case files."""
    normalized = dict(case)
    normalized.setdefault("category", "nutrition_deviation")
    normalized.setdefault("difficulty", "regression")
    normalized.setdefault("tags", [])
    return normalized


def validate_harness_case(case: dict[str, Any]) -> None:
    """Validate the minimum case contract."""
    required = ["id", "title", "trigger", "user_context", "plan_context", "logs", "expectations"]
    missing = [field for field in required if field not in case]
    if missing:
        raise ValueError(f"Harness case {case.get('id', '<unknown>')} missing fields: {', '.join(missing)}")
    if not isinstance(case["logs"], list):
        raise ValueError(f"Harness case {case['id']} logs must be a list")
    category = case.get("category", "nutrition_deviation")
    difficulty = case.get("difficulty", "regression")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Harness case {case['id']} has invalid category: {category}")
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"Harness case {case['id']} has invalid difficulty: {difficulty}")
    if "tags" in case and not isinstance(case["tags"], list):
        raise ValueError(f"Harness case {case['id']} tags must be a list")


async def run_harness_cases(
    *,
    case_ids: Optional[list[str]] = None,
    db_session: Optional[Any] = None,
    output_dir: Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    """Run selected harness cases and persist a compact JSON report."""
    cases = list_harness_cases()
    if case_ids:
        selected = [case for case in cases if case["id"] in set(case_ids)]
    else:
        selected = cases

    results = []
    settings = get_settings()
    for index, case in enumerate(selected):
        if index > 0 and settings.harness_case_delay_seconds > 0:
            await asyncio.sleep(settings.harness_case_delay_seconds)
        result = await run_harness_case(case, db_session=db_session)
        retries = 0
        while (
            _is_rate_limited_result(result)
            and retries < settings.harness_rate_limit_retry_count
        ):
            retries += 1
            await asyncio.sleep(_retry_delay_seconds(result, settings.harness_rate_limit_retry_delay_seconds))
            result = await run_harness_case(case, db_session=db_session)
            result["retry_count"] = retries
        results.append(result)

    passed = sum(1 for result in results if result["passed"])
    summary = {
        "run_id": str(uuid4()),
        "created_at": datetime.now().isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0,
        "average_harness_score": round(
            sum(result.get("harness_score", 0) for result in results) / len(results),
            1,
        ) if results else 0,
        "average_dimension_scores": _average_dimension_scores(results),
        "category_summary": _group_summary(results, "category"),
        "difficulty_summary": _group_summary(results, "difficulty"),
        "results": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"harness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["report_path"] = str(output_path)
    return summary


async def run_harness_case(case: dict[str, Any], db_session: Optional[Any] = None) -> dict[str, Any]:
    """Run one case through the real agent runner and score expectations."""
    validate_harness_case(case)
    result = await agent_graph.run_agent(
        user_id=str(case["user_context"].get("user_id", "harness-user")),
        trigger=case["trigger"],
        user_context=case["user_context"],
        plan_context=case["plan_context"],
        logs=case["logs"],
        db_session=db_session,
        memory_context=case.get("memory_context") or {},
        evaluation_summary={"source": "harness_case", "case_id": case["id"]},
    )
    expectation_result = evaluate_expectations(result, case["expectations"])
    return {
        "case_id": case["id"],
        "title": case["title"],
        "category": case.get("category", "nutrition_deviation"),
        "difficulty": case.get("difficulty", "regression"),
        "tags": case.get("tags", []),
        "passed": expectation_result["passed"],
        "failures": expectation_result["failures"],
        "expectation_failures": expectation_result.get("expectation_failures", []),
        "hard_failures": expectation_result.get("hard_failures", []),
        "run_id": result.get("run_id"),
        "status": result.get("status"),
        "verification_status": result.get("verification_status"),
        "harness_score": expectation_result.get("overall_score", 0),
        "agent_harness_score": result.get("harness_score", 0),
        "dimension_scores": expectation_result.get("dimension_scores", {}),
        "error": result.get("error"),
        "model_status": result.get("model_status") or {},
        "verification_findings": result.get("verification_findings") or [],
        "summary": {
            "trace_count": len(result.get("trace") or []),
            "tool_call_count": len(result.get("tool_trace") or []),
            "warning_rules": [item.get("rule") for item in result.get("safety_warnings") or []],
            "tool_names": [item.get("tool_name") for item in result.get("tool_trace") or []],
            "action_types": [item.get("type") for item in result.get("action_cards") or []],
            "trace_nodes": [item.get("node") for item in result.get("trace") or []],
        },
    }


def evaluate_expectations(result: dict[str, Any], expectations: dict[str, Any]) -> dict[str, Any]:
    """Evaluate domain expectations against an agent result."""
    return score_agent_result(result, expectations)


def _is_rate_limited_result(result: dict[str, Any]) -> bool:
    model_status = result.get("model_status") or {}
    return (
        model_status.get("status_code") == 429
        or model_status.get("code") == "rate_limited"
        or model_status.get("type") == "rate_limit_error"
    )


def _retry_delay_seconds(result: dict[str, Any], fallback_seconds: float) -> float:
    model_status = result.get("model_status") or {}
    retry_after = model_status.get("retry_after_seconds")
    try:
        if retry_after is not None:
            return max(float(retry_after), 0)
    except (TypeError, ValueError):
        pass
    return max(fallback_seconds, 0)


def _average_dimension_scores(results: list[dict[str, Any]]) -> dict[str, float]:
    if not results:
        return {name: 0 for name in DIMENSION_WEIGHTS}
    return {
        name: round(sum((result.get("dimension_scores") or {}).get(name, 0) for result in results) / len(results), 1)
        for name in DIMENSION_WEIGHTS
    }


def _group_summary(results: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        grouped.setdefault(str(result.get(key) or "unknown"), []).append(result)
    return {
        group: {
            "total": len(items),
            "passed": sum(1 for item in items if item.get("passed")),
            "failed": sum(1 for item in items if not item.get("passed")),
            "average_harness_score": round(
                sum(item.get("harness_score", 0) for item in items) / len(items),
                1,
            ),
        }
        for group, items in grouped.items()
    }
