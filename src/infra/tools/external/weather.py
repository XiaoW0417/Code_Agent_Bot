"""
Weather tool using OpenMeteo.
"""
import logging
import httpx
from typing import Literal, TypedDict, cast

from src.core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)

class GeocodingResult(TypedDict):
    id: int
    name: str
    latitude: float
    longitude: float

class WeatherResult(TypedDict):
    temperature: float
    windspeed: float
    weathercode: int
    unit: str

WEATHER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get current weather for a location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name (English only, e.g. 'Beijing').",
                },
                "unit": {
                    "type": "string",
                    "description": "Temperature unit.",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["location"],
        },
    },
}

async def _get_geocoding(location: str, client: httpx.AsyncClient) -> GeocodingResult:
    """Convert city name to coordinates."""
    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location, "count": 1, "language": "en", "format": "json"}

    try:
        response = await client.get(geocoding_url, params=params)
        response.raise_for_status()
        data = response.json()
        if not data.get("results"):
            raise ToolExecutionError("get_current_weather", f"City not found: '{location}'")
        return cast(GeocodingResult, data["results"][0])
    
    except httpx.HTTPStatusError as e:
        raise ToolExecutionError("get_current_weather", f"Geocoding API error: {e.response.status_code}")
    except Exception as e:
        # Wrap exception to ToolExecutionError if it isn't one already? 
        # The original code did `raise ToolExecutionError`
        if isinstance(e, ToolExecutionError):
            raise
        raise ToolExecutionError("get_current_weather", f"Geocoding error: {e}")

async def get_current_weather(
    location: str, unit: Literal["celsius", "fahrenheit"] = "celsius"
) -> WeatherResult:
    """Get current weather for location."""
    async with httpx.AsyncClient() as client:
        geo_info = await _get_geocoding(location, client)
        lat, lon = geo_info.get("latitude"), geo_info.get("longitude")

        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "temperature_unit": unit
        }

        try:
            response = await client.get(weather_url, params=params)
            response.raise_for_status()
            weather_data = response.json()["current_weather"]

            return WeatherResult(
                temperature=weather_data.get("temperature"),
                windspeed=weather_data.get("windspeed"),
                weathercode=weather_data.get("weathercode"),
                unit=unit
            )

        except httpx.HTTPStatusError as e:
            raise ToolExecutionError("get_current_weather", f"Weather API error: {e.response.status_code}")
        except Exception as e:
            raise ToolExecutionError("get_current_weather", f"Weather error: {e}")
