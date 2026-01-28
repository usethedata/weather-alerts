"""Condition evaluation for weather alerts."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class ConditionEvaluator:
    """Evaluate weather conditions and track state."""

    def __init__(self, state_file: str):
        """Initialize condition evaluator.

        Args:
            state_file: Path to state file for tracking occurrences
        """
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return {'occurrences': {}}

    def save_state(self):
        """Save state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            print(f"Warning: Failed to save state: {e}")

    def evaluate(self, condition: Dict[str, Any], forecast_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a condition against forecast data.

        Args:
            condition: Condition configuration
            forecast_data: List of daily forecast data

        Returns:
            Dict with 'triggered' (bool) and optional 'context' (dict) for template substitution
        """
        condition_type = condition.get('type', 'threshold')

        if condition_type == 'threshold':
            return self._evaluate_threshold(condition, forecast_data)
        elif condition_type == 'first_occurrence':
            return self._evaluate_first_occurrence(condition, forecast_data)
        elif condition_type == 'combined':
            return self._evaluate_combined(condition, forecast_data)
        else:
            print(f"Warning: Unknown condition type: {condition_type}")
            return {'triggered': False}

    def _evaluate_threshold(self, condition: Dict[str, Any], forecast_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a simple threshold condition.

        Args:
            condition: Condition with weather_condition field
            forecast_data: Forecast data

        Returns:
            Evaluation result
        """
        weather_cond = condition['weather_condition']
        field = weather_cond['field']
        operator = weather_cond['operator']
        threshold = weather_cond['value']
        forecast_days = weather_cond.get('forecast_days', 1)

        # Check forecast data up to specified days
        for day_data in forecast_data[:forecast_days]:
            value = day_data.get(field)

            if value is None:
                continue

            if self._compare_value(value, operator, threshold):
                return {
                    'triggered': True,
                    'context': {
                        'forecast_date': day_data['date'],
                        field: value
                    }
                }

        return {'triggered': False}

    def _evaluate_first_occurrence(self, condition: Dict[str, Any], forecast_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a first occurrence condition (e.g., first freeze of season).

        Args:
            condition: Condition with weather_condition and season info
            forecast_data: Forecast data

        Returns:
            Evaluation result
        """
        # Check if we're in the right season
        now = datetime.now()
        season_start = condition.get('season_start_month', 1)
        season_end = condition.get('season_end_month', 12)

        if not self._is_in_season(now.month, season_start, season_end):
            return {'triggered': False}

        # Generate a state key for this condition
        state_key = f"first_{condition['weather_condition']['field']}_{season_start}_{season_end}"
        current_year = now.year

        # Check if this has already occurred this season
        if state_key in self.state['occurrences']:
            last_occurrence = self.state['occurrences'][state_key]
            if last_occurrence.get('year') == current_year:
                # Already occurred this season
                return {'triggered': False}

        # Evaluate the underlying weather condition
        weather_result = self._evaluate_threshold(condition, forecast_data)

        if weather_result['triggered']:
            # Mark this as occurred
            self.state['occurrences'][state_key] = {
                'year': current_year,
                'date': str(now.date()),
                'forecast_date': weather_result['context']['forecast_date']
            }
            return weather_result

        return {'triggered': False}

    def _evaluate_combined(self, condition: Dict[str, Any], forecast_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate combined conditions (multiple conditions ANDed or ORed).

        Args:
            condition: Condition with weather_conditions list
            forecast_data: Forecast data

        Returns:
            Evaluation result
        """
        weather_conds = condition['weather_conditions']
        all_must_match = condition.get('all_must_match', True)

        contexts = []
        matches = 0

        for weather_cond in weather_conds:
            # Create a threshold condition for each
            temp_condition = {
                'type': 'threshold',
                'weather_condition': weather_cond
            }
            result = self._evaluate_threshold(temp_condition, forecast_data)

            if result['triggered']:
                matches += 1
                contexts.append(result['context'])

        if all_must_match:
            triggered = matches == len(weather_conds)
        else:
            triggered = matches > 0

        if triggered:
            # Merge contexts
            merged_context = {}
            for ctx in contexts:
                merged_context.update(ctx)
            return {'triggered': True, 'context': merged_context}

        return {'triggered': False}

    def _compare_value(self, value: float, operator: str, threshold: float) -> bool:
        """Compare a value against a threshold using the specified operator.

        Args:
            value: Value to compare
            operator: Comparison operator (lt, lte, gt, gte, eq)
            threshold: Threshold value

        Returns:
            True if comparison passes
        """
        if operator == 'lt':
            return value < threshold
        elif operator == 'lte':
            return value <= threshold
        elif operator == 'gt':
            return value > threshold
        elif operator == 'gte':
            return value >= threshold
        elif operator == 'eq':
            return value == threshold
        else:
            print(f"Warning: Unknown operator: {operator}")
            return False

    def _is_in_season(self, current_month: int, start_month: int, end_month: int) -> bool:
        """Check if current month is within season.

        Args:
            current_month: Current month (1-12)
            start_month: Season start month
            end_month: Season end month

        Returns:
            True if in season
        """
        if start_month <= end_month:
            return start_month <= current_month <= end_month
        else:
            # Season wraps around year end
            return current_month >= start_month or current_month <= end_month
