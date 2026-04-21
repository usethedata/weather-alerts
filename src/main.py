"""Main entry point for weather alerts system."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml

from version import __version__
from weather.forecast import WeatherForecast
from alerts.evaluator import ConditionEvaluator
from alerts.email import EmailAction


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Weather alerts system - monitor forecasts and send notifications"
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Check conditions but don't send emails. Outputs triggered alerts to stdout."
    )
    return parser.parse_args()


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"Error: Configuration file '{config_path}' not found.", file=sys.stderr)
        print("Please copy config.example.yaml to config.yaml and configure it.", file=sys.stderr)
        sys.exit(1)

    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def read_cached_forecast(config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Read today's forecast from the cache directory.

    Args:
        config: Full configuration dict

    Returns:
        Forecast data list, or None if cache miss
    """
    collection_config = config.get('collection')
    if not collection_config:
        return None

    data_dir = Path(collection_config['data_directory']).expanduser()
    sources = collection_config.get('sources', ['nws'])
    today = datetime.now().strftime('%Y-%m-%d')

    # Try each configured source until we find a cached forecast
    for source in sources:
        cache_path = data_dir / 'forecasts' / source / f"{today}.json"
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    record = json.load(f)
                return record.get('forecast_days', [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not read cache {cache_path}: {e}",
                      file=sys.stderr)
                continue

    return None


def fetch_live_forecast(config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Fetch a live forecast from the weather API.

    This is the fallback path when no cached forecast is available.
    It also attempts to run the full collection routine so that the
    cache is populated for other consumers.

    Args:
        config: Full configuration dict

    Returns:
        Forecast data list, or None on failure
    """
    from collection.collector import ForecastCollector

    collection_config = config.get('collection')
    if collection_config:
        print("  Cache miss — running forecast collection...", file=sys.stderr)
        collector = ForecastCollector(
            collection_config,
            config['weather'],
            config['location']
        )
        if collector.collect():
            # Now read from the cache we just wrote
            cached = read_cached_forecast(config)
            if cached:
                return cached

    # Final fallback: direct fetch without caching
    print("  Falling back to direct forecast fetch...", file=sys.stderr)
    weather = WeatherForecast(config['weather'], config['location'])
    return weather.get_forecast()


def main(dry_run: bool = False):
    """Main execution function.

    Args:
        dry_run: If True, evaluate conditions but don't send emails.
    """
    if dry_run:
        print("Weather Alerts - DRY RUN MODE", file=sys.stderr)
    else:
        print("Weather Alerts - Starting...")

    # Load configuration
    config = load_config()

    # Try cached forecast first, then live fetch
    if not dry_run:
        print("Reading cached forecast...")
    forecast_data = read_cached_forecast(config)

    if forecast_data:
        if not dry_run:
            print(f"  Using cached forecast ({len(forecast_data)} days)")
    else:
        if not dry_run:
            print("  No cached forecast found, fetching live...")
        forecast_data = fetch_live_forecast(config)

    if not forecast_data:
        print("Error: Failed to get weather data (cache miss and live fetch failed)",
              file=sys.stderr)
        sys.exit(1)

    # Initialize evaluator and actions
    evaluator = ConditionEvaluator(config.get('state_file', '.weather_alerts_state.json'))
    if not dry_run:
        email_action = EmailAction(config['email'])

    # Process each alert rule
    alerts_triggered = 0
    for rule in config.get('alert_rules', []):
        if not rule.get('enabled', True):
            continue

        if not dry_run:
            print(f"Evaluating rule: {rule['name']}")

        # Evaluate condition
        result = evaluator.evaluate(rule['condition'], forecast_data)

        if result['triggered']:
            alerts_triggered += 1
            context = result.get('context', {})

            if dry_run:
                # Output one line per triggered condition to stdout
                context_str = ', '.join(f"{k}={v}" for k, v in context.items())
                print(f"TRIGGERED: {rule['name']} ({context_str})")
            else:
                print(f"  ✓ Condition met!")
                # Execute action
                if rule['action']['type'] == 'email':
                    email_action.send(
                        subject=rule['action']['subject'],
                        body=rule['action']['body'],
                        context=context
                    )
                else:
                    print(f"  Warning: Unknown action type: {rule['action']['type']}", file=sys.stderr)
        else:
            if not dry_run:
                print(f"  - Condition not met")

    # Save state (only in normal mode - dry-run should have no side effects)
    if not dry_run:
        evaluator.save_state()

    if not dry_run:
        print(f"\nComplete. {alerts_triggered} alert(s) triggered.")


if __name__ == "__main__":
    args = parse_args()
    main(dry_run=args.dry_run)
