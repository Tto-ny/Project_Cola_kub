"""
Load historical landslide points from CSV files into the database.

Sources:
  1. cleaned_data.csv            → All rows (already Nan province)
  2. Landslide_Final_Cleaned_V2.csv → Filtered: PROVINCE='น่าน' AND Geohaz_E=1

Run:  cd backend && py load_historical_points.py
"""

import os
import sys
import pandas as pd
from database import engine, SessionLocal, HistoricalLandslidePoint, Base

# Paths (CSVs are in project root, one level up from backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV1 = os.path.join(PROJECT_ROOT, "cleaned_data.csv")
CSV2 = os.path.join(PROJECT_ROOT, "Landslide_Final_Cleaned_V2.csv")


def load():
    # Ensure table exists
    Base.metadata.create_all(bind=engine)

    # ── 1. cleaned_data.csv ──
    print(f"[1/3] Reading {CSV1} ...")
    cols_available_1 = pd.read_csv(CSV1, nrows=0).columns.tolist()
    use_cols_1 = ["LONGITUDE", "LATITUDE"]
    for c in ["TAMBON", "DISTRICT", "PROVINCE"]:
        if c in cols_available_1:
            use_cols_1.append(c)
    df1 = pd.read_csv(CSV1, usecols=use_cols_1)
    df1["source"] = "cleaned_data"
    print(f"   → {len(df1)} rows")

    # ── 2. Landslide_Final_Cleaned_V2.csv ──
    print(f"[2/3] Reading {CSV2} ...")
    df2 = pd.read_csv(CSV2)
    print(f"   → {len(df2)} total rows")
    
    # Filter: PROVINCE = น่าน AND Geohaz_E = 1
    df2 = df2[(df2["PROVINCE"] == "น่าน") & (df2["Geohaz_E"] == 1)].copy()
    print(f"   → {len(df2)} rows after filter (PROVINCE='น่าน' & Geohaz_E=1)")
    
    # Keep only the columns we need
    keep_cols = ["LONGITUDE", "LATITUDE"]
    for c in ["TAMBON", "DISTRICT", "PROVINCE"]:
        if c in df2.columns:
            keep_cols.append(c)
    df2 = df2[keep_cols].copy()
    df2["source"] = "landslide_final_v2"

    # ── 3. Combine & deduplicate ──
    combined = pd.concat([df1, df2], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["LATITUDE", "LONGITUDE"], keep="first")
    after = len(combined)
    print(f"[3/3] Combined: {before} → {after} unique points (dropped {before - after} duplicates)")

    # Normalize column names
    combined = combined.rename(columns={
        "LONGITUDE": "longitude",
        "LATITUDE": "latitude",
        "TAMBON": "tambon",
        "DISTRICT": "district",
        "PROVINCE": "province",
    })

    # Fill missing province
    if "province" not in combined.columns:
        combined["province"] = "น่าน"
    combined["province"] = combined["province"].fillna("น่าน")

    # ── Insert into DB ──
    db = SessionLocal()
    try:
        # Clear old data
        deleted = db.query(HistoricalLandslidePoint).delete()
        db.commit()
        if deleted:
            print(f"   Cleared {deleted} old records")

        # Bulk insert
        records = []
        for _, row in combined.iterrows():
            records.append(HistoricalLandslidePoint(
                latitude=row["latitude"],
                longitude=row["longitude"],
                tambon=row.get("tambon"),
                district=row.get("district"),
                province=row.get("province", "น่าน"),
                source=row["source"],
            ))

        CHUNK = 2000
        for i in range(0, len(records), CHUNK):
            db.bulk_save_objects(records[i:i + CHUNK])
            db.commit()
            print(f"   Inserted {min(i + CHUNK, len(records))}/{len(records)} ...")

        print(f"\n✅ Done! {len(records)} historical landslide points loaded into DB.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    load()
