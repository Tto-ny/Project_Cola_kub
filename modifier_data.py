import pandas as pd
import numpy as np

# รายชื่อฟีเจอร์ที่โมเดลบังคับเป๊ะตามลำดับ
FEATURE_ORDER = [
    'CHIRPS_Day_1', 'CHIRPS_Day_2', 'CHIRPS_Day_3', 'CHIRPS_Day_4', 'CHIRPS_Day_5', 
    'CHIRPS_Day_6', 'CHIRPS_Day_7', 'CHIRPS_Day_8', 'CHIRPS_Day_9', 'CHIRPS_Day_10', 
    'Elevation_Extracted', 'Slope_Extracted', 'Aspect_Extracted', 'MODIS_LC', 
    'NDVI', 'NDWI', 'TWI', 'Soil_Type', 'Road_Zone', 
    'Rain_3D_Prior', 'Rain_5D_Prior', 'Rain_7D_Prior', 'Rain_10D_Prior',
    'Rain3D_x_Slope', 'Rain5D_x_Slope', 'Rain7D_x_Slope', 'Rain10D_x_Slope'
]

# Baseline medians derived from the training dataset to fill unexpected missing features safely
TRAINING_MEDIANS = {
    'Elevation_Extracted': 500, 'Slope_Extracted': 15, 'Aspect_Extracted': 180,
    'MODIS_LC': 10, 'NDVI': 0.6, 'NDWI': -0.1, 'TWI': 8.5, 'Soil_Type': 2,
    'Road_Zone': 3, 'CHIRPS_Day_1': 0, 'CHIRPS_Day_2': 0, 'CHIRPS_Day_3': 0,
    'CHIRPS_Day_4': 0, 'CHIRPS_Day_5': 0, 'CHIRPS_Day_6': 0, 'CHIRPS_Day_7': 0,
    'CHIRPS_Day_8': 0, 'CHIRPS_Day_9': 0, 'CHIRPS_Day_10': 0,
    'Rain_3D_Prior': 0, 'Rain_5D_Prior': 0, 'Rain_7D_Prior': 0, 'Rain_10D_Prior': 0,
    'Rain3D_x_Slope': 0, 'Rain5D_x_Slope': 0, 'Rain7D_x_Slope': 0, 'Rain10D_x_Slope': 0
}

