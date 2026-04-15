# Weather Tools

A collection of weather utilities for monitoring forecasts, collecting weather data, and sending customizable alerts. Designed to run on macOS with scheduling via launchd.

## Features

- **Forecast collection** — Fetches daily forecasts from NWS (and optionally other providers) and archives them as JSON files for use by other tools
- **Actuals collection** — Retrieves observed weather data from NWS observation stations
- **Weather alerts** — Evaluates configurable conditions against forecast data and sends email notifications (first freeze of season, extreme cold, watering reminders, etc.)
- **Forecast caching** — Alerts read from cached forecast files, avoiding redundant API calls across multiple consumers

## Quick Start

```bash
# Set up the virtual environment and install dependencies
./install.sh

# Edit configuration
cp config.example.yaml config.yaml
# Edit config.yaml with your location, email settings, and data directory

# Test forecast collection
./check-weather-collect --dry-run

# Test weather alerts
./check-weather-alerts --dry-run

# Run for real
./check-weather-collect
./check-weather-alerts
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and configure:

- **location** — Latitude/longitude for your location
- **weather** — API provider selection (`nws` or `openweather`) and optional API key
- **collection** — Data archive directory, max forecast days (actual days returned depends on source; NWS returns up to 7), observation station ID
- **email** — SMTP settings for alert notifications
- **alert_rules** — Conditions and actions for weather alerts

`config.yaml` contains secrets and machine-specific paths — it is gitignored and should never be committed.

## Data Archive

The collection job writes JSON files to the configured `data_directory`:

```
weather/
├── forecasts/
│   └── nws/
│       ├── 2026-04-13.json
│       └── ...
└── actuals/
    └── nws/
        ├── 2026-04-12.json
        └── ...
```

Each JSON file includes metadata (`retrieved_at`, `source`, `location`, `retrieval_type`) alongside the weather data. The `retrieval_type` field distinguishes between `current` (collected when the forecast was live) and `backfill` (retrieved historically).

## Scheduling

The collection job is intended to run daily via launchd (macOS) before 6:00 AM. The install script can set this up, or manually:

1. Copy `net.bewilson.weather-collect.example.plist` to `net.bewilson.weather-collect.plist`
2. Replace placeholder paths with actual paths
3. Copy to `~/Library/LaunchAgents/`
4. Load: `launchctl load ~/Library/LaunchAgents/net.bewilson.weather-collect.plist`

## Project Structure

```
src/
├── weather/
│   └── forecast.py          # Weather API fetching (NWS, OpenWeatherMap)
├── alerts/
│   ├── evaluator.py         # Condition evaluation and state tracking
│   └── email.py             # SMTP email notifications
├── collection/
│   ├── collector.py         # Forecast archiving
│   └── actuals.py           # NWS observation retrieval
├── main.py                  # Alerts entry point
├── collect.py               # Collection entry point
└── version.py
tests/                       # pytest test suite
```

## Commands

| Command | Description |
|---------|-------------|
| `./check-weather-collect` | Run forecast and actuals collection |
| `./check-weather-collect --dry-run` | Fetch data but don't write files |
| `./check-weather-collect --forecasts-only` | Collect forecasts only |
| `./check-weather-collect --actuals-only` | Collect actuals only |
| `./check-weather-collect --retrieval-type backfill` | Tag data as historical backfill |
| `./check-weather-alerts` | Run weather alerts |
| `./check-weather-alerts --dry-run` | Check conditions without sending emails |
| `pytest` | Run test suite |

## Development

- **Python compatibility**: 3.9+
- **Git workflow**: Work on `dev` branch, PRs go from `dev` to `main`
- **Tests**: `pytest` with mocked HTTP requests (no real API calls)
- **CI**: GitHub Actions runs pytest on PRs to `main`

## Security

- `config.yaml` is gitignored — never commit it
- `net.bewilson.weather-collect.plist` is gitignored (contains machine-specific paths)
- Use app-specific passwords for email (not your main password)
- Never commit API keys, passwords, or other secrets

## Future Enhancements

- Additional forecast sources (Open-Meteo, OpenWeatherMap)
- Ambient Weather station integration (WS-4000 and nearby stations)
- Forecast accuracy analysis (forecast vs. actuals vs. weather station)
- Unified daily job (collect then alert in a single scheduled run)
- Error reporting and monitoring for automated jobs
- Backfill tooling for historical forecast retrieval

## License

BSD 3-Clause (see LICENSE file)
