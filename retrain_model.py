import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import os

print("📂 Loading dataset...")
df = pd.read_csv('Landslide_Final_Cleaned_V2.csv')
TARGET_COL = 'Geohaz_E'

features_to_use = [
    'CHIRPS_Day_1', 'CHIRPS_Day_2', 'CHIRPS_Day_3', 'CHIRPS_Day_4', 'CHIRPS_Day_5',
    'CHIRPS_Day_6', 'CHIRPS_Day_7', 'CHIRPS_Day_8', 'CHIRPS_Day_9', 'CHIRPS_Day_10',
    'Elevation_Extracted', 'Slope_Extracted', 'Aspect_Extracted',
    'MODIS_LC', 'NDVI', 'NDWI', 'TWI', 'Soil_Type',
    'Road_Zone',
    'Rain_3D_Prior', 'Rain_5D_Prior', 'Rain_7D_Prior',
    'Rain3D_x_Slope', 'Rain5D_x_Slope', 'Rain7D_x_Slope'
]

print("🧹 Preprocessing data & Balance Classes...")
X = df[features_to_use].fillna(df[features_to_use].median(numeric_only=True))
y = df[TARGET_COL]

df_combined = pd.concat([X, y], axis=1)
majority = df_combined[df_combined[TARGET_COL] == 0.0]
minority = df_combined[df_combined[TARGET_COL] == 1.0]
minority_upsampled = minority.sample(n=len(majority), replace=True, random_state=42)
df_balanced = pd.concat([majority, minority_upsampled])

X_bal = df_balanced[features_to_use]
y_bal = df_balanced[TARGET_COL]

X_train, X_test, y_train, y_test = train_test_split(X_bal, y_bal, test_size=0.3, random_state=42, stratify=y_bal)

print("⚖️ Scaling features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

joblib.dump(scaler, 'landslide_scaler.pkl')

print("🧠 Training Random Forest...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

joblib.dump(model, 'best_model_Random_Forest_Normalized.pkl')
print(f"✅ Success! Saved to:\n- {os.path.abspath('best_model_Random_Forest_Normalized.pkl')}\n- {os.path.abspath('landslide_scaler.pkl')}")
