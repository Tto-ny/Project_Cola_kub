"""
Scheduler - Auto-update ทุก 6 ชั่วโมง
ดึงข้อมูลจาก GEE และทำนายความเสี่ยง
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

from gee_extractor import GEEExtractor
from predictor import LandslidePredictor
from database import Database

load_dotenv()

class LandslideScheduler:
    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler()
        self.db = Database()
        self.extractor = None  # จะ initialize ตอนรัน
        self.predictor = LandslidePredictor()
        
        # Load locations
        self.locations_csv = os.getenv('LOCATIONS_CSV_PATH', './new_landslide_data.csv')
        self.load_locations()
        
        # Schedule hours (default: 0, 6, 12, 18)
        schedule_hours = os.getenv('UPDATE_SCHEDULE_HOURS', '0,6,12,18')
        self.schedule_hours = [int(h.strip()) for h in schedule_hours.split(',')]
        
        print(f"✅ Scheduler initialized")
        print(f"   Update schedule: Every 6 hours at {self.schedule_hours}")
        print(f"   Total locations: {len(self.locations)}")
    
    def load_locations(self):
        """โหลดรายการจุดติดตามจาก CSV"""
        try:
            df = pd.read_csv(self.locations_csv)
            self.locations = df.to_dict('records')
            print(f"✅ Loaded {len(self.locations)} locations from {self.locations_csv}")
            
            # เพิ่มลง database ถ้ายังไม่มี
            existing = self.db.get_all_locations()
            if len(existing) == 0:
                print("   Adding locations to database...")
                for loc in self.locations:
                    self.db.add_location(
                        invent_id=str(loc.get('INVENT_ID')),
                        lon=loc.get('LONGITUDE'),
                        lat=loc.get('LATITUDE'),
                        tambon=loc.get('TAMBON'),
                        district=loc.get('DISTRICT'),
                        province=loc.get('PROVINCE')
                    )
                print(f"   ✅ Added {len(self.locations)} locations to database")
        except Exception as e:
            print(f"❌ Failed to load locations: {e}")
            self.locations = []
    
    def update_all_predictions(self):
        """
        อัปเดตการทำนายสำหรับทุกจุด
        เรียกใช้ทุก 6 ชั่วโมง
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting prediction update at {datetime.now()}")
        print(f"{'='*60}")
        
        # Initialize GEE (ต้อง initialize ใหม่ทุกครั้ง)
        try:
            self.extractor = GEEExtractor()
        except Exception as e:
            print(f"❌ Failed to initialize GEE: {e}")
            return
        
        total = len(self.locations)
        success_count = 0
        danger_count = 0
        warning_count = 0
        normal_count = 0
        
        for i, loc in enumerate(self.locations, 1):
            try:
                invent_id = str(loc.get('INVENT_ID'))
                lon = loc.get('LONGITUDE')
                lat = loc.get('LATITUDE')
                
                print(f"\n[{i}/{total}] Processing {invent_id} ({lon:.4f}, {lat:.4f})...")
                
                # 1. ดึงข้อมูลจาก GEE
                features = self.extractor.extract_all_features(lon, lat)
                
                # 2. ทำนายความเสี่ยง
                prediction = self.predictor.predict_single(features)
                
                # 3. บันทึกลง database
                self.db.add_prediction(
                    location_id=i,
                    invent_id=invent_id,
                    prediction_result=prediction,
                    features=features
                )
                
                # นับสถิติ
                if prediction['risk_level'] == 'DANGER':
                    danger_count += 1
                elif prediction['risk_level'] == 'WARNING':
                    warning_count += 1
                else:
                    normal_count += 1
                
                success_count += 1
                print(f"   ✅ {prediction['status']} (Prob: {prediction['probability']}%)")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                continue
        
        print(f"\n{'='*60}")
        print(f"📊 Update Summary:")
        print(f"   Total processed: {success_count}/{total}")
        print(f"   🔴 Danger: {danger_count}")
        print(f"   🟡 Warning: {warning_count}")
        print(f"   🟢 Normal: {normal_count}")
        print(f"   Completed at: {datetime.now()}")
        print(f"{'='*60}\n")
    
    def start(self):
        """เริ่ม scheduler"""
        # เพิ่ม job สำหรับแต่ละชั่วโมงที่กำหนด
        for hour in self.schedule_hours:
            trigger = CronTrigger(hour=hour, minute=0)
            self.scheduler.add_job(
                self.update_all_predictions,
                trigger=trigger,
                id=f'update_{hour}',
                name=f'Update predictions at {hour}:00'
            )
            print(f"   ✅ Scheduled update at {hour}:00")
        
        self.scheduler.start()
        print(f"\n✅ Scheduler started!")
        print(f"   Next run: {self.scheduler.get_jobs()[0].next_run_time}")
    
    def run_now(self):
        """รันการอัปเดตทันที (สำหรับ manual trigger)"""
        self.update_all_predictions()
    
    def stop(self):
        """หยุด scheduler"""
        self.scheduler.shutdown()
        self.db.close()
        print("✅ Scheduler stopped")


# Test function
def test_scheduler():
    """ทดสอบ scheduler"""
    scheduler = LandslideScheduler()
    
    # ทดสอบรันทันที (แค่ 5 จุดแรก)
    print("Testing with first 5 locations...")
    scheduler.locations = scheduler.locations[:5]
    scheduler.run_now()


if __name__ == "__main__":
    test_scheduler()
