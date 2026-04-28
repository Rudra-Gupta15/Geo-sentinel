from fastapi import APIRouter, Query
from typing import Optional
from services.gdelt_service import get_news

router = APIRouter()


@router.get("/")
async def fetch_news(
    hazard_type: Optional[str] = Query(default=None, description="Filter by hazard type"),
    query: Optional[str] = Query(default=None, description="Custom search query"),
    limit: int = Query(default=20, ge=1, le=50)
):
    """Fetch disaster news from GDELT."""
    return await get_news(hazard_type=hazard_type, query=query, limit=limit)


@router.get("/hazard/{hazard_type}")
async def news_by_hazard(hazard_type: str, limit: int = Query(default=10, ge=1, le=30)):
    """Fetch news filtered by hazard type."""
    return await get_news(hazard_type=hazard_type, limit=limit)
