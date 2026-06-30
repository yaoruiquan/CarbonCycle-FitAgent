from app.harness.safety_policy import NutritionSafetyPolicy


def test_minimum_calorie_floor_triggers_danger():
    findings = NutritionSafetyPolicy().warnings(
        user={"tdee": 2000, "weight_kg": 70},
        plan={"target_calories": 1500, "target_protein": 140},
        plan_diff=[{"field": "target_calories", "after": 1100}],
        reflection={},
    )

    assert any(item["rule"] == "minimum_calorie_floor" and item["level"] == "danger" for item in findings)


def test_deficit_cap_triggers_warning():
    findings = NutritionSafetyPolicy().warnings(
        user={"tdee": 3000, "weight_kg": 70},
        plan={"target_calories": 2400, "target_protein": 140},
        plan_diff=[{"field": "target_calories", "after": 1800}],
        reflection={},
    )

    assert any(item["rule"] == "deficit_cap" and item["level"] == "warning" for item in findings)


def test_protein_floor_triggers_warning():
    findings = NutritionSafetyPolicy().warnings(
        user={"tdee": 2200, "weight_kg": 100},
        plan={"target_calories": 2000, "target_protein": 90},
        plan_diff=[],
        reflection={},
    )

    assert any(item["rule"] == "protein_floor" for item in findings)


def test_normal_plan_has_no_warnings():
    findings = NutritionSafetyPolicy().warnings(
        user={"tdee": 2400, "weight_kg": 70},
        plan={"target_calories": 2000, "target_protein": 140},
        plan_diff=[],
        reflection={"calorie_deviation_pct": 5},
    )

    assert findings == []
