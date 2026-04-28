"""
GDACS — Global Disaster Alert and Coordination System
Fetches live disasters: earthquakes, cyclones, floods, volcanoes, droughts.
No API key required. Public RSS/JSON feed.

API: https://www.gdacs.org/xml/rss.xml
"""

import httpx
import json
from typing import List, Dict
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET


GDACS_RSS_URL = "https://www.gdacs.org/xml/rss.xml"
GDACS_GEOJSON_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

# Rich demo data covering multiple hazard types
DEMO_DISASTERS = [
    {
        "id": "gdacs_eq_1305094",
        "type": "earthquake",
        "title": "M 5.8 Earthquake - Gujarat, India",
        "description": "Moderate earthquake struck near Bhuj at 08:42 UTC. Depth: 12km. Felt in 3 districts.",
        "severity": "Orange",
        "lat": 23.21, "lon": 70.03,
        "date": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        "country": "India",
        "region": "Gujarat",
        "magnitude": 5.8,
        "deaths": 0,
        "affected": 15000,
        "url": "https://www.gdacs.org",
        "icon": "🏔️"
    },
    {
        "id": "gdacs_fl_1284731",
        "type": "flood",
        "title": "Major Flooding — Assam, India",
        "description": "Brahmaputra river overflow causing widespread flooding in 12 districts. Over 200,000 displaced.",
        "severity": "Red",
        "lat": 26.14, "lon": 91.74,
        "date": (datetime.utcnow() - timedelta(hours=18)).isoformat(),
        "country": "India",
        "region": "Assam",
        "magnitude": None,
        "deaths": 23,
        "affected": 210000,
        "url": "https://www.gdacs.org",
        "icon": "🌊"
    },
    {
        "id": "gdacs_cy_1299321",
        "type": "cyclone",
        "title": "Cyclone REMAL — Bay of Bengal",
        "description": "Category 2 cyclone tracking toward West Bengal coast. Wind speed: 110 km/h. Landfall expected in 36h.",
        "severity": "Red",
        "lat": 18.5, "lon": 88.3,
        "date": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
        "country": "India",
        "region": "West Bengal",
        "magnitude": None,
        "deaths": 0,
        "affected": 500000,
        "url": "https://www.gdacs.org",
        "icon": "🌀"
    },
    {
        "id": "gdacs_dr_1290012",
        "type": "drought",
        "title": "Severe Drought — Rajasthan",
        "description": "Rainfall 62% below normal this season. 8 districts declared drought-affected. Crop failure in 340,000 hectares.",
        "severity": "Orange",
        "lat": 27.02, "lon": 74.21,
        "date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "country": "India",
        "region": "Rajasthan",
        "magnitude": None,
        "deaths": 0,
        "affected": 1200000,
        "url": "https://www.gdacs.org",
        "icon": "☀️"
    },
    {
        "id": "gdacs_vo_1287654",
        "type": "volcano",
        "title": "Volcanic Activity — Barren Island",
        "description": "India's only active volcano showing increased lava flow. Aviation warning issued. No civilians at risk.",
        "severity": "Green",
        "lat": 12.28, "lon": 93.86,
        "date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "country": "India",
        "region": "Andaman Islands",
        "magnitude": None,
        "deaths": 0,
        "affected": 0,
        "url": "https://www.gdacs.org",
        "icon": "🌋"
    },
    {
        "id": "gdacs_eq_1305098",
        "type": "earthquake",
        "title": "M 4.2 Earthquake — Uttarakhand",
        "description": "Light earthquake detected in Chamoli district. No damage reported. Tremors felt for ~15 seconds.",
        "severity": "Green",
        "lat": 30.41, "lon": 79.45,
        "date": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
        "country": "India",
        "region": "Uttarakhand",
        "magnitude": 4.2,
        "deaths": 0,
        "affected": 0,
        "url": "https://www.gdacs.org",
        "icon": "🏔️"
    },
    {
        "id": "gdacs_fl_1284800",
        "type": "flood",
        "title": "Flash Floods — Himachal Pradesh",
        "description": "Cloudbursts triggered flash floods in 4 valleys. Roads blocked, 12 villages isolated.",
        "severity": "Orange",
        "lat": 31.10, "lon": 77.17,
        "date": (datetime.utcnow() - timedelta(hours=30)).isoformat(),
        "country": "India",
        "region": "Himachal Pradesh",
        "magnitude": None,
        "deaths": 8,
        "affected": 45000,
        "url": "https://www.gdacs.org",
        "icon": "🌊"
    },
]


