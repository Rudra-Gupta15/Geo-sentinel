"""
Earth Intelligence Copilot — FastAPI Backend
==========================================
Multi-hazard environmental monitoring: fires, floods, earthquakes,
cyclones, landslides, heatwaves, droughts + AI predictions.

Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from routers import fires, analysis, chat, alerts, disasters, news, weather, predict, history

app = FastAPI(
    title="🌍 Earth Intelligence Copilot",
    description="AI-powered multi-hazard satellite environmental monitoring system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Core routes ──────────────────────────────────────────────────────
app.include_router(fires.router,     prefix="/api/fires",     tags=["🔥 Fires"])
app.include_router(analysis.router,  prefix="/api/analysis",  tags=["🛰️ Analysis"])
app.include_router(chat.router,      prefix="/api/chat",      tags=["💬 Chat"])
app.include_router(alerts.router,    prefix="/api/alerts",    tags=["🚨 Alerts"])

# ── New multi-hazard routes ───────────────────────────────────────────
app.include_router(disasters.router, prefix="/api/disasters", tags=["⚠️ Disasters"])
app.include_router(news.router,      prefix="/api/news",      tags=["📰 News"])
app.include_router(weather.router,   prefix="/api/weather",   tags=["🌡️ Weather"])
app.include_router(predict.router,   prefix="/api/predict",   tags=["🔮 Predictions"])
app.include_router(history.router,   prefix="/api/history",   tags=["📅 History"])


@app.get("/api/health")
async def health_check():
    return {"status": "online", "service": "Earth Intelligence Copilot", "version": "2.0.0"}


@app.get("/api/stats")
async def get_global_stats(bbox: str = None):
    """High-level dashboard stats."""
    from services.nasa_firms import get_fire_hotspots, filter_by_days
    from services.cv_analyzer import cv_analyzer
    from services.gdacs_service import get_live_disasters
    from config import settings

    target_bbox = bbox or settings.INDIA_BBOX
    hotspots = await get_fire_hotspots(settings.NASA_FIRMS_KEY, 7, target_bbox)
    hotspots = filter_by_days(hotspots, 7)
    analysis = cv_analyzer.analyze(hotspots, "India", 7)
    disasters = await get_live_disasters(limit=50)

    return {
        "total_fires_7d": analysis["fire_count"],
        "forest_loss_pct": analysis["forest_loss_pct"],
        "flood_risk": analysis["flood_risk"],
        "alert_level": analysis["alert_level"],
        "co2_tons": analysis["estimated_co2_tons"],
        "air_quality": analysis["air_quality_impact"],
        "active_disasters": len(disasters),
        "critical_events": len([d for d in disasters if d.get("severity") in ["Red", "critical"]]),
    }


# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/style.css", include_in_schema=False)
    async def serve_css():
        return FileResponse(os.path.join(frontend_dir, "style.css"), media_type="text/css")

    @app.get("/app.js", include_in_schema=False)
    async def serve_js():
        return FileResponse(os.path.join(frontend_dir, "app.js"), media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
