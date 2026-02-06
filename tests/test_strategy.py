"""
Carbon strategy service tests.
"""

import pytest
from datetime import date

from app.models.plan import DayType, PlanCreate
from app.models.user import ActivityLevel, Gender, UserGoal, UserProfile
from app.services.carbon_strategy import CarbonStrategyService


class TestCarbonStrategyService:
    """Test carbon strategy calculation logic."""

    @pytest.fixture
    def service(self) -> CarbonStrategyService:
        """Create service instance."""
        return CarbonStrategyService()

    @pytest.fixture
    def sample_user(self) -> UserProfile:
        """Create sample user for testing."""
        return UserProfile(
            name="测试用户",
            gender=Gender.MALE,
            birth_date=date(1990, 1, 1),
            height_cm=175,
            weight_kg=75,
            target_weight_kg=70,
            goal=UserGoal.FAT_LOSS,
            activity_level=ActivityLevel.MODERATE,
            training_days_per_week=4,
        )

    def test_calculate_day_calories_high_carb(self, service):
        """Test high carb day calorie calculation."""
        calories = service.calculate_day_calories(
            base_tdee=2000,
            day_type=DayType.HIGH_CARB,
            goal=UserGoal.FAT_LOSS,
        )
        
        # High carb = TDEE * 1.10 - daily deficit
        assert 2100 <= calories <= 2200

    def test_calculate_day_calories_low_carb(self, service):
        """Test low carb day calorie calculation."""
        calories = service.calculate_day_calories(
            base_tdee=2000,
            day_type=DayType.LOW_CARB,
            goal=UserGoal.FAT_LOSS,
        )
        
        # Low carb = TDEE * 0.85 - daily deficit
        assert 1600 <= calories <= 1750

    def test_calculate_macros_protein_prioritized(self, service):
        """Test protein is calculated based on body weight."""
        macros = service.calculate_macros(
            calories=2000,
            day_type=DayType.HIGH_CARB,
            weight_kg=75,
        )
        
        # Protein should be ~2g/kg
        assert 145 <= macros.protein_g <= 155

    def test_calculate_macros_minimum_fat(self, service):
        """Test minimum fat requirement is met."""
        macros = service.calculate_macros(
            calories=1500,  # Low calories
            day_type=DayType.HIGH_CARB,
            weight_kg=75,
        )
        
        # Minimum fat should be 0.8g/kg = 60g
        assert macros.fat_g >= 60

    def test_determine_day_sequence_fat_loss(self, service):
        """Test day sequence for fat loss goal."""
        sequence = service.determine_day_sequence(
            training_days=4,
            cycle_length=7,
            goal=UserGoal.FAT_LOSS,
        )
        
        assert len(sequence) == 7
        assert sequence.count(DayType.LOW_CARB) >= 3  # More low carb days

    def test_determine_day_sequence_muscle_gain(self, service):
        """Test day sequence for muscle gain goal."""
        sequence = service.determine_day_sequence(
            training_days=4,
            cycle_length=7,
            goal=UserGoal.MUSCLE_GAIN,
        )
        
        assert sequence.count(DayType.HIGH_CARB) == 4  # All training days

    def test_generate_plan_creates_correct_days(self, service, sample_user):
        """Test plan generation creates correct number of days."""
        request = PlanCreate(
            user_id=sample_user.id,
            start_date=date(2024, 1, 1),
            cycle_length_days=7,
            num_cycles=4,
        )
        
        plan = service.generate_plan(sample_user, request)
        
        assert len(plan.days) == 28  # 7 days * 4 cycles
        assert plan.start_date == date(2024, 1, 1)

    def test_generate_plan_training_on_high_carb(self, service, sample_user):
        """Test training is scheduled on high carb days."""
        request = PlanCreate(
            user_id=sample_user.id,
            start_date=date(2024, 1, 1),
            cycle_length_days=7,
            num_cycles=1,
        )
        
        plan = service.generate_plan(sample_user, request)
        
        for day in plan.days:
            if day.day_type == DayType.HIGH_CARB:
                assert day.training_scheduled
            if day.day_type == DayType.LOW_CARB:
                assert not day.training_scheduled
