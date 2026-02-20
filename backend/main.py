from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.gee_extractor import extract_gee_data
from services.spatial_search import search_location, get_all_districts
from services.predictor import predict_risk, predict_batch, load_model
from services.rainfall import fetch_rainfall
from services.chatbot import chat as chatbot_answer
import json, os, math
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(title="Landslide Early Warning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

extraction_status = {"status": "idle", "message": "Ready"}
alert_logs = []

@app.on_event("startup")
def on_startup():
    load_model()

# ── GEE Extraction ──
def run_extraction():
    global extraction_status
    extraction_status = {"status": "running", "message": "Extracting GEE data..."}
    try:
        result = extract_gee_data()
        extraction_status = {"status": "done", "message": f"Done. {len(result)} cells.", "count": len(result)}
        alert_logs.insert(0, {"id": len(alert_logs)+1, "timestamp": datetime.now().isoformat(),
            "type": "extraction", "message": f"GEE extraction: {len(result)} cells", "severity": "info"})
    except Exception as e:
        extraction_status = {"status": "error", "message": str(e)}
        alert_logs.insert(0, {"id": len(alert_logs)+1, "timestamp": datetime.now().isoformat(),
            "type": "error", "message": f"Extraction failed: {str(e)[:100]}", "severity": "error"})

@app.get("/")
def read_root():
    return {"message": "Landslide Early Warning API"}

@app.post("/api/extract_grid")
async def trigger_extraction(bg: BackgroundTasks):
    bg.add_task(run_extraction)
    return {"status": "started", "message": "GEE extraction started."}

@app.get("/api/status")
def get_status():
    return extraction_status

@app.get("/api/grid_data")
def get_grid_data():
    path = "extracted_grid_data.json"
    if os.path.exists(path):
        with open(path, 'r') as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content=[])

# ── Spatial Search ──
@app.get("/api/search")
def search(q: str = Query("", min_length=1)):
    return search_location(q)

@app.get("/api/districts")
def list_districts():
    return get_all_districts()

# ── Alert Logs ──
@app.get("/api/alerts")
def get_alerts():
    return alert_logs[:50]

# ── Rainfall ──
@app.get("/api/rainfall")
def get_rainfall(lat: float = 18.8, lon: float = 100.78, hours: int = 24):
    return fetch_rainfall(lat=lat, lon=lon, hours=hours)

# ── Manual Predict Now ──
@app.post("/api/predict_now")
def predict_now():
    path = "extracted_grid_data.json"
    if not os.path.exists(path):
        return {"error": "No grid data. Run extraction first."}
    
    with open(path, 'r') as f:
        grid_data = json.load(f)
    
    rain = fetch_rainfall(lat=18.8, lon=100.78, hours=24)
    rainfall_mm = rain.get("total_mm", 0)
    
    results = predict_batch(grid_data, rainfall_mm)
    
    with open("predicted_grid_data.json", 'w') as f:
        json.dump(results, f)
    
    summary = {
        "total": len(results),
        "high": sum(1 for r in results if r['risk'] == 'High'),
        "medium": sum(1 for r in results if r['risk'] == 'Medium'),
        "low": sum(1 for r in results if r['risk'] == 'Low'),
        "rainfall_mm": rainfall_mm,
        "timestamp": datetime.now().isoformat()
    }
    
    alert_logs.insert(0, {"id": len(alert_logs)+1, "timestamp": datetime.now().isoformat(),
        "type": "prediction", "message": f"Predicted {summary['total']} cells. Rain={rainfall_mm}mm. High={summary['high']}", 
        "severity": "warning" if summary['high'] > 0 else "info"})
    
    return {"status": "done", "summary": summary}

@app.get("/api/predicted_data")
def get_predicted_data():
    path = "predicted_grid_data.json"
    if os.path.exists(path):
        with open(path, 'r') as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content=[])

# ── What-If Simulation (uses cached grid data, no GEE call) ──
class WhatIfRequest(BaseModel):
    lat: float
    lon: float
    rainfall: float = 50.0

@app.post("/api/whatif")
def whatif_simulation(req: WhatIfRequest):
    """Find nearest grid cell from cached data, apply custom rainfall, predict."""
    path = "extracted_grid_data.json"
    if not os.path.exists(path):
        return {"error": "No grid data. Run extraction first."}
    
    with open(path, 'r') as f:
        grid_data = json.load(f)
    
    # Find nearest cell
    best = None
    best_dist = float('inf')
    for cell in grid_data:
        poly = cell.get('polygon', [])
        if not poly or len(poly) < 4:
            continue
        # Centroid of polygon
        cx = sum(p[0] for p in poly[:4]) / 4
        cy = sum(p[1] for p in poly[:4]) / 4
        dist = math.sqrt((cx - req.lon)**2 + (cy - req.lat)**2)
        if dist < best_dist:
            best_dist = dist
            best = cell
    
    if not best:
        return {"error": "No nearby grid cell found"}
    
    props = dict(best.get('properties', {}))
    props['Rainfall'] = req.rainfall
    
    prediction = predict_risk(props)
    
    return {
        "coordinates": [req.lon, req.lat],
        "rainfall_input": req.rainfall,
        "features": props,
        "prediction": prediction,
        "timestamp": datetime.now().isoformat()
    }

# ── Chatbot ──
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    answer = chatbot_answer(req.message)
    return {"answer": answer}

# ── Scheduler ──
def scheduled_prediction():
    print(f"\n[SCHEDULER] Running prediction at {datetime.now()}")
    predict_now()

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_prediction, 'interval', hours=6, id='predict_6h')
scheduler.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