async def get_live_disasters(limit: int = 50) -> List[Dict]:
    """Fetch live disasters from GDACS and include demo data."""
    live_events = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                GDACS_GEOJSON_URL,
                params={"alertlevel": "Orange,Red,Green", "eventtype": "EQ,FL,CY,VO,DR,TS", "limit": limit},
                headers={"Accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            events = data.get("features", [])
            if events:
                live_events = _parse_gdacs_geojson(events)
    except Exception as e:
        print(f"[GDACS] API failed: {e}. Using demo data only.")

    # Always include demo data to ensure map is richly populated (as requested by user)
    # Combine live events with demo events
    return live_events + DEMO_DISASTERS


def _parse_gdacs_geojson(features: list) -> List[Dict]:
    """Parse GDACS GeoJSON features into our format."""
    results = []
    type_icons = {
        "EQ": "🏔️", "FL": "🌊", "CY": "🌀", "VO": "🌋",
        "DR": "☀️", "TS": "🌊", "WF": "🔥"
    }
    type_names = {
        "EQ": "earthquake", "FL": "flood", "CY": "cyclone", "VO": "volcano",
        "DR": "drought", "TS": "tsunami", "WF": "wildfire"
    }
    for f in features:
        try:
            props = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [0, 0])
            etype = props.get("eventtype", "EQ")
            results.append({
                "id": f"gdacs_{props.get('eventid', 'unknown')}",
                "type": type_names.get(etype, "unknown"),
                "title": props.get("htmldescription", props.get("name", "Unknown Event")),
                "description": props.get("description", ""),
                "severity": props.get("alertlevel", "Green"),
                "lat": coords[1] if len(coords) > 1 else 0,
                "lon": coords[0] if len(coords) > 0 else 0,
                "date": props.get("fromdate", datetime.utcnow().isoformat()),
                "country": props.get("country", "Unknown"),
                "region": props.get("name", "Unknown"),
                "magnitude": props.get("severitydata", {}).get("severity"),
                "deaths": int(props.get("severitydata", {}).get("severityvalue", 0) or 0),
                "affected": 0,
                "url": props.get("url", {}).get("report", "https://www.gdacs.org"),
                "icon": type_icons.get(etype, "⚠️")
            })
        except Exception:
            continue
    return results


def get_disaster_history(days: int = 30) -> List[Dict]:
    """Return historical disasters (demo) for the past N days."""
    history = []
    # Generate synthetic historical events to simulate a real catalog
    types = [
        ("earthquake", "🏔️", [
            ("M 6.1 Earthquake — Manipur", 24.8, 93.9, "Red", 120000),
            ("M 4.9 Earthquake — Maharashtra", 19.1, 74.2, "Green", 0),
            ("M 5.3 Earthquake — Andaman Sea", 11.5, 92.4, "Orange", 5000),
        ]),
        ("flood", "🌊", [
            ("Major Flooding — Bihar", 25.6, 85.1, "Red", 380000),
            ("Flash Floods — Kerala", 10.8, 76.3, "Orange", 65000),
            ("Urban Flooding — Mumbai", 19.0, 72.8, "Orange", 200000),
        ]),
        ("cyclone", "🌀", [
            ("Cyclone BIPARJOY — Arabian Sea", 22.3, 68.1, "Red", 1100000),
        ]),
        ("drought", "☀️", [
            ("Drought Alert — Karnataka", 15.3, 75.7, "Orange", 850000),
            ("Drought — Vidarbha Region", 20.7, 77.7, "Red", 1500000),
        ]),
    ]

    day_offset = 0
    done = False
    for hazard_type, icon, events in types:
        if done:
            break
        for title, lat, lon, severity, affected in events:
            day_offset += 3
            if day_offset > days:
                done = True
                break
            history.append({
                "id": f"hist_{hazard_type}_{day_offset}",
                "type": hazard_type,
                "title": title,
                "description": f"Historical event recorded {day_offset} days ago.",
                "severity": severity,
                "lat": lat, "lon": lon,
                "date": (datetime.utcnow() - timedelta(days=day_offset)).isoformat(),
                "country": "India",
                "region": title.split("—")[-1].strip() if "—" in title else "India",
                "magnitude": None,
                "deaths": 0,
                "affected": affected,
                "url": "https://www.gdacs.org",
                "icon": icon
            })
    return sorted(history, key=lambda x: x["date"], reverse=True)
