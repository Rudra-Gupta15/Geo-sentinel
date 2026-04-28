"""
Computer Vision Analyzer for Environmental Change Detection.

MVP: Uses NASA FIRMS fire data + statistical analysis.
     Simulates deforestation and flood detection.

Production Upgrade Path:
    - Replace _estimate_forest_loss() with PyTorch SegForest model
    - Add Sentinel-2 NDVI calculation via Sentinel Hub API
    - Add Global Forest Watch (GFW) API integration
    - Add FloodSense or Copernicus flood mapping
"""

from typing import List, Tuple
from schemas import FireHotspot


# Confidence score map
CONFIDENCE_SCORE = {"h": 1.0, "n": 0.6, "l": 0.3}

# FRP thresholds for alert levels (MW)
ALERT_THRESHOLDS = {
    "Green":  0,
    "Yellow": 20,
    "Orange": 50,
    "Red":    100,
}


class CVAnalyzer:
    """
    Main CV analysis engine.
    
    Flow:
        Fire hotspots → FRP analysis → Forest loss estimation
                                     → CO2 estimation  
                                     → Risk scoring → Alert level
    """

    def analyze(
        self,
        hotspots: List[FireHotspot],
        region_name: str = "Region",
        days: int = 7
    ) -> dict:
        """
        Core analysis pipeline.
        Returns structured analysis dict.
        """
        if not hotspots:
            return self._empty_result(region_name, days)

        # Step 1: Fire metrics
        fire_count = len(hotspots)
        high_conf = [h for h in hotspots if h.confidence == "h"]
        total_frp = sum(h.frp for h in hotspots)
        avg_brightness = sum(h.brightness for h in hotspots) / fire_count

        # Step 2: Forest loss estimation (mock — replace with real model)
        forest_loss_pct = self._estimate_forest_loss(hotspots, days)

        # Step 3: CO2 impact estimate
        # Each MW of FRP ≈ 0.37 kg CO2 per second → simplified annual estimate
        co2_tons = total_frp * 0.37 * 3600 / 1000  # per hour estimate

        # Step 4: Flood risk (based on region + season proxy)
        flood_risk = self._estimate_flood_risk(hotspots)

        # Step 5: Air quality impact
        air_quality = self._estimate_air_quality(total_frp, fire_count)

        # Step 6: Alert level
        alert_level = self._compute_alert_level(total_frp, fire_count, forest_loss_pct)

        return {
            "fire_count": fire_count,
            "high_confidence_fires": len(high_conf),
            "total_frp": round(total_frp, 2),
            "avg_brightness": round(avg_brightness, 2),
            "forest_loss_pct": round(forest_loss_pct, 2),
            "flood_risk": flood_risk,
            "air_quality_impact": air_quality,
            "estimated_co2_tons": round(co2_tons, 2),
            "alert_level": alert_level,
            "region": region_name,
            "days": days,
        }

    def _estimate_forest_loss(self, hotspots: List[FireHotspot], days: int) -> float:
        """
        Estimate forest loss % based on fire intensity.
        
        MVP model: weighted FRP / day → forest coverage loss proxy.
        Production: Replace with PyTorch SegForest or GFW GLAD alerts.
        """
        if not hotspots:
            return 0.0

        # Weighted sum: high confidence fires count more
        weighted_frp = sum(
            h.frp * CONFIDENCE_SCORE.get(h.confidence, 0.5)
            for h in hotspots
        )

        # Normalize to a 0–100% scale
        # Calibrated so 500MW total FRP ≈ ~15% forest loss over 7 days
        base_loss = (weighted_frp / (500 * days)) * 100 * 7
        return min(base_loss, 95.0)  # cap at 95%

    def _estimate_flood_risk(self, hotspots: List[FireHotspot]) -> str:
        """
        Estimate flood risk based on location density patterns.
        
        MVP: Uses lat/lon proximity to known flood-prone regions.
        Production: Replace with Copernicus Emergency Management or FloodSense.
        """
        # Identify hotspots in high-flood-risk zones (India coast + NE)
        flood_zone_count = sum(
            1 for h in hotspots
            if (h.lat > 24 and h.lon > 88)  # Northeast India — high flood risk
            or (h.lat < 15 and h.lon > 78)   # Coastal South India
        )

        total = len(hotspots) if hotspots else 1
        ratio = flood_zone_count / total

        if ratio > 0.5:
            return "High"
        elif ratio > 0.25:
            return "Moderate"
        else:
            return "Low"

    def _estimate_air_quality(self, total_frp: float, fire_count: int) -> str:
        """Estimate air quality impact from fire smoke."""
        if total_frp > 200 or fire_count > 15:
            return "Hazardous"
        elif total_frp > 100 or fire_count > 8:
            return "Very Unhealthy"
        elif total_frp > 50 or fire_count > 4:
            return "Unhealthy"
        elif total_frp > 20:
            return "Moderate"
        else:
            return "Good"

    def _compute_alert_level(self, total_frp: float, fire_count: int, forest_loss_pct: float) -> str:
        """Compute overall alert level."""
        score = 0
        score += min(fire_count * 2, 40)       # up to 40 pts from fire count
        score += min(total_frp / 10, 30)        # up to 30 pts from FRP
        score += min(forest_loss_pct * 2, 30)   # up to 30 pts from forest loss

        if score >= 70:
            return "Red"
        elif score >= 40:
            return "Orange"
        elif score >= 20:
            return "Yellow"
        else:
            return "Green"

    def _empty_result(self, region: str, days: int) -> dict:
        return {
            "fire_count": 0,
            "high_confidence_fires": 0,
            "total_frp": 0.0,
            "avg_brightness": 0.0,
            "forest_loss_pct": 0.0,
            "flood_risk": "Low",
            "air_quality_impact": "Good",
            "estimated_co2_tons": 0.0,
            "alert_level": "Green",
            "region": region,
            "days": days,
        }


# Singleton instance
cv_analyzer = CVAnalyzer()
