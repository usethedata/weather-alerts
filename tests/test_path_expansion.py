"""Tests that ~ in data_directory is expanded to an absolute path.

Allows config.yaml to use portable ~/Dropbox/... paths across macOS and Linux
without editing per machine.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from collection.actuals import ActualsCollector
from collection.collector import ForecastCollector


def test_forecast_collector_expands_tilde():
    config = {'data_directory': '~/tilde-test-data'}
    weather = {'provider': 'nws'}
    location = {'latitude': 0.0, 'longitude': 0.0}
    collector = ForecastCollector(config, weather, location)

    assert '~' not in str(collector.data_dir)
    assert collector.data_dir == Path.home() / 'tilde-test-data'


def test_actuals_collector_expands_tilde():
    config = {'data_directory': '~/tilde-test-data'}
    location = {'latitude': 0.0, 'longitude': 0.0}
    collector = ActualsCollector(config, location)

    assert '~' not in str(collector.data_dir)
    assert collector.data_dir == Path.home() / 'tilde-test-data'
