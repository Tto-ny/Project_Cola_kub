"""
Spatial search service for Nan Province districts (Amphoe) and sub-districts (Tambon).
Uses a local GeoJSON instead of PostGIS for Phase 2 MVP.
"""

# Nan Province districts with approximate center coordinates and bbox
NAN_DISTRICTS = [
    {"name_th": "เมืองน่าน", "name_en": "Mueang Nan", "type": "amphoe",
     "center": [100.773, 18.783], "bbox": [100.65, 18.65, 100.90, 18.90]},
    {"name_th": "แม่จริม", "name_en": "Mae Charim", "type": "amphoe",
     "center": [100.85, 18.55], "bbox": [100.70, 18.40, 101.00, 18.70]},
    {"name_th": "บ้านหลวง", "name_en": "Ban Luang", "type": "amphoe",
     "center": [100.60, 18.90], "bbox": [100.50, 18.80, 100.75, 19.00]},
    {"name_th": "นาน้อย", "name_en": "Na Noi", "type": "amphoe",
     "center": [100.72, 18.35], "bbox": [100.55, 18.15, 100.90, 18.55]},
    {"name_th": "ปัว", "name_en": "Pua", "type": "amphoe",
     "center": [101.08, 19.17], "bbox": [100.90, 19.00, 101.25, 19.35]},
    {"name_th": "ท่าวังผา", "name_en": "Tha Wang Pha", "type": "amphoe",
     "center": [100.75, 19.13], "bbox": [100.55, 19.00, 100.95, 19.30]},
    {"name_th": "เวียงสา", "name_en": "Wiang Sa", "type": "amphoe",
     "center": [100.70, 18.55], "bbox": [100.45, 18.35, 100.95, 18.75]},
    {"name_th": "ทุ่งช้าง", "name_en": "Thung Chang", "type": "amphoe",
     "center": [101.05, 19.40], "bbox": [100.85, 19.25, 101.25, 19.55]},
    {"name_th": "เชียงกลาง", "name_en": "Chiang Klang", "type": "amphoe",
     "center": [100.87, 19.28], "bbox": [100.70, 19.15, 101.05, 19.40]},
    {"name_th": "นาหมื่น", "name_en": "Na Muen", "type": "amphoe",
     "center": [100.65, 18.20], "bbox": [100.50, 18.05, 100.80, 18.35]},
    {"name_th": "สันติสุข", "name_en": "Santi Suk", "type": "amphoe",
     "center": [100.85, 18.90], "bbox": [100.75, 18.80, 101.00, 19.00]},
    {"name_th": "บ่อเกลือ", "name_en": "Bo Kluea", "type": "amphoe",
     "center": [101.15, 19.25], "bbox": [101.00, 19.08, 101.35, 19.45]},
    {"name_th": "สองแคว", "name_en": "Song Khwae", "type": "amphoe",
     "center": [100.98, 19.35], "bbox": [100.85, 19.25, 101.10, 19.50]},
    {"name_th": "ภูเพียง", "name_en": "Phu Phiang", "type": "amphoe",
     "center": [100.80, 18.72], "bbox": [100.70, 18.60, 100.95, 18.85]},
    {"name_th": "เฉลิมพระเกียรติ", "name_en": "Chaloem Phra Kiat", "type": "amphoe",
     "center": [101.15, 19.50], "bbox": [101.00, 19.35, 101.35, 19.65]},
]

def search_location(query: str):
    """Search for a district/sub-district by name (Thai or English)."""
    query_lower = query.lower().strip()
    results = []
    for district in NAN_DISTRICTS:
        if (query_lower in district["name_th"].lower() or
            query_lower in district["name_en"].lower()):
            results.append(district)
    return results

def get_all_districts():
    """Return all districts for dropdown/autocomplete."""
    return NAN_DISTRICTS
