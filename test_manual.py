"""
Manual Test Script - ทดสอบการดึงข้อมูลและทำนาย
รันไฟล์นี้เพื่อดูการทำงานแบบละเอียด
"""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from scheduler import LandslideScheduler

def main():
    print("\n" + "="*60)
    print("🧪 Manual Test - Landslide Prediction")
    print("="*60 + "\n")
    
    # สร้าง scheduler
    scheduler = LandslideScheduler()
    
    # ลดจำนวนจุดให้ทดสอบแค่ 10 จุดแรก
    print(f"📊 Total locations: {len(scheduler.locations)}")
    print("🔧 Testing with first 10 locations only...\n")
    scheduler.locations = scheduler.locations[:10]
    
    # รันการอัปเดตทันที
    scheduler.run_now()
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
