from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FireHotspot(BaseModel):
    lat: float
    lon: float
    brightness: float = 0.0
    confidence: str = "n"
    acq_date: str = ""
    acq_time: str = ""
    frp: float = 0.0  # Fire Radiative Power (MW)
    satellite: str = "VIIRS"


class AnalysisRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 100.0
    days: int = 7
    region_name: Optional[str] = "Selected Region"


class AnalysisResult(BaseModel):
    region: str
    days: int
    fire_count: int
    high_confidence_fires: int
    total_frp: float
    forest_loss_pct: float
    flood_risk: str         # Low / Moderate / High / Critical
    air_quality_impact: str
    estimated_co2_tons: float
    hotspots: List[FireHotspot]
    llm_insight: str
    alert_level: str        # Green / Yellow / Orange / Red
    timestamp: str


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    context: Optional[dict] = {}


class ChatResponse(BaseModel):
    reply: str
    sources: Optional[List[str]] = []


class Alert(BaseModel):
    id: str
    title: str
    description: str
    severity: str   # info / warning / danger / critical
    region: str
    lat: float
    lon: float
    timestamp: str
    type: str       # fire / deforestation / flood


class StatsResponse(BaseModel):
    total_fires_today: int
    total_fires_7d: int
    forest_loss_pct_7d: float
    high_risk_regions: int
    active_alerts: int
    last_updated: str
