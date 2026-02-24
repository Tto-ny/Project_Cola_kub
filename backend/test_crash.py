import json
import sys
import os
import traceback

sys.path.append(r'c:\Users\nongt\OneDrive\Desktop\model')
sys.path.append(r'c:\Users\nongt\OneDrive\Desktop\model\backend')

try:
    from services.rainfall_pipeline import apply_spatial_interpolation
    from modifier_data import predict_landslide_batch
    import services.predictor as predictor

    print("Loading data...")
    with open(r'c:\Users\nongt\OneDrive\Desktop\model\backend\extracted_grid_data.json', 'r') as f:
        grid_data = json.load(f)
        
    print("Interpolating...")
    grid_data = apply_spatial_interpolation(grid_data[:500])
    
    print("Loading model...")
    predictor.load_model()
    
    print("Predict...")
    res = predict_landslide_batch(grid_data, predictor._model, predictor._scaler)
    print("Done")
except Exception as e:
    traceback.print_exc()
