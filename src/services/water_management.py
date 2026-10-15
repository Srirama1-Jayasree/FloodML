"""Transparent, advisory water management recommendation engine."""

from __future__ import annotations

from src.services.risk_engine import risk_level_from_probability, water_management_status_from_probability


def _get_risk_actions(risk_level):
    if risk_level == "LOW":
        return [
            "Continue normal monitoring",
            "Monitor rainfall and weather",
            "Maintain normal drainage operations",
            "Review local water storage levels",
        ]
    if risk_level == "MODERATE":
        return [
            "Increase monitoring frequency",
            "Inspect drainage channels",
            "Prepare drainage pumps",
            "Check vulnerable roads/areas",
            "Review reservoir/storage capacity",
            "Prepare emergency response resources",
        ]
    if risk_level == "HIGH":
        return [
            "Issue flood warning",
            "Activate emergency preparedness",
            "Prepare drainage pumps",
            "Inspect vulnerable infrastructure",
            "Prepare evacuation readiness",
            "Increase water-level monitoring",
            "Review reservoir storage/gate-management requirements",
        ]
    return [
        "Issue emergency warning",
        "Activate emergency response plan",
        "Coordinate evacuation readiness",
        "Inspect critical infrastructure",
        "Increase water-level monitoring",
        "Review reservoir storage and gate operations",
        "Prepare emergency resources and public communications",
    ]


def build_water_management_report(probability, rainfall=0.0, temperature=0.0, humidity=0.0, current_weather=None, forecast_rainfall=None):
    risk_level = risk_level_from_probability(probability)
    status = water_management_status_from_probability(probability)
    rainfall_value = float(rainfall or 0.0)
    forecast_value = float(forecast_rainfall or 0.0)

    if risk_level == "LOW":
        primary_message = "Consider water conservation and storage planning." if rainfall_value < 20 else "Continue normal monitoring and drainage operations."
    elif risk_level == "MODERATE":
        primary_message = "Increase drainage readiness and inspect vulnerable low-lying areas." if rainfall_value >= 20 else "Monitor rainfall closely and prepare drainage systems."
    elif risk_level == "HIGH":
        primary_message = "Prioritize drainage capacity and emergency water release planning." if forecast_value >= 20 else "Prioritize drainage capacity and flood preparedness."
    else:
        primary_message = "Activate emergency flood response coordination and critical infrastructure checks."

    report = {
        "status": status,
        "risk_level": risk_level,
        "message": primary_message,
        "reservoir_status": "Reservoir data unavailable",
        "drainage_status": "Drainage status unavailable",
        "pump_recommendation": "Prepare drainage pumps" if risk_level in {"MODERATE", "HIGH", "CRITICAL"} else "Normal pump readiness",
        "flood_preparedness": "Maintain routine readiness" if risk_level == "LOW" else "Escalate flood preparedness planning",
        "water_conservation_recommendation": "Consider water conservation and storage planning." if risk_level == "LOW" else "Prioritize water storage protection and flood readiness.",
        "recommended_action": "Recommended Action",
        "confirmation_required": "Requires human/operator confirmation.",
        "actions": _get_risk_actions(risk_level),
    }
    return report
