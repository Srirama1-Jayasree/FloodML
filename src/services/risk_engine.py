"""Rule-based risk classification helpers."""

from __future__ import annotations


def normalize_probability(value):
    """Normalize probability to a 0-1 scale."""
    if value is None:
        return 0.0
    value = float(value)
    if value > 1:
        value = value / 100.0
    return max(0.0, min(1.0, value))


def probability_to_percent(value):
    """Return probability on a 0-100 scale."""
    return round(normalize_probability(value) * 100, 2)


def risk_level_from_probability(probability):
    """Map probability to a transparent risk level."""
    probability = probability_to_percent(probability)
    if probability >= 90:
        return "CRITICAL"
    if probability >= 65:
        return "HIGH"
    if probability >= 35:
        return "MODERATE"
    return "LOW"


def water_management_status_from_probability(probability):
    """Map probability to water-management status."""
    probability = probability_to_percent(probability)
    if probability < 35:
        return "NORMAL"
    if probability < 65:
        return "WATCH"
    if probability < 90:
        return "PREPARE"
    return "EMERGENCY"


def build_model_feature_vector(weather_data):
    """Create the feature vector compatible with the existing model."""
    if not weather_data:
        return None
    temperature = float(weather_data.get("temperature", 0) or 0)
    max_temperature = float(weather_data.get("max_temperature", temperature) or temperature)
    wind_speed = float(weather_data.get("wind_speed", 0) or 0)
    cloudiness = float(weather_data.get("cloudiness", 0) or 0)
    rainfall = float(weather_data.get("rainfall", 0) or 0)
    humidity = float(weather_data.get("humidity", 0) or 0)
    return [temperature, max_temperature, wind_speed, cloudiness, rainfall, humidity]
