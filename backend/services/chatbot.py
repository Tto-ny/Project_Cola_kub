"""
Landslide RAG Chatbot - retrieves relevant grid data and answers questions
about landslide risk in Nan Province using rule-based NLP.
"""
import json
import os
import re
import math

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extracted_grid_data.json")
PRED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "predicted_grid_data.json")

# District lookup for spatial queries
DISTRICTS = {
    "เมืองน่าน": {"en": "Mueang Nan", "center": [100.773, 18.783]},
    "แม่จริม": {"en": "Mae Charim", "center": [100.85, 18.55]},
    "บ้านหลวง": {"en": "Ban Luang", "center": [100.60, 18.90]},
    "นาน้อย": {"en": "Na Noi", "center": [100.72, 18.35]},
    "ปัว": {"en": "Pua", "center": [101.08, 19.17]},
    "ท่าวังผา": {"en": "Tha Wang Pha", "center": [100.75, 19.13]},
    "เวียงสา": {"en": "Wiang Sa", "center": [100.70, 18.55]},
    "ทุ่งช้าง": {"en": "Thung Chang", "center": [101.05, 19.40]},
    "เชียงกลาง": {"en": "Chiang Klang", "center": [100.87, 19.28]},
    "นาหมื่น": {"en": "Na Muen", "center": [100.65, 18.20]},
    "สันติสุข": {"en": "Santi Suk", "center": [100.85, 18.90]},
    "บ่อเกลือ": {"en": "Bo Kluea", "center": [101.15, 19.25]},
    "สองแคว": {"en": "Song Khwae", "center": [100.98, 19.35]},
    "ภูเพียง": {"en": "Phu Phiang", "center": [100.80, 18.72]},
    "เฉลิมพระเกียรติ": {"en": "Chaloem Phra Kiat", "center": [101.15, 19.50]},
}

def _load_grid():
    # Prefer predicted data, fallback to raw extraction
    for path in [PRED_PATH, DATA_PATH]:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    return []

def _cells_near(grid, lon, lat, radius_deg=0.15):
    """Get cells within radius of a point."""
    return [c for c in grid if _dist(c, lon, lat) < radius_deg]

def _dist(cell, lon, lat):
    poly = cell.get('polygon', [])
    if not poly or len(poly) < 4:
        return float('inf')
    cx = sum(p[0] for p in poly[:4]) / 4
    cy = sum(p[1] for p in poly[:4]) / 4
    return math.sqrt((cx - lon)**2 + (cy - lat)**2)

def _summary_stats(cells):
    if not cells:
        return {"total": 0, "high": 0, "medium": 0, "low": 0, "avg_slope": 0, "avg_elev": 0}
    high = sum(1 for c in cells if c.get('risk') == 'High')
    med = sum(1 for c in cells if c.get('risk') == 'Medium')
    low = sum(1 for c in cells if c.get('risk') == 'Low')
    slopes = [c['properties'].get('Slope', 0) or 0 for c in cells]
    elevs = [c['properties'].get('Elevation', 0) or 0 for c in cells]
    return {
        "total": len(cells), "high": high, "medium": med, "low": low,
        "avg_slope": round(sum(slopes) / len(slopes), 1) if slopes else 0,
        "avg_elev": round(sum(elevs) / len(elevs), 0) if elevs else 0,
        "max_slope": round(max(slopes), 1) if slopes else 0,
    }

