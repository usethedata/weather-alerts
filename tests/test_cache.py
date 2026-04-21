"""Tests for forecast cache reading in main.py."""

import json
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import read_cached_forecast


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test cache files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_forecast_data():
    """Sample forecast data as it would appear in a cache file."""
    return [
        {
            'date': '2026-04-13',
            'temperature_min': 55,
            'temperature_max': 72,
            'precipitation_probability': 10,
            'conditions': 'Mostly Sunny',
        }
    ]


class TestReadCachedForecast:
    """Tests for the read_cached_forecast function."""

    def test_reads_cached_file(self, temp_data_dir, sample_forecast_data):
        """Test reading a cached forecast for today."""
        today = datetime.now().strftime('%Y-%m-%d')
        nws_dir = Path(temp_data_dir) / 'forecasts' / 'nws'
        nws_dir.mkdir(parents=True)

        record = {
            'retrieved_at': '2026-04-13T05:00:00+00:00',
            'source': 'nws',
            'location': {'latitude': 35.81, 'longitude': -84.33},
            'retrieval_type': 'current',
            'forecast_days': sample_forecast_data,
        }
        with open(nws_dir / f'{today}.json', 'w') as f:
            json.dump(record, f)

        config = {
            'collection': {
                'data_directory': temp_data_dir,
                'sources': ['nws'],
            }
        }

        result = read_cached_forecast(config)
        assert result is not None
        assert len(result) == 1
        assert result[0]['temperature_max'] == 72

    def test_returns_none_when_no_cache(self, temp_data_dir):
        """Test that None is returned when no cache file exists."""
        config = {
            'collection': {
                'data_directory': temp_data_dir,
                'sources': ['nws'],
            }
        }

        result = read_cached_forecast(config)
        assert result is None

    def test_returns_none_when_no_collection_config(self):
        """Test that None is returned when collection is not configured."""
        config = {}
        result = read_cached_forecast(config)
        assert result is None

    def test_handles_corrupted_cache_file(self, temp_data_dir):
        """Test that corrupted cache files are handled gracefully."""
        today = datetime.now().strftime('%Y-%m-%d')
        nws_dir = Path(temp_data_dir) / 'forecasts' / 'nws'
        nws_dir.mkdir(parents=True)

        with open(nws_dir / f'{today}.json', 'w') as f:
            f.write('not valid json {{{')

        config = {
            'collection': {
                'data_directory': temp_data_dir,
                'sources': ['nws'],
            }
        }

        result = read_cached_forecast(config)
        assert result is None
