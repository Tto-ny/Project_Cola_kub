"""
Google Earth Engine Data Extractor
ดึงข้อมูลจาก GEE สำหรับทำนายดินถล่ม
"""

import ee
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv

load_dotenv()

class GEEExtractor:
    def __init__(self):
        """Initialize Google Earth Engine"""
        try:
            project_id = os.getenv('GEE_PROJECT_ID', 'arched-wharf-485715-f9')
            ee.Initialize(project=project_id)
            print(f"✅ GEE Initialized successfully (Project: {project_id})")
        except Exception as e:
            print(f"❌ GEE Initialization failed: {e}")
            print("   Trying to authenticate...")
            try:
                ee.Authenticate()
                ee.Initialize(project=project_id)
                print("✅ GEE Authenticated and initialized")
            except Exception as auth_error:
                print(f"❌ Authentication failed: {auth_error}")
                raise
    
    def extract_terrain_nasadem(self, lon: float, lat: float) -> Dict:
        """
        ดึงข้อมูลภูมิประเทศจาก NASADEM
        Returns: Slope, Elevation, Aspect
        """
        try:
            point = ee.Geometry.Point([lon, lat])
            
            # NASADEM Digital Elevation Model (30m resolution)
            dem = ee.Image('NASA/NASADEM_HGT/001').select('elevation')
            
            # คำนวณ Slope และ Aspect
            terrain = ee.Terrain.products(dem)
            
            # Sample ค่าที่จุดนั้นๆ
            sample = terrain.sample(point, 30).first()
            
            elevation = sample.get('elevation').getInfo()
            slope = sample.get('slope').getInfo()
            aspect = sample.get('aspect').getInfo()
            
            return {
                'Elevation_Extracted': round(elevation, 2) if elevation else None,
                'Slope_Extracted': round(slope, 2) if slope else None,
                'Aspect_Extracted': round(aspect, 2) if aspect else None
            }
        except Exception as e:
            print(f"   ⚠️ Terrain extraction failed for ({lon}, {lat}): {e}")
            return {
                'Elevation_Extracted': None,
                'Slope_Extracted': None,
                'Aspect_Extracted': None
            }
    
    def extract_vegetation_indices(self, lon: float, lat: float, date: datetime = None) -> Dict:
        """
        ดึง NDVI และ NDWI จาก Sentinel-2
        ถ้าเจอเมฆมาก จะลองย้อนหาภาพที่ดีกว่า
        """
        if date is None:
            date = datetime.now()
        
        try:
            point = ee.Geometry.Point([lon, lat])
            
            # หาภาพ Sentinel-2 ในช่วง 90 วันย้อนหลัง (เพิ่มจาก 30 เป็น 90 วัน)
            end_date = date
            start_date = date - timedelta(days=90)
            
            s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(point) \
                .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50)) \
                .sort('CLOUDY_PIXEL_PERCENTAGE')
            
            # ตรวจสอบว่ามีภาพหรือไม่
            count = s2.size().getInfo()
            if count == 0:
                print(f"   ⚠️ No Sentinel-2 image found for ({lon}, {lat}) in 90 days")
                return {'NDVI': -9999, 'NDWI': -9999}
            
            # เอาภาพที่มีเมฆน้อยที่สุด
            image = s2.first()
            
            # คำนวณ NDVI = (NIR - Red) / (NIR + Red)
            nir = image.select('B8')
            red = image.select('B4')
            ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
            
            # คำนวณ NDWI = (Green - NIR) / (Green + NIR)
            green = image.select('B3')
            ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI')
            
            # Sample ค่า (ระบุ scale เพื่อให้มี CRS)
            combined = image.addBands([ndvi, ndwi])
            sample = combined.sample(
                region=point,
                scale=10,  # Sentinel-2 resolution
                geometries=True
            ).first()
            
            # ตรวจสอบว่า sample สำเร็จหรือไม่
            if sample is None:
                print(f"   ⚠️ Failed to sample Sentinel-2 for ({lon}, {lat})")
                return {'NDVI': -9999, 'NDWI': -9999}
            
            # ดึงค่า NDVI และ NDWI (ต้อง handle null ด้วย try-catch)
            try:
                ndvi_obj = sample.get('NDVI')
                ndvi_val = ndvi_obj.getInfo() if ndvi_obj is not None else None
            except:
                ndvi_val = None
            
            try:
                ndwi_obj = sample.get('NDWI')
                ndwi_val = ndwi_obj.getInfo() if ndwi_obj is not None else None
            except:
                ndwi_val = None
            
            return {
                'NDVI': round(ndvi_val, 4) if ndvi_val is not None else -9999,
                'NDWI': round(ndwi_val, 4) if ndwi_val is not None else -9999
            }
        except Exception as e:
            print(f"   ⚠️ Vegetation indices extraction failed for ({lon}, {lat}): {e}")
            return {'NDVI': -9999, 'NDWI': -9999}
    
    def extract_twi(self, lon: float, lat: float) -> float:
        """
        คำนวณ Topographic Wetness Index (TWI)
        TWI = ln(Flow Accumulation / tan(Slope))
        """
        try:
            point = ee.Geometry.Point([lon, lat])
            dem = ee.Image('NASA/NASADEM_HGT/001').select('elevation')
            
            # คำนวณ slope (in radians)
            slope = ee.Terrain.slope(dem).multiply(3.14159 / 180)
            
            # Flow accumulation (ใช้ approximation ด้วย catchment area)
            # สำหรับ production ควรใช้ algorithm ที่ซับซ้อนกว่านี้
            flow_acc = dem.focal_max(radius=100, units='meters')
            
            # TWI = ln(flow_acc / tan(slope))
            twi = flow_acc.divide(slope.tan()).log().rename('TWI')
            
            sample = twi.sample(point, 30).first()
            twi_val = sample.get('TWI').getInfo()
            
            return round(twi_val, 2) if twi_val is not None else 10.0  # default value
        except Exception as e:
            print(f"   ⚠️ TWI extraction failed for ({lon}, {lat}): {e}")
            return 10.0  # default value
    
    def extract_distance_to_road(self, lon: float, lat: float) -> float:
        """
        คำนวณระยะทางถึงถนนใกล้ที่สุด
        ใช้ OpenStreetMap road network
        """
        try:
            point = ee.Geometry.Point([lon, lat])
            
            # ใช้ Global Roads dataset
            # Note: อาจต้องใช้ dataset อื่นที่เหมาะสมกว่า
            # ตอนนี้ใช้ค่า default ก่อน
            
            # TODO: Implement actual road distance calculation
            # สำหรับตอนนี้ return ค่า default
            return 500.0  # meters (default)
        except Exception as e:
            print(f"   ⚠️ Distance to road extraction failed for ({lon}, {lat}): {e}")
            return 500.0
    
    def extract_rainfall_gpm(self, lon: float, lat: float, date: datetime = None) -> Dict:
        """
        ดึงข้อมูลฝนจาก GPM IMERG Early (real-time)
        Returns: ฝน 7 วันย้อนหลัง (Day_1 ถึง Day_7)
        หน่วย: mm/day
        """
        if date is None:
            date = datetime.now()
        
        try:
            point = ee.Geometry.Point([lon, lat])
            
            # GPM IMERG Early (30-minute, near real-time)
            # Dataset: 'NASA/GPM_L3/IMERG_V06'
            
            rainfall_data = {}
            
            for day in range(1, 8):  # Day 1 to Day 7
                try:
                    target_date = date - timedelta(days=day)
                    start = target_date.strftime('%Y-%m-%d')
                    end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    # ดึงข้อมูลฝนในวันนั้น
                    gpm = ee.ImageCollection('NASA/GPM_L3/IMERG_V06') \
                        .filterBounds(point) \
                        .filterDate(start, end) \
                        .select('precipitationCal')
                    
                    # ตรวจสอบว่ามีข้อมูลหรือไม่
                    count = gpm.size().getInfo()
                    if count == 0:
                        rainfall_data[f'CHIRPS_Day_{day}'] = 0.0
                        continue
                    
                    # Sum ฝนทั้งวัน (GPM ให้ค่าเป็น mm/hr)
                    daily_precip = gpm.sum()
                    
                    # Sample ค่า (ระบุ scale และ CRS)
                    sample = daily_precip.sample(
                        region=point,
                        scale=11132,  # GPM resolution ~11km
                        geometries=True
                    ).first()
                    
                    if sample is None:
                        rainfall_data[f'CHIRPS_Day_{day}'] = 0.0
                        continue
                    
                    precip_val = sample.get('precipitationCal').getInfo()
                    
                    # GPM ให้ค่าเป็น mm/hr (30-min data)
                    # Sum ของทั้งวัน (48 images) = total mm
                    if precip_val is not None:
                        rainfall_data[f'CHIRPS_Day_{day}'] = round(precip_val * 0.5, 2)  # convert to mm/day
                    else:
                        rainfall_data[f'CHIRPS_Day_{day}'] = 0.0
                        
                except Exception as day_error:
                    print(f"   ⚠️ Day {day} rainfall failed: {day_error}")
                    rainfall_data[f'CHIRPS_Day_{day}'] = 0.0
            
            return rainfall_data
        except Exception as e:
            print(f"   ⚠️ Rainfall extraction failed for ({lon}, {lat}): {e}")
            return {f'CHIRPS_Day_{i}': 0.0 for i in range(1, 8)}
    
    def extract_all_features(self, lon: float, lat: float, date: datetime = None) -> Dict:
        """
        ดึงข้อมูลทั้งหมดสำหรับจุดหนึ่งๆ
        """
        print(f"📍 Extracting features for ({lon:.4f}, {lat:.4f})...")
        
        features = {}
        
        # 1. Terrain (NASADEM)
        terrain = self.extract_terrain_nasadem(lon, lat)
        features.update(terrain)
        
        # 2. Vegetation indices (Sentinel-2) - monthly update
        veg = self.extract_vegetation_indices(lon, lat, date)
        features.update(veg)
        
        # 3. TWI - monthly update
        features['TWI'] = self.extract_twi(lon, lat)
        
        # 4. Distance to road - monthly update
        features['Distance_to_Road'] = self.extract_distance_to_road(lon, lat)
        
        # 5. Rainfall (GPM IMERG) - daily update
        rainfall = self.extract_rainfall_gpm(lon, lat, date)
        features.update(rainfall)
        
        # คำนวณ Rain_Ant_3D, 5D, 7D
        features['Rain_Ant_3D'] = sum([rainfall.get(f'CHIRPS_Day_{i}', 0) for i in range(1, 4)])
        features['Rain_Ant_5D'] = sum([rainfall.get(f'CHIRPS_Day_{i}', 0) for i in range(1, 6)])
        features['Rain_Ant_7D'] = sum([rainfall.get(f'CHIRPS_Day_{i}', 0) for i in range(1, 8)])
        
        print(f"   ✅ Extraction complete!")
        return features


# Test function
def test_extraction():
    """ทดสอบการดึงข้อมูล"""
    extractor = GEEExtractor()
    
    # ทดสอบกับจุดแรกในไฟล์
    test_lon = 100.50327844902031
    test_lat = 18.27965608528279
    
    features = extractor.extract_all_features(test_lon, test_lat)
    
    print("\n📊 Extracted Features:")
    for key, value in features.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    test_extraction()
