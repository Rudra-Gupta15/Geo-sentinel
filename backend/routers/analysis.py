from fastapi import APIRouter
from datetime import datetime
from schemas import AnalysisRequest, AnalysisResult
from services.nasa_firms import get_fire_hotspots, filter_by_bbox, filter_by_days
from services.cv_analyzer import cv_analyzer
from services.llm_service import generate_insight
from config import settings

router = APIRouter()


@router.post("/", response_model=AnalysisResult)
async def analyze_region(req: AnalysisRequest):
    """
    Full analysis pipeline for a geographic region.
    
    Flow:
        1. Fetch NASA FIRMS fire hotspots
        2. Filter to requested region
        3. CV analysis (forest loss, CO2, risk scores)
        4. LLM insight generation
        5. Return structured result
    """
    # Step 1: Fetch satellite fire data for the requested region
    # Compute a bounding box from lat/lon/radius so non-India regions work correctly
    import math
    lat_deg = req.radius_km / 111.0
    lon_deg = req.radius_km / (111.0 * math.cos(math.radians(req.lat)))
    computed_bbox = (
        f"{req.lon - lon_deg:.4f},{req.lat - lat_deg:.4f},"
        f"{req.lon + lon_deg:.4f},{req.lat + lat_deg:.4f}"
    )
    # Fall back to INDIA_BBOX only when the computed box is essentially all of India
    fetch_bbox = computed_bbox if req.radius_km < 2000 else settings.INDIA_BBOX

    all_hotspots = await get_fire_hotspots(
        map_key=settings.NASA_FIRMS_KEY,
        days=req.days,
        bbox=fetch_bbox
    )
    all_hotspots = filter_by_days(all_hotspots, req.days)

    # Step 2: Filter to requested region
    regional_hotspots = filter_by_bbox(all_hotspots, req.lat, req.lon, req.radius_km)

    # Step 3: CV analysis
    analysis = cv_analyzer.analyze(
        hotspots=regional_hotspots,
        region_name=req.region_name or f"({req.lat:.2f}, {req.lon:.2f})",
        days=req.days
    )

    # Step 4: LLM insight
    llm_insight = await generate_insight(analysis)

    # Step 5: Build response
    return AnalysisResult(
        region=analysis["region"],
        days=analysis["days"],
        fire_count=analysis["fire_count"],
        high_confidence_fires=analysis["high_confidence_fires"],
        total_frp=analysis["total_frp"],
        forest_loss_pct=analysis["forest_loss_pct"],
        flood_risk=analysis["flood_risk"],
        air_quality_impact=analysis["air_quality_impact"],
        estimated_co2_tons=analysis["estimated_co2_tons"],
        alert_level=analysis["alert_level"],
        hotspots=regional_hotspots[:50],  # limit to 50 hotspots in response
        llm_insight=llm_insight,
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/india")
async def analyze_india(days: int = 7):
    """Quick full-India analysis using default bounding box."""
    req = AnalysisRequest(
        lat=20.5937,
        lon=78.9629,
        radius_km=2500,
        days=days,
        region_name="India"
    )
    return await analyze_region(req)
