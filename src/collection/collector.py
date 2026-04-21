"""Forecast collection — fetches and archives daily weather forecasts."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from weather.forecast import WeatherForecast


class ForecastCollector:
    """Fetches weather forecasts and writes them to the archive."""

    def __init__(self, collection_config: Dict[str, Any],
                 weather_config: Dict[str, Any],
                 location_config: Dict[str, Any]):
        """Initialize the forecast collector.

        Args:
            collection_config: Collection settings (data_directory, forecast_days, sources)
            weather_config: Weather API configuration
            location_config: Location information (latitude/longitude)
        """
        self.data_dir = Path(collection_config['data_directory']).expanduser()
        self.forecast_days = collection_config.get('forecast_days', 10)
        self.sources = collection_config.get('sources', ['nws'])
        self.weather_config = weather_config
        self.location_config = location_config

    def collect(self, retrieval_type: str = "current",
                dry_run: bool = False) -> bool:
        """Collect forecasts from all configured sources.

        Args:
            retrieval_type: "current" for live collection, "backfill" for historical
            dry_run: If True, fetch data but don't write files

        Returns:
            True if all sources succeeded, False if any failed
        """
        all_ok = True
        retrieved_at = datetime.now(timezone.utc).isoformat()
        today = datetime.now().strftime('%Y-%m-%d')

        for source in self.sources:
            print(f"Collecting forecast from {source}...")

            # Configure provider for this source
            source_weather_config = dict(self.weather_config)
            source_weather_config['provider'] = source

            fetcher = WeatherForecast(source_weather_config, self.location_config)
            forecast_data = fetcher.get_forecast(days=self.forecast_days)

            if forecast_data is None:
                print(f"Error: Failed to fetch forecast from {source}",
                      file=sys.stderr)
                all_ok = False
                continue

            record = {
                'retrieved_at': retrieved_at,
                'source': source,
                'location': {
                    'latitude': self.location_config.get('latitude'),
                    'longitude': self.location_config.get('longitude'),
                },
                'retrieval_type': retrieval_type,
                'forecast_days': forecast_data,
            }

            if dry_run:
                print(f"  [dry-run] Would write {source}/{today}.json "
                      f"({len(forecast_data)} days)")
                print(json.dumps(record, indent=2))
            else:
                self._write(source, today, record)

        return all_ok

    def _write(self, source: str, date_str: str,
               record: Dict[str, Any]) -> None:
        """Write a forecast record to the archive.

        Args:
            source: Provider name (used as subdirectory)
            date_str: Date string for the filename (YYYY-MM-DD)
            record: The complete forecast record to write
        """
        out_dir = self.data_dir / 'forecasts' / source
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / f"{date_str}.json"
        with open(out_path, 'w') as f:
            json.dump(record, f, indent=2)

        print(f"  Wrote {out_path}")
