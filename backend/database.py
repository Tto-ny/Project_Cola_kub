import os
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv(override=True)

# Use local SQLite database for maximum performance (no network latency)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "landslide.db")
db_url = f"sqlite:///{DB_PATH}"

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

class AlertHistory(Base):
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    longitude = Column(Float, index=True)
    latitude = Column(Float, index=True)
    risk = Column(String(50), index=True)
    probability = Column(Float)
    timestamp = Column(String(100), index=True)  # ISO format string for easy querying
    properties = Column(JSON, nullable=True)     # Store some properties if needed

class Officer(Base):
    __tablename__ = "officers"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="officer")

# Auto-create tables on import
Base.metadata.create_all(bind=engine)

# Dependency to get DB session in FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
