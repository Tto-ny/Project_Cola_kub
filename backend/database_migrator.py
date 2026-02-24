import json
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

load_dotenv(override=True)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("❌ ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

# SQLAlchemy requires postgresql:// instead of postgres:// (just in case)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

print("Connecting to Supabase Database...")
engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class GridCell(Base):
    __tablename__ = "grid_data"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    longitude = Column(Float, index=True)
    latitude = Column(Float, index=True)
    polygon = Column(JSONB)       # We store the polygon vertices as a JSON array
    properties = Column(JSONB)    # Stores Elevation, Slope, NDVI, etc
    risk = Column(String(50))     # 'High', 'Medium', 'Low'
    prediction_probability = Column(Float, nullable=True) # E.g., 0.85
    
def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def migrate_data():
    print("⏳ Creating 'grid_data' table in Supabase...")
    Base.metadata.drop_all(bind=engine) # Drop old table if exists
    Base.metadata.create_all(bind=engine)
    print("✅ Table created successfully.")
    
    print("📂 Loading extracted_grid_data.json from local disk...")
    # Load the latest json
    try:
        if os.path.exists("predicted_grid_data.json"):
            file_to_load = "predicted_grid_data.json"
        else:
            file_to_load = "extracted_grid_data.json"
            
        with open(file_to_load, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} grid cells from {file_to_load}.")
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        return

    db = SessionLocal()
    
    # We will insert in chunks of 5000 to avoid blowing up memory/network limits
    CHUNK_SIZE = 5000
    total_cells = len(data)
    inserted = 0
    
    print(f"🚀 Starting migration of {total_cells} cells in chunks of {CHUNK_SIZE}...")
    
    try:
        for idx, chunk in enumerate(chunker(data, CHUNK_SIZE)):
            db_cells = []
            for item in chunk:
                # Calculate center point for indexed querying
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
            
        print("🎉 Migration Complete! All 117,000 cells are now in Supabase PostgreSQL.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Database error during insertion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
