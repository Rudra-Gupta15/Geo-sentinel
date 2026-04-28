"""
NASA FIRMS (Fire Information for Resource Management System)
Real-time fire data from VIIRS satellite.
Free API key: https://firms.modaps.eosdis.nasa.gov/api/
"""

import httpx
import csv
import io
import json
from typing import List, Dict
from schemas import FireHotspot

NASA_FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api"

# Demo/fallback data when API is unavailable
DEMO_HOTSPOTS = [
    {"lat": 23.25, "lon": 77.41, "brightness": 335.2, "confidence": "h", "acq_date": "2026-04-28", "acq_time": "0630", "frp": 45.2},
    {"lat": 21.14, "lon": 79.08, "brightness": 312.8, "confidence": "h", "acq_date": "2026-04-28", "acq_time": "0635", "frp": 38.1},
    {"lat": 19.89, "lon": 82.31, "brightness": 298.4, "confidence": "n", "acq_date": "2026-04-27", "acq_time": "0612", "frp": 22.7},
    {"lat": 24.67, "lon": 93.94, "brightness": 356.1, "confidence": "h", "acq_date": "2026-04-28", "acq_time": "0645", "frp": 67.3},
    {"lat": 26.55, "lon": 94.21, "brightness": 341.9, "confidence": "h", "acq_date": "2026-04-27", "acq_time": "0622", "frp": 53.8},
    {"lat": 13.09, "lon": 80.27, "brightness": 289.2, "confidence": "l", "acq_date": "2026-04-26", "acq_time": "0601", "frp": 15.3},
    {"lat": 22.97, "lon": 88.43, "brightness": 301.7, "confidence": "n", "acq_date": "2026-04-28", "acq_time": "0655", "frp": 28.9},
    {"lat": 28.64, "lon": 77.21, "brightness": 310.5, "confidence": "n", "acq_date": "2026-04-25", "acq_time": "0618", "frp": 19.4},
    {"lat": 17.38, "lon": 78.47, "brightness": 295.8, "confidence": "l", "acq_date": "2026-04-28", "acq_time": "0640", "frp": 12.6},
    {"lat": 26.84, "lon": 80.94, "brightness": 325.3, "confidence": "h", "acq_date": "2026-04-27", "acq_time": "0629", "frp": 41.7},
    {"lat": 23.66, "lon": 85.31, "brightness": 318.9, "confidence": "h", "acq_date": "2026-04-28", "acq_time": "0648", "frp": 35.2},
    {"lat": 20.46, "lon": 85.88, "brightness": 307.4, "confidence": "n", "acq_date": "2026-04-26", "acq_time": "0610", "frp": 24.8},
    {"lat": 15.34, "lon": 75.14, "brightness": 292.1, "confidence": "l", "acq_date": "2026-04-27", "acq_time": "0625", "frp": 11.3},
    {"lat": 27.18, "lon": 88.47, "brightness": 361.7, "confidence": "h", "acq_date": "2026-04-28", "acq_time": "0652", "frp": 72.1},
    {"lat": 25.09, "lon": 91.89, "brightness": 347.3, "confidence": "h", "acq_date": "2026-04-27", "acq_time": "0633", "frp": 58.4},
    {"lat": 12.97, "lon": 77.59, "brightness": 284.6, "confidence": "l", "acq_date": "2026-04-25", "acq_time": "0605", "frp": 9.7},
    {"lat": 29.34, "lon": 79.52, "brightness": 329.8, "confidence": "h", "acq_date": "2026-04-28", "acq_time": "0641", "frp": 44.6},
    {"lat": 18.52, "lon": 73.85, "brightness": 299.3, "confidence": "n", "acq_date": "2026-04-26", "acq_time": "0614", "frp": 18.2},
    {"lat": 11.67, "lon": 92.73, "brightness": 316.5, "confidence": "h", "acq_date": "2026-04-27", "acq_time": "0638", "frp": 33.9},
    {"lat": 22.31, "lon": 73.18, "brightness": 303.7, "confidence": "n", "acq_date": "2026-04-28", "acq_time": "0657", "frp": 21.5},
]


async def get_fire_hotspots(
    map_key: str,
    days: int = 7,
    bbox: str = None  # "lon_min,lat_min,lon_max,lat_max"
) -> List[FireHotspot]:
    """
    Fetch real fire hotspot data from NASA FIRMS VIIRS.
    Falls back to demo data if API fails.
    """
    if map_key == "DEMO_KEY" or not map_key:
        print("[NASA FIRMS] Using demo data. Set NASA_FIRMS_KEY for real data.")
        return _parse_demo_data(bbox)

    # Use bounding box if provided, else global
    area = bbox if bbox else "world"
    url = f"{NASA_FIRMS_BASE}/area/csv/{map_key}/VIIRS_SNPP_NRT/{area}/{min(days, 10)}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return _parse_firms_csv(resp.text)
    except Exception as e:
        print(f"[NASA FIRMS] API error: {e}. Using demo data.")
        return _parse_demo_data()


def _parse_firms_csv(csv_text: str) -> List[FireHotspot]:
    """Parse NASA FIRMS CSV response into FireHotspot objects."""
    hotspots = []
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            try:
                hotspots.append(FireHotspot(
                    lat=float(row.get("latitude", 0)),
                    lon=float(row.get("longitude", 0)),
                    brightness=float(row.get("bright_ti4", 0)),
                    confidence=str(row.get("confidence", "n")),
                    acq_date=str(row.get("acq_date", "")),
                    acq_time=str(row.get("acq_time", "")),
                    frp=float(row.get("frp", 0)),
                    satellite="VIIRS"
                ))
            except (ValueError, KeyError):
                continue
    except Exception as e:
        print(f"[FIRMS Parse] Error: {e}")
    return hotspots


def _parse_demo_data(bbox: str = None) -> List[FireHotspot]:
    """Return curated on-land demo hotspots, filtered to the visible bbox.
    Never generates random coordinates — avoids fires appearing in the ocean."""
    all_hotspots = [FireHotspot(**h, satellite="VIIRS_DEMO") for h in DEMO_HOTSPOTS]

    if not bbox or bbox == "DEMO_KEY" or bbox == "world":
        return all_hotspots

    try:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            return all_hotspots

        lon_min, lat_min, lon_max, lat_max = parts
        # Filter curated hotspots to those visible on screen
        visible = [h for h in all_hotspots
                   if lat_min <= h.lat <= lat_max and lon_min <= h.lon <= lon_max]
        # Always return at least the full set if nothing is visible
        return visible if visible else all_hotspots
    except Exception:
        return all_hotspots


def filter_by_bbox(hotspots: List[FireHotspot], lat: float, lon: float, radius_km: float) -> List[FireHotspot]:
    """Filter hotspots within radius (km) of a center point."""
    import math
    filtered = []
    for h in hotspots:
        # Haversine distance
        dlat = math.radians(h.lat - lat)
        dlon = math.radians(h.lon - lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(h.lat)) * math.sin(dlon/2)**2
        dist_km = 6371 * 2 * math.asin(math.sqrt(a))
        if dist_km <= radius_km:
            filtered.append(h)
    return filtered


def filter_by_days(hotspots: List[FireHotspot], days: int) -> List[FireHotspot]:
    """Filter hotspots to last N days."""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days)
    filtered = []
    for h in hotspots:
        try:
            acq_dt = datetime.strptime(h.acq_date, "%Y-%m-%d")
            if acq_dt >= cutoff:
                filtered.append(h)
        except ValueError:
            filtered.append(h)  # include if date parsing fails
    return filtered
