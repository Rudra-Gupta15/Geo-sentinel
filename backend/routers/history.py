from fastapi import APIRouter, Query
from typing import Optional
from services.landslide_service import get_landslides
from services.gdacs_service import get_disaster_history
from services.nasa_firms import get_fire_hotspots, filter_by_days
from config import settings
from datetime import datetime

router = APIRouter()


@router.get("/events")
async def get_historical_events(
    event_type: Optional[str] = Query(default=None, description="Filter by type: fire, flood, landslide, etc."),
    days: int = Query(default=30, ge=1, le=365)
):
    """Get all historical hazard events for the past N days."""
    results = []

    # Fires from NASA FIRMS
    if not event_type or event_type == "fire":
        fires = await get_fire_hotspots(settings.NASA_FIRMS_KEY, days=min(days, 10), bbox=settings.INDIA_BBOX)
        fires = filter_by_days(fires, min(days, 10))
        results += [{"type": "fire", "icon": "🔥", "lat": f.lat, "lon": f.lon,
                     "date": f.acq_date, "title": f"Fire Hotspot (FRP: {f.frp:.0f} MW)",
                     "severity": "high" if f.frp > 50 else "medium" if f.frp > 20 else "low",
                     "id": f"fire_{i}"} for i, f in enumerate(fires)]

    # Landslides from NASA catalog
    if not event_type or event_type == "landslide":
        landslides = await get_landslides(days=days)
        results += [{"type": "landslide", "icon": "⛰️", "lat": ls["lat"], "lon": ls["lon"],
                     "date": ls["date"], "title": ls["title"],
                     "severity": ls["severity"], "id": ls["id"]} for ls in landslides]

    # Disasters from GDACS
    gdacs_hist = get_disaster_history(days=days)
    if event_type:
        gdacs_hist = [d for d in gdacs_hist if d["type"] == event_type]
    results += [{"type": d["type"], "icon": d["icon"], "lat": d["lat"], "lon": d["lon"],
                 "date": d["date"], "title": d["title"],
                 "severity": d["severity"].lower() if isinstance(d["severity"], str) else "medium",
                 "id": d["id"]} for d in gdacs_hist]

    # Sort by date descending
    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results[:200]


@router.get("/timeline")
async def get_timeline(
    lat: float = Query(default=20.5937),
    lon: float = Query(default=78.9629),
    radius_km: float = Query(default=500),
    days: int = Query(default=30, ge=1, le=365)
):
    """Get event timeline for a specific region (for the history scrubber)."""
    all_events = await get_historical_events(days=days)

    # Filter by radius
    import math
    def dist(e):
        dlat = math.radians(e["lat"] - lat)
        dlon = math.radians(e["lon"] - lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(e["lat"])) * math.sin(dlon/2)**2
        return 6371 * 2 * math.asin(math.sqrt(a))

    regional = [e for e in all_events if dist(e) <= radius_km]
    return {"events": regional, "total": len(regional), "days": days}


@router.get("/landslides")
async def get_landslide_history(days: int = Query(default=30, ge=1, le=365)):
    """Get NASA landslide catalog data."""
    return await get_landslides(days=days)
