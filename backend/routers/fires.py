from fastapi import APIRouter, Query
from typing import List, Optional
from schemas import FireHotspot
from services.nasa_firms import get_fire_hotspots, filter_by_bbox, filter_by_days
from config import settings

router = APIRouter()


@router.get("/", response_model=List[FireHotspot])
async def get_fires(
    days: int = Query(default=7, ge=1, le=10, description="Number of days of data"),
    lat: Optional[float] = Query(default=None, description="Center latitude for radius filter"),
    lon: Optional[float] = Query(default=None, description="Center longitude for radius filter"),
    radius_km: float = Query(default=500.0, description="Search radius in km"),
    bbox: Optional[str] = Query(default=None, description="Bounding box: lon_min,lat_min,lon_max,lat_max")
):
    """
    Fetch fire hotspots from NASA FIRMS VIIRS satellite data.
    
    - **days**: 1–10 days of historical data
    - **lat/lon + radius_km**: Filter to circular region
    - **bbox**: Filter to bounding box (overrides lat/lon)
    """
    hotspots = await get_fire_hotspots(
        map_key=settings.NASA_FIRMS_KEY,
        days=days,
        bbox=bbox or settings.INDIA_BBOX
    )
    
    # Apply filters
    hotspots = filter_by_days(hotspots, days)
    
    if lat is not None and lon is not None and not bbox:
        hotspots = filter_by_bbox(hotspots, lat, lon, radius_km)
    
    return hotspots


@router.get("/stats")
async def get_fire_stats(
    days: int = Query(default=7, ge=1, le=10),
    bbox: Optional[str] = None
):
    """Get aggregated fire statistics."""
    hotspots = await get_fire_hotspots(
        map_key=settings.NASA_FIRMS_KEY,
        days=days,
        bbox=bbox or settings.INDIA_BBOX
    )
    hotspots = filter_by_days(hotspots, days)
    
    high_conf = [h for h in hotspots if h.confidence == "h"]
    total_frp = sum(h.frp for h in hotspots)
    
    return {
        "total_fires": len(hotspots),
        "high_confidence": len(high_conf),
        "total_frp_mw": round(total_frp, 2),
        "avg_frp_mw": round(total_frp / len(hotspots), 2) if hotspots else 0,
        "days": days
    }
