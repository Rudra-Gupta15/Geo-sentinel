"""
Weather Service — Open-Meteo API (free, no key required)
Provides: temperature, precipitation, heatwave index, drought assessment.

API: https://api.open-meteo.com/v1/forecast
"""

import httpx
from typing import Dict
from datetime import datetime

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"


async def get_weather_data(lat: float, lon: float) -> Dict:
    """Fetch current + forecast weather data for a location."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(OPEN_METEO_URL, params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "hourly": "temperature_2m,relativehumidity_2m,precipitation",
                "current_weather": True,
                "timezone": "Asia/Kolkata",
                "forecast_days": 7
            })
            resp.raise_for_status()
            data = resp.json()
            return _parse_weather(data, lat, lon)
    except Exception as e:
        print(f"[Weather] API failed: {e}. Using demo data.")
        return _demo_weather(lat, lon)


def _parse_weather(data: Dict, lat: float, lon: float) -> Dict:
    current = data.get("current_weather", {})
    daily = data.get("daily", {})
    temp_max = daily.get("temperature_2m_max", [35])
    precip = daily.get("precipitation_sum", [0])

    avg_temp = sum(temp_max) / len(temp_max) if temp_max else 35
    total_precip = sum(precip) if precip else 0
    max_temp = max(temp_max) if temp_max else 35
    wind = current.get("windspeed", 15)

    heatwave = max_temp >= 40
    heatwave_index = min(100, int((max_temp - 35) * 10)) if max_temp > 35 else 0
    drought_index = max(0, min(100, int(100 - total_precip * 5)))

    return {
        "lat": lat, "lon": lon,
        "current_temp": current.get("temperature", avg_temp),
        "max_temp_7d": round(max_temp, 1),
        "avg_temp_7d": round(avg_temp, 1),
        "total_precip_7d": round(total_precip, 1),
        "windspeed_kmh": round(wind, 1),
        "heatwave_active": heatwave,
        "heatwave_index": heatwave_index,
        "drought_index": drought_index,
        "drought_severity": "Extreme" if drought_index > 75 else "Severe" if drought_index > 50 else "Moderate" if drought_index > 25 else "None",
        "timestamp": datetime.utcnow().isoformat(),
        "forecast": [
            {"date": daily.get("time", [""])[i] if i < len(daily.get("time", [])) else "",
             "max_temp": temp_max[i] if i < len(temp_max) else 0,
             "precip": precip[i] if i < len(precip) else 0}
            for i in range(min(7, len(temp_max)))
        ]
    }


def _demo_weather(lat: float, lon: float) -> Dict:
    """Demo weather data."""
    # Simulate hotter weather for northern latitudes (heatwave zone)
    is_north = lat > 22
    base_temp = 44 if is_north else 36
    precip = 2 if is_north else 18
    heatwave_idx = 85 if is_north else 20
    drought_idx = 78 if is_north else 30

    return {
        "lat": lat, "lon": lon,
        "current_temp": base_temp - 2,
        "max_temp_7d": base_temp,
        "avg_temp_7d": base_temp - 3,
        "total_precip_7d": precip,
        "windspeed_kmh": 22,
        "heatwave_active": is_north,
        "heatwave_index": heatwave_idx,
        "drought_index": drought_idx,
        "drought_severity": "Severe" if drought_idx > 50 else "Moderate" if drought_idx > 25 else "None",
        "timestamp": datetime.utcnow().isoformat(),
        "forecast": [
            {"date": f"Day {i+1}", "max_temp": base_temp - i * 0.5, "precip": precip * (0.8 + i * 0.1)}
            for i in range(7)
        ]
    }
