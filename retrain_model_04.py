import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import optuna
import warnings

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve, precision_recall_curve
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

# ปิดแจ้งเตือนเพื่อความสะอาดของหน้าจอ
optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings('ignore')

print("==================================================")
print("1. Loading and Preprocessing Dataset...")
print("==================================================")
df = pd.read_csv('Landslide_Final_Cleaned_V2.csv')
TARGET_COL = 'Geohaz_E'

features_to_use = [
    'CHIRPS_Day_1', 'CHIRPS_Day_2', 'CHIRPS_Day_3', 'CHIRPS_Day_4', 'CHIRPS_Day_5',
    'CHIRPS_Day_6', 'CHIRPS_Day_7', 'CHIRPS_Day_8', 'CHIRPS_Day_9', 'CHIRPS_Day_10',
    'Elevation_Extracted', 'Slope_Extracted', 'Aspect_Extracted',
    'MODIS_LC', 'NDVI', 'NDWI', 'TWI', 'Soil_Type', 'Road_Zone',
    'Rain_3D_Prior', 'Rain_5D_Prior', 'Rain_7D_Prior', 'Rain_10D_Prior',
    'Rain3D_x_Slope', 'Rain5D_x_Slope', 'Rain7D_x_Slope', 'Rain10D_x_Slope'
]

X = df[features_to_use]
y = df[TARGET_COL]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# เติมค่าว่างและ Scale ข้อมูล
train_medians = X_train.median(numeric_only=True)
X_train = X_train.fillna(train_medians)
X_test = X_test.fillna(train_medians)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
joblib.dump(scaler, 'landslide_scaler.pkl')
print("-> Preprocessing complete. Scaler saved as 'landslide_scaler.pkl'")

print("\n==================================================")
print("2. Tuning LightGBM & CatBoost (Optimizing for PR-AUC)...")
print("==================================================")

def objective_lgb(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 300),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'class_weight': 'balanced',
        'random_state': 42,
        'verbose': -1
    }
    m = LGBMClassifier(**params).fit(X_train_scaled, y_train)
    return average_precision_score(y_test, m.predict_proba(X_test_scaled)[:, 1])

study_lgb = optuna.create_study(direction='maximize')
study_lgb.optimize(objective_lgb, n_trials=15)
print(f"-> LightGBM Tuned (Best PR-AUC: {study_lgb.best_value:.4f})")

def objective_cat(trial):
    params = {
        'iterations': trial.suggest_int('iterations', 100, 300),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'depth': trial.suggest_int('depth', 4, 8),
        'auto_class_weights': 'Balanced',
        'random_seed': 42,
        'verbose': 0
    }
    m = CatBoostClassifier(**params).fit(X_train_scaled, y_train)
    return average_precision_score(y_test, m.predict_proba(X_test_scaled)[:, 1])

study_cat = optuna.create_study(direction='maximize')
study_cat.optimize(objective_cat, n_trials=15)
print(f"-> CatBoost Tuned (Best PR-AUC: {study_cat.best_value:.4f})")

print("\n==================================================")
print("3. Evaluating All Models...")
print("==================================================")

pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42),
    "Decision Tree": DecisionTreeClassifier(class_weight='balanced', random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42),
    "XGBoost": XGBClassifier(scale_pos_weight=pos_weight, eval_metric='logloss', random_state=42),
    "Gradient Boosting": GradientBoostingClassifier(random_state=42),
    "LightGBM (Tuned)": LGBMClassifier(**study_lgb.best_params, class_weight='balanced', random_state=42, verbose=-1),
    "CatBoost (Tuned)": CatBoostClassifier(**study_cat.best_params, auto_class_weights='Balanced', random_state=42, verbose=0)
}

results = []
model_probs = {}
best_pr_auc = -1
best_model_name = ""
best_model_obj = None

for name, model in models.items():
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_test_scaled)[:, 1]
    model_probs[name] = probs
    
    roc_auc = roc_auc_score(y_test, probs)
    pr_auc = average_precision_score(y_test, probs)
    
    results.append({
        "Model": name,
        "ROC-AUC": f"{roc_auc:.4f}",
        "PR-AUC (Primary)": f"{pr_auc:.4f}",
        "_pr_auc_val": pr_auc
    })
    
    if pr_auc > best_pr_auc:
        best_pr_auc = pr_auc
        best_model_name = name
        best_model_obj = model
        
    print(f"Trained -> {name} (PR-AUC: {pr_auc:.4f})")

print("\n==================================================")
print("4. Generating Output Plots...")
print("==================================================")

results_df = pd.DataFrame(results).sort_values(by="_pr_auc_val", ascending=False)

