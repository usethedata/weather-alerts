"""
Tests for the ConditionEvaluator class.

=== PYTHON TESTING PRIMER ===

Python testing with pytest works like this:

1. TEST DISCOVERY: pytest automatically finds files named test_*.py or *_test.py
   and runs functions that start with "test_".

2. ASSERTIONS: Tests use Python's "assert" statement. If the assertion is True,
   the test passes. If False, the test fails with a helpful error message.

   Example:
       assert 1 + 1 == 2      # Passes
       assert 1 + 1 == 3      # Fails with: AssertionError: assert 2 == 3

3. FIXTURES: Reusable setup code. The @pytest.fixture decorator creates a function
   that returns test data or objects. Tests request fixtures by including them
   as parameters - pytest automatically calls the fixture and passes the result.

4. ARRANGE-ACT-ASSERT: Most tests follow this pattern:
   - Arrange: Set up the test data and conditions
   - Act: Call the code being tested
   - Assert: Verify the result is what you expected

5. RUNNING TESTS: From your project directory with the venv activated:
       python -m pytest tests/                    # Run all tests
       python -m pytest tests/test_evaluator.py  # Run one test file
       python -m pytest -v                        # Verbose output (shows each test name)
       python -m pytest -v -s                     # Also show print statements
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

# Import the class we're testing
# Note: We need to add src/ to Python's path so it can find our modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from conditions.evaluator import ConditionEvaluator


# =============================================================================
# FIXTURES - Reusable test setup
# =============================================================================

@pytest.fixture
def temp_state_file():
    """
    Create a temporary file for state storage during tests.

    This fixture uses Python's tempfile module to create a file that:
    - Is automatically cleaned up after the test
    - Doesn't interfere with other tests or real state files

    The 'yield' statement is like 'return', but allows cleanup code after the test.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    yield temp_path  # This value is passed to the test

    # Cleanup after test completes
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def evaluator(temp_state_file):
    """
    Create a ConditionEvaluator with a temporary state file.

    This fixture depends on another fixture (temp_state_file).
    pytest handles this automatically - it runs temp_state_file first,
    then passes its result to this fixture.
    """
    return ConditionEvaluator(temp_state_file)


@pytest.fixture
def sample_forecast_data():
    """
    Create sample forecast data that mimics what the weather API returns.

    This is "fake" data that lets us test the evaluator without
    actually calling the weather API.
    """
    return [
        {
            'date': '2024-01-15',
            'temperature_min': 28,  # Below freezing
            'temperature_max': 45,
            'precipitation_probability': 20,
            'conditions': 'Partly Cloudy'
        },
        {
            'date': '2024-01-16',
            'temperature_min': 35,
            'temperature_max': 52,
            'precipitation_probability': 10,
            'conditions': 'Sunny'
        },
        {
            'date': '2024-01-17',
            'temperature_min': 40,
            'temperature_max': 65,
            'precipitation_probability': 80,
            'conditions': 'Rain'
        }
    ]


# =============================================================================
# TESTS FOR _compare_value (the basic comparison operator)
# =============================================================================

