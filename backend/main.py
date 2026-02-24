from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.gee_extractor import extract_gee_data
from services.spatial_search import search_location, get_all_districts
from services.predictor import predict_risk, predict_batch, load_model
from services.rainfall import fetch_rainfall
from services.chatbot import chat as chatbot_answer
from services.rainfall_pipeline import apply_spatial_interpolation
import json, os, math, sys
from datetime import datetime

# Add root dir to path so we can import modifier_data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modifier_data import predict_landslide_batch
import services.predictor as predictor_service
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
    extraction_status = {"status": "running", "message": "Starting GEE extraction..."}
    
    def update_progress(current_chunk, total_chunks, valid_cells):
        global extraction_status
        percentage = int((current_chunk / total_chunks) * 100)
        extraction_status = {
            "status": "running", 
            "message": f"Downloading GEE: {percentage}% (Chunk {current_chunk}/{total_chunks}) | Valid: {valid_cells} cells"
        }
        
    try:
        result = extract_gee_data(progress_callback=update_progress)
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
    
    # 1. Fetch Spatial Rainfall & Interpolate 10 Days (117k points)
    print("Applying spatial interpolation from Open-Meteo...")
    grid_data = apply_spatial_interpolation(grid_data)
    
    # 2. Vectorized Feature Engineering & Prediction (Pandas)
    if predictor_service._model is None:
        predictor_service.load_model()
        
    print("Running vectorized prediction batch...")
    results = predict_landslide_batch(grid_data, predictor_service._model, predictor_service._scaler)
    
    with open("predicted_grid_data.json", 'w') as f:
        json.dump(results, f)
    
    # Calculate Summary
    rainfall_sample = results[0]['properties'].get('CHIRPS_Day_1', 0) if results else 0
    summary = {
        "total": len(results),
        "high": sum(1 for r in results if r['risk'] == 'High'),
        "medium": sum(1 for r in results if r['risk'] == 'Medium'),
        "low": sum(1 for r in results if r['risk'] == 'Low'),
        "rainfall_mm": round(rainfall_sample, 2), # Sample point for the dashboard
        "timestamp": datetime.now().isoformat()
    }
    
    alert_logs.insert(0, {"id": len(alert_logs)+1, "timestamp": datetime.now().isoformat(),
        "type": "prediction", "message": f"Predicted {summary['total']} cells. Sample Rain={summary['rainfall_mm']}mm. High={summary['high']}", 
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
    path = "predicted_grid_data.json"
    if not os.path.exists(path):
        path = "extracted_grid_data.json" # Fallback if never predicted
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
        cx = sum(p[0] for p in poly[:4]) / 4
        cy = sum(p[1] for p in poly[:4]) / 4
        dist = math.sqrt((cx - req.lon)**2 + (cy - req.lat)**2)
        if dist < best_dist:
            best_dist = dist
            best = cell
    
    if not best:
        return {"error": "No nearby grid cell found"}
    
    props = dict(best.get('properties', {}))
    
    # Map simulator rainfall: Spread over 7 days so Prior Soil Saturation triggers correctly
    daily_rain = req.rainfall / 7.0
    for i in range(1, 8):
        props[f'CHIRPS_Day_{i}'] = daily_rain
    for i in range(8, 11):
        props[f'CHIRPS_Day_{i}'] = 0
        
    # We must format it as a list to use the vectorized batch predictor
    test_cell = {'polygon': best.get('polygon', []), 'properties': props}
    if predictor_service._model is None:
        predictor_service.load_model()
        
    result_batch = predict_landslide_batch([test_cell], predictor_service._model, predictor_service._scaler)
    prediction = {
        "risk": result_batch[0].get('risk', 'Low'),
        "probability": result_batch[0].get('probability', 0)
    }
    
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
