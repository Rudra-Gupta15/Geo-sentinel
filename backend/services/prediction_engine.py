"""
Prediction Engine — Statistical Risk Forecaster
Computes future hazard risk percentages based on:
  - Historical event frequency in the region
  - Current weather conditions
  - Seasonal factors
  - Recent activity indicators

Output: { wildfire: 72, landslide: 35, flood: 58, heatwave: 80, drought: 65, earthquake: 12, cyclone: 45 }
"""

from typing import Dict, List
from datetime import datetime
import math


# India region risk profiles (baseline historical frequency)
REGION_BASELINES = {
    # Northeast: high fire + flood + landslide
    "northeast": {"wildfire": 65, "flood": 75, "landslide": 70, "cyclone": 20, "earthquake": 35, "heatwave": 30, "drought": 15},
    # Northwest: high heatwave + drought
    "northwest":  {"wildfire": 45, "flood": 25, "landslide": 20, "cyclone": 5,  "earthquake": 30, "heatwave": 90, "drought": 80},
    # South: moderate all, higher cyclone
    "south":      {"wildfire": 35, "flood": 55, "landslide": 40, "cyclone": 65, "earthquake": 20, "heatwave": 60, "drought": 40},
    # Central: moderate fire + heatwave
    "central":    {"wildfire": 55, "flood": 45, "landslide": 30, "cyclone": 10, "earthquake": 25, "heatwave": 75, "drought": 55},
    # Himalayan: high landslide + earthquake
    "himalayan":  {"wildfire": 40, "flood": 60, "landslide": 85, "cyclone": 5,  "earthquake": 70, "heatwave": 25, "drought": 30},
    # Coastal east: high cyclone + flood
    "coastal_e":  {"wildfire": 25, "flood": 70, "landslide": 35, "cyclone": 80, "earthquake": 15, "heatwave": 50, "drought": 20},
    # Coastal west: moderate cyclone
    "coastal_w":  {"wildfire": 30, "flood": 55, "landslide": 50, "cyclone": 45, "earthquake": 20, "heatwave": 55, "drought": 35},
    # Default
    "default":    {"wildfire": 40, "flood": 45, "landslide": 35, "cyclone": 30, "earthquake": 25, "heatwave": 50, "drought": 40},
}

# Month-based seasonal multipliers (1.0 = normal)
SEASONAL_FACTORS = {
    # month: {hazard: multiplier}
    1:  {"wildfire": 1.2, "flood": 0.3, "cyclone": 0.2, "heatwave": 0.1, "drought": 1.5, "landslide": 0.3, "earthquake": 1.0},
    2:  {"wildfire": 1.3, "flood": 0.3, "cyclone": 0.2, "heatwave": 0.3, "drought": 1.4, "landslide": 0.3, "earthquake": 1.0},
    3:  {"wildfire": 1.5, "flood": 0.4, "cyclone": 0.3, "heatwave": 0.6, "drought": 1.3, "landslide": 0.4, "earthquake": 1.0},
    4:  {"wildfire": 1.8, "flood": 0.5, "cyclone": 0.4, "heatwave": 1.2, "drought": 1.2, "landslide": 0.5, "earthquake": 1.0},
    5:  {"wildfire": 1.6, "flood": 0.7, "cyclone": 1.5, "heatwave": 1.8, "drought": 1.1, "landslide": 0.6, "earthquake": 1.0},
    6:  {"wildfire": 0.8, "flood": 1.8, "cyclone": 1.2, "heatwave": 1.5, "drought": 0.5, "landslide": 1.8, "earthquake": 1.0},
    7:  {"wildfire": 0.4, "flood": 2.0, "cyclone": 0.8, "heatwave": 0.8, "drought": 0.3, "landslide": 2.0, "earthquake": 1.0},
    8:  {"wildfire": 0.4, "flood": 2.0, "cyclone": 0.9, "heatwave": 0.7, "drought": 0.3, "landslide": 2.0, "earthquake": 1.0},
    9:  {"wildfire": 0.5, "flood": 1.8, "cyclone": 1.8, "heatwave": 0.6, "drought": 0.4, "landslide": 1.5, "earthquake": 1.0},
    10: {"wildfire": 0.7, "flood": 1.2, "cyclone": 1.5, "heatwave": 0.4, "drought": 0.7, "landslide": 0.9, "earthquake": 1.0},
    11: {"wildfire": 1.0, "flood": 0.6, "cyclone": 0.5, "heatwave": 0.2, "drought": 1.1, "landslide": 0.5, "earthquake": 1.0},
    12: {"wildfire": 1.1, "flood": 0.3, "cyclone": 0.2, "heatwave": 0.1, "drought": 1.4, "landslide": 0.3, "earthquake": 1.0},
}