# 4.1 Comparison Table
display_df = results_df.drop(columns=["_pr_auc_val"]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.axis('off')
table = ax.table(cellText=display_df.values, colLabels=display_df.columns, cellLoc='center', loc='center')
table.set_fontsize(12)
table.scale(1.2, 1.5)
for (row, col), cell in table.get_celld().items():
    if row == 0: 
        cell.set_facecolor('#4472C4'); cell.set_text_props(weight='bold', color='white')
    elif row == 1: 
        cell.set_facecolor('#F2F2F2'); cell.set_text_props(weight='bold', color='red')
    else: 
        cell.set_facecolor('#F2F2F2' if row % 2 == 0 else 'white')
plt.title("Model Comparison (Score-based)", weight='bold', pad=15)
plt.savefig('01_comparison_table.png', bbox_inches='tight', dpi=300)
print("-> Generated: 01_comparison_table.png")

# 4.2 PR Curve & ROC Curve
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
for name, probs in model_probs.items():
    fpr, tpr, _ = roc_curve(y_test, probs)
    precision, recall, _ = precision_recall_curve(y_test, probs)
    lw = 2.5 if name == best_model_name else 1.5
    ax1.plot(fpr, tpr, lw=lw, label=name)
    ax2.plot(recall, precision, lw=lw, label=name)

ax1.set_title('ROC Curve', weight='bold')
ax1.set_xlabel('False Positive Rate')
ax1.set_ylabel('True Positive Rate')
ax1.legend(fontsize=8)
ax1.grid(True, linestyle='--', alpha=0.5)

ax2.set_title('Precision-Recall Curve (Primary)', weight='bold')
ax2.set_xlabel('Recall')
ax2.set_ylabel('Precision')
ax2.legend(fontsize=8)
ax2.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('02_Performance_Curves.png', dpi=300)
print("-> Generated: 02_Performance_Curves.png")

# 4.3 Risk Tier Distribution
best_p = model_probs[best_model_name]
landslide_pts = best_p[y_test == 1]
safe_pts = best_p[y_test == 0]

def get_tier_pct(p):
    return [(p <= 0.3).sum()/len(p)*100, ((p > 0.3) & (p <= 0.6)).sum()/len(p)*100, (p > 0.6).sum()/len(p)*100]

tier_landslide = get_tier_pct(landslide_pts)
tier_safe = get_tier_pct(safe_pts)

fig, ax = plt.subplots(figsize=(8, 5))
labels = ['Actual Landslide (1)', 'Safe Zone (0)']
b1 = ax.bar(labels, [tier_landslide[0], tier_safe[0]], label='Low Risk (<= 0.3)', color='#A6A6A6')
b2 = ax.bar(labels, [tier_landslide[1], tier_safe[1]], bottom=[tier_landslide[0], tier_safe[0]], label='Medium Risk (0.3 - 0.6)', color='#FFC000')
b3 = ax.bar(labels, [tier_landslide[2], tier_safe[2]], bottom=[tier_landslide[0]+tier_landslide[1], tier_safe[0]+tier_safe[1]], label='High Risk (> 0.6)', color='#FF0000')

plt.ylabel('Percentage (%)')
plt.title(f'Risk Tier Distribution by {best_model_name}', weight='bold')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

for i, (l, m, h) in enumerate(zip([tier_landslide[0], tier_safe[0]], [tier_landslide[1], tier_safe[1]], [tier_landslide[2], tier_safe[2]])):
    if h > 5: ax.text(i, l + m + h/2, f'{h:.1f}%', ha='center', va='center', color='white', weight='bold')
    if m > 5: ax.text(i, l + m/2, f'{m:.1f}%', ha='center', va='center', color='black', weight='bold')
    if l > 5: ax.text(i, l/2, f'{l:.1f}%', ha='center', va='center', color='black', weight='bold')
    
plt.tight_layout()
plt.savefig('03_Risk_Distribution.png', dpi=300)
print("-> Generated: 03_Risk_Distribution.png")

# 4.4 Feature Importance
if hasattr(best_model_obj, 'feature_importances_'):
    fi_df = pd.DataFrame({'Feature': features_to_use, 'Importance': best_model_obj.feature_importances_})
    fi_df = fi_df.sort_values(by='Importance', ascending=False).head(10)
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=fi_df, palette='viridis')
    plt.title(f'Top 10 Feature Importances ({best_model_name})', weight='bold')
    plt.tight_layout()
    plt.savefig('04_Feature_Importance.png', dpi=300)
    print("-> Generated: 04_Feature_Importance.png")

# Save Model
joblib.dump(best_model_obj, 'best_landslide_model.pkl')
print("\n==================================================")
print(f"🏆 Pipeline Finished! Best Model: {best_model_name}")
print("✅ Saved model as 'best_landslide_model.pkl'")
print("==================================================")