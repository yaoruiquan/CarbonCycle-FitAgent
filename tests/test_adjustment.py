"""
Adjustment engine tests.
"""

import pytest
from datetime import date

from app.models.user import UserGoal
from app.services.adjustment_engine import AdjustmentEngine
from app.services.execution_analysis import (
    DailyAnalysis,
    DeviationSeverity,
    DeviationType,
    MacroDeviation,
)


class TestAdjustmentEngine:
    """Test adjustment engine logic."""

    @pytest.fixture
    def engine(self) -> AdjustmentEngine:
        """Create engine instance."""
        return AdjustmentEngine()

    @pytest.fixture
    def sample_analysis(self) -> DailyAnalysis:
        """Create sample daily analysis."""
        return DailyAnalysis(
            date=date(2024, 1, 1),
            calories=MacroDeviation(target=2000, actual=2300),
            protein=MacroDeviation(target=150, actual=140),
            carbs=MacroDeviation(target=250, actual=300),
            fat=MacroDeviation(target=67, actual=75),
            training_deviation=False,
            severity=DeviationSeverity.MODERATE,
            primary_deviation_type=DeviationType.CALORIE_EXCESS,
            adherence_score=70,
        )

    def test_calculate_calorie_adjustment_reduces_excess(self, engine, sample_analysis):
        """Test adjustment counteracts calorie excess."""
        adjustment = engine._calculate_calorie_adjustment(
            [sample_analysis],
            UserGoal.FAT_LOSS,
        )
        
        # Should reduce calories to compensate
        assert adjustment < 0

    def test_adjustment_capped_at_200(self, engine):
        """Test adjustment is capped at reasonable value."""
        extreme_analysis = DailyAnalysis(
            date=date(2024, 1, 1),
            calories=MacroDeviation(target=2000, actual=3000),  # +50%
            protein=MacroDeviation(target=150, actual=150),
            carbs=MacroDeviation(target=250, actual=400),
            fat=MacroDeviation(target=67, actual=100),
            training_deviation=False,
            severity=DeviationSeverity.SIGNIFICANT,
            primary_deviation_type=DeviationType.CALORIE_EXCESS,
            adherence_score=40,
        )
        
        adjustment = engine._calculate_calorie_adjustment(
            [extreme_analysis],
            UserGoal.FAT_LOSS,
        )
        
        assert -200 <= adjustment <= 200

    def test_generates_immediate_actions_for_excess(self, engine, sample_analysis):
        """Test immediate actions generated for calorie excess."""
        actions = engine._generate_immediate_actions(sample_analysis)
        
        assert len(actions) > 0
        assert any("活动" in a.action or "碳水" in a.action for a in actions)

    def test_generates_behavioral_suggestions_for_patterns(self, engine):
        """Test behavioral suggestions based on patterns."""
        patterns = ["持续热量超标", "周末执行率下降"]
        suggestions = engine._generate_behavioral_suggestions(patterns)
        
        assert len(suggestions) > 0

    def test_generate_full_adjustment_plan(self, engine, sample_analysis):
        """Test complete adjustment plan generation."""
        plan = engine.generate_adjustment_plan(
            analyses=[sample_analysis],
            patterns=["持续热量超标"],
            goal=UserGoal.FAT_LOSS,
        )
        
        assert plan.adjustment_type in ("minor", "moderate", "significant")
        assert plan.confidence > 0
        assert len(plan.reasoning) > 0

    def test_no_adjustment_for_empty_analyses(self, engine):
        """Test no adjustment when no data available."""
        plan = engine.generate_adjustment_plan(
            analyses=[],
            patterns=[],
            goal=UserGoal.FAT_LOSS,
        )
        
        assert plan.adjustment_type == "none"
        assert plan.confidence == 1.0
