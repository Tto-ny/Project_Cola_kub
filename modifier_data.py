import pandas as pd
import numpy as np

# รายชื่อฟีเจอร์ที่โมเดลบังคับเป๊ะตามลำดับ
FEATURE_ORDER = [
    'CHIRPS_Day_1', 'CHIRPS_Day_2', 'CHIRPS_Day_3', 'CHIRPS_Day_4', 'CHIRPS_Day_5', 
    'CHIRPS_Day_6', 'CHIRPS_Day_7', 'CHIRPS_Day_8', 'CHIRPS_Day_9', 'CHIRPS_Day_10', 
    'Elevation_Extracted', 'Slope_Extracted', 'Aspect_Extracted', 'MODIS_LC', 
    'NDVI', 'NDWI', 'TWI', 'Soil_Type', 'Road_Zone', 
    'Rain_3D_Prior', 'Rain_5D_Prior', 'Rain_7D_Prior', 
    'Rain3D_x_Slope', 'Rain5D_x_Slope', 'Rain7D_x_Slope'
]

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
    # 2.1 คำนวณฝนสะสมก่อนหน้า 
    # (Day_1 คือวันนี้ -> ดังนั้น 3 วันก่อนหน้าคือ Day_2 + Day_3 + Day_4)
    # เติม 0 กัน Error สมมติบางช่วงไม่มีค่า
    df.fillna(0, inplace=True)
    
    df['Rain_3D_Prior'] = df['CHIRPS_Day_2'] + df['CHIRPS_Day_3'] + df['CHIRPS_Day_4']
    df['Rain_5D_Prior'] = df['Rain_3D_Prior'] + df['CHIRPS_Day_5'] + df['CHIRPS_Day_6']
    df['Rain_7D_Prior'] = df['Rain_5D_Prior'] + df['CHIRPS_Day_7'] + df['CHIRPS_Day_8']
    
    # 2.2 Interaction Terms (การคูณไขว้เพื่อประเมินความลาดชันกับน้ำ)
    df['Rain3D_x_Slope'] = df['Rain_3D_Prior'] * df['Slope']
    df['Rain5D_x_Slope'] = df['Rain_5D_Prior'] * df['Slope']
    df['Rain7D_x_Slope'] = df['Rain_7D_Prior'] * df['Slope']
    
    # 2.3 Categorical/Routing variables หรืองานเชื่อมโยงข้อมูล
    # (สมมติถ้าใน base_grid มีคำว่า 'Distance_to_Road' ให้แปลงเป็น Road_Zone ระยะทาง เช่น โซน 1 < 1KM)
    if 'Road_Zone' not in df.columns:
        if 'Distance_to_Road' in df.columns:
            # สมมติแบ่งเป็น 3 Categories ตามระยะเข้าถึง
            df['Road_Zone'] = pd.cut(df['Distance_to_Road'], bins=[-1, 500, 2000, np.inf], labels=[1, 2, 3]).astype(float)
        else:
            df['Road_Zone'] = 1  # ถ้าหาไม่เจอจริงๆ ให้ใส่เป็น 1
            
    # 3. Rename Base Columns ให้ออกมาเหมือน GEE Extraction ของเดิมก่อน Fit Model
    rename_map = {
        'Elevation': 'Elevation_Extracted',
        'Slope': 'Slope_Extracted',
        'Aspect': 'Aspect_Extracted'
    }
    df = df.rename(columns=rename_map)
    
    # (Safety Check) เติม Column ที่หายไปให้เป็น 0 มิฉะนั้น Model Predict จะระเบิด
    for col in FEATURE_ORDER:
        if col not in df.columns:
            df[col] = 0
            
    # จัดเรียงลำดับให้เป๊ะ 100% ตาม Strict Order ที่โมเดลตกลงไว้
    X_df = df[FEATURE_ORDER]
    X_values = X_df.values
    
    print("[Modifier Data] Completed Vectorized Transform. Running Model Inference...")
    
    # 4. Predict
    if scaler is not None:
        X_values = scaler.transform(X_values)
        
    # Array ขนาด (117000, 1) ตอบ High(2) Med(1) Low(0)
    preds_numeric = model.predict(X_values)
    
    # ลองสกัด probability สำหรับ Dashboard
    try:
        proba = model.predict_proba(X_values)
        max_probs = np.max(proba, axis=1)
    except:
        max_probs = np.zeros(len(preds_numeric))
    
    # Map ผลลับ
    risk_mapping = {0: 'Low', 1: 'Medium', 2: 'High'}
    vectorized_mapping = np.vectorize(risk_mapping.get)
    preds_risk = vectorized_mapping(preds_numeric, 'Low')
    
    # 5. รวมร่างกลับไปยัง JSON เดิม (O(N) loop แค่ set variable จึงเร็วมาก)
    # ดึง .values ออกมาก่อน เพื่อหลีกเลี่ยงความอืดของ .iloc ใน for data loop
    rain_3d_vals = df['Rain_3D_Prior'].values
    rain_5d_vals = df['Rain_5D_Prior'].values
    rain_7d_vals = df['Rain_7D_Prior'].values
    
    for i, cell_record in enumerate(base_grid_data):
        cell_record['risk'] = str(preds_risk[i])
        cell_record['probability'] = float(max_probs[i])
        # สามารถอัพเดต propery ที่เราสร้างขึ้นใหม่กลับไปให้ Frontend ใช้ด้วย
        cell_record['properties']['Rain_3D (mm)'] = float(rain_3d_vals[i])
        cell_record['properties']['Rain_5D (mm)'] = float(rain_5d_vals[i])
        cell_record['properties']['Rain_7D (mm)'] = float(rain_7d_vals[i])
        
    print(f"✅ [Modifier Data] Inference Complete: Translated Predictions back to {len(base_grid_data)} JSON items.")
    return base_grid_data