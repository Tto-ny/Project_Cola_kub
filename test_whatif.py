import sys
import pandas as pd
import numpy as np
import joblib

model = joblib.load(r'C:\Users\nongt\OneDrive\Desktop\model\best_model_Random_Forest_Normalized.pkl')
scaler = joblib.load(r'C:\Users\nongt\OneDrive\Desktop\model\landslide_scaler.pkl')

columns_order = [
    'CHIRPS_Day_1', 'CHIRPS_Day_2', 'CHIRPS_Day_3', 'CHIRPS_Day_4', 'CHIRPS_Day_5',
    'CHIRPS_Day_6', 'CHIRPS_Day_7', 'CHIRPS_Day_8', 'CHIRPS_Day_9', 'CHIRPS_Day_10',
    'Elevation_Extracted', 'Slope_Extracted', 'Aspect_Extracted',
    'MODIS_LC', 'NDVI', 'NDWI', 'TWI', 'Soil_Type',
    'Road_Zone',
    'Rain_3D_Prior', 'Rain_5D_Prior', 'Rain_7D_Prior',
    'Rain3D_x_Slope', 'Rain5D_x_Slope', 'Rain7D_x_Slope'
]

# Simulate user's test.ipynb behavior
def user_test(rain_val):
    features = {}
    
    # Let's guess how they input "5000": Maybe all days? Or just day 1?
    # They said "เทสน้ำฝน 5000" in their UI? Whatif UI sends 5000 as total.
    # In their test.ipynb, they had a list of 10. Let's assume they put 5000 in day 1? 
    # Or maybe they divided it? Let's check a few.
    features['Slope_Extracted'] = 21.2
    features['Elevation_Extracted'] = 1574
    features['Distance_to_Road'] = 0.09
    features['Aspect_Extracted'] = 69.53
    features['MODIS_LC'] = 10
    features['NDVI'] = 0.87
    features['NDWI'] = -0.79
    features['TWI'] = 0.95
    features['Soil_Type'] = 4
    features['Road_Zone'] = 1

    # Scenario: User's old code included Day 1 in Rain_3D_Prior
    features['CHIRPS_Day_1'] = rain_val
    for i in range(2, 11):
        features[f'CHIRPS_Day_{i}'] = 0
        
    features['Rain_3D_Prior'] = rain_val
    features['Rain_5D_Prior'] = rain_val
    features['Rain_7D_Prior'] = rain_val
    features['Rain3D_x_Slope'] = rain_val * 21.2
    features['Rain5D_x_Slope'] = rain_val * 21.2
    features['Rain7D_x_Slope'] = rain_val * 21.2

    df_input = pd.DataFrame([features], columns=columns_order)
    X_scaled = scaler.transform(df_input)
    proba = model.predict_proba(X_scaled)[0][1]
    return proba

print("User Test with 500mm Day 1 (Old logic where Day1 was included):", user_test(500))
print("User Test with 5000mm Day 1 (Old logic where Day1 was included):", user_test(5000))
print("User Test with 50mm Day 1 (Old logic where Day1 was included):", user_test(50))

# Try mapping exactly like our current what-if does
def new_backend_test(rain_val):
    features = {}
    features['Slope_Extracted'] = 21.2
    features['Elevation_Extracted'] = 1574
    features['Distance_to_Road'] = 0.09
    features['Aspect_Extracted'] = 69.53
    features['MODIS_LC'] = 10
    features['NDVI'] = 0.87
    features['NDWI'] = -0.79
    features['TWI'] = 0.95
    features['Soil_Type'] = 4
    features['Road_Zone'] = 1
    
    daily = rain_val / 7.0
    for i in range(1, 8):
        features[f'CHIRPS_Day_{i}'] = daily
    for i in range(8, 11):
        features[f'CHIRPS_Day_{i}'] = 0
        
    # NEW LOGIC: without Day 1 !
    r3 = daily*3
    r5 = r3 + daily*2
    r7 = r5 + daily*2
    
    features['Rain_3D_Prior'] = r3
    features['Rain_5D_Prior'] = r5
    features['Rain_7D_Prior'] = r7
    features['Rain3D_x_Slope'] = r3 * 21.2
    features['Rain5D_x_Slope'] = r5 * 21.2
    features['Rain7D_x_Slope'] = r7 * 21.2
    
    df_input = pd.DataFrame([features], columns=columns_order)
    X_scaled = scaler.transform(df_input)
    proba = model.predict_proba(X_scaled)[0][1]
    return proba

print("Backend evenly 7-days with 500:", new_backend_test(500))
print("Backend evenly 7-days with 5000:", new_backend_test(5000))
