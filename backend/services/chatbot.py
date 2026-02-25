import json
import os
import re
import math
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from database import GridCell

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

def get_stats_from_db(db: Session, cx=None, cy=None, radius_deg=0.15):
    """Fetch aggregated stats directly using PostgreSQL."""
    if cx is not None and cy is not None:
        # Distance filter condition
        dist_filter = f"(POWER(longitude - {cx}, 2) + POWER(latitude - {cy}, 2)) < {radius_deg**2}"
        where_clause = f"WHERE {dist_filter}"
    else:
        where_clause = ""
        dist_filter = "1=1"

    total = db.execute(text(f"SELECT COUNT(*) FROM grid_data {where_clause}")).scalar() or 0
    if total == 0:
        return {"total": 0, "high": 0, "medium": 0, "low": 0, "avg_slope": 0, "max_slope": 0, "avg_elev": 0}
        
    high = db.execute(text(f"SELECT COUNT(*) FROM grid_data WHERE risk = 'High' AND {dist_filter}")).scalar() or 0
    medium = db.execute(text(f"SELECT COUNT(*) FROM grid_data WHERE risk = 'Medium' AND {dist_filter}")).scalar() or 0
    low = db.execute(text(f"SELECT COUNT(*) FROM grid_data WHERE risk = 'Low' AND {dist_filter}")).scalar() or 0
    
    avg_slope = db.execute(text(f"SELECT AVG((properties->>'Slope')::float) FROM grid_data {where_clause}")).scalar() or 0
    max_slope = db.execute(text(f"SELECT MAX((properties->>'Slope')::float) FROM grid_data {where_clause}")).scalar() or 0
    avg_elev = db.execute(text(f"SELECT AVG((properties->>'Elevation')::float) FROM grid_data {where_clause}")).scalar() or 0
    
    return {
        "total": total, "high": high, "medium": medium, "low": low,
        "avg_slope": round(avg_slope, 1),
        "max_slope": round(max_slope, 1),
        "avg_elev": round(avg_elev, 0)
    }

def chat(message: str, db: Session) -> str:
    """Process a chat message and return an answer."""
    msg = message.lower().strip()
    
    total_count = db.query(GridCell).count()
    if total_count == 0:
        return "ยังไม่มีข้อมูลในระบบครับ กรุณากดปุ่ม Extract GEE Features ก่อน แล้วค่อยถามใหม่นะครับ"
    
    # ── Pattern matching ──
    
    # Overall summary
    if any(w in msg for w in ['สรุป', 'ภาพรวม', 'summary', 'overview', 'ทั้งหมด', 'รวม']):
        total_stats = get_stats_from_db(db)
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
        high_cells_count = db.execute(text("SELECT COUNT(*) FROM grid_data WHERE risk = 'High'")).scalar() or 0
        if high_cells_count == 0:
            return "ตอนนี้ยังไม่พบพื้นที่เสี่ยงสูง (High Risk) ในข้อมูลปัจจุบันครับ"
        
        # Find which districts have highest concentration
        district_counts = {}
        for dname, dinfo in DISTRICTS.items():
            cx, cy = dinfo['center']
            dist_filter = f"(POWER(longitude - {cx}, 2) + POWER(latitude - {cy}, 2)) < {0.15**2}"
            count = db.execute(text(f"SELECT COUNT(*) FROM grid_data WHERE risk = 'High' AND {dist_filter}")).scalar() or 0
            if count > 0:
                district_counts[dname] = count
        
        top_districts = sorted(district_counts.items(), key=lambda x: -x[1])[:5]
        
        result = f"🔴 **พื้นที่เสี่ยงสูง (High Risk)**\n\nมีทั้งหมด **{high_cells_count:,}** cells\n\n"
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
        cx, cy = dinfo['center']
        stats = get_stats_from_db(db, cx, cy, 0.15)
        
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
        total_stats = get_stats_from_db(db)
        steep_count = db.execute(text("SELECT COUNT(*) FROM grid_data WHERE (properties->>'Slope')::float > 30")).scalar() or 0
        return (
            f"⛰️ **ข้อมูลความชัน (Slope)**\n\n"
            f"• Slope เฉลี่ย: **{total_stats['avg_slope']}°**\n"
            f"• Slope สูงสุด: **{total_stats['max_slope']}°**\n"
            f"• จุดที่ชันเกิน 30°: **{steep_count:,}** cells\n\n"
            f"พื้นที่ที่มี Slope สูงกว่า 25° ถือว่ามีความเสี่ยงดินถล่มสูงครับ"
        )
    
    # NDVI / vegetation
    if any(w in msg for w in ['ndvi', 'พืช', 'vegetation', 'ป่า', 'forest']):
        avg_ndvi = db.execute(text("SELECT AVG((properties->>'NDVI')::float) FROM grid_data")).scalar() or 0
        low_ndvi = db.execute(text("SELECT COUNT(*) FROM grid_data WHERE (properties->>'NDVI')::float < 0.2")).scalar() or 0
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
    total_stats = get_stats_from_db(db)
    return (
        f"ขอบคุณสำหรับคำถามครับ 🙏\n\n"
        f"ตอนนี้ระบบมีข้อมูล **{total_stats['total']:,}** cells | "
        f"🔴 {total_stats['high']:,} High | 🟠 {total_stats['medium']:,} Med | 🟢 {total_stats['low']:,} Low\n\n"
        f"ลองถาม: **สรุป**, **พื้นที่เสี่ยงสูง**, **อ.ปัว**, **slope**, **ndvi**, **ฝน** หรือพิมพ์ **help** ดูนะครับ"
    )
