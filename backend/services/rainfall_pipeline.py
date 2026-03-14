import numpy as np
import scipy.spatial
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import math
import time
import traceback

# ตั้งค่า Open-Meteo API Client พร้อม Cache และ Retry
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.5)
openmeteo = openmeteo_requests.Client(session=retry_session)

def generate_control_grid(min_lon=100.2, min_lat=17.9, max_lon=101.6, max_lat=19.8, grid_km=5.0):
    """
    สร้างจุด Control Points ห่างกัน 5 กม. (สี่เหลี่ยมจัตุรัส) ให้ครอบคลุมจังหวัดน่าน
    คำนวณ step แยก lon/lat ตามระยะทางจริงที่ latitude กลาง
    """
    center_lat = (min_lat + max_lat) / 2  # ~18.85°
    step_lon = grid_km / (111.32 * math.cos(math.radians(center_lat)))  # ~0.04744°
    step_lat = grid_km / 110.54  # ~0.04523°
    
    lons = np.arange(min_lon, max_lon, step_lon)
    lats = np.arange(min_lat, max_lat, step_lat)
    
    control_points = []
    for lat in lats:
        for lon in lons:
            control_points.append({'latitude': lat, 'longitude': lon})
            
    return control_points

def fetch_openmeteo_batch(control_points):
    """
    ยิง Open-Meteo API ทีละ 100 จุด (ตาม Rate Limit ที่ปลอดภัย)
    ดึงข้อมูล daily precipitation ย้อนหลัง 9 วัน + วันนี้ (รวม 10 วัน)
    ถ้าโดน Rate Limit จะรอ 65 วินาทีแล้ว Retry (สูงสุด 3 ครั้งต่อ chunk)
    """
    url = "https://api.open-meteo.com/v1/forecast"
    
    chunk_size = 100
    max_retries = 3
    rate_limit_wait = 65  # วินาที - รอให้ rate limit หมดอายุ (1 นาที + buffer)
    inter_chunk_delay = 8  # วินาที - delay ระหว่าง chunk ป้องกัน rate limit
    all_rainfall = []
    
    total_chunks = math.ceil(len(control_points) / chunk_size)
    print(f"[Rainfall Pipeline] Fetching {len(control_points)} control points in {total_chunks} chunks of {chunk_size}...")
    
    for i in range(0, len(control_points), chunk_size):
        chunk = control_points[i:i+chunk_size]
        chunk_num = i // chunk_size + 1
        lats = [c['latitude'] for c in chunk]
        lons = [c['longitude'] for c in chunk]
        
        params = {
            "latitude": lats,
            "longitude": lons,
            "daily": "precipitation_sum",
            "past_days": 10,
            "forecast_days": 1,
            "timezone": "Asia/Bangkok"
        }
        
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                responses = openmeteo.weather_api(url, params=params)
                
                for response in responses:
                    daily = response.Daily()
                    daily_precipitation = daily.Variables(0).ValuesAsNumpy()
                    daily_precipitation = np.nan_to_num(daily_precipitation, nan=0.0)
                    daily_precip_reversed = np.flip(daily_precipitation)
                    
                    if len(daily_precip_reversed) < 10:
                        pad_width = 10 - len(daily_precip_reversed)
                        daily_precip_reversed = np.pad(daily_precip_reversed, (0, pad_width), 'constant')
                        
                    all_rainfall.append(daily_precip_reversed[:10])
                    
                print(f"  -> Fetched chunk {chunk_num}/{total_chunks}, got {len(chunk)} locations.")
                success = True
                break  # ออก retry loop ถ้าสำเร็จ
                
            except Exception as e:
                if "Please try again in one minute" in str(e):
                    if attempt < max_retries:
                        print(f"[Rate Limit] Chunk {chunk_num} attempt {attempt}/{max_retries} - waiting {rate_limit_wait}s before retry...")
                        time.sleep(rate_limit_wait)
                    else:
                        print(f"[Error] Chunk {chunk_num} failed after {max_retries} retries (Rate Limit). Using zeros.")
                else:
                    print(f"[Error] Chunk {chunk_num} attempt {attempt}: {e}")
                    traceback.print_exc()
                    if attempt < max_retries:
                        print(f"  Waiting {rate_limit_wait}s before retry...")
                        time.sleep(rate_limit_wait)
                    else:
                        print(f"[Error] Chunk {chunk_num} failed after {max_retries} retries. Using zeros.")
        
        # ถ้าลอง retry หมดแล้วยังไม่สำเร็จ ใส่ 0 แทน
        if not success:
            for _ in range(len(chunk)):
                all_rainfall.append(np.zeros(10))
        
        # delay ระหว่าง chunk (ยกเว้น chunk สุดท้าย)
        if i + chunk_size < len(control_points):
            time.sleep(inter_chunk_delay)

    # แปลงเป็น Numpy Array รูปแบบ (Num_Control_Points, 10)
    return np.array(all_rainfall)

def apply_spatial_interpolation(base_grid_data):
    """
    1. สร้าง Control Points 450 จุด
    2. ยิง Open-Meteo (ได้ 450x10 array)
    3. interpolate ข้อมูลทับลงใน base_grid_data 117,000 จุดด้วย cKDTree อย่างรวดเร็ว
    """
    # 1. & 2.ดึงฝน 450 จุด
    control_points = generate_control_grid()
    rainfall_matrix = fetch_openmeteo_batch(control_points) # Shape: (450, 10)
    
    # ดึงพิกัด (X, Y) ออกมาเตรียมคำนวณระยะทาง
    ctrl_coords = np.array([[cp['longitude'], cp['latitude']] for cp in control_points])
    
    # สร้าง KDTree ของพิกัด 450 จุด
    print(f"[Rainfall Pipeline] Building KDTree for {len(ctrl_coords)} control points...")
    tree = scipy.spatial.cKDTree(ctrl_coords)
    
    # 3. เตรียมพิกัดของ 117k points จาก properties เพื่อ Interpolate
    print(f"[Rainfall Pipeline] Interpolating rainfall mapping for {len(base_grid_data)} target cells...")
    
    # หาพิกัด (Center Lon, Center Lat) ของ base grid cells (ใช้ polygon[0] เป็นตัวแทนเพื่อความเร็ว)
    # สมมติ polygon เป็น list of [lon, lat]
    target_coords = np.array([
        [cell['polygon'][0][0], cell['polygon'][0][1]] if 'polygon' in cell and len(cell['polygon']) > 0 else [0, 0]
        for cell in base_grid_data
    ])
    
    # ค้นหา Nearest Neighbor: หา Index ของจุด Control Point ที่ใกล้ที่สุดสำหรับแต่ละพิกัด 117k
    # nearest_indices จะเป็น Array ขนาด 117000 ที่บอกว่าพิกัดที่ใกล้ที่สุดคือ Control Point เบอร์ใด
    _, nearest_indices = tree.query(target_coords, k=1)
    
    # 4. โคลนข้อมูลฝนลง Base Grid
    mapped_rainfall = rainfall_matrix[nearest_indices] # Vectorized Broadcast -> (117000, 10)
    
    # อัปเดต Dict Properties อย่างรวดเร็ว
    for i, cell in enumerate(base_grid_data):
        props = cell.setdefault('properties', {})
        rain_array = mapped_rainfall[i]
        
        # ฝัง CHIRPS_Day_1 จนถึง CHIRPS_Day_10 เข้า properties
        for day in range(1, 11):
            props[f'CHIRPS_Day_{day}'] = float(rain_array[day-1])
            
    print("[Rainfall Pipeline] Successfully updated JSON with daily spatial rainfall (10 days).")
    return base_grid_data
