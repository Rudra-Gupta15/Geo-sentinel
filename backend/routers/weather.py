from fastapi import APIRouter, Query
from services.weather_service import get_weather_data

router = APIRouter()


@router.get("/")
async def get_weather(
    lat: float = Query(default=20.5937, description="Latitude"),
    lon: float = Query(default=78.9629, description="Longitude")
):
    """Get current weather + heatwave/drought analysis for a location."""
    return await get_weather_data(lat=lat, lon=lon)


@router.get("/heatwave")
async def get_heatwave(lat: float = Query(...), lon: float = Query(...)):
    """Get heatwave risk assessment for a location."""
    data = await get_weather_data(lat=lat, lon=lon)
    return {
        "lat": lat, "lon": lon,
        "heatwave_active": data["heatwave_active"],
        "heatwave_index": data["heatwave_index"],
        "max_temp": data["max_temp_7d"],
        "risk_level": "Critical" if data["heatwave_index"] > 75 else
                      "High" if data["heatwave_index"] > 50 else
                      "Moderate" if data["heatwave_index"] > 25 else "Low"
    }


@router.get("/drought")
async def get_drought(lat: float = Query(...), lon: float = Query(...)):
    """Get drought index for a location."""
    data = await get_weather_data(lat=lat, lon=lon)
    return {
        "lat": lat, "lon": lon,
        "drought_index": data["drought_index"],
        "drought_severity": data["drought_severity"],
        "total_precip_7d": data["total_precip_7d"]
    }
