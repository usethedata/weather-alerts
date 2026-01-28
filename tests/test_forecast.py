"""
Tests for the WeatherForecast class.

These tests focus on:
1. Data normalization - converting API responses to our standard format
2. Coordinate handling
3. Error handling when APIs fail

We mock the HTTP requests so tests don't actually call weather APIs.
This makes tests fast, reliable, and doesn't use up API quotas.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from weather.forecast import WeatherForecast


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def nws_config():
    """Configuration for National Weather Service provider."""
    weather_config = {'provider': 'nws'}
    location_config = {'latitude': 35.81, 'longitude': -84.33}
    return weather_config, location_config


@pytest.fixture
def openweather_config():
    """Configuration for OpenWeatherMap provider."""
    weather_config = {'provider': 'openweather', 'api_key': 'test_api_key'}
    location_config = {'latitude': 35.81, 'longitude': -84.33}
    return weather_config, location_config


@pytest.fixture
def sample_nws_response():
    """
    Sample NWS API response data.

    NWS returns forecast periods - typically day/night pairs.
    Each period has temperature, conditions, precipitation probability, etc.
    """
    return {
        'properties': {
            'forecast': 'https://api.weather.gov/gridpoints/MRX/71,45/forecast',
            'periods': [
                {
                    'number': 1,
                    'name': 'Today',
                    'startTime': '2024-01-15T06:00:00-05:00',
                    'isDaytime': True,
                    'temperature': 45,
                    'shortForecast': 'Mostly Cloudy',
                    'probabilityOfPrecipitation': {'value': 20}
                },
                {
                    'number': 2,
                    'name': 'Tonight',
                    'startTime': '2024-01-15T18:00:00-05:00',
                    'isDaytime': False,
                    'temperature': 28,
                    'shortForecast': 'Partly Cloudy',
                    'probabilityOfPrecipitation': {'value': 10}
                },
                {
                    'number': 3,
                    'name': 'Tuesday',
                    'startTime': '2024-01-16T06:00:00-05:00',
                    'isDaytime': True,
                    'temperature': 52,
                    'shortForecast': 'Sunny',
                    'probabilityOfPrecipitation': {'value': 0}
                },
                {
                    'number': 4,
                    'name': 'Tuesday Night',
                    'startTime': '2024-01-16T18:00:00-05:00',
                    'isDaytime': False,
                    'temperature': 35,
                    'shortForecast': 'Clear',
                    'probabilityOfPrecipitation': {'value': 5}
                }
            ]
        }
    }


@pytest.fixture
def sample_openweather_response():
    """
    Sample OpenWeatherMap API response data.

    OpenWeatherMap returns 3-hour intervals, so we get multiple
    data points per day that need to be aggregated.
    """
    return {
        'list': [
            {
                'dt_txt': '2024-01-15 09:00:00',
                'main': {'temp_min': 38, 'temp_max': 42},
                'weather': [{'main': 'Clouds'}],
                'pop': 0.2
            },
            {
                'dt_txt': '2024-01-15 12:00:00',
                'main': {'temp_min': 42, 'temp_max': 48},
                'weather': [{'main': 'Clouds'}],
                'pop': 0.15
            },
            {
                'dt_txt': '2024-01-15 18:00:00',
                'main': {'temp_min': 35, 'temp_max': 45},
                'weather': [{'main': 'Clear'}],
                'pop': 0.1
            },
            {
                'dt_txt': '2024-01-16 09:00:00',
                'main': {'temp_min': 30, 'temp_max': 40},
                'weather': [{'main': 'Rain'}],
                'pop': 0.8
            },
            {
                'dt_txt': '2024-01-16 15:00:00',
                'main': {'temp_min': 32, 'temp_max': 38},
                'weather': [{'main': 'Rain'}],
                'pop': 0.9
            }
        ]
    }


# =============================================================================
# TESTS FOR coordinate handling
# =============================================================================

class TestCoordinates:
    """Tests for getting coordinates from configuration."""

    def test_get_coordinates_from_lat_lon(self, nws_config):
        """Test extracting coordinates when lat/lon are provided."""
        weather_config, location_config = nws_config
        forecast = WeatherForecast(weather_config, location_config)

        lat, lon = forecast._get_coordinates()

        assert lat == 35.81
        assert lon == -84.33

    def test_get_coordinates_zip_only_fails(self, capsys):
        """Test that zip code only configuration shows an error."""
        weather_config = {'provider': 'nws'}
        location_config = {'zip_code': '37771'}  # No lat/lon

        forecast = WeatherForecast(weather_config, location_config)
        lat, lon = forecast._get_coordinates()

        assert lat is None
        assert lon is None

        captured = capsys.readouterr()
        assert "Please provide latitude and longitude" in captured.out

    def test_get_coordinates_empty_config(self, capsys):
        """Test handling of empty location configuration."""
        weather_config = {'provider': 'nws'}
        location_config = {}

        forecast = WeatherForecast(weather_config, location_config)
        lat, lon = forecast._get_coordinates()

        assert lat is None
        assert lon is None


# =============================================================================
# TESTS FOR NWS data normalization
# =============================================================================

class TestNWSNormalization:
    """Tests for normalizing National Weather Service API data."""

    def test_normalize_nws_data_basic(self, nws_config, sample_nws_response):
        """Test basic NWS data normalization."""
        weather_config, location_config = nws_config
        forecast = WeatherForecast(weather_config, location_config)

        periods = sample_nws_response['properties']['periods']
        result = forecast._normalize_nws_data(periods, days=2)

        # Should have 2 days
        assert len(result) == 2

        # Check first day
        day1 = result[0]
        assert day1['date'] == '2024-01-15'
        assert day1['temperature_max'] == 45  # Daytime temp
        assert day1['temperature_min'] == 28  # Nighttime temp
        assert day1['precipitation_probability'] == 20  # Max of day/night

    def test_normalize_nws_data_respects_days_limit(self, nws_config, sample_nws_response):
        """Test that the days parameter limits output."""
        weather_config, location_config = nws_config
        forecast = WeatherForecast(weather_config, location_config)

        periods = sample_nws_response['properties']['periods']
        result = forecast._normalize_nws_data(periods, days=1)

        assert len(result) == 1
        assert result[0]['date'] == '2024-01-15'

    def test_normalize_nws_data_handles_null_precip(self, nws_config):
        """Test handling of null precipitation probability."""
        weather_config, location_config = nws_config
        forecast = WeatherForecast(weather_config, location_config)

        periods = [
            {
                'startTime': '2024-01-15T06:00:00-05:00',
                'isDaytime': True,
                'temperature': 45,
                'shortForecast': 'Sunny',
                'probabilityOfPrecipitation': {'value': None}  # Can be null
            }
        ]

        result = forecast._normalize_nws_data(periods, days=1)

        # Should default to 0, not crash
        assert result[0]['precipitation_probability'] == 0


# =============================================================================
# TESTS FOR OpenWeatherMap data normalization
# =============================================================================

class TestOpenWeatherNormalization:
    """Tests for normalizing OpenWeatherMap API data."""

    def test_normalize_openweather_data_basic(self, openweather_config, sample_openweather_response):
        """Test basic OpenWeatherMap data normalization."""
        weather_config, location_config = openweather_config
        forecast = WeatherForecast(weather_config, location_config)

        result = forecast._normalize_openweather_data(
            sample_openweather_response['list'],
            days=2
        )

        # Should have 2 days
        assert len(result) == 2

        # Check first day - should aggregate multiple readings
        day1 = result[0]
        assert day1['date'] == '2024-01-15'
        assert day1['temperature_min'] == 35  # Min of all readings
        assert day1['temperature_max'] == 48  # Max of all readings
        assert day1['precipitation_probability'] == 20  # Max pop (0.2 * 100)

    def test_normalize_openweather_aggregates_conditions(self, openweather_config, sample_openweather_response):
        """Test that weather conditions are aggregated."""
        weather_config, location_config = openweather_config
        forecast = WeatherForecast(weather_config, location_config)

        result = forecast._normalize_openweather_data(
            sample_openweather_response['list'],
            days=2
        )

        # First day should have both Clouds and Clear
        assert 'Clouds' in result[0]['conditions']
        assert 'Clear' in result[0]['conditions']


# =============================================================================
# TESTS FOR full API flow (with mocked requests)
# =============================================================================

class TestAPIIntegration:
    """
    Tests for the full get_forecast() method with mocked HTTP.

    These tests verify the complete flow:
    1. Call the right API endpoints
    2. Parse the response correctly
    3. Return normalized data
    """

    @patch('weather.forecast.requests.get')
    def test_nws_forecast_success(self, mock_get, nws_config, sample_nws_response):
        """Test successful NWS forecast retrieval."""
        weather_config, location_config = nws_config
        forecast = WeatherForecast(weather_config, location_config)

        # Set up mock responses for the two NWS API calls
        # First call: points endpoint returns forecast URL
        # Second call: forecast endpoint returns actual forecast
        points_response = MagicMock()
        points_response.json.return_value = {
            'properties': {
                'forecast': 'https://api.weather.gov/gridpoints/MRX/71,45/forecast'
            }
        }
        points_response.raise_for_status = MagicMock()

        forecast_response = MagicMock()
        forecast_response.json.return_value = sample_nws_response
        forecast_response.raise_for_status = MagicMock()

        # Return different responses for each call
        mock_get.side_effect = [points_response, forecast_response]

        result = forecast.get_forecast(days=2)

        assert result is not None
        assert len(result) == 2
        assert result[0]['temperature_min'] == 28

    @patch('weather.forecast.requests.get')
    def test_nws_forecast_network_error(self, mock_get, nws_config):
        """Test handling of network errors."""
        import requests

        weather_config, location_config = nws_config
        forecast = WeatherForecast(weather_config, location_config)

        # Simulate a network error
        mock_get.side_effect = requests.RequestException("Network error")

        result = forecast.get_forecast()

        # Should return None, not crash
        assert result is None

    @patch('weather.forecast.requests.get')
    def test_openweather_forecast_success(self, mock_get, openweather_config, sample_openweather_response):
        """Test successful OpenWeatherMap forecast retrieval."""
        weather_config, location_config = openweather_config
        forecast = WeatherForecast(weather_config, location_config)

        mock_response = MagicMock()
        mock_response.json.return_value = sample_openweather_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = forecast.get_forecast(days=2)

        assert result is not None
        assert len(result) == 2

        # Verify API was called with correct parameters
        call_args = mock_get.call_args
        assert call_args[1]['params']['appid'] == 'test_api_key'
        assert call_args[1]['params']['units'] == 'imperial'

    def test_openweather_missing_api_key(self, capsys):
        """Test that missing API key is handled."""
        weather_config = {'provider': 'openweather'}  # No api_key
        location_config = {'latitude': 35.81, 'longitude': -84.33}

        forecast = WeatherForecast(weather_config, location_config)
        result = forecast.get_forecast()

        assert result is None

        captured = capsys.readouterr()
        assert "API key not configured" in captured.out

    def test_unknown_provider(self, capsys):
        """Test handling of unknown weather provider."""
        weather_config = {'provider': 'unknown_service'}
        location_config = {'latitude': 35.81, 'longitude': -84.33}

        forecast = WeatherForecast(weather_config, location_config)
        result = forecast.get_forecast()

        assert result is None

        captured = capsys.readouterr()
        assert "Unknown weather provider" in captured.out
