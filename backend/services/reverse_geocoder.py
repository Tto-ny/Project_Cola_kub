"""
Reverse geocoder service using Nominatim (OpenStreetMap).
Converts lat/lon to actual Thai admin names (tambon, amphoe, changwat).
Results are cached to avoid repeated API calls.
"""
import requests
import time
import json
import os
import threading

# In-memory cache + file-based persistence
_cache = {}
_cache_lock = threading.Lock()
_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "geocode_cache.json")

def _load_cache():
    global _cache
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                _cache = json.load(f)
            print(f"[GEO] Loaded {len(_cache)} cached locations")
    except Exception as e:
        print(f"[GEO] Cache load error: {e}")
        _cache = {}

def _save_cache():
    try:
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_cache, f, ensure_ascii=False, indent=None)
    except Exception as e:
        print(f"[GEO] Cache save error: {e}")

# Load cache on import
_load_cache()


def _nominatim_reverse(lat, lon):
    """Call Nominatim reverse geocoding API."""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "accept-language": "th",
            "zoom": 14,  # village/suburb level
            "addressdetails": 1
        }
        headers = {
            "User-Agent": "LandslideWarningSystem/1.0 (student-project)"
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            # Thai administrative hierarchy in Nominatim:
            # suburb/village = tambon, county/city_district = amphoe, state/province = changwat
            tambon = (addr.get("suburb") or addr.get("village") or 
                      addr.get("town") or addr.get("hamlet") or 
                      addr.get("neighbourhood") or "")
            amphoe = (addr.get("county") or addr.get("city_district") or 
                      addr.get("city") or addr.get("municipality") or "")
            changwat = (addr.get("state") or addr.get("province") or "")
            country = addr.get("country", "")
            
            # Clean up: remove prefixes like "อำเภอ", "ตำบล", "จังหวัด"
            for prefix in ["ตำบล", "แขวง"]:
                if tambon.startswith(prefix):
                    tambon = tambon[len(prefix):]
            for prefix in ["อำเภอ", "เขต"]:
                if amphoe.startswith(prefix):
                    amphoe = amphoe[len(prefix):]
            for prefix in ["จังหวัด"]:
                if changwat.startswith(prefix):
                    changwat = changwat[len(prefix):]
            
            return {
                "tambon": tambon.strip(),
                "amphoe": amphoe.strip(),
                "changwat": changwat.strip(),
                "country": country.strip()
            }
    except Exception as e:
        print(f"[GEO] Nominatim error for ({lat},{lon}): {e}")
    
    return {"tambon": "", "amphoe": "", "changwat": "", "country": ""}


def reverse_geocode(lat, lon):
    """
    Get location name for a coordinate. Uses cache first, then Nominatim.
    Returns: {"tambon": "...", "amphoe": "...", "changwat": "...", "country": "..."}
    """
    # Round to 3 decimal places (~100m precision) for caching
    key = f"{round(lat, 3)},{round(lon, 3)}"
    
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    
    # Query Nominatim
    result = _nominatim_reverse(lat, lon)
    
    with _cache_lock:
        _cache[key] = result
        # Save cache periodically (every 10 new entries)
        if len(_cache) % 10 == 0:
            _save_cache()
    
    return result


def reverse_geocode_batch(coordinates, max_count=100):
    """
    Batch reverse geocode. Respects Nominatim rate limit (1 req/sec).
    coordinates: list of {"lat": float, "lon": float}
    Returns: list of {"lat", "lon", "tambon", "amphoe", "changwat", "country"}
    """
    results = []
    new_queries = 0
    
    for coord in coordinates[:max_count]:
        lat = coord.get("lat", 0)
        lon = coord.get("lon", 0)
        if not lat or not lon:
            results.append({"lat": lat, "lon": lon, "tambon": "", "amphoe": "", "changwat": "", "country": ""})
            continue
        
        key = f"{round(lat, 3)},{round(lon, 3)}"
        
        # Check cache first (no delay needed)
        with _cache_lock:
            if key in _cache:
                results.append({"lat": lat, "lon": lon, **_cache[key]})
                continue
        
        # Need to query Nominatim - rate limit
        if new_queries > 0:
            time.sleep(1.1)  # Nominatim: max 1 req/sec
        
        result = _nominatim_reverse(lat, lon)
        
        with _cache_lock:
            _cache[key] = result
        
        results.append({"lat": lat, "lon": lon, **result})
        new_queries += 1
    
    # Save cache after batch
    if new_queries > 0:
        _save_cache()
        print(f"[GEO] Batch done: {new_queries} new queries, {len(_cache)} total cached")
    
    return results
