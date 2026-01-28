"""Main entry point for weather alerts system."""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any
import yaml

from weather.forecast import WeatherForecast
from conditions.evaluator import ConditionEvaluator
from actions.email import EmailAction


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Weather alerts system - monitor forecasts and send notifications"
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

    # Initialize weather forecast fetcher
    weather = WeatherForecast(config['weather'], config['location'])

    # Fetch forecast data
    if not dry_run:
        print("Fetching weather forecast...")
    forecast_data = weather.get_forecast()

    if not forecast_data:
        print("Error: Failed to fetch weather data", file=sys.stderr)
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

    # Save state (even in dry-run mode, to track first occurrences)
    evaluator.save_state()

    if not dry_run:
        print(f"\nComplete. {alerts_triggered} alert(s) triggered.")


if __name__ == "__main__":
    args = parse_args()
    main(dry_run=args.dry_run)