class TestCompareValue:
    """
    Group related tests in a class for organization.

    The class name must start with "Test" for pytest to find it.
    Methods must start with "test_".
    """

    def test_less_than_true(self, evaluator):
        """Test that 'lt' (less than) returns True when value < threshold."""
        # Arrange & Act & Assert combined for simple tests
        assert evaluator._compare_value(30, 'lt', 32) is True

    def test_less_than_false(self, evaluator):
        """Test that 'lt' returns False when value >= threshold."""
        assert evaluator._compare_value(32, 'lt', 32) is False
        assert evaluator._compare_value(35, 'lt', 32) is False

    def test_less_than_or_equal_true(self, evaluator):
        """Test that 'lte' returns True when value <= threshold."""
        assert evaluator._compare_value(30, 'lte', 32) is True
        assert evaluator._compare_value(32, 'lte', 32) is True  # Equal case

    def test_less_than_or_equal_false(self, evaluator):
        """Test that 'lte' returns False when value > threshold."""
        assert evaluator._compare_value(35, 'lte', 32) is False

    def test_greater_than_true(self, evaluator):
        """Test that 'gt' returns True when value > threshold."""
        assert evaluator._compare_value(100, 'gt', 90) is True

    def test_greater_than_false(self, evaluator):
        """Test that 'gt' returns False when value <= threshold."""
        assert evaluator._compare_value(90, 'gt', 90) is False
        assert evaluator._compare_value(85, 'gt', 90) is False

    def test_greater_than_or_equal_true(self, evaluator):
        """Test that 'gte' returns True when value >= threshold."""
        assert evaluator._compare_value(100, 'gte', 90) is True
        assert evaluator._compare_value(90, 'gte', 90) is True  # Equal case

    def test_greater_than_or_equal_false(self, evaluator):
        """Test that 'gte' returns False when value < threshold."""
        assert evaluator._compare_value(85, 'gte', 90) is False

    def test_equal_true(self, evaluator):
        """Test that 'eq' returns True when values match."""
        assert evaluator._compare_value(32, 'eq', 32) is True

    def test_equal_false(self, evaluator):
        """Test that 'eq' returns False when values don't match."""
        assert evaluator._compare_value(30, 'eq', 32) is False

    def test_unknown_operator(self, evaluator):
        """Test that unknown operators return False (safe default)."""
        assert evaluator._compare_value(30, 'unknown', 32) is False


# =============================================================================
# TESTS FOR _is_in_season
# =============================================================================

class TestIsInSeason:
    """Tests for the season checking logic."""

    def test_normal_season_in_range(self, evaluator):
        """Test month within a normal season (e.g., Aug-Dec for fall freeze alerts)."""
        # October is between August (8) and December (12)
        assert evaluator._is_in_season(10, 8, 12) is True

    def test_normal_season_at_start(self, evaluator):
        """Test month at season start boundary."""
        assert evaluator._is_in_season(8, 8, 12) is True

    def test_normal_season_at_end(self, evaluator):
        """Test month at season end boundary."""
        assert evaluator._is_in_season(12, 8, 12) is True

    def test_normal_season_before_start(self, evaluator):
        """Test month before season starts."""
        assert evaluator._is_in_season(7, 8, 12) is False

    def test_normal_season_after_end(self, evaluator):
        """Test month after season ends."""
        assert evaluator._is_in_season(1, 8, 12) is False

    def test_wrapped_season_in_first_part(self, evaluator):
        """
        Test season that wraps around year end (e.g., Nov-Feb for winter).
        Month in the first part (Nov-Dec).
        """
        assert evaluator._is_in_season(11, 11, 2) is True
        assert evaluator._is_in_season(12, 11, 2) is True

    def test_wrapped_season_in_second_part(self, evaluator):
        """Test wrapped season, month in second part (Jan-Feb)."""
        assert evaluator._is_in_season(1, 11, 2) is True
        assert evaluator._is_in_season(2, 11, 2) is True

    def test_wrapped_season_outside(self, evaluator):
        """Test wrapped season, month outside the range."""
        assert evaluator._is_in_season(5, 11, 2) is False
        assert evaluator._is_in_season(10, 11, 2) is False


# =============================================================================
# TESTS FOR threshold condition evaluation
# =============================================================================

class TestThresholdCondition:
    """Tests for simple threshold conditions (e.g., temp <= 32)."""

    def test_threshold_triggered_first_day(self, evaluator, sample_forecast_data):
        """Test that a condition triggers when met on the first forecast day."""
        # Arrange: Create a condition checking for freezing temps
        condition = {
            'type': 'threshold',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32,
                'forecast_days': 2
            }
        }

        # Act: Evaluate the condition
        result = evaluator.evaluate(condition, sample_forecast_data)

        # Assert: Should trigger because day 1 has temp_min of 28
        assert result['triggered'] is True
        assert result['context']['temperature_min'] == 28
        assert result['context']['forecast_date'] == '2024-01-15'

    def test_threshold_not_triggered(self, evaluator, sample_forecast_data):
        """Test that a condition doesn't trigger when not met."""
        condition = {
            'type': 'threshold',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 15,  # Very cold - not in our sample data
                'forecast_days': 3
            }
        }

        result = evaluator.evaluate(condition, sample_forecast_data)

        assert result['triggered'] is False
        assert 'context' not in result

    def test_threshold_respects_forecast_days(self, evaluator, sample_forecast_data):
        """Test that forecast_days limits how far ahead we look."""
        # This condition would be met on day 3, but we only look at day 1
        condition = {
            'type': 'threshold',
            'weather_condition': {
                'field': 'precipitation_probability',
                'operator': 'gte',
                'value': 80,
                'forecast_days': 1  # Only check first day (20% precip)
            }
        }

        result = evaluator.evaluate(condition, sample_forecast_data)

        # Should NOT trigger - 80% is on day 3, we only look at day 1
        assert result['triggered'] is False

    def test_threshold_finds_later_day(self, evaluator, sample_forecast_data):
        """Test that we can find conditions on later days within the window."""
        condition = {
            'type': 'threshold',
            'weather_condition': {
                'field': 'precipitation_probability',
                'operator': 'gte',
                'value': 80,
                'forecast_days': 3  # Check all 3 days
            }
        }

        result = evaluator.evaluate(condition, sample_forecast_data)

        # Should trigger - day 3 has 80% precipitation
        assert result['triggered'] is True
        assert result['context']['forecast_date'] == '2024-01-17'


