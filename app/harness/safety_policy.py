"""
Nutrition safety policies for plan changes proposed by the agent.
"""

from typing import Any


class NutritionSafetyPolicy:
    """Evaluate nutrition guardrails for proposed plan changes."""

    version = "nutrition-safety:v1"

    def evaluate(
        self,
        *,
        user: dict[str, Any],
        plan: dict[str, Any],
        plan_diff: list[dict[str, Any]],
        reflection: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return policy findings. Failed info/warning/danger findings are warnings."""
        findings: list[dict[str, Any]] = []
        current_calories = self._target_calories(plan)
        proposed_calories = next(
            (float(item["after"]) for item in plan_diff if item.get("field") == "target_calories"),
            current_calories,
        )
        tdee = float(user.get("tdee", 0) or 0)
        weight = float(user.get("weight_kg", 0) or 0)
        protein_target = next(
            (float(item["after"]) for item in plan_diff if item.get("field") == "target_protein"),
            float(plan.get("target_protein", 0) or 0),
        )

        if proposed_calories and proposed_calories < 1200:
            findings.append(self._finding(
                level="danger",
                rule="minimum_calorie_floor",
                message="建议热量低于 1200 kcal，已限制为安全下限，避免极端节食。",
                evidence={"proposed_calories": proposed_calories},
            ))
        if tdee and proposed_calories and (tdee - proposed_calories) / tdee > 0.35:
            findings.append(self._finding(
                level="warning",
                rule="deficit_cap",
                message="建议热量缺口超过 TDEE 的 35%，需要谨慎执行并观察恢复状态。",
                evidence={"tdee": tdee, "proposed_calories": proposed_calories},
            ))
        if weight and protein_target and protein_target / weight < 1.2:
            findings.append(self._finding(
                level="warning",
                rule="protein_floor",
                message="蛋白质目标低于 1.2g/kg，可能影响训练恢复和保肌。",
                evidence={"weight_kg": weight, "protein_target": protein_target},
            ))
        if reflection.get("calorie_deviation_pct", 0) < -25:
            findings.append(self._finding(
                level="info",
                rule="under_eating_recovery",
                message="今日摄入明显不足，Agent 会优先建议补足营养而不是继续降低热量。",
                evidence={"calorie_deviation_pct": reflection.get("calorie_deviation_pct")},
            ))
        return findings

    def warnings(
        self,
        *,
        user: dict[str, Any],
        plan: dict[str, Any],
        plan_diff: list[dict[str, Any]],
        reflection: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return API-compatible warning payloads."""
        return [
            {
                "level": finding["level"],
                "message": finding["message"],
                "rule": finding["rule"],
                "evidence": finding["evidence"],
                "passed": finding["passed"],
                "policy_version": finding["policy_version"],
            }
            for finding in self.evaluate(
                user=user,
                plan=plan,
                plan_diff=plan_diff,
                reflection=reflection,
            )
        ]

    @staticmethod
    def _target_calories(plan: dict[str, Any]) -> float:
        if plan.get("target_calories"):
            return float(plan["target_calories"])
        protein = float(plan.get("target_protein", 0) or 0)
        carbs = float(plan.get("target_carbs", 0) or 0)
        fat = float(plan.get("target_fat", 0) or 0)
        return protein * 4 + carbs * 4 + fat * 9

    def _finding(
        self,
        *,
        level: str,
        rule: str,
        message: str,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "rule": rule,
            "level": level,
            "message": message,
            "passed": False,
            "evidence": evidence,
            "policy_version": self.version,
        }
