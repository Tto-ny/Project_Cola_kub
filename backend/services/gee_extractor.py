import ee
import json
import sys
import math
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv

load_dotenv()

def initialize_gee():
    try:
        print("Initializing Google Earth Engine...")
        project_id = os.getenv("GEE_PROJECT_ID")
        if not project_id:
            raise ValueError("GEE_PROJECT_ID is not set in the environment.")
        ee.Initialize(project=project_id)
        print("GEE Initialized successfully.")
    except Exception as e:
        print(f"Error initializing GEE: {e}")
        sys.exit(1)

def generate_local_grid():
    """
    Generate a regular 500x500m grid covering Nan Province.
    Returns list of (lon, lat, polygon) for each cell center.
    """
    # Bounding box
    min_lon, min_lat = 100.248301, 17.902120
    max_lon, max_lat = 101.541031, 19.726141
    
    # 500m steps in degrees at ~18.8° latitude
    center_lat = (min_lat + max_lat) / 2
    step_lon = 500.0 / (111320.0 * math.cos(math.radians(center_lat)))  # ~0.00472°
    step_lat = 500.0 / 110540.0  # ~0.00452°
    half_w = step_lon / 2
    half_h = step_lat / 2
    
    grid = []
    lat = min_lat + half_h
    while lat < max_lat:
        lon = min_lon + half_w
        while lon < max_lon:
            polygon = [
                [lon - half_w, lat - half_h],
                [lon + half_w, lat - half_h],
                [lon + half_w, lat + half_h],
                [lon - half_w, lat + half_h],
                [lon - half_w, lat - half_h],
            ]
            grid.append((lon, lat, polygon))
            lon += step_lon
        lat += step_lat
    
    return grid

def build_combined_image():
    """Build combined GEE image with all required features."""
    bbox = ee.Geometry.Rectangle([100.248301, 17.902120, 101.541031, 19.726141])
    
    # DEM
    dem = ee.Image("NASA/NASADEM_HGT/001").select('elevation')
    slope = ee.Terrain.slope(dem).rename('Slope')
    aspect = ee.Terrain.aspect(dem).rename('Aspect')
    
    # TWI proxy
    slope_rad = slope.multiply(math.pi).divide(180)
    tan_slope = slope_rad.tan().max(0.001)
    twi = ee.Image.constant(1).divide(tan_slope).log().rename('TWI')
    
    # Land Cover
    landcover = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').rename('MODIS_LC')
    
    # Soil
    soil = ee.Image("OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02").select('b0').rename('Soil_Type')
    
    # Sentinel-2 NDVI/NDWI
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    def mask_s2_clouds(image):
        qa = image.select('QA60')
        mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
        return image.updateMask(mask).divide(10000)
    
    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterBounds(bbox)
          .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
          .map(mask_s2_clouds)
          .median())
    
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndwi = s2.normalizedDifference(['B3', 'B8']).rename('NDWI')
    ndvi_filled = ndvi.unmask(ndvi.focal_mean(3, 'circle', 'pixels')).unmask(0)
    ndwi_filled = ndwi.unmask(ndwi.focal_mean(3, 'circle', 'pixels')).unmask(0)
    
    # Correct Distance to Road (in meters)
    # Using GRIP4 Global Roads dataset or a simple distance function
    roads = ee.FeatureCollection("projects/sat-io/open-datasets/GRIP4/GlobalRoads")
    # Calculate distance to nearest road in meters
    distance_to_road = roads.distance(searchRadius=10000, maxError=50).rename('Distance_to_Road')
    
    # Combine
    combined = (dem.rename('Elevation')
                .addBands([slope, aspect, twi, landcover, soil,
                           ndvi_filled, ndwi_filled, distance_to_road]))
    return combined.unmask(0)

def extract_gee_data(progress_callback=None):
    """
    Generate full regular 500x500m grid and extract GEE features in chunks.
    progress_callback: A function(current_chunk, total_chunks, current_valid)
    """
    initialize_gee()
    
    # Step 1: Generate the local grid
    print("Generating regular 500x500m grid over Nan Province...")
    grid = generate_local_grid()
    total = len(grid)
    print(f"Generated {total} grid cells.")
    
    # Step 2: Build the combined GEE image
    print("Building combined GEE image...")
    combined_img = build_combined_image()
    print("GEE image ready.\n")
    
    # Step 3: Extract in chunks
    CHUNK_SIZE = 2000
    num_chunks = math.ceil(total / CHUNK_SIZE)
    feature_names = ['Elevation', 'Slope', 'Aspect', 'TWI', 'MODIS_LC',
                     'Soil_Type', 'NDVI', 'NDWI', 'Distance_to_Road']
    
    all_valid = []
    nodata_total = 0
    
    for chunk_idx in range(num_chunks):
        if progress_callback:
            progress_callback(chunk_idx + 1, num_chunks, len(all_valid))
            
        start = chunk_idx * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, total)
        chunk = grid[start:end]
        
        print(f"Fetching Grid Chunk {chunk_idx+1}/{num_chunks} (cells {start+1}-{end}/{total})...")
        
        # Create ee.FeatureCollection of point geometries for this chunk
        ee_features = []
        for lon, lat, polygon in chunk:
            ee_features.append(ee.Feature(ee.Geometry.Point([lon, lat])))
        
        ee_fc = ee.FeatureCollection(ee_features)
        
        # Extract values at each point
        try:
            results = combined_img.sampleRegions(
                collection=ee_fc,
                scale=500,
                geometries=True
            )
            features = results.getInfo()['features']
        except Exception as e:
            print(f"  ERROR on chunk {chunk_idx+1}: {e}")
            print(f"  Skipping this chunk...")
            continue
        
        # Process results
        for i, (feat, grid_cell) in enumerate(zip(features, chunk)):
            props = feat.get('properties', {})
            lon, lat, polygon = grid_cell
            
            has_nodata = False
            for f_name in feature_names:
                val = props.get(f_name)
                if val is None or val == -9999 or val == -9999.0:
                    nodata_total += 1
                    has_nodata = True
                    cell_num = start + i + 1
                    print(f"  WARNING NoData | Feature: {f_name} | Cell: {cell_num} | Lon={lon:.4f} Lat={lat:.4f}")
            
            if not has_nodata:
                slope_val = props.get('Slope', 0) or 0
                if slope_val > 25:
                    risk = 'High'
                elif slope_val > 12:
                    risk = 'Medium'
                else:
                    risk = 'Low'
                
                all_valid.append({
                    'polygon': polygon,
                    'properties': props,
                    'risk': risk
                })
        
        print(f"  Chunk {chunk_idx+1} done. Valid so far: {len(all_valid)}")
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"EXTRACTION COMPLETE")
    print(f"   Total grid cells     : {total}")
    print(f"   Valid cells          : {len(all_valid)}")
    print(f"   NoData warnings      : {nodata_total}")
    print(f"   High risk            : {sum(1 for d in all_valid if d['risk'] == 'High')}")
    print(f"   Medium risk          : {sum(1 for d in all_valid if d['risk'] == 'Medium')}")
    print(f"   Low risk             : {sum(1 for d in all_valid if d['risk'] == 'Low')}")
    print(f"{'=' * 60}")
    
    output_path = "extracted_grid_data.json"
    with open(output_path, 'w') as f:
        json.dump(all_valid, f)
    print(f"Data saved to {output_path}")
    
    return all_valid