# =============================================================================
# TESTS FOR combined conditions
# =============================================================================

class TestCombinedCondition:
    """Tests for combined conditions (multiple conditions ANDed or ORed)."""

    def test_combined_all_match_success(self, evaluator):
        """Test AND logic - all conditions must match."""
        forecast = [
            {
                'date': '2024-07-15',
                'temperature_max': 95,  # Hot
                'precipitation_probability': 5  # Dry
            }
        ]

        condition = {
            'type': 'combined',
            'all_must_match': True,  # AND logic
            'weather_conditions': [
                {'field': 'temperature_max', 'operator': 'gte', 'value': 90, 'forecast_days': 1},
                {'field': 'precipitation_probability', 'operator': 'lte', 'value': 10, 'forecast_days': 1}
            ]
        }

        result = evaluator.evaluate(condition, forecast)

        assert result['triggered'] is True
        assert result['context']['temperature_max'] == 95
        assert result['context']['precipitation_probability'] == 5

    def test_combined_all_match_partial_failure(self, evaluator):
        """Test AND logic fails when only some conditions match."""
        forecast = [
            {
                'date': '2024-07-15',
                'temperature_max': 85,  # Not hot enough
                'precipitation_probability': 5  # Dry
            }
        ]

        condition = {
            'type': 'combined',
            'all_must_match': True,
            'weather_conditions': [
                {'field': 'temperature_max', 'operator': 'gte', 'value': 90, 'forecast_days': 1},
                {'field': 'precipitation_probability', 'operator': 'lte', 'value': 10, 'forecast_days': 1}
            ]
        }

        result = evaluator.evaluate(condition, forecast)

        # Should NOT trigger - temperature condition not met
        assert result['triggered'] is False

    def test_combined_any_match_success(self, evaluator):
        """Test OR logic - any condition matching is enough."""
        forecast = [
            {
                'date': '2024-07-15',
                'temperature_max': 85,  # Not hot
                'precipitation_probability': 5  # But dry
            }
        ]

        condition = {
            'type': 'combined',
            'all_must_match': False,  # OR logic
            'weather_conditions': [
                {'field': 'temperature_max', 'operator': 'gte', 'value': 90, 'forecast_days': 1},
                {'field': 'precipitation_probability', 'operator': 'lte', 'value': 10, 'forecast_days': 1}
            ]
        }

        result = evaluator.evaluate(condition, forecast)

        # Should trigger - dry condition is met
        assert result['triggered'] is True


# =============================================================================
# TESTS FOR first_occurrence conditions
# =============================================================================

