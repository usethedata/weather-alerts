"""Entry point for weather data collection.

Fetches forecasts and actuals, writes them to the archive directory.
Intended to run daily via launchd before 6:00 AM.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any

import yaml

from version import __version__
from collection.collector import ForecastCollector
from collection.actuals import ActualsCollector


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect weather forecasts and actuals for archiving"
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Fetch data but don't write files. Output to stdout."
    )
    parser.add_argument(
        '--forecasts-only',
        action='store_true',
        help="Collect forecasts only, skip actuals."
    )
    parser.add_argument(
        '--actuals-only',
        action='store_true',
        help="Collect actuals only, skip forecasts."
    )
    parser.add_argument(
        '--retrieval-type',
        choices=['current', 'backfill'],
        default='current',
        help="Tag data as 'current' (live) or 'backfill' (historical). Default: current."
    )
    return parser.parse_args()


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"Error: Configuration file '{config_path}' not found.",
              file=sys.stderr)
        print("Please copy config.example.yaml to config.yaml and configure it.",
              file=sys.stderr)
        sys.exit(1)

    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main execution function."""
    args = parse_args()

    config = load_config()

    if 'collection' not in config:
        print("Error: No 'collection' section in config.yaml", file=sys.stderr)
        sys.exit(1)

    collection_config = config['collection']
    errors = 0

    # Collect forecasts
    if not args.actuals_only:
        collector = ForecastCollector(
            collection_config,
            config['weather'],
            config['location']
        )
        if not collector.collect(retrieval_type=args.retrieval_type,
                                 dry_run=args.dry_run):
            errors += 1

    # Collect actuals
    if not args.forecasts_only:
        actuals = ActualsCollector(collection_config, config['location'])
        if not actuals.collect(dry_run=args.dry_run):
            errors += 1

    if errors > 0:
        print(f"\nCollection finished with {errors} error(s).", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nCollection complete.")


if __name__ == "__main__":
    main()
