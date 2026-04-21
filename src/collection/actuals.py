"""Actuals collection — fetches observed weather data from NWS stations."""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests


class ActualsCollector:
    """Fetches observed weather data from NWS observation stations."""

    NWS_BASE_URL = "https://api.weather.gov"

    def __init__(self, collection_config: Dict[str, Any],
                 location_config: Dict[str, Any]):
        """Initialize the actuals collector.

        Args:
            collection_config: Collection settings (data_directory, observation_station)
            location_config: Location information (latitude/longitude)
        """
        self.data_dir = Path(collection_config['data_directory']).expanduser()
        self.station_id = collection_config.get('observation_station', '')
        self.location_config = location_config

    def collect(self, dry_run: bool = False) -> bool:
        """Collect yesterday's observed weather data.

        Fetches observations from the configured NWS station and writes
        a daily summary to the actuals archive.

        Args:
            dry_run: If True, fetch data but don't write files

        Returns:
            True on success, False on failure
        """
        if not self.station_id:
            print("Error: No observation_station configured", file=sys.stderr)
            return False

        print(f"Collecting actuals from NWS station {self.station_id}...")

        observations = self._fetch_observations()
        if observations is None:
            return False

        # Summarize yesterday's observations into a daily record
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        daily = self._summarize_day(observations, yesterday)

        if daily is None:
            print(f"  Warning: No observations found for {yesterday}",
                  file=sys.stderr)
            return False

        retrieved_at = datetime.now(timezone.utc).isoformat()
        record = {
            'retrieved_at': retrieved_at,
            'source': 'nws',
            'station_id': self.station_id,
            'location': {
                'latitude': self.location_config.get('latitude'),
                'longitude': self.location_config.get('longitude'),
            },
            'retrieval_type': 'current',
            'date': yesterday,
            'observations': daily,
        }

        if dry_run:
            print(f"  [dry-run] Would write nws/{yesterday}.json")
            print(json.dumps(record, indent=2))
        else:
            self._write(yesterday, record)

        return True

    def _fetch_observations(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch recent observations from the NWS station.

        Returns:
            List of observation records, or None on error
        """
        url = f"{self.NWS_BASE_URL}/stations/{self.station_id}/observations"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('features', [])
        except requests.RequestException as e:
            print(f"Error fetching observations from {self.station_id}: {e}",
                  file=sys.stderr)
            return None
        except (KeyError, ValueError) as e:
            print(f"Error parsing observation data: {e}", file=sys.stderr)
            return None

    def _summarize_day(self, observations: List[Dict[str, Any]],
                       target_date: str) -> Optional[Dict[str, Any]]:
        """Summarize observations for a single day.

        Args:
            observations: Raw NWS observation features
            target_date: Date to summarize (YYYY-MM-DD)

        Returns:
            Daily summary dict, or None if no observations match
        """
        day_obs = []
        for obs in observations:
            props = obs.get('properties', {})
            timestamp = props.get('timestamp', '')
            if not timestamp:
                continue
            obs_date = timestamp[:10]  # YYYY-MM-DD from ISO timestamp
            if obs_date == target_date:
                day_obs.append(props)

        if not day_obs:
            return None

        # Extract temperature readings (NWS returns Celsius)
        temps_c = []
        for props in day_obs:
            temp = props.get('temperature', {})
            if isinstance(temp, dict):
                val = temp.get('value')
            else:
                val = temp
            if val is not None:
                temps_c.append(val)

        # Extract precipitation (NWS returns mm)
        precip_mm = []
        for props in day_obs:
            p = props.get('precipitationLastHour', {})
            if isinstance(p, dict):
                val = p.get('value')
            else:
                val = p
            if val is not None:
                precip_mm.append(val)

        # Convert to Fahrenheit for consistency with forecast data
        temps_f = [round(c * 9.0 / 5.0 + 32, 1) for c in temps_c]

        result = {
            'observation_count': len(day_obs),
            'temperature_min_f': min(temps_f) if temps_f else None,
            'temperature_max_f': max(temps_f) if temps_f else None,
            'temperature_min_c': round(min(temps_c), 1) if temps_c else None,
            'temperature_max_c': round(max(temps_c), 1) if temps_c else None,
            'precipitation_total_mm': round(sum(precip_mm), 2) if precip_mm else None,
            'raw_observations': day_obs,
        }

        return result

    def _write(self, date_str: str, record: Dict[str, Any]) -> None:
        """Write an actuals record to the archive.

        Args:
            date_str: Date string for the filename (YYYY-MM-DD)
            record: The complete actuals record to write
        """
        out_dir = self.data_dir / 'actuals' / 'nws'
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / f"{date_str}.json"
        with open(out_path, 'w') as f:
            json.dump(record, f, indent=2)

        print(f"  Wrote {out_path}")
