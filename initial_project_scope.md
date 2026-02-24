# Initial Project Scope (Detailed Archive)
*The original roadmap defined during the first prompt (Phase 0)*

## 1. System Architecture
- **Web App**: React (Vite) + MapLibre GL JS + Deck.gl.
- **API**: FastAPI (Python) for processing and model serving.
- **Data Source**: Google Earth Engine (GEE) as the primary GIS data backbone.
- **Model Layer**: Random Forest Normalized model trained for Nan Province landslide risk.

## 2. Phase 1: Grid Generation & Feature Extraction
- **Spatial Scope**: Nan Province, Thailand (BBox: 100.248, 17.902 to 101.541, 19.726).
- **Core Grid**: 500m x 500m grid cells.
- **GEE Bands (Planned)**:
  - **Topography**: NASADEM (Elevation, Slope, Aspect, TWI calculation).
  - **Land Surface**: WorldCover v100/v200.
  - **Vegetation/Moisture**: Sentinel-2 MSIL1C Median Composites (NDVI, NDWI).
  - **Infrastructure**: Distance to Roads.
  - **Soil**: USDA Soil Texture classes.
- **Handling**: Strict NoData (-9999) validation and cloud masking (QA60 band).

## 3. Phase 2: Dashboard UI
- **Map View**: Dark-themed base map with interactive risk GridLayer.
- **Components**: Sidebar with buttons for data extraction and prediction manual triggers.
- **Features**: Tooltips showing Slope, Elevation, and NDVI on hover/click.

## 4. Phase 3: Prediction & Weather
- **Intelligence**: Integration of `.pkl` model and scaler files (`best_model_Random_Forest_Normalized.pkl`).
- **Rainfall**: Real-time precipitation prediction (Open-Meteo) to update risk levels dynamically.
- **Scheduler**: Automatic background tasks to refresh predictions.
