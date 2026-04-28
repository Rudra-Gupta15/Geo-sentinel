from fastapi import APIRouter, Query
from services.prediction_engine import compute_risk_profile
from services.weather_service import get_weather_data
from services.nasa_firms import get_fire_hotspots, filter_by_bbox, filter_by_days
from services.landslide_service import get_landslides
from services.gdacs_service import get_live_disasters
from config import settings

router = APIRouter()


@router.get("/region")
async def predict_region(
    lat: float = Query(default=20.5937),
    lon: float = Query(default=78.9629),
    radius_km: float = Query(default=300)
):
    """
    Compute full hazard risk profile for a region.
    Returns percentage risk for each hazard type.
    """
    # Gather live data for better prediction accuracy
    weather = await get_weather_data(lat=lat, lon=lon)
    fires = await get_fire_hotspots(settings.NASA_FIRMS_KEY, days=7, bbox=settings.INDIA_BBOX)
    fires = filter_by_days(fires, 7)
    regional_fires = filter_by_bbox(fires, lat, lon, radius_km)
    landslides = await get_landslides(days=30, lat=lat, lon=lon, radius_km=radius_km)
    disasters = await get_live_disasters(limit=50)

    profile = compute_risk_profile(
        lat=lat, lon=lon,
        fire_count=len(regional_fires),
        total_frp=sum(f.frp for f in regional_fires),
        recent_landslides=len(landslides),
        weather=weather,
        recent_disasters=disasters
    )
    return profile


@router.get("/{hazard_type}")
async def predict_hazard(
    hazard_type: str,
    lat: float = Query(default=20.5937),
    lon: float = Query(default=78.9629)
):
    """Predict risk for a specific hazard type at a location."""
    weather = await get_weather_data(lat=lat, lon=lon)
    profile = compute_risk_profile(lat=lat, lon=lon, weather=weather)
    risk_pct = profile["risks"].get(hazard_type, 0)
    return {
        "hazard_type": hazard_type,
        "lat": lat, "lon": lon,
        "risk_percentage": risk_pct,
        "risk_label": profile["labels"].get(hazard_type, "Unknown"),
        "region_type": profile["region_type"],
        "timestamp": profile["timestamp"]
    }