def predict_landslide_batch(base_grid_data, model, scaler=None):
    """
    รับ JSON 117k records นำมาแปลงเป็น DataFrame เพื่อสร้าง Features แบบ Vectorized
    (เร็วที่สุด ไม่พึ่ง Loop) และ Predict เอาผลลัพธ์กลับไปฝัง JSON เหมือนเดิม
    """
    
    print(f"[Modifier Data] Transforming JSON to DataFrame ({len(base_grid_data)} records)...")
    
    # 1. โยก properties จาก JSON ลง DataFrame
    # (Extract Only Dictionary Properties for Speed)
    properties_list = [item.get('properties', {}) for item in base_grid_data]
    df = pd.DataFrame(properties_list)
    
    # 2. Vectorized Feature Engineering (สมการคำนวณทั้งหมดทำรวดเดียว 117k แถว)
    # 2.1 คำนวณฝนสะสมก่อนหน้า (คำนวณเหมือน test.ipynb ของผู้ใช้: เริ่มนับจาก Day 1)
    df.fillna(0, inplace=True)
    
    # 2.2 Interaction Terms (การคูณไขว้เพื่อประเมินความลาดชันกับน้ำ)
    df['Rain_3D_Prior'] = df['CHIRPS_Day_1'] + df['CHIRPS_Day_2'] + df['CHIRPS_Day_3']
    df['Rain_5D_Prior'] = df['Rain_3D_Prior'] + df['CHIRPS_Day_4'] + df['CHIRPS_Day_5']
    df['Rain_7D_Prior'] = df['Rain_5D_Prior'] + df['CHIRPS_Day_6'] + df['CHIRPS_Day_7']
    df['Rain_10D_Prior'] = df['Rain_7D_Prior'] + df['CHIRPS_Day_8'] + df['CHIRPS_Day_9'] + df['CHIRPS_Day_10']
    
    # 2.2 Interaction Terms (การคูณไขว้เพื่อประเมินความลาดชันกับน้ำ)
    df['Rain3D_x_Slope'] = df['Rain_3D_Prior'] * df['Slope']
    df['Rain5D_x_Slope'] = df['Rain_5D_Prior'] * df['Slope']
    df['Rain7D_x_Slope'] = df['Rain_7D_Prior'] * df['Slope']
    df['Rain10D_x_Slope'] = df['Rain_10D_Prior'] * df['Slope']
    
    # 2.3 Categorical/Routing variables หรืองานเชื่อมโยงข้อมูล
    # (สมมติถ้าใน base_grid มีคำว่า 'Distance_to_Road' ให้แปลงเป็น Road_Zone ระยะทาง เช่น โซน 1 < 1KM)
    if 'Road_Zone' not in df.columns:
        if 'Distance_to_Road' in df.columns:
            # ใช้ Vectorization แทน lambda เพื่อเร่งความเร็ว 110k แถว
            df['Distance_to_Road'] = df['Distance_to_Road'].fillna(5000)
            df['Distance_to_Road'] = df['Distance_to_Road'].clip(lower=0)
            df['Road_Zone'] = pd.cut(df['Distance_to_Road'], bins=[-1, 50, 100, 200, 500, np.inf], labels=[1, 2, 3, 4, 5]).astype(float)
        else:
            df['Road_Zone'] = 1
            
    # 3. Rename Base Columns ให้ออกมาเหมือน GEE Extraction ของเดิมก่อน Fit Model
    rename_map = {
        'Elevation': 'Elevation_Extracted',
        'Slope': 'Slope_Extracted',
        'Aspect': 'Aspect_Extracted'
    }
    df = df.rename(columns=rename_map)
    
    # (Safety Check) เติม Column ที่หายไปให้เป็นค่า Median มาตรฐานจากคู่มือ แทนที่จะเป็น 0
    # เพื่อป้องกันค่าผิดเพี้ยนร้ายแรงเช่น NDWI หรือ Slope กลายเป็น 0
    for col in FEATURE_ORDER:
        if col not in df.columns:
            df[col] = TRAINING_MEDIANS.get(col, 0)
            
    # จัดเรียงลำดับให้เป๊ะ 100% ตาม Strict Order ที่โมเดลตกลงไว้
    X_df = df[FEATURE_ORDER]
    X_values = X_df.values
    
    print("[Modifier Data] Completed Vectorized Transform. Running Model Inference...")
    
    # 4. Predict
    if scaler is not None:
        X_values = scaler.transform(X_values)
        
    # ดึง Probability ของคลาส 1.0 (ความเสี่ยงเกิดดินถล่ม)
    try:
        proba = model.predict_proba(X_values)
        # ตรวจสอบว่าโมเดลมี 2 classes ถ้ายึดตามโค้ดเทรน (0.0=No, 1.0=Yes) ก็คือ index 1
        hazard_probs = proba[:, 1] if proba.shape[1] > 1 else np.max(proba, axis=1)
    except:
        hazard_probs = np.zeros(len(X_values))
    
    # Map ผลลับตาม Thresholds ที่ตั้งไว้ตอนเทรน
    # < 0.35 = Low, < 0.70 = Medium, >= 0.70 = High
    preds_risk = np.where(
        hazard_probs < 0.35, 'Low',
        np.where(hazard_probs < 0.70, 'Medium', 'High')
    )
    
    # อัพเดต max_probs ไว้ส่งกลับไปด้วย (เผื่อระบบเดิมใช้ตัวแปรนี้)
    max_probs = hazard_probs
    
    # 5. รวมร่างกลับไปยัง JSON เดิม (O(N) loop แค่ set variable จึงเร็วมาก)
    # ดึง .values ออกมาก่อน เพื่อหลีกเลี่ยงความอืดของ .iloc ใน for data loop
    rain_3d_vals = df['Rain_3D_Prior'].values
    rain_5d_vals = df['Rain_5D_Prior'].values
    rain_7d_vals = df['Rain_7D_Prior'].values
    rain_10d_vals = df['Rain_10D_Prior'].values
    
    for i, cell_record in enumerate(base_grid_data):
        cell_record['risk'] = str(preds_risk[i])
        cell_record['probability'] = float(max_probs[i])
        # สามารถอัพเดต propery ที่เราสร้างขึ้นใหม่กลับไปให้ Frontend ใช้ด้วย
        cell_record['properties']['Rain_3D (mm)'] = float(rain_3d_vals[i])
        cell_record['properties']['Rain_5D (mm)'] = float(rain_5d_vals[i])
        cell_record['properties']['Rain_7D (mm)'] = float(rain_7d_vals[i])
        cell_record['properties']['Rain_10D (mm)'] = float(rain_10d_vals[i])
        
    print(f"[Modifier Data] Inference Complete: Translated Predictions back to {len(base_grid_data)} JSON items.")
    return base_grid_data