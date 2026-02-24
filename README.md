# 🛡️ Landslide Early Warning System (Nan Province)

ระบบวิเคราะห์และแจ้งเตือนภัยดินถล่มล่วงหน้าแบบ Real-time สำหรับพื้นที่ **จังหวัดน่าน** โดยบูรณาการข้อมูลสภาพแวดล้อมจากดาวเทียม (Google Earth Engine) เข้ากับข้อมูลน้ำฝน (Open-Meteo & CHIRPS) และประมวลผลผ่านโมเดล **Machine Learning (Random Forest)** เพื่อประเมินความเสี่ยงระดับรายพื้นที่ (Grid 500x500 เมตร)

## ✨ ฟีเจอร์หลัก (Features)
- **Automated GEE Extraction:** ดึงค่าความชัน (Slope), ระดับความสูง (Elevation), ดัชนีพืชพรรณ (NDVI), ดัชนีความชื้น (NDWI) อัตโนมัติจาก Google Earth Engine
- **Rainfall Integration:** นำเข้าข้อมูลน้ำฝนย้อนหลังและฝนพยากรณ์ เพื่อคำนวณ "ฝนสะสม" (Rain 3D/5D/7D Prior) อย่างแม่นยำ
- **Machine Learning Inference:** ประเมินความน่าจะเป็น (Probability) ในการเกิดดินสไลด์ด้วย Random Forest Model
- **Interactive Map Dashboard:** แผนที่แสดงความเสี่ยง (High/Medium/Low) พร้อมระบบจำลองสถานการณ์สมมุติ (What-If Simulation) แจ้งเตือนเมื่อฝนตกหนัก
- **AI Chat Assistant:** ระบบถาม-ตอบข้อมูลดินถล่มอัตโนมัติ

---

## 🛠️ โครงสร้างโปรเจค (Project Structure)
โปรเจคถูกแบ่งออกเป็น 2 ส่วนหลัก:
1. **`backend/`** - FastAPI server ทำหน้าที่ดึงข้อมูล GEE, รันโมเดล ML, และส่ง API
2. **`frontend/`** - React (Vite) + Deck.gl ทำหน้าที่แสดงแผนที่ 3D และ UI ทั้งหมด

---

## 🚀 วิธีการติดตั้งและรันระบบ (How to Run)

### 1. การเตรียม Backend (FastAPI + Python)
เปิด Terminal และรันคำสั่งต่อไปนี้:

```bash
# เข้าสู่โฟลเดอร์โปรเจค
cd backend

# เปิดใช้งาน Virtual Environment (ถ้ามี)
# Windows: ..\venv\Scripts\activate
# Mac/Linux: source ../venv/bin/activate

# รันเซิฟเวอร์ Uvicorn
..\venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000
```
*💡 Backend จะรันอยู่ที่ `http://localhost:8000`*

### 2. การเตรียม Frontend (React + Vite)
เปิด Terminal **หน้าต่างใหม่** และรันคำสั่งต่อไปนี้:

```bash
# เข้าสู่โฟลเดอร์ frontend
cd frontend

# ติดตั้ง Dependencies (ทำครั้งแรกครั้งเดียว)
npm install

# รันเซิฟเวอร์ Frontend
npm run dev
```
*💡 Frontend จะรันอยู่ที่ `http://localhost:5173` (กดคลิก Link ที่โผล่ใน Terminal เพื่อเปิดหน้าเว็บแบบ Dashboard)*

---

## 🗺️ การใช้งานระบบเบื้องต้น
1. เมื่อเปิดหน้าเว็บครั้งแรก หากแผนที่ยังว่างเปล่า ให้กดปุ่ม **"🚀 Extract GEE"** เพื่อสั่งให้เซิร์ฟเวอร์ดึงข้อมูลจากดาวเทียมและสร้างตาราง Grid (ใช้เวลาประมาณ 3-5 นาที)
2. เมื่อได้ตาราง Grid แล้ว ให้กดปุ่ม **"⚡ Fetch Rainfall & Predict Now"** เพื่อดึงข้อมูลน้ำฝนล่าสุดเข้าสู่โมเดล และอัปเดตสีความเสี่ยงบนแผนที่
3. สามารถใช้แท็บ **🎯 What-If** เพื่อปักหมุดจำลองปริมาณฝน (เช่น 5,000 mm) ว่าจะทำให้พื้นที่นั้นเสี่ยงระดับไหน

---

## 🧠 โมเดล Machine Learning (Random Forest)
ระดับความเสี่ยงจะถูกประเมินจากสมการความน่าจะเป็น (Probability Score `p`):
- `p < 0.35` 🟢 **Low Risk (ความเสี่ยงต่ำ):** สีเทาอมเขียว (พื้นที่ปลอดภัย/เฝ้าระวังปกติ)
- `0.35 <= p < 0.70` 🟡 **Medium Risk (ความเสี่ยงปานกลาง):** สีส้ม (ฝนสะสมเริ่มสูง แจ้งเตือนมิสเตอร์เตือนภัย)
- `p >= 0.70` 🔴 **High Risk (ความเสี่ยงสูง):** สีแดง (อันตราย เสี่ยงดินถล่มสูง เตรียมอพยพ!)
