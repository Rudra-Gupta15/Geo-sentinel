from fastapi import APIRouter, Query
from typing import Optional
from services.gdacs_service import get_live_disasters, get_disaster_history

router = APIRouter()


@router.get("/live")
async def get_live(limit: int = Query(default=50, ge=1, le=200)):
    """Fetch all active GDACS disaster events."""
    return await get_live_disasters(limit=limit)


@router.get("/history")
async def get_history(days: int = Query(default=30, ge=1, le=365)):
    """Return historical disaster events for past N days."""
    return get_disaster_history(days=days)


@router.get("/types")
async def get_disaster_types():
    """Return available disaster types."""
    return {
        "types": ["earthquake", "flood", "cyclone", "volcano", "drought", "wildfire", "tsunami", "landslide"],
        "icons": {
            "earthquake": "🏔️", "flood": "🌊", "cyclone": "🌀", "volcano": "🌋",
            "drought": "☀️", "wildfire": "🔥", "tsunami": "🌊", "landslide": "⛰️"
        }
    }
