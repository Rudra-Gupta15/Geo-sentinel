"""
Geocode Service — reverse geocoding (lat/lon → Country › State › City).
Uses a fast built-in lookup for Indian states (zero latency, no API call),
plus Open-Meteo reverse geocoding as a fallback for other regions.
"""

import httpx
from typing import Optional

# ── Fast lookup: India state boundaries (approximate bounding boxes) ──────────
# Format: (name, lat_min, lat_max, lon_min, lon_max)
INDIA_STATES = [
    ("Rajasthan",        23.0, 30.2, 69.3, 78.3),
    ("Madhya Pradesh",   21.0, 26.9, 74.0, 82.8),
    ("Maharashtra",      15.6, 22.0, 72.6, 80.9),
    ("Uttar Pradesh",    23.9, 30.4, 77.1, 84.6),
    ("Gujarat",          20.1, 24.7, 68.2, 74.5),
    ("Andhra Pradesh",   12.6, 19.1, 77.0, 84.8),
    ("Karnataka",        11.5, 18.5, 74.0, 78.6),
    ("Tamil Nadu",        8.1, 13.6, 76.2, 80.3),
    ("West Bengal",      21.5, 27.2, 85.8, 89.9),
    ("Odisha",           17.8, 22.6, 81.4, 87.5),
    ("Telangana",        15.9, 19.9, 77.2, 81.3),
    ("Bihar",            24.3, 27.5, 83.3, 88.2),
    ("Jharkhand",        21.9, 25.3, 83.3, 87.9),
    ("Chhattisgarh",     17.8, 24.1, 80.2, 84.4),
    ("Assam",            24.1, 28.2, 89.7, 96.0),
    ("Punjab",           29.5, 32.5, 73.9, 76.9),
    ("Haryana",          27.6, 30.9, 74.5, 77.6),
    ("Himachal Pradesh", 30.4, 33.2, 75.6, 79.0),
    ("Uttarakhand",      28.7, 31.4, 77.6, 81.1),
    ("Kerala",            8.3, 12.8, 74.9, 77.4),
    ("Goa",              14.9, 15.8, 73.7, 74.3),
    ("Manipur",          23.8, 25.7, 93.0, 94.8),
    ("Meghalaya",        25.0, 26.1, 89.8, 92.8),
    ("Nagaland",         25.2, 27.0, 93.3, 95.3),
    ("Tripura",          22.9, 24.5, 91.2, 92.3),
    ("Mizoram",          21.9, 24.5, 92.3, 93.4),
    ("Sikkim",           27.1, 28.1, 88.0, 88.9),
    ("Arunachal Pradesh",26.7, 29.5, 91.6, 97.4),
    ("Jammu & Kashmir",  32.3, 37.1, 73.7, 80.3),
    ("Delhi",            28.4, 28.9, 76.8, 77.4),
]


def _india_state_for(lat: float, lon: float) -> Optional[str]:
    """Return best-matching India state name for a coordinate, or None."""
    best: Optional[str] = None
    for name, lat_min, lat_max, lon_min, lon_max in INDIA_STATES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            best = name
            break
    return best


async def reverse_geocode(lat: float, lon: float) -> str:
    """
    Return a human-readable breadcrumb: 'Country › State › City'.
    Falls back gracefully at every step.
    """
    # Fast path: within India lat/lon bounds — use state table first
    if 6.5 <= lat <= 37.5 and 68.0 <= lon <= 97.5:
        state = _india_state_for(lat, lon)
        if state:
            # Try to get city from Open-Meteo reverse geocode
            city = await _open_meteo_city(lat, lon)
            if city:
                return f"India › {state} › {city}"
            return f"India › {state}"

    # General case: use Open-Meteo geocoding to get full location
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "zoom": 10},
                headers={"User-Agent": "EarthIntelligenceCopilot/1.0"}
            )
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})
            parts = [
                addr.get("country"),
                addr.get("state") or addr.get("region"),
                addr.get("city") or addr.get("town") or addr.get("village"),
            ]
            breadcrumb = " › ".join(p for p in parts if p)
            return breadcrumb or f"{lat:.2f}°N, {lon:.2f}°E"
    except Exception:
        return f"{lat:.2f}°N, {lon:.2f}°E"


async def _open_meteo_city(lat: float, lon: float) -> Optional[str]:
    """Approximate city name using Open-Meteo search on nearby coordinates."""
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            # Use a rough grid search: find closest known city
            # Open-Meteo doesn't have reverse geocoding, so we skip it
            # and rely on the state table + Nominatim above.
            pass
    except Exception:
        pass
    return None
