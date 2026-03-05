"""
Prediction service that loads the trained Random Forest model and scaler,
fetches rainfall from Open-Meteo, and predicts landslide risk.
"""
import joblib
import numpy as np
import os

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_PATH = os.path.join(MODEL_DIR, "best_ml_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "landslide_scaler.pkl")

_model = None
_scaler = None

def load_model():
    global _model, _scaler
    try:
        _model = joblib.load(MODEL_PATH)
        print(f"Model loaded from {MODEL_PATH}")
    except Exception as e:
        print(f"WARNING: Could not load model: {e}")
        _model = None
    
    try:
        _scaler = joblib.load(SCALER_PATH)
        print(f"Scaler loaded from {SCALER_PATH}")
    except Exception as e:
        print(f"WARNING: Could not load scaler: {e}")
        _scaler = None

def predict_risk(features: dict) -> dict:
    """
    Predict landslide risk for a single cell.
    features: dict with keys like Elevation, Slope, Aspect, TWI, MODIS_LC,
              Soil_Type, NDVI, NDWI, Distance_to_Road, Rainfall
    Returns: { risk: 'High'|'Medium'|'Low', probability: float }
    """
    if _model is None:
        load_model()
    
    # Feature order expected by the model (27 features)
    feature_order = [
         'CHIRPS_Day_1', 'CHIRPS_Day_2', 'CHIRPS_Day_3', 'CHIRPS_Day_4', 'CHIRPS_Day_5',
         'CHIRPS_Day_6', 'CHIRPS_Day_7', 'CHIRPS_Day_8', 'CHIRPS_Day_9', 'CHIRPS_Day_10',
         'Elevation_Extracted', 'Slope_Extracted', 'Aspect_Extracted',
         'MODIS_LC', 'NDVI', 'NDWI', 'TWI', 'Soil_Type',
         'Road_Zone',
         'Rain_3D_Prior', 'Rain_5D_Prior', 'Rain_7D_Prior', 'Rain_10D_Prior',
         'Rain3D_x_Slope', 'Rain5D_x_Slope', 'Rain7D_x_Slope', 'Rain10D_x_Slope'
    ]
    
    values = [features.get(f, 0) for f in feature_order]
    X = np.array([values])
    
    # If model is loaded, use it
    if _model is not None:
        try:
            if _scaler is not None:
                X = _scaler.transform(X)
            prediction = _model.predict(X)[0]
            
            # Try to get probability
            try:
                # Assuming model is binary classification where class 1 is landslide
                proba = _model.predict_proba(X)[0]
                if len(proba) > 1:
                    max_prob = float(proba[1]) # Use probability of landslide (class 1)
                else:
                    max_prob = float(max(proba))
            except:
                max_prob = 0.0
            
            # Map prediction using probability threshold
            if max_prob > 0.6:
                risk = 'High'
            elif max_prob > 0.3:
                risk = 'Medium'
            else:
                risk = 'Low'
            
            return {"risk": risk, "probability": max_prob, "prediction_raw": int(prediction)}
        except Exception as e:
            print(f"Model prediction error: {e}")
    
    # Fallback: rule-based prediction using slope + rainfall
    slope = features.get('Slope', 0) or 0
    rainfall = features.get('Rainfall', 0) or 0
    
    score = (slope / 45.0) * 0.5 + (min(rainfall, 200) / 200.0) * 0.5
    if score > 0.6:
        risk = 'High'
    elif score > 0.3:
        risk = 'Medium'
    else:
        risk = 'Low'
    
    return {"risk": risk, "probability": score, "prediction_raw": -1}

def predict_batch(grid_data: list, rainfall: float) -> list:
    """Predict risk for all cells with a given rainfall amount."""
    results = []
    for cell in grid_data:
        props = cell.get('properties', {})
        props['Rainfall'] = rainfall
        pred = predict_risk(props)
        results.append({
            'polygon': cell.get('polygon'),
            'properties': props,
            'risk': pred['risk'],
            'probability': pred['probability'],
        })
    return results
