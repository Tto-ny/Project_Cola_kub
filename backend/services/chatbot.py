import json
import os
import re
import math
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from database import GridCell

load_dotenv(override=True)

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
        dist_filter = f"(((longitude - {cx}) * (longitude - {cx})) + ((latitude - {cy}) * (latitude - {cy}))) < {radius_deg**2}"
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
    
    avg_slope = db.execute(text(f"SELECT AVG(CAST(json_extract(properties, '$.Slope') AS REAL)) FROM grid_data {where_clause}")).scalar() or 0
    max_slope = db.execute(text(f"SELECT MAX(CAST(json_extract(properties, '$.Slope') AS REAL)) FROM grid_data {where_clause}")).scalar() or 0
    avg_elev = db.execute(text(f"SELECT AVG(CAST(json_extract(properties, '$.Elevation') AS REAL)) FROM grid_data {where_clause}")).scalar() or 0
    
    return {
        "total": total, "high": high, "medium": medium, "low": low,
        "avg_slope": round(avg_slope, 1),
        "max_slope": round(max_slope, 1),
        "avg_elev": round(avg_elev, 0)
    }

def chat(message: str, db: Session) -> str:
    """Process a chat message and return an answer using LLM API."""
    msg = message.strip()
    
    total_count = db.query(GridCell).count()
    if total_count == 0:
        return "ยังไม่มีข้อมูลในระบบครับ กรุณากดปุ่ม Extract GEE Features ก่อน แล้วค่อยถามใหม่นะครับ"
    
    # ── Context Gathering ──
    stats = get_stats_from_db(db)
    
    context_lines = [
        f"ข้อมูลรวมจังหวัดน่าน:",
        f"จำนวนจุดทั้งหมด: {stats['total']:,} จุด",
        f"ความเสี่ยงสูง (High Risk): {stats['high']:,} จุด",
        f"ความเสี่ยงปานกลาง (Medium Risk): {stats['medium']:,} จุด",
        f"ความเสี่ยงต่ำ (Low Risk): {stats['low']:,} จุด",
        f"ความชันเฉลี่ย: {stats['avg_slope']} องศา, สูงสุด: {stats['max_slope']} องศา",
        f"ความสูงเฉลี่ย: {stats['avg_elev']} เมตร"
    ]
    
    # Check for specific district mentions
    for dname, dinfo in DISTRICTS.items():
        if dname in msg or dinfo['en'].lower() in msg.lower():
            cx, cy = dinfo['center']
            d_stats = get_stats_from_db(db, cx, cy, 0.15)
            context_lines.extend([
                f"\nข้อมูลเฉพาะพื้นที่อำเภอ{dname} ({dinfo['en']}):",
                f"จำนวนจุด: {d_stats['total']:,} จุด",
                f"ความเสี่ยงสูง: {d_stats['high']:,} จุด, ปานกลาง: {d_stats['medium']:,} จุด, ต่ำ: {d_stats['low']:,} จุด",
                f"ความชันเฉลี่ย: {d_stats['avg_slope']} องศา, ความสูงเฉลี่ย: {d_stats['avg_elev']} เมตร"
            ])
            break
            
    # Include steep / ndvi summary if asked
    msg_lower = msg.lower()
    if any(w in msg_lower for w in ['slope', 'ความชัน', 'ลาดเอียง']):
        steep_count = db.execute(text("SELECT COUNT(*) FROM grid_data WHERE CAST(json_extract(properties, '$.Slope') AS REAL) > 30")).scalar() or 0
        context_lines.append(f"\nจุดที่มีความชันเกิน 30 องศา: {steep_count:,} จุด (ความชันเกิน 25 องศาถือว่าเสี่ยงสูง)")
        
    if any(w in msg_lower for w in ['ndvi', 'พืช', 'vegetation', 'ป่า', 'forest']):
        avg_ndvi = db.execute(text("SELECT AVG(CAST(json_extract(properties, '$.NDVI') AS REAL)) FROM grid_data")).scalar() or 0
        low_ndvi = db.execute(text("SELECT COUNT(*) FROM grid_data WHERE CAST(json_extract(properties, '$.NDVI') AS REAL) < 0.2")).scalar() or 0
        context_lines.append(f"\nดัชนีพืชพรรณ (NDVI) เฉลี่ย: {avg_ndvi:.3f}, จุดที่ NDVI ต่ำ(<0.2): {low_ndvi:,} จุด (พืชน้อย=เสี่ยงสูง)")
            
    context_text = "\n".join(context_lines)
    
    system_prompt = (
        "You are an intelligent assistant for a Landslide Prediction System in Nan province, Thailand. "
        "Answer the user's questions in Thai based on the provided context about the current landslide risk data. "
        "Summarize the information naturally, use markdown formatting if helpful. If the user asks for details not in the context, "
        "politely inform them that you only have the provided summary data at the moment, and suggest exploring the map. "
        "Recommend specific features like 'What-If Simulation' or 'Extract GEE' if relevant. "
        "Always be helpful and polite."
    )
    
    api_key = os.getenv("KKU_AI_API_KEY")
    if not api_key:
        return "❌ ไม่พบ API Key ครับ กรุณาตั้งค่า KKU_AI_API_KEY ใน .env ก่อนใช้งาน Chatbot"
    url = "https://gen.ai.kku.ac.th/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gemini-2.5-flash-lite",
        "messages": [
            {"role": "system", "content": f"{system_prompt}\n\n[Context Data]\n{context_text}"},
            {"role": "user", "content": msg}
        ],
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบจาก AI: {str(e)}\n\n(สถิติเบื้องต้น: ระบบมีจุดเสี่ยงสูงทั้งหมด {stats['high']:,} จุด จากทั้งหมด {stats['total']:,} จุด)"
