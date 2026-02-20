"""
Fetch rainfall data from Open-Meteo API for Nan Province.
"""
import urllib.request
import json
from datetime import datetime, timedelta

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_rainfall(lat: float = 18.8, lon: float = 100.78, hours: int = 24) -> dict:
    """
    Fetch recent rainfall for a coordinate from Open-Meteo.
    Returns: { total_mm, hourly_data, timestamp }
    """
    params = (
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=precipitation"
        f"&past_hours={hours}"
        f"&forecast_days=1"
        f"&timezone=Asia%2FBangkok"
    )
    
    url = OPEN_METEO_URL + params
    print(f"Fetching rainfall from Open-Meteo: lat={lat}, lon={lon}")
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        hourly = data.get('hourly', {})
        precip = hourly.get('precipitation', [])
        times = hourly.get('time', [])
        
        total_mm = sum(p for p in precip if p is not None)
        max_mm = max(precip) if precip else 0
        
        print(f"  Total precipitation (last {hours}h): {total_mm:.1f} mm")
        print(f"  Max hourly: {max_mm:.1f} mm")
        
        return {
            "total_mm": round(total_mm, 2),
            "max_hourly_mm": round(max_mm, 2),
            "hours": hours,
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.now().isoformat(),
            "hourly_data": [
                {"time": t, "precipitation": p}
                for t, p in zip(times[-hours:], precip[-hours:])
            ]
        }
    except Exception as e:
        print(f"  Error fetching rainfall: {e}")
        return {
            "total_mm": 0,
            "max_hourly_mm": 0,
            "hours": hours,
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "hourly_data": []
        }

def fetch_rainfall_for_point(lat: float, lon: float) -> float:
    """Quick fetch: return total rainfall in mm for the last 24h."""
    result = fetch_rainfall(lat=lat, lon=lon, hours=24)
    return result.get("total_mm", 0)
