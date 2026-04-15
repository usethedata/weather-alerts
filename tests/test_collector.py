"""Tests for the ForecastCollector class."""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from collection.collector import ForecastCollector


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def collection_config(temp_data_dir):
    """Sample collection configuration."""
    return {
        'data_directory': temp_data_dir,
        'forecast_days': 10,
        'sources': ['nws'],
    }


@pytest.fixture
def weather_config():
    return {'provider': 'nws'}


@pytest.fixture
def location_config():
    return {'latitude': 35.81, 'longitude': -84.33}


@pytest.fixture
def sample_forecast():
    """Sample normalized forecast data."""
    return [
        {
            'date': '2026-04-13',
            'temperature_min': 55,
            'temperature_max': 72,
            'precipitation_probability': 10,
            'conditions': 'Mostly Sunny',
            'raw_data': {}
        },
        {
            'date': '2026-04-14',
            'temperature_min': 58,
            'temperature_max': 75,
            'precipitation_probability': 20,
            'conditions': 'Partly Cloudy',
            'raw_data': {}
        },
    ]


class TestForecastCollector:
    """Tests for forecast collection."""

    @patch('collection.collector.WeatherForecast')
    def test_collect_writes_json_file(
        self, mock_weather_class, collection_config, weather_config,
        location_config, sample_forecast, temp_data_dir
    ):
        """Test that collect writes a properly formatted JSON file."""
        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = sample_forecast
        mock_weather_class.return_value = mock_weather

        collector = ForecastCollector(
            collection_config, weather_config, location_config
        )
        result = collector.collect()

        assert result is True

        # Check that a file was written
        nws_dir = Path(temp_data_dir) / 'forecasts' / 'nws'
        assert nws_dir.exists()

        files = list(nws_dir.glob('*.json'))
        assert len(files) == 1

        # Verify JSON content
        with open(files[0]) as f:
            record = json.load(f)

        assert record['source'] == 'nws'
        assert record['retrieval_type'] == 'current'
        assert record['location']['latitude'] == 35.81
        assert record['location']['longitude'] == -84.33
        assert 'retrieved_at' in record
        assert len(record['forecast_days']) == 2

    @patch('collection.collector.WeatherForecast')
    def test_collect_dry_run_no_files(
        self, mock_weather_class, collection_config, weather_config,
        location_config, sample_forecast, temp_data_dir
    ):
        """Test that dry-run mode doesn't write files."""
        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = sample_forecast
        mock_weather_class.return_value = mock_weather

        collector = ForecastCollector(
            collection_config, weather_config, location_config
        )
        result = collector.collect(dry_run=True)

        assert result is True

        # No files should be written
        nws_dir = Path(temp_data_dir) / 'forecasts' / 'nws'
        assert not nws_dir.exists()

    @patch('collection.collector.WeatherForecast')
    def test_collect_returns_false_on_fetch_failure(
        self, mock_weather_class, collection_config, weather_config,
        location_config
    ):
        """Test that collect returns False when the API fetch fails."""
        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = None
        mock_weather_class.return_value = mock_weather

        collector = ForecastCollector(
            collection_config, weather_config, location_config
        )
        result = collector.collect()

        assert result is False

    @patch('collection.collector.WeatherForecast')
    def test_collect_backfill_type(
        self, mock_weather_class, collection_config, weather_config,
        location_config, sample_forecast, temp_data_dir
    ):
        """Test that retrieval_type is correctly set for backfill."""
        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = sample_forecast
        mock_weather_class.return_value = mock_weather

        collector = ForecastCollector(
            collection_config, weather_config, location_config
        )
        collector.collect(retrieval_type='backfill')

        nws_dir = Path(temp_data_dir) / 'forecasts' / 'nws'
        files = list(nws_dir.glob('*.json'))
        with open(files[0]) as f:
            record = json.load(f)

        assert record['retrieval_type'] == 'backfill'

    @patch('collection.collector.WeatherForecast')
    def test_collect_creates_directories(
        self, mock_weather_class, collection_config, weather_config,
        location_config, sample_forecast, temp_data_dir
    ):
        """Test that collect creates the necessary directory structure."""
        mock_weather = MagicMock()
        mock_weather.get_forecast.return_value = sample_forecast
        mock_weather_class.return_value = mock_weather

        collector = ForecastCollector(
            collection_config, weather_config, location_config
        )
        collector.collect()

        assert (Path(temp_data_dir) / 'forecasts' / 'nws').is_dir()
