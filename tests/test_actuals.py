"""Tests for the ActualsCollector class."""

import json
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from collection.actuals import ActualsCollector


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
        'observation_station': 'KTYS',
    }


@pytest.fixture
def location_config():
    return {'latitude': 35.81, 'longitude': -84.33}


@pytest.fixture
def sample_observations():
    """Sample NWS observation response matching yesterday's date."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    return {
        'features': [
            {
                'properties': {
                    'timestamp': f'{yesterday}T06:00:00+00:00',
                    'temperature': {'value': 10.0, 'unitCode': 'wmoUnit:degC'},
                    'precipitationLastHour': {'value': 0.0, 'unitCode': 'wmoUnit:mm'},
                }
            },
            {
                'properties': {
                    'timestamp': f'{yesterday}T12:00:00+00:00',
                    'temperature': {'value': 22.0, 'unitCode': 'wmoUnit:degC'},
                    'precipitationLastHour': {'value': 2.5, 'unitCode': 'wmoUnit:mm'},
                }
            },
            {
                'properties': {
                    'timestamp': f'{yesterday}T18:00:00+00:00',
                    'temperature': {'value': 18.0, 'unitCode': 'wmoUnit:degC'},
                    'precipitationLastHour': {'value': 0.0, 'unitCode': 'wmoUnit:mm'},
                }
            },
        ]
    }


class TestActualsCollector:
    """Tests for actuals collection."""

    @patch('collection.actuals.requests.get')
    def test_collect_writes_json_file(
        self, mock_get, collection_config, location_config,
        sample_observations, temp_data_dir
    ):
        """Test that collect writes a properly formatted JSON file."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_observations
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        collector = ActualsCollector(collection_config, location_config)
        result = collector.collect()

        assert result is True

        nws_dir = Path(temp_data_dir) / 'actuals' / 'nws'
        assert nws_dir.exists()

        files = list(nws_dir.glob('*.json'))
        assert len(files) == 1

        with open(files[0]) as f:
            record = json.load(f)

        assert record['source'] == 'nws'
        assert record['station_id'] == 'KTYS'
        assert record['retrieval_type'] == 'current'
        assert 'retrieved_at' in record

        obs = record['observations']
        assert obs['observation_count'] == 3
        assert obs['temperature_min_c'] == 10.0
        assert obs['temperature_max_c'] == 22.0
        # 10°C = 50°F, 22°C = 71.6°F
        assert obs['temperature_min_f'] == 50.0
        assert obs['temperature_max_f'] == 71.6
        assert obs['precipitation_total_mm'] == 2.5

    @patch('collection.actuals.requests.get')
    def test_collect_dry_run_no_files(
        self, mock_get, collection_config, location_config,
        sample_observations, temp_data_dir
    ):
        """Test that dry-run mode doesn't write files."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_observations
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        collector = ActualsCollector(collection_config, location_config)
        result = collector.collect(dry_run=True)

        assert result is True
        nws_dir = Path(temp_data_dir) / 'actuals' / 'nws'
        assert not nws_dir.exists()

    def test_collect_fails_without_station(self, temp_data_dir, location_config):
        """Test that collect fails when no station is configured."""
        config = {'data_directory': temp_data_dir}
        collector = ActualsCollector(config, location_config)
        result = collector.collect()

        assert result is False

    @patch('collection.actuals.requests.get')
    def test_collect_handles_network_error(
        self, mock_get, collection_config, location_config
    ):
        """Test that network errors are handled gracefully."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        collector = ActualsCollector(collection_config, location_config)
        result = collector.collect()

        assert result is False

    @patch('collection.actuals.requests.get')
    def test_collect_handles_no_observations_for_day(
        self, mock_get, collection_config, location_config
    ):
        """Test handling when no observations exist for yesterday."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'features': [
                {
                    'properties': {
                        'timestamp': '2020-01-01T12:00:00+00:00',
                        'temperature': {'value': 10.0},
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        collector = ActualsCollector(collection_config, location_config)
        result = collector.collect()

        assert result is False


class TestSummarizeDay:
    """Tests for the day summarization logic."""

    def test_temperature_conversion(self, collection_config, location_config):
        """Test that Celsius to Fahrenheit conversion is correct."""
        collector = ActualsCollector(collection_config, location_config)

        observations = [
            {
                'properties': {
                    'timestamp': '2026-04-12T12:00:00+00:00',
                    'temperature': {'value': 0.0},
                    'precipitationLastHour': {'value': None},
                }
            }
        ]
        result = collector._summarize_day(observations, '2026-04-12')

        assert result is not None
        assert result['temperature_min_f'] == 32.0  # 0°C = 32°F
        assert result['temperature_max_f'] == 32.0

    def test_handles_null_temperature(self, collection_config, location_config):
        """Test handling of null temperature values."""
        collector = ActualsCollector(collection_config, location_config)

        observations = [
            {
                'properties': {
                    'timestamp': '2026-04-12T12:00:00+00:00',
                    'temperature': {'value': None},
                }
            }
        ]
        result = collector._summarize_day(observations, '2026-04-12')

        assert result is not None
        assert result['temperature_min_f'] is None
        assert result['temperature_max_f'] is None
