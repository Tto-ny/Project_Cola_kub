"""
Spatial search service for Nan Province districts (Amphoe) and sub-districts (Tambon).
Uses a local GeoJSON instead of PostGIS for Phase 2 MVP.
"""
import math

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

# Tambon (sub-district) data for each Amphoe with approximate centers
NAN_TAMBONS = [
    # เมืองน่าน
    {"name_th": "ในเวียง", "name_en": "Nai Wiang", "amphoe": "Mueang Nan", "center": [100.773, 18.783]},
    {"name_th": "บ่อ", "name_en": "Bo", "amphoe": "Mueang Nan", "center": [100.75, 18.76]},
    {"name_th": "ผาสิงห์", "name_en": "Pha Sing", "amphoe": "Mueang Nan", "center": [100.80, 18.80]},
    {"name_th": "ไชยสถาน", "name_en": "Chai Sathan", "amphoe": "Mueang Nan", "center": [100.78, 18.75]},
    {"name_th": "ถืมตอง", "name_en": "Thuem Tong", "amphoe": "Mueang Nan", "center": [100.76, 18.77]},
    {"name_th": "เรือง", "name_en": "Rueang", "amphoe": "Mueang Nan", "center": [100.72, 18.82]},
    {"name_th": "นาซาว", "name_en": "Na Sao", "amphoe": "Mueang Nan", "center": [100.70, 18.68]},
    {"name_th": "ดู่ใต้", "name_en": "Du Tai", "amphoe": "Mueang Nan", "center": [100.83, 18.73]},
    {"name_th": "กองควาย", "name_en": "Kong Khwai", "amphoe": "Mueang Nan", "center": [100.85, 18.81]},
    {"name_th": "สวก", "name_en": "Suak", "amphoe": "Mueang Nan", "center": [100.88, 18.87]},
    # แม่จริม
    {"name_th": "หนองแดง", "name_en": "Nong Daeng", "amphoe": "Mae Charim", "center": [100.83, 18.58]},
    {"name_th": "หมอเมือง", "name_en": "Mo Mueang", "amphoe": "Mae Charim", "center": [100.87, 18.53]},
    {"name_th": "น้ำพาง", "name_en": "Nam Phang", "amphoe": "Mae Charim", "center": [100.90, 18.48]},
    {"name_th": "แม่จริม", "name_en": "Mae Charim", "amphoe": "Mae Charim", "center": [100.85, 18.55]},
    # บ้านหลวง
    {"name_th": "บ้านฟ้า", "name_en": "Ban Fa", "amphoe": "Ban Luang", "center": [100.61, 18.92]},
    {"name_th": "ป่าคาหลวง", "name_en": "Pa Kha Luang", "amphoe": "Ban Luang", "center": [100.58, 18.88]},
    {"name_th": "สวด", "name_en": "Suat", "amphoe": "Ban Luang", "center": [100.63, 18.95]},
    {"name_th": "บ้านพี้", "name_en": "Ban Phi", "amphoe": "Ban Luang", "center": [100.56, 18.85]},
    # นาน้อย
    {"name_th": "นาน้อย", "name_en": "Na Noi", "amphoe": "Na Noi", "center": [100.72, 18.38]},
    {"name_th": "เชียงของ", "name_en": "Chiang Khong", "amphoe": "Na Noi", "center": [100.68, 18.30]},
    {"name_th": "ศรีษะเกษ", "name_en": "Si Sa Ket", "amphoe": "Na Noi", "center": [100.75, 18.42]},
    {"name_th": "สถาน", "name_en": "Sathan", "amphoe": "Na Noi", "center": [100.78, 18.35]},
    {"name_th": "สันทะ", "name_en": "San Tha", "amphoe": "Na Noi", "center": [100.65, 18.25]},
    {"name_th": "บัวใหญ่", "name_en": "Bua Yai", "amphoe": "Na Noi", "center": [100.75, 18.32]},
    {"name_th": "น้ำตก", "name_en": "Nam Tok", "amphoe": "Na Noi", "center": [100.80, 18.28]},
    # ปัว
    {"name_th": "ปัว", "name_en": "Pua", "amphoe": "Pua", "center": [101.08, 19.17]},
    {"name_th": "แงง", "name_en": "Ngaeng", "amphoe": "Pua", "center": [101.05, 19.20]},
    {"name_th": "สกาด", "name_en": "Sakad", "amphoe": "Pua", "center": [101.12, 19.22]},
    {"name_th": "ศิลาเพชร", "name_en": "Sila Phet", "amphoe": "Pua", "center": [101.00, 19.15]},
    {"name_th": "ศิลาแลง", "name_en": "Sila Laeng", "amphoe": "Pua", "center": [101.15, 19.25]},
    {"name_th": "อวน", "name_en": "Uan", "amphoe": "Pua", "center": [101.02, 19.10]},
    {"name_th": "ไชยวัฒนา", "name_en": "Chai Watthana", "amphoe": "Pua", "center": [101.10, 19.12]},
    {"name_th": "เจดีย์ชัย", "name_en": "Chedi Chai", "amphoe": "Pua", "center": [101.06, 19.05]},
    {"name_th": "ภูคา", "name_en": "Phu Kha", "amphoe": "Pua", "center": [101.18, 19.30]},
    {"name_th": "สวนขวัญ", "name_en": "Suan Khwan", "amphoe": "Pua", "center": [101.03, 19.18]},
    {"name_th": "วรนคร", "name_en": "Woranakhon", "amphoe": "Pua", "center": [101.07, 19.15]},
    # ท่าวังผา
    {"name_th": "ริม", "name_en": "Rim", "amphoe": "Tha Wang Pha", "center": [100.75, 19.12]},
    {"name_th": "ป่าคา", "name_en": "Pa Kha", "amphoe": "Tha Wang Pha", "center": [100.72, 19.08]},
    {"name_th": "ผาตอ", "name_en": "Pha To", "amphoe": "Tha Wang Pha", "center": [100.80, 19.18]},
    {"name_th": "ยม", "name_en": "Yom", "amphoe": "Tha Wang Pha", "center": [100.68, 19.05]},
    {"name_th": "ตาลี่", "name_en": "Ta Li", "amphoe": "Tha Wang Pha", "center": [100.78, 19.15]},
    {"name_th": "ศรีภูมิ", "name_en": "Si Phum", "amphoe": "Tha Wang Pha", "center": [100.70, 19.10]},
    {"name_th": "จอมพระ", "name_en": "Chom Phra", "amphoe": "Tha Wang Pha", "center": [100.73, 19.20]},
    {"name_th": "แสนทอง", "name_en": "Saen Thong", "amphoe": "Tha Wang Pha", "center": [100.82, 19.22]},
    # เวียงสา
    {"name_th": "กลางเวียง", "name_en": "Klang Wiang", "amphoe": "Wiang Sa", "center": [100.70, 18.55]},
    {"name_th": "ขึ่ง", "name_en": "Khueng", "amphoe": "Wiang Sa", "center": [100.65, 18.50]},
    {"name_th": "ไหล่น่าน", "name_en": "Lai Nan", "amphoe": "Wiang Sa", "center": [100.72, 18.62]},
    {"name_th": "ตาลชุม", "name_en": "Tan Chum", "amphoe": "Wiang Sa", "center": [100.60, 18.45]},
    {"name_th": "นาเหลือง", "name_en": "Na Lueang", "amphoe": "Wiang Sa", "center": [100.75, 18.58]},
    {"name_th": "ส้าน", "name_en": "San", "amphoe": "Wiang Sa", "center": [100.58, 18.40]},
    {"name_th": "น้ำมวบ", "name_en": "Nam Muap", "amphoe": "Wiang Sa", "center": [100.82, 18.65]},
    {"name_th": "น้ำปั้ว", "name_en": "Nam Pua", "amphoe": "Wiang Sa", "center": [100.78, 18.68]},
    {"name_th": "ยาบหัวนา", "name_en": "Yap Hua Na", "amphoe": "Wiang Sa", "center": [100.68, 18.52]},
    {"name_th": "ปงสนุก", "name_en": "Pong Sanuk", "amphoe": "Wiang Sa", "center": [100.73, 18.48]},
    # ทุ่งช้าง
    {"name_th": "ทุ่งช้าง", "name_en": "Thung Chang", "amphoe": "Thung Chang", "center": [101.05, 19.40]},
    {"name_th": "งอบ", "name_en": "Ngop", "amphoe": "Thung Chang", "center": [101.00, 19.38]},
    {"name_th": "และ", "name_en": "Lae", "amphoe": "Thung Chang", "center": [101.10, 19.45]},
    {"name_th": "ปอน", "name_en": "Pon", "amphoe": "Thung Chang", "center": [101.08, 19.35]},
    # เชียงกลาง
    {"name_th": "เชียงกลาง", "name_en": "Chiang Klang", "amphoe": "Chiang Klang", "center": [100.87, 19.28]},
    {"name_th": "เปือ", "name_en": "Puea", "amphoe": "Chiang Klang", "center": [100.82, 19.25]},
    {"name_th": "เชียงคาน", "name_en": "Chiang Khan", "amphoe": "Chiang Klang", "center": [100.90, 19.32]},
    {"name_th": "พระธาตุ", "name_en": "Phra That", "amphoe": "Chiang Klang", "center": [100.85, 19.30]},
    {"name_th": "พญาแก้ว", "name_en": "Phaya Kaeo", "amphoe": "Chiang Klang", "center": [100.93, 19.35]},
    # นาหมื่น
    {"name_th": "นาทะนุง", "name_en": "Na Thanung", "amphoe": "Na Muen", "center": [100.65, 18.22]},
    {"name_th": "บ่อแก้ว", "name_en": "Bo Kaeo", "amphoe": "Na Muen", "center": [100.60, 18.18]},
    {"name_th": "เมืองลี", "name_en": "Mueang Li", "amphoe": "Na Muen", "center": [100.70, 18.25]},
    {"name_th": "ปิงหลวง", "name_en": "Ping Luang", "amphoe": "Na Muen", "center": [100.63, 18.15]},
    # สันติสุข
    {"name_th": "ดู่พงษ์", "name_en": "Du Phong", "amphoe": "Santi Suk", "center": [100.85, 18.92]},
    {"name_th": "ป่าแลวหลวง", "name_en": "Pa Laeo Luang", "amphoe": "Santi Suk", "center": [100.88, 18.88]},
    {"name_th": "พงษ์", "name_en": "Phong", "amphoe": "Santi Suk", "center": [100.82, 18.95]},
    # บ่อเกลือ
    {"name_th": "บ่อเกลือเหนือ", "name_en": "Bo Kluea Nuea", "amphoe": "Bo Kluea", "center": [101.15, 19.30]},
    {"name_th": "บ่อเกลือใต้", "name_en": "Bo Kluea Tai", "amphoe": "Bo Kluea", "center": [101.12, 19.22]},
    {"name_th": "ภูฟ้า", "name_en": "Phu Fa", "amphoe": "Bo Kluea", "center": [101.20, 19.35]},
    {"name_th": "ดงพญา", "name_en": "Dong Phaya", "amphoe": "Bo Kluea", "center": [101.18, 19.18]},
    # สองแคว
    {"name_th": "นาไร่หลวง", "name_en": "Na Rai Luang", "amphoe": "Song Khwae", "center": [100.98, 19.38]},
    {"name_th": "ชนแดน", "name_en": "Chon Daen", "amphoe": "Song Khwae", "center": [100.95, 19.32]},
    {"name_th": "ยอด", "name_en": "Yot", "amphoe": "Song Khwae", "center": [101.02, 19.42]},
    # ภูเพียง
    {"name_th": "ม่วงตึ๊ด", "name_en": "Muang Tuet", "amphoe": "Phu Phiang", "center": [100.80, 18.72]},
    {"name_th": "นาปัง", "name_en": "Na Pang", "amphoe": "Phu Phiang", "center": [100.77, 18.68]},
    {"name_th": "น้ำแก่น", "name_en": "Nam Kaen", "amphoe": "Phu Phiang", "center": [100.83, 18.75]},
    {"name_th": "ท่าน้าว", "name_en": "Tha Nao", "amphoe": "Phu Phiang", "center": [100.85, 18.78]},
    {"name_th": "เมืองจัง", "name_en": "Mueang Chang", "amphoe": "Phu Phiang", "center": [100.75, 18.65]},
    {"name_th": "ฝายแก้ว", "name_en": "Fai Kaeo", "amphoe": "Phu Phiang", "center": [100.88, 18.82]},
    {"name_th": "สองแคว", "name_en": "Song Khwae", "amphoe": "Phu Phiang", "center": [100.78, 18.70]},
    # เฉลิมพระเกียรติ
    {"name_th": "ห้วยโก๋น", "name_en": "Huai Kon", "amphoe": "Chaloem Phra Kiat", "center": [101.15, 19.52]},
    {"name_th": "ขุนน่าน", "name_en": "Khun Nan", "amphoe": "Chaloem Phra Kiat", "center": [101.18, 19.48]},
]


