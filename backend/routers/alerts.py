from fastapi import APIRouter
from typing import List, Optional
from schemas import Alert
from services.alert_service import get_demo_alerts, generate_alerts_from_analysis
from services.nasa_firms import get_fire_hotspots, filter_by_days
from services.cv_analyzer import cv_analyzer
from config import settings

router = APIRouter()


@router.get("/", response_model=List[Alert])
async def get_alerts(
    days: int = 7,
    bbox: Optional[str] = None
):
    """
    Get current environmental alerts for any target bbox.
    Runs live analysis and generates alerts from satellite data.
    """
    try:
        hotspots = await get_fire_hotspots(
            map_key=settings.NASA_FIRMS_KEY,
            days=days,
            bbox=bbox or settings.INDIA_BBOX
        )
        hotspots = filter_by_days(hotspots, days)
        
        if not hotspots:
            return get_demo_alerts()
        
        analysis = cv_analyzer.analyze(hotspots, "India", days)
        alerts = await generate_alerts_from_analysis(hotspots, analysis, "India")
        
        return alerts if alerts else get_demo_alerts()
    
    except Exception as e:
        print(f"[Alerts] Error: {e}")
        return get_demo_alerts()


@router.get("/demo", response_model=List[Alert])
async def get_demo_alert_data():
    """Get demo alerts for testing the dashboard without real data."""
    return get_demo_alerts()
