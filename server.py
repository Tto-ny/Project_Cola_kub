"""
FastAPI Server - Landslide Warning System API
ให้บริการ API สำหรับ dashboard
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import pandas as pd
import os

from database import Database
from predictor import LandslidePredictor
from scheduler import LandslideScheduler

# Initialize FastAPI
app = FastAPI(
    title="Landslide Early Warning System",
    description="ระบบเตือนภัยดินถล่มล่วงหน้าสำหรับภาคเหนือ",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Initialize components
db = Database()
predictor = LandslidePredictor()
scheduler = LandslideScheduler()

# Pydantic models
class LocationResponse(BaseModel):
    id: int
    invent_id: str
    longitude: float
    latitude: float
    tambon: Optional[str]
    district: Optional[str]
    province: Optional[str]

class PredictionResponse(BaseModel):
    id: int
    location_id: int
    invent_id: str
    longitude: float
    latitude: float
    probability: float
    risk_level: str
    risk_color: str
    status: str
    predicted_at: datetime
    details: dict

class StatsResponse(BaseModel):
    total_locations: int
    danger_count: int
    warning_count: int
    normal_count: int
    last_update: Optional[datetime]

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🏔️ Landslide Early Warning System API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "database": "connected",
        "model": "loaded"
    }

@app.get("/api/locations", response_model=List[LocationResponse])
async def get_locations():
    """ดึงรายการจุดติดตามทั้งหมด"""
    try:
        locations = db.get_all_locations()
        return [
            LocationResponse(
                id=loc.id,
                invent_id=loc.invent_id,
                longitude=loc.longitude,
                latitude=loc.latitude,
                tambon=loc.tambon,
                district=loc.district,
                province=loc.province
            )
            for loc in locations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predictions/latest")
async def get_latest_predictions(limit: int = 100):
    """ดึงผลทำนายล่าสุด"""
    try:
        predictions = db.get_latest_predictions(limit=limit)
        locations = {loc.id: loc for loc in db.get_all_locations()}
        
        results = []
        for pred in predictions:
            loc = locations.get(pred.location_id)
            if loc:
                results.append({
                    "id": pred.id,
                    "location_id": pred.location_id,
                    "invent_id": pred.invent_id,
                    "longitude": loc.longitude,
                    "latitude": loc.latitude,
                    "tambon": loc.tambon,
                    "district": loc.district,
                    "province": loc.province,
                    "probability": pred.probability,
                    "risk_level": pred.risk_level,
                    "risk_color": pred.risk_color,
                    "status": pred.status,
                    "predicted_at": pred.predicted_at,
                    "details": pred.features
                })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predictions/by-risk/{risk_level}")
async def get_predictions_by_risk(risk_level: str):
    """ดึงผลทำนายตาม risk level (NORMAL, WARNING, DANGER)"""
    try:
        predictions = db.get_predictions_by_risk(risk_level.upper())
        locations = {loc.id: loc for loc in db.get_all_locations()}
        
        results = []
        for pred in predictions:
            loc = locations.get(pred.location_id)
            if loc:
                results.append({
                    "id": pred.id,
                    "location_id": pred.location_id,
                    "invent_id": pred.invent_id,
                    "longitude": loc.longitude,
                    "latitude": loc.latitude,
                    "probability": pred.probability,
                    "risk_level": pred.risk_level,
                    "risk_color": pred.risk_color,
                    "status": pred.status,
                    "predicted_at": pred.predicted_at
                })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predictions/location/{location_id}")
async def get_prediction_history(location_id: int, limit: int = 10):
    """ดึงประวัติการทำนายของจุดหนึ่งๆ"""
    try:
        predictions = db.get_prediction_by_location(location_id, limit=limit)
        return [
            {
                "id": pred.id,
                "probability": pred.probability,
                "risk_level": pred.risk_level,
                "status": pred.status,
                "predicted_at": pred.predicted_at,
                "features": pred.features
            }
            for pred in predictions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats", response_model=StatsResponse)
async def get_statistics():
    """ดึงสถิติภาพรวม"""
    try:
        all_locations = db.get_all_locations()
        latest_preds = db.get_latest_predictions(limit=len(all_locations))
        
        danger = len([p for p in latest_preds if p.risk_level == 'DANGER'])
        warning = len([p for p in latest_preds if p.risk_level == 'WARNING'])
        normal = len([p for p in latest_preds if p.risk_level == 'NORMAL'])
        
        last_update = latest_preds[0].predicted_at if latest_preds else None
        
        return StatsResponse(
            total_locations=len(all_locations),
            danger_count=danger,
            warning_count=warning,
            normal_count=normal,
            last_update=last_update
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update")
async def trigger_update(background_tasks: BackgroundTasks):
    """
    Trigger manual update (admin only)
    รันการอัปเดตในพื้นหลัง
    """
    try:
        background_tasks.add_task(scheduler.run_now)
        return {
            "message": "Update started in background",
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend
@app.get("/dashboard")
async def serve_dashboard():
    """Serve dashboard HTML"""
    return FileResponse("frontend/index.html")

# Startup event
@app.on_event("startup")
async def startup_event():
    """เริ่ม scheduler เมื่อ server start"""
    print("\n🚀 Starting Landslide Warning System...")
    scheduler.start()
    print("✅ System ready!\n")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """หยุด scheduler เมื่อ server shutdown"""
    print("\n🛑 Shutting down...")
    scheduler.stop()
    db.close()
    print("✅ Shutdown complete\n")


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8000))
    
    print(f"\n{'='*60}")
    print(f"🏔️  Landslide Early Warning System")
    print(f"{'='*60}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📊 Dashboard: http://{host}:{port}/dashboard")
    print(f"📖 API Docs: http://{host}:{port}/docs")
    print(f"{'='*60}\n")
    
    uvicorn.run(app, host=host, port=port)