def chat(message: str) -> str:
    """Process a chat message and return an answer."""
    msg = message.lower().strip()
    grid = _load_grid()
    
    if not grid:
        return "ยังไม่มีข้อมูลในระบบครับ กรุณากดปุ่ม Extract GEE Features ก่อน แล้วค่อยถามใหม่นะครับ"
    
    total_stats = _summary_stats(grid)
    
    # ── Pattern matching ──
    
    # Overall summary
    if any(w in msg for w in ['สรุป', 'ภาพรวม', 'summary', 'overview', 'ทั้งหมด', 'รวม']):
        return (
            f"📊 **สรุปภาพรวมจังหวัดน่าน**\n\n"
            f"• Grid cells ทั้งหมด: **{total_stats['total']:,}** cells\n"
            f"• 🔴 High Risk: **{total_stats['high']:,}** cells ({total_stats['high']/max(total_stats['total'],1)*100:.1f}%)\n"
            f"• 🟠 Medium Risk: **{total_stats['medium']:,}** cells ({total_stats['medium']/max(total_stats['total'],1)*100:.1f}%)\n"
            f"• 🟢 Low Risk: **{total_stats['low']:,}** cells ({total_stats['low']/max(total_stats['total'],1)*100:.1f}%)\n"
            f"• Slope เฉลี่ย: **{total_stats['avg_slope']}°** (สูงสุด {total_stats['max_slope']}°)\n"
            f"• Elevation เฉลี่ย: **{total_stats['avg_elev']:.0f} เมตร**"
        )
    
    # High risk areas
    if any(w in msg for w in ['เสี่ยงสูง', 'อันตราย', 'high risk', 'danger', 'พื้นที่เสี่ยง', 'จุดเสี่ยง']):
        high_cells = [c for c in grid if c.get('risk') == 'High']
        if not high_cells:
            return "ตอนนี้ยังไม่พบพื้นที่เสี่ยงสูง (High Risk) ในข้อมูลปัจจุบันครับ"
        
        # Find which districts have highest concentration
        district_counts = {}
        for dname, dinfo in DISTRICTS.items():
            nearby = _cells_near(high_cells, dinfo['center'][0], dinfo['center'][1], 0.15)
            if nearby:
                district_counts[dname] = len(nearby)
        
        top_districts = sorted(district_counts.items(), key=lambda x: -x[1])[:5]
        
        result = f"🔴 **พื้นที่เสี่ยงสูง (High Risk)**\n\nมีทั้งหมด **{len(high_cells):,}** cells\n\n"
        if top_districts:
            result += "**อำเภอที่มีจุดเสี่ยงมากที่สุด:**\n"
            for dname, count in top_districts:
                result += f"• {dname} ({DISTRICTS[dname]['en']}): {count} cells\n"
        
        return result
    
    # District-specific query
    found_district = None
    for dname, dinfo in DISTRICTS.items():
        if dname in msg or dinfo['en'].lower() in msg:
            found_district = (dname, dinfo)
            break
    
    if found_district:
        dname, dinfo = found_district
        nearby = _cells_near(grid, dinfo['center'][0], dinfo['center'][1], 0.15)
        stats = _summary_stats(nearby)
        
        return (
            f"📍 **อำเภอ{dname} ({dinfo['en']})**\n\n"
            f"• Grid cells ในพื้นที่: **{stats['total']:,}** cells\n"
            f"• 🔴 High: {stats['high']:,} | 🟠 Medium: {stats['medium']:,} | 🟢 Low: {stats['low']:,}\n"
            f"• Slope เฉลี่ย: {stats['avg_slope']}°\n"
            f"• Elevation เฉลี่ย: {stats['avg_elev']:.0f} m\n\n"
            f"{'⚠️ พื้นที่นี้มีจุดเสี่ยงสูงจำนวนมาก ควรเฝ้าระวัง!' if stats['high'] > 10 else '✅ พื้นที่นี้ค่อนข้างปลอดภัย'}"
        )
    
    # Slope / terrain questions
    if any(w in msg for w in ['slope', 'ความชัน', 'ลาดเอียง']):
        steep = [c for c in grid if (c['properties'].get('Slope', 0) or 0) > 30]
        return (
            f"⛰️ **ข้อมูลความชัน (Slope)**\n\n"
            f"• Slope เฉลี่ย: **{total_stats['avg_slope']}°**\n"
            f"• Slope สูงสุด: **{total_stats['max_slope']}°**\n"
            f"• จุดที่ชันเกิน 30°: **{len(steep):,}** cells\n\n"
            f"พื้นที่ที่มี Slope สูงกว่า 25° ถือว่ามีความเสี่ยงดินถล่มสูงครับ"
        )
    
    # NDVI / vegetation
    if any(w in msg for w in ['ndvi', 'พืช', 'vegetation', 'ป่า', 'forest']):
        ndvi_vals = [c['properties'].get('NDVI', 0) or 0 for c in grid]
        avg_ndvi = sum(ndvi_vals) / len(ndvi_vals) if ndvi_vals else 0
        low_ndvi = sum(1 for v in ndvi_vals if v < 0.2)
        return (
            f"🌿 **ข้อมูลพืชพรรณ (NDVI)**\n\n"
            f"• NDVI เฉลี่ย: **{avg_ndvi:.3f}**\n"
            f"• พื้นที่ NDVI ต่ำ (<0.2): **{low_ndvi:,}** cells\n\n"
            f"NDVI ต่ำ = พืชปกคลุมน้อย = ความเสี่ยงดินถล่มสูงขึ้น"
        )
    
    # Rainfall
    if any(w in msg for w in ['ฝน', 'rain', 'rainfall', 'น้ำ', 'precipitation']):
        return (
            f"🌧️ **ข้อมูลฝน**\n\n"
            f"ระบบดึงข้อมูลฝนจาก Open-Meteo API แบบ Real-time ครับ\n"
            f"• กดปุ่ม **⚡ Fetch Rainfall & Predict Now** ที่แท็บ Map เพื่อดึงข้อมูลฝนล่าสุดและทำนายความเสี่ยงใหม่\n"
            f"• หรือใช้ **🎯 What-If** เพื่อจำลองสถานการณ์ฝนตกที่จุดใดจุดหนึ่ง"
        )
    
    # Help / generic
    if any(w in msg for w in ['help', 'ช่วย', 'ทำอะไรได้', 'คำสั่ง', 'วิธีใช้']):
        return (
            "🤖 **สิ่งที่ถามได้:**\n\n"
            "• **\"สรุป\"** → ภาพรวมความเสี่ยงทั้งจังหวัด\n"
            "• **\"พื้นที่เสี่ยงสูง\"** → อำเภอที่มี High Risk มากสุด\n"
            "• **\"อ.ปัว\"** หรือ **\"Pua\"** → สถิติเฉพาะอำเภอ\n"
            "• **\"slope\"** → ข้อมูลความชันของพื้นที่\n"
            "• **\"ndvi\"** → ข้อมูลพืชพรรณ\n"
            "• **\"ฝน\"** → ข้อมูลฝนและวิธีใช้\n"
        )
    
    # Default
    return (
        f"ขอบคุณสำหรับคำถามครับ 🙏\n\n"
        f"ตอนนี้ระบบมีข้อมูล **{total_stats['total']:,}** cells | "
        f"🔴 {total_stats['high']:,} High | 🟠 {total_stats['medium']:,} Med | 🟢 {total_stats['low']:,} Low\n\n"
        f"ลองถาม: **สรุป**, **พื้นที่เสี่ยงสูง**, **อ.ปัว**, **slope**, **ndvi**, **ฝน** หรือพิมพ์ **help** ดูนะครับ"
    )
