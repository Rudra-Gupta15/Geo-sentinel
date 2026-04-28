"""
NASA Global Landslide Catalog
Fetches historical landslide events.
Free API endpoint from NASA Earthdata.

Catalog: https://catalog.data.gov/dataset/global-landslide-catalog
"""

import httpx
from typing import List, Dict
from datetime import datetime, timedelta
import math

LANDSLIDE_API = "https://pmm.nasa.gov/api/query/geoglows/landslide"

DEMO_LANDSLIDES = [
    {"id": "ls_001", "title": "Kinnaur Landslide — NH-5 Blocked", "lat": 31.52, "lon": 78.15, "date": (datetime.utcnow() - timedelta(days=5)).isoformat(), "trigger": "rain", "size": "large", "deaths": 14, "injuries": 8, "country": "India", "state": "Himachal Pradesh", "description": "Heavy monsoon rainfall triggered massive landslide blocking national highway for 72 hours.", "severity": "high"},
    {"id": "ls_002", "title": "Chamoli Rock Fall — Uttarakhand", "lat": 30.40, "lon": 79.35, "date": (datetime.utcnow() - timedelta(days=12)).isoformat(), "trigger": "rain", "size": "medium", "deaths": 3, "injuries": 12, "country": "India", "state": "Uttarakhand", "description": "Rock fall on Badrinath highway. NDRF team deployed for rescue.", "severity": "medium"},
    {"id": "ls_003", "title": "Wayanad Mudslide — Kerala", "lat": 11.60, "lon": 76.05, "date": (datetime.utcnow() - timedelta(days=8)).isoformat(), "trigger": "rain", "size": "large", "deaths": 27, "injuries": 40, "country": "India", "state": "Kerala", "description": "Catastrophic mudslide destroyed 3 villages. 27 confirmed dead, 40+ injured.", "severity": "critical"},
    {"id": "ls_004", "title": "Shimla Debris Flow", "lat": 31.10, "lon": 77.17, "date": (datetime.utcnow() - timedelta(days=20)).isoformat(), "trigger": "rain", "size": "small", "deaths": 0, "injuries": 2, "country": "India", "state": "Himachal Pradesh", "description": "Minor debris flow blocked road for 6 hours. No fatalities.", "severity": "low"},
    {"id": "ls_005", "title": "Sikkim Flash Flood + Landslide", "lat": 27.53, "lon": 88.51, "date": (datetime.utcnow() - timedelta(days=3)).isoformat(), "trigger": "rain", "size": "large", "deaths": 19, "injuries": 35, "country": "India", "state": "Sikkim", "description": "Glacial lake outburst triggered landslide and flooding. Army rescue ongoing.", "severity": "critical"},
    {"id": "ls_006", "title": "Arunachal Slope Failure", "lat": 28.21, "lon": 94.73, "date": (datetime.utcnow() - timedelta(days=15)).isoformat(), "trigger": "earthquake", "size": "medium", "deaths": 6, "injuries": 18, "country": "India", "state": "Arunachal Pradesh", "description": "Earthquake-triggered slope failure near Tawang. 6 casualties.", "severity": "high"},
    {"id": "ls_007", "title": "Darjeeling Tea Garden Landslide", "lat": 27.04, "lon": 88.26, "date": (datetime.utcnow() - timedelta(days=25)).isoformat(), "trigger": "rain", "size": "small", "deaths": 0, "injuries": 0, "country": "India", "state": "West Bengal", "description": "Landslide damaged tea garden. Fortunately no casualties.", "severity": "low"},
    {"id": "ls_008", "title": "Manipur Highway Blockade", "lat": 24.82, "lon": 93.94, "date": (datetime.utcnow() - timedelta(days=9)).isoformat(), "trigger": "rain", "size": "medium", "deaths": 2, "injuries": 5, "country": "India", "state": "Manipur", "description": "Multiple landslides blocked Imphal-Moreh highway for 4 days.", "severity": "medium"},
]


async def get_landslides(days: int = 30, lat: float = None, lon: float = None, radius_km: float = 500) -> List[Dict]:
    """Fetch landslide events. Falls back to demo data."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            params = {"format": "json", "limit": 100}
            if lat is not None and lon is not None:
                params.update({"lat": lat, "lon": lon, "radius": radius_km})
            resp = await client.get(LANDSLIDE_API, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return _parse_nasa_landslides(data, days)
    except Exception as e:
        print(f"[Landslide] API failed: {e}. Using demo data.")

    cutoff = datetime.utcnow() - timedelta(days=days)
    filtered = [ls for ls in DEMO_LANDSLIDES if datetime.fromisoformat(ls["date"]) >= cutoff]
    if lat is not None and lon is not None:
        filtered = [ls for ls in filtered if _haversine(lat, lon, ls["lat"], ls["lon"]) <= radius_km]
    return filtered


def _parse_nasa_landslides(data: list, days: int) -> List[Dict]:
    results = []
    cutoff = datetime.utcnow() - timedelta(days=days)
    for item in data:
        try:
            dt = datetime.fromisoformat(item.get("event_date", "").replace("Z", ""))
            if dt < cutoff:
                continue
            deaths = int(item.get("fatality_count", 0) or 0)
            results.append({
                "id": f"nasa_ls_{item.get('id', '')}",
                "title": item.get("event_description", "Landslide Event"),
                "lat": float(item.get("latitude", 0)),
                "lon": float(item.get("longitude", 0)),
                "date": dt.isoformat(),
                "trigger": item.get("landslide_trigger", "unknown"),
                "size": item.get("landslide_size", "unknown"),
                "deaths": deaths,
                "injuries": int(item.get("injury_count", 0) or 0),
                "country": item.get("country_name", "Unknown"),
                "state": item.get("admin_division_name", ""),
                "description": item.get("event_description", ""),
                "severity": "critical" if deaths > 10 else "high" if deaths > 3 else "medium" if deaths > 0 else "low"
            })
        except Exception:
            continue
    return results


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))
