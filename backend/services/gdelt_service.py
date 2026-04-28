"""
GDELT — Global Database of Events, Language, and Tone
Fetches disaster-related news articles. Free API, no key needed.
"""

import httpx
from typing import List, Dict
from datetime import datetime, timedelta

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

HAZARD_QUERIES = {
    "wildfire":   "wildfire OR forest fire India",
    "flood":      "flood OR flooding India",
    "earthquake": "earthquake OR tremor India",
    "cyclone":    "cyclone OR typhoon India",
    "drought":    "drought India rainfall",
    "landslide":  "landslide OR mudslide India",
    "heatwave":   "heatwave India temperature",
}

DEMO_NEWS = [
    {"id": "news_001", "title": "Northeast India Wildfire Season Hits Record High", "url": "https://gdeltproject.org", "source": "Times of India", "date": (datetime.utcnow() - timedelta(hours=2)).isoformat(), "hazard_type": "wildfire", "sentiment": -0.72, "summary": "Satellite data shows 340% increase in fire hotspots across Manipur and Nagaland.", "tone": "negative"},
    {"id": "news_002", "title": "Assam Flood Toll Rises to 23, 200K Displaced", "url": "https://gdeltproject.org", "source": "NDTV", "date": (datetime.utcnow() - timedelta(hours=5)).isoformat(), "hazard_type": "flood", "sentiment": -0.88, "summary": "Brahmaputra river overflows banks. Army called in for rescue in 12 districts.", "tone": "negative"},
    {"id": "news_003", "title": "Cyclone REMAL: IMD Issues Red Alert for Coastal West Bengal", "url": "https://gdeltproject.org", "source": "IMD", "date": (datetime.utcnow() - timedelta(hours=1)).isoformat(), "hazard_type": "cyclone", "sentiment": -0.65, "summary": "Category 2 cyclone expected to make landfall near Sagar Island.", "tone": "negative"},
    {"id": "news_004", "title": "Rajasthan Drought: 8 Districts Get Relief Funds", "url": "https://gdeltproject.org", "source": "Hindustan Times", "date": (datetime.utcnow() - timedelta(hours=8)).isoformat(), "hazard_type": "drought", "sentiment": 0.15, "summary": "State government announces ₹850 crore package for drought-affected farmers.", "tone": "neutral"},
    {"id": "news_005", "title": "Himachal Pradesh Landslide: NH-5 Blocked Near Kinnaur", "url": "https://gdeltproject.org", "source": "The Hindu", "date": (datetime.utcnow() - timedelta(hours=14)).isoformat(), "hazard_type": "landslide", "sentiment": -0.55, "summary": "Major landslide triggered by heavy rainfall blocks national highway. 2000+ stranded.", "tone": "negative"},
    {"id": "news_006", "title": "India Heatwave: Temperatures Breach 46°C in 5 States", "url": "https://gdeltproject.org", "source": "India Today", "date": (datetime.utcnow() - timedelta(hours=3)).isoformat(), "hazard_type": "heatwave", "sentiment": -0.78, "summary": "Extreme heat affecting UP, Bihar, MP, Rajasthan and Odisha.", "tone": "negative"},
    {"id": "news_007", "title": "M5.8 Gujarat Earthquake Felt Across Three States", "url": "https://gdeltproject.org", "source": "Economic Times", "date": (datetime.utcnow() - timedelta(hours=6)).isoformat(), "hazard_type": "earthquake", "sentiment": -0.43, "summary": "Earthquake struck at 08:42 IST near Bhuj. No structural damage reported.", "tone": "negative"},
    {"id": "news_008", "title": "Forest Cover Report: 1.5% Loss in Past Year", "url": "https://gdeltproject.org", "source": "Down to Earth", "date": (datetime.utcnow() - timedelta(hours=20)).isoformat(), "hazard_type": "wildfire", "sentiment": -0.62, "summary": "FSI satellite analysis shows significant forest degradation in NE India.", "tone": "negative"},
    {"id": "news_009", "title": "NDRF Deploys 20 Teams Ahead of Cyclone Season", "url": "https://gdeltproject.org", "source": "PTI", "date": (datetime.utcnow() - timedelta(hours=10)).isoformat(), "hazard_type": "cyclone", "sentiment": 0.40, "summary": "National Disaster Response Force pre-positions teams across coastal states.", "tone": "positive"},
    {"id": "news_010", "title": "Uttarakhand Landslide Warning: Yellow Alert Issued", "url": "https://gdeltproject.org", "source": "ANI", "date": (datetime.utcnow() - timedelta(hours=16)).isoformat(), "hazard_type": "landslide", "sentiment": -0.38, "summary": "Continuous rainfall saturates soil in Chamoli. Residents advised to evacuate.", "tone": "negative"},
]


async def get_news(hazard_type: str = None, query: str = None, limit: int = 20) -> List[Dict]:
    """Fetch disaster news from GDELT. Falls back to demo data."""
    try:
        search_query = query or HAZARD_QUERIES.get(hazard_type, "disaster India natural hazard")
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                GDELT_DOC_API,
                params={"query": search_query, "mode": "artlist", "maxrecords": limit, "format": "json", "timespan": "7d", "sort": "DateDesc"}
            )
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get("articles", [])
                if articles:
                    return _parse_gdelt_articles(articles, hazard_type)
    except Exception as e:
        print(f"[GDELT] API failed: {e}. Using demo data.")

    if hazard_type:
        return [n for n in DEMO_NEWS if n["hazard_type"] == hazard_type][:limit]
    return DEMO_NEWS[:limit]


def _parse_gdelt_articles(articles: list, hazard_type: str = None) -> List[Dict]:
    results = []
    for i, art in enumerate(articles):
        try:
            tone = float(art.get("tone", 0) or 0)
            results.append({
                "id": f"gdelt_{i}",
                "title": art.get("title", "Unknown"),
                "url": art.get("url", ""),
                "source": art.get("domain", "Unknown"),
                "date": art.get("seendate", datetime.utcnow().isoformat()),
                "hazard_type": hazard_type or "general",
                "sentiment": round(tone / 10, 2),
                "summary": art.get("title", ""),
                "tone": "positive" if tone > 1 else "negative" if tone < -1 else "neutral"
            })
        except Exception:
            continue
    return results
