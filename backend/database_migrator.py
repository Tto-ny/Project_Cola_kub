import json
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# Use local SQLite database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "landslide.db")
db_url = f"sqlite:///{DB_PATH}"

print(f"Connecting to Local SQLite: {DB_PATH}")
engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class GridCell(Base):
    __tablename__ = "grid_data"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    longitude = Column(Float, index=True)
    latitude = Column(Float, index=True)
    polygon = Column(JSON)        # Polygon vertices as JSON array
    properties = Column(JSON)     # Elevation, Slope, NDVI, etc.
    risk = Column(String(50))     # 'High', 'Medium', 'Low'
    prediction_probability = Column(Float, nullable=True)

class Officer(Base):
    __tablename__ = "officers"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="officer")
    
def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def migrate_data():
    print("[MIGRATE] Creating tables in local SQLite...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[MIGRATE] Tables created successfully.")
    
    print("[MIGRATE] Loading grid data JSON from local disk...")
    try:
        if os.path.exists("predicted_grid_data.json"):
            file_to_load = "predicted_grid_data.json"
        else:
            file_to_load = "extracted_grid_data.json"
            
        with open(file_to_load, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[MIGRATE] Loaded {len(data)} grid cells from {file_to_load}.")
    except Exception as e:
        print(f"[MIGRATE] ERROR - Failed to load JSON: {e}")
        return

    db = SessionLocal()
    
    # Insert in chunks of 5000
    CHUNK_SIZE = 5000
    total_cells = len(data)
    inserted = 0
    
    print(f"[MIGRATE] Starting migration of {total_cells} cells in chunks of {CHUNK_SIZE}...")
    
    try:
        for idx, chunk in enumerate(chunker(data, CHUNK_SIZE)):
            db_cells = []
            for item in chunk:
                poly = item.get('polygon', [])
                if poly and len(poly) > 0:
                    cx = sum(p[0] for p in poly[:4]) / 4
                    cy = sum(p[1] for p in poly[:4]) / 4
                else:
                    cx, cy = 0.0, 0.0
                    
                cell = GridCell(
                    longitude=cx,
                    latitude=cy,
                    polygon=poly,
                    properties=item.get('properties', {}),
                    risk=item.get('risk', 'Low'),
                    prediction_probability=item.get('probability', 0.0)
                )
                db_cells.append(cell)
            
            db.bulk_save_objects(db_cells)
            db.commit()
            
            inserted += len(chunk)
            print(f"   -> Inserted {inserted}/{total_cells} cells...")
            
        # Also create default admin officer if not exists
        from auth import get_password_hash
        existing = db.query(Officer).filter(Officer.username == "admin").first()
        if not existing:
            admin = Officer(username="admin", password_hash=get_password_hash("nanlandslide2024"), role="admin")
            db.add(admin)
            db.commit()
            print("[MIGRATE] Created default admin user (admin/nanlandslide2024)")
        
        print(f"[MIGRATE] Migration Complete! All {total_cells} cells are now in local SQLite.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Database error during insertion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
