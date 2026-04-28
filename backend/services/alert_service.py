"""
Alert Service — generates real-time environmental alerts from analysis data.
"""

import uuid
from datetime import datetime
from typing import List
from schemas import Alert, FireHotspot
from services.geocode_service import reverse_geocode


async def generate_alerts_from_analysis(
    hotspots: List[FireHotspot],
    analysis: dict,
    region: str = "India"
) -> List[Alert]:
    """Generate Alert objects from analysis results."""
    alerts = []
    now = datetime.utcnow().isoformat()

    # ─── Fire Alert ─────────────────────────────────────────────────────────
    fire_count = analysis.get("fire_count", 0)
    if fire_count > 0:
        severity = "critical" if fire_count > 15 else "danger" if fire_count > 8 else "warning" if fire_count > 3 else "info"
        
        # Find center of fire cluster
        avg_lat = sum(h.lat for h in hotspots) / len(hotspots)
        avg_lon = sum(h.lon for h in hotspots) / len(hotspots)
        
        # Reverse geocode to get Country › State › City
        precise_region = await reverse_geocode(avg_lat, avg_lon)

        alerts.append(Alert(
            id=str(uuid.uuid4())[:8],
            title=f"🔥 {fire_count} Active Fires Detected",
            description=(
                f"{fire_count} fire hotspots detected. "
                f"High-confidence fires: {analysis.get('high_confidence_fires', 0)}. "
                f"Total FRP: {analysis.get('total_frp', 0):.1f} MW."
            ),
            severity=severity,
            region=precise_region,
            lat=avg_lat,
            lon=avg_lon,
            timestamp=now,
            type="fire"
        ))

    # ─── Deforestation Alert ─────────────────────────────────────────────────
    forest_loss = analysis.get("forest_loss_pct", 0)
    if forest_loss > 5:
        severity = "critical" if forest_loss > 20 else "danger" if forest_loss > 12 else "warning"
        avg_lat = sum(h.lat for h in hotspots[:3]) / max(len(hotspots[:3]), 1)
        avg_lon = sum(h.lon for h in hotspots[:3]) / max(len(hotspots[:3]), 1)
        
        precise_region = await reverse_geocode(avg_lat, avg_lon)

        alerts.append(Alert(
            id=str(uuid.uuid4())[:8],
            title=f"🌲 {forest_loss:.1f}% Forest Loss Detected",
            description=(
                f"Satellite analysis shows {forest_loss:.1f}% vegetation loss. "
                f"Estimated CO2 release: {analysis.get('estimated_co2_tons', 0):.0f} tons. "
                f"Possible illegal logging or wildfire damage."
            ),
            severity=severity,
            region=precise_region,
            lat=avg_lat,
            lon=avg_lon,
            timestamp=now,
            type="deforestation"
        ))

    # ─── Air Quality Alert ───────────────────────────────────────────────────
    aq = analysis.get("air_quality_impact", "Good")
    if aq in ["Unhealthy", "Very Unhealthy", "Hazardous"]:
        avg_lat = sum(h.lat for h in hotspots) / len(hotspots)
        avg_lon = sum(h.lon for h in hotspots) / len(hotspots)
        
        precise_region = await reverse_geocode(avg_lat, avg_lon)

        alerts.append(Alert(
            id=str(uuid.uuid4())[:8],
            title=f"💨 Air Quality: {aq}",
            description=(
                f"Smoke from wildfires has degraded air quality to '{aq}'. "
                f"Sensitive groups should avoid outdoor activity."
            ),
            severity="danger" if aq == "Hazardous" else "warning",
            region=precise_region,
            lat=avg_lat,
            lon=avg_lon,
            timestamp=now,
            type="fire"
        ))

    # ─── Flood Alert ─────────────────────────────────────────────────────────
    flood_risk = analysis.get("flood_risk", "Low")
    if flood_risk in ["High", "Moderate"]:
        ne_hotspots = [h for h in hotspots if h.lat > 24 and h.lon > 88]
        if ne_hotspots:
            precise_region = await reverse_geocode(ne_hotspots[0].lat, ne_hotspots[0].lon)
            alerts.append(Alert(
                id=str(uuid.uuid4())[:8],
                title=f"🌊 Flood Risk: {flood_risk}",
                description=(
                    f"Flood risk detected as {flood_risk}. "
                    f"Post-fire deforestation increases runoff and landslide vulnerability."
                ),
                severity="danger" if flood_risk == "High" else "warning",
                region=precise_region,
                lat=ne_hotspots[0].lat,
                lon=ne_hotspots[0].lon,
                timestamp=now,
                type="flood"
            ))

    return alerts


def get_demo_alerts() -> List[Alert]:
    """Return demo alerts when no real analysis has been done yet."""
    now = datetime.utcnow().isoformat()
    return [
        Alert(
            id="demo_001",
            title="🔥 14 Active Fires — Northeast Region",
            description="14 high-confidence fire hotspots detected. Total FRP: 621 MW. Possible agricultural burning or wildfire.",
            severity="danger",
            region="India › Assam › Guwahati",
            lat=26.2006,
            lon=92.9376,
            timestamp=now,
            type="fire"
        ),
        Alert(
            id="demo_002",
            title="🌲 8.3% Forest Loss — Eastern Region",
            description="Significant vegetation loss detected over last 7 days. Estimated CO2: 420 tons. Illegal logging suspected.",
            severity="warning",
            region="India › Jharkhand › Ranchi",
            lat=23.6102,
            lon=85.2799,
            timestamp=now,
            type="deforestation"
        ),
        Alert(
            id="demo_003",
            title="💨 Air Quality: Unhealthy — Central Region",
            description="Smoke from wildfires has degraded air quality. Sensitive groups should reduce outdoor exposure.",
            severity="warning",
            region="India › Madhya Pradesh › Bhopal",
            lat=23.4733,
            lon=77.9470,
            timestamp=now,
            type="fire"
        ),
    ]
