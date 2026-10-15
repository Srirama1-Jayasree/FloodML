"""AquaSentinel AI flood warning and water management dashboard."""

from __future__ import annotations

import os
import pickle
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request

from src.notifications.email_service import send_email_alert
from src.notifications.notification_manager import NotificationManager
from src.services.alert_engine import build_alert_for_prediction
from src.services.forecast_service import build_forecast_risk_projection, get_forecast_data
from src.services.risk_engine import build_model_feature_vector, risk_level_from_probability, water_management_status_from_probability
from src.services.water_management import build_water_management_report
from src.services.weather_service import get_current_weather, get_weather_api_key, resolve_location

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "aqua_sentinel.db"
MODEL_PATH = BASE_DIR / "model.pickle"
MODEL_COMPARISON_PATH = BASE_DIR / "model_comparison.json"


def load_environment():
    """Load local environment variables without overriding variables set by the shell."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and not os.environ.get(key):
            os.environ[key] = value


load_environment()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
notification_manager = NotificationManager()


def load_model():
    """Load the legacy flood model if the current environment supports it."""
    if not MODEL_PATH.exists():
        return None, "Model file is missing."
    try:
        with MODEL_PATH.open("rb") as handle:
            model = pickle.load(handle)
        return model, None
    except Exception as exc:  # pragma: no cover - environment-dependent
        return None, f"Model could not be loaded in this environment: {exc}"


MODEL, MODEL_ERROR = load_model()


def init_db():
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            risk_level TEXT,
            probability REAL,
            location TEXT,
            message TEXT,
            created_at TEXT,
            status TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            risk_level TEXT,
            probability REAL,
            location TEXT,
            message TEXT,
            created_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    migrated = connection.execute(
        "SELECT value FROM settings WHERE key = ?",
        ("history_probability_percent_v1",),
    ).fetchone()
    if not migrated:
        connection.execute(
            "UPDATE alerts SET probability = ROUND(probability * 100.0, 2) "
            "WHERE probability >= 0 AND probability <= 1"
        )
        connection.execute(
            "UPDATE history SET probability = ROUND(probability * 100.0, 2) "
            "WHERE probability >= 0 AND probability <= 1"
        )
        connection.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("history_probability_percent_v1", "true"),
        )
    connection.commit()
    connection.close()


init_db()


def get_location_and_weather(location_name=None):
    location_name = (location_name or "Hyderabad").strip() or "Hyderabad"
    lat, lon, location_meta = resolve_location(location_name)
    weather = get_current_weather(lat, lon)
    return {
        "location": location_name,
        "resolved_location": location_meta,
        "coordinates": {"lat": lat, "lon": lon},
        "weather": weather,
    }


def get_recent_alerts(limit=10):
    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute(
        "SELECT title, risk_level, probability, location, message, created_at, status FROM alerts ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    connection.close()
    return [
        {
            "title": row[0],
            "risk_level": row[1],
            "probability": row[2],
            "location": row[3],
            "message": row[4],
            "created_at": row[5],
            "status": row[6],
        }
        for row in rows
    ]


def persist_alert(alert):
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        "INSERT INTO alerts (title, risk_level, probability, location, message, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            alert.get("title", "AquaSentinel Alert"),
            alert.get("risk_level", "UNKNOWN"),
            alert.get("probability", 0.0),
            alert.get("location", "Unknown"),
            alert.get("message", "AquaSentinel alert"),
            alert.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
            alert.get("status", "new"),
        ),
    )
    connection.execute(
        "INSERT INTO history (title, risk_level, probability, location, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            alert.get("title", "AquaSentinel Alert"),
            alert.get("risk_level", "UNKNOWN"),
            alert.get("probability", 0.0),
            alert.get("location", "Unknown"),
            alert.get("message", "AquaSentinel alert"),
            alert.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
        ),
    )
    connection.commit()
    connection.close()
    notification_manager.add_alert(alert)
    return alert


def get_request_location():
    if request.method == "POST" and request.is_json:
        payload = request.get_json(silent=True) or {}
        return payload.get("location") or payload.get("city") or payload.get("query")
    if request.method == "POST":
        return request.form.get("location") or request.form.get("city") or request.form.get("query")
    return request.args.get("location") or request.args.get("city") or request.args.get("query")


def evaluate_prediction(location_name=None):
    location_data = get_location_and_weather(location_name)
    location_name = location_data["location"]
    weather = location_data["weather"]
    feature_vector = build_model_feature_vector(weather)

    result = {
        "location": location_name,
        "coordinates": location_data["coordinates"],
        "resolved_location": location_data["resolved_location"],
        "weather": weather,
        "model_loaded": MODEL is not None,
        "model_status": "ready" if MODEL is not None else "unavailable",
        "model_message": MODEL_ERROR,
        "probability": None,
        "risk_level": "Data unavailable",
        "status": "Data unavailable",
        "water_management": {
            "status": "Data unavailable",
            "message": "Flood-model data is unavailable in the current environment.",
            "recommended_action": "Recommended Action",
            "confirmation_required": "Requires human/operator confirmation.",
        },
        "alert": None,
    }

    if MODEL is not None and feature_vector is not None:
        try:
            probability = float(MODEL.predict_proba([feature_vector])[0][1])
            result["probability"] = round(probability * 100, 2)
            result["risk_level"] = risk_level_from_probability(probability)
            result["status"] = result["risk_level"]
            result["water_management"] = build_water_management_report(
                probability,
                rainfall=weather.get("rainfall", 0),
                temperature=weather.get("temperature", 0),
                humidity=weather.get("humidity", 0),
                current_weather=weather,
                forecast_rainfall=weather.get("rainfall", 0),
            )
            weather_summary = (
                f"{weather.get('condition', 'Unknown')} / {weather.get('temperature', 'n/a')}°C / "
                f"{weather.get('humidity', 'n/a')}% humidity"
            )
            result["alert"] = build_alert_for_prediction(
                location_name,
                probability,
                weather_summary,
                result["water_management"].get("actions", ["Continue monitoring"]),
            )
            result["alert"]["status"] = "new"
        except Exception as exc:  # pragma: no cover - environment or model dependent
            result["status"] = "Data unavailable"
            result["model_message"] = f"Prediction failed: {exc}"
    else:
        result["model_message"] = MODEL_ERROR or "Prediction unavailable because the legacy model cannot be loaded in this environment."

    if result["alert"]:
        persist_alert(result["alert"])

    return result


@app.route("/")
@app.route("/index.html")
def index():
    """Render the AquaSentinel dashboard."""
    location = request.args.get("location") or "Hyderabad"
    prediction = evaluate_prediction(location)
    return render_template(
        "index.html",
        location=prediction["location"],
        data=prediction,
        alerts=get_recent_alerts(5),
    )


@app.route("/api/weather", methods=["GET", "POST"])
def weather_api():
    location_name = get_request_location() or "Hyderabad"
    location_data = get_location_and_weather(location_name)
    return jsonify({"status": "ok", "location": location_name, "data": location_data})


@app.route("/api/forecast", methods=["GET", "POST"])
def forecast_api():
    location_name = get_request_location() or "Hyderabad"
    location_data = get_location_and_weather(location_name)
    forecast_payload = get_forecast_data(location_data["coordinates"]["lat"], location_data["coordinates"]["lon"])
    forecast_projection = build_forecast_risk_projection(MODEL, forecast_payload)
    return jsonify({
        "status": "ok",
        "location": location_name,
        "forecast": forecast_payload,
        "projection": forecast_projection,
    })


@app.route("/api/predict", methods=["GET", "POST"])
def predict_api():
    location_name = get_request_location() or "Hyderabad"
    result = evaluate_prediction(location_name)
    return jsonify({"status": "ok", "location": location_name, "data": result})


@app.route("/api/flood-forecast", methods=["GET", "POST"])
def flood_forecast_api():
    location_name = get_request_location() or "Hyderabad"
    location_data = get_location_and_weather(location_name)
    forecast_payload = get_forecast_data(location_data["coordinates"]["lat"], location_data["coordinates"]["lon"])
    projection = build_forecast_risk_projection(MODEL, forecast_payload)
    return jsonify({"status": "ok", "location": location_name, "data": projection})


@app.route("/api/water-management", methods=["GET", "POST"])
def water_management_api():
    location_name = get_request_location() or "Hyderabad"
    result = evaluate_prediction(location_name)
    return jsonify({"status": "ok", "location": location_name, "data": result["water_management"]})


@app.route("/api/alerts", methods=["GET", "POST"])
def alerts_api():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        location_name = payload.get("location") or "Hyderabad"
        summary = payload.get("summary") or "AquaSentinel alert"
        weather = get_location_and_weather(location_name)["weather"]
        alert = build_alert_for_prediction(
            location_name,
            payload.get("probability", 0.5),
            summary,
            payload.get("actions") or ["Continue monitoring"],
        )
        persist_alert(alert)
        return jsonify({"status": "ok", "alert": alert})
    return jsonify({"status": "ok", "alerts": get_recent_alerts(10)})


@app.route("/api/history", methods=["GET"])
def history_api():
    connection = sqlite3.connect(DB_PATH)
    rows = connection.execute(
        """
        SELECT h.id, h.title, h.risk_level, h.probability, h.location, h.message, h.created_at
        FROM history h
        JOIN (
            SELECT MAX(id) AS id
            FROM history
            WHERE lower(location) = lower(?)
            GROUP BY location, substr(created_at, 1, 16)
            ORDER BY MAX(id) DESC
            LIMIT 30
        ) recent ON recent.id = h.id
        ORDER BY h.id ASC
        """,
        (request.args.get("location") or "Hyderabad",),
    ).fetchall()
    connection.close()
    return jsonify({
        "status": "ok",
        "history": [
            {
                "id": row[0],
                "title": row[1],
                "risk_level": row[2],
                "probability": row[3],
                "location": row[4],
                "message": row[5],
                "created_at": row[6],
            }
            for row in rows
        ],
    })


@app.route("/api/settings", methods=["GET", "POST"])
def settings_api():
    connection = sqlite3.connect(DB_PATH)
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        for key, value in (payload or {}).items():
            connection.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (str(key), str(value)))
        connection.commit()
    rows = connection.execute("SELECT key, value FROM settings").fetchall()
    connection.close()
    settings = {key: value for key, value in rows}
    settings.setdefault("alert_email_configured", bool(os.getenv("ALERT_EMAIL")))
    settings.setdefault("forecast_source", "OpenWeather")
    settings.setdefault("model_status", "ready" if MODEL is not None else "unavailable")
    return jsonify({"status": "ok", "settings": settings})


@app.route("/api/alerts/test", methods=["GET", "POST"])
def test_alert_api():
    location_name = get_request_location() or "Hyderabad"
    alert = build_alert_for_prediction(
        location_name,
        0.65,
        "Test mode / 28°C / 70% humidity",
        [
            "Recommended Action",
            "Requires human/operator confirmation.",
            "Continue monitoring and verify local conditions.",
        ],
    )
    persist_alert(alert)
    email_result = send_email_alert(alert)
    return jsonify({"status": "ok", "alert": alert, "email": email_result})


@app.route("/api/model-info")
def model_info_api():
    return jsonify({
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_file": str(MODEL_PATH),
        "model_error": MODEL_ERROR,
        "feature_contract": ["temperature", "max_temperature", "wind_speed", "cloudiness", "rainfall", "humidity"],
    })


@app.route("/api/model-comparison")
def model_comparison_api():
    if not MODEL_COMPARISON_PATH.exists():
        return jsonify({
            "status": "unavailable",
            "message": "Model comparison results have not been generated yet.",
        }), 404
    with MODEL_COMPARISON_PATH.open("r", encoding="utf-8") as handle:
        return jsonify(json.load(handle))


@app.route("/api/health")
def health_api():
    return jsonify({
        "status": "ok",
        "service": "AquaSentinel",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model_loaded": MODEL is not None,
        "openweather_configured": bool(get_weather_api_key()),
        "database": str(DB_PATH.exists()),
    })


@app.route("/predicts.html")
def predicts_page():
    return redirect("/")


@app.route("/plots.html")
def plots_page():
    return redirect("/")


@app.route("/heatmaps.html")
def heatmaps_page():
    return redirect("/")


@app.route("/satellite.html")
def satellite_page():
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)