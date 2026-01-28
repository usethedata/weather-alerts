"""
Tests for the main module, including command-line argument parsing and dry-run mode.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import parse_args, main


# =============================================================================
# TESTS FOR argument parsing
# =============================================================================

class TestParseArgs:
    """Tests for command-line argument parsing."""

    def test_no_arguments(self):
        """Test default behavior with no arguments."""
        with patch('sys.argv', ['main.py']):
            args = parse_args()
            assert args.dry_run is False

    def test_dry_run_flag(self):
        """Test --dry-run flag is recognized."""
        with patch('sys.argv', ['main.py', '--dry-run']):
            args = parse_args()
            assert args.dry_run is True

    def test_help_flag_exits(self):
        """Test that --help exits gracefully."""
        with patch('sys.argv', ['main.py', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                parse_args()
            # argparse exits with 0 for --help
            assert exc_info.value.code == 0


# =============================================================================
# TESTS FOR dry-run mode
# =============================================================================

class TestDryRunMode:
    """Tests for dry-run functionality."""

    @pytest.fixture
    def mock_config(self):
        """Sample configuration for testing."""
        return {
            'weather': {'provider': 'nws'},
            'location': {'latitude': 35.81, 'longitude': -84.33},
            'email': {
                'smtp_host': 'smtp.example.com',
                'smtp_port': 465,
                'use_ssl': True,
                'username': 'test@example.com',
                'password': 'password',
                'from_address': 'test@example.com',
                'to_addresses': ['recipient@example.com']
            },
            'state_file': '/tmp/test_state.json',
            'alert_rules': [
                {
                    'name': 'Test Freeze Alert',
                    'enabled': True,
                    'condition': {
                        'type': 'threshold',
                        'weather_condition': {
                            'field': 'temperature_min',
                            'operator': 'lte',
                            'value': 32,
                            'forecast_days': 2
                        }
                    },
                    'action': {
                        'type': 'email',
                        'subject': 'Freeze Alert',
                        'body': 'Freezing temps expected'
                    }
                }
            ]
        }

    @pytest.fixture
    def mock_forecast_data(self):
        """Sample forecast data that triggers the freeze alert."""
        return [
            {
                'date': '2024-01-15',
                'temperature_min': 28,
                'temperature_max': 45,
                'precipitation_probability': 20
            }
        ]

    @patch('main.load_config')
    @patch('main.WeatherForecast')
    @patch('main.ConditionEvaluator')
    @patch('main.EmailAction')
    def test_dry_run_does_not_send_email(
        self, mock_email_class, mock_evaluator_class, mock_weather_class,
        mock_load_config, mock_config, mock_forecast_data, capsys
    ):
        """Test that dry-run mode does not instantiate EmailAction or send emails."""
        # Setup mocks
        mock_load_config.return_value = mock_config

        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = mock_forecast_data
        mock_weather_class.return_value = mock_weather

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            'triggered': True,
            'context': {'temperature_min': 28, 'forecast_date': '2024-01-15'}
        }
        mock_evaluator_class.return_value = mock_evaluator

        # Run in dry-run mode
        main(dry_run=True)

        # EmailAction should NOT be instantiated in dry-run mode
        mock_email_class.assert_not_called()

    @patch('main.load_config')
    @patch('main.WeatherForecast')
    @patch('main.ConditionEvaluator')
    def test_dry_run_outputs_triggered_alerts(
        self, mock_evaluator_class, mock_weather_class,
        mock_load_config, mock_config, mock_forecast_data, capsys
    ):
        """Test that dry-run mode outputs triggered alerts to stdout."""
        # Setup mocks
        mock_load_config.return_value = mock_config

        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = mock_forecast_data
        mock_weather_class.return_value = mock_weather

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            'triggered': True,
            'context': {'temperature_min': 28, 'forecast_date': '2024-01-15'}
        }
        mock_evaluator_class.return_value = mock_evaluator

        # Run in dry-run mode
        main(dry_run=True)

        # Check stdout for triggered alert output
        captured = capsys.readouterr()
        assert "TRIGGERED: Test Freeze Alert" in captured.out
        assert "temperature_min=28" in captured.out
        assert "forecast_date=2024-01-15" in captured.out

    @patch('main.load_config')
    @patch('main.WeatherForecast')
    @patch('main.ConditionEvaluator')
    def test_dry_run_no_output_when_not_triggered(
        self, mock_evaluator_class, mock_weather_class,
        mock_load_config, mock_config, mock_forecast_data, capsys
    ):
        """Test that dry-run mode produces no TRIGGERED output when conditions aren't met."""
        # Setup mocks
        mock_load_config.return_value = mock_config

        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = mock_forecast_data
        mock_weather_class.return_value = mock_weather

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {'triggered': False}
        mock_evaluator_class.return_value = mock_evaluator

        # Run in dry-run mode
        main(dry_run=True)

        # Check stdout - should not contain TRIGGERED
        captured = capsys.readouterr()
        assert "TRIGGERED" not in captured.out

    @patch('main.load_config')
    @patch('main.WeatherForecast')
    @patch('main.ConditionEvaluator')
    def test_dry_run_still_saves_state(
        self, mock_evaluator_class, mock_weather_class,
        mock_load_config, mock_config, mock_forecast_data
    ):
        """Test that dry-run mode still saves state (for first_occurrence tracking)."""
        # Setup mocks
        mock_load_config.return_value = mock_config

        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = mock_forecast_data
        mock_weather_class.return_value = mock_weather

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {'triggered': False}
        mock_evaluator_class.return_value = mock_evaluator

        # Run in dry-run mode
        main(dry_run=True)

        # State should still be saved
        mock_evaluator.save_state.assert_called_once()


