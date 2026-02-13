"""
Landslide Prediction Engine
ระบบทำนายความเสี่ยงดินถล่ม
"""

import joblib
import pandas as pd
import numpy as np
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

class LandslidePredictor:
    def __init__(self, model_path: str = None):
        """โหลดโมเดลและ configuration"""
        if model_path is None:
            model_path = os.getenv('MODEL_PATH', './Northern_Landslide_Model_Final.pkl')
        
        try:
            package = joblib.load(model_path)
            self.model = package['model']
            self.fill_values = package['fill_values']
            self.feature_names = package['feature_names']
            
            # Risk thresholds
            self.threshold_warning = float(os.getenv('RISK_THRESHOLD_WARNING', 0.3))
            self.threshold_danger = float(os.getenv('RISK_THRESHOLD_DANGER', 0.6))
            
            print(f"✅ Model loaded successfully from {model_path}")
            print(f"   Features: {len(self.feature_names)}")
            print(f"   Thresholds: Warning={self.threshold_warning}, Danger={self.threshold_danger}")
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Model file not found: {model_path}")
        except Exception as e:
            raise Exception(f"❌ Failed to load model: {e}")
    
    def preprocess_input(self, input_data: Dict) -> pd.DataFrame:
        """
        Preprocess ข้อมูลก่อนทำนาย
        1. แก้ค่า -9999 (missing values)
        2. สร้าง interaction features
        3. เลือกเฉพาะ features ที่โมเดลต้องการ
        """
        df = pd.DataFrame([input_data])
        
        # 1. แก้ค่า -9999 (Missing Value Handling)
        for col in ['NDVI', 'NDWI']:
            if col in df.columns:
                val = df[col].iloc[0]
                if val == -9999 or pd.isna(val):
                    df[col] = self.fill_values[col]
                    print(f"   ⚠️ {col} missing! Using median value: {self.fill_values[col]:.4f}")
        
        # 2. สร้าง Interaction Features (สำคัญมาก!)
        df['Hydro_Slope_3D'] = df['Slope_Extracted'] * df['Rain_Ant_3D']
        df['Hydro_Slope_5D'] = df['Slope_Extracted'] * df['Rain_Ant_5D']
        df['Hydro_Slope_7D'] = df['Slope_Extracted'] * df['Rain_Ant_7D']
        
        # 3. เลือกเฉพาะคอลัมน์ที่โมเดลต้องการ
        try:
            X_ready = df[self.feature_names]
            return X_ready
        except KeyError as e:
            raise KeyError(f"❌ Missing required features: {e}")
    
    def predict_single(self, input_data: Dict) -> Dict:
        """
        ทำนายความเสี่ยงสำหรับจุดเดียว
        Returns: {
            'probability': float,
            'risk_level': str,
            'risk_color': str,
            'status': str,
            'details': dict
        }
        """
        # Preprocess
        X = self.preprocess_input(input_data)
        
        # Predict probability
        prob_score = self.model.predict_proba(X)[0][1]
        
        # Interpret risk level
        if prob_score >= self.threshold_danger:
            risk_level = "DANGER"
            risk_color = "red"
            status = "🔴 อันตราย"
            
            # เช็กเงื่อนไขพิเศษ: ไร่ข้าวโพด (NDVI ต่ำ) บนที่ชัน
            if input_data.get('NDVI', 0.5) < 0.4:
                status += " [เสี่ยงโคลนไหล/หน้าดินพัง]"
            else:
                status += " [เสี่ยงดินถล่มลึก]"
        
        elif prob_score >= self.threshold_warning:
            risk_level = "WARNING"
            risk_color = "yellow"
            status = "🟡 เฝ้าระวัง"
        
        else:
            risk_level = "NORMAL"
            risk_color = "green"
            status = "🟢 ปกติ"
        
        return {
            'probability': round(prob_score * 100, 2),  # as percentage
            'probability_raw': round(prob_score, 4),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'status': status,
            'details': {
                'slope': input_data.get('Slope_Extracted'),
                'elevation': input_data.get('Elevation_Extracted'),
                'ndvi': input_data.get('NDVI'),
                'ndwi': input_data.get('NDWI'),
                'rain_3d': input_data.get('Rain_Ant_3D'),
                'rain_5d': input_data.get('Rain_Ant_5D'),
                'rain_7d': input_data.get('Rain_Ant_7D')
            }
        }
    
    def predict_batch(self, input_list: List[Dict]) -> List[Dict]:
        """
        ทำนายแบบ batch สำหรับหลายจุดพร้อมกัน
        """
        results = []
        
        for i, input_data in enumerate(input_list):
            try:
                result = self.predict_single(input_data)
                result['index'] = i
                results.append(result)
            except Exception as e:
                print(f"   ❌ Prediction failed for index {i}: {e}")
                results.append({
                    'index': i,
                    'error': str(e),
                    'risk_level': 'ERROR',
                    'risk_color': 'gray'
                })
        
        return results


# Test function
def test_prediction():
    """ทดสอบการทำนาย"""
    predictor = LandslidePredictor()
    
    # Test case: ป่าทึบ + ฝนหนัก
    test_data = {
        'Slope_Extracted': 35,
        'Elevation_Extracted': 1200,
        'Aspect_Extracted': 180,
        'NDVI': 0.75,
        'NDWI': 0.3,
        'TWI': 12,
        'Distance_to_Road': 500,
        'Rain_Ant_3D': 120,
        'Rain_Ant_5D': 180,
        'Rain_Ant_7D': 250
    }
    
    result = predictor.predict_single(test_data)
    
    print("\n📊 Prediction Result:")
    print(f"   Probability: {result['probability']}%")
    print(f"   Status: {result['status']}")
    print(f"   Risk Level: {result['risk_level']}")
    print(f"   Details: {result['details']}")


if __name__ == "__main__":
    test_prediction()
