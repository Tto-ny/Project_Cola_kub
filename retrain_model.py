import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
import matplotlib.pyplot as plt
import seaborn as sns
import os

print("Loading dataset...")
df = pd.read_csv('df_cleaned_final_v2.csv')
TARGET_COL = 'Geohaz_E'

features_to_use = [
    'CHIRPS_Day_1', 'CHIRPS_Day_2', 'CHIRPS_Day_3', 'CHIRPS_Day_4', 'CHIRPS_Day_5',
    'CHIRPS_Day_6', 'CHIRPS_Day_7', 'CHIRPS_Day_8', 'CHIRPS_Day_9', 'CHIRPS_Day_10',
    'Elevation_Extracted', 'Slope_Extracted', 'Aspect_Extracted',
    'MODIS_LC', 'NDVI', 'NDWI', 'TWI', 'Soil_Type',
    'Road_Zone',
    'Rain_3D_Prior', 'Rain_5D_Prior', 'Rain_7D_Prior', 'Rain_10D_Prior',
    'Rain3D_x_Slope', 'Rain5D_x_Slope', 'Rain7D_x_Slope', 'Rain10D_x_Slope'
]

# 1. กำหนด X และ y ก่อน
X = df[features_to_use]
y = df[TARGET_COL]

# 2. แบ่ง Train / Test ทันที! (กันข้อมูลข้อสอบรั่วไหล)
print("Splitting data into Train and Test sets...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# 3. จัดการ Missing Values (อ้างอิงค่าจากชุด Train เท่านั้น)
print("Handling Missing Values...")
train_medians = X_train.median(numeric_only=True)
X_train = X_train.fillna(train_medians)
X_test = X_test.fillna(train_medians) # ใช้ค่า Median ของ Train มาเติมใส่ Test

# 4. ทำ Imbalanced Data เฉพาะบนชุด Train
print("Balancing Classes on Training Data...")
df_train = pd.concat([X_train, y_train], axis=1)
majority = df_train[df_train[TARGET_COL] == 0.0]
minority = df_train[df_train[TARGET_COL] == 1.0]

minority_upsampled = minority.sample(n=len(majority), replace=True, random_state=42)
df_train_balanced = pd.concat([majority, minority_upsampled])

# (Optional แต่แนะนำ) สับเปลี่ยนข้อมูลเล็กน้อย เพื่อไม่ให้คลาสเกาะกลุ่มกัน
df_train_balanced = df_train_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

X_train_bal = df_train_balanced[features_to_use]
y_train_bal = df_train_balanced[TARGET_COL]

# 5. Scaling features
print("Scaling features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_bal) # Fit กับข้อมูลที่ Balance แล้ว
X_test_scaled = scaler.transform(X_test) # Transform อย่างเดียว

joblib.dump(scaler, 'landslide_scaler.pkl')

print("Training and Evaluating 7 Models...")

models = {
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
    "Gradient Boosting": GradientBoostingClassifier(random_state=42),
    "XGBoost": XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42),
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "LightGBM": LGBMClassifier(random_state=42, verbose=-1),
    "CatBoost": CatBoostClassifier(verbose=0, random_state=42)
}

results = []
best_model = None
best_f1 = -1
best_model_name = ""

for name, model in models.items():
    print(f"  -> Training {name}...")
    model.fit(X_train_scaled, y_train_bal) # เทรนด้วย y ที่ Balance แล้ว
    y_pred = model.predict(X_test_scaled)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    results.append({
        "Model": name,
        "Accuracy": f"{acc*100:.2f}%",
        "Precision": f"{prec*100:.2f}%",
        "Recall": f"{rec*100:.2f}%",
        "F1-Score": f"{f1*100:.2f}%",
        "_f1_val": f1  # Used for sorting
    })
    
    if f1 > best_f1:
        best_f1 = f1
        best_model = model
        best_model_name = name

# Print Comparison Table
results_df = pd.DataFrame(results).sort_values(by="_f1_val", ascending=False).drop(columns=["_f1_val"])
print("\nModel Comparison Results:")
print(results_df.to_string(index=False))

print(f"\nBest Model Selected: {best_model_name} (F1-Score: {best_f1*100:.2f}%)")

# Feature Importances for Best Model
if hasattr(best_model, 'feature_importances_'):
    importances = best_model.feature_importances_
    feature_imp_df = pd.DataFrame({
        'Feature': features_to_use,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False).reset_index(drop=True)
    
    print(f"\nFeature Importances ({best_model_name}):")
    print(feature_imp_df.head(10).to_string(index=False))
    
    # Plotting Feature Importances
    plt.figure(figsize=(10, 8))
    sns.barplot(x='Importance', y='Feature', data=feature_imp_df)
    plt.title(f'Feature Importances ({best_model_name})')
    plt.tight_layout()
    plt.savefig('feature_importances.png')
    print("Saved Feature Importances plot to 'feature_importances.png'")

# Save Best Model
joblib.dump(best_model, 'best_ml_model.pkl')
print(f"\nSuccess! Saved to:\n- {os.path.abspath('best_ml_model.pkl')}\n- {os.path.abspath('landslide_scaler.pkl')}")