def _detect_region(lat: float, lon: float) -> str:
    """Classify lat/lon into one of our region profiles."""
    if lat > 27 and lon > 88:
        return "northeast"
    if lat > 26 and lon < 78:
        return "northwest"
    if lat < 15:
        return "south"
    if lat > 27 and lon < 88:
        return "himalayan"
    if lon > 85 and lat < 22:
        return "coastal_e"
    if lon < 75 and lat < 22:
        return "coastal_w"
    return "central"


def compute_risk_profile(
    lat: float,
    lon: float,
    fire_count: int = 0,
    total_frp: float = 0,
    recent_landslides: int = 0,
    weather: dict = None,
    recent_disasters: list = None
) -> Dict:
    """
    Compute risk percentages for all hazard types at a given location.
    Returns: dict of hazard_type -> risk_percentage (0-100)
    """
    region = _detect_region(lat, lon)
    baseline = REGION_BASELINES.get(region, REGION_BASELINES["default"])
    month = datetime.utcnow().month
    seasonal = SEASONAL_FACTORS.get(month, SEASONAL_FACTORS[4])
    weather = weather or {}

    risks = {}

    for hazard in ["wildfire", "flood", "landslide", "cyclone", "earthquake", "heatwave", "drought"]:
        base = baseline[hazard]
        seasonal_mult = seasonal.get(hazard, 1.0)
        score = base * seasonal_mult

        # Boost from real-time data
        if hazard == "wildfire":
            if fire_count > 10:
                score += 15
            if total_frp > 100:
                score += 10
            heat_idx = weather.get("heatwave_index", 0)
            score += heat_idx * 0.2

        elif hazard == "landslide":
            if recent_landslides > 3:
                score += 20
            precip = weather.get("total_precip_7d", 0)
            if precip > 50:
                score += 15

        elif hazard == "flood":
            precip = weather.get("total_precip_7d", 0)
            if precip > 80:
                score += 25
            elif precip > 40:
                score += 10

        elif hazard == "heatwave":
            max_temp = weather.get("max_temp_7d", 35)
            if max_temp >= 45:
                score += 30
            elif max_temp >= 42:
                score += 20
            elif max_temp >= 40:
                score += 10

        elif hazard == "drought":
            drought_idx = weather.get("drought_index", 0)
            score += drought_idx * 0.3

        # Boost from recent disaster counts of the same type
        if recent_disasters:
            same_type = [d for d in recent_disasters if d.get("type") == hazard]
            score += min(len(same_type) * 5, 20)

        # Clamp 5–97
        risks[hazard] = max(5, min(97, round(score)))

    # Confidence label per risk level
    def confidence_label(pct):
        if pct >= 75:
            return "High Risk"
        elif pct >= 50:
            return "Moderate Risk"
        elif pct >= 25:
            return "Low Risk"
        else:
            return "Minimal Risk"

    return {
        "lat": lat, "lon": lon,
        "region_type": region,
        "month": month,
        "risks": risks,
        "labels": {k: confidence_label(v) for k, v in risks.items()},
        "dominant_hazard": max(risks, key=risks.get),
        "overall_risk": round(sum(risks.values()) / len(risks)),
        "timestamp": datetime.utcnow().isoformat()
    }
