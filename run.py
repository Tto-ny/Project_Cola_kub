"""
Main Runner - เริ่มระบบทั้งหมด
รันไฟล์นี้เพื่อเปิดระบบ Landslide Warning Dashboard
"""

import os
import sys
from dotenv import load_dotenv

# Fix Windows terminal encoding for emoji support
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
load_dotenv()

def check_requirements():
    """ตรวจสอบว่าติดตั้ง dependencies ครบหรือยัง"""
    try:
        import fastapi
        import uvicorn
        import ee
        import pandas
        import sklearn
        import sqlalchemy
        import apscheduler
        print("✅ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n📦 Please install dependencies:")
        print("   py -m pip install -r requirements.txt")
        return False

def initialize_gee():
    """Initialize Google Earth Engine"""
    try:
        import ee
        project_id = os.getenv('GEE_PROJECT_ID', 'arched-wharf-485715-f9')
        
        print("\n🌍 Initializing Google Earth Engine...")
        try:
            ee.Initialize(project=project_id)
            print(f"✅ GEE initialized (Project: {project_id})")
            return True
        except Exception as e:
            print(f"⚠️  GEE not authenticated. Attempting authentication...")
            ee.Authenticate()
            ee.Initialize(project=project_id)
            print(f"✅ GEE authenticated and initialized")
            return True
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        print("\n📝 To use GEE, you need to:")
        print("   1. Sign up at https://earthengine.google.com/")
        print("   2. Run: earthengine authenticate")
        print("   3. Set GEE_PROJECT_ID in .env file")
        return False

def check_model():
    """ตรวจสอบว่ามีไฟล์โมเดลหรือไม่"""
    model_path = os.getenv('MODEL_PATH', './Northern_Landslide_Model_Final.pkl')
    if os.path.exists(model_path):
        print(f"✅ Model found: {model_path}")
        return True
    else:
        print(f"❌ Model not found: {model_path}")
        print("   Please ensure the model file is in the correct location")
        return False

def check_locations():
    """ตรวจสอบว่ามีไฟล์ locations หรือไม่"""
    csv_path = os.getenv('LOCATIONS_CSV_PATH', './new_landslide_data.csv')
    if os.path.exists(csv_path):
        import pandas as pd
        df = pd.read_csv(csv_path)
        print(f"✅ Locations file found: {len(df)} locations")
        return True
    else:
        print(f"❌ Locations file not found: {csv_path}")
        return False

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🏔️  Landslide Early Warning System")
    print("="*60 + "\n")
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check model
    if not check_model():
        print("\n⚠️  Warning: Model file not found. System will not work properly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Check locations
    if not check_locations():
        print("\n⚠️  Warning: Locations file not found.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Initialize GEE
    gee_ready = initialize_gee()
    if not gee_ready:
        print("\n⚠️  Warning: GEE not initialized. Data extraction will not work.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Start server
    print("\n" + "="*60)
    print("🚀 Starting Server...")
    print("="*60 + "\n")
    
    import uvicorn
    from server import app
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8000))
    
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📊 Dashboard: http://localhost:{port}/dashboard")
    print(f"📖 API Docs: http://localhost:{port}/docs")
    print(f"\n{'='*60}\n")
    
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
