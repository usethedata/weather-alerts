# weather-alerts

A flexible Python application for generating custom weather alerts and automating actions based on weather forecasts.

## Overview

This project monitors weather forecasts and triggers customizable alerts when specific conditions are met. It's particularly useful for:

- Protecting your home from freeze damage
- Managing outdoor watering schedules
- Any situation where you need automated notifications based on weather conditions

## Features

- **Flexible Condition System**: Define custom weather conditions using simple YAML configuration
- **Multiple Alert Types**: Currently supports email alerts, extensible for other notification methods
- **State Tracking**: Remembers occurrences (e.g., "first freeze of the season")
- **Multiple Weather Providers**: Supports National Weather Service (US, no API key needed) and OpenWeatherMap
- **Template Variables**: Email subjects and bodies can use weather data from the forecast
- **Python 3.9+ Compatible**: Works on modern systems and older platforms like Synology NAS

## Initial Use Cases

1. **First Freeze Alert**: Get notified when the first freeze of the fall season is forecasted
2. **Extreme Cold Alert**: Get notified when temperatures of 15°F or below are forecasted
3. **Hot & Dry Alert**: (Future) Adjust watering schedules based on extended hot, dry weather

## Project Structure

```
weather-alerts/
├── src/
│   ├── main.py              # Main entry point
│   ├── weather/             # Weather data fetching
│   │   └── forecast.py
│   ├── conditions/          # Condition evaluation logic
│   │   └── evaluator.py
│   └── actions/             # Alert actions (email, etc.)
│       └── email.py
├── tests/                   # Test suite
├── config.example.yaml      # Example configuration (safe to commit)
├── config.yaml              # Your actual config (DO NOT COMMIT)
└── requirements.txt         # Python dependencies
```

## Setup

### Prerequisites

- Python 3.9 or higher
- pip

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/weather-alerts.git
   cd weather-alerts
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your configuration:
   ```bash
   cp config.example.yaml config.yaml
   ```

4. Edit `config.yaml` with your settings:
   - Add your location (latitude/longitude)
   - Configure email settings (FastMail SMTP credentials)
   - Customize alert rules as needed

   **IMPORTANT**: Never commit `config.yaml` to version control! It contains your secrets.

### Getting Your Location Coordinates

For National Weather Service API, you need latitude and longitude:
- Visit https://www.latlong.net/
- Search for your address
- Copy the coordinates to your `config.yaml`

### Email Setup (FastMail)

1. Log in to FastMail
2. Go to Settings → Privacy & Security → App Passwords
3. Create a new app password for this application
4. Use that app password (not your regular password) in `config.yaml`

## Usage

### Running Manually

```bash
cd /path/to/weather-alerts
python src/main.py
```

### Scheduling on Synology

1. Open Task Scheduler on your Synology
2. Create a new Scheduled Task → User-defined script
3. Set schedule (e.g., daily at 6:00 AM)
4. User: Your user account
5. Script:
   ```bash
   cd /path/to/weather-alerts
   /usr/local/bin/python3 src/main.py
   ```

### Running on macOS with cron

Add to your crontab:
```
0 6 * * * cd /path/to/weather-alerts && /usr/local/bin/python3 src/main.py
```

## Configuration

See `config.example.yaml` for detailed configuration options. Key sections:

- **location**: Your coordinates for weather data
- **weather**: API provider and credentials
- **email**: SMTP settings for alerts
- **alert_rules**: Define conditions and actions

### Alert Rule Examples

**First freeze of the season:**
```yaml
- name: "First Freeze Alert"
  enabled: true
  condition:
    type: "first_occurrence"
    weather_condition:
      field: "temperature_min"
      operator: "lte"
      value: 32
      forecast_days: 2
    season_start_month: 8
    season_end_month: 12
  action:
    type: "email"
    subject: "ALERT: First Freeze Forecasted"
    body: "The first freeze is forecasted for {forecast_date}..."
```

**Extreme cold:**
```yaml
- name: "Extreme Cold Alert"
  enabled: true
  condition:
    type: "threshold"
    weather_condition:
      field: "temperature_min"
      operator: "lte"
      value: 15
      forecast_days: 2
  action:
    type: "email"
    subject: "ALERT: Extreme Cold ({temperature_min}°F)"
    body: "Extreme cold forecasted..."
```

## Development

### Python Version Compatibility

- **Development**: Python 3.14.1 (macOS)
- **Deployment**: Python 3.9 (Synology)
- Code is written to be compatible with Python 3.9+

### Running Tests

```bash
python -m pytest tests/
```

## Security Notes

- This is a **public repository**
- `config.yaml` is in `.gitignore` and will never be committed
- Never commit API keys, passwords, or other secrets
- Use app-specific passwords for email (not your main password)
- The `.gitignore` also excludes `.env`, `*.local.yaml`, and other common secret files

## Future Enhancements

- Timer/reminder actions (e.g., reset a 12-hour timer when conditions persist)
- Additional notification methods (SMS, push notifications)
- More weather data providers
- Web dashboard for viewing alerts
- Historical tracking and analytics
- **Forecast Accuracy Tracking**: Integrate with Ambient Weather station to compare forecasted vs. actual conditions. Track high/low temperature accuracy and precipitation amounts to measure forecast reliability over time.
- **Smart Garden Watering**: Use soil moisture probe data from Ambient Weather station to assess watering needs. Support multiple soil moisture probes to provide zone-specific recommendations based on actual soil conditions combined with weather forecasts.

## License

BSD 3-Clause License (see LICENSE file)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
