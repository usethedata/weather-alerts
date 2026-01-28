"""Weather forecast data fetching from various providers."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests


class WeatherForecast:
    """Fetch and process weather forecast data."""

    def __init__(self, weather_config: Dict[str, Any], location_config: Dict[str, Any]):
        """Initialize weather forecast fetcher.

        Args:
            weather_config: Weather API configuration
            location_config: Location information (zip code or coordinates)
        """
        self.provider = weather_config.get('provider', 'nws')
        self.api_key = weather_config.get('api_key')
        self.location = location_config

    def get_forecast(self, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        """Get weather forecast for the specified number of days.

        Args:
            days: Number of days to fetch forecast for

        Returns:
            List of daily forecast data, or None on error
        """
        if self.provider == 'nws':
            return self._get_nws_forecast(days)
        elif self.provider == 'openweather':
            return self._get_openweather_forecast(days)
        else:
            print(f"Error: Unknown weather provider: {self.provider}")
            return None

    def _get_nws_forecast(self, days: int) -> Optional[List[Dict[str, Any]]]:
        """Fetch forecast from National Weather Service API.

        The NWS API is free and doesn't require an API key, but only works for US locations.

        Args:
            days: Number of days to fetch

        Returns:
            Normalized forecast data
        """
        # First, get the grid coordinates for the location
        lat, lon = self._get_coordinates()

        if not lat or not lon:
            return None

        try:
            # Get grid endpoint
            points_url = f"https://api.weather.gov/points/{lat},{lon}"
            response = requests.get(points_url, timeout=10)
            response.raise_for_status()

            points_data = response.json()
            forecast_url = points_data['properties']['forecast']

            # Get forecast
            forecast_response = requests.get(forecast_url, timeout=10)
            forecast_response.raise_for_status()

            forecast_data = forecast_response.json()
            periods = forecast_data['properties']['periods']

            # Normalize data
            return self._normalize_nws_data(periods, days)

        except requests.RequestException as e:
            print(f"Error fetching NWS data: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"Error parsing NWS data: {e}")
            return None

    def _get_openweather_forecast(self, days: int) -> Optional[List[Dict[str, Any]]]:
        """Fetch forecast from OpenWeatherMap API.

        Args:
            days: Number of days to fetch

        Returns:
            Normalized forecast data
        """
        if not self.api_key:
            print("Error: OpenWeatherMap API key not configured")
            return None

        lat, lon = self._get_coordinates()

        if not lat or not lon:
            return None

        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'imperial',  # Fahrenheit
                'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Normalize data
            return self._normalize_openweather_data(data['list'], days)

        except requests.RequestException as e:
            print(f"Error fetching OpenWeatherMap data: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"Error parsing OpenWeatherMap data: {e}")
            return None

    def _get_coordinates(self) -> tuple[Optional[float], Optional[float]]:
        """Get latitude and longitude from location config.

        Returns:
            Tuple of (latitude, longitude) or (None, None) on error
        """
        if 'latitude' in self.location and 'longitude' in self.location:
            return self.location['latitude'], self.location['longitude']

        if 'zip_code' in self.location:
            # For now, require manual lat/lon
            # In a full implementation, we'd use a geocoding service
            print("Error: Please provide latitude and longitude in config")
            print("You can find your coordinates at https://www.latlong.net/")
            return None, None

        print("Error: No valid location configured")
        return None, None

    def _normalize_nws_data(self, periods: List[Dict], days: int) -> List[Dict[str, Any]]:
        """Normalize NWS forecast data to common format.

        Args:
            periods: Raw NWS forecast periods
            days: Number of days to include

        Returns:
            Normalized daily forecast data
        """
        daily_forecasts = []
        current_date = None
        day_data = None

        for period in periods[:days * 2]:  # Day and night periods
            period_date = datetime.fromisoformat(period['startTime'].replace('Z', '+00:00')).date()

            if period_date != current_date:
                if day_data:
                    daily_forecasts.append(day_data)

                current_date = period_date
                day_data = {
                    'date': str(current_date),
                    'temperature_min': None,
                    'temperature_max': None,
                    'precipitation_probability': 0,
                    'conditions': period.get('shortForecast', ''),
                    'raw_data': {'periods': []}
                }

            if day_data:
                day_data['raw_data']['periods'].append(period)

                temp = period['temperature']
                if period['isDaytime']:
                    day_data['temperature_max'] = temp
                else:
                    day_data['temperature_min'] = temp

                precip_prob = period.get('probabilityOfPrecipitation', {}).get('value', 0) or 0
                day_data['precipitation_probability'] = max(
                    day_data['precipitation_probability'],
                    precip_prob
                )

        if day_data:
            daily_forecasts.append(day_data)

        return daily_forecasts[:days]

    def _normalize_openweather_data(self, forecast_list: List[Dict], days: int) -> List[Dict[str, Any]]:
        """Normalize OpenWeatherMap forecast data to common format.

        Args:
            forecast_list: Raw OpenWeatherMap forecast list
            days: Number of days to include

        Returns:
            Normalized daily forecast data
        """
        daily_data = {}

        for item in forecast_list:
            date_str = item['dt_txt'].split()[0]

            if date_str not in daily_data:
                daily_data[date_str] = {
                    'date': date_str,
                    'temperature_min': float('inf'),
                    'temperature_max': float('-inf'),
                    'precipitation_probability': 0,
                    'conditions': [],
                    'raw_data': {'items': []}
                }

            daily_data[date_str]['raw_data']['items'].append(item)
            daily_data[date_str]['temperature_min'] = min(
                daily_data[date_str]['temperature_min'],
                item['main']['temp_min']
            )
            daily_data[date_str]['temperature_max'] = max(
                daily_data[date_str]['temperature_max'],
                item['main']['temp_max']
            )

            if 'pop' in item:
                daily_data[date_str]['precipitation_probability'] = max(
                    daily_data[date_str]['precipitation_probability'],
                    item['pop'] * 100
                )

            if item['weather'][0]['main'] not in daily_data[date_str]['conditions']:
                daily_data[date_str]['conditions'].append(item['weather'][0]['main'])

        forecasts = []
        for date_str in sorted(daily_data.keys())[:days]:
            data = daily_data[date_str]
            data['conditions'] = ', '.join(data['conditions'])
            forecasts.append(data)

        return forecasts
