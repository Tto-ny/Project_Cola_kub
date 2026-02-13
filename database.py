"""
Database Layer
จัดการข้อมูลการทำนายและ locations
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Location(Base):
    """ตารางเก็บพิกัดจุดติดตาม"""
    __tablename__ = 'locations'
    
    id = Column(Integer, primary_key=True)
    invent_id = Column(String, unique=True, index=True)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    tambon = Column(String)
    district = Column(String)
    province = Column(String)
    created_at = Column(DateTime, default=datetime.now)

class Prediction(Base):
    """ตารางเก็บผลการทำนาย"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, nullable=False, index=True)
    invent_id = Column(String, index=True)
    
    # Prediction results
    probability = Column(Float)  # 0-100
    probability_raw = Column(Float)  # 0-1
    risk_level = Column(String)  # NORMAL, WARNING, DANGER
    risk_color = Column(String)  # green, yellow, red
    status = Column(Text)
    
    # Input features (stored as JSON)
    features = Column(JSON)
    
    # Metadata
    predicted_at = Column(DateTime, default=datetime.now, index=True)
    prediction_date = Column(DateTime, index=True)  # วันที่ทำนาย (สำหรับ historical)

class RawData(Base):
    """ตารางเก็บข้อมูลดิบจาก GEE (สำหรับ debugging)"""
    __tablename__ = 'raw_data'
    
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, nullable=False)
    invent_id = Column(String)
    
    # GEE data
    gee_data = Column(JSON)
    
    # Metadata
    extracted_at = Column(DateTime, default=datetime.now)
    data_date = Column(DateTime)

class Database:
    def __init__(self, db_url: str = None):
        """Initialize database connection"""
        if db_url is None:
            db_url = os.getenv('DATABASE_URL', 'sqlite:///./landslide_predictions.db')
        
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        print(f"✅ Database initialized: {db_url}")
    
    def add_location(self, invent_id: str, lon: float, lat: float, 
                     tambon: str = None, district: str = None, province: str = None):
        """เพิ่มจุดติดตามใหม่"""
        location = Location(
            invent_id=invent_id,
            longitude=lon,
            latitude=lat,
            tambon=tambon,
            district=district,
            province=province
        )
        self.session.add(location)
        self.session.commit()
        return location.id
    
    def get_all_locations(self):
        """ดึงจุดติดตามทั้งหมด"""
        return self.session.query(Location).all()
    
    def add_prediction(self, location_id: int, invent_id: str, 
                      prediction_result: dict, features: dict, 
                      prediction_date: datetime = None):
        """บันทึกผลการทำนาย"""
        if prediction_date is None:
            prediction_date = datetime.now()
        
        pred = Prediction(
            location_id=location_id,
            invent_id=invent_id,
            probability=prediction_result.get('probability'),
            probability_raw=prediction_result.get('probability_raw'),
            risk_level=prediction_result.get('risk_level'),
            risk_color=prediction_result.get('risk_color'),
            status=prediction_result.get('status'),
            features=features,
            prediction_date=prediction_date
        )
        self.session.add(pred)
        self.session.commit()
        return pred.id
    
    def get_latest_predictions(self, limit: int = None):
        """ดึงผลทำนายล่าสุด"""
        query = self.session.query(Prediction).order_by(Prediction.predicted_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def get_predictions_by_risk(self, risk_level: str):
        """ดึงผลทำนายตาม risk level"""
        return self.session.query(Prediction).filter(
            Prediction.risk_level == risk_level
        ).order_by(Prediction.predicted_at.desc()).all()
    
    def get_prediction_by_location(self, location_id: int, limit: int = 10):
        """ดึงประวัติการทำนายของจุดหนึ่งๆ"""
        return self.session.query(Prediction).filter(
            Prediction.location_id == location_id
        ).order_by(Prediction.predicted_at.desc()).limit(limit).all()
    
    def add_raw_data(self, location_id: int, invent_id: str, gee_data: dict, data_date: datetime = None):
        """บันทึกข้อมูลดิบจาก GEE"""
        if data_date is None:
            data_date = datetime.now()
        
        raw = RawData(
            location_id=location_id,
            invent_id=invent_id,
            gee_data=gee_data,
            data_date=data_date
        )
        self.session.add(raw)
        self.session.commit()
        return raw.id
    
    def close(self):
        """ปิด connection"""
        self.session.close()


# Test function
def test_database():
    """ทดสอบ database"""
    db = Database()
    
    # Test add location
    loc_id = db.add_location(
        invent_id="TEST001",
        lon=100.5,
        lat=18.3,
        tambon="Test",
        district="Test District",
        province="Nan"
    )
    print(f"✅ Added location: ID={loc_id}")
    
    # Test add prediction
    pred_result = {
        'probability': 45.5,
        'probability_raw': 0.455,
        'risk_level': 'WARNING',
        'risk_color': 'yellow',
        'status': '🟡 เฝ้าระวัง'
    }
    features = {'slope': 35, 'rain_7d': 150}
    
    pred_id = db.add_prediction(loc_id, "TEST001", pred_result, features)
    print(f"✅ Added prediction: ID={pred_id}")
    
    # Test query
    latest = db.get_latest_predictions(limit=5)
    print(f"✅ Latest predictions: {len(latest)} records")
    
    db.close()


if __name__ == "__main__":
    test_database()