class TestFirstOccurrenceCondition:
    """
    Tests for first_occurrence conditions (e.g., "first freeze of the season").

    These tests need to mock datetime.now() to control what "today" is,
    since the condition checks the current month against the season.
    """

    def test_first_occurrence_triggers_in_season(self, evaluator, sample_forecast_data):
        """Test that first occurrence triggers when in season and condition met."""
        condition = {
            'type': 'first_occurrence',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32,
                'forecast_days': 2
            },
            'season_start_month': 8,
            'season_end_month': 12
        }

        # Mock datetime.now() to return October (month 10, in season)
        with patch('conditions.evaluator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 10, 15)

            result = evaluator.evaluate(condition, sample_forecast_data)

        assert result['triggered'] is True

    def test_first_occurrence_not_triggered_out_of_season(self, evaluator, sample_forecast_data):
        """Test that first occurrence doesn't trigger outside the season."""
        condition = {
            'type': 'first_occurrence',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32,
                'forecast_days': 2
            },
            'season_start_month': 8,
            'season_end_month': 12
        }

        # Mock datetime.now() to return July (month 7, before season)
        with patch('conditions.evaluator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 7, 15)

            result = evaluator.evaluate(condition, sample_forecast_data)

        assert result['triggered'] is False

    def test_first_occurrence_only_triggers_once(self, evaluator, sample_forecast_data):
        """Test that first occurrence only triggers once per season."""
        condition = {
            'type': 'first_occurrence',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32,
                'forecast_days': 2
            },
            'season_start_month': 8,
            'season_end_month': 12
        }

        with patch('conditions.evaluator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 10, 15)

            # First evaluation - should trigger
            result1 = evaluator.evaluate(condition, sample_forecast_data)
            assert result1['triggered'] is True

            # Second evaluation (same season) - should NOT trigger
            result2 = evaluator.evaluate(condition, sample_forecast_data)
            assert result2['triggered'] is False


# =============================================================================
# TESTS FOR state persistence
# =============================================================================

class TestStatePersistence:
    """Tests for saving and loading state across evaluator instances."""

    def test_state_persists_across_instances(self, temp_state_file, sample_forecast_data):
        """Test that state is saved and loaded correctly."""
        condition = {
            'type': 'first_occurrence',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32,
                'forecast_days': 2
            },
            'season_start_month': 8,
            'season_end_month': 12
        }

        with patch('conditions.evaluator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 10, 15)

            # First instance - trigger the condition
            evaluator1 = ConditionEvaluator(temp_state_file)
            result1 = evaluator1.evaluate(condition, sample_forecast_data)
            evaluator1.save_state()  # Save state to file

            assert result1['triggered'] is True

            # Second instance - load state from file
            evaluator2 = ConditionEvaluator(temp_state_file)
            result2 = evaluator2.evaluate(condition, sample_forecast_data)

            # Should NOT trigger - previous occurrence is remembered
            assert result2['triggered'] is False

    def test_handles_missing_state_file(self, temp_state_file):
        """Test that evaluator handles missing state file gracefully."""
        # Delete the temp file to simulate first run
        Path(temp_state_file).unlink(missing_ok=True)

        # Should not raise an error
        evaluator = ConditionEvaluator(temp_state_file)

        assert evaluator.state == {'occurrences': {}}

    def test_handles_corrupted_state_file(self, temp_state_file):
        """Test that evaluator handles corrupted state file gracefully."""
        # Write invalid JSON to the state file
        with open(temp_state_file, 'w') as f:
            f.write("this is not valid json {{{")

        # Should not raise an error, should start with empty state
        evaluator = ConditionEvaluator(temp_state_file)

        assert evaluator.state == {'occurrences': {}}


# =============================================================================
# TESTS FOR edge cases and error handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unknown_condition_type(self, evaluator, sample_forecast_data):
        """Test that unknown condition types are handled safely."""
        condition = {
            'type': 'some_future_type',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32
            }
        }

        result = evaluator.evaluate(condition, sample_forecast_data)

        # Should return not triggered (safe default)
        assert result['triggered'] is False

    def test_missing_field_in_forecast(self, evaluator):
        """Test handling of forecast data missing the required field."""
        forecast = [
            {
                'date': '2024-01-15',
                # temperature_min is missing!
                'temperature_max': 45
            }
        ]

        condition = {
            'type': 'threshold',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32,
                'forecast_days': 1
            }
        }

        result = evaluator.evaluate(condition, forecast)

        # Should not trigger - field is missing
        assert result['triggered'] is False

    def test_empty_forecast_data(self, evaluator):
        """Test handling of empty forecast data."""
        condition = {
            'type': 'threshold',
            'weather_condition': {
                'field': 'temperature_min',
                'operator': 'lte',
                'value': 32,
                'forecast_days': 1
            }
        }

        result = evaluator.evaluate(condition, [])

        assert result['triggered'] is False
