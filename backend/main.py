from fastapi import FastAPI, BackgroundTasks, Query, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, GridCell, SessionLocal, Officer, HistoricalLandslidePoint
from auth import verify_password, create_access_token, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from services.gee_extractor import extract_gee_data
from services.spatial_search import search_location, get_all_districts
from services.predictor import predict_risk, predict_batch, load_model
from services.rainfall import fetch_rainfall
from services.chatbot import chat as chatbot_answer
from services.rainfall_pipeline import apply_spatial_interpolation
import json, os, math, sys
from datetime import datetime, timedelta

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
    from database import Base, engine, SessionLocal, HistoricalLandslidePoint
    Base.metadata.create_all(bind=engine)
    load_model()
    
    # Auto-load historical points if table is empty
    db = SessionLocal()
    try:
        count = db.query(HistoricalLandslidePoint).count()
        if count == 0:
            print("[STARTUP] No historical points found. Auto-loading from CSVs...")
            from load_historical_points import load as load_historical_data
            load_historical_data()
    except Exception as e:
        print(f"[STARTUP] Error auto-loading historical points: {e}")
    finally:
        db.close()

# ── Authentication ──
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(Officer).filter(Officer.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/api/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Officer).filter(Officer.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me")
def read_users_me(current_user: Officer = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}

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
async def trigger_extraction(bg: BackgroundTasks, current_user: Officer = Depends(get_current_user)):
    bg.add_task(run_extraction)
    return {"status": "started", "message": "GEE extraction started."}

@app.get("/api/status")
def get_status():
    return extraction_status

@app.get("/api/grid_data")
def get_grid_data(db: Session = Depends(get_db)):
    cells = db.query(GridCell).all()
    result = []
    for c in cells:
        poly = c.polygon if isinstance(c.polygon, list) else json.loads(c.polygon) if c.polygon else []
        props = c.properties if isinstance(c.properties, dict) else json.loads(c.properties) if c.properties else {}
        result.append({
            "polygon": poly,
            "properties": props,
            "risk": c.risk
        })
    return JSONResponse(content=result)

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
def predict_now(db: Session = Depends(get_db), current_user: Officer = Depends(get_current_user)):
    # For performance, avoid instantiating 117k SQLAlchemy objects. Query specific columns instead.
    from sqlalchemy.orm import load_only
    cells = db.query(GridCell).options(load_only(GridCell.id, GridCell.latitude, GridCell.longitude, GridCell.polygon, GridCell.properties, GridCell.risk)).all()
    
    if not cells:
        return {"error": "No grid data in database. Run extraction first."}
    
    # Reconstruct grid_data format for the pipeline
    grid_data = []
    for c in cells:
        grid_data.append({
            "id": c.id,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "polygon": c.polygon,
            "properties": c.properties,
            "risk": c.risk
        })
    
    # 1. Fetch Spatial Rainfall & Interpolate 10 Days (117k points)
    print("Applying spatial interpolation from Open-Meteo...")
    grid_data = apply_spatial_interpolation(grid_data)
    
    # 2. Vectorized Feature Engineering & Prediction (Pandas)
    if predictor_service._model is None:
        predictor_service.load_model()
        
    print("Running vectorized prediction batch...")
    results = predict_landslide_batch(grid_data, predictor_service._model, predictor_service._scaler)
    
    # Save back to Postgres DB
    print("Saving predictions to database...")
    update_mappings = []
    import json
    for i, row in enumerate(results):
        # Handle null grids when extracting
        base_id = cells[i].id
        grid_id = base_id if base_id else f"mock_{i}"

        update_mappings.append({
            "id": grid_id,
            "risk": str(row.get('risk', 'Low')),
            "prediction_probability": float(row.get('probability', 0.0)),
            "properties": json.dumps(row.get('properties', {}))
        })
        
    # Single-transaction bulk update (SQLite = instant, no network overhead)
    print("Executing bulk SQL update (single transaction)...")
    import time
    t_start = time.time()
    
    from sqlalchemy import text
    stmt = text("""
        UPDATE grid_data 
        SET properties = :properties, 
            risk = :risk, 
            prediction_probability = :prediction_probability 
        WHERE id = :id
    """)
    
    conn = db.connection()
    conn.execute(stmt, update_mappings)
    
    # Save High/Medium alerts to History Log
    from database import AlertHistory
    history_objects = []
    current_time = datetime.now().isoformat()
    for update in update_mappings:
        if update["risk"] in ["High", "Medium"]:
            # Find corresponding lat/lon from cells array (mapped by ID)
            # Since cells order might not map 1:1 if mock_id used, let's use the index safely
            idx = int(str(update["id"]).replace("mock_", "")) if str(update["id"]).startswith("mock_") else None
            # If base_id was used, find index in cells
            c = next((c for c in cells if str(c.id) == str(update["id"])), None)
            if c:
                history_objects.append(
                    AlertHistory(
                        longitude=c.longitude,
                        latitude=c.latitude,
                        risk=update["risk"],
                        probability=update["prediction_probability"],
                        timestamp=current_time,
                        properties=update["properties"] # json string
                    )
                )

    if history_objects:
        db.add_all(history_objects)
        print(f"Saved {len(history_objects)} alerts to AlertHistory.")

    db.commit()
    
    elapsed = time.time() - t_start
    print(f"[DONE] Saved {len(update_mappings)} predictions and {len(history_objects)} history records in {elapsed:.2f} seconds")

        
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
def get_predicted_data(db: Session = Depends(get_db)):
    from sqlalchemy import text
    conn = db.connection()
    # Use raw SQL to completely bypass ORM overhead for 117k records (huge performance boost)
    stmt = text("SELECT polygon, properties, risk, prediction_probability, latitude, longitude FROM grid_data")
    result = conn.execute(stmt).fetchall()
    
    # Format the raw tuples into a list of dicts for JSON serialization
    # SQLite returns JSON columns as strings, so we need to parse them
    formatted_result = []
    for row in result:
        poly = row[0] if isinstance(row[0], (list, dict)) else json.loads(row[0]) if row[0] else []
        props = row[1] if isinstance(row[1], (list, dict)) else json.loads(row[1]) if row[1] else {}
        formatted_result.append({
            "polygon": poly,
            "properties": props,
            "risk": row[2],
            "probability": float(row[3]) if row[3] is not None else 0.0,
            "latitude": float(row[4]) if row[4] is not None else 0.0,
            "longitude": float(row[5]) if row[5] is not None else 0.0
        })
    return JSONResponse(content=formatted_result)

@app.get("/api/alert_history")
def get_alert_history(start_date: str = None, end_date: str = None, db: Session = Depends(get_db)):
    from database import AlertHistory
    query = db.query(AlertHistory)
    
    if start_date:
        query = query.filter(AlertHistory.timestamp >= start_date)
    if end_date:
        if len(end_date) == 10:  # just YYYY-MM-DD
            query = query.filter(AlertHistory.timestamp <= f"{end_date}T23:59:59")
        else:
            query = query.filter(AlertHistory.timestamp <= end_date)
            
    history = query.order_by(AlertHistory.timestamp.desc()).all()
    
    result = []
    for h in history:
        result.append({
            "id": h.id,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "risk": h.risk,
            "probability": h.probability,
            "timestamp": h.timestamp,
            "properties": json.loads(h.properties) if h.properties and isinstance(h.properties, str) else (h.properties or {})
        })
    return JSONResponse(content=result)

# ── What-If Simulation (uses cached grid data, no GEE call) ──
class WhatIfRequest(BaseModel):
    lat: float
    lon: float
    rainfall_days: list[float]  # Array of 10 days [Day10, Day9, ..., Day1]

@app.post("/api/whatif")
def whatif_simulation(req: WhatIfRequest, db: Session = Depends(get_db)):
    """Find nearest grid cell via SQL, apply custom rainfall, predict."""
    
    # Use SQL math to find the closest Euclidean distance directly in Postgres
    # Use multiplication instead of func.pow() for SQLite compatibility
    closest_cell = db.query(GridCell).order_by(
        (GridCell.longitude - req.lon) * (GridCell.longitude - req.lon) + 
        (GridCell.latitude - req.lat) * (GridCell.latitude - req.lat)
    ).first()
    
    if not closest_cell:
        return {"error": "No nearby grid cell found"}
    
    props = dict(closest_cell.properties)
    
    # Map simulator rainfall from 10-day array
    # Frontend array is [Day10, Day9, Day8 ... Day1] based on standard display
    # Let's map it backwards so idx 9 -> Day 1, idx 8 -> Day 2, etc.
    if req.rainfall_days and len(req.rainfall_days) == 10:
        for idx, val in enumerate(req.rainfall_days):
            day_num = 10 - idx
            props[f'CHIRPS_Day_{day_num}'] = val
    else:
        # Fallback if somehow array isn't 10
        for i in range(1, 11):
            props[f'CHIRPS_Day_{i}'] = 0
            
    # We must format it as a list to use the vectorized batch predictor
    test_cell = {'polygon': closest_cell.polygon, 'properties': props}
    if predictor_service._model is None:
        predictor_service.load_model()
        
    result_batch = predict_landslide_batch([test_cell], predictor_service._model, predictor_service._scaler)
    prediction = {
        "risk": result_batch[0].get('risk', 'Low'),
        "probability": result_batch[0].get('probability', 0)
    }
    
    return {
        "coordinates": [req.lon, req.lat],
        "rainfall_total": sum(req.rainfall_days) if req.rainfall_days else 0,
        "features": props,
        "prediction": prediction,
        "timestamp": datetime.now().isoformat()
    }

# ── Historical Landslide Points ──
@app.get("/api/historical_points")
def get_historical_points(db: Session = Depends(get_db)):
    points = db.query(HistoricalLandslidePoint).all()
    return JSONResponse(content=[
        {
            "latitude": p.latitude,
            "longitude": p.longitude,
            "tambon": p.tambon,
            "district": p.district,
            "source": p.source,
        }
        for p in points
    ])

# ── Chatbot ──
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    answer = chatbot_answer(req.message, db)
    return {"answer": answer}

# ── Scheduler ──
def scheduled_prediction():
    print(f"\n[SCHEDULER] Running prediction at {datetime.now()}")
    db = SessionLocal()
    try:
        predict_now(db)
    except Exception as e:
        print(f"[SCHEDULER] Error during prediction: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_prediction, 'interval', hours=6, id='predict_6h')
scheduler.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
