"""OpenWeather forecast service."""

from __future__ import annotations

import os

import requests

from src.services.risk_engine import probability_to_percent


def get_forecast_api_key():
    return os.getenv("OPENWEATHER_API_KEY", "")


def _build_period_record(item):
    rain = item.get("rain", {})
    precipitation = rain.get("3h", 0.0) if isinstance(rain, dict) else float(rain or 0.0)
    return {
        "timestamp": item.get("dt_txt") or item.get("dt"),
        "temperature": round(float(item.get("main", {}).get("temp", 0.0)), 2),
        "humidity": round(float(item.get("main", {}).get("humidity", 0.0)), 2),
        "rainfall": round(float(precipitation or 0.0), 2),
        "wind_speed": round(float(item.get("wind", {}).get("speed", 0.0)), 2),
        "cloudiness": round(float(item.get("clouds", {}).get("all", 0.0)), 2),
        "condition": (item.get("weather", [{}])[0].get("main") if item.get("weather") else "Clear"),
        "description": (item.get("weather", [{}])[0].get("description") if item.get("weather") else "Forecast"),
    }


def get_forecast_data(lat, lon):
    """Fetch next 72-hour OpenWeather forecast."""
    api_key = get_forecast_api_key()
    if not api_key:
        return {
            "status": "unavailable",
            "message": "Weather forecast available — flood-model forecasting requires compatible model inputs.",
            "periods": {"24h": [], "48h": [], "72h": []},
        }

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "cnt": 40}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("list", [])
        if not items:
            return {"status": "unavailable", "message": "Weather forecast data unavailable.", "periods": {"24h": [], "48h": [], "72h": []}} 

        periods = {
            "24h": [_build_period_record(item) for item in items[:8]],
            "48h": [_build_period_record(item) for item in items[:16]],
            "72h": [_build_period_record(item) for item in items[:24]],
        }
        return {"status": "ok", "message": "Forecast data retrieved successfully.", "periods": periods}
    except Exception:
        return {
            "status": "unavailable",
            "message": "Weather forecast temporarily unavailable.",
            "periods": {"24h": [], "48h": [], "72h": []},
        }


def build_forecast_risk_projection(model, forecast_payload):
    """Map forecast weather values into flood probabilities when the model supports them."""
    if not forecast_payload or forecast_payload.get("status") != "ok":
        return {
            "status": "unavailable",
            "message": forecast_payload.get("message", "Weather forecast data unavailable.") if forecast_payload else "Weather forecast data unavailable.",
            "projections": {"24h": [], "48h": [], "72h": []},
        }
    if model is None:
        return {
            "status": "unavailable",
            "message": "Flood-risk forecast unavailable because the compatible flood model is not loaded.",
            "projections": {"24h": [], "48h": [], "72h": []},
        }

    projections = {}
    for period_name, entries in forecast_payload.get("periods", {}).items():
        items = []
        for entry in entries:
            feature_vector = [
                entry.get("temperature", 0),
                max(entry.get("temperature", 0), 0),
                entry.get("wind_speed", 0),
                entry.get("cloudiness", 0),
                entry.get("rainfall", 0),
                entry.get("humidity", 0),
            ]
            try:
                probability = float(model.predict_proba([feature_vector])[0][1])
            except Exception:
                probability = 0.0
            risk = "LOW"
            percent = probability_to_percent(probability)
            if percent >= 90:
                risk = "CRITICAL"
            elif percent >= 65:
                risk = "HIGH"
            elif percent >= 35:
                risk = "MODERATE"
            items.append({
                "timestamp": entry.get("timestamp"),
                "risk_level": risk,
                "probability": round(percent, 2),
                "weather_summary": f"{entry.get('condition', 'Clear')} / {entry.get('temperature', 0)}°C / {entry.get('humidity', 0)}% humidity",
            })
        projections[period_name] = items

    return {"status": "ok", "message": "Flood-risk forecast generated from compatible model features.", "projections": projections}
