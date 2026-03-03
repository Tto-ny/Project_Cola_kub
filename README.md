# 🛡️ Landslide Early Warning System (Nan Province)

ระบบวิเคราะห์และแจ้งเตือนภัยดินถล่มล่วงหน้าแบบ Real-time สำหรับพื้นที่ **จังหวัดน่าน** โดยบูรณาการข้อมูลสภาพแวดล้อมจากดาวเทียม (Google Earth Engine) เข้ากับข้อมูลน้ำฝน (Open-Meteo & CHIRPS) และประมวลผลผ่านโมเดล **Machine Learning (Random Forest)** เพื่อประเมินความเสี่ยงระดับรายพื้นที่ (Grid 500x500 เมตร)

## ✨ ฟีเจอร์ใหม่และหลัก (Features)
- **Automated GEE Extraction:** ดึงค่าความชัน (Slope), ระดับความสูง (Elevation), ดัชนีพืชพรรณ (NDVI), ดัชนีความชื้น (NDWI) อัตโนมัติจาก Google Earth Engine
- **Rainfall Integration:** นำเข้าข้อมูลน้ำฝนย้อนหลังและฝนพยากรณ์ เพื่อคำนวณ "ฝนสะสม" (Rain 3D/5D/7D Prior) อย่างแม่นยำ
- **Machine Learning Inference:** ประเมินความน่าจะเป็น (Probability) ในการเกิดดินสไลด์ด้วย Random Forest Model
- **Interactive Map Dashboard:** แผนที่แสดงความเสี่ยง (High/Medium/Low) พร้อมระบบจำลองสถานการณ์สมมุติ (What-If Simulation)
- **📅 Alert History Management:** ระบบบันทึกประวัติการแจ้งเตือน สามารถเลือกดูย้อนหลังตามช่วงวันที่ และกรองจุดเสี่ยงย้อนหลังได้
- **🔍 Advanced Search:** ค้นหาพื้นที่ได้ละเอียดระดับ **ตำบล (Tambon)** และ **อำเภอ (Amphoe)** พร้อมระบบ Autocomplete
- **AI Chat Assistant:** ระบบถาม-ตอบข้อมูลดินถล่มอัตโนมัติ

---

## 🛠️ โครงสร้างโปรเจค (Project Structure)
โปรเจคถูกแบ่งออกเป็น 2 ส่วนหลัก:
1. **`backend/`** - FastAPI server ทำหน้าที่ดึงข้อมูล GEE, รันโมเดล ML, และจัดการฐานข้อมูล SQLite (Local)
2. **`frontend/`** - React (Vite) + Deck.gl ทำหน้าที่แสดงแผนที่ 3V และ UI ทั้งหมด

---

## 🚀 วิธีการติดตั้งและรันระบบแบบ Local (How to Run on Localhost)

### 1. การตั้งค่าไฟล์ `.env` สำหรับ Backend
สร้างไฟล์ `.env` ไว้ในโฟลเดอร์ `backend/` โดยมีรายละเอียดดังนี้:

```env
# 1. GEE_PROJECT_ID: ไอดีโปรเจคจาก Google Cloud
# วิธีเอา: ไปที่ https://console.cloud.google.com/ สร้างโปรเจคใหม่ 
# และเปิดใช้งาน (Enable) "Google Earth Engine API" จากนั้นนำ Project ID มาใส่
GEE_PROJECT_ID=your-project-id-123

# 2. DATABASE_URL: ที่อยู่ของฐานข้อมูล
# สำหรับ Local (เครื่องตัวเอง) ให้ใช้ค่าด้านล่างนี้ได้เลย ระบบจะสร้างไฟล์ .db ให้เองอัตโนมัติ
DATABASE_URL=sqlite:///./landslide.db

# 3. SECRET_KEY: รหัสลับสำหรับความปลอดภัยของ Login
# สามารถพิมพ์สุ่มอะไรก็ได้ยาวๆ เช่น my-super-secret-key-2024
SECRET_KEY=any-random-string-here
```

### 2. การเตรียม Backend (FastAPI + Python)
เปิด Terminal และรันคำสั่งต่อไปนี้:

```bash
# เข้าสู่โฟลเดอร์ backend
cd backend

# 1. สร้าง Virtual Environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# 2. ติดตั้ง Dependencies
pip install -r requirements.txt

# 3. เตรียมฐานข้อมูลและนำเข้าข้อมูล Grid (ทำครั้งแรก)
# คำสั่งนี้จะสร้าง landslide.db และนำเข้าข้อมูลจากไฟล์ JSON/CSV
python database_migrator.py

# 4. สร้าง Account ผู้ดูแล (Admin) สำหรับ Login
python create_admin.py

# 5. รันเซิฟเวอร์ API
uvicorn main:app --host 0.0.0.0 --port 8000
```
*💡 Backend จะรันอยู่ที่ `http://localhost:8000`*

### 3. การเตรียม Frontend (React + Vite)
เปิด Terminal **หน้าต่างใหม่** และรันคำสั่งต่อไปนี้:

```bash
# เข้าสู่โฟลเดอร์ frontend
cd frontend

# ติดตั้ง Dependencies
npm install

# รันเซิฟเวอร์ Frontend
npm run dev
```
*💡 Frontend จะรันอยู่ที่ `http://localhost:5173`*

---

## 🗺️ การใช้งานระบบเบื้องต้น
1. **Login:** เข้าสู่ระบบด้วย User ที่สร้างจาก `create_admin.py`
2. **Dashboard:** หากแผนที่ยังไม่มีข้อมูล ให้เลือกแท็บ "Map" และตรวจสอบว่ามีไฟล์ `landslide.db` เรียบร้อยแล้ว
3. **History:** ใช้แท็บ 📅 History เพื่อดูข้อมูลการแจ้งเตือนย้อนหลัง โดยเลือกช่วงวันที่ที่ต้องการ
4. **Search:** พิมพ์ชื่อตำบลหรืออำเภอในช่องค้นหาเพื่อซูมไปยังพื้นที่นั้นๆ

---

## 🧠 โมเดล Machine Learning (Random Forest)
ระดับความเสี่ยงจะถูกประเมินจากสมการความน่าจะเป็น (Probability Score `p`):
- `p < 0.35` 🟢 **Low Risk:** พื้นที่ปลอดภัย/เฝ้าระวังปกติ
- `0.35 <= p < 0.70` 🟡 **Medium Risk:** แจ้งเตือนระดับเฝ้าระวัง
- `p >= 0.70` 🔴 **High Risk:** อันตราย เสี่ยงดินถล่มสูง เตรียมอพยพ!

---

## 📝 Requirements ล่าสุด
- **Python 3.10+**
- **Node.js 18+**
- **Libraries สำคัญ:**
    - `FastAPI`, `SQLAlchemy` (ORM)
    - `scikit-learn`, `numpy`, `pandas` (ML/Data)
    - `earthengine-api` (GEE)
    - `PyJWT`, `bcrypt` (Auth)
    - `react-map-gl`, `deck.gl` (Visualization)

