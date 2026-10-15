"""OpenWeather-backed weather service with graceful degradation."""

from __future__ import annotations

import os

import requests

DEFAULT_LOCATION = "Hyderabad"
DEFAULT_LATITUDE = 17.3850
DEFAULT_LONGITUDE = 78.4867


def get_weather_api_key():
    return os.getenv("OPENWEATHER_API_KEY", "")


def resolve_location(location=None):
    """Resolve a city name to latitude and longitude."""
    city_name = (location or DEFAULT_LOCATION).strip() or DEFAULT_LOCATION
    api_key = get_weather_api_key()
    if not api_key:
        return DEFAULT_LATITUDE, DEFAULT_LONGITUDE, {"name": city_name, "status": "fallback"}

    url = "https://api.openweathermap.org/geo/1.0/direct"
    params = {"q": city_name, "limit": 1, "appid": api_key}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if not payload:
            raise ValueError("No location data returned.")
        item = payload[0]
        return float(item.get("lat", DEFAULT_LATITUDE)), float(item.get("lon", DEFAULT_LONGITUDE)), {
            "name": item.get("name", city_name),
            "country": item.get("country", ""),
            "status": "ok",
        }
    except Exception:
        return DEFAULT_LATITUDE, DEFAULT_LONGITUDE, {"name": city_name, "status": "fallback"}


def get_current_weather(lat, lon):
    """Fetch current weather from OpenWeather."""
    api_key = get_weather_api_key()
    if not api_key:
        return {
            "status": "unavailable",
            "message": "Live weather temporarily unavailable.",
            "temperature": 0,
            "humidity": 0,
            "rainfall": 0,
            "wind_speed": 0,
            "pressure": 0,
            "cloudiness": 0,
            "condition": "Weather data unavailable",
        }

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        rain_data = payload.get("rain", {})
        if isinstance(rain_data, dict):
            if "1h" in rain_data:
                rainfall = rain_data["1h"]
                rainfall_period_hours = 1
            elif "3h" in rain_data:
                rainfall = rain_data["3h"]
                rainfall_period_hours = 3
            else:
                rainfall = 0.0
                rainfall_period_hours = 1
        else:
            rainfall = rain_data or 0.0
            rainfall_period_hours = 1
        weather = payload.get("weather", [{}])[0]
        return {
            "status": "ok",
            "temperature": round(float(payload.get("main", {}).get("temp", 0.0)), 2),
            "max_temperature": round(float(payload.get("main", {}).get("temp_max", 0.0)), 2),
            "humidity": round(float(payload.get("main", {}).get("humidity", 0.0)), 2),
            "rainfall": round(float(rainfall or 0.0), 2),
            "rainfall_period_hours": rainfall_period_hours,
            "wind_speed": round(float(payload.get("wind", {}).get("speed", 0.0)), 2),
            "pressure": round(float(payload.get("main", {}).get("pressure", 0.0)), 2),
            "cloudiness": round(float(payload.get("clouds", {}).get("all", 0.0)), 2),
            "condition": weather.get("main", "Clear"),
            "description": weather.get("description", "Current conditions"),
        }
    except Exception:
        return {
            "status": "unavailable",
            "message": "Live weather temporarily unavailable.",
            "temperature": 0,
            "humidity": 0,
            "rainfall": 0,
            "rainfall_period_hours": 1,
            "wind_speed": 0,
            "pressure": 0,
            "cloudiness": 0,
            "condition": "Weather data unavailable",
        }