def search_location(query: str):
    """Search for a district/sub-district by name (Thai or English)."""
    query_lower = query.lower().strip()
    results = []
    
    # 1. Search Districts (Amphoe)
    for d in NAN_DISTRICTS:
        if (query_lower in d["name_th"].lower() or 
            query_lower in d["name_en"].lower()):
            results.append(d)
            
    # 2. Search Sub-districts (Tambon)
    for t in NAN_TAMBONS:
        if (query_lower in t["name_th"].lower() or 
            query_lower in t["name_en"].lower()):
            results.append({
                "name_th": t["name_th"],
                "name_en": t["name_en"],
                "type": "tambon",
                "center": t["center"]
            })
            
    return results[:10]  # Return top 10 matches for UI dropdown

def get_all_districts():
    """Return all districts for dropdown/autocomplete."""
    return NAN_DISTRICTS

def reverse_geocode(lat, lon):
    """
    Find the nearest Amphoe and Tambon for a given lat/lon.
    Returns dict with amphoe and tambon names (Thai + English).
    """
    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return {"amphoe_th": "ไม่ทราบ", "amphoe_en": "Unknown", "tambon_th": "ไม่ทราบ", "tambon_en": "Unknown"}

    # 1. Find amphoe by bounding box first, then nearest center
    best_amphoe = None
    best_dist = float('inf')
    
    for d in NAN_DISTRICTS:
        bbox = d["bbox"]  # [min_lon, min_lat, max_lon, max_lat]
        # Check if point is inside bbox
        if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
            dist = (lon - d["center"][0]) ** 2 + (lat - d["center"][1]) ** 2
            if dist < best_dist:
                best_dist = dist
                best_amphoe = d
    
    # Fallback: nearest center if not inside any bbox
    if not best_amphoe:
        for d in NAN_DISTRICTS:
            dist = (lon - d["center"][0]) ** 2 + (lat - d["center"][1]) ** 2
            if dist < best_dist:
                best_dist = dist
                best_amphoe = d
    
    # 2. Find nearest tambon within the matched amphoe
    best_tambon = None
    best_tambon_dist = float('inf')
    
    if best_amphoe:
        for t in NAN_TAMBONS:
            if t["amphoe"] == best_amphoe["name_en"]:
                dist = (lon - t["center"][0]) ** 2 + (lat - t["center"][1]) ** 2
                if dist < best_tambon_dist:
                    best_tambon_dist = dist
                    best_tambon = t
    
    return {
        "amphoe_th": best_amphoe["name_th"] if best_amphoe else "ไม่ทราบ",
        "amphoe_en": best_amphoe["name_en"] if best_amphoe else "Unknown",
        "tambon_th": best_tambon["name_th"] if best_tambon else "ไม่ทราบ",
        "tambon_en": best_tambon["name_en"] if best_tambon else "Unknown",
    }

def reverse_geocode_batch(cells):
    """
    Batch reverse geocode for a list of cells.
    Each cell must have 'latitude' and 'longitude' keys.
    Returns a dict mapping (lat, lon) tuple to location info.
    """
    cache = {}
    for cell in cells:
        try:
            lat = float(cell.get('latitude') or cell.get('lat', 0))
            lon = float(cell.get('longitude') or cell.get('lon', 0))
        except (ValueError, TypeError):
            continue
            
        # Round to reduce cache misses for nearby cells (same ~500m grid)
        key = (round(lat, 3), round(lon, 3))
        if key not in cache:
            cache[key] = reverse_geocode(lat, lon)
    return cache

