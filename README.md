# Landslide Early Warning System 🏔️

ระบบเตือนภัยดินถล่มล่วงหน้าสำหรับภาคเหนือ - Officer Monitoring Dashboard

## 📋 Features

- ✅ **Real-time Monitoring**: ติดตาม 2,728 จุดในภาคเหนือแบบ real-time
- ✅ **Google Earth Engine Integration**: ดึงข้อมูลจาก NASADEM, Sentinel-2, GPM IMERG อัตโนมัติ
- ✅ **ML Prediction**: ทำนายความเสี่ยง 3 ระดับ (🟢 Normal / 🟡 Warning / 🔴 Danger)
- ✅ **Auto-Update**: อัปเดตข้อมูลทุก 6 ชั่วโมง (0:00, 6:00, 12:00, 18:00)
- ✅ **Interactive Dashboard**: แผนที่แบบ interactive พร้อม filter และ search
- ✅ **REST API**: API สำหรับดึงข้อมูลและ integrate กับระบบอื่น

## 🚀 Quick Start

### 1. ติดตั้ง Dependencies

```bash
# สร้าง virtual environment
py -m venv landslide_env

# Activate environment
landslide_env\Scripts\activate

# ติดตั้ง packages
pip install -r requirements.txt
```

### 2. ตั้งค่า Google Earth Engine

```bash
# Authenticate GEE (ครั้งแรกเท่านั้น)
earthengine authenticate

# ตรวจสอบว่า authenticate สำเร็จ
earthengine ls
```

### 3. ตั้งค่า Environment Variables

แก้ไขไฟล์ `.env`:
```
GEE_PROJECT_ID=arched-wharf-485715-f9
```

### 4. รันระบบ

```bash
python run.py
```

เปิดเบราว์เซอร์ไปที่:
- **Dashboard**: http://localhost:8000/dashboard
- **API Docs**: http://localhost:8000/docs

## 📁 Project Structure

```
model/
├── run.py                    # Main runner
├── server.py                 # FastAPI server
├── gee_extractor.py          # GEE data extraction
├── predictor.py              # ML prediction engine
├── database.py               # Database layer
├── scheduler.py              # Auto-update scheduler
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── Northern_Landslide_Model_Final.pkl  # ML model
├── new_landslide_data.csv    # Monitoring locations
└── frontend/
    ├── index.html            # Dashboard UI
    ├── style.css             # Styling
    └── app.js                # Frontend logic
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Google Earth Engine
GEE_PROJECT_ID=arched-wharf-485715-f9

# Database
DATABASE_URL=sqlite:///./landslide_predictions.db

# Scheduler (every 6 hours)
UPDATE_SCHEDULE_HOURS=0,6,12,18

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Model & Data
MODEL_PATH=./Northern_Landslide_Model_Final.pkl
LOCATIONS_CSV_PATH=./new_landslide_data.csv

# Risk Thresholds
RISK_THRESHOLD_WARNING=0.3
RISK_THRESHOLD_DANGER=0.6
```

## 📊 API Endpoints

### GET /api/locations
ดึงรายการจุดติดตามทั้งหมด

### GET /api/predictions/latest
ดึงผลทำนายล่าสุด

### GET /api/predictions/by-risk/{risk_level}
ดึงผลทำนายตาม risk level (NORMAL, WARNING, DANGER)

### GET /api/stats
ดึงสถิติภาพรวม

### POST /api/update
Trigger manual update (admin)

## 🗺️ Data Sources

- **Terrain**: NASADEM (30m resolution)
- **Vegetation**: Sentinel-2 (NDVI, NDWI)
- **Rainfall**: GPM IMERG Early (real-time)
- **Hydrology**: TWI calculation
- **Infrastructure**: Distance to road

## 🎯 Risk Levels

- 🟢 **Normal**: Probability < 30%
- 🟡 **Warning**: 30% ≤ Probability < 60%
- 🔴 **Danger**: Probability ≥ 60%

## 🔄 Update Schedule

ระบบจะอัปเดตข้อมูลอัตโนมัติทุก 6 ชั่วโมง:
- 00:00 น.
- 06:00 น.
- 12:00 น.
- 18:00 น.

หรือสามารถ trigger manual update ได้ผ่าน dashboard

## 🐛 Troubleshooting

### GEE Authentication Error
```bash
earthengine authenticate
```

### Model File Not Found
ตรวจสอบว่าไฟล์ `Northern_Landslide_Model_Final.pkl` อยู่ในโฟลเดอร์เดียวกับ `run.py`

### Port Already in Use
แก้ไข `API_PORT` ใน `.env` เป็นพอร์ตอื่น

## 📝 License

For government use only - Northern Thailand Landslide Warning System

## 👥 Contact

For support, please contact the development team.
