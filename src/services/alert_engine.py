"""Alert generation based on advisory flood-risk rules."""

from __future__ import annotations

from datetime import datetime

from src.services.risk_engine import probability_to_percent, risk_level_from_probability


def build_alert_for_prediction(location, probability, weather_summary, recommended_actions):
    risk_level = risk_level_from_probability(probability)
    probability_percent = probability_to_percent(probability)
    alert_title = {
        "LOW": "Low Flood Risk",
        "MODERATE": "Advisory Flood Risk",
        "HIGH": "High Flood Risk Detected",
        "CRITICAL": "Emergency Flood Warning",
    }.get(risk_level, "Flood Risk Notification")

    message_lines = [
        f"Flood Probability: {probability_percent}%",
        f"Location: {location}",
        "Recommended:",
    ]
    for action in recommended_actions[:5]:
        message_lines.append(f"- {action}")

    return {
        "title": alert_title,
        "risk_level": risk_level,
        "probability": probability_percent,
        "location": location,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "weather_summary": weather_summary,
        "recommended_actions": recommended_actions,
        "message": "\n".join(message_lines),
        "status": "new",
        "notification_type": "in-app",
    }