# =============================================================================
# TESTS FOR normal mode (to ensure we didn't break it)
# =============================================================================

class TestNormalMode:
    """Tests to verify normal (non-dry-run) mode still works."""

    @pytest.fixture
    def mock_config(self):
        """Sample configuration for testing."""
        return {
            'weather': {'provider': 'nws'},
            'location': {'latitude': 35.81, 'longitude': -84.33},
            'email': {
                'smtp_host': 'smtp.example.com',
                'smtp_port': 465,
                'use_ssl': True,
                'username': 'test@example.com',
                'password': 'password',
                'from_address': 'test@example.com',
                'to_addresses': ['recipient@example.com']
            },
            'state_file': '/tmp/test_state.json',
            'alert_rules': [
                {
                    'name': 'Test Alert',
                    'enabled': True,
                    'condition': {
                        'type': 'threshold',
                        'weather_condition': {
                            'field': 'temperature_min',
                            'operator': 'lte',
                            'value': 32,
                            'forecast_days': 1
                        }
                    },
                    'action': {
                        'type': 'email',
                        'subject': 'Test',
                        'body': 'Test body'
                    }
                }
            ]
        }

    @pytest.fixture
    def mock_forecast_data(self):
        """Sample forecast data."""
        return [{'date': '2024-01-15', 'temperature_min': 28, 'temperature_max': 45}]

    @patch('main.load_config')
    @patch('main.WeatherForecast')
    @patch('main.ConditionEvaluator')
    @patch('main.EmailAction')
    def test_normal_mode_sends_email(
        self, mock_email_class, mock_evaluator_class, mock_weather_class,
        mock_load_config, mock_config, mock_forecast_data
    ):
        """Test that normal mode does send emails when conditions are triggered."""
        # Setup mocks
        mock_load_config.return_value = mock_config

        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = mock_forecast_data
        mock_weather_class.return_value = mock_weather

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            'triggered': True,
            'context': {'temperature_min': 28}
        }
        mock_evaluator_class.return_value = mock_evaluator

        mock_email = MagicMock()
        mock_email_class.return_value = mock_email

        # Run in normal mode
        main(dry_run=False)

        # EmailAction should be instantiated and send() called
        mock_email_class.assert_called_once()
        mock_email.send.assert_called_once()